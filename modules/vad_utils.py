import webrtcvad
import numpy as np

# Niveau d'agressivité 0–3 (3 = le plus strict sur les silences)
vad = webrtcvad.Vad(2)

def filter_speech(audio_np: np.ndarray, sample_rate: int) -> np.ndarray:
    """
    Ne conserve que les frames de 30 ms détectées comme parole.
    Retourne un numpy array (int16) concaténé.
    """
    pcm = audio_np.tobytes()
    frame_len = int(sample_rate * 0.03 * 2)  # 30 ms × 2 octets
    frames = [
        pcm[i : i + frame_len]
        for i in range(0, len(pcm), frame_len)
        if len(pcm[i : i + frame_len]) == frame_len
    ]
    speech_frames = [f for f in frames if vad.is_speech(f, sample_rate)]
    if not speech_frames:
        return np.zeros(0, dtype=np.int16)
    return np.frombuffer(b"".join(speech_frames), dtype=np.int16)
