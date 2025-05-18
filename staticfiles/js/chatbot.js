class Chatbot {
    constructor() {
        // Get DOM elements
        this.widget = document.getElementById('chatbot-widget');
        this.messages = this.widget.querySelector('.chatbot-messages');
        this.input = this.widget.querySelector('.chatbot-input input');
        this.sendButton = this.widget.querySelector('.send-button');
        this.toggleButton = this.widget.querySelector('.chatbot-toggle');
        this.voiceBotButton = document.getElementById('voice-bot-button');
        
        // Initialize state
        this.isMinimized = false;
        this.isProcessing = false;
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
        // Toggle chatbot visibility
        this.toggleButton.addEventListener('click', () => this.toggleChatbot());
        
        // Send message on button click
        this.sendButton.addEventListener('click', () => this.handleSendMessage());
        
        // Send message on Enter key
        this.input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.handleSendMessage();
            }
        });

        // Voice bot button
        if (this.voiceBotButton) {
            this.voiceBotButton.addEventListener('click', () => this.toggleRecording());
        }
    }

    toggleChatbot() {
        this.isMinimized = !this.isMinimized;
        this.widget.classList.toggle('minimized');
        this.toggleButton.textContent = this.isMinimized ? '+' : '−';
    }

    async handleSendMessage() {
        const message = this.input.value.trim();
        if (!message || this.isProcessing) return;

        try {
            this.isProcessing = true;
            this.input.value = '';
            this.addMessage(message, 'user');
            this.setTypingIndicator(true);

            const response = await this.processMessage(message);
            this.addMessage(response, 'bot');
        } catch (error) {
            console.error('Error processing message:', error);
            this.addMessage('Sorry, I encountered an error processing your message.', 'bot');
        } finally {
            this.isProcessing = false;
            this.setTypingIndicator(false);
        }
    }

    async processMessage(message) {
        try {
            const response = await fetch(`${this.fastApiUrl}/api/rag/text_query`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                },
                mode: 'cors',
                body: JSON.stringify({ query: message })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            if (data?.status === 'success' && typeof data.response === 'string') {
                return data.response;
            } else {
                throw new Error('Invalid response format from RAG service');
            }
        } catch (error) {
            console.error('Error processing message:', error);
            return `Sorry, I encountered an error: ${error.message}`;
        }
    }

    addMessage(text, type) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}-message`;
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        contentDiv.textContent = text;
        
        messageDiv.appendChild(contentDiv);
        this.messages.appendChild(messageDiv);
        
        // Scroll to bottom
        this.messages.scrollTop = this.messages.scrollHeight;
    }

    setTypingIndicator(show) {
        const existingIndicator = this.messages.querySelector('.typing-indicator');
        if (show && !existingIndicator) {
            const indicator = document.createElement('div');
            indicator.className = 'typing-indicator';
            indicator.innerHTML = '<span></span><span></span><span></span>';
            this.messages.appendChild(indicator);
            this.messages.scrollTop = this.messages.scrollHeight;
        } else if (!show && existingIndicator) {
            existingIndicator.remove();
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
                this.addMessage(data.response, 'bot');
            } else {
                throw new Error('Invalid response format from audio service');
            }
        } catch (error) {
            console.error('Error processing audio:', error);
            this.addMessage('Sorry, I encountered an error processing your audio.', 'bot');
        }
    }
}

// Initialize chatbot when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.chatbot = new Chatbot();
}); 

