try {
    document.addEventListener('DOMContentLoaded', (event) => {

        const elements = {
            startButton: document.getElementById('start-recording'),
            stopButton: document.getElementById('stop-recording'),
            transcriptionOutput: document.getElementById('transcription-output'),
            insightsOutput: document.getElementById('insights-output'),
            copyButton: document.getElementById('copyTranscription'),
            clearButton: document.getElementById('clearTranscription')
        };

        Object.entries(elements).forEach(([name, element]) => {
            if (!element) {
                throw new Error(`Required element ${name} not found`);
            }
        });        

        let socket;
        let recognition = null;
        let wsRetryCount = 0;
        const MAX_RETRIES = 5;
        let isRecording = false;
        let finalTranscript = '';        

        function copyTranscription() {
            const text = elements.transcriptionOutput.innerText;
            navigator.clipboard.writeText(text)
                .then(() => {
                    alert('Transcription copied to clipboard!');
                })
                .catch(err => {
                    console.error('Failed to copy text:', err);
                    alert('Failed to copy text. Please try again.');
                });
        }

        function getCSRFToken() {
            let cookieValue = null;
            if (document.cookie && document.cookie !== '') {
                const cookies = document.cookie.split(';');
                for (let i = 0; i < cookies.length; i++) {
                    const cookie = cookies[i].trim();
                    if (cookie.substring(0, 10) === 'csrftoken=') {
                        cookieValue = decodeURIComponent(cookie.substring(10));
                        break;
                    }
                }
            }
            if (!cookieValue) {
                // Fallback to getting token from the DOM
                const tokenElement = document.querySelector('[name=csrfmiddlewaretoken]');
                if (tokenElement) {
                    cookieValue = tokenElement.value;
                }
            }
            return cookieValue;
        }

        function initializeSpeechRecognition() {
            if (!('webkitSpeechRecognition' in window)) {
                elements.transcriptionOutput.textContent = 'Speech recognition not supported in this browser.';
                return null;
            }
        
            try {
                recognition = new webkitSpeechRecognition();
                recognition.continuous = true;
                recognition.interimResults = true;
                recognition.lang = 'en-US';
        
                recognition.onstart = () => {
                    console.log('Speech recognition started');
                    isRecording = true;
                    elements.startButton.disabled = true;
                    elements.stopButton.disabled = false;
                };
        
                recognition.onresult = (event) => {
                    if (elements.transcriptionOutput.innerHTML === 'Listening...') {
                        elements.transcriptionOutput.innerHTML = '';
                    }
                
                    let interimTranscript = '';
                    let currentFinalTranscript = '';
                
                    for (let i = 0; i < event.results.length; i++) {
                        const result = event.results[i];
                        if (result.isFinal) {
                            currentFinalTranscript += result[0].transcript + ' ';
                            console.log('Final transcript:', result[0].transcript);
                        } else {
                            interimTranscript += result[0].transcript;
                            console.log('Interim transcript:', result[0].transcript);
                        }
                    }
                
                    if (currentFinalTranscript) {
                        finalTranscript = currentFinalTranscript;
                    }
                
                    elements.transcriptionOutput.innerHTML = 
                        finalTranscript + 
                        '<span style="color: #666;">' + interimTranscript + '</span>';
                
                    // Generate real-time insights when we have final transcript
                    if (currentFinalTranscript) {
                        generateRealTimeInsights(finalTranscript);
                    }
                
                    elements.transcriptionOutput.scrollTop = elements.transcriptionOutput.scrollHeight;
                };
                
                recognition.onend = () => {
                    console.log('Speech recognition ended');
                    if (isRecording) {
                        console.log('Restarting recognition');
                        try {
                            recognition.start();
                        } catch (error) {
                            console.error('Error restarting recognition:', error);
                        }
                    } else {
                        elements.startButton.disabled = false;
                        elements.stopButton.disabled = true;
                    }
                };
        
                return recognition;
        
            } catch (error) {
                console.error('Error initializing speech recognition:', error);
                elements.transcriptionOutput.textContent = 'Error initializing speech recognition';
                return null;
            }
        }

        function updateTranscriptionDisplay() {
            if (transcriptionBuffer.trim()) {
                let currentText = elements.transcriptionOutput.innerText;
                if (currentText === 'Listening...' || 
                    currentText === 'Waiting to start...' ||
                    currentText === 'Connected to transcription service...') {
                    currentText = '';
                }
                
                // Update display with buffered text
                elements.transcriptionOutput.innerText = (currentText + transcriptionBuffer).trim();
                
                // Clear buffer
                transcriptionBuffer = '';
                
                // Auto-scroll
                elements.transcriptionOutput.scrollTop = elements.transcriptionOutput.scrollHeight;
            }
        }

        let transcriptionBuffer = '';
        let lastUpdateTime = Date.now();
        const UPDATE_INTERVAL = 100; // Update every 100ms
        
        function setupWebSocket() {
            if (wsRetryCount >= MAX_RETRIES) {
                console.error('Max WebSocket connection retries reached');
                elements.transcriptionOutput.textContent = 'Unable to establish connection. Please refresh the page.';
                return null;
            }
        
            const protocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
            const wsUrl = `${protocol}${window.location.hostname}/ws/transcribe/`;
            
            console.log(`Attempting WebSocket connection to ${wsUrl}`);
        
            try {
                socket = new WebSocket(wsUrl);
        
                socket.onopen = function(e) {
                    console.log('WebSocket connection established');
                    wsRetryCount = 0;
                };
        
                socket.onmessage = function(e) {
                    try {
                        const data = JSON.parse(e.data);
                        console.log('WebSocket message received:', data);
                        
                        if (data.status === 'error') {
                            console.error('Server error:', data.error);
                        } else if (data.status === 'transcription' && data.text) {
                            console.log('Transcription received:', data.text);
                            
                            // Update the display immediately with new text
                            let currentText = elements.transcriptionOutput.innerText;
                            if (currentText === 'Listening...' || 
                                currentText === 'Waiting to start...' ||
                                currentText === 'Connected to transcription service...') {
                                currentText = '';
                            }
                            elements.transcriptionOutput.innerText = (currentText + ' ' + data.text).trim();
                            
                            // Auto-scroll
                            elements.transcriptionOutput.scrollTop = elements.transcriptionOutput.scrollHeight;
                        }
                    } catch (error) {
                        console.error('Error processing WebSocket message:', error);
                    }
                };
        
                socket.onerror = function(error) {
                    console.error('WebSocket error:', error);
                };
        
                socket.onclose = function(event) {
                    console.log('WebSocket connection closed:', event);
                    if (!event.wasClean) {
                        wsRetryCount++;
                        if (wsRetryCount < MAX_RETRIES) {
                            console.log('Attempting to reconnect...');
                            setTimeout(setupWebSocket, 2000);
                        }
                    }
                };
        
                return socket;
            } catch (error) {
                console.error('Error creating WebSocket:', error);
                return null;
            }
        }

        function sendAudioChunk(blob) {
            if (socket && socket.readyState === WebSocket.OPEN) {
                const reader = new FileReader();
                reader.onloadend = () => {
                    const base64data = reader.result.split(',')[1];
                    socket.send(JSON.stringify({
                        audio_data: base64data,
                        format: 'raw',
                        sample_rate: 44100,
                        channels: 1
                    }));
                };
                reader.readAsDataURL(blob);
            }
        }

        function startRecording() {
            console.log('Starting recording...');
            wsRetryCount = 0;
            isRecording = true;
            finalTranscript = ''; 
            elements.transcriptionOutput.innerHTML = '';
        
            if (recognition) {
                try {
                    recognition.start();
                    console.log('Recognition started successfully');
                } catch (error) {
                    console.error('Error starting recognition:', error);
                    if (error.name === 'InvalidStateError') {
                        recognition.stop();
                        setTimeout(() => recognition.start(), 50);
                    }
                }
            }
        
            navigator.mediaDevices.getUserMedia({
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true,
                    sampleRate: 44100,  
                    channelCount: 1
                }
            })
            .then(stream => {
                try {
                    const mediaRecorderOptions = {
                        mimeType: 'audio/webm;codecs=opus',
                        bitsPerSecond: 128000,
                        audioBitsPerSecond: 128000
                    }
        
                    mediaRecorder = new MediaRecorder(stream, mediaRecorderOptions);
                    console.log('MediaRecorder initialized with options:', mediaRecorderOptions);
        
                    let chunks = [];
                    mediaRecorder.ondataavailable = (e) => {
                        if (e.data.size > 0) {
                            chunks.push(e.data);
                            if (chunks.length >= 3) {  
                                const blob = new Blob(chunks, { type: mediaRecorderOptions.mimeType });
                                chunks = [];
                                sendAudioChunk(blob);
                            }
                        }
                    };
        
                    mediaRecorder.start(50);
                    this.mediaRecorder = mediaRecorder;
                    this.stream = stream;
        
                    elements.startButton.disabled = true;
                    elements.stopButton.disabled = false;
        
                    socket = setupWebSocket();
                }
                 catch (error) {
                    console.error('MediaRecorder initialization error:', error);
                    elements.transcriptionOutput.textContent = 'Error initializing recording: ' + error.message;
                }
            })
            .catch(error => {
                console.error('Error accessing microphone:', error);
                elements.transcriptionOutput.textContent = 'Error accessing microphone: ' + error.message;
                elements.startButton.disabled = false;
                elements.stopButton.disabled = true;
            });
        
            startTranscriptionUpdates();
        }

        function stopRecording() {
            console.log('Stopping recording...');
            isRecording = false;
        
            updateTranscriptionDisplay();

            if (recognition) {
                recognition.stop();
            }
            if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
                this.mediaRecorder.stop();
            }
            if (this.stream) {
                this.stream.getTracks().forEach(track => track.stop());
            }

            if (socket && socket.readyState === WebSocket.OPEN) {
                socket.close();
            }            
            
            elements.startButton.disabled = false;
            elements.stopButton.disabled = true;

        }

        function startTranscriptionUpdates() {
            function update() {
                const now = Date.now();
                if (now - lastUpdateTime >= UPDATE_INTERVAL) {
                    updateTranscriptionDisplay();
                    lastUpdateTime = now;
                }
                if (isRecording) {
                    requestAnimationFrame(update);
                }
            }
            requestAnimationFrame(update);
        }        

        function clearTranscription() {
            finalTranscript = ''; 
            elements.transcriptionOutput.innerHTML = 'Waiting to start...';
        }
        function debounce(func, wait) {
            let timeout;
            return function executedFunction(...args) {
                const later = () => {
                    clearTimeout(timeout);
                    func(...args);
                };
                clearTimeout(timeout);
                timeout = setTimeout(later, wait);
            };
        }
        
        // Add new function for real-time insights
        const generateRealTimeInsights = debounce((transcription) => {
            // Remove the company reference that was here
            if (!transcription || 
                transcription === 'Waiting to start...' || 
                transcription === 'Listening...' ||
                transcription === 'Connected to transcription service...') {
                return;
            }
        
            elements.insightsOutput.innerHTML = 'Generating insights...';
        
            const csrftoken = getCSRFToken();
            if (!csrftoken) {
                console.error('CSRF token not found');
                elements.insightsOutput.innerHTML = 'Error: CSRF token not found. Please refresh the page.';
                return;
            }
        
            fetch('/generate_insights/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrftoken,
                    'Accept': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify({
                    transcription: transcription
                }),
                credentials: 'include'
            })
            .then(async response => {
                if (!response.ok) {
                    const text = await response.text();
                    console.error('Server response:', text);
                    throw new Error('Server returned an error. Please try again.');
                }
                return response.json();
            })
            .then(data => {
                if (!data || !data.insights) {
                    throw new Error('Invalid response format');
                }
                elements.insightsOutput.innerHTML = data.insights;
            })
            .catch(error => {
                console.error('Error generating insights:', error);
                elements.insightsOutput.innerHTML = `Error generating insights: ${error.message}`;
            });
        }, 2000);
        
        // Add all event listeners
        function initializeEventListeners() {
            elements.startButton.addEventListener('click', startRecording);
            elements.stopButton.addEventListener('click', stopRecording);
            elements.clearButton.addEventListener('click', clearTranscription);
            elements.copyButton.addEventListener('click', copyTranscription);
        }
        // Initialize everything
        initializeSpeechRecognition();
        initializeEventListeners();    

    });
} catch (error) {
    console.error('Critical error during setup:', error);
}