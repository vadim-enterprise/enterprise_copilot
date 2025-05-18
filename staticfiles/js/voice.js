class VoiceAssistant {
    constructor() {
        // Get voice bot button
        this.voiceBotButton = document.getElementById('voice-bot-button');
        
        // Initialize state
        this.isRecording = false;
        this.mediaRecorder = null;
        this.audioChunks = [];
        
        // FastAPI configuration
        this.fastApiUrl = 'http://127.0.0.1:8001';
        this.serverAvailable = false;
        this.serverCheckRetries = 0;
        this.maxRetries = 3;
        
        // Initialize services and event listeners
        this.initializeServices();
        this.setupEventListeners();
    }

    initializeServices() {
        // Check if FastAPI server is running
        this.startupCheck();
        
        // Initialize voice recognition
        this.initializeVoiceRecognition();
    }

    setupEventListeners() {
        // Voice bot button
        if (this.voiceBotButton) {
            this.voiceBotButton.addEventListener('click', () => this.toggleRecording());
        }
    }

    async startupCheck() {
        try {
            const response = await fetch(`${this.fastApiUrl}/api/health`);
            if (response.ok) {
                this.serverAvailable = true;
                console.log('FastAPI server is running');
            } else {
                throw new Error('Server not available');
            }
        } catch (error) {
            console.error('FastAPI server not running:', error);
            this.showNotification('Please start the FastAPI server for full functionality', 'warning');
        }
    }

    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.remove();
        }, 5000);
    }

    async initializeVoiceRecognition() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            this.mediaRecorder = new MediaRecorder(stream);
            
            this.mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    this.audioChunks.push(event.data);
                }
            };

            this.mediaRecorder.onstop = async () => {
                const audioBlob = new Blob(this.audioChunks, { type: 'audio/wav' });
                await this.processAudioInput(audioBlob);
                this.audioChunks = [];
            };
        } catch (error) {
            console.error('Error initializing voice recognition:', error);
            this.showNotification('Microphone access denied', 'error');
        }
    }

    async toggleRecording() {
        if (!this.isRecording) {
            // Start recording
            this.isRecording = true;
            this.voiceBotButton.classList.add('recording');
            this.audioChunks = [];
            this.mediaRecorder.start();
            this.showNotification('Recording...', 'info');
        } else {
            // Stop recording
            this.isRecording = false;
            this.voiceBotButton.classList.remove('recording');
            this.mediaRecorder.stop();
            this.showNotification('Processing audio...', 'info');
        }
    }

    async processAudioInput(audioBlob) {
        try {
            const formData = new FormData();
            formData.append('audio', audioBlob);

            const response = await fetch(`${this.fastApiUrl}/api/rag/audio_query`, {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            if (data?.status === 'success' && typeof data.response === 'string') {
                // Update search input with the transcribed text
                const searchInput = document.getElementById('webSearchInput');
                if (searchInput) {
                    searchInput.value = data.response;
                    // Trigger search
                    const searchButton = document.getElementById('webSearchButton');
                    if (searchButton) {
                        searchButton.click();
                    }
                }
            } else {
                throw new Error('Invalid response format from audio service');
            }
        } catch (error) {
            console.error('Error processing audio:', error);
            this.showNotification('Sorry, I encountered an error processing your audio.', 'error');
        }
    }
}

// Initialize voice assistant when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.voiceAssistant = new VoiceAssistant();
}); 