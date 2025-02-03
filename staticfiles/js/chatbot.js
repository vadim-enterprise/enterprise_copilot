class Chatbot {
    constructor() {
        this.container = document.getElementById('chatbotContainer');
        this.messages = document.getElementById('chatbotMessages');
        this.form = document.getElementById('chatbotForm');
        this.input = document.getElementById('chatbotInput');
        this.widget = document.getElementById('chatbotWidget');
        this.minimizeBtn = document.getElementById('minimizeChatbot');
        this.enrichBtn = document.getElementById('enrichKnowledgeBase');
        this.voiceBotBtn = document.getElementById('voiceBotToggle');
        this.isVoiceMode = false;
        this.audio = new Audio();
        this.currentVoice = 'alloy';
        this.isRecording = false;
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.micButton = document.createElement('button');
        this.micButton.type = 'button';
        this.micButton.className = 'mic-button';
        this.micButton.innerHTML = '🎤';
        this.micButton.title = 'Click to start/stop recording';
        this.micButton.style.display = 'none';
        this.form.insertBefore(this.micButton, this.form.querySelector('button'));
        this.isProcessing = false;
        this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
        this.recordingStartTime = 0;
        
        // Pre-initialize audio stream
        navigator.mediaDevices.getUserMedia({ audio: true })
            .then(stream => {
                this.audioStream = stream;
            })
            .catch(console.error);
        
        // Add FastAPI base URL and fallback mode
        this.fastApiUrl = 'http://127.0.0.1:8001';
        this.serverAvailable = false;
        this.serverCheckRetries = 0;
        this.maxRetries = 3;
        this.fallbackMode = false;
        
        // Use the global SpeechManager
        this.speechManager = new window.SpeechManager();
        this.isSpeechMode = false;
        
        // Set up speech callbacks
        this.speechManager.setTranscriptCallback((text) => this.handleTranscript(text));
        this.speechManager.setAudioCallback((audio) => this.handleAudioResponse(audio));
        
        this.initializeServices();
        
        this.setupEventListeners();
    }

    setupEventListeners() {
        this.form.addEventListener('submit', (e) => this.handleSubmit(e));
        this.minimizeBtn.addEventListener('click', () => this.toggleMinimize());
        this.enrichBtn.addEventListener('click', () => this.enrichKnowledgeBase());
        this.voiceBotBtn.addEventListener('click', () => this.toggleVoiceMode());
        
        // Replace the old input listeners with mic button listeners
        this.micButton.addEventListener('click', (e) => this.toggleSpeechMode(e));
        
        // Add Company DNA button listener if element exists
        const dnaButton = document.querySelector('.company-dna');
        if (dnaButton) {
            dnaButton.addEventListener('click', () => this.handleCompanyDNA());
        }
    }

    async handleSubmit(event) {
        event.preventDefault();
        
        const message = this.input.value.trim();
        if (!message) return;

        // Clear input
        this.input.value = '';

        // Add user message to chat
        await this.addMessage(message, 'user');

        // Show typing indicator
        const typingIndicator = this.addTypingIndicator();

        try {
            const response = await this.getResponse(message);
            // Remove typing indicator
            typingIndicator.remove();
            
            // Add bot response
            await this.addMessage(response, 'bot');
        } catch (error) {
            typingIndicator.remove();
            await this.addMessage('Sorry, I encountered an error. Please try again.', 'bot');
            console.error('Chatbot error:', error);
        }
    }

    async getResponse(message) {
        try {
            const response = await fetch('/search-knowledge/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({ query: message })
            });

            const data = await response.json();

            if (data.status === 'success' && data.results) {
                // Format search results for display
                return this.formatSearchResults(data.results);
            } else {
                throw new Error(data.error || 'Failed to get response');
            }
        } catch (error) {
            console.error('Error getting chatbot response:', error);
            throw error;
        }
    }

    formatSearchResults(results) {
        return results.map(result => {
            return `
                <div class="search-result">
                    <h3><a href="${result.url}" target="_blank">${result.title}</a></h3>
                    <p>${result.summary}</p>
                    ${result.similarity_score ? `<small>Relevance: ${Math.round(result.similarity_score * 100)}%</small>` : ''}
                </div>
            `.trim();
        }).join('<br>');
    }

    async addMessage(content, type) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}-message`;
        messageDiv.innerHTML = `
            <div class="message-content">${content}</div>
        `;

        this.messages.appendChild(messageDiv);
        this.scrollToBottom();

        // Speak bot messages in voice mode
        if (type === 'bot' && this.isVoiceMode) {
            console.log('Attempting to speak:', content);
            await this.speakText(content);
        }
    }

    addTypingIndicator() {
        const typingDiv = document.createElement('div');
        typingDiv.className = 'message bot-message typing';
        typingDiv.innerHTML = `
            <div class="message-content">
                <div class="typing-indicator">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
            </div>
        `;

        this.messages.appendChild(typingDiv);
        this.scrollToBottom();
        return typingDiv;
    }

    scrollToBottom() {
        this.messages.scrollTop = this.messages.scrollHeight;
    }

    toggleMinimize() {
        this.widget.classList.toggle('minimized');
        this.minimizeBtn.textContent = this.widget.classList.contains('minimized') ? '+' : '−';
    }

    async enrichKnowledgeBase() {
        if (this.enrichBtn.classList.contains('loading')) return;

        try {
            this.enrichBtn.classList.add('loading');
            
            await this.addMessage('Enriching knowledge base...', 'bot');

            const response = await fetch('/enrich-knowledge-base/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({
                    source: 'chatbot_request'
                })
            });

            const data = await response.json();

            if (data.status === 'success') {
                await this.addMessage('Knowledge base has been successfully enriched! I now have more information to help you.', 'bot');
                
                this.showNotification('Knowledge base enriched successfully!', 'success');
            } else {
                throw new Error(data.message || 'Failed to enrich knowledge base');
            }
        } catch (error) {
            console.error('Error enriching knowledge base:', error);
            
            await this.addMessage('Sorry, I encountered an error while enriching the knowledge base. Please try again later.', 'bot');
            
            this.showNotification('Failed to enrich knowledge base', 'error');
        } finally {
            this.enrichBtn.classList.remove('loading');
        }
    }

    showNotification(message, type = 'success') {
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.style.animation = 'slideOut 0.3s ease-in forwards';
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }

    async toggleVoiceMode() {
        try {
            this.isVoiceMode = !this.isVoiceMode;
            this.voiceBotBtn.classList.toggle('voice-bot-active', this.isVoiceMode);

            if (this.isVoiceMode) {
                this.micButton.style.display = 'inline-block';
                this.showNotification('Voice mode activated', 'success');
            } else {
                this.speechManager.cleanup();
                this.micButton.style.display = 'none';
                if (this.isSpeechMode) {
                    this.isSpeechMode = false;
                    this.micButton.classList.remove('recording');
                }
                this.showNotification('Voice mode deactivated', 'info');
            }
        } catch (error) {
            console.error('Error toggling voice mode:', error);
            this.showNotification('Failed to toggle voice mode', 'error');
            this.isVoiceMode = false;
            this.voiceBotBtn.classList.remove('voice-bot-active');
        }
    }

    async initializeServices() {
        try {
            await this.checkServerWithRetry();
            if (!this.serverAvailable) {
                this.enableFallbackMode();
            }
        } catch (error) {
            console.error('Error initializing services:', error);
            this.enableFallbackMode();
        }
    }

    enableFallbackMode() {
        this.fallbackMode = true;
        this.voiceBotBtn.style.display = 'none';
        this.showNotification('Running in text-only mode. Voice features unavailable.', 'warning');
        console.log('Chatbot running in fallback mode (text-only)');
    }

    async checkServer() {
        try {
            const response = await fetch(`${this.fastApiUrl}/api/health-check`, {
                method: 'GET',
                headers: {
                    'Accept': 'application/json'
                },
                mode: 'cors'  // Add CORS mode
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            this.serverAvailable = data.status === 'ok';
            return this.serverAvailable;
            
        } catch (error) {
            console.error('Error checking FastAPI server:', error);
            this.serverAvailable = false;
            return false;
        }
    }

    async checkServerWithRetry() {
        while (this.serverCheckRetries < this.maxRetries) {
            if (await this.checkServer()) {
                return true;
            }
            this.serverCheckRetries++;
            // Add delay between retries
            await new Promise(resolve => setTimeout(resolve, 1000));
        }
        return false;
    }

    async speakText(text) {
        if (!this.isVoiceMode || !this.serverAvailable) return;
        
        try {
            const formData = new FormData();
            formData.append('text', text);
            formData.append('voice', this.currentVoice);
            
            console.log('Sending TTS request:', text);
            
            const response = await fetch(`${this.fastApiUrl}/api/generate-speech/`, {
                method: 'POST',
                body: formData,
                mode: 'cors',
                credentials: 'include'
            });
            
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.message || `HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            console.log('TTS Response:', data);
            
            if (data.status === 'success' && data.audio_url) {
                const audioUrl = `${this.fastApiUrl}${data.audio_url}`;
                console.log('Playing audio from:', audioUrl);
                
                this.audio = new Audio(audioUrl);
                await this.audio.play().catch(error => {
                    console.error('Audio playback error:', error);
                    throw error;
                });
            } else {
                throw new Error(data.message || 'Failed to generate speech');
            }
        } catch (error) {
            console.error('Error playing speech:', error);
            this.showNotification('Failed to play speech: ' + error.message, 'error');
        }
    }

    async toggleSpeechMode(e) {
        e.preventDefault();
        
        if (!this.isVoiceMode || this.isProcessing) {
            this.showNotification('Please enable voice mode first', 'warning');
            return;
        }
        
        this.isSpeechMode = !this.isSpeechMode;
        
        if (this.isSpeechMode) {
            try {
                this.micButton.classList.add('recording');
                await this.speechManager.startListening();
                this.showNotification('Speech mode activated - Start speaking', 'success');
            } catch (error) {
                console.error('Error starting speech mode:', error);
                this.isSpeechMode = false;
                this.micButton.classList.remove('recording');
                this.showNotification('Failed to start speech mode', 'error');
            }
        } else {
            this.micButton.classList.remove('recording');
            this.speechManager.stopListening();
            this.showNotification('Speech mode deactivated', 'info');
        }
    }

    async handleTranscript(text) {
        if (text.trim()) {
            // Add user's speech to chat
            await this.addMessage(text, 'user');
            
            // Get and display assistant's response
            const response = await this.getResponse(text);
            await this.addMessage(response, 'bot');
        }
    }

    handleAudioResponse(audio) {
        // Handle incoming audio from the assistant
        if (audio && this.isSpeechMode) {
            const audioBlob = new Blob([audio], { type: 'audio/wav' });
            const audioUrl = URL.createObjectURL(audioBlob);
            const audioEl = new Audio(audioUrl);
            audioEl.play();
        }
    }

    getCsrfToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]').value;
    }

    async handleCompanyDNA() {
        try {
            const response = await fetch('/api/company-dna/', {
                method: 'GET',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken')
                }
            });
            
            const data = await response.json();
            if (data.status === 'success') {
                this.addMessage("Here's what I know about our company:", 'bot');
                this.addMessage(data.content, 'bot');
            } else {
                throw new Error(data.error || 'Failed to fetch company DNA');
            }
        } catch (error) {
            console.error('Error fetching company DNA:', error);
            this.showNotification('Failed to fetch company information', 'error');
        }
    }
}
// Initialize chatbot when document loads
document.addEventListener('DOMContentLoaded', () => {
    new Chatbot();
}); 

