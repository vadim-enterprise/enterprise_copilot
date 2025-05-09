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
        const data = await response.json();
        console.log('Received tile data:', data);
        
        // Log all available tile names for debugging
        console.log("All available tiles in the database:");
        data.tiles.forEach(tile => {
            console.log(`- "${tile.tile_name}" (${tile.notification_type})`);
        });
        
        // Find all map sections on the page
        const allMapSections = document.querySelectorAll('.map-section');
        console.log(`Found ${allMapSections.length} map sections on the page`);
        
        // Print HTML of all map sections for debugging
        console.log("*** HTML Structure of Map Sections ***");
        allMapSections.forEach((section, index) => {
            const header = section.querySelector('.map-section-header');
            console.log(`Section ${index + 1}: Header = "${header ? header.textContent.trim() : 'No header found'}"`);
            console.log(`Section HTML: ${section.outerHTML.substring(0, 200)}...`);
        });
        
        // Log all section headers for comparison
        console.log("All map section headers on the page:");
        const allHeaders = document.querySelectorAll('.map-section-header');
        allHeaders.forEach((header, index) => {
            console.log(`- ${index + 1}: "${header.textContent.trim()}"`);
        });
        
        // Force exact matches with a map for debugging
        console.log("Creating a direct mapping between headers and tiles");
        const tileMap = {};
        
        // First pass: Collect all header texts
        allHeaders.forEach(header => {
            tileMap[header.textContent.trim()] = null;
        });
        
        console.log("Current header map:", Object.keys(tileMap));
        
        // Second pass: Try to match tiles to headers
        data.tiles.forEach(tile => {
            // Exact match
            if (tileMap.hasOwnProperty(tile.tile_name)) {
                tileMap[tile.tile_name] = tile;
                console.log(`Direct match found for: "${tile.tile_name}"`);
            } else {
                console.log(`No direct match for tile: "${tile.tile_name}"`);
                
                // Try case-insensitive match
                let foundMatch = false;
                Object.keys(tileMap).forEach(headerText => {
                    if (headerText.toLowerCase() === tile.tile_name.toLowerCase()) {
                        tileMap[headerText] = tile;
                        console.log(`Case-insensitive match found: "${headerText}" = "${tile.tile_name}"`);
                        foundMatch = true;
                    }
                });
                
                if (!foundMatch) {
                    console.log(`Warning: No match found for tile "${tile.tile_name}" with any header`);
                }
            }
        });
        
        console.log("Final tile mapping:", tileMap);
        
        // Manually create a corrective mapping for known header issues
        const correctionMap = {
            "Churn Analysis": "Churn Analysis",
            "Competitor Analysis": "Competitor Analysis",
            "Market Share": "Market Share",
            "Sales Performance": "Sales Performance",
            "Customer Satisfaction": "Customer Satisfaction",
            "Growth Opportunities": "Growth Opportunities",
            "Revenue Analysis": "Revenue Analysis",
            "Product Performance": "Product Performance",
            "Customer Demographics": "Customer Demographics",
            "Market Trends": "Market Trends",
            "Regional Analysis": "Regional Analysis",
            "Competitive Landscape": "Competitive Landscape"
        };
        
        // Update each tile with its data using the correction map
        allHeaders.forEach(header => {
            const headerText = header.textContent.trim();
            console.log(`Processing header: "${headerText}"`);
            
            // Check if we have a correction mapping
            const correctedHeader = correctionMap[headerText];
            if (correctedHeader) {
                console.log(`Using corrected header: "${correctedHeader}"`);
                
                // Find the matching tile
                const matchingTile = data.tiles.find(t => t.tile_name === correctedHeader);
                if (matchingTile) {
                    console.log(`Found matching tile for "${headerText}": ${matchingTile.tile_name}`);
                    updateTileContent(header, matchingTile);
                } else {
                    console.warn(`No matching tile found for corrected header: "${correctedHeader}"`);
                }
            } else {
                console.warn(`No correction mapping for header: "${headerText}"`);
            }
        });
    } catch (error) {
        console.error('Error fetching tile data:', error);
    }
}

// Helper function to update the tile content
function updateTileContent(header, tile) {
    const tileContainer = header.closest('.map-section');
    if (tileContainer) {
        // Set color based on notification type
        let tileColor = '#ffffff'; // Default white
        switch(tile.notification_type) {
            case 'Alert':
                tileColor = '#ff5252'; // Red
                console.log(`Setting Alert color (${tileColor}) for ${tile.tile_name}`);
                break;
            case 'Warning':
                tileColor = '#ffb142'; // Orange
                console.log(`Setting Warning color (${tileColor}) for ${tile.tile_name}`);
                break;
            case 'Info':
                tileColor = '#54a0ff'; // Blue
                console.log(`Setting Info color (${tileColor}) for ${tile.tile_name}`);
                break;
            case 'Good News':
                tileColor = '#2ed573'; // Green
                console.log(`Setting Good News color (${tileColor}) for ${tile.tile_name}`);
                break;
            default:
                console.log(`Unknown notification type: ${tile.notification_type}, using default color for ${tile.tile_name}`);
        }
        
        // Apply the color to the tile container (with !important to override any other styles)
        console.log(`Applying background color ${tileColor} to tile ${tile.tile_name}`);
        tileContainer.setAttribute('style', `background-color: ${tileColor} !important`);
        
        // Also set text color for better contrast
        if (tile.notification_type === 'Alert' || tile.notification_type === 'Warning') {
            tileContainer.style.color = '#ffffff'; // White text for dark backgrounds
        } else {
            tileContainer.style.color = '#333333'; // Dark text for light backgrounds
        }
        
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
            
            // Display the tile data with a clear visual style
            dataDisplay.innerHTML = `
                <div class="tile-info" style="padding: 10px; background-color: rgba(255, 255, 255, 0.9); border-radius: 5px; margin-top: 10px; color: #333;">
                    <p><strong>Notification:</strong> ${tile.notification_type || 'N/A'}</p>
                    <p><strong>Motion:</strong> ${tile.motion || 'N/A'}</p>
                    <p><strong>Customer:</strong> ${tile.customer || 'N/A'}</p>
                    <p><strong>Issue:</strong> ${tile.issue || 'N/A'}</p>
                </div>
            `;
            
            // Add a debug marker to see which tiles were updated
            const debugMarker = document.createElement('div');
            debugMarker.style.position = 'absolute';
            debugMarker.style.top = '5px';
            debugMarker.style.right = '5px';
            debugMarker.style.padding = '2px 5px';
            debugMarker.style.backgroundColor = 'black';
            debugMarker.style.color = 'white';
            debugMarker.style.fontSize = '10px';
            debugMarker.style.borderRadius = '3px';
            debugMarker.textContent = 'Updated';
            tileContainer.style.position = 'relative';
            tileContainer.appendChild(debugMarker);
        } else {
            console.error(`Could not find content for tile ${tile.tile_name}`);
        }
    } else {
        console.error(`Could not find container for tile ${tile.tile_name}`);
    }
}

// Update tiles when the page loads
document.addEventListener('DOMContentLoaded', updateTileData);

// Update tiles every 30 seconds
setInterval(updateTileData, 30000); 