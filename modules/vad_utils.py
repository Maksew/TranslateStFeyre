import numpy as np
import torch


# Télécharger et charger le modèle Silero VAD
class SileroVAD:
    def __init__(self):
        self.model = None
        self.threshold = 0.55 # Ajustable: diminuer pour plus de sensibilité
        self.sampling_rate = 16000
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self._load_model()

    def _load_model(self):
        model, utils = torch.hub.load(repo_or_dir='snakers4/silero-vad',
                                      model='silero_vad',
                                      force_reload=False,
                                      onnx=False)
        self.model = model.to(self.device)
        (self.get_speech_timestamps, _, self.read_audio, _, _) = utils

    def is_speech(self, audio_np, return_filtered=True):
        # Normaliser l'audio si nécessaire
        if audio_np.dtype == np.int16:
            audio_np = audio_np.astype(np.float32) / 32768.0

        # Convertir en tensor torch
        audio_tensor = torch.from_numpy(audio_np).to(self.device)

        # Obtenir les timestamps de parole
        speech_timestamps = self.get_speech_timestamps(
            audio_tensor,
            self.model,
            threshold=self.threshold,
            sampling_rate=self.sampling_rate
        )

        if not return_filtered:
            return len(speech_timestamps) > 0

        # Si aucun segment de parole, retourner un tableau vide
        if not speech_timestamps:
            return np.zeros(0, dtype=np.float32)

        # Créer un masque pour ne conserver que les segments de parole
        filtered_audio = np.zeros_like(audio_np)
        for ts in speech_timestamps:
            filtered_audio[ts['start']:ts['end']] = audio_np[ts['start']:ts['end']]

        # Convertir en int16 si c'était le format d'origine
        if audio_np.dtype == np.int16:
            filtered_audio = (filtered_audio * 32768).astype(np.int16)

        return filtered_audio


# Initialiser le modèle Silero VAD
vad = SileroVAD()


def filter_speech(audio_np, sample_rate):
    """
    Ne conserve que les segments détectés comme parole.
    Retourne un numpy array concaténé.
    """
    # Vérification pour le débogage
    if audio_np.size == 0:
        print("[VAD] Audio vide reçu!")
        return audio_np

    # Vérifier le niveau sonore
    if np.max(np.abs(audio_np)) < 750 :
        print("[VAD] Niveau audio trop faible, ignoré")
        return np.zeros(0, dtype=np.int16)

    # Statistiques
    print(f"[VAD] Audio: {len(audio_np) / sample_rate:.2f}s, Max amplitude: {np.max(np.abs(audio_np))}")

    # Utiliser Silero VAD pour filtrer la parole
    filtered_audio = vad.is_speech(audio_np)

    # Journalisation
    has_speech = filtered_audio.size > 0
    print(f"[VAD] Parole détectée: {has_speech}, Taille: {filtered_audio.size}")

    return filtered_audio