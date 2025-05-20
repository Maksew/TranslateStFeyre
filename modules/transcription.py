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
            num_workers=1  # Nombre de workers pour le chargement
        )

        self.language = language
        self.full_transcript = ""

        # Initialiser un cache simple pour les segments courts répétés
        self.segment_cache = {}
        self.cache_size = 100  # Limite du cache

        if self.device == "cuda" and model_name in ["medium", "large"]:
            torch.cuda.set_per_process_memory_fraction(0.6)
            print(f"[CUDA] Limitation mémoire à 60% de la VRAM disponible pour modèle {model_name}")

    def transcribe_audio(self, audio_data, sample_rate: int) -> str:
        """Retourne le texte transcrit pour un segment audio avec améliorations de continuité."""
        start = time.time()

        print(f"[Audio] Taille: {audio_data.size}, Max: {np.max(np.abs(audio_data))}")

        # Conversion de type doit être en premier
        if audio_data.dtype == np.int16:
            print(f"[Conversion] Audio converti de {audio_data.dtype} à float32")
            audio_data = audio_data.astype(np.float32) / 32768.0

        # Recherche dans le cache (pour les phrases répétées)
        audio_bytes = audio_data.tobytes()
        cache_key = hashlib.md5(audio_bytes).hexdigest()
        if cache_key in self.segment_cache:
            transcript = self.segment_cache[cache_key]
            print(f"[Whisper] Cache hit! « {transcript} »")

            # Mettre à jour la transcription complète de manière intelligente
            if self.full_transcript and transcript:
                # Éviter la duplication de contenu
                if not self.full_transcript.endswith(transcript):
                    # Ajouter un espace pour éviter les mots collés
                    self.full_transcript += " " + transcript.strip()
            else:
                self.full_transcript = transcript

            return transcript

        # Préparation du prompt contextuel pour améliorer la continuité
        prompt = None
        if self.full_transcript:
            # Utiliser les derniers mots comme contexte
            prompt = f"Transcription précédente: \"{self.full_transcript[-200:]}\". Suite:"

        # Paramètres optimisés pour la GTX 1660 Ti
        segments, _ = self.model.transcribe(
            audio_data,
            language=self.language,
            initial_prompt=prompt,
            vad_filter=False,  # Le VAD est déjà appliqué en amont
            beam_size=3,  # Réduit pour performance sans trop sacrifier la qualité
            best_of=1,
            temperature=0,
            compression_ratio_threshold=2.0,  # Plus tolérant pour les segments courts
            log_prob_threshold=-1.5,  # Légèrement plus restrictif
            no_speech_threshold=0.35  # Plus sensible
        )

        # Concatène tous les segments
        transcript = " ".join(seg.text for seg in segments).strip()

        # Mise à jour intelligente du full_transcript
        if transcript:
            if self.full_transcript:
                # Analyse pour éviter les redondances
                transcript_words = transcript.split()
                full_words = self.full_transcript.split()

                # Vérifier si les premiers mots du nouveau segment sont les mêmes
                # que les derniers mots de la transcription existante
                overlap_detected = False
                for i in range(min(3, len(transcript_words))):  # Vérifier jusqu'à 3 mots
                    if len(full_words) >= i + 1 and transcript_words[:i + 1] == full_words[-i - 1:]:
                        # Supprimer le chevauchement
                        transcript = " ".join(transcript_words[i + 1:])
                        overlap_detected = True
                        break

                # Ajouter avec espace si nécessaire
                if transcript:
                    if overlap_detected or self.full_transcript[-1] in ".!?":
                        self.full_transcript += " " + transcript
                    else:
                        # S'assurer qu'il y a un espace
                        self.full_transcript += " " + transcript
            else:
                self.full_transcript = transcript

        # Mettre en cache si le segment est court
        if len(transcript) < 50 and len(self.segment_cache) < self.cache_size:
            self.segment_cache[cache_key] = transcript

        # Gérer le cache
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