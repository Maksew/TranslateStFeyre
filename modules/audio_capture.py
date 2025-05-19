import pyaudio
import numpy as np
import threading
import time
import wave
import os

class AudioCapture:
    def __init__(self, callback_function, device_index=None, chunk=1024, format=pyaudio.paInt16, channels=1,
                 rate=16000, segment_seconds=0.8, save_recordings=False, output_directory="recordings"):
        """
        Initialise la capture audio en temps réel.

        :param callback_function: Fonction à appeler avec chaque segment audio
        :param device_index: Index du périphérique d'entrée à utiliser (None = périphérique par défaut)
        :param chunk: Taille de bloc pour l'enregistrement
        :param format: Format audio (par défaut: 16-bit)
        :param channels: Nombre de canaux (1=mono)
        :param rate: Taux d'échantillonnage (16kHz recommandé pour Whisper)
        :param segment_seconds: Durée d'un segment d'enregistrement
        :param save_recordings: Si True, sauvegarde les segments audio (debug)
        :param output_directory: Dossier pour sauvegarder les fichiers si save_recordings=True
        """
        self.callback_function = callback_function
        self.device_index = device_index
        self.chunk = chunk
        self.format = format
        self.channels = channels
        self.rate = rate
        self.segment_seconds = segment_seconds
        self.save_recordings = save_recordings
        self.output_directory = output_directory
        self.recording = False
        self.audio = pyaudio.PyAudio()

        # Créer le dossier de sortie si nécessaire
        if save_recordings and not os.path.exists(output_directory):
            os.makedirs(output_directory)

    def start_recording(self):
        """Démarre l'enregistrement audio continu en temps réel"""
        self.recording = True
        self.thread = threading.Thread(target=self._process_audio_stream)
        self.thread.daemon = True
        self.thread.start()
        print("Capture audio en temps réel démarrée...")


    def stop_recording(self):
        """Arrête l'enregistrement audio"""
        self.recording = False
        if hasattr(self, 'thread') and self.thread.is_alive():
            self.thread.join()
        print("Capture audio arrêtée.")

    def _process_audio_stream(self):
        """Capture et traite l'audio en continu par segments"""
        stream = self.audio.open(
            format=self.format,
            channels=self.channels,
            rate=self.rate,
            input=True,
            input_device_index=self.device_index,
            frames_per_buffer=self.chunk
        )

        frames = []
        samples_per_segment = int(self.rate * self.segment_seconds)
        collected_samples = 0

        try:
            while self.recording:
                # Lire un morceau d'audio
                data = stream.read(self.chunk, exception_on_overflow=False)
                frames.append(data)
                collected_samples += self.chunk

                # Quand on a suffisamment d'échantillons pour former un segment
                if collected_samples >= samples_per_segment:
                    audio_segment = b''.join(frames)

                    # Sauvegarder le fichier (optionnel, pour debug)
                    filename = None
                    if self.save_recordings:
                        timestamp = int(time.time())
                        filename = f"{self.output_directory}/segment_{timestamp}.wav"
                        self._save_audio_file(filename, audio_segment)

                    # Appeler le callback avec les données audio en mémoire
                    # Note: on convertit les bytes en numpy array pour faciliter le traitement
                    audio_np = np.frombuffer(audio_segment, dtype=np.int16)
                    self.callback_function(audio_np, self.rate, filename)

                    # Réinitialiser pour le prochain segment
                    frames = []
                    collected_samples = 0
        finally:
            stream.stop_stream()
            stream.close()

    def _save_audio_file(self, filename, audio_data):
        """Sauvegarde les données audio dans un fichier WAV (pour debug)"""
        wf = wave.open(filename, 'wb')
        wf.setnchannels(self.channels)
        wf.setsampwidth(self.audio.get_sample_size(self.format))
        wf.setframerate(self.rate)
        wf.writeframes(audio_data)
        wf.close()
        print(f"Segment audio sauvegardé: {filename}")

    def __del__(self):
        """Libère les ressources PyAudio"""
        self.audio.terminate()

    @staticmethod
    def list_devices():
        """Liste les périphériques d'entrée audio pertinents"""
        p = pyaudio.PyAudio()
        device_count = p.get_device_count()
        devices = []
        default_device_index = p.get_default_input_device_info()['index'] if p.get_default_input_device_info() else None

        # Mots-clés pour filtrer les vrais microphones des périphériques virtuels
        real_mic_keywords = ['mic', 'microphone', 'input', 'casque', 'headset']

        for i in range(device_count):
            device_info = p.get_device_info_by_index(i)
            if device_info.get('maxInputChannels') > 0:  # C'est un périphérique d'entrée
                device_name = device_info.get('name', '').lower()

                # Détecter si c'est probablement un vrai micro (et pas un périphérique virtuel)
                is_real_mic = any(keyword in device_name for keyword in real_mic_keywords)

                # Ajouter seulement si c'est un vrai micro ou le périphérique par défaut
                if is_real_mic or i == default_device_index:
                    devices.append({
                        'index': i,
                        'name': device_info.get('name'),
                        'channels': device_info.get('maxInputChannels'),
                        'sample_rate': int(device_info.get('defaultSampleRate')),
                        'is_default': (i == default_device_index)
                    })

        p.terminate()
        return devices


# Test simple
if __name__ == "__main__":
    def process_audio(audio_data, sample_rate, filename=None):
        """Fonction de test pour le traitement audio"""
        duration = len(audio_data) / sample_rate
        print(f"Segment audio reçu: {duration:.2f} secondes")
        # Dans une vraie application, vous enverriez ces données à Whisper ici


    print("Test de la capture audio en temps réel. Appuyez sur Ctrl+C pour arrêter.")
    recorder = AudioCapture(callback_function=process_audio, segment_seconds=3, save_recordings=True)
    try:
        recorder.start_recording()
        # Test pendant 15 secondes
        time.sleep(15)
    except KeyboardInterrupt:
        print("Test interrompu.")
    finally:
        recorder.stop_recording()