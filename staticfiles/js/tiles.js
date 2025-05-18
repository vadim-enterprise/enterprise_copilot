// Function to setup tile interactions
function setupTileInteractions() {
    const tiles = document.querySelectorAll('.map-section');
    const overlay = document.createElement('div');
    overlay.className = 'tile-overlay';
    document.body.appendChild(overlay);

    const closeButton = document.createElement('button');
    closeButton.className = 'close-tile';
    closeButton.innerHTML = '×';
    document.body.appendChild(closeButton);

    tiles.forEach(tile => {
        tile.addEventListener('click', () => {
            // Remove active class from all tiles
            tiles.forEach(t => t.classList.remove('active'));
            
            // Add active class to clicked tile
            tile.classList.add('active');
            overlay.classList.add('active');
            closeButton.classList.add('active');
        });
    });

    function closeActiveTile() {
        const activeTile = document.querySelector('.map-section.active');
        if (activeTile) {
            activeTile.classList.remove('active');
        }
        overlay.classList.remove('active');
        closeButton.classList.remove('active');
    }

    closeButton.addEventListener('click', closeActiveTile);
    overlay.addEventListener('click', closeActiveTile);
}

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
        console.log('Fetched tiles:', data);
        
        // Check if data and data.tiles exist
        if (!data || !data.tiles || !Array.isArray(data.tiles)) {
            console.error('Invalid data format received:', data);
            return;
        }

        // Loop through tiles 1-12 and populate with data
        for (let i = 1; i <= 12; i++) {
            const tileId = `tile-${i}`;
            const tileElement = document.getElementById(tileId);
            
            if (!tileElement) {
                console.error(`Tile element with ID ${tileId} not found`);
                continue;
            }

            // Get the corresponding tile data (if available)
            const tileData = data.tiles[i - 1] || null;
            
            if (tileData) {
                console.log(`Updating tile ${i} with data:`, tileData);
                
                // Set color based on notification_type and content
                let tileColor = '#1a1a2e'; // Default dark blue
                let textColor = '#e0e0e0'; // Default light gray
                let borderColor = '#2a2a3a'; // Default border color
                let glowColor = 'rgba(0, 0, 0, 0.2)'; // Default glow

                // Determine severity and type of information
                const isChurnRisk = tileData.issue?.toLowerCase().includes('churn') || 
                                  tileData.title?.toLowerCase().includes('churn');
                const isCustomerSatisfaction = tileData.issue?.toLowerCase().includes('satisfaction') || 
                                            tileData.title?.toLowerCase().includes('satisfaction');
                const isRevenue = tileData.issue?.toLowerCase().includes('revenue') || 
                                tileData.title?.toLowerCase().includes('revenue');
                const isGrowth = tileData.issue?.toLowerCase().includes('growth') || 
                               tileData.title?.toLowerCase().includes('growth');

                // Set colors based on severity and type
                if (isChurnRisk) {
                    tileColor = '#2d1b1b'; // Dark red
                    borderColor = '#3d2b2b';
                    glowColor = 'rgba(255, 0, 0, 0.1)';
                } else if (isCustomerSatisfaction) {
                    if (tileData.notification_type === 'Warning') {
                        tileColor = '#2d2b1b'; // Dark orange
                        borderColor = '#3d3b2b';
                        glowColor = 'rgba(255, 165, 0, 0.1)';
                    } else {
                        tileColor = '#1b2d1b'; // Dark green
                        borderColor = '#2b3d2b';
                        glowColor = 'rgba(0, 255, 0, 0.1)';
                    }
                } else if (isRevenue) {
                    if (tileData.notification_type === 'Good News') {
                        tileColor = '#1b2d2d'; // Dark teal
                        borderColor = '#2b3d3d';
                        glowColor = 'rgba(0, 255, 255, 0.1)';
                    } else {
                        tileColor = '#2d1b2d'; // Dark purple
                        borderColor = '#3d2b3d';
                        glowColor = 'rgba(255, 0, 255, 0.1)';
                    }
                } else if (isGrowth) {
                    tileColor = '#1b1b2d'; // Dark blue
                    borderColor = '#2b2b3d';
                    glowColor = 'rgba(0, 0, 255, 0.1)';
                }

                // Apply the colors and styles
                tileElement.style.backgroundColor = tileColor;
                tileElement.style.color = textColor;
                tileElement.style.border = `1px solid ${borderColor}`;
                tileElement.style.boxShadow = `0 0 15px ${glowColor}`;
                tileElement.style.transition = 'all 0.3s ease';
                
                // Update header
                const header = tileElement.querySelector('.map-section-header');
                if (header) {
                    header.textContent = tileData.title || tileData.name || 'Untitled';
                    header.style.borderBottom = `1px solid ${borderColor}`;
                }
                
                // Update content
                const content = tileElement.querySelector('.map-section-content');
                if (content) {
                    content.innerHTML = `
                        <div class="tile-data" style="background-color: rgba(26, 26, 46, 0.7); border-radius: 5px; margin-top: 10px;">
                            <div class="tile-info" style="padding: 10px; color: #e0e0e0;">
                                <p><strong>ID:</strong> ${tileData.id || 'N/A'}</p>
                                <p><strong>Name:</strong> ${tileData.name || 'N/A'}</p>
                                <p><strong>Category:</strong> ${tileData.category || 'N/A'}</p>
                                <p><strong>Title:</strong> ${tileData.title || 'N/A'}</p>
                                <p><strong>Description:</strong> ${tileData.description || 'N/A'}</p>
                                <p><strong>Company:</strong> ${tileData.customer || 'N/A'}</p>
                                <p><strong>Status:</strong> ${tileData.notification_type || 'N/A'}</p>
                                <p><strong>Issue:</strong> ${tileData.issue || 'N/A'}</p>
                                <p><strong>Motion:</strong> ${tileData.motion || 'N/A'}</p>
                                <p><strong>Metrics:</strong> ${tileData.metrics ? JSON.stringify(tileData.metrics, null, 2) : 'N/A'}</p>
                                <p><strong>Created At:</strong> ${tileData.created_at ? new Date(tileData.created_at).toLocaleString() : 'N/A'}</p>
                                <p><strong>Updated At:</strong> ${tileData.updated_at ? new Date(tileData.updated_at).toLocaleString() : 'N/A'}</p>
                            </div>
                            <div style="font-size: 10px; color: #888; margin-top: 5px; text-align: right;">
                                Last updated: ${new Date().toLocaleString()}
                            </div>
                        </div>
                    `;
                }
            } else {
                console.log(`No data available for tile ${i}`);
                // Clear the tile content if no data is available
                const header = tileElement.querySelector('.map-section-header');
                const content = tileElement.querySelector('.map-section-content');
                if (header) header.textContent = '';
                if (content) content.innerHTML = '';
                tileElement.style.backgroundColor = '#1a1a2e';
                tileElement.style.border = '1px solid #2a2a3a';
                tileElement.style.boxShadow = 'none';
            }
        }
    } catch (error) {
        console.error('Error fetching tile data:', error);
    }
}

// Initialize when the page loads
document.addEventListener('DOMContentLoaded', () => {
    setupTileInteractions();
    updateTileData();
});

// Update tiles every 5 seconds
setInterval(updateTileData, 5000);