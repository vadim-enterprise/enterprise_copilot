// Global variables
let recognition;
let isRecording = false;
let socket;
let mediaRecorder;
let wsRetryCount = 0;
const MAX_RETRIES = 3;
let transcriptionBuffer = '';
let lastUpdateTime = Date.now();
const UPDATE_INTERVAL = 100; // Update every 100ms
let finalTranscript = '';

// DOM Elements
const elements = {
    startButton: document.getElementById('start-recording'),
    stopButton: document.getElementById('stop-recording'),
    transcriptionOutput: document.getElementById('transcription-output'),
    summaryOutput: document.getElementById('summary-output'),
    insightsOutput: document.getElementById('insights-output'),
    resetButton: document.getElementById('reset-conversation')
};

try {
    document.addEventListener('DOMContentLoaded', (event) => {
        // Validate required elements
        Object.entries(elements).forEach(([name, element]) => {
            if (!element) {
                throw new Error(`Required element ${name} not found`);
            }
        });

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
                
                elements.transcriptionOutput.innerText = (currentText + transcriptionBuffer).trim();
                transcriptionBuffer = '';
                elements.transcriptionOutput.scrollTop = elements.transcriptionOutput.scrollHeight;
            }
        }
        
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
                            
                            let currentText = elements.transcriptionOutput.innerText;
                            if (currentText === 'Listening...' || 
                                currentText === 'Waiting to start...' ||
                                currentText === 'Connected to transcription service...') {
                                currentText = '';
                            }
                            elements.transcriptionOutput.innerText = (currentText + ' ' + data.text).trim();
                            elements.transcriptionOutput.scrollTop = elements.transcriptionOutput.scrollHeight;
                        }
                    } catch (error) {
                        console.error('Error processing WebSocket message:', error);
                    }
                };
        
                socket.onerror = function(error) {
                    console.error('WebSocket error:', error);
                };
        
                socket.onclose = function(e) {
                    console.log('WebSocket connection closed');
                    if (isRecording) {
                        wsRetryCount++;
                        console.log(`Retrying WebSocket connection (${wsRetryCount}/${MAX_RETRIES})`);
                        setupWebSocket();
                    }
                };
        
                return socket;
            } catch (error) {
                console.error('Error setting up WebSocket:', error);
                return null;
            }
        }

        function startRecording() {
            elements.transcriptionOutput.textContent = 'Connecting to transcription service...';
            
            navigator.mediaDevices.getUserMedia({ audio: true })
            .then(stream => {
                this.stream = stream;
                this.mediaRecorder = new MediaRecorder(stream);
                
                setupWebSocket();
                initializeSpeechRecognition();
                
                if (recognition) {
                    try {
                        recognition.start();
                        elements.transcriptionOutput.textContent = 'Listening...';
                    } catch (error) {
                        console.error('Error starting recognition:', error);
                        elements.transcriptionOutput.textContent = 'Error starting recognition: ' + error.message;
                    }
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

        function resetConversation() {
            if (!confirm('Are you sure you want to reset the conversation? This will clear all current data.')) {
                return;
            }
        
            elements.summaryOutput.innerHTML = '';
            elements.insightsOutput.innerHTML = '';
            elements.transcriptionOutput.innerHTML = 'Waiting to start...';
        
            if (elements.stopButton && !elements.stopButton.disabled) {
                elements.stopButton.click();
            }
            
            elements.startButton.disabled = false;
            elements.stopButton.disabled = true;
            
            finalTranscript = '';
            transcriptionBuffer = '';
        
            fetch('/reset_conversation/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCSRFToken(),
                },
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error('Failed to reset conversation history');
                }
                console.log('Conversation history reset successfully');
            })
            .catch(error => {
                console.error('Error resetting conversation:', error);
                alert('Error resetting conversation. Please try again.');
            });
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
        
        const generateRealTimeInsights = debounce((transcription) => {
            if (!transcription || 
                transcription === 'Waiting to start...' || 
                transcription === 'Listening...' ||
                transcription === 'Connected to transcription service...') {
                return;
            }
        
            elements.summaryOutput.innerHTML = 'Generating summary...';
            elements.insightsOutput.innerHTML = 'Generating insights...';
        
            const csrftoken = getCSRFToken();
            if (!csrftoken) {
                console.error('CSRF token not found');
                elements.summaryOutput.innerHTML = 'Error: CSRF token not found. Please refresh the page.';
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
                console.log('Parsed response data:', data);
        
                if (!data) {
                    throw new Error('Empty response from server');
                }
        
                if (data.error) {
                    throw new Error(data.error);
                }
        
                if (typeof data.summary === 'string') {
                    elements.summaryOutput.innerHTML = data.summary;
                } else {
                    elements.summaryOutput.innerHTML = 'No summary available';
                }
                
                if (typeof data.insights === 'string') {
                    elements.insightsOutput.innerHTML = data.insights;
                } else {
                    elements.insightsOutput.innerHTML = 'No insights available';
                }
        
                console.log('Successfully updated UI with insights and summary');
            })
            .catch(error => {
                console.error('Error generating insights:', error);
                elements.summaryOutput.innerHTML = `Error: ${error.message}`;
                elements.insightsOutput.innerHTML = `Error: ${error.message}`;
            });
        }, 2000);
        
        // Initialize everything
        initializeSpeechRecognition();
        
        // Add event listeners
        elements.startButton.addEventListener('click', startRecording);
        elements.stopButton.addEventListener('click', stopRecording);
        elements.resetButton.addEventListener('click', resetConversation);
    });
} catch (error) {
    console.error('Critical error during setup:', error);
}