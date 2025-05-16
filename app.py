import os
import time
import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template, request, jsonify, session
from flask_socketio import SocketIO

# Importer la configuration
from config import (
    AWS_ACCESS_KEY, AWS_SECRET_KEY, AWS_REGION,
    FLASK_SECRET_KEY, WHISPER_MODEL, SOURCE_LANGUAGE,
    SUPPORTED_LANGUAGES, RECORDINGS_DIR
)

# Importer nos modules
from modules.audio_capture import AudioCapture
from modules.transcription import WhisperTranscriber
from modules.translation import AWSTranslator

# Initialisation de l'application Flask
app = Flask(__name__)
app.config['SECRET_KEY'] = FLASK_SECRET_KEY
socketio = SocketIO(app, async_mode='eventlet', cors_allowed_origins="*", ping_timeout=2)

# Initialiser les modules
transcriber = WhisperTranscriber(
    model_name=WHISPER_MODEL,
    language=SOURCE_LANGUAGE
)

translator = AWSTranslator(
    region_name=AWS_REGION,
    aws_access_key=AWS_ACCESS_KEY,
    aws_secret_key=AWS_SECRET_KEY
)

# Variables globales pour stocker les données
current_transcription = ""
translations = {}
is_recording = False
recorder = None


# Fonction de callback pour le traitement audio
def process_audio(audio_data, sample_rate, filename=None):
    global current_transcription, translations

    # Transcrire l'audio avec Whisper
    text = transcriber.transcribe_audio(audio_data, sample_rate)

    # Ne traduire que si nous avons du texte
    if text and not text.isspace():
        # Mettre à jour la transcription
        current_transcription = transcriber.get_full_transcript()

        # Traduire vers toutes les langues supportées
        translations = translator.translate_to_all(text)

        # Envoyer les mises à jour aux clients connectés
        emit_updates()


# Émission des mises à jour via websocket
def emit_updates():
    socketio.emit('update_transcription', {'text': current_transcription})
    socketio.emit('update_translations', translations)
    print(f"✅ Émis: transcription='{current_transcription[:30]}...'")


# Routes
@app.route('/')
def index():
    """Page principale pour le présentateur"""
    device_index = request.args.get('device')

    # Si un appareil spécifique est demandé, le stocker dans la session
    if device_index:
        try:
            device_index = int(device_index)
            session['device_index'] = device_index
        except ValueError:
            session.pop('device_index', None)  # Réinitialiser si invalide

    # Obtenir les informations sur le micro actuellement sélectionné
    current_device = None
    if 'device_index' in session and session['device_index'] is not None:
        devices = AudioCapture.list_devices()
        for device in devices:
            if device['index'] == session['device_index']:
                current_device = device
                break

    # Si aucun appareil n'est explicitement sélectionné, obtenir l'appareil par défaut
    if current_device is None:
        devices = AudioCapture.list_devices()
        for device in devices:
            if device.get('is_default'):
                current_device = device
                break

    return render_template('index.html',
                           languages=SUPPORTED_LANGUAGES,
                           is_recording=is_recording,
                           current_device=current_device)


@app.route('/client')
def client():
    """Page pour les clients (spectateurs)"""
    return render_template('client.html',
                           languages=SUPPORTED_LANGUAGES)


# API Routes
@app.route('/start_recording', methods=['POST'])
def start_recording():
    global recorder, is_recording

    if not is_recording:
        # Réinitialiser les transcriptions
        global current_transcription, translations
        current_transcription = ""
        translations = {}

        # Récupérer l'index du périphérique de la session
        device_index = session.get('device_index', None)

        # Initialiser et démarrer l'enregistrement
        recorder = AudioCapture(
            callback_function=process_audio,
            device_index=device_index,
            segment_seconds=1
        )
        recorder.start_recording()
        is_recording = True

        # Informer les clients
        socketio.emit('recording_status', {'status': True})

    return jsonify({"status": "recording_started"})


@app.route('/devices')
def list_devices():
    """Liste les périphériques d'entrée audio disponibles"""
    devices = AudioCapture.list_devices()
    return render_template('devices.html', devices=devices)


@app.route('/stop_recording', methods=['POST'])
def stop_recording():
    global recorder, is_recording

    if is_recording and recorder:
        recorder.stop_recording()
        is_recording = False

        # Informer les clients
        socketio.emit('recording_status', {'status': False})

    return jsonify({"status": "recording_stopped"})


@app.route('/reset', methods=['POST'])
def reset():
    global current_transcription, translations

    # Réinitialiser les transcriptions
    current_transcription = ""
    transcriber.reset_transcript()
    translations = {}

    # Informer les clients
    emit_updates()

    return jsonify({"status": "reset_done"})


# Websocket pour les connexions temps réel
@socketio.on('connect')
def handle_connect():
    # Envoyer l'état actuel au client qui vient de se connecter
    socketio.emit('update_transcription', {'text': current_transcription}, to=request.sid)
    socketio.emit('update_translations', translations, to=request.sid)
    socketio.emit('recording_status', {'status': is_recording}, to=request.sid)
    print(f"✅ Client connecté: {request.sid}")


def start_background_task():
    """Fonction qui s'exécute en arrière-plan pour envoyer périodiquement des mises à jour"""
    def send_updates():
        while True:
            # Forcer l'envoi des mises à jour toutes les 500ms
            if is_recording:
                socketio.emit('heartbeat', {'timestamp': time.time()})
            eventlet.sleep(0.5)  # 500ms

    return socketio.start_background_task(send_updates)


if __name__ == '__main__':
    # Créer les dossiers nécessaires
    if not os.path.exists(RECORDINGS_DIR):
        os.makedirs(RECORDINGS_DIR)

    # Assurez-vous que les répertoires pour les templates et static existent
    if not os.path.exists('templates'):
        os.makedirs('templates')
    if not os.path.exists('static'):
        os.makedirs('static')

    # Démarrer la tâche d'arrière-plan
    start_background_task()

    # Démarrer le serveur
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)