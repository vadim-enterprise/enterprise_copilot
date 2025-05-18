/**
 * Analytics Search Integration
 * This file handles the integration between the websearch bar and analytics functionality
 */

// Function to handle analytics-related search queries
async function handleAnalyticsSearch(query) {
    try {
        // Show loading indicator
        showLoadingIndicator();
        
        // Call the websearch API endpoint
        const response = await fetch('/websearch', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: `query=${encodeURIComponent(query)}`
        });
        
        if (!response.ok) {
            throw new Error(`Error: ${response.status}`);
        }
        
        const data = await response.json();
        
        // Hide loading indicator
        hideLoadingIndicator();
        
        // Process the response
        if (data.type === 'analytics') {
            // This is an analytics result
            displayAnalyticsResults(data.results);
            return true; // Indicate that this was handled as analytics
        }
        
        // This was not an analytics query
        return false;
    } catch (error) {
        console.error('Error in analytics search:', error);
        hideLoadingIndicator();
        showErrorMessage('Error processing analytics query');
        return false;
    }
}

// Function to display analytics results
function displayAnalyticsResults(results) {
    // Get the results container
    const resultsContainer = document.getElementById('search-results') || 
                             document.getElementById('results-container') ||
                             createResultsContainer();
    
    // Clear previous results
    resultsContainer.innerHTML = '';
    
    // Check if the query was successfully processed as an analytics query
    if (!results.is_analytics_query) {
        resultsContainer.innerHTML = '<div class="alert alert-info">This query is not related to analytics.</div>';
        return;
    }
    
    // Check if the analytics processing was successful
    if (!results.success) {
        resultsContainer.innerHTML = `<div class="alert alert-danger">Analytics Error: ${results.message}</div>`;
        return;
    }
    
    // Create header
    const header = document.createElement('h3');
    header.textContent = 'Analytics Results';
    resultsContainer.appendChild(header);
    
    // Display analysis type if available
    if (results.analysis_type) {
        const analysisType = document.createElement('div');
        analysisType.className = 'analysis-type';
        analysisType.textContent = `Analysis Type: ${formatAnalysisType(results.analysis_type)}`;
        resultsContainer.appendChild(analysisType);
    }
    
    // Display results
    if (results.results) {
        displayAnalyticsResultDetails(resultsContainer, results.results);
    }
}

// Function to display detailed analytics results
function displayAnalyticsResultDetails(container, results) {
    // Check if we have anomaly detection results
    if (results.anomaly_detection) {
        displayAnomalyDetectionResults(container, results.anomaly_detection);
    }
    
    // Check if we have clustering results
    if (results.clustering) {
        displayClusteringResults(container, results.clustering);
    }
    
    // Check if we have time series results
    const timeSeriesKeys = Object.keys(results).filter(key => key.startsWith('time_series_'));
    if (timeSeriesKeys.length > 0) {
        timeSeriesKeys.forEach(key => {
            displayTimeSeriesResults(container, results[key], key.replace('time_series_', ''));
        });
    }
    
    // If we have a plot, display it
    if (results.plot) {
        displayPlot(container, results.plot);
    }
}

// Function to display anomaly detection results
function displayAnomalyDetectionResults(container, results) {
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
        displayPlot(section, results.plot);
    }
    
    container.appendChild(section);
}

// Function to display clustering results
function displayClusteringResults(container, results) {
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
        displayPlot(section, results.plot);
    }
    
    container.appendChild(section);
}

// Function to display time series results
function displayTimeSeriesResults(container, results, columnName) {
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
        trendDiv.textContent = `Trend: ${results.trend}`;
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
                item.textContent = `${formatStatName(key)}: ${value.toFixed(2)}`;
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
        forecastDiv.innerHTML = `<strong>Forecast (next ${results.forecast.length} periods):</strong> ${results.forecast.map(v => v.toFixed(2)).join(', ')}`;
        section.appendChild(forecastDiv);
    }
    
    // Display plot if available
    if (results.plot) {
        displayPlot(section, results.plot);
    }
    
    container.appendChild(section);
}

// Function to display a plot
function displayPlot(container, plotBase64) {
    const plotDiv = document.createElement('div');
    plotDiv.className = 'plot-container';
    
    const img = document.createElement('img');
    img.src = `data:image/png;base64,${plotBase64}`;
    img.className = 'analytics-plot';
    img.alt = 'Analytics Plot';
    
    plotDiv.appendChild(img);
    container.appendChild(plotDiv);
}

// Helper function to format analysis type
function formatAnalysisType(type) {
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

// Helper function to format stat names
function formatStatName(name) {
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

// Function to show loading indicator
function showLoadingIndicator() {
    // Check if loading indicator already exists
    let loader = document.getElementById('analytics-loader');
    
    if (!loader) {
        // Create loading indicator
        loader = document.createElement('div');
        loader.id = 'analytics-loader';
        loader.className = 'analytics-loader';
        loader.innerHTML = '<div class="spinner"></div><p>Processing analytics query...</p>';
        
        // Add styles for the loader
        const style = document.createElement('style');
        style.textContent = `
            .analytics-loader {
                position: fixed;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                background-color: rgba(255, 255, 255, 0.9);
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
                z-index: 1000;
                text-align: center;
            }
            .spinner {
                border: 4px solid #f3f3f3;
                border-top: 4px solid #3498db;
                border-radius: 50%;
                width: 40px;
                height: 40px;
                animation: spin 2s linear infinite;
                margin: 0 auto 10px;
            }
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
        `;
        document.head.appendChild(style);
        
        // Add to document
        document.body.appendChild(loader);
    } else {
        loader.style.display = 'block';
    }
}

// Function to hide loading indicator
function hideLoadingIndicator() {
    const loader = document.getElementById('analytics-loader');
    if (loader) {
        loader.style.display = 'none';
    }
}

// Function to show error message
function showErrorMessage(message) {
    // Create error message element
    const errorDiv = document.createElement('div');
    errorDiv.className = 'analytics-error';
    errorDiv.textContent = message;
    errorDiv.style.cssText = 'background-color: #f8d7da; color: #721c24; padding: 10px; border-radius: 4px; margin: 10px 0;';
    
    // Get the results container or create one
    const resultsContainer = document.getElementById('search-results') || 
                             document.getElementById('results-container') ||
                             createResultsContainer();
    
    // Add error message to results container
    resultsContainer.prepend(errorDiv);
    
    // Remove after 5 seconds
    setTimeout(() => {
        errorDiv.remove();
    }, 5000);
}

// Function to create results container if it doesn't exist
function createResultsContainer() {
    const container = document.createElement('div');
    container.id = 'search-results';
    container.className = 'search-results-container';
    
    // Find a suitable place to add the container
    const searchBar = document.querySelector('.search-bar') || document.querySelector('input[type="search"]');
    if (searchBar) {
        // Add after search bar
        searchBar.parentNode.insertBefore(container, searchBar.nextSibling);
    } else {
        // Add to body if search bar not found
        document.body.appendChild(container);
    }
    
    return container;
}

// Function to integrate with the search bar
function integrateWithSearchBar() {
    // Find the search form
    const searchForm = document.querySelector('form.search-form') || document.querySelector('form:has(input[type="search"])');
    
    if (searchForm) {
        // Add event listener to the form
        searchForm.addEventListener('submit', async function(event) {
            // Get the search input
            const searchInput = this.querySelector('input[type="search"]') || this.querySelector('input[name="q"]');
            
            if (searchInput) {
                const query = searchInput.value.trim();
                
                // Check if this is potentially an analytics query
                const analyticsKeywords = ['analyze', 'analysis', 'analytics', 'statistics', 'stats', 
                                          'anomaly', 'anomalies', 'clustering', 'cluster', 'forecast',
                                          'time series', 'trend', 'prediction', 'predict', 'model'];
                
                const isAnalyticsQuery = analyticsKeywords.some(keyword => query.toLowerCase().includes(keyword));
                
                if (isAnalyticsQuery) {
                    // Prevent the default form submission
                    event.preventDefault();
                    
                    // Handle as analytics query
                    const handled = await handleAnalyticsSearch(query);
                    
                    // If not handled as analytics, submit the form normally
                    if (!handled) {
                        this.submit();
                    }
                }
            }
        });
    }
}

// Initialize when the DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    integrateWithSearchBar();
}); 