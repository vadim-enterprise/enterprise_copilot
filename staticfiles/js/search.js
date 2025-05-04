class Logger {
    constructor(moduleName) {
        this.moduleName = moduleName;
    }

    info(message) {
        console.log(`[${this.moduleName}] INFO: ${message}`);
    }

    error(message) {
        console.error(`[${this.moduleName}] ERROR: ${message}`);
    }

    warn(message) {
        console.warn(`[${this.moduleName}] WARN: ${message}`);
    }

    debug(message) {
        console.debug(`[${this.moduleName}] DEBUG: ${message}`);
    }
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

async function handleSearch(event) {
    event.preventDefault();
    
    const searchInput = document.getElementById('searchInput');
    const searchResults = document.getElementById('searchResults');
    const query = searchInput.value.trim();
    
    if (!query) return;

    // Show loading state
    searchResults.innerHTML = '<div class="search-result-item"><div class="loading-spinner"></div></div>';
    searchResults.classList.add('active');

    try {
        const response = await fetch('/search-knowledge/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({ query })
        });

        const data = await response.json();

        if (data.status === 'success' && data.results) {
            displaySearchResults(data.results);
        } else {
            searchResults.innerHTML = '<div class="search-result-item">No results found</div>';
        }
    } catch (error) {
        console.error('Search error:', error);
        searchResults.innerHTML = '<div class="search-result-item">Error performing search</div>';
    }
}

function displaySearchResults(results) {
    const searchResults = document.getElementById('searchResults');
    searchResults.innerHTML = '';

    if (results.length === 0) {
        searchResults.innerHTML = '<div class="search-result-item">No results found</div>';
        return;
    }

    results.forEach(result => {
        const resultElement = document.createElement('div');
        resultElement.className = 'search-result-item';
        resultElement.innerHTML = `
            <button class="add-to-kb" onclick="addToKnowledgeBase('${encodeURIComponent(JSON.stringify(result))}')">
                <span class="kb-icon">📚</span>
                Add to KB
            </button>
            <div class="search-result-title">
                <a href="${result.link}" target="_blank">${result.title}</a>
            </div>
            <div class="search-result-description">${result.snippet}</div>
        `;
        
        // Add click handler to add to knowledge base
        resultElement.addEventListener('click', () => addToKnowledgeBase(result));
        
        searchResults.appendChild(resultElement);
    });

    searchResults.classList.add('active');
}

async function addToKnowledgeBase(result) {
    try {
        const response = await fetch('http://127.0.0.1:8001/api/rag/add-to-kb', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                title: result.title,
                content: result.snippet,
                url: result.link
            })
        });

        const data = await response.json();
        
        // Show notification of success/failure
        const notification = document.createElement('div');
        notification.className = `notification ${data.status}`;
        notification.textContent = data.message;
        document.body.appendChild(notification);
        
        setTimeout(() => notification.remove(), 3000);
        
    } catch (error) {
        console.error('Error adding to knowledge base:', error);
        showNotification('Failed to add to knowledge base', 'error');
    }
}

class WebSearch {
    constructor() {
        this.baseUrl = 'http://127.0.0.1:8001/api';
        this.chatEndpoint = '/chat/query';
        this.websearchEndpoint = '/websearch/search';
        this.logger = new Logger('WebSearch');
        this.searchInput = document.getElementById('webSearchInput');
        this.searchButton = document.getElementById('webSearchButton');
        this.resultsWindow = document.getElementById('searchResultsWindow');
        this.setupEventListeners();
    }

    setupEventListeners() {
        // Handle search button click
        this.searchButton.addEventListener('click', (e) => {
            e.preventDefault();
            this.performSearch();
        });
        
        // Handle Enter key press in search input
        this.searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                this.performSearch();
            }
        });
    }

    async performSearch() {
        const query = this.searchInput.value.trim();
        if (!query) return;

        try {
            this.showLoadingState();
            
            // First try to get response from ChatGPT
            const chatResponse = await this._callChatAPI(query);
            this.logger.info(`ChatGPT response received: ${chatResponse.response.substring(0, 100)}...`);
            
            // Display the chat response
            this.displayResults({
                chat_response: chatResponse.response,
                web_results: []
            });
            
            // If web search was used or needed, perform web search
            if (chatResponse.used_web_search) {
                this.logger.info('Performing web search...');
                const webSearchResults = await this._callWebSearchAPI(query);
                this.logger.info(`Web search results received: ${webSearchResults.results.length} results`);
                
                // Update the display with web search results
                this.displayResults({
                    chat_response: chatResponse.response,
                    web_results: webSearchResults.results
                });
            }
            
        } catch (error) {
            this.logger.error(`Search error: ${error}`);
            this.showError('Failed to perform search. Please try again.');
        } finally {
            this.hideLoadingState();
        }
    }

    displayResults(data) {
        this.resultsWindow.innerHTML = '';
        
        // Display ChatGPT response
        const chatResponseElement = document.createElement('div');
        chatResponseElement.className = 'result-item chat-response';
        chatResponseElement.innerHTML = `
            <div class="result-title">AI Response</div>
            <div class="result-description">${data.chat_response}</div>
        `;
        this.resultsWindow.appendChild(chatResponseElement);
        
        // If there are web search results, display them
        if (data.web_results && data.web_results.length > 0) {
            const webResultsTitle = document.createElement('div');
            webResultsTitle.className = 'result-title web-results-title';
            webResultsTitle.textContent = 'Web Search Results';
            this.resultsWindow.appendChild(webResultsTitle);
            
            data.web_results.forEach(result => {
                const resultElement = document.createElement('div');
                resultElement.className = 'result-item web-result';
                resultElement.innerHTML = `
                    <div class="result-title">${result.title}</div>
                    <div class="result-description">${result.snippet}</div>
                    <a href="${result.link}" class="result-link" target="_blank">Read more</a>
                `;
                this.resultsWindow.appendChild(resultElement);
            });
        }

        this.resultsWindow.classList.add('active');
    }

    showLoadingState() {
        this.searchButton.classList.add('loading');
        this.resultsWindow.innerHTML = '<div class="result-item">Analyzing your query...</div>';
        this.resultsWindow.classList.add('active');
    }

    hideLoadingState() {
        this.searchButton.classList.remove('loading');
    }

    showError(message) {
        this.resultsWindow.innerHTML = `<div class="result-item error">${message}</div>`;
        this.resultsWindow.classList.add('active');
    }

    async _callChatAPI(query) {
        try {
            this.logger.info(`Calling chat API with query: ${query}`);
            
            const response = await fetch(`${this.baseUrl}${this.chatEndpoint}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify({
                    query: query,
                    use_web_search: false
                })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(`Chat API error! status: ${response.status}, detail: ${errorData.detail || 'Unknown error'}`);
            }

            return await response.json();
        } catch (error) {
            this.logger.error(`Error calling chat API: ${error}`);
            throw error;
        }
    }

    async _callWebSearchAPI(query) {
        try {
            this.logger.info(`Calling web search API with query: ${query}`);
            
            const response = await fetch(`${this.baseUrl}${this.websearchEndpoint}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify({
                    query: query
                })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(`Web search API error! status: ${response.status}, detail: ${errorData.detail || 'Unknown error'}`);
            }

            return await response.json();
        } catch (error) {
            this.logger.error(`Error calling web search API: ${error}`);
            throw error;
        }
    }
}

// Helper function to show notifications
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    document.body.appendChild(notification);
    
    setTimeout(() => notification.remove(), 3000);
}

// Initialize WebSearch when the page loads
document.addEventListener('DOMContentLoaded', () => {
    window.webSearch = new WebSearch();
});

async function performSearch(query) {
    try {
        const response = await fetch('/api/search', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ query })
        });
        
        const data = await response.json();
        
        if (data.type === 'combined') {
            // Display the AI's combined analysis
            const resultsWindow = document.getElementById('searchResultsWindow');
            resultsWindow.innerHTML = `
                <div class="alert alert-info">
                    <h6>Analysis Context:</h6>
                    <p>Using ${data.context.total_datasets} available datasets</p>
                </div>
                <div class="mt-3">
                    <h6>Comprehensive Answer:</h6>
                    <p>${data.answer.replace(/\n/g, '<br>')}</p>
                </div>
                <div class="mt-3">
                    <h6>Web Search Results:</h6>
                    ${data.web_results.map(result => `
                        <div class="card mb-3">
                            <div class="card-body">
                                <h5 class="card-title">${result.title}</h5>
                                <p class="card-text">${result.snippet}</p>
                                <a href="${result.link}" class="btn btn-primary" target="_blank">Visit Source</a>
                            </div>
                        </div>
                    `).join('')}
                </div>
            `;
        }
    } catch (error) {
        console.error('Search error:', error);
        const resultsWindow = document.getElementById('searchResultsWindow');
        resultsWindow.innerHTML = `
            <div class="alert alert-danger">
                Error: ${error.message}
            </div>
        `;
    }
} 