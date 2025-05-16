document.addEventListener('DOMContentLoaded', function() {
    const socket = io({
        transports: ['websocket'],
        upgrade: false
    });

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

    // Connection debugging
    socket.on('connect', function() {
        console.log('Connecté au serveur avec ID:', socket.id);
    });

    socket.on('disconnect', function() {
        console.log('Déconnecté du serveur');
    });

    // Socket.io event handlers
    socket.on('update_transcription', function(data) {
        console.log("Reçu transcription:", data);
        transcriptionElement.textContent = data.text || 'Aucune transcription disponible';
    });

    socket.on('recording_status', function(data) {
        console.log("Reçu status:", data);
        const isRecording = data.status;
        recordingStatusDot.classList.toggle('active', isRecording);
        statusText.textContent = isRecording ? 'Enregistrement en cours...' : 'Prêt';
        startButton.disabled = isRecording;
        stopButton.disabled = !isRecording;
    });

    socket.on('heartbeat', function(data) {
        // Heartbeat pour garder la connexion active
        console.log("Heartbeat reçu:", data.timestamp);
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