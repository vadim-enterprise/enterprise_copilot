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
        // Define API endpoints
        this.chatEndpoint = 'http://127.0.0.1:8001/api/chat/query';
        this.webSearchEndpoint = 'http://127.0.0.1:8001/api/websearch/search';
        
        // Get DOM elements
        this.searchInput = document.getElementById('webSearchInput');
        this.searchButton = document.getElementById('webSearchButton');
        this.resultsWindow = document.getElementById('searchResultsWindow');
        this.resultsContent = document.querySelector('.search-results-content');
        this.closeButton = this.resultsWindow?.querySelector('.search-results-close');
        this.mapContainer = document.querySelector('.map-container');
        
        if (!this.mapContainer) {
            console.warn('[WebSearch] Map container not found - maps will not be displayed');
        }
        
        if (!this.resultsContent) {
            console.warn('[WebSearch] Results content container not found - results will not be displayed');
        }
        
        // Initialize if elements exist
        if (this.searchInput && this.searchButton && this.resultsWindow && this.resultsContent) {
            this.initialize();
            this.initializeMap();
        } else {
            console.error('[WebSearch] Required elements not found:', {
                searchInput: !!this.searchInput,
                searchButton: !!this.searchButton,
                resultsWindow: !!this.resultsWindow,
                resultsContent: !!this.resultsContent
            });
        }
    }

    initialize() {
        // Add event listeners
        this.searchButton.addEventListener('click', () => this.performSearch());
        this.searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.performSearch();
            }
        });
        
        // Add close button handler
        if (this.closeButton) {
            this.closeButton.addEventListener('click', () => {
                this.resultsWindow.classList.remove('active');
            });
        }
    }

    initializeMap() {
        if (!this.mapContainer) {
            console.warn('[WebSearch] Map container not found - skipping map initialization');
            return;
        }

        // Set up the map dimensions
        const width = 800;
        const height = 400;

        // Create SVG container
        const svg = d3.select(this.mapContainer)
            .append('svg')
            .attr('width', width)
            .attr('height', height);

        // Create a projection
        const projection = d3.geoAlbersUsa()
            .fitSize([width, height], { type: 'Sphere' });

        // Create a path generator
        const path = d3.geoPath().projection(projection);

        // Load the US map data
        d3.json('https://cdn.jsdelivr.net/npm/us-atlas@3/states-10m.json')
            .then(us => {
                // Convert TopoJSON to GeoJSON
                const states = topojson.feature(us, us.objects.states);

                // Draw the states
                svg.append('g')
                    .selectAll('path')
                    .data(states.features)
                    .enter()
                    .append('path')
                    .attr('d', path)
                    .attr('class', 'state')
                    .attr('fill', '#e0e0e0')
                    .attr('stroke', '#fff')
                    .attr('stroke-width', 1)
                    .on('mouseover', function(event, d) {
                        d3.select(this)
                            .attr('fill', '#bdbdbd');
                    })
                    .on('mouseout', function(event, d) {
                        d3.select(this)
                            .attr('fill', '#e0e0e0');
                    });

                // Add state names
                svg.append('g')
                    .selectAll('text')
                    .data(states.features)
                    .enter()
                    .append('text')
                    .attr('x', d => path.centroid(d)[0])
                    .attr('y', d => path.centroid(d)[1])
                    .attr('text-anchor', 'middle')
                    .attr('font-size', '8px')
                    .text(d => d.properties.name);

                // Add tooltip
                const tooltip = d3.select('#map')
                    .append('div')
                    .attr('class', 'state-tooltip')
                    .style('opacity', 0);

                // Add tooltip events
                svg.selectAll('.state')
                    .on('mouseover', function(event, d) {
                        tooltip.transition()
                            .duration(200)
                            .style('opacity', .9);
                        tooltip.html(d.properties.name)
                            .style('left', (event.pageX + 10) + 'px')
                            .style('top', (event.pageY - 28) + 'px');
                    })
                    .on('mouseout', function(d) {
                        tooltip.transition()
                            .duration(500)
                            .style('opacity', 0);
                    });
            })
            .catch(error => {
                console.error('[WebSearch] Error loading map data:', error);
            });
    }

    updateMapColors(stateData) {
        if (!this.mapContainer) return;

        // Update state colors based on data
        d3.selectAll('.state')
            .attr('fill', d => {
                const stateName = d.properties.name;
                const data = stateData[stateName];
                if (data) {
                    // Color scale based on data value
                    return d3.scaleSequential(d3.interpolateBlues)(data.value);
                }
                return '#e0e0e0';
            });
    }

    async performSearch() {
        const query = this.searchInput.value.trim();
        
        if (!query) {
            return;
        }
        
        // Show loading state
        this.resultsWindow.classList.add('active');
        this.resultsContent.innerHTML = '<div class="loading-spinner"></div>';
        
        try {
            // First check if this is an analytics-related query
            const analyticsKeywords = [
                'analyze', 'analysis', 'analytics', 'statistics', 'stats',
                'anomaly', 'anomalies', 'clustering', 'cluster', 'forecast',
                'time series', 'trend', 'prediction', 'predict', 'model'
            ];
            
            const isAnalyticsQuery = analyticsKeywords.some(keyword => query.toLowerCase().includes(keyword));
            
            if (isAnalyticsQuery) {
                // Try to handle as an analytics query
                const analyticsResponse = await fetch('/websearch', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded',
                    },
                    body: `query=${encodeURIComponent(query)}`
                });
                
                if (analyticsResponse.ok) {
                    const analyticsData = await analyticsResponse.json();
                    
                    if (analyticsData.type === 'analytics' && analyticsData.results.is_analytics_query) {
                        // This was successfully processed as an analytics query
                        this.displayAnalyticsResults(analyticsData.results);
                        return;
                    }
                }
            }
            
            // If not an analytics query or analytics processing failed, proceed with regular search
            const data = await this._callChatAPI(query);
            this.displayResults(data);
        } catch (error) {
            console.error('Search error:', error);
            this.displayError('Error performing search. Please try again.');
        }
    }

    async _callChatAPI(query) {
        try {
            console.log('[WebSearch] Calling chat API with query:', query);
            
            const response = await fetch(this.chatEndpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    query,
                    use_web_search: true
                })
            });

            if (!response.ok) {
                throw new Error(`API request failed with status ${response.status}`);
            }

            const data = await response.json();
            console.log('[WebSearch] Raw API response data:', data);

            // Check if we have a valid response
            if (!data || typeof data !== 'object') {
                throw new Error('Invalid response format from API');
            }

            // Check the structure of the response
            if (data.response) {
                // If the response is nested under a 'response' key
                return {
                    chat_response: data.response,
                    web_results: data.web_results || []
                };
            } else if (data.chat_response) {
                // If the response is already in the expected format
                return data;
            } else {
                // If we have a different response structure
                console.warn('[WebSearch] Unexpected response structure:', data);
                return {
                    chat_response: JSON.stringify(data),
                    web_results: []
                };
            }
        } catch (error) {
            console.error('[WebSearch] Error calling chat API:', error);
            throw error;
        }
    }

    displayResults(data) {
        if (!this.resultsContent) {
            console.error('[WebSearch] Results content element not found');
            return;
        }

        console.log('[WebSearch] Processing data for display:', data);

        // Clear previous results
        this.resultsContent.innerHTML = '';
        
        // Display chat response if available
        if (data.chat_response) {
            console.log('[WebSearch] Displaying chat response:', data.chat_response);
            const chatResponseElement = document.createElement('div');
            chatResponseElement.className = 'result-item chat-response';
            chatResponseElement.innerHTML = `
                <div class="result-title">AI Analysis</div>
                <div class="result-description">${data.chat_response}</div>
            `;
            this.resultsContent.appendChild(chatResponseElement);
        }
        
        // Display web search results if available
        if (data.web_results && data.web_results.length > 0) {
            console.log('[WebSearch] Displaying web results:', data.web_results);
            const webResultsTitle = document.createElement('div');
            webResultsTitle.className = 'web-results-title';
            webResultsTitle.textContent = 'Web Search Results';
            this.resultsContent.appendChild(webResultsTitle);
            
            data.web_results.forEach(result => {
                const resultElement = document.createElement('div');
                resultElement.className = 'result-item web-result';
                resultElement.innerHTML = `
                    <div class="result-title">${result.title || 'Untitled'}</div>
                    <div class="result-description">${result.snippet || 'No description available'}</div>
                    ${result.link ? `<a href="${result.link}" class="result-link" target="_blank">Read more</a>` : ''}
                `;
                this.resultsContent.appendChild(resultElement);
            });
        }

        // Only show "No Results" if we have no chat response and no web results
        if (!data.chat_response && (!data.web_results || data.web_results.length === 0)) {
            console.log('[WebSearch] No results found');
            const noResultsElement = document.createElement('div');
            noResultsElement.className = 'result-item';
            noResultsElement.innerHTML = `
                <div class="result-title">No Results</div>
                <div class="result-description">No results found for your search query.</div>
            `;
            this.resultsContent.appendChild(noResultsElement);
        }
        
        // Show the results window
        this.resultsWindow.classList.add('active');
    }

    displayError(message) {
        if (!this.resultsContent) {
            console.error('[WebSearch] Results content element not found');
            return;
        }

        this.resultsContent.innerHTML = `
            <div class="result-item chat-response">
                <div class="result-title">Error</div>
                <div class="result-description">${message}</div>
            </div>
        `;
        
        this.resultsWindow.classList.add('active');
    }

    formatTextToBullets(text) {
        if (!text) return '';
        
        // Split text into sentences
        const sentences = text.split(/[.!?]+/).filter(s => s.trim());
        
        // Format each sentence as a bullet point
        return sentences.map(sentence => `<p>${sentence.trim()}</p>`).join('');
    }

    displayAnalyticsResults(results) {
        // Clear previous results
        this.resultsContent.innerHTML = '';
        
        // Create header
        const header = document.createElement('h3');
        header.textContent = 'Analytics Results';
        this.resultsContent.appendChild(header);
        
        // Check if the analytics processing was successful
        if (!results.success) {
            const errorDiv = document.createElement('div');
            errorDiv.className = 'error-message';
            errorDiv.textContent = `Analytics Error: ${results.message}`;
            this.resultsContent.appendChild(errorDiv);
            return;
        }
        
        // Display analysis type if available
        if (results.analysis_type) {
            const analysisType = document.createElement('div');
            analysisType.className = 'analysis-type';
            analysisType.innerHTML = `<strong>Analysis Type:</strong> ${this.formatAnalysisType(results.analysis_type)}`;
            this.resultsContent.appendChild(analysisType);
        }
        
        // Display results
        if (results.results) {
            this.displayAnalyticsResultDetails(results.results);
        }
    }

    displayAnalyticsResultDetails(results) {
        // Check if we have anomaly detection results
        if (results.anomaly_detection) {
            this.displayAnomalyDetectionResults(results.anomaly_detection);
        }
        
        // Check if we have clustering results
        if (results.clustering) {
            this.displayClusteringResults(results.clustering);
        }
        
        // Check if we have time series results
        const timeSeriesKeys = Object.keys(results).filter(key => key.startsWith('time_series_'));
        if (timeSeriesKeys.length > 0) {
            timeSeriesKeys.forEach(key => {
                this.displayTimeSeriesResults(results[key], key.replace('time_series_', ''));
            });
        }
    }

    displayAnomalyDetectionResults(results) {
        const section = document.createElement('div');
        section.className = 'analysis-section anomaly-section';
        
        // Create header
        const header = document.createElement('h4');
        header.textContent = 'Anomaly Detection Results';
        section.appendChild(header);
        
        // Display anomaly count
        const countDiv = document.createElement('div');
        countDiv.className = 'anomaly-count';
        countDiv.textContent = `Found ${results.anomaly_count} anomalies in the data`;
        section.appendChild(countDiv);
        
        // Display plot if available
        if (results.plot) {
            this.displayPlot(section, results.plot);
        }
        
        this.resultsContent.appendChild(section);
    }

    displayClusteringResults(results) {
        const section = document.createElement('div');
        section.className = 'analysis-section clustering-section';
        
        // Create header
        const header = document.createElement('h4');
        header.textContent = 'Clustering Results';
        section.appendChild(header);
        
        // Display cluster count
        const countDiv = document.createElement('div');
        countDiv.className = 'cluster-count';
        countDiv.textContent = `Data segmented into ${results.n_clusters} distinct clusters`;
        section.appendChild(countDiv);
        
        // Display plot if available
        if (results.plot) {
            this.displayPlot(section, results.plot);
        }
        
        this.resultsContent.appendChild(section);
    }

    displayTimeSeriesResults(results, columnName) {
        const section = document.createElement('div');
        section.className = 'analysis-section time-series-section';
        
        // Create header
        const header = document.createElement('h4');
        header.textContent = `Time Series Analysis: ${columnName}`;
        section.appendChild(header);
        
        // Display trend information
        if (results.trend) {
            const trendDiv = document.createElement('div');
            trendDiv.className = 'trend-info';
            trendDiv.innerHTML = `<strong>Trend:</strong> ${results.trend}`;
            section.appendChild(trendDiv);
        }
        
        // Display statistics if available
        if (results.stats) {
            const statsDiv = document.createElement('div');
            statsDiv.className = 'stats-info';
            
            const statsList = document.createElement('ul');
            for (const [key, value] of Object.entries(results.stats)) {
                if (typeof value === 'number') {
                    const item = document.createElement('li');
                    item.textContent = `${this.formatStatName(key)}: ${value.toFixed(2)}`;
                    statsList.appendChild(item);
                }
            }
            
            statsDiv.appendChild(statsList);
            section.appendChild(statsDiv);
        }
        
        // Display forecast if available
        if (results.forecast && results.forecast.length > 0) {
            const forecastDiv = document.createElement('div');
            forecastDiv.className = 'forecast-info';
            forecastDiv.innerHTML = `<strong>Forecast (next ${results.forecast.length} periods):</strong> ${results.forecast.map(v => parseFloat(v).toFixed(2)).join(', ')}`;
            section.appendChild(forecastDiv);
        }
        
        // Display plot if available
        if (results.plot) {
            this.displayPlot(section, results.plot);
        }
        
        this.resultsContent.appendChild(section);
    }

    displayPlot(container, plotBase64) {
        const plotDiv = document.createElement('div');
        plotDiv.className = 'plot-container';
        
        const img = document.createElement('img');
        img.src = `data:image/png;base64,${plotBase64}`;
        img.className = 'analytics-plot';
        img.alt = 'Analytics Plot';
        img.style.maxWidth = '100%';
        
        plotDiv.appendChild(img);
        container.appendChild(plotDiv);
    }

    formatAnalysisType(type) {
        switch (type) {
            case 'anomaly':
                return 'Anomaly Detection';
            case 'clustering':
                return 'Clustering Analysis';
            case 'time_series':
                return 'Time Series Analysis';
            default:
                return type.charAt(0).toUpperCase() + type.slice(1);
        }
    }

    formatStatName(name) {
        switch (name) {
            case 'mean':
                return 'Mean';
            case 'std':
                return 'Standard Deviation';
            case 'min':
                return 'Minimum';
            case 'max':
                return 'Maximum';
            case 'current':
                return 'Current Value';
            case 'previous':
                return 'Previous Value';
            case 'percent_change':
                return 'Percent Change';
            default:
                return name.charAt(0).toUpperCase() + name.slice(1).replace(/_/g, ' ');
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
    // Create logger instance
    const logger = new Logger('WebSearch');
    
    // Initialize WebSearch instance
    window.webSearch = new WebSearch();
    
    // Log initialization
    logger.info('WebSearch initialized');
});