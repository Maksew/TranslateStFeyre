import whisper
import numpy as np
import torch
import time


class WhisperTranscriber:
    def __init__(self, model_name="base", device=None, language="fr"):
        """
        Initialise le transcripteur Whisper.

        :param model_name: Taille du modèle Whisper ("tiny", "base", "small", "medium", "large")
        :param device: Appareil à utiliser pour l'inférence ("cpu" ou "cuda" pour GPU)
        :param language: Langue source pour la transcription
        """
        # Détection automatique du device (CPU ou GPU)
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device

        print(f"Chargement du modèle Whisper '{model_name}' sur {self.device}...")
        self.model = whisper.load_model(model_name, device=self.device)
        self.language = language
        print(f"Modèle Whisper chargé avec succès.")

        # Options de transcription
        self.options = {
            "task": "transcribe",
            "language": self.language,
            "beam_size": 5,
            "best_of": 5,
            "fp16": torch.cuda.is_available(),
            "without_timestamps": True,
        }

        # État de la transcription
        self.full_transcript = ""

    def transcribe_audio(self, audio_data, sample_rate):
        """
        Transcrit un segment audio en texte.

        :param audio_data: Données audio (numpy array)
        :param sample_rate: Taux d'échantillonnage
        :return: Texte transcrit
        """
        start_time = time.time()

        # Normalisation du signal audio (comme dans l'exemple Whisper)
        if sample_rate != 16000:
            print(f"ATTENTION: Rééchantillonnage requis de {sample_rate}Hz à 16000Hz")

        # Convertir en float32 et normaliser entre -1 et 1
        audio_data = audio_data.astype(np.float32) / 32768.0

        # Transcrire avec Whisper
        result = self.model.transcribe(audio_data, **self.options)

        # Extraire le texte transcrit
        transcript = result["text"].strip()

        # Calcul du temps de traitement
        elapsed_time = time.time() - start_time
        audio_duration = len(audio_data) / sample_rate
        rtf = elapsed_time / audio_duration if audio_duration > 0 else 0

        print(f"Transcription: '{transcript}'")
        print(f"Temps de traitement: {elapsed_time:.2f}s (RTF: {rtf:.2f}x)")

        # Mettre à jour la transcription complète
        self.full_transcript += " " + transcript

        return transcript

    def get_full_transcript(self):
        """Récupère la transcription complète depuis le début de la session"""
        return self.full_transcript.strip()

    def reset_transcript(self):
        """Réinitialise la transcription complète"""
        self.full_transcript = ""


# Test simple
if __name__ == "__main__":
    import wave


    # Charger un fichier audio pour le test
    def load_audio_file(file_path):
        with wave.open(file_path, 'rb') as wf:
            frames = wf.readframes(wf.getnframes())
            audio_data = np.frombuffer(frames, dtype=np.int16)
            sample_rate = wf.getframerate()
        return audio_data, sample_rate


    # Remplacer par le chemin vers un fichier audio de test
    test_file = "recordings/segment_example.wav"

    try:
        audio_data, sample_rate = load_audio_file(test_file)
        print(f"Fichier audio chargé: {len(audio_data) / sample_rate:.2f} secondes")

        transcriber = WhisperTranscriber(model_name="base")
        text = transcriber.transcribe_audio(audio_data, sample_rate)
        print(f"Transcription finale: {text}")
    except FileNotFoundError:
        print(f"Pour tester, créez d'abord un fichier audio avec audio_capture.py")