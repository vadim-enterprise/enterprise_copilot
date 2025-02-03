class SpeechManager {
    constructor() {
        this.pc = null;
        this.dc = null;
        this.audioEl = null;
        this.isInitialized = false;
        this.isDataChannelReady = false;
        this.baseUrl = "https://api.openai.com/v1/realtime";
        this.model = "gpt-4o-realtime-preview-2024-12-17";
    }

    async initialize() {
        try {
            // Get ephemeral key from server
            const tokenResponse = await fetch("http://127.0.0.1:8001/api/session", {
                method: "GET",
                headers: {
                    "Accept": "application/json"
                },
                credentials: 'include',
                mode: 'cors'
            });

            const data = await tokenResponse.json();
            if (!data.client_secret?.value) {
                console.error('Invalid session response:', data);
                throw new Error('Invalid session response from server');
            }

            const EPHEMERAL_KEY = data.client_secret.value;

            // Create peer connection
            this.pc = new RTCPeerConnection({
                iceServers: [{ urls: 'stun:stun.l.google.com:19302' }]
            });

            // Set up audio playback
            this.audioEl = document.createElement("audio");
            this.audioEl.autoplay = true;
            this.pc.ontrack = e => this.audioEl.srcObject = e.streams[0];

            // Add local audio track
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            this.pc.addTrack(stream.getTracks()[0]);

            // Set up data channel
            this.dc = this.pc.createDataChannel("oai-events");
            this.setupDataChannel();

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

            this.isInitialized = true;
            console.log('WebRTC connection established');

        } catch (error) {
            console.error('Error initializing WebRTC:', error);
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

    stopListening() {
        if (this.dc && this.isDataChannelReady) {
            this.dc.send(JSON.stringify({
                type: "stop_listening"
            }));
        }
    }

    handleRealtimeEvent(event) {
        switch (event.type) {
            case "transcript":
                this.onTranscript?.(event.text);
                break;
            case "audio":
                this.onAudio?.(event.data);
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

    cleanup() {
        if (this.pc) {
            this.pc.close();
            this.pc = null;
        }
        if (this.audioEl) {
            this.audioEl.srcObject = null;
        }
        this.isInitialized = false;
        this.isDataChannelReady = false;
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