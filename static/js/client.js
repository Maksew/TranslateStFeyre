document.addEventListener('DOMContentLoaded', function() {
    const socket = io({
        transports: ['websocket'],
        upgrade: false
    });

    const languageSelect = document.getElementById('language-select');
    const languageTitle = document.getElementById('language-title');
    const translationElement = document.getElementById('translation');
    const recordingStatusDot = document.getElementById('recording-status');
    const statusText = document.getElementById('status-text');

    // Set default language to French
    let currentLanguage = 'fr';

    // Language names mapping
    const languageNames = {
        'fr': 'Français',
        'en': 'English',
        'es': 'Español',
        'de': 'Deutsch',
        'it': 'Italiano'
    };

    // Connection debugging
    socket.on('connect', function() {
        console.log('Connecté au serveur avec ID:', socket.id);
    });

    socket.on('disconnect', function() {
        console.log('Déconnecté du serveur');
    });

    // Socket.io event handlers
    socket.on('update_translations', function(translations) {
        console.log("Reçu translations:", translations);
        if (translations && translations[currentLanguage]) {
            translationElement.textContent = translations[currentLanguage];
        } else {
            translationElement.textContent = 'Aucune traduction disponible';
        }
    });

    socket.on('update_transcription', function(data) {
        console.log("Reçu transcription:", data);
    });

    socket.on('recording_status', function(data) {
        console.log("Reçu status:", data);
        const isRecording = data.status;
        recordingStatusDot.classList.toggle('active', isRecording);
        statusText.textContent = isRecording ? 'Présentation en cours...' : 'En attente...';
    });

    socket.on('heartbeat', function(data) {
        // Heartbeat pour garder la connexion active
        console.log("Heartbeat reçu:", data.timestamp);
    });

    // Language selector event handler
    languageSelect.addEventListener('change', function() {
        currentLanguage = this.value;
        languageTitle.textContent = languageNames[currentLanguage] || currentLanguage;

        // Re-request the current translation
        socket.emit('get_translation', { language: currentLanguage });
    });
});