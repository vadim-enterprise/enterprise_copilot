// Global variables
let recognition;
let isRecording = false;
let socket;
let mediaRecorder;
let wsRetryCount = 0;
let transcriptionBuffer = '';
let lastUpdateTime = Date.now();
let finalTranscript = '';
let chunkCount = 0;

const CONFIG = {
    MAX_RETRIES: 3,
    CHUNKS_BEFORE_INSIGHTS: 1,  // Number of audio chunks before generating insights
    MIN_TRANSCRIPT_LENGTH: 10,   // Minimum characters before generating insights
    UPDATE_INTERVAL: 100,        // Update interval for transcription display (ms)
    DEBOUNCE_DELAY: 0,        // Delay before generating insights (ms)
    MAX_CONTENT_LENGTH: 120,
    EMAIL_UPDATE_INTERVAL: 3, 
};

// DOM Elements
const elements = {
    startButton: document.getElementById('start-recording'),
    stopButton: document.getElementById('stop-recording'),
    transcriptionOutput: document.getElementById('transcription-output'),
    summaryOutput: document.getElementById('summary-output'),
    insightsOutput: document.getElementById('insights-output'),
    resetButton: document.getElementById('reset-conversation'),
    emailOutput: document.getElementById('email-output'),
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
        
            // try {
            recognition = new webkitSpeechRecognition();
            recognition.continuous = true;
            recognition.interimResults = true;
            recognition.lang = 'en-US';
    
            recognition.onstart = () => {
                console.log('Speech recognition started');
                isRecording = true;
                elements.startButton.disabled = true;
                elements.stopButton.disabled = false;
                chunkCount = 0;
            };
    
            recognition.onresult = (event) => {
                if (elements.transcriptionOutput.innerHTML === 'Listening...') {
                    elements.transcriptionOutput.innerHTML = '';
                }
            
                let interimTranscript = '';
                let currentFinalTranscript = '';
            
                for (let i = event.resultIndex; i < event.results.length; i++) {
                    const result = event.results[i];
                    if (result.isFinal) {
                        currentFinalTranscript += result[0].transcript + ' ';
                        console.log('Final transcript:', result[0].transcript);
                        chunkCount++;  // Increment chunk counter
                        console.log(`Chunk count: ${chunkCount}/${CONFIG.CHUNKS_BEFORE_INSIGHTS}`);
                    } else {
                        interimTranscript += result[0].transcript;
                        console.log('Interim transcript:', result[0].transcript);
                    }
                }
            
                if (currentFinalTranscript) {
                    finalTranscript += currentFinalTranscript;
                }
            
                elements.transcriptionOutput.innerHTML = 
                    finalTranscript + 
                    '<span style="color: #666;">' + interimTranscript + '</span>';
            
                // Generate insights based on chunk count and minimum length
                if (chunkCount >= CONFIG.CHUNKS_BEFORE_INSIGHTS && 
                    finalTranscript.length >= CONFIG.MIN_TRANSCRIPT_LENGTH) {
                    console.log('Generating email update...'); // Debug log
                    generateRealTimeInsights(finalTranscript);

                    // Generate email every EMAIL_UPDATE_INTERVAL chunks
                    if (chunkCount % CONFIG.EMAIL_UPDATE_INTERVAL === 0) {
                        generateEmail(finalTranscript);
                    }

                    chunkCount = 0;  // Reset counter after generating insights
                }
            
                elements.transcriptionOutput.scrollTop = elements.transcriptionOutput.scrollHeight;
            };
            
            recognition.onend = () => {
                console.log('Speech recognition ended');
                if (isRecording) {
                    console.log('Restarting recognition');
                    recognition.start();
                } else {
                    elements.startButton.disabled = false;
                    elements.stopButton.disabled = true;
                }
            };
    
            return recognition;
            // } catch (error) {
            //     console.error('Error initializing speech recognition:', error);
            //     elements.transcriptionOutput.textContent = 'Error initializing speech recognition';
            //     return null;
            // }
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
            if (wsRetryCount >= CONFIG.MAX_RETRIES) {
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
                        console.log(`Retrying WebSocket connection (${wsRetryCount}/${CONFIG.MAX_RETRIES})`);
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
        
            // Reset counters and transcripts
            chunkCount = 0;
            finalTranscript = '';
            transcriptionBuffer = '';
        
            // Reset UI
            elements.summaryOutput.innerHTML = 'Waiting for conversation...';
            elements.insightsOutput.innerHTML = 'Waiting for conversation...';
            elements.transcriptionOutput.innerHTML = 'Waiting to start...';
            elements.emailOutput.innerHTML = 'Waiting for conversation...';
        
            if (elements.stopButton && !elements.stopButton.disabled) {
                elements.stopButton.click();
            }

            if (isRecording) {
                stopRecording();
            }
            
            elements.startButton.disabled = false;
            elements.stopButton.disabled = true;
        
            // Call backend to reset conversation
            fetch('/reset-conversation/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCSRFToken(),
                    'Accept': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                credentials: 'include'
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                console.log('Conversation reset successfully:', data);
            })
            .catch(error => {
                console.error('Error resetting conversation:', error);
            });
        }

        function startTranscriptionUpdates() {
            function update() {
                const now = Date.now();
                if (now - lastUpdateTime >= CONFIG.UPDATE_INTERVAL) {
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

        function updateContentBox(element, newContent, contentType) {
            // Get existing content
            const existingContent = element.innerHTML;
            
            // Skip if it's the initial waiting message
            if (existingContent === `Waiting for conversation...` || 
                existingContent === `Generating ${contentType.toLowerCase()}...`) {
                element.innerHTML = `<div class="content-item newest">${newContent}</div>`;
                return;
            }
        
            // Create new content element
            const newContentHtml = `<div class="content-item newest">${newContent}</div>`;
            
            // Update existing content classes (shift opacity)
            const updatedExisting = existingContent
                .replace(/newest/g, 'recent')
                .replace(/recent/g, 'old');
            
            // Combine new and existing content
            let combinedContent = newContentHtml + updatedExisting;
            
            // Get all content items
            const tempDiv = document.createElement('div');
            tempDiv.innerHTML = combinedContent;
            const contentItems = Array.from(tempDiv.getElementsByClassName('content-item'));
            
            // Trim content if it exceeds max length
            let totalLength = 0;
            let trimmedContent = '';
            
            for (let item of contentItems) {
                const itemLength = item.textContent.length;
                if (totalLength + itemLength <= CONFIG.MAX_CONTENT_LENGTH) {
                    trimmedContent += item.outerHTML;
                    totalLength += itemLength;
                } else {
                    // If this is the first item and it's already too long, trim it
                    if (totalLength === 0) {
                        item.textContent = item.textContent.substring(0, CONFIG.MAX_CONTENT_LENGTH);
                        trimmedContent = item.outerHTML;
                    }
                    break;
                }
            }
            
            // Update the element
            element.innerHTML = trimmedContent;
        }
        
        const generateRealTimeInsights = debounce((transcription) => {
            if (!transcription || 
                transcription.length < CONFIG.MIN_TRANSCRIPT_LENGTH || 
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

            // Log the request details for debugging
            console.log('Sending request to generate insights:', {
                url: '/generate-insights/',
                transcription: transcription.substring(0, 100) + '...',
                chunkSize: CONFIG.CHUNKS_BEFORE_INSIGHTS
            });            
        
            fetch('/generate-insights/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrftoken,
                    'Accept': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify({
                    transcription: transcription,
                    chunkSize: CONFIG.CHUNKS_BEFORE_INSIGHTS  // Send chunk size to backend
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
        
                // if (typeof data.summary === 'string') {
                //     elements.summaryOutput.innerHTML = data.summary;
                // } else {
                //     elements.summaryOutput.innerHTML = 'No summary available';
                // }
                
                // if (typeof data.insights === 'string') {
                //     elements.insightsOutput.innerHTML = data.insights;
                // } else {
                //     elements.insightsOutput.innerHTML = 'No insights available';
                // }
                // Update summary with new text in bold
                if (typeof data.summary === 'string') {
                    updateContentBox(elements.summaryOutput, data.summary, 'Summary');
                }
                
                // Update insights with new text
                if (typeof data.insights === 'string') {
                    updateContentBox(elements.insightsOutput, data.insights, 'Insights');
                }

                console.log('Successfully updated UI with insights and summary');
            })
            .catch(error => {
                console.error('Error generating insights:', error);
                elements.summaryOutput.innerHTML = `Error: ${error.message}`;
                elements.insightsOutput.innerHTML = `Error: ${error.message}`;
            });
        }, CONFIG.DEBOUNCE_DELAY);

        function generateEmail(transcription) {
            console.log('generateEmail called with transcription length:', transcription.length); // Debug log
            
            if (!transcription || 
                transcription.length < CONFIG.MIN_TRANSCRIPT_LENGTH || 
                transcription === 'Waiting to start...') {
                console.log('Email generation skipped - invalid transcription'); // Debug log
                return;
            }
        
            console.log('Generating email...'); // Debug log
            elements.emailOutput.innerHTML = 'Generating email...';
            
            const csrftoken = getCSRFToken();
            
            fetch('/generate-email/', {
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
            .then(response => {
                console.log('Email generation response received'); // Debug log
                return response.json();
            })
            .then(data => {
                if (data.error) {
                    throw new Error(data.error);
                }
        
                console.log('Email data received:', data); // Debug log
        
                const emailContent = `
                    <div class="email-field">
                        <span class="email-label">To:</span>
                        <span class="email-value">${data.email_data.to}</span>
                    </div>
                    <div class="email-field">
                        <span class="email-label">Subject:</span>
                        <span class="email-value">${data.email_data.subject}</span>
                    </div>
                    <div class="email-body">${data.email_data.body}</div>
                `;
        
                updateContentBox(elements.emailOutput, emailContent, 'Email');
                console.log('Email content updated'); // Debug log
            })
            .catch(error => {
                console.error('Error generating email:', error);
                elements.emailOutput.innerHTML = `Error: ${error.message}`;
            });
        }
        
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