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
        
        // Check if FastAPI server is running
        this.startupCheck();
        
        // Use the global SpeechManager
        this.speechManager = new window.SpeechManager();
        this.speechManager.enableWhisper();
        this.speechManager.enableTTS();  // Enable TTS support
        this.isSpeechMode = false;

        this.speechManager.setTranscriptCallback((text) => {
            console.log('Received transcript:', text);
        });
        
        // Set up speech callbacks
        this.speechManager.setTranscriptCallback((text) => this.handleTranscript(text));
        this.speechManager.setAudioCallback((audio) => this.handleAudioResponse(audio));
        this.speechManager.setTTSCallback((audioUrl) => this.handleTTSResponse(audioUrl));
        
        // Add transcription properties
        this.isTranscribing = false;
        this.transcriptMessageDiv = null;
        this.currentTranscript = '';
        
        this.initializeServices();
        
        this.setupEventListeners();
    }

    setupEventListeners() {
        this.form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const message = this.input.value.trim();
            if (!message) return;

            this.input.value = '';
            await this.addMessage(message, 'user');
            
            const response = await this.processMessage(message);
            await this.addMessage(response, 'bot');
        });
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

    async processMessage(message) {
        try {
            this.setTypingIndicator(true);
            
            // Ensure message is a string
            const query = typeof message === 'string' ? message : String(message);
            
            const response = await fetch(`${this.fastApiUrl}/api/rag/text_query`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                },
                credentials: 'include',
                body: JSON.stringify({ query })
            });

            if (!response.ok) {
                const errorData = await response.json();
                console.error('RAG error response:', errorData);
                throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            console.log('RAG response:', data);
            if (data?.status === 'success' && typeof data.response === 'string') {
                return data.response;
            } else {
                console.error('Invalid response format:', data);
                throw new Error('Invalid response format from RAG service');
            }
        } catch (error) {
            console.error('Error processing message:', error);
            return `Sorry, I encountered an error: ${error.message}`;
        } finally {
            this.setTypingIndicator(false);
        }
    }

    async addMessage(message, sender) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}-message`;
        messageDiv.innerHTML = `<div class="message-content">${this.escapeHtml(message)}</div>`;
        this.messages.appendChild(messageDiv);
        this.scrollToBottom();
    }

    escapeHtml(unsafe) {
        return unsafe
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    async sendMessage(message, isVoice = false) {
        try {
            this.addUserMessage(message);
            this.setTypingIndicator(true);
            
            let response;
            if (!isVoice) {
                // Text mode - use knowledge base only
                const textResponse = await fetch(`${this.fastApiUrl}/api/rag/query`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ query: message })
                });

                if (!textResponse.ok) {
                    throw new Error(`HTTP error! status: ${textResponse.status}`);
                }

                const data = await textResponse.json();
                if (data.status === 'success') {
                    response = data.response;
                    // Optionally show sources
                    if (data.sources && data.sources.length > 0) {
                        response += '\n\nSources:\n' + data.sources.join('\n');
                    }
                } else {
                    throw new Error(data.message || 'Error processing query');
                }
            } else {
                // Voice mode - existing implementation
                response = await this.processVoiceMessage(message);
            }
            
            this.addBotMessage(response);
            
        } catch (error) {
            console.error('Error sending message:', error);
            this.addBotMessage('Sorry, I encountered an error processing your message.');
        } finally {
            this.setTypingIndicator(false);
        }
    }

    async processVoiceMessage(text) {
        try {
            const response = await this.processMessage(text);
            if (this.isVoiceMode) {
                await this.speechManager.speakText(response);
            }
            return response;
        } catch (error) {
            console.error('Error processing voice message:', error);
            return 'Sorry, I encountered an error processing your voice message.';
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

            const response = await fetch(`${this.fastApiUrl}/api/rag/enrich`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({})
            });

            const data = await response.json();

            if (data.status === 'success') {
                await this.addMessage('Knowledge base has been successfully enriched! I now have more information to help you.', 'bot');
                
                if (data.text_summary) {
                    await this.addMessage('Summary of loaded content:\n\n' + data.text_summary, 'bot');
                }
                
                // Update voice bot instructions with full knowledge base content
                if (data.full_content && window.speechManager) {
                    window.speechManager.setKnowledgeBase(data.full_content);
                }
                
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
            // Check server availability before enabling voice mode
            if (!this.serverAvailable) {
                const isAvailable = await this.checkServer();
                if (!isAvailable) {
                    this.showNotification('Voice mode unavailable - server not running', 'error');
                    return;
                }
            }

            if (this.isVoiceMode) {
                // Turning off voice mode
                this.isVoiceMode = false;
                this.isSpeechMode = false;  // Ensure speech mode is off
                this.voiceBotBtn.classList.remove('active');
                this.micButton.style.display = 'none';
                this.micButton.classList.remove('recording');
                
                if (window.speechManager) {
                    // First stop listening
                    window.speechManager.stopListening();
                    // Then cleanup the connection
                    await window.speechManager.cleanup();
                    // Reset the manager state
                    window.speechManager.isInitialized = false;
                    window.speechManager.isDataChannelReady = false;
                }
                
                this.showNotification('Voice mode deactivated', 'info');
            } else {
                // Turning on voice mode
                this.isVoiceMode = true;
                this.voiceBotBtn.classList.add('active');
                this.micButton.style.display = 'inline-block';
                
                // Initialize speech manager
                if (window.speechManager) {
                    await window.speechManager.initialize();
                }
                
                this.showNotification('Voice mode activated', 'success');
            }
        } catch (error) {
            console.error('Error toggling voice mode:', error);
            this.showNotification('Error toggling voice mode', 'error');
            
            // Reset all states in case of error
            this.isVoiceMode = false;
            this.isSpeechMode = false;
            this.voiceBotBtn.classList.remove('active');
            this.micButton.classList.remove('recording');
            this.micButton.style.display = 'none';
            
            if (window.speechManager) {
                window.speechManager.stopListening();
                await window.speechManager.cleanup();
                window.speechManager.isInitialized = false;
                window.speechManager.isDataChannelReady = false;
            }
        }
    }

    async initializeServices() {
        try {
            console.log('Initializing services...');
            await this.checkServerWithRetry();
            if (!this.serverAvailable) {
                console.log('Server not available, enabling fallback mode');
                this.enableFallbackMode();
            } else {
                console.log('Services initialized successfully');
            }
        } catch (error) {
            console.error('Error initializing services:', error);
            this.enableFallbackMode();
        }
    }

    enableFallbackMode() {
        this.fallbackMode = true;
        this.voiceBotBtn.style.display = 'none';
        this.enrichBtn.style.display = 'none';  // Hide enrich button in fallback mode
        this.showNotification('Running in text-only mode. Voice features unavailable.', 'warning');
        console.log('Chatbot running in fallback mode (text-only)');
    }

    async checkServer() {
        try {
            console.log('Attempting to connect to FastAPI server...');
            const response = await fetch(`${this.fastApiUrl}/api/health-check`, {
                method: 'GET',
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                },
            });

            if (!response.ok) {
                throw new Error(`Server responded with status: ${response.status}`);
            }

            const data = await response.json();
            return data.status === 'ok';
        } catch (error) {
            console.error('Error checking FastAPI server:', error);
            if (error.name === 'TypeError' && error.message.includes('Failed to fetch')) {
                console.log('FastAPI server is not running or not accessible');
                this.showNotification('Voice features unavailable - FastAPI server not running', 'warning');
            }
            return false;
        }
    }

    async checkServerWithRetry() {
        console.log('Checking FastAPI server availability...');
        for (let i = 0; i < this.maxRetries; i++) {
            console.log(`Attempt ${i + 1} of ${this.maxRetries}`);
            if (await this.checkServer()) {
                this.serverAvailable = true;
                console.log('FastAPI server is available');
                return;
            }
            console.log(`Server check attempt ${i + 1} failed, retrying...`);
            await new Promise(resolve => setTimeout(resolve, 2000));
        }
        console.log('Server check failed after all retries');
        this.serverAvailable = false;
    }

    async toggleSpeechMode(e) {
        e.preventDefault();
        
        if (!this.isVoiceMode || this.isProcessing) {
            this.showNotification('Please enable voice mode first', 'warning');
            return;
        }
        
        if (!this.isSpeechMode) {
            try {
                this.micButton.classList.add('recording');
                await this.speechManager.startListening();
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                this.mediaRecorder = new MediaRecorder(stream);
                this.audioChunks = [];
                
                this.mediaRecorder.ondataavailable = (event) => {
                    if (event.data.size > 0) {
                        this.audioChunks.push(event.data);
                    }
                };
                
                this.mediaRecorder.onstop = async () => {
                    const audioBlob = new Blob(this.audioChunks, { type: 'audio/webm' });
                    // Process both regular speech and Whisper transcription
                    await Promise.all([
                        this.speechManager.processAudio(audioBlob),
                        this.processWhisperTranscription(audioBlob)
                    ]);
                    this.audioChunks = [];
                };
                
                this.mediaRecorder.start(1000);
                this.isSpeechMode = true;
                this.showNotification('Speech mode activated - Start speaking', 'success');
            } catch (error) {
                console.error('Error starting speech mode:', error);
                this.isSpeechMode = false;
                this.micButton.classList.remove('recording');
                this.showNotification('Failed to start speech mode', 'error');
            }
        } else {
            this.micButton.classList.remove('recording');
            await this.speechManager.stopListening();
            if (this.mediaRecorder && this.mediaRecorder.state === 'recording') {
                this.mediaRecorder.stop();
            }
            this.isSpeechMode = false;
            await this.speechManager.cleanup();
            this.speechManager.isInitialized = false;
            this.showNotification('Speech mode deactivated', 'info');
        }
    }

    async handleTranscript(text) {
        if (text.trim()) {
            // Add user's speech to chat
            await this.addMessage(text, 'user');
            
            // Use the same processing as text mode
            const response = await this.processVoiceMessage(text);
            await this.addMessage(response, 'bot');
        }
    }

    handleAudioResponse(audioUrl) {
        if (audioUrl) {
            this.audio.src = audioUrl;
            this.audio.play();
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

    addUserMessage(message) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message user-message';
        messageDiv.innerHTML = `<div class="message-content">${message}</div>`;
        this.messages.appendChild(messageDiv);
        this.scrollToBottom();
    }

    addBotMessage(message) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message bot-message';
        messageDiv.innerHTML = `<div class="message-content">${message}</div>`;
        this.messages.appendChild(messageDiv);
        this.scrollToBottom();
    }

    setTypingIndicator(show) {
        const existingIndicator = this.messages.querySelector('.typing-indicator');
        if (existingIndicator) {
            existingIndicator.remove();
        }
        if (show) {
            const indicator = document.createElement('div');
            indicator.className = 'message bot-message typing-indicator';
            indicator.innerHTML = '<div class="dots"><span></span><span></span><span></span></div>';
            this.messages.appendChild(indicator);
            this.scrollToBottom();
        }
    }

    async startupCheck() {
        console.log('Performing initial FastAPI server check...');
        try {
            // First check if server is already running
            const isAvailable = await this.checkServer();
            if (isAvailable) {
                console.log('FastAPI server is already running');
                this.serverAvailable = true;
                return;
            }

            // If not running, show message to start server
            console.log('FastAPI server not running. Please start the server using:');
            console.log('python run.py in the fastapi_app directory');
            this.showNotification('Please start the FastAPI server for voice features', 'warning');
            
            // Enable fallback mode
            this.enableFallbackMode();
        } catch (error) {
            console.error('Startup check failed:', error);
            this.enableFallbackMode();
        }
    }

    async processWhisperTranscription(audioBlob) {
        try {
            const formData = new FormData();
            formData.append('audio', audioBlob, 'audio.webm');
            
            const response = await fetch(`${this.fastApiUrl}/api/speech/transcribe-speech/`, {
                method: 'POST',
                credentials: 'include',
                headers: {
                    'Accept': 'application/json'
                },
                body: formData
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            if (data.status === 'success' && data.text) {
                await this.showTranscript(data.text);
            }
        } catch (error) {
            console.error('Whisper transcription error:', error);
        }
    }

    async showTranscript(text) {
        if (!this.isTranscribing) {
            // Start new transcript
            this.isTranscribing = true;
            this.currentTranscript = text;
            this.transcriptMessageDiv = document.createElement('div');
            this.transcriptMessageDiv.className = 'message user-message transcript';
            this.transcriptMessageDiv.innerHTML = `
                <div class="message-content">
                    <div class="transcript-indicator">🎤 </div>
                    <span class="transcript-text">${this.escapeHtml(text)}</span>
                </div>
            `;
            this.messages.appendChild(this.transcriptMessageDiv);
            this.scrollToBottom();
        }
        
        // Process complete transcript
        await this.handleTranscript(text);
        this.isTranscribing = false;
        this.transcriptMessageDiv = null;
    }

    // Add new TTS handler without modifying existing ones
    async handleTTSResponse(audioUrl) {
        if (audioUrl && this.isVoiceMode) {
            this.audio.src = audioUrl;
            await this.audio.play();
        }
    }
}
// Initialize chatbot when document loads
document.addEventListener('DOMContentLoaded', () => {
    new Chatbot();
}); 

