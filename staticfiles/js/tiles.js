// Function to fetch and update tile data
async function updateTileData() {
    try {
        console.log('Fetching tile data from http://localhost:8001/api/tiles');
        const response = await fetch('http://localhost:8001/api/tiles', {
            method: 'GET',
            headers: {
                'Accept': 'application/json'
            },
            mode: 'cors'
        });
        
       
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('fetched tiles:', data); 
        console.log('Raw API response:', data);
        
        // Check if data and data.tiles exist
        if (!data || !data.tiles || !Array.isArray(data.tiles)) {
            console.error('Invalid data format received:', data);
            return;
        }
        
        // Log the first tile to see its structure
        if (data.tiles.length > 0) {
            console.log('First tile structure:', JSON.stringify(data.tiles[0], null, 2));
            console.log('First tile keys:', Object.keys(data.tiles[0]));
        }

        // Log all unique keys across all tiles
        const allKeys = new Set();
        data.tiles.forEach(tile => {
            Object.keys(tile).forEach(key => allKeys.add(key));
        });
        console.log('All unique keys in tiles:', Array.from(allKeys));

        // Log all unique values for each key
        const uniqueValues = {};
        allKeys.forEach(key => {
            uniqueValues[key] = new Set();
            data.tiles.forEach(tile => {
                if (tile[key] !== undefined) {
                    uniqueValues[key].add(tile[key]);
                }
            });
        });
        console.log('Unique values for each key:', Object.fromEntries(
            Object.entries(uniqueValues).map(([key, values]) => [key, Array.from(values)])
        ));
        
        // Log detailed information about each tile
        console.log("Detailed tile information:");
        data.tiles.forEach((tile, index) => {
            console.log(`Tile ${index + 1}:`, JSON.stringify({
                name: tile.name,
                category: tile.category,
                title: tile.title,
                description: tile.description,
                color: tile.color,
                metrics: tile.metrics,
                notification_type: tile.notification_type,
                motion: tile.motion,
                customer: tile.customer,
                issue: tile.issue
            }, null, 2));
        });
        
        // Find all map sections on the page
        const allMapSections = document.querySelectorAll('.map-section');
        console.log(`Found ${allMapSections.length} map sections on the page`);
        
        // Update each section with its corresponding tile data
        allMapSections.forEach(section => {
            const header = section.querySelector('.map-section-header');
            if (!header) return;
            
            const headerText = header.textContent.trim();
            console.log(`Processing section: "${headerText}"`);
        });
    } catch (error) {
        console.error('Error fetching tile data:', error);
    }
}

// Helper function to update the tile content
function updateTileContent(header, tile) {
    if (!header) {
        console.error('No header element provided');
        return;
    }
    
    const tileContainer = header.closest('.map-section');
    if (!tileContainer) {
        console.error('No tile container found');
        return;
    }
    
    console.log(`Updating tile content for company:`, tile);
    
    // Set color based on notification_type
    let tileColor = '#ffffff'; // Default white
    switch(tile.notification_type) {
        case 'Alert':
            tileColor = '#ff5252'; // Red
            break;
        case 'Warning':
            tileColor = '#ffb142'; // Orange
            break;
        case 'Good News':
            tileColor = '#2ed573'; // Green
            break;
        case 'Info':
            tileColor = '#54a0ff'; // Blue
            break;
        default:
            console.log(`Unknown notification type: ${tile.notification_type}, using default color`);
    }
    
    // Apply the color to the tile container
    tileContainer.style.backgroundColor = tileColor;
    
    // Set text color for better contrast
    tileContainer.style.color = (tile.notification_type === 'Alert' || tile.notification_type === 'Warning') 
        ? '#ffffff'  // White text for dark backgrounds
        : '#333333'; // Dark text for light backgrounds
    
    // Update tile content
    const content = tileContainer.querySelector('.map-section-content');
    if (content) {
        // Create or update the data display
        let dataDisplay = content.querySelector('.tile-data');
        if (!dataDisplay) {
            dataDisplay = document.createElement('div');
            dataDisplay.className = 'tile-data';
            content.appendChild(dataDisplay);
        }
        
        // Display all tile data
        dataDisplay.innerHTML = `
            <div class="tile-info" style="padding: 10px; background-color: rgba(255, 255, 255, 0.9); border-radius: 5px; margin-top: 10px; color: #333;">
                <p><strong>ID:</strong> ${tile.id || 'N/A'}</p>
                <p><strong>Name:</strong> ${tile.name || 'N/A'}</p>
                <p><strong>Category:</strong> ${tile.category || 'N/A'}</p>
                <p><strong>Color:</strong> ${tile.color || 'N/A'}</p>
                <p><strong>Title:</strong> ${tile.title || 'N/A'}</p>
                <p><strong>Description:</strong> ${tile.description || 'N/A'}</p>
                <p><strong>Metrics:</strong> ${tile.metrics ? JSON.stringify(tile.metrics, null, 2) : 'N/A'}</p>
                <p><strong>Created At:</strong> ${tile.created_at ? new Date(tile.created_at).toLocaleString() : 'N/A'}</p>
                <p><strong>Updated At:</strong> ${tile.updated_at ? new Date(tile.updated_at).toLocaleString() : 'N/A'}</p>
            </div>
        `;
        
        // Add update timestamp
        const timestamp = document.createElement('div');
        timestamp.style.fontSize = '10px';
        timestamp.style.color = '#666';
        timestamp.style.marginTop = '5px';
        timestamp.textContent = `Last updated: ${new Date().toLocaleString()}`;
        dataDisplay.appendChild(timestamp);
    }
}

// Update tiles when the page loads
document.addEventListener('DOMContentLoaded', updateTileData);

// Update tiles every 5 seconds
setInterval(updateTileData, 5000);