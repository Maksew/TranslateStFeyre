import whisper
import numpy as np
from faster_whisper import WhisperModel
import torch
import time

class WhisperTranscriber:
    def __init__(self,
                 model_name: str = "large-v3",
                 device: str = None,
                 language: str = "fr"):
        # Choix du device
        self.device = device or ("cuda" if __import__('torch').cuda.is_available() else "cpu")
        print(f"[Init] Chargement de Whisper « {model_name} » sur {self.device}…")

        # Chargement du modèle faster-whisper
        self.model = WhisperModel(
            model_name,
            device=self.device,
            compute_type="float16" if self.device.startswith("cuda") else "int8"
        )

        self.language = language
        self.full_transcript = ""

    def transcribe_audio(self, audio_data, sample_rate: int) -> str:
        """Retourne le texte transcrit pour un segment audio."""
        start = time.time()
        # Contexte : on conserve les 100 derniers caractères
        prompt = self.full_transcript[-100:] if self.full_transcript else None

        segments, _ = self.model.transcribe(
            audio_data,
            language=self.language,
            initial_prompt=prompt,
            vad_filter=True,
            beam_size=1,
            best_of=1
        )

        # Concatène tous les segments
        transcript = " ".join(seg.text for seg in segments).strip()
        self.full_transcript += (" " + transcript).strip()

        elapsed = time.time() - start
        print(f"[Whisper] « {transcript} » ({elapsed:.2f}s) RTF={(elapsed/(len(audio_data)/sample_rate)):.2f}×")
        return transcript

    def get_full_transcript(self) -> str:
        return self.full_transcript

    def reset_transcript(self):
        self.full_transcript = ""
