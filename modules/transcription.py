import whisper
import numpy as np
import hashlib
from faster_whisper import WhisperModel
import torch
import time
import gc
import os


class WhisperTranscriber:
    def __init__(self,
                 model_name: str = "small",
                 device: str = None,
                 language: str = "fr"):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        print(f"[Init] Chargement de Whisper « {model_name} » sur {self.device}…")

        if self.device == "cuda":
            torch.cuda.empty_cache()
            print(
                f"[GPU] {torch.cuda.get_device_name(0)}, Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB")

        # Répertoire de cache local pour éviter les téléchargements répétés
        os.makedirs("models_cache", exist_ok=True)

        # Chargement du modèle faster-whisper avec paramètres optimisés
        self.model = WhisperModel(
            model_name,
            device=self.device,
            compute_type="int8_float16" if self.device == "cuda" else "int8",
            download_root="models_cache",  # Cache local
            cpu_threads=6,  # Optimisé pour Ryzen 5 4600H
            num_workers=2  # Nombre de workers pour le chargement
        )

        self.language = language
        self.full_transcript = ""

        # Initialiser un cache simple pour les segments courts répétés
        self.segment_cache = {}
        self.cache_size = 100  # Limite du cache

        if self.device == "cuda":
            # Limiter à 1.5GB pour laisser de l'espace pour d'autres opérations
            torch.cuda.set_per_process_memory_fraction(0.75)
            print(f"[CUDA] Limitation mémoire à 75% de la VRAM disponible")

    def transcribe_audio(self, audio_data, sample_rate: int) -> str:
        """Retourne le texte transcrit pour un segment audio."""
        start = time.time()

        print(f"[Audio] Taille: {audio_data.size}, Max: {np.max(np.abs(audio_data))}")

        # IMPORTANT: Conversion de type doit être EN PREMIER
        # Convertir de int16 à float32 et normaliser entre -1.0 et 1.0
        if audio_data.dtype == np.int16:
            print(f"[Conversion] Audio converti de {audio_data.dtype} à float32")
            audio_data = audio_data.astype(np.float32) / 32768.0

        # Recherche dans le cache (pour les phrases répétées)
        audio_bytes = audio_data.tobytes()
        cache_key = hashlib.md5(audio_bytes).hexdigest()
        if cache_key in self.segment_cache:
            transcript = self.segment_cache[cache_key]
            print(f"[Whisper] Cache hit! « {transcript} »")
            self.full_transcript += (" " + transcript).strip()
            return transcript

        # Contexte : on conserve les 200 derniers caractères (augmenté pour meilleure continuité)
        prompt = self.full_transcript[-200:] if self.full_transcript else None

        # Paramètres optimisés pour GTX 1660 Ti
        segments, _ = self.model.transcribe(
            audio_data,
            language=self.language,
            initial_prompt=prompt,
            vad_filter=False,  # Désactivez le VAD interne pour voir si c'est la cause
            beam_size=5,  # Augmentez pour améliorer la recherche
            best_of=1,
            temperature=0,
            compression_ratio_threshold=1.5,  # Plus tolérant (la valeur par défaut est 2.4)
            log_prob_threshold=-2.0,  # Plus tolérant (la valeur par défaut est -1.0)
            no_speech_threshold=0.3  # Plus sensible (la valeur par défaut est 0.6)
        )

        # Concatène tous les segments
        transcript = " ".join(seg.text for seg in segments).strip()
        self.full_transcript += (" " + transcript).strip()

        # Mettre en cache si le segment est court (évite les grosses entrées)
        if len(transcript) < 50 and len(self.segment_cache) < self.cache_size:
            self.segment_cache[cache_key] = transcript

        # Si le cache devient trop grand, supprimer les entrées les plus anciennes
        if len(self.segment_cache) >= self.cache_size:
            # Supprimer 20% des entrées les plus anciennes
            keys_to_remove = list(self.segment_cache.keys())[:int(self.cache_size * 0.2)]
            for key in keys_to_remove:
                del self.segment_cache[key]

        elapsed = time.time() - start
        rtf = elapsed / (len(audio_data) / sample_rate) if len(audio_data) > 0 else 0
        print(f"[Whisper] « {transcript} » ({elapsed:.2f}s) RTF={rtf:.2f}×")

        # Nettoyage mémoire occasionnel
        if time.time() % 60 < 1:  # Environ une fois par minute
            if self.device == "cuda":
                torch.cuda.empty_cache()
            gc.collect()

        return transcript

    def get_full_transcript(self) -> str:
        return self.full_transcript

    def reset_transcript(self):
        self.full_transcript = ""
        # Conserver le cache lors des réinitialisations