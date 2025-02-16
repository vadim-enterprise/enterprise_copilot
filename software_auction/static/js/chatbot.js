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
        this.isSpeechMode = false;

        // Set up speech callbacks
        this.speechManager.setTranscriptCallback((text) => this.showTranscript(text));
        this.speechManager.setAudioCallback((audio) => this.handleAudioResponse(audio));
        
        // Add transcription properties
        this.isTranscribing = false;
        this.transcriptMessageDiv = null;
        this.currentTranscript = '';
        
        this.initializeServices();
        
        this.setupEventListeners();

        // Create chart container
        this.createChartContainer();
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
            
            // Check if text contains chart-related keywords
            if (this.isChartRequest(text)) {
                try {
                    const chartCode = this.generateChartCode(text);
                    // Add the chart code as a bot message with code formatting
                    await this.addMessage("Here's the Chart.js code for your request:\n```javascript\n" + 
                        chartCode + "\n```", 'bot');
                    
                    // Execute the chart code
                    try {
                        // Check if Chart.js is loaded
                        if (typeof Chart === 'undefined') {
                            throw new Error('Chart.js is not loaded. Please include the Chart.js library.');
                        }

                        // Destroy existing chart if any
                        if (window.currentChart) {
                            window.currentChart.destroy();
                        }
                        
                        // Execute the generated code
                        const ctx = document.getElementById('myChart').getContext('2d');
                        window.currentChart = new Chart(ctx, {
                            type: this.detectChartType(text),
                            data: {
                                labels: this.generateSampleData(text).labels,
                                datasets: [{
                                    label: this.generateSampleData(text).label,
                                    data: this.generateSampleData(text).values,
                                    backgroundColor: this.generateSampleData(text).colors,
                                    borderColor: this.generateSampleData(text).borderColors,
                                    borderWidth: 1
                                }]
                            },
                            options: {
                                responsive: true,
                                maintainAspectRatio: false,
                                scales: {
                                    y: {
                                        beginAtZero: true
                                    }
                                }
                            }
                        });
                    } catch (chartError) {
                        console.error('Error creating chart:', chartError);
                        await this.addMessage("Error: Could not create chart. " + chartError.message, 'bot');
                    }
                } catch (error) {
                    console.error('Error generating chart code:', error);
                    await this.addMessage("Sorry, I couldn't generate the chart code.", 'bot');
                }
            }
            
            // Use the same processing as text mode
            const response = await this.processVoiceMessage(text);
            await this.addMessage(response, 'bot');
        }
    }

    isChartRequest(text) {
        const chartKeywords = ['chart', 'graph', 'plot', 'bar chart', 'line graph', 'pie chart'];
        return chartKeywords.some(keyword => text.toLowerCase().includes(keyword));
    }

    generateChartCode(text) {
        // Basic chart type detection
        const type = this.detectChartType(text);
        
        // Generate sample data based on the request
        const data = this.generateSampleData(text);
        
        return `
            const ctx = document.getElementById('myChart').getContext('2d');
            new Chart(ctx, {
                type: '${type}',
                data: {
                    labels: ${JSON.stringify(data.labels)},
                    datasets: [{
                        label: '${data.label}',
                        data: ${JSON.stringify(data.values)},
                        backgroundColor: ${JSON.stringify(data.colors)},
                        borderColor: ${JSON.stringify(data.borderColors)},
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    scales: {
                        y: {
                            beginAtZero: true
                        }
                    }
                }
            });
        `.trim();
    }

    detectChartType(text) {
        if (text.toLowerCase().includes('pie')) return 'pie';
        if (text.toLowerCase().includes('line')) return 'line';
        if (text.toLowerCase().includes('bar')) return 'bar';
        return 'bar'; // default type
    }

    generateSampleData(text) {
        // Default sample data
        return {
            labels: ['January', 'February', 'March', 'April', 'May'],
            values: [12, 19, 3, 5, 2],
            label: 'Sample Data',
            colors: [
                'rgba(255, 99, 132, 0.2)',
                'rgba(54, 162, 235, 0.2)',
                'rgba(255, 206, 86, 0.2)',
                'rgba(75, 192, 192, 0.2)',
                'rgba(153, 102, 255, 0.2)'
            ],
            borderColors: [
                'rgba(255, 99, 132, 1)',
                'rgba(54, 162, 235, 1)',
                'rgba(255, 206, 86, 1)',
                'rgba(75, 192, 192, 1)',
                'rgba(153, 102, 255, 1)'
            ]
        };
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
            
            // Process complete transcript
            await this.handleTranscript(text);
            this.isTranscribing = false;
        }
    }

    createChartContainer() {
        // Create chart widget container
        this.chartWidget = document.createElement('div');
        this.chartWidget.id = 'chartWidget';
        this.chartWidget.className = 'chart-widget';
        
        // Create header with title and minimize button
        const header = document.createElement('div');
        header.className = 'chart-header';
        
        const title = document.createElement('span');
        title.textContent = 'Chart Display';
        
        const minimizeBtn = document.createElement('button');
        minimizeBtn.innerHTML = '−';
        minimizeBtn.className = 'minimize-chart';
        minimizeBtn.onclick = () => this.toggleChartWidget();
        
        header.appendChild(title);
        header.appendChild(minimizeBtn);
        
        // Create canvas for chart
        const chartContainer = document.createElement('div');
        chartContainer.className = 'chart-container';
        
        const canvas = document.createElement('canvas');
        canvas.id = 'myChart';
        
        chartContainer.appendChild(canvas);
        
        // Add resize handle
        const resizeHandle = document.createElement('div');
        resizeHandle.className = 'resize-handle';
        chartContainer.appendChild(resizeHandle);
        
        // Assemble widget
        this.chartWidget.appendChild(header);
        this.chartWidget.appendChild(chartContainer);
        
        // Add to document
        document.body.appendChild(this.chartWidget);
        
        // Make widget draggable
        this.makeChartWidgetDraggable();
        // Make widget resizable
        this.makeChartWidgetResizable();
    }

    toggleChartWidget() {
        const container = this.chartWidget.querySelector('.chart-container');
        const button = this.chartWidget.querySelector('.minimize-chart');
        
        if (container.style.display === 'none') {
            container.style.display = 'block';
            button.innerHTML = '−';
        } else {
            container.style.display = 'none';
            button.innerHTML = '+';
        }
    }

    makeChartWidgetDraggable() {
        const header = this.chartWidget.querySelector('.chart-header');
        let isDragging = false;
        let currentX;
        let currentY;
        let initialX;
        let initialY;
        let xOffset = 0;
        let yOffset = 0;
        
        header.addEventListener('mousedown', (e) => {
            initialX = e.clientX - xOffset;
            initialY = e.clientY - yOffset;
            
            if (e.target === header) {
                isDragging = true;
            }
        });
        
        document.addEventListener('mousemove', (e) => {
            if (isDragging) {
                e.preventDefault();
                
                currentX = e.clientX - initialX;
                currentY = e.clientY - initialY;
                
                xOffset = currentX;
                yOffset = currentY;
                
                this.chartWidget.style.transform = 
                    `translate(${currentX}px, ${currentY}px)`;
            }
        });
        
        document.addEventListener('mouseup', () => {
            isDragging = false;
        });
    }

    makeChartWidgetResizable() {
        const resizeHandle = this.chartWidget.querySelector('.resize-handle');
        let isResizing = false;
        let startWidth, startHeight, startX, startY;

        resizeHandle.addEventListener('mousedown', (e) => {
            isResizing = true;
            startX = e.clientX;
            startY = e.clientY;
            startWidth = this.chartWidget.offsetWidth;
            startHeight = this.chartWidget.offsetHeight;

            // Add event listeners
            document.addEventListener('mousemove', handleMouseMove);
            document.addEventListener('mouseup', () => {
                isResizing = false;
                document.removeEventListener('mousemove', handleMouseMove);
            });
        });

        const handleMouseMove = (e) => {
            if (!isResizing) return;

            // Calculate new size
            const newWidth = startWidth + (e.clientX - startX);
            const newHeight = startHeight + (e.clientY - startY);

            // Apply minimum dimensions
            this.chartWidget.style.width = `${Math.max(300, newWidth)}px`;
            this.chartWidget.style.height = `${Math.max(200, newHeight)}px`;

            // If there's an active chart, update its size
            if (window.currentChart) {
                window.currentChart.resize();
            }
        };
    }
}
// Initialize chatbot when document loads
document.addEventListener('DOMContentLoaded', () => {
    new Chatbot();
}); 

