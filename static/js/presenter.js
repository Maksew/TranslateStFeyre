const fetchWithTimeout = (url, options, timeout = 10000) => {
    return Promise.race([
        fetch(url, options),
        new Promise((_, reject) =>
            setTimeout(() => reject(new Error('Timeout')), timeout)
        )
    ]);
};

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

        if (isRecording) {
            startButton.innerText = 'Enregistrement démarré';  // État "démarré"
        } else {
            startButton.innerText = 'Démarrer l\'enregistrement';  // État initial
        }
    });

    socket.on('heartbeat', function(data) {
        // Heartbeat pour garder la connexion active
        console.log("Heartbeat reçu:", data.timestamp);
    });

    startButton.addEventListener('click', function() {
        startButton.innerText = 'Démarrage en cours...';
        startButton.disabled = true;

        fetchWithTimeout('/start_recording', { method: 'POST' }, 5000)
            .then(response => response.json())
            .then(data => {
                console.log("Réponse start:", data);
                // Le status sera mis à jour par les événements socket.io
            })
            .catch(error => {
                console.error('Erreur:', error);
                // En cas d'erreur, réactiver le bouton
                startButton.disabled = false;
                startButton.innerText = 'Démarrer l\'enregistrement';
            });
    });

    stopButton.addEventListener('click', function() {
        stopButton.innerText = 'Arrêt en cours...';
        stopButton.disabled = true;

        fetchWithTimeout('/stop_recording', { method: 'POST' }, 5000)
            .then(response => response.json())
            .then(data => {
                console.log("Réponse stop:", data);
                // Le status sera mis à jour par les événements socket.io
            })
            .catch(error => {
                console.error('Erreur:', error);
                stopButton.disabled = false;
                stopButton.innerText = 'Arrêter l\'enregistrement';
            });
    });

    resetButton.addEventListener('click', function() {
        fetchWithTimeout('/reset', { method: 'POST' }, 3000)
            .then(response => response.json())
            .then(data => console.log("Réponse reset:", data))
            .catch(error => console.error('Erreur:', error));
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