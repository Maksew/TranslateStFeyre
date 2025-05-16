import os
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO
import time
from dotenv import load_dotenv

load_dotenv()

from modules.audio_capture import AudioCapture
from modules.transcription import WhisperTranscriber
from modules.translation import AWSTranslator


# Initialisation de l'application Flask
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY')
socketio = SocketIO(app)

# Initialiser les modules
transcriber = WhisperTranscriber(
    model_name=os.getenv('WHISPER_MODEL', 'base'),
    language=os.getenv('SOURCE_LANGUAGE', 'fr')
)

translator = AWSTranslator(
    region_name=os.getenv('AWS_REGION'),
    aws_access_key=os.getenv('AWS_ACCESS_KEY'),
    aws_secret_key=os.getenv('AWS_SECRET_KEY')
)

current_transcription = ""
translations = {}
is_recording = False
recorder = None

# Langues supportées
supported_languages = {
    'fr': 'Français (original)',
    'en': 'English',
    'es': 'Español',
    'de': 'Deutsch',
    'it': 'Italiano'
}


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


# Routes
@app.route('/')
def index():
    """Page principale pour le présentateur"""
    return render_template('index.html',
                           languages=supported_languages,
                           is_recording=is_recording)


@app.route('/client')
def client():
    """Page pour les clients (spectateurs)"""
    return render_template('client.html',
                           languages=supported_languages)


# API Routes
@app.route('/start_recording', methods=['POST'])
def start_recording():
    global recorder, is_recording

    if not is_recording:
        # Réinitialiser les transcriptions
        global current_transcription, translations
        current_transcription = ""
        translations = {}

        # Initialiser et démarrer l'enregistrement
        recorder = AudioCapture(callback_function=process_audio, segment_seconds=3)
        recorder.start_recording()
        is_recording = True

        # Informer les clients
        socketio.emit('recording_status', {'status': True})

    return jsonify({"status": "recording_started"})


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


if __name__ == '__main__':
    # Créer les dossiers nécessaires
    if not os.path.exists('recordings'):
        os.makedirs('recordings')

    # Assurez-vous que les répertoires pour les templates et static existent
    if not os.path.exists('templates'):
        os.makedirs('templates')
    if not os.path.exists('static'):
        os.makedirs('static')

    # Démarrer le serveur
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)