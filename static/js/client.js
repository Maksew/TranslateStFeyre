document.addEventListener('DOMContentLoaded', function() {
    const socket = io();
    const languageSelect = document.getElementById('language-select');
    const languageTitle = document.getElementById('language-title');
    const translationElement = document.getElementById('translation');
    const recordingStatusDot = document.getElementById('recording-status');
    const statusText = document.getElementById('status-text');

    // Set default language to English
    let currentLanguage = 'fr';

    // Language names mapping
    const languageNames = {
        'fr': 'Français',
        'en': 'English',
        'es': 'Español',
        'de': 'Deutsch',
        'it': 'Italiano'
    };

    // Socket.io event handlers
    socket.on('update_translations', function(translations) {
        if (translations && translations[currentLanguage]) {
            translationElement.textContent = translations[currentLanguage];
        } else {
            translationElement.textContent = 'Aucune traduction disponible';
        }
    });

    socket.on('recording_status', function(data) {
        const isRecording = data.status;
        recordingStatusDot.classList.toggle('active', isRecording);
        statusText.textContent = isRecording ? 'Présentation en cours...' : 'En attente...';
    });

    // Language selector event handler
    languageSelect.addEventListener('change', function() {
        currentLanguage = this.value;
        languageTitle.textContent = languageNames[currentLanguage] || currentLanguage;

        // Re-request the current translation
        socket.emit('get_translation', { language: currentLanguage });
    });
});