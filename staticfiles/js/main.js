// Main JavaScript functionality
document.addEventListener('DOMContentLoaded', function() {
    // Initialize any global functionality here
});

// Search functionality
const searchInput = document.getElementById('search-input');
const searchResults = document.getElementById('search-results');

searchInput.addEventListener('input', async (e) => {
    const query = e.target.value.trim();
    
    if (query.length > 0) {
        try {
            const response = await fetch('/search', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ query })
            });
            
            if (!response.ok) {
                throw new Error('Search failed');
            }
            
            const results = await response.json();
            displaySearchResults(results);
        } catch (error) {
            console.error('Search error:', error);
            searchResults.innerHTML = '<div class="search-result-item">Error performing search</div>';
        }
    } else {
        // When search is empty, show a default message or clear the results
        searchResults.innerHTML = '<div class="search-result-item">Enter a search query to find software</div>';
    }
}); 