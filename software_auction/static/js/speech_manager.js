class SpeechManager {
    constructor() {
        this.pc = null;
        this.dc = null;
        this.audioEl = null;
        this.isInitialized = false;
        this.isDataChannelReady = false;
        this.baseUrl = "https://api.openai.com/v1/realtime";
        this.model = "gpt-4o-realtime-preview-2024-12-17";
        this.ragContext = null;
        this.lastQuery = null;
        this.conversationHistory = [];
        this.fastApiUrl = 'http://127.0.0.1:8001';

        // Store the knowledge base content
        this.knowledgeBaseContent = null;
        this.instructions = null;

        this.sessionConfig = {
            voice: "coral",
            input_audio_format: "pcm16",  
            output_audio_format: "pcm16", 
            turn_detection: {
                type: "server_vad",
                threshold: 0.5,
                prefix_padding_ms: 300,
                silence_duration_ms: 200,
                create_response: true
            },
            input_audio_transcription: {
                model: "whisper-1"
            },
            tool_choice: "auto",
            temperature: 0.6,
            max_response_output_tokens: "inf",
            tools: []
        };
    }

    setKnowledgeBase(content) {
        this.knowledgeBaseContent = content;
        console.log('Knowledge base content updated:', content.substring(0, 100) + '...');
        if (this.isInitialized) {
            console.log('Updating instructions for active session');
            this.updateInstructions();
            this.reinitializeSession();
        }
    }

    async reinitializeSession() {
        try {
            // Store current config except instructions
            const currentConfig = { ...this.sessionConfig };
            delete currentConfig.instructions;
            
            await this.cleanup();
            
            // Restore config except instructions
            this.sessionConfig = {
                ...currentConfig,
                instructions: this.sessionConfig.instructions
            };
            
            await this.initialize();
            console.log('Session reinitialized with new instructions');
        } catch (error) {
            console.error('Error reinitializing session:', error);
        }
    }

    updateInstructions() {
        if (this.knowledgeBaseContent) {
            console.log('Setting instructions with knowledge base content');
            this.sessionConfig.instructions = `
                ${this.knowledgeBaseContent}
            `.trim();
        } else {
            console.log('Using default instructions - no knowledge base content available');
            this.sessionConfig.instructions = "You are a helpful assistant. Be concise and accurate in your responses.";
        }
        console.log('Instructions updated:', this.sessionConfig.instructions.substring(0, 100) + '...');
    }

    async loadInstructions() {
        try {
            console.log('Attempting to load instructions from server...');
            const response = await fetch(`${this.fastApiUrl}/api/rag/text_instructions`);
            console.log('Response status:', response.status);
            if (response.ok) {
                const data = await response.json();
                console.log('Response data:', data);
                if (data.instructions) {
                    this.instructions = data.instructions;
                    console.log('Loaded instructions from text.txt:', this.instructions.substring(0, 100) + '...');
                } else {
                    console.warn('No instructions found in response');
                }
            } else {
                console.error('Failed to load instructions:', await response.text());
            }
        } catch (error) {
            console.error('Error loading instructions:', error);
        }
    }

    async initialize() {
        try {
            if (this.isInitialized) {
                console.log('Already initialized, cleaning up first...');
                // Store current config except instructions
                const currentConfig = { ...this.sessionConfig };
                delete currentConfig.instructions;
                await this.cleanup();
                // Restore config except instructions
                this.sessionConfig = {
                    ...currentConfig,
                    instructions: this.sessionConfig.instructions
                };
            }

            // Load instructions from text.txt before initializing
            await this.loadInstructions();
            if (this.instructions) {
                // Only update instructions, preserve other config
                this.sessionConfig.instructions = this.instructions;
            }

            // Get ephemeral key from server
            const sessionParams = new URLSearchParams({
                config: JSON.stringify(this.sessionConfig)
            });

            const sessionUrl = `http://127.0.0.1:8001/api/speech/session?${sessionParams}`;
            console.log('Requesting session at:', sessionUrl);

            const tokenResponse = await fetch(sessionUrl, {
                method: "GET",
                headers: {
                    "Accept": "application/json"
                },
                credentials: 'include',
                mode: 'cors'
            });

            if (!tokenResponse.ok) {
                const errorText = await tokenResponse.text();
                console.error('Session request failed:', tokenResponse.status, errorText);
                throw new Error(`Session request failed: ${tokenResponse.status} ${errorText}`);
            }

            const data = await tokenResponse.json();
            console.log('Session response:', data);

            if (data?.status !== 'success' || !data?.client_secret?.value) {
                console.error('Invalid session response:', data);
                throw new Error('Invalid session response from server');
            }

            const EPHEMERAL_KEY = data.client_secret.value;
            console.log('Got ephemeral key:', EPHEMERAL_KEY.substring(0, 8) + '...');

            // Create peer connection
            this.pc = new RTCPeerConnection({
                iceServers: [{ urls: 'stun:stun.l.google.com:19302' }]
            });

            // Set up connection state monitoring first
            this.pc.onconnectionstatechange = () => {
                const state = this.pc.connectionState;
                console.log(`Connection state changed: ${state}`);
                if (state === 'failed' || state === 'closed') {
                    this.cleanup();
                }
            };

            this.pc.oniceconnectionstatechange = () => {
                console.log(`ICE connection state: ${this.pc.iceConnectionState}`);
            };

            this.pc.onicegatheringstatechange = () => {
                console.log(`ICE gathering state: ${this.pc.iceGatheringState}`);
            };

            // Create data channel before setting up connection
            this.dc = this.pc.createDataChannel("oai-events", {
                ordered: true,
                protocol: 'json',
                negotiated: true,
                id: 0
            });

            // Set up data channel handlers immediately
            this.setupDataChannel();

            // Set up audio playback
            this.audioEl = document.createElement("audio");
            this.audioEl.autoplay = true;
            this.pc.ontrack = e => this.audioEl.srcObject = e.streams[0];

            // Add local audio track
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            this.pc.addTrack(stream.getTracks()[0]);

            // Create and send offer
            const offer = await this.pc.createOffer();
            await this.pc.setLocalDescription(offer);

            const sdpResponse = await fetch(`${this.baseUrl}?model=${this.model}`, {
                method: "POST",
                body: offer.sdp,
                headers: {
                    Authorization: `Bearer ${EPHEMERAL_KEY}`,
                    "Content-Type": "application/sdp"
                }
            });

            const answer = {
                type: "answer",
                sdp: await sdpResponse.text()
            };
            await this.pc.setRemoteDescription(answer);

            // Wait for both ICE gathering and data channel to be ready
            await new Promise((resolve, reject) => {
                const timeout = setTimeout(() => {
                    reject(new Error('Data channel connection timeout'));
                }, 10000);

                const checkReady = () => {
                    if (this.dc.readyState === 'open' && 
                        this.pc.iceGatheringState === 'complete') {
                        clearTimeout(timeout);
                        this.isDataChannelReady = true;
                        resolve();
                    }
                };

                // Check initial state
                checkReady();

                // Set up event listeners
                this.dc.onopen = () => {
                    console.log('Data channel opened');
                    checkReady();
                };

                this.pc.onicegatheringstatechange = () => {
                    console.log(`ICE gathering state changed: ${this.pc.iceGatheringState}`);
                    checkReady();
                };

                this.dc.onerror = (error) => {
                    clearTimeout(timeout);
                    reject(error);
                };
            });

            this.isInitialized = true;
            console.log('WebRTC connection established');

        } catch (error) {
            console.error('Error initializing WebRTC:', error);
            this.cleanup();
            throw error;
        }
    }

    setupDataChannel() {
        this.dc.onopen = () => {
            console.log('Data channel is open');
            this.isDataChannelReady = true;
        };

        this.dc.onclose = () => {
            console.log('Data channel closed');
            this.isDataChannelReady = false;
        };

        this.dc.onmessage = (e) => {
            const event = JSON.parse(e.data);
            this.handleRealtimeEvent(event);
        };
    }

    async startListening() {
        if (!this.isInitialized) {
            await this.initialize();
        }

        if (!this.isDataChannelReady) {
            throw new Error('Data channel not ready');
        }

        this.dc.send(JSON.stringify({
            type: "start_listening"
        }));
    }

    async stopListening() {
        try {
            if (this.dc && this.isDataChannelReady) {
                // Send stop listening command to the server
                this.dc.send(JSON.stringify({
                    type: "stop_listening"
                }));
                // Wait for the command to be sent
                await new Promise(resolve => setTimeout(resolve, 100));
                
                // Close the data channel
                this.dc.close();
                this.dc = null;
            }
            
            // Reset state
            this.isDataChannelReady = false;
            this.isInitialized = false;
            
            // Close the peer connection
            if (this.pc) {
                await this.pc.close();
                this.pc = null;
            }
            
            console.log('Stopped listening and cleaned up connections');
        } catch (error) {
            console.error('Error stopping listening:', error);
            // Force cleanup on error
            this.dc = null;
            this.pc = null;
            this.isDataChannelReady = false;
            this.isInitialized = false;
        }
    }

    async updateRagContext(query) {
        try {
            const response = await fetch(`${this.fastApiUrl}/api/rag/query`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ query: query }),
            });
            
            if (!response.ok) {
                throw new Error('Failed to fetch RAG context');
            }
            
            const data = await response.json();
            if (data.status === 'success' && data.context_used) {
                // Update instructions with the new context
                const newInstructions = `
                    You are a helpful assistant. Use the following context to answer questions:
                    
                    ${data.context_used}
                    
                    If you cannot answer based on this context, say so clearly.
                    Be concise and accurate in your responses.
                `.trim();
                
                // Update the session config
                this.sessionConfig.instructions = newInstructions;
                
                // Send the updated instructions to the realtime session
                if (this.isDataChannelReady && this.dc) {
                    this.dc.send(JSON.stringify({
                        type: "update_context",
                        instructions: newInstructions
                    }));
                }
            }
        } catch (error) {
            console.error('Error updating RAG context:', error);
        }
    }

    handleRealtimeEvent(event) {
        switch (event.type) {
            case "transcript":
                this.onTranscript?.(event.text);
                // Then update RAG context for next interaction
                this.updateRagContext(event.text);
                break;
            case "audio":
                this.onAudio?.(event.data);
                break;
            case "context_updated":
                console.log('Context updated successfully');
                break;
            default:
                console.log('Unknown event:', event);
        }
    }

    setTranscriptCallback(callback) {
        this.onTranscript = callback;
    }

    setAudioCallback(callback) {
        this.onAudio = callback;
    }

    async cleanup() {
        // Just clean up resources without sending stop command
        try {
            // Close data channel if it exists
            if (this.dc) {
                this.dc.close();
                this.dc = null;
            }

            // Close peer connection if it exists
            if (this.pc) {
                await this.pc.close();
                this.pc = null;
            }

            // Reset all states
            this.isInitialized = false;
            this.isDataChannelReady = false;
            this.ragContext = null;
            this.lastQuery = null;
            
            console.log('Cleanup completed');
        } catch (error) {
            console.error('Error during cleanup:', error);
        }
    }

    updateConfig(config) {
        this.sessionConfig = {
            ...this.sessionConfig,
            ...config
        };
        console.log('Updated session config:', this.sessionConfig);
    }

    // Method to set audio format
    setAudioFormat(format) {
        const validFormats = ['pcm16'];
        if (!validFormats.includes(format)) {
            throw new Error(`Invalid audio format. Must be one of: ${validFormats.join(', ')}`);
        }
        this.sessionConfig.input_audio_format = format;
        this.sessionConfig.output_audio_format = format;
        console.log(`Audio format set to: ${format}`);
    }

    async getKnowledgeContext(text) {
        try {
            const response = await fetch(`${this.fastApiUrl}/api/rag/query`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ query: text })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            return data.status === 'success' ? data : null;
        } catch (error) {
            console.error('Error getting knowledge context:', error);
            return null;
        }
    }

    async processUserInput(text) {
        // Get context from knowledge base
        const knowledgeData = await this.getKnowledgeContext(text);
        
        // Process with OpenAI
        try {
            const response = await this.callOpenAI(text);
            return response;
        } catch (error) {
            console.error('Error processing user input:', error);
            throw error;
        }
    }
}

// Make SpeechManager available globally
window.SpeechManager = SpeechManager;

// Helper Functions
function updateUI(isRecording) {
    document.getElementById('start-recording').disabled = isRecording;
    document.getElementById('stop-recording').disabled = !isRecording;
    
    // Update voice bot icon
    const voiceBotIcon = document.querySelector('.voice-bot-icon');
    if (voiceBotIcon) {
        voiceBotIcon.classList.toggle('active', isRecording);
    }
}

function showTranscriptionStatus(message) {
    const output = document.getElementById('transcription-output');
    if (output) output.textContent = message;
}

// Update the analysis instructions handling
async function generateAnalysisInstructions(transcript, useLlama = false) {
    try {
        const response = await fetch('/generate-analysis-instructions/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({ 
                transcript,
                use_llama: useLlama  
            }),
            credentials: 'same-origin'
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        if (data.status === 'success') {
            window.APP_STATE = window.APP_STATE || {};
            window.APP_STATE.analysisInstructions = data.instructions;
            
            try {
                const instructions = JSON.parse(data.instructions);
                const sectionsContainer = document.getElementById('analysis-sections');
                sectionsContainer.innerHTML = ''; 
                
                // Create a single textbox for all sections
                if (instructions.sections && Array.isArray(instructions.sections)) {
                    const allSectionsHtml = instructions.sections.map(section => {
                        const sectionTitle = formatSectionTitle(section.title);
                        return `
                            <h4>${sectionTitle}</h4>
                            ${formatInstructions(section.items)}
                        `;
                    }).join('');

                    // Create single container for all content
                    const containerHtml = `
                        <div class="analysis-section">
                            <div class="code-output">
                                ${allSectionsHtml}
                            </div>
                        </div>
                    `;
                    sectionsContainer.innerHTML = containerHtml;
                }
                
                // Apply syntax highlighting
                document.querySelectorAll('pre code').forEach((block) => {
                    hljs.highlightBlock(block);
                });
                
                showAnalysisPanel();
            } catch (parseError) {
                console.error('Error parsing analysis instructions:', parseError);
                showNotification('Error formatting analysis output', 'error');
            }
        } else {
            throw new Error(data.error || 'Failed to generate analysis instructions');
        }
    } catch (error) {
        console.error('Error generating analysis instructions:', error);
        showNotification('Error generating analysis: ' + error.message, 'error');
    }
}

// Helper function to format section titles
function formatSectionTitle(sectionName) {
    return sectionName
        .split('_')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ');
}

// Update the formatting function for more compact output
function formatInstructions(instructions) {
    if (Array.isArray(instructions)) {
        return instructions.map((item, index) => {
            const description = item.description || item;
            const code = item.code ? 
                `<pre><code class="python">${escapeHtml(item.code)}</code></pre>` : '';
            return `${index + 1}. ${description}${code}`;
        }).join('');  
    }
    return instructions || 'No instructions available';
}

function showAnalysisPanel() {
    const panel = document.querySelector('.analysis-panel');
    if (panel) {
        panel.classList.remove('collapsed');
        panel.querySelector('.analysis-content').style.display = 'block';
        
        // Add syntax highlighting for code blocks
        document.querySelectorAll('pre code').forEach((block) => {
            hljs.highlightBlock(block);
        });
    }
}

function toggleAnalysisPanel() {
    const panel = document.querySelector('.analysis-panel');
    const content = panel.querySelector('.analysis-content');
    const button = panel.querySelector('.toggle-button');
    
    if (content.style.display === 'none') {
        content.style.display = 'block';
        button.textContent = '▼';
        panel.classList.remove('collapsed');
    } else {
        content.style.display = 'none';
        button.textContent = '▲';
        panel.classList.add('collapsed');
    }
}

// Add helper function for checking sentence completeness
function isSentenceComplete(text) {
    // Check for sentence endings
    if (SENTENCE_ENDINGS.test(text)) return true;
    
    // Check for meaningful phrase length
    const words = text.trim().split(/\s+/);
    if (words.length >= MIN_CHUNK_LENGTH) return true;
    
    return false;
}

// Helper function to escape HTML special characters
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Add this function to create and append the voice bot icon
function createVoiceBotIcon() {
    const iconContainer = document.createElement('div');
    iconContainer.className = 'voice-bot-icon';
    iconContainer.innerHTML = `
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
            <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3zm-1-9c0-.55.45-1 1-1s1 .45 1 1v6c0 .55-.45 1-1 1s-1-.45-1-1V5z"/>
            <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"/>
        </svg>
    `;

    // Add click handler
    iconContainer.addEventListener('click', () => {
        if (iconContainer.classList.contains('disabled')) return;
        
        if (isRecording) {
            stopWhisperRecording();
            iconContainer.classList.remove('active');
        } else {
            startWhisperRecording();
            iconContainer.classList.add('active');
        }
    });

    document.body.appendChild(iconContainer);
    return iconContainer;
} 