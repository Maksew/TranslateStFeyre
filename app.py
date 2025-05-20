# app.py
import gc
import os
import time
import queue
import threading
import eventlet
import torch

from modules.vad_utils import filter_speech
eventlet.monkey_patch()

from flask import Flask, render_template, request, jsonify, session
from flask_socketio import SocketIO

from config import (
    AWS_ACCESS_KEY, AWS_SECRET_KEY, AWS_REGION,
    FLASK_SECRET_KEY, WHISPER_MODEL, SOURCE_LANGUAGE,
    SUPPORTED_LANGUAGES, RECORDINGS_DIR, CACHE_DIR
)
from modules.audio_capture import AudioCapture
from modules.transcription import WhisperTranscriber
from modules.translation import AWSTranslator

if torch.cuda.is_available():
    # Optimisations pour les GPU NVIDIA série 16xx
    torch.backends.cudnn.benchmark = True
    torch.cuda.empty_cache()
app = Flask(__name__)
app.config['SECRET_KEY'] = FLASK_SECRET_KEY
socketio = SocketIO(app, async_mode='eventlet', cors_allowed_origins="*")

# Files d’attente pour découplage
audio_q = queue.Queue(maxsize=10)
text_q  = queue.Queue(maxsize=10)

# Modules
transcriber = WhisperTranscriber(model_name=WHISPER_MODEL,
                                 device=None,
                                 language=SOURCE_LANGUAGE)
translator  = AWSTranslator(AWS_ACCESS_KEY,
                            AWS_SECRET_KEY,
                            AWS_REGION,
                            supported_languages=list(SUPPORTED_LANGUAGES.keys()))

current_transcription = ""
translations = {}
is_recording = False
recorder = None

def audio_callback(audio_np, sample_rate, filename=None):
    """Empile le segment brut, ne fait rien d’autre."""
    audio_q.put((audio_np, sample_rate))

def whisper_worker():
    global current_transcription
    while True:
        try:
            raw_audio, sr = audio_q.get(timeout=1)
            audio_np = filter_speech(raw_audio, sr)
            if audio_np.size == 0:
                continue
            text = transcriber.transcribe_audio(audio_np, sr)
            if text.strip():
                current_transcription = transcriber.get_full_transcript()
                text_q.put(text)
                emit_updates()
                time.sleep(0.1)
        except queue.Empty:
            continue
        except Exception as e:
            print(f"Erreur dans whisper_worker: {e}")
            continue


def translate_worker():
    global translations
    while True:
        text = text_q.get()
        translations = translator.translate_to_all(text, source_lang=SOURCE_LANGUAGE)
        emit_updates()

def emit_updates():
    socketio.emit('update_transcription', {'text': current_transcription})
    socketio.emit('update_translations', translations)

def memory_cleanup():
    while True:
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        time.sleep(60)  # Chaque minute

@app.route('/')
def index():
    device_index = request.args.get('device')
    if device_index:
        try:
            session['device_index'] = int(device_index)
        except ValueError:
            session.pop('device_index', None)

    devices = AudioCapture.list_devices()
    idx = session.get('device_index', None)
    current_device = next((d for d in devices if d['index']==idx), None) \
                     or next((d for d in devices if d.get('is_default')), None)
    return render_template('index.html',
                           languages=SUPPORTED_LANGUAGES,
                           is_recording=is_recording,
                           current_device=current_device)

@app.route('/client')
def client():
    return render_template('client.html',
                           languages=SUPPORTED_LANGUAGES)


@app.route('/start_recording', methods=['POST'])
def start_recording():
    global recorder, is_recording, current_transcription, translations

    # Empêcher les démarrages multiples
    if is_recording:
        return jsonify(status="already_recording")

    # Mettre à jour l'état AVANT de démarrer l'enregistrement effectif
    # pour que l'interface se mette à jour rapidement
    is_recording = True
    socketio.emit('recording_status', {'status': True})

    # Réinitialiser les transcriptions
    current_transcription, translations = "", {}
    emit_updates()

    # Maintenant démarrer l'enregistrement en arrière-plan
    device_index = session.get('device_index', None)
    try:
        def start_recording_task():
            global recorder
            recorder = AudioCapture(
                callback_function=audio_callback,
                device_index=device_index,
                segment_seconds=2.0
            )
            recorder.start_recording()

        # Démarrer dans un thread séparé
        threading.Thread(target=start_recording_task, daemon=True).start()
    except Exception as e:
        print(f"Erreur au démarrage de l'enregistrement: {e}")
        is_recording = False
        socketio.emit('recording_status', {'status': False})
        return jsonify(status="recording_error", error=str(e))

    return jsonify(status="recording_started")

@app.route('/stop_recording', methods=['POST'])
def stop_recording():
    global recorder, is_recording
    if is_recording and recorder:
        recorder.stop_recording()
        is_recording = False
        socketio.emit('recording_status', {'status': False})
    return jsonify(status="recording_stopped")

@app.route('/reset', methods=['POST'])
def reset():
    global current_transcription, translations
    current_transcription = ""
    transcriber.reset_transcript()
    translations = {}
    emit_updates()
    return jsonify(status="reset_done")

@socketio.on('connect')
def handle_connect():
    sid = request.sid
    socketio.emit('update_transcription', {'text': current_transcription}, to=sid)
    socketio.emit('update_translations', translations,    to=sid)
    socketio.emit('recording_status', {'status': is_recording}, to=sid)

def start_background_task():
    def heartbeat():
        while True:
            if is_recording:
                socketio.emit('heartbeat', {'ts': time.time()})
            eventlet.sleep(0.5)
    return socketio.start_background_task(heartbeat)

if __name__ == '__main__':
    if torch.cuda.is_available():
        device_name = torch.cuda.get_device_name(0)
        memory_gb = torch.cuda.get_device_properties(0).total_memory / 1e9
        print(f"🟢 CUDA disponible: {device_name} ({memory_gb:.2f} GB)")
        if "1660" in device_name:  # Vérification de votre GPU spécifique
            print("✅ Configuration optimisée pour GTX 1660 Ti")
    else:
        print("⚠️ ATTENTION: CUDA non disponible, utilisation du CPU uniquement (performances réduites)")
    os.makedirs(RECORDINGS_DIR, exist_ok=True)
    os.makedirs(CACHE_DIR, exist_ok=True)  # Pour le stockage cache
    threading.Thread(target=whisper_worker, daemon=True).start()
    threading.Thread(target=translate_worker, daemon=True).start()
    threading.Thread(target=memory_cleanup, daemon=True).start()
    start_background_task()
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
