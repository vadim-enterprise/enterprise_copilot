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
        this.searchInput = document.getElementById('webSearchInput');
        this.searchButton = document.getElementById('webSearchButton');
        // Create results container if it doesn't exist
        this.resultsContainer = document.querySelector('.search-results') || (() => {
            const container = document.createElement('div');
            container.className = 'search-results';
            document.querySelector('.search-container').appendChild(container);
            return container;
        })();
        
        this.fastApiUrl = 'http://127.0.0.1:8001';
        this.serverAvailable = false;
        
        // Add reference to search button icon
        this.searchIcon = this.searchButton.querySelector('.search-icon');
        
        this.setupEventListeners();
        this.checkServer();
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

        // Add input event listener to enable/disable button
        this.searchInput.addEventListener('input', () => {
            this.searchButton.disabled = !this.searchInput.value.trim();
        });
    }

    async checkServer() {
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 5000);

            // Update the URL to include /api/ prefix
            const response = await fetch(`${this.fastApiUrl}/api/health-check`, {
                signal: controller.signal
            });
            
            clearTimeout(timeoutId);

            if (response.ok) {
                const data = await response.json();
                this.serverAvailable = data.status === 'ok';
                console.log('Search server status:', data);
                
                if (!this.serverAvailable) {
                    this.showError('Some services may be unavailable');
                }
            } else {
                throw new Error(`Server responded with status: ${response.status}`);
            }
        } catch (error) {
            if (error.name === 'AbortError') {
                console.error('Server check timed out');
                throw new Error('Server check timed out');
            }
            console.error('Search server is not available:', error);
            this.showError('Search service is currently unavailable. Please try again later.');
            this.serverAvailable = false;
        }
    }

    async performSearch() {
        const query = this.searchInput.value.trim();
        if (!query) return;

        if (!this.serverAvailable) {
            this.showError('Search service is currently unavailable. Please ensure the server is running.');
            return;
        }

        try {
            // Show loading state
            this.searchButton.classList.add('loading');
            this.showLoadingState();

            console.log('Performing web search with query:', query);

            const response = await fetch(`${this.fastApiUrl}/api/websearch/search`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ query })
            });

            const data = await response.json();
            
            // Clear previous results
            this.resultsContainer.innerHTML = '';
            
            if (data.status === 'success' && data.results && data.results.length > 0) {
                const resultsHeader = document.createElement('h2');
                resultsHeader.className = 'results-header';
                resultsHeader.textContent = `Search Results for "${query}"`;
                this.resultsContainer.appendChild(resultsHeader);
                
                data.results.forEach(result => {
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
                    this.resultsContainer.appendChild(resultElement);
                });
            } else {
                this.resultsContainer.innerHTML = '<div class="no-results">No results found</div>';
            }
            this.resultsContainer.classList.add('active');
            
            // Make results visible with animation
            setTimeout(() => {
                this.resultsContainer.classList.add('visible');
            }, 100);

        } catch (error) {
            console.error('Search error:', error);
            this.showError(error.message || 'Failed to perform search. Please try again later.');
            this.resultsContainer.innerHTML = '<div class="error-message">Error performing search</div>';
            this.resultsContainer.classList.add('active');
        } finally {
            // Hide loading states
            this.searchButton.classList.remove('loading');
            this.hideLoadingState();
        }
    }

    showLoadingState() {
        this.resultsContainer.classList.remove('visible');
        this.resultsContainer.innerHTML = `
            <div class="loading-indicator">
                <div class="spinner"></div>
                <span>Searching...</span>
            </div>
        `;
        // Trigger reflow and show loading indicator
        void this.resultsContainer.offsetWidth;
        this.resultsContainer.classList.add('visible');
    }

    hideLoadingState() {
        const loading = this.resultsContainer.querySelector('.loading-indicator');
        if (loading) {
            this.resultsContainer.classList.remove('visible');
            setTimeout(() => {
                loading.remove();
            }, 300); // Match the CSS transition duration
        }
    }

    showError(message) {
        this.resultsContainer.innerHTML = `
            <div class="error-message">
                <p>🚫 ${message}</p>
                <p>Please try again later.</p>
            </div>
        `;
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

// Initialize web search when document loads
document.addEventListener('DOMContentLoaded', () => {
    new WebSearch();
}); 