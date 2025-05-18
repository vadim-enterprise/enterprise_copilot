@app.post("/api/tiles/load-data")
async def load_tile_data():
    """Load data from company_info.json into tile_analytics table"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Drop and recreate tile_analytics table to ensure correct schema
        cur.execute("DROP TABLE IF EXISTS tile_analytics;")
        cur.execute("""
            CREATE TABLE tile_analytics (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                category VARCHAR(50) NOT NULL,
                color VARCHAR(20) NOT NULL,
                title VARCHAR(255) NOT NULL,
                description TEXT,
                metrics JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Load data from company_info.json
        company_info_path = Path(__file__).resolve().parent / 'data' / 'company_info.json'
        logger.info(f"Looking for company_info.json at: {company_info_path}")
        
        if company_info_path.exists():
            logger.info("Found company_info.json, loading data...")
            with open(company_info_path, 'r') as f:
                company_info = json.load(f)
                companies = company_info.get('companies', [])
                logger.info(f"Loaded company info with {len(companies)} companies")
                logger.info(f"Raw company info content: {json.dumps(company_info, indent=2)}")
            
            # Insert data for each company
            for company in companies:
                name = company.get('name')
                metrics = company.get('metrics', {})
                logger.info(f"\nProcessing company: {name}")
                logger.info(f"Raw metrics: {json.dumps(metrics, indent=2)}")
                logger.info(f"Available metric keys: {list(metrics.keys())}")
                
                # Check for high churn risk
                churn_risk = metrics.get('churn_Rate')
                logger.info(f"Raw churn risk value: {churn_risk}")
                logger.info(f"Churn risk for {name}: {churn_risk} (type: {type(churn_risk)})")
                if churn_risk is not None:
                    try:
                        # Try to handle string percentage format
                        if isinstance(churn_risk, str) and '%' in churn_risk:
                            churn_risk = float(churn_risk.strip('%')) / 100
                        else:
                            churn_risk = float(churn_risk)
                        logger.info(f"Converted churn risk to float: {churn_risk}")
                        if churn_risk > 0.1:  # High churn risk threshold
                            logger.info(f"Creating churn risk tile for {name} with risk {churn_risk}")
                            try:
                                metrics_data = {
                                    'churn_risk': churn_risk,
                                    'customer_satisfaction': metrics.get('customer_Satisfaction'),
                                    'last_activity': metrics.get('last_Activity')
                                }
                                logger.info(f"Metrics data for insertion: {json.dumps(metrics_data, indent=2)}")
                                
                                cur.execute("""
                                    INSERT INTO tile_analytics 
                                    (analysis_type, metrics, results)
                                    VALUES (%s, %s, %s)
                                """, (
                                    'churn_risk',
                                    json.dumps(metrics_data),
                                    json.dumps({
                                        'name': name,
                                        'description': f'Churn risk is {churn_risk:.1%}. Immediate attention required.'
                                    })
                                ))
                                logger.info(f"Successfully inserted churn risk tile for {name}")
                            except Exception as e:
                                logger.error(f"Error inserting churn risk tile for {name}: {str(e)}")
                                raise
                    except ValueError as e:
                        logger.error(f"Error converting churn risk to float: {str(e)}")
                
                # Check for growth opportunities
                growth_rate = metrics.get('growth_Rate')
                logger.info(f"Raw growth rate value: {growth_rate}")
                logger.info(f"Growth rate for {name}: {growth_rate} (type: {type(growth_rate)})")
                if growth_rate is not None:
                    try:
                        # Try to handle string percentage format
                        if isinstance(growth_rate, str) and '%' in growth_rate:
                            growth_rate = float(growth_rate.strip('%')) / 100
                        else:
                            growth_rate = float(growth_rate)
                        logger.info(f"Converted growth rate to float: {growth_rate}")
                        if growth_rate > 0.1:  # High growth threshold
                            logger.info(f"Creating growth opportunity tile for {name} with rate {growth_rate}")
                            try:
                                metrics_data = {
                                    'growth_rate': growth_rate,
                                    'revenue': metrics.get('revenue'),
                                    'market_share': metrics.get('market_Share')
                                }
                                logger.info(f"Metrics data for insertion: {json.dumps(metrics_data, indent=2)}")
                                
                                cur.execute("""
                                    INSERT INTO tile_analytics 
                                    (analysis_type, metrics, results)
                                    VALUES (%s, %s, %s)
                                """, (
                                    'growth_opportunity',
                                    json.dumps(metrics_data),
                                    json.dumps({
                                        'name': name,
                                        'description': f'Growth rate is {growth_rate:.1%}. Consider expansion strategies.'
                                    })
                                ))
                                logger.info(f"Successfully inserted growth opportunity tile for {name}")
                            except Exception as e:
                                logger.error(f"Error inserting growth opportunity tile for {name}: {str(e)}")
                                raise
                    except ValueError as e:
                        logger.error(f"Error converting growth rate to float: {str(e)}")
                
                # Check for engagement opportunities
                engagement_score = metrics.get('engagement_Score')
                logger.info(f"Raw engagement score value: {engagement_score}")
                logger.info(f"Engagement score for {name}: {engagement_score} (type: {type(engagement_score)})")
                if engagement_score is not None:
                    try:
                        # Try to handle string percentage format
                        if isinstance(engagement_score, str) and '%' in engagement_score:
                            engagement_score = float(engagement_score.strip('%')) / 100
                        else:
                            engagement_score = float(engagement_score)
                        logger.info(f"Converted engagement score to float: {engagement_score}")
                        if engagement_score < 0.7:  # Low engagement threshold
                            logger.info(f"Creating engagement tile for {name} with score {engagement_score}")
                            try:
                                metrics_data = {
                                    'engagement_score': engagement_score,
                                    'feature_usage': metrics.get('feature_Usage'),
                                    'last_interaction': metrics.get('last_Interaction')
                                }
                                logger.info(f"Metrics data for insertion: {json.dumps(metrics_data, indent=2)}")
                                
                                cur.execute("""
                                    INSERT INTO tile_analytics 
                                    (analysis_type, metrics, results)
                                    VALUES (%s, %s, %s)
                                """, (
                                    'engagement_risk',
                                    json.dumps(metrics_data),
                                    json.dumps({
                                        'name': name,
                                        'description': f'Engagement score is {engagement_score:.1%}. Consider engagement initiatives.'
                                    })
                                ))
                                logger.info(f"Successfully inserted engagement tile for {name}")
                            except Exception as e:
                                logger.error(f"Error inserting engagement tile for {name}: {str(e)}")
                                raise
                    except ValueError as e:
                        logger.error(f"Error converting engagement score to float: {str(e)}")
        else:
            logger.error(f"company_info.json not found at {company_info_path}")
            raise HTTPException(status_code=404, detail="company_info.json not found")
        
        # Commit the transaction
        conn.commit()
        cur.close()
        conn.close()
        
        return {"status": "success", "message": "Data loaded successfully into tile_analytics"}
    except Exception as e:
        logger.error(f"Error loading tile data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))



            # Create tile_data table
            subprocess.run([
                'psql',
                '-h', 'localhost',
                '-p', '5540',
                'pred_genai',
                '-c', """
                CREATE TABLE IF NOT EXISTS tile_data (
                    id SERIAL PRIMARY KEY,
                    tile_name VARCHAR(100) NOT NULL,
                    notification_type TEXT,
                    motion TEXT,
                    customer TEXT,
                    issue TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
                
                -- Create trigger to update updated_at timestamp
                CREATE OR REPLACE FUNCTION update_updated_at_column()
                RETURNS TRIGGER AS $$
                BEGIN
                    NEW.updated_at = CURRENT_TIMESTAMP;
                    RETURN NEW;
                END;
                $$ language 'plpgsql';
                
                DROP TRIGGER IF EXISTS update_tile_data_updated_at ON tile_data;
                CREATE TRIGGER update_tile_data_updated_at
                    BEFORE UPDATE ON tile_data
                    FOR EACH ROW
                    EXECUTE FUNCTION update_updated_at_column();
                
                -- Clear existing data
                TRUNCATE TABLE tile_data RESTART IDENTITY;
                
                -- Insert initial data for 12 tiles
                INSERT INTO tile_data (tile_name) VALUES
                    ('Churn Analysis'),
                    ('Competitor Analysis'),
                    ('Market Share'),
                    ('Sales Performance'),
                    ('Customer Satisfaction'),
                    ('Growth Opportunities'),
                    ('Revenue Analysis'),
                    ('Product Performance'),
                    ('Customer Demographics'),
                    ('Market Trends'),
                    ('Regional Analysis'),
                    ('Competitive Landscape');
                """
            ], check=True, capture_output=True)
            logger.info("Created tile_data table and inserted initial data")


@app.post("/api/files/upload-csv")
async def upload_csv(file: UploadFile = File(...)):
    """
    Upload a CSV file, store it in PostgreSQL, and process it with analytics
    
    Args:
        file: The uploaded CSV file
        
    Returns:
        JSON response with processing results
    """
    try:
        logger.info(f"Received file upload: {file.filename}")
        
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as temp_file:
            # Copy the uploaded file to the temporary file
            shutil.copyfileobj(file.file, temp_file)
            temp_file_path = temp_file.name
        
        # Read the CSV file
        df = pd.read_csv(temp_file_path)
        logger.info(f"Successfully read CSV with {len(df)} rows and columns: {df.columns.tolist()}")
        
        # Generate a unique table name based on the file name and timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        table_name = f"csv_data_{os.path.splitext(file.filename)[0]}_{timestamp}"
        table_name = table_name.lower().replace('-', '_').replace(' ', '_')
        logger.info(f"Generated table name: {table_name}")
        
        # Store the data in PostgreSQL
        try:
            df.to_sql(table_name, engine, if_exists='replace', index=False)
            logger.info(f"Successfully created table {table_name} in PostgreSQL")
        except Exception as e:
            logger.error(f"Error creating table in PostgreSQL: {str(e)}")
            raise
        
        # Create a metadata entry for the uploaded file
        try:
            with engine.connect() as conn:
                # Check if csv_metadata table exists
                result = conn.execute(text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'csv_metadata'
                    );
                """))
                if not result.scalar():
                    logger.info("Creating csv_metadata table")
                    conn.execute(text("""
                        CREATE TABLE csv_metadata (
                            id SERIAL PRIMARY KEY,
                            table_name VARCHAR(255) NOT NULL,
                            original_filename VARCHAR(255) NOT NULL,
                            upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            column_names TEXT[] NOT NULL,
                            row_count INTEGER NOT NULL
                        )
                    """))
                
                conn.execute(text("""
                    INSERT INTO csv_metadata (table_name, original_filename, column_names, row_count)
                    VALUES (:table_name, :filename, :columns, :row_count)
                """), {
                    'table_name': table_name,
                    'filename': file.filename,
                    'columns': df.columns.tolist(),
                    'row_count': len(df)
                })
                conn.commit()
                logger.info("Successfully inserted metadata")
        except Exception as e:
            logger.error(f"Error handling metadata: {str(e)}")
            raise
        
        # Process the data with analytics service and populate company_info.json
        try:
            result = analytics_service.handle_csv_upload(temp_file_path)
            logger.info(f"Analytics processing complete: {result.get('success', False)}")
            
            # After company_info.json is populated, load data into tile_analytics
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            try:
                # Drop and recreate tile_analytics table to ensure correct schema
                cur.execute("DROP TABLE IF EXISTS tile_analytics;")
                logger.info("Dropped existing tile_analytics table")
                
                cur.execute("""
                    CREATE TABLE tile_analytics (
                        id SERIAL PRIMARY KEY,
                        analysis_type VARCHAR(50) NOT NULL,
                        metrics JSONB,
                        results JSONB,
                        model_performance JSONB,
                        feature_importance JSONB,
                        predictions JSONB,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                logger.info("Created new tile_analytics table")
                
                # Load data from company_info.json
                company_info_path = Path(__file__).resolve().parent / 'data' / 'company_info.json'
                logger.info(f"Looking for company_info.json at: {company_info_path}")
                
                if company_info_path.exists():
                    logger.info("Found company_info.json, loading data...")
                    with open(company_info_path, 'r') as f:
                        company_info = json.load(f)
                        companies = company_info.get('companies', [])
                        logger.info(f"Loaded company info with {len(companies)} companies")
                        logger.info(f"Raw company info content: {json.dumps(company_info, indent=2)}")
                    
                    # Insert data for each company
                    for company in companies:
                        name = company.get('name')
                        metrics = company.get('metrics', {})
                        logger.info(f"\nProcessing company: {name}")
                        logger.info(f"Raw metrics: {json.dumps(metrics, indent=2)}")
                        logger.info(f"Available metric keys: {list(metrics.keys())}")
                        
                        # Check for high churn risk
                        churn_risk = metrics.get('churn_rate')
                        logger.info(f"Raw churn risk value: {churn_risk}")
                        logger.info(f"Churn risk for {name}: {churn_risk} (type: {type(churn_risk)})")
                        if churn_risk is not None:
                            try:
                                # Try to handle string percentage format
                                if isinstance(churn_risk, str) and '%' in churn_risk:
                                    churn_risk = float(churn_risk.strip('%')) / 100
                                else:
                                    churn_risk = float(churn_risk)
                                logger.info(f"Converted churn risk to float: {churn_risk}")
                                if churn_risk > 0.1:  # High churn risk threshold
                                    logger.info(f"Creating churn risk tile for {name} with risk {churn_risk}")
                                    try:
                                        metrics_data = {
                                            'churn_risk': churn_risk,
                                            'customer_satisfaction': metrics.get('customer_Satisfaction'),
                                            'last_activity': metrics.get('last_Activity')
                                        }
                                        logger.info(f"Metrics data for insertion: {json.dumps(metrics_data, indent=2)}")
                                        
                                        cur.execute("""
                                            INSERT INTO tile_analytics 
                                            (analysis_type, metrics, results)
                                            VALUES (%s, %s, %s)
                                        """, (
                                            'churn_risk',
                                            json.dumps(metrics_data),
                                            json.dumps({
                                                'name': name,
                                                'description': f'Churn risk is {churn_risk:.1%}. Immediate attention required.'
                                            })
                                        ))
                                        logger.info(f"Successfully inserted churn risk tile for {name}")
                                    except Exception as e:
                                        logger.error(f"Error inserting churn risk tile for {name}: {str(e)}")
                                        raise
                            except ValueError as e:
                                logger.error(f"Error converting churn risk to float: {str(e)}")
                        
                        # Check for growth opportunities
                        growth_rate = metrics.get('growth_rate')
                        logger.info(f"Raw growth rate value: {growth_rate}")
                        logger.info(f"Growth rate for {name}: {growth_rate} (type: {type(growth_rate)})")
                        if growth_rate is not None:
                            try:
                                # Try to handle string percentage format
                                if isinstance(growth_rate, str) and '%' in growth_rate:
                                    growth_rate = float(growth_rate.strip('%')) / 100
                                else:
                                    growth_rate = float(growth_rate)
                                logger.info(f"Converted growth rate to float: {growth_rate}")
                                if growth_rate > 0.1:  # High growth threshold
                                    logger.info(f"Creating growth opportunity tile for {name} with rate {growth_rate}")
                                    try:
                                        metrics_data = {
                                            'growth_rate': growth_rate,
                                            'revenue': metrics.get('revenue'),
                                            'market_share': metrics.get('market_Share')
                                        }
                                        logger.info(f"Metrics data for insertion: {json.dumps(metrics_data, indent=2)}")
                                        
                                        cur.execute("""
                                            INSERT INTO tile_analytics 
                                            (analysis_type, metrics, results)
                                            VALUES (%s, %s, %s)
                                        """, (
                                            'growth_opportunity',
                                            json.dumps(metrics_data),
                                            json.dumps({
                                                'name': name,
                                                'description': f'Growth rate is {growth_rate:.1%}. Consider expansion strategies.'
                                            })
                                        ))
                                        logger.info(f"Successfully inserted growth opportunity tile for {name}")
                                    except Exception as e:
                                        logger.error(f"Error inserting growth opportunity tile for {name}: {str(e)}")
                                        raise
                            except ValueError as e:
                                logger.error(f"Error converting growth rate to float: {str(e)}")
                        
                        # Check for engagement opportunities
                        engagement_score = metrics.get('engagement_Score')
                        logger.info(f"Raw engagement score value: {engagement_score}")
                        logger.info(f"Engagement score for {name}: {engagement_score} (type: {type(engagement_score)})")
                        if engagement_score is not None:
                            try:
                                # Try to handle string percentage format
                                if isinstance(engagement_score, str) and '%' in engagement_score:
                                    engagement_score = float(engagement_score.strip('%')) / 100
                                else:
                                    engagement_score = float(engagement_score)
                                logger.info(f"Converted engagement score to float: {engagement_score}")
                                if engagement_score < 0.7:  # Low engagement threshold
                                    logger.info(f"Creating engagement tile for {name} with score {engagement_score}")
                                    try:
                                        metrics_data = {
                                            'engagement_score': engagement_score,
                                            'feature_usage': metrics.get('feature_Usage'),
                                            'last_interaction': metrics.get('last_Interaction')
                                        }
                                        logger.info(f"Metrics data for insertion: {json.dumps(metrics_data, indent=2)}")
                                        
                                        cur.execute("""
                                            INSERT INTO tile_analytics 
                                            (analysis_type, metrics, results)
                                            VALUES (%s, %s, %s)
                                        """, (
                                            'engagement_risk',
                                            json.dumps(metrics_data),
                                            json.dumps({
                                                'name': name,
                                                'description': f'Engagement score is {engagement_score:.1%}. Consider engagement initiatives.'
                                            })
                                        ))
                                        logger.info(f"Successfully inserted engagement tile for {name}")
                                    except Exception as e:
                                        logger.error(f"Error inserting engagement tile for {name}: {str(e)}")
                                        raise
                            except ValueError as e:
                                logger.error(f"Error converting engagement score to float: {str(e)}")
                else:
                    logger.error(f"company_info.json not found at {company_info_path}")
                    raise HTTPException(status_code=404, detail="company_info.json not found")
                
                # Commit the transaction
                conn.commit()
                logger.info("Committed all tile_analytics changes")
                
                # Verify the data was inserted
                cur.execute("SELECT COUNT(*) as count FROM tile_analytics")
                count = cur.fetchone()['count']
                logger.info(f"Verified {count} rows in tile_analytics table")
                
                # Log all inserted rows for verification
                cur.execute("SELECT * FROM tile_analytics")
                rows = cur.fetchall()
                logger.info(f"All rows in tile_analytics: {json.dumps([dict(row) for row in rows], indent=2)}")
                
            except Exception as e:
                conn.rollback()
                logger.error(f"Error during tile_analytics operations: {str(e)}")
                raise
            finally:
                cur.close()
                conn.close()
                logger.info("Closed database connection")
            
        except Exception as e:
            logger.error(f"Error processing data with analytics service: {str(e)}")
            # Don't raise here, as the file was successfully uploaded
            result = {"success": False, "message": f"Error in analytics processing: {str(e)}"}
        
        # Clean up the temporary file
        os.unlink(temp_file_path)
        
        return JSONResponse(
            status_code=200,
            content={
                "message": "File uploaded and processed successfully",
                "table_name": table_name,
                "row_count": len(df),
                "columns": df.columns.tolist(),
                "analytics_result": result,
                "should_refresh": True  # Indicate that the UI should refresh to show new tiles
            }
        )
        
    except Exception as e:
        logger.error(f"Error processing CSV file: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))




    def process_websearch_query(self, query: str) -> Dict[str, Any]:
        """
        Process a websearch query to determine if it's analytics-related
        
        Args:
            query: The websearch query string
            
        Returns:
            Dictionary with processing results
        """
        query_lower = query.lower()
        
        # Check if the query is analytics-related
        analytics_keywords = [
            'analyze', 'analysis', 'analytics', 'statistics', 'stats',
            'anomaly', 'anomalies', 'clustering', 'cluster', 'forecast',
            'time series', 'trend', 'prediction', 'predict', 'model'
        ]
        
        is_analytics_query = any(keyword in query_lower for keyword in analytics_keywords)
        
        if not is_analytics_query:
            return {
                "is_analytics_query": False,
                "message": "Not an analytics-related query"
            }
        
        # Extract table name if specified
        table_pattern = r'(?:table|data|dataset)\s+[\'"]?([a-zA-Z0-9_]+)[\'"]?'
        table_match = re.search(table_pattern, query_lower)
        table_name = table_match.group(1) if table_match else None
        
        # Run the appropriate analysis
        try:
            # Get the data
            data = self._get_relevant_data(query)
            
            if data.empty:
                return {
                    "is_analytics_query": True,
                    "success": False,
                    "message": f"No data found{' for table ' + table_name if table_name else ''}"
                }
            
            # Log the columns we have
            self.logger.info(f"Data columns: {data.columns.tolist()}")
            
            # Extract analysis type if specified
            analysis_type = None
            if 'anomaly' in query_lower or 'anomalies' in query_lower:
                analysis_type = 'anomaly'
            elif 'cluster' in query_lower:
                analysis_type = 'clustering'
            elif 'time series' in query_lower or 'trend' in query_lower or 'forecast' in query_lower:
                analysis_type = 'time_series'
            
            # Run the specific analysis
            if analysis_type:
                if analysis_type == 'anomaly':
                    numeric_cols = data.select_dtypes(include=['number']).columns.tolist()
                    results = self.run_anomaly_detection(data, numeric_cols)
                elif analysis_type == 'clustering':
                    numeric_cols = data.select_dtypes(include=['number']).columns.tolist()
                    results = self.run_clustering_analysis(data, numeric_cols)
                elif analysis_type == 'time_series':
                    # Find timestamp and numeric columns
                    timestamp_cols = [col for col in data.columns if 'date' in col.lower() or 'time' in col.lower()]
                    numeric_cols = data.select_dtypes(include=['number']).columns.tolist()
                    
                    if timestamp_cols and numeric_cols:
                        results = self.run_time_series_analysis(data, timestamp_cols[0], numeric_cols[0])
                    else:
                        return {
                            "is_analytics_query": True,
                            "success": False,
                            "message": "Could not find appropriate timestamp and numeric columns for time series analysis"
                        }

            return {
                "is_analytics_query": True,
                "success": True,
                "analysis_type": analysis_type,
                "results": results
            }
        except Exception as e:
            logger.error(f"Error processing analytics query: {str(e)}")
            return {
                "is_analytics_query": True,
                "success": False,
                "message": f"Error processing analytics query: {str(e)}"
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
        console.log('Received tile data:', data);
        
        // Check if data and data.tiles exist
        if (!data || !data.tiles || !Array.isArray(data.tiles)) {
            console.error('Invalid data format received:', data);
            return;
        }
        
        // Log all available tile names for debugging
        console.log("All available tiles in the database:");
        data.tiles.forEach(tile => {
            console.log(`- "${tile.name}" (${tile.category})`);
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
            if (tileMap.hasOwnProperty(tile.name)) {
                tileMap[tile.name] = tile;
                console.log(`Direct match found for: "${tile.name}"`);
            } else {
                console.log(`No direct match for tile: "${tile.name}"`);
                
                // Try case-insensitive match
                let foundMatch = false;
                Object.keys(tileMap).forEach(headerText => {
                    if (headerText.toLowerCase() === tile.name.toLowerCase()) {
                        tileMap[headerText] = tile;
                        console.log(`Case-insensitive match found: "${headerText}" = "${tile.name}"`);
                        foundMatch = true;
                    }
                });
                
                if (!foundMatch) {
                    console.log(`Warning: No match found for tile "${tile.name}" with any header`);
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
                const matchingTile = data.tiles.find(t => t.name === correctedHeader);
                if (matchingTile) {
                    console.log(`Found matching tile for "${headerText}": ${matchingTile.name}`);
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
    if (!header) {
        console.error('No header element provided');
        return;
    }
    
    const tileContainer = header.closest('.map-section');
    if (!tileContainer) {
        console.error('No tile container found');
        return;
    }
    
    console.log(`Updating tile content for: ${tile.name}`);
    
    // Set color based on color field
    let tileColor = '#ffffff'; // Default white
    switch(tile.color) {
        case 'red':
            tileColor = '#ff5252'; // Red
            break;
        case 'yellow':
            tileColor = '#ffb142'; // Orange
            break;
        case 'blue':
            tileColor = '#54a0ff'; // Blue
            break;
        case 'green':
            tileColor = '#2ed573'; // Green
            break;
        default:
            console.log(`Unknown color: ${tile.color}, using default color`);
    }
    
    // Apply the color to the tile container
    tileContainer.style.backgroundColor = tileColor;
    
    // Set text color for better contrast
    tileContainer.style.color = (tile.color === 'red' || tile.color === 'yellow') 
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
        
        // Display the tile data
        dataDisplay.innerHTML = `
            <div class="tile-info" style="padding: 10px; background-color: rgba(255, 255, 255, 0.9); border-radius: 5px; margin-top: 10px; color: #333;">
                <p><strong>Category:</strong> ${tile.category || 'N/A'}</p>
                <p><strong>Title:</strong> ${tile.title || 'N/A'}</p>
                <p><strong>Description:</strong> ${tile.description || 'N/A'}</p>
                ${tile.metrics ? `<p><strong>Metrics:</strong> ${JSON.stringify(tile.metrics)}</p>` : ''}
            </div>
        `;
        
        // Add update timestamp
        const timestamp = document.createElement('div');
        timestamp.style.fontSize = '10px';
        timestamp.style.color = '#666';
        timestamp.style.marginTop = '5px';
        timestamp.textContent = `Last updated: ${new Date(tile.updated_at).toLocaleString()}`;
        dataDisplay.appendChild(timestamp);
    }
}

// Update tiles when the page loads
document.addEventListener('DOMContentLoaded', updateTileData);

// Update tiles every 5 seconds
setInterval(updateTileData, 5000); 



# def ensure_tile_postgres_running():
#     """Ensure PostgreSQL is running on port 5541 for tile analytics"""
#     # Check if port is in use and kill any process using it
#     if is_port_in_use(5541):
#         logger.info("Port 5541 is already in use. Stopping existing PostgreSQL instance...")
#         kill_process_on_port(5541)
#         # Wait for the port to be released
#         max_retries = 10
#         for i in range(max_retries):
#             if not is_port_in_use(5541):
#                 logger.info("Port 5541 is now available.")
#                 break
#             logger.info(f"Waiting for port 5541 to be released... ({i+1}/{max_retries})")
#             time.sleep(1)
#         else:
#             logger.error("Could not free up port 5541. Please check for running processes manually.")
#             return False

#     logger.info("Starting PostgreSQL on port 5541...")
#     try:
#         # Create data directory if it doesn't exist
#         data_dir = BASE_DIR / 'postgres_tile_data'
#         if data_dir.exists():
#             logger.info("Removing existing PostgreSQL data directory...")
#             import shutil
#             shutil.rmtree(str(data_dir), ignore_errors=True)
#         data_dir.mkdir(exist_ok=True)

#         # Initialize database
#         logger.info("Initializing PostgreSQL database for tiles...")
#         subprocess.run([
#             'initdb',
#             '-D', str(data_dir),
#             '--auth=trust'
#         ], check=True)

#         # Configure PostgreSQL to allow local connections
#         pg_hba_conf = data_dir / 'pg_hba.conf'
#         with open(pg_hba_conf, 'w') as f:
#             f.write("""# TYPE  DATABASE        USER            ADDRESS                 METHOD
# local   all             all                                     trust
# host    all             all             127.0.0.1/32            trust
# host    all             all             ::1/128                 trust
# """)

#         # Configure PostgreSQL to listen on localhost
#         postgresql_conf = data_dir / 'postgresql.conf'
#         with open(postgresql_conf, 'w') as f:
#             f.write("""# Basic PostgreSQL configuration
# listen_addresses = 'localhost'
# port = 5541
# max_connections = 100
# shared_buffers = 128MB
# dynamic_shared_memory_type = posix
# max_wal_size = 1GB
# min_wal_size = 80MB
# """)

#         # Start PostgreSQL
#         postgres_process = subprocess.Popen([
#             'postgres',
#             '-D', str(data_dir),
#             '-p', '5541',
#             '-c', 'listen_addresses=localhost'
#         ])

#         # Wait for PostgreSQL to start
#         max_retries = 30
#         for i in range(max_retries):
#             if is_port_in_use(5541):
#                 logger.info("PostgreSQL started successfully on port 5541")
#                 break
#             logger.info(f"Waiting for PostgreSQL to start... ({i+1}/{max_retries})")
#             time.sleep(1)
#         else:
#             logger.error("Failed to start PostgreSQL on port 5541")
#             return False

#         # Wait for PostgreSQL to be ready for connections
#         max_retries = 30
#         for i in range(max_retries):
#             try:
#                 result = subprocess.run([
#                     'psql',
#                     '-h', 'localhost',
#                     '-p', '5541',
#                     'postgres',
#                     '-c', 'SELECT 1;'
#                 ], check=True, capture_output=True, text=True)
#                 logger.info("PostgreSQL is ready for connections")
#                 break
#             except subprocess.CalledProcessError:
#                 if i == max_retries - 1:
#                     logger.error("PostgreSQL failed to become ready for connections")
#                     return False
#                 time.sleep(1)

#         # Create database and tables
#         try:
#             logger.info("Creating database tile_analytics...")
            
#             # Create the database
#             subprocess.run([
#                 'psql',
#                 '-h', 'localhost',
#                 '-p', '5541',
#                 'postgres',
#                 '-c', 'CREATE DATABASE tile_analytics;'
#             ], check=True, capture_output=True)
#             logger.info("Created database tile_analytics")

#             # Grant ownership
#             subprocess.run([
#                 'psql',
#                 '-h', 'localhost',
#                 '-p', '5541',
#                 'postgres',
#                 '-c', 'ALTER DATABASE tile_analytics OWNER TO glinskiyvadim;'
#             ], check=True, capture_output=True)
#             logger.info("Changed database ownership to glinskiyvadim")

#             # Create the tiles table
#             subprocess.run([
#                 'psql',
#                 '-h', 'localhost',
#                 '-p', '5541',
#                 'tile_analytics',
#                 '-c', """
#                 CREATE TABLE IF NOT EXISTS tile_data (
#                     id SERIAL PRIMARY KEY,
#                     tile_name VARCHAR(100) NOT NULL,
#                     notification_type TEXT,
#                     motion TEXT,
#                     customer TEXT,
#                     issue TEXT,
#                     created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
#                     updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
#                 );
                
#                 -- Create trigger to update updated_at timestamp
#                 CREATE OR REPLACE FUNCTION update_updated_at_column()
#                 RETURNS TRIGGER AS $$
#                 BEGIN
#                     NEW.updated_at = CURRENT_TIMESTAMP;
#                     RETURN NEW;
#                 END;
#                 $$ language 'plpgsql';
                
#                 DROP TRIGGER IF EXISTS update_tile_data_updated_at ON tile_data;
#                 CREATE TRIGGER update_tile_data_updated_at
#                     BEFORE UPDATE ON tile_data
#                     FOR EACH ROW
#                     EXECUTE FUNCTION update_updated_at_column();
                
#                 -- Clear existing data
#                 TRUNCATE TABLE tile_data RESTART IDENTITY;
                
#                 -- Insert initial data for 12 tiles
#                 INSERT INTO tile_data (tile_name) VALUES
#                     ('Churn Analysis'),
#                     ('Competitor Analysis'),
#                     ('Market Share'),
#                     ('Sales Performance'),
#                     ('Customer Satisfaction'),
#                     ('Growth Opportunities'),
#                     ('Revenue Analysis'),
#                     ('Product Performance'),
#                     ('Customer Demographics'),
#                     ('Market Trends'),
#                     ('Regional Analysis'),
#                     ('Competitive Landscape');
#                 """
#             ], check=True, capture_output=True)
#             logger.info("Created tile_data table and inserted initial data")

#             # Create tile_analytics table
#             subprocess.run([
#                 'psql',
#                 '-h', 'localhost',
#                 '-p', '5541',
#                 'tile_analytics',
#                 '-c', """
#                 CREATE TABLE IF NOT EXISTS tile_analytics (
#                     id SERIAL PRIMARY KEY,
#                     analysis_type VARCHAR(50) NOT NULL,
#                     analysis_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#                     metrics JSONB NOT NULL,
#                     results JSONB NOT NULL,
#                     model_performance JSONB,
#                     feature_importance JSONB,
#                     predictions JSONB
#                 );
#                 """
#             ], check=True, capture_output=True)
#             logger.info("Created tile_analytics table")

#             # Grant privileges
#             subprocess.run([
#                 'psql',
#                 '-h', 'localhost',
#                 '-p', '5541',
#                 'tile_analytics',
#                 '-c', 'GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO glinskiyvadim;'
#             ], check=True, capture_output=True)
            
#             subprocess.run([
#                 'psql',
#                 '-h', 'localhost',
#                 '-p', '5541',
#                 'tile_analytics',
#                 '-c', 'GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO glinskiyvadim;'
#             ], check=True, capture_output=True)
#             logger.info("Granted privileges to glinskiyvadim")

#             return True

#         except subprocess.CalledProcessError as e:
#             logger.error(f"Error creating/verifying database: {e.stderr if hasattr(e, 'stderr') else str(e)}")
#             return False

#     except Exception as e:
#         logger.error(f"Error starting PostgreSQL: {e}")
#         return False