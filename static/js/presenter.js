document.addEventListener('DOMContentLoaded', function() {
    const socket = io();
    const startButton = document.getElementById('start-recording');
    const stopButton = document.getElementById('stop-recording');
    const resetButton = document.getElementById('reset');
    const transcriptionElement = document.getElementById('transcription');
    const recordingStatusDot = document.getElementById('recording-status');
    const statusText = document.getElementById('status-text');
    const serverIpElement = document.getElementById('server-ip');
    const copyUrlButton = document.getElementById('copy-url');

    // Get the server IP address
    serverIpElement.textContent = window.location.hostname;

    // Socket.io event handlers
    socket.on('update_transcription', function(data) {
        transcriptionElement.textContent = data.text || 'Aucune transcription disponible';
    });

    socket.on('recording_status', function(data) {
        const isRecording = data.status;
        recordingStatusDot.classList.toggle('active', isRecording);
        statusText.textContent = isRecording ? 'Enregistrement en cours...' : 'Prêt';
        startButton.disabled = isRecording;
        stopButton.disabled = !isRecording;
    });

    // Button event handlers
    startButton.addEventListener('click', function() {
        fetch('/start_recording', {
            method: 'POST'
        });
    });

    stopButton.addEventListener('click', function() {
        fetch('/stop_recording', {
            method: 'POST'
        });
    });

    resetButton.addEventListener('click', function() {
        fetch('/reset', {
            method: 'POST'
        });
    });

    copyUrlButton.addEventListener('click', function() {
        const clientUrl = document.getElementById('client-url').textContent;
        navigator.clipboard.writeText(clientUrl)
            .then(() => {
                copyUrlButton.textContent = 'Copié!';
                setTimeout(() => {
                    copyUrlButton.textContent = 'Copier';
                }, 2000);
            });
    });
});