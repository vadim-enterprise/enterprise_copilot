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
let currentPage = 1;
const itemsPerPage = 10;
let knowledgeBaseItems = [];

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
    enrichButton: document.getElementById('enrich-knowledge'),
    inspectButton: document.getElementById('inspect-knowledge'),
    knowledgeBaseContent: document.getElementById('knowledge-base-content'),
    ragSearchInput: document.getElementById('rag-search-input'),
    ragSearchButton: document.getElementById('rag-search-button'),
    clearButton: document.getElementById('clear-knowledge'),
};

function changePage(pageName) {
    // Hide all content sections
    const sections = document.querySelectorAll('.content-section');
    sections.forEach(section => {
        section.style.display = 'none';
    });
    
    // Show the selected section
    const selectedSection = document.getElementById(`${pageName}-section`);
    if (selectedSection) {
        selectedSection.style.display = 'block';
    }
    
    // Update active state of navigation buttons
    const navButtons = document.querySelectorAll('.nav-button');
    navButtons.forEach(button => {
        button.classList.remove('active');
        if (button.getAttribute('onclick').includes(pageName)) {
            button.classList.add('active');
        }
    });
}

function showNotification(message, type = 'info') {
    // Create notification container if it doesn't exist
    let container = document.getElementById('notification-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'notification-container';
        document.body.appendChild(container);
    }
    
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    
    // Add to container
    container.appendChild(notification);
    
    // Remove after delay
    setTimeout(() => {
        notification.classList.add('fade-out');
        setTimeout(() => {
            notification.remove();
            if (container.children.length === 0) {
                container.remove();
            }
        }, 300);
    }, 3000);
}

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

try {
    document.addEventListener('DOMContentLoaded', (event) => {
        // Debug log to check if script is running
        console.log('Script loaded, checking for enrich button...');
        
        const enrichButton = document.getElementById('enrich-knowledge');
        if (!enrichButton) {
            console.error('Enrich knowledge button not found!');
            return;
        }
        console.log('Enrich button found, attaching event listener...');

        // Enrich knowledge base handler
        function enrichKnowledgeBase() {
            console.log('Enrich button clicked!'); // Debug log
            const button = document.getElementById('enrich-knowledge');
            
            try {
                // Show loading state
                button.disabled = true;
                button.textContent = 'Enriching...';
                console.log('Making fetch request to enrich knowledge base...'); // Debug log
                
                fetch('/enrich-knowledge-base/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCSRFToken()
                    },
                    body: JSON.stringify({})
                })
                .then(response => {
                    console.log('Received response:', response); // Debug log
                    if (!response.ok) {
                        throw new Error(`Server error: ${response.status}`);
                    }
                    return response.json();
                })
                .then(data => {
                    console.log('Received data:', data); // Debug log
                    if (data.status === 'success') {
                        showNotification(data.message, 'success');
                    } else {
                        showNotification(`Error: ${data.message}`, 'error');
                    }
                })
                .catch(error => {
                    console.error('Error enriching knowledge base:', error);
                    showNotification('Failed to enrich knowledge base', 'error');
                })
                .finally(() => {
                    // Reset button state
                    button.disabled = false;
                    button.textContent = 'Enrich';
                });
                
            } catch (error) {
                console.error('Error in enrichKnowledgeBase:', error);
                button.disabled = false;
                button.textContent = 'Enrich';
                showNotification('Failed to enrich knowledge base', 'error');
            }
        }

        // Remove any existing listeners first
        enrichButton.replaceWith(enrichButton.cloneNode(true));
        
        // Get the fresh reference after replacing
        const newEnrichButton = document.getElementById('enrich-knowledge');
        
        // Add the event listener
        newEnrichButton.addEventListener('click', enrichKnowledgeBase);
        console.log('Event listener attached to enrich button');

        // Validate required elements
        Object.entries(elements).forEach(([name, element]) => {
            if (!element) {
                throw new Error(`Required element ${name} not found`);
            }
        });

        function getCSRFToken() {
            const name = 'csrftoken';
            let cookieValue = null;
            
            if (document.cookie && document.cookie !== '') {
                const cookies = document.cookie.split(';');
                for (let i = 0; i < cookies.length; i++) {
                    const cookie = cookies[i].trim();
                    if (cookie.substring(0, name.length + 1) === (name + '=')) {
                        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                        break;
                    }
                }
            }
            
            if (!cookieValue) {
                // Try to get from meta tag if cookie not found
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
            const protocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
            const wsUrl = `${protocol}${window.location.hostname}/ws/transcribe/`;
            
            socket = new WebSocket(wsUrl);

            // Set up WebSocket handlers when socket is created
            socket.onmessage = function(e) {
                const data = JSON.parse(e.data);
                
                // Handle transcription data
                if (data.message) {
                    let currentText = elements.transcriptionOutput.innerText;
                    if (currentText === 'Listening...' || 
                        currentText === 'Waiting to start...' ||
                        currentText === 'Connected to transcription service...') {
                        currentText = '';
                    }
                    elements.transcriptionOutput.innerText = (currentText + ' ' + data.message).trim();
                    
                    // Generate email when enough content is available
                    if (chunkCount >= CONFIG.EMAIL_UPDATE_INTERVAL) {
                        generateEmail(elements.transcriptionOutput.innerText);
                        chunkCount = 0;  // Reset counter
                    }
                }

                // Handle enhanced response from HybridRAG
                if (data.enhanced_response) {
                    updateContentBox(elements.insightsOutput, data.enhanced_response, 'Insights');
                    
                    let summaryContent = `Confidence: ${(data.confidence * 100).toFixed(1)}%`;
                    if (data.sources) {
                        summaryContent += `\nSources: ${data.sources.join(', ')}`;
                    }
                    updateContentBox(elements.summaryOutput, summaryContent, 'Summary');
                }
            };
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

            // Add console logging for debugging
            console.log(`Updating ${contentType} box:`, {
                existingContent,
                newContent
            });
            
            // Skip if it's the initial waiting message
            if (existingContent.includes('Waiting for conversation') || 
            existingContent.includes(`Generating ${contentType.toLowerCase()}...`)) {
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
            if (!transcription) return;
            
            const emailOutput = document.getElementById('email-output');
            emailOutput.innerHTML = '<div class="generating-email">Generating email...</div>';
            
            fetch('/generate-send-email/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCSRFToken(),
                },
                body: JSON.stringify({ transcription: transcription })
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    throw new Error(data.error);
                }
                
                // Update email display
                if (data.email_data) {
                    emailOutput.innerHTML = `
                        <div class="email-header">
                            <div class="email-field">
                                <span class="email-label">To:</span>
                                <span class="email-value">${data.email_data.to}</span>
                            </div>
                            <div class="email-field">
                                <span class="email-label">Subject:</span>
                                <span class="email-value">${data.email_data.subject}</span>
                            </div>
                        </div>
                        <div class="email-content">
                            ${data.email_data.body.replace(/\n/g, '<br>')}
                        </div>
                    `;
                }
            })
            .catch(error => {
                console.error('Email generation error:', error);
                emailOutput.innerHTML = `<div class="error">Error generating email: ${error.message}</div>`;
            });
        }
        
        // Initialize everything
        initializeSpeechRecognition();
        
        // Add event listeners
        elements.startButton.addEventListener('click', startRecording);
        elements.stopButton.addEventListener('click', stopRecording);
        elements.resetButton.addEventListener('click', resetConversation);



        // Remove any duplicate event listeners first
        document.getElementById('enrich-knowledge')?.removeEventListener('click', enrichKnowledgeBase);

        // Add single event listener
        document.getElementById('enrich-knowledge').addEventListener('click', enrichKnowledgeBase);

        // Remove any conflicting anonymous function listeners
        document.getElementById('enrich-knowledge').removeEventListener('click', async function() {
            // ... any existing anonymous function
        });

        function displayKnowledgeBasePage(page) {
            const startIndex = (page - 1) * itemsPerPage;
            const endIndex = startIndex + itemsPerPage;
            const pageItems = knowledgeBaseItems.slice(startIndex, endIndex);
            
            const content = elements.knowledgeBaseContent.querySelector('.content');
            
            // Clear existing content
            content.innerHTML = '';
            
            // Add total count
            elements.knowledgeBaseContent.insertAdjacentHTML('beforeend', 
                `<div class="total-count">Total Documents: ${knowledgeBaseItems.length}</div>`);
            
            // Add content - simplified version without metadata
            content.innerHTML = pageItems.map(item => {
                const safeItem = item || {};
                return `
                    <div class="knowledge-item">
                        <div class="content-preview">
                            ${safeItem.content_preview || 'No content preview available'}
                        </div>
                    </div>
                `;
            }).join('');
            
            // Add pagination
            const totalPages = Math.ceil(knowledgeBaseItems.length / itemsPerPage);
            
            let paginationDiv = elements.knowledgeBaseContent.querySelector('.pagination');
            if (!paginationDiv) {
                paginationDiv = document.createElement('div');
                paginationDiv.className = 'pagination';
                elements.knowledgeBaseContent.appendChild(paginationDiv);
            }
            
            paginationDiv.innerHTML = `
                <button onclick="displayKnowledgeBasePage(${page - 1})" 
                        ${page <= 1 ? 'disabled' : ''}>Previous</button>
                <span>Page ${page} of ${totalPages}</span>
                <button onclick="displayKnowledgeBasePage(${page + 1})"
                        ${page >= totalPages ? 'disabled' : ''}>Next</button>
            `;
            
            currentPage = page;
        }

        function inspectKnowledgeBase() {
            const container = document.querySelector('#knowledge-base-content .content');
            if (!container) {
                console.error('Container not found');
                return;
            }
            
            // Show loading state
            container.innerHTML = '<div class="loading">Loading knowledge base content...</div>';
            
            fetch('/predict_best_option/inspect-knowledge-base/')
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`Server error: ${response.status}`);
                    }
                    return response.json();
                })
                .then(data => {
                    if (!data) {
                        throw new Error('No data received');
                    }
                    
                    if (data.status === 'error') {
                        throw new Error(data.error || 'Unknown error occurred');
                    }
                    
                    displayKnowledgeBaseContent(data);
                })
                .catch(error => {
                    console.error('Error loading knowledge base:', error);
                    if (error.message.includes('Failed to fetch')) {
                        container.innerHTML = '<div class="error">Server not responding. Please check if Django server is running.</div>';
                    } else {
                        container.innerHTML = `<div class="error">Failed to load knowledge base: ${error.message}</div>`;
                    }
                });
        }

        // Add event listener
        document.getElementById('inspect-knowledge').addEventListener('click', inspectKnowledgeBase);

        async function performSearch() {
            const searchButton = document.getElementById('rag-search-button');
            const searchInput = document.getElementById('rag-search-input');
            const searchResultsDiv = document.getElementById('search-results');
            
            if (!searchInput ) {
                console.error('searchInput not found');
                return;
            }

            if (!searchResultsDiv) {
                console.error('searchResultsDiv not found');
                return;
            }

            const query = searchInput.value.trim();
            
            try {
                // Change button text to "Searching..."
                searchButton.textContent = 'Searching...';
                searchButton.disabled = true;  // Disable button while searching

                const response = await fetch('/search-knowledge/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken')
                    },
                    body: JSON.stringify({ query: query })
                });

                const data = await response.json();
                searchResultsDiv.innerHTML = ''; // Clear previous results

                if (data.status === 'success' && data.results && data.results.length > 0) {
                    data.results.forEach(result => {
                        const resultDiv = document.createElement('div');
                        resultDiv.className = 'search-result';
                        
                        const escapedResult = {
                            title: result.title,
                            url: result.url,
                            summary: result.summary,
                            timestamp: result.timestamp || new Date().toISOString(),
                            similarity_score: result.similarity_score
                        };
                        
                        const similarityScore = result.similarity_score ? 
                            `<div class="similarity-score">Relevance Score: ${(result.similarity_score * 100).toFixed(1)}%</div>` : '';
                        
                        resultDiv.innerHTML = `
                            <h3><a href="${result.url}" target="_blank" rel="noopener noreferrer">${result.title}</a></h3>
                            <p>${result.summary}</p>
                            ${similarityScore}
                            <div class="result-actions">
                                <button class="btn btn-primary btn-sm add-to-kb" 
                                        onclick='addToKnowledgeBase(${JSON.stringify(escapedResult).replace(/'/g, "&apos;")}, this)'>
                                    Add to Knowledge Base
                                </button>
                            </div>
                        `;
                        
                        searchResultsDiv.appendChild(resultDiv);
                    });
                } else {
                    searchResultsDiv.innerHTML = '<p>No results found</p>';
                }
            } catch (error) {
                console.error('Search error:', error);
                searchResultsDiv.innerHTML = '<p>Error performing search</p>';
            } finally {
                // Reset button state regardless of success or failure
                searchButton.textContent = 'Search';
                searchButton.disabled = false;
            }
        }

        // Add event listeners
        elements.ragSearchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                performSearch(e.target.value);
            }
        });

        elements.ragSearchButton.addEventListener('click', () => {
            performSearch(elements.ragSearchInput.value);
        });

        // Call this when the page loads to show the default section
        document.addEventListener('DOMContentLoaded', () => {
            changePage('home');  // or whatever your default page is
        });

        // Make sure these functions are globally accessible
        window.displayKnowledgeBasePage = displayKnowledgeBasePage;
        window.inspectKnowledgeBase = inspectKnowledgeBase;

        // Add the clear knowledge base function
        async function clearKnowledgeBase() {
            try {
                // Show confirmation dialog
                if (!confirm('Are you sure you want to clear the knowledge base? This action cannot be undone.')) {
                    return;
                }

                // Disable button and show loading state
                elements.clearButton.disabled = true;
                elements.clearButton.textContent = 'Clearing...';

                const response = await fetch('/clear-knowledge-base/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCSRFToken(),
                        'Accept': 'application/json'
                    },
                    credentials: 'same-origin'
                });

                if (!response.ok) {
                    throw new Error(`Server error: ${response.status}`);
                }

                const data = await response.json();
                
                if (data.status === 'success') {
                    showNotification('Knowledge base cleared successfully', 'success');
                    // Refresh the knowledge base display
                    inspectKnowledgeBase();
                } else {
                    showNotification(`Error: ${data.error}`, 'error');
                }

            } catch (error) {
                console.error('Error:', error);
                showNotification(`Error: ${error.message}`, 'error');
            } finally {
                // Reset button state
                elements.clearButton.disabled = false;
                elements.clearButton.textContent = 'Clear';
            }
        }

        // Add event listener
        elements.clearButton.addEventListener('click', clearKnowledgeBase);

        function displayKnowledgeBaseContent(data) {
            const container = document.querySelector('#knowledge-base-content .content');
            if (!container) return;
            
            // Handle error state
            if (data.error) {
                container.innerHTML = `<div class="error">Error: ${data.error}</div>`;
                return;
            }
            
            // Handle empty state
            if (!data.documents || data.documents.length === 0) {
                container.innerHTML = '<div class="empty">Knowledge base is empty. Click "Enrich" to add content.</div>';
                return;
            }
            
            // Display documents
            let html = '<div class="documents">';
            data.documents.forEach(doc => {
                if (!doc) return; // Skip invalid documents
                
                html += `
                    <div class="document">
                        <div class="document-content">${formatDocumentContent(doc.content || '')}</div>
                        <div class="document-metadata">
                            <span class="timestamp">${doc.metadata?.timestamp || 'Unknown date'}</span>
                            ${doc.metadata?.source ? `<span class="source">Source: ${doc.metadata.source}</span>` : ''}
                            ${doc.metadata?.type ? `<span class="type">Type: ${doc.metadata.type}</span>` : ''}
                        </div>
                    </div>
                `;
            });
            html += '</div>';
            
            container.innerHTML = html;
        }

        function formatDocumentContent(content) {
            // Format the content for display
            if (typeof content !== 'string') return 'Invalid content';
            
            // Replace newlines with <br> tags
            content = content.replace(/\n/g, '<br>');
            
            // Highlight sections
            content = content.replace(/Title:/g, '<strong>Title:</strong>');
            content = content.replace(/Source URL:/g, '<strong>Source URL:</strong>');
            content = content.replace(/Original Summary:/g, '<strong>Original Summary:</strong>');
            content = content.replace(/Enhanced Analysis:/g, '<strong>Enhanced Analysis:</strong>');
            content = content.replace(/Search Query:/g, '<strong>Search Query:</strong>');
            
            return content;
        }

        // Knowledge base inspection handler
        document.getElementById('inspect-knowledge').addEventListener('click', function() {
            const container = document.querySelector('#knowledge-base-content .content');
            if (!container) {
                console.error('Container not found');
                return;
            }
            
            // Show loading state
            container.innerHTML = '<div class="loading">Loading knowledge base content...</div>';
            
            fetch('/inspect-knowledge-base/')
                .then(response => {
                    console.log('Raw response:', response);
                    return response.json();
                })
                .then(data => {
                    console.log('Received data:', data);  // Log the received data
                    
                    // Handle error response
                    if (!data) {
                        console.error('No data received');
                        container.innerHTML = '<div class="error">No data received from server</div>';
                        return;
                    }

                    if (data.status === 'error') {
                        console.error('Error status received:', data.error);
                        container.innerHTML = `<div class="error">Error: ${data.error || 'Unknown error occurred'}</div>`;
                        return;
                    }
                    
                    // Ensure documents exists
                    if (!data.documents) {
                        console.error('No documents array in response');
                        container.innerHTML = '<div class="error">Invalid response format</div>';
                        return;
                    }
                    
                    // Handle empty knowledge base
                    if (data.documents.length === 0) {
                        console.log('Empty documents array');
                        container.innerHTML = '<div class="empty">Knowledge base is empty. Click "Enrich" to add content.</div>';
                        return;
                    }
                    
                    // Build content HTML
                    let html = '<div class="documents">';
                    data.documents.forEach((doc, index) => {
                        console.log(`Processing document ${index}:`, doc);  // Log each document
                        
                        if (!doc) {
                            console.warn(`Skipping invalid document at index ${index}`);
                            return;
                        }
                        
                        const content = doc.content || '';
                        const metadata = doc.metadata || {};
                        
                        html += `
                            <div class="document">
                                <div class="document-content">
                                    ${formatDocumentContent(content)}
                                </div>
                                <div class="document-metadata">
                                    ${metadata.timestamp ? `<span class="timestamp">${metadata.timestamp}</span>` : ''}
                                    ${metadata.source ? `<span class="source">Source: ${metadata.source}</span>` : ''}
                                    ${metadata.type ? `<span class="type">Type: ${metadata.type}</span>` : ''}
                                </div>
                            </div>
                        `;
                    });
                    html += '</div>';
                    
                    container.innerHTML = html;
                })
                .catch(error => {
                    console.error('Error loading knowledge base:', error);
                    container.innerHTML = `<div class="error">Failed to load knowledge base: ${error.message}</div>`;
                });
        });

        function formatDocumentContent(content) {
            if (!content) return '';
            
            // Sanitize content
            const sanitized = content
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/\n/g, '<br>');
            
            return sanitized;
        }

        // Helper function to show alerts
        function showAlert(type, message) {
            const alertDiv = document.createElement('div');
            alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
            alertDiv.role = 'alert';
            alertDiv.innerHTML = `
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            `;
            
            const container = document.querySelector('.container');
            container.insertBefore(alertDiv, container.firstChild);
            
            // Auto-dismiss after 5 seconds
            setTimeout(() => {
                alertDiv.remove();
            }, 5000);
        }

        // Find the function that's currently handling the search results display
        function displayWebSearchResults(results) {
            const searchResultsDiv = document.getElementById('searchResults');
            searchResultsDiv.innerHTML = '';
            
            if (!results || results.length === 0) {
                searchResultsDiv.innerHTML = '<p>No results found</p>';
                return;
            }
            
            results.forEach(result => {
                const resultDiv = document.createElement('div');
                resultDiv.className = 'search-result';
                
                // Escape the result data to safely use in JSON.stringify
                const escapedResult = {
                    title: result.title,
                    url: result.url,
                    summary: result.summary,
                    timestamp: result.timestamp || new Date().toISOString(),
                    similarity_score: result.similarity_score
                };
                
                const similarityScore = result.similarity_score ? 
                    `<div class="similarity-score">Relevance Score: ${(result.similarity_score * 100).toFixed(1)}%</div>` : '';
                
                resultDiv.innerHTML = `
                    <h3><a href="${result.url}" target="_blank" rel="noopener noreferrer">${result.title}</a></h3>
                    <p>${result.summary}</p>
                    ${similarityScore}
                    <div class="result-actions">
                        <button class="btn btn-primary btn-sm add-to-kb" 
                                onclick='addToKnowledgeBase(${JSON.stringify(escapedResult).replace(/'/g, "&apos;")}, this)'>
                            Add to Knowledge Base
                        </button>
                    </div>
                `;
                
                searchResultsDiv.appendChild(resultDiv);
            });
        }

        // Make sure this function is being called when search results are received
        async function performWebSearch() {
            const searchInput = document.getElementById('searchInput');
            const query = searchInput.value.trim();
            
            if (!query) {
                showAlert('warning', 'Please enter a search query');
                return;
            }
            
            try {
                const response = await fetch('/predict_best_option/search-knowledge/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken')
                    },
                    body: JSON.stringify({ query: query })
                });
                
                const data = await response.json();

                if (data.status === 'success') {
                    displayWebSearchResults(data.results);  // Use the new display function
                } else {
                    showAlert('error', data.message || 'Search failed');
                }
            } catch (error) {
                console.error('Search error:', error);
                showAlert('error', 'Failed to perform search');
            }
        }

        // Add event listener for search input
        document.addEventListener('DOMContentLoaded', function() {
            const searchInput = document.getElementById('searchInput');
            if (searchInput) {
                searchInput.addEventListener('keypress', function(e) {
                    if (e.key === 'Enter') {
                        performWebSearch();
                    }
                });
            }
            
            const searchButton = document.getElementById('searchButton');
            if (searchButton) {
                searchButton.addEventListener('click', performWebSearch);
            }
        });

        // Helper function to show alerts (if not already defined)
        function showAlert(type, message) {
            const alertDiv = document.createElement('div');
            alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
            alertDiv.role = 'alert';
            alertDiv.innerHTML = `
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            `;
            
            const container = document.querySelector('.container');
            container.insertBefore(alertDiv, container.firstChild);
            
            // Auto-dismiss after 5 seconds
            setTimeout(() => {
                alertDiv.remove();
            }, 5000);
        }

        // Add this function to handle adding to knowledge base
        window.addToKnowledgeBase = async function(result, button) {
            try {
                const response = await fetch('/add-website-to-knowledge-base/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken')
                    },
                    body: JSON.stringify({ result })
                });
                
                const data = await response.json();
                
                if (data.status === 'success') {
                    // Use the button parameter instead of event.target
                    button.disabled = true;
                    button.textContent = 'Added to KB';
                    button.classList.add('added');
                    showNotification('Successfully added to knowledge base', 'success');
                } else {
                    showNotification('Failed to add to knowledge base: ' + data.message, 'error');
                }
            } catch (error) {
                console.error('Error:', error);
                showNotification('Failed to add to knowledge base', 'error');
            }
        };
    });

} catch (error) {
    console.error('Critical error during setup:', error);
}