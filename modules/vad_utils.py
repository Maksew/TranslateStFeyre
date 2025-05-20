import webrtcvad
import numpy as np

# Niveau d'agressivité encore plus faible (0 = le moins strict)
vad = webrtcvad.Vad(0)


def filter_speech(audio_np: np.ndarray, sample_rate: int) -> np.ndarray:
    """
    Ne conserve que les frames de 30 ms détectées comme parole.
    Retourne un numpy array (int16) concaténé.
    """
    # Ajouter cette vérification pour déboguer
    if audio_np.size == 0:
        print("[VAD] Audio vide reçu!")
        return audio_np

    # Ajouter un seuil minimum d'amplitude
    if np.max(np.abs(audio_np)) < 500:  # Très faible niveau sonore
        print("[VAD] Niveau audio trop faible, ignoré")
        return np.zeros(0, dtype=np.int16)

    # Imprimer des statistiques
    print(f"[VAD] Audio: {len(audio_np) / sample_rate:.2f}s, Max amplitude: {np.max(np.abs(audio_np))}")

    # Reste du code inchangé...
    pcm = audio_np.tobytes()
    frame_len = int(sample_rate * 0.03 * 2)
    frames = [
        pcm[i: i + frame_len]
        for i in range(0, len(pcm), frame_len)
        if len(pcm[i: i + frame_len]) == frame_len
    ]
    speech_frames = [f for f in frames if vad.is_speech(f, sample_rate)]

    # Ajouter ce log
    ratio = len(speech_frames) / len(frames) if frames else 0
    print(f"[VAD] Ratio parole: {ratio:.2f}, Frames: {len(speech_frames)}/{len(frames)}")

    if not speech_frames:
        return np.zeros(0, dtype=np.int16)
    return np.frombuffer(b"".join(speech_frames), dtype=np.int16)