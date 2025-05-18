# Plot a histogram to visualize the distribution of sensor readings
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

plt.hist(readings_array, bins='auto')
plt.title('Histogram of Sensor Readings')
plt.xlabel('Reading')
plt.ylabel('Frequency')
plt.show()

def generate_text_visualization(data, title="Data Visualization"):
    """
    Generate a text-based visualization of data
    
    Args:
        data: DataFrame or Series to visualize
        title: Title for the visualization
        
    Returns:
        String with text visualization
    """
    output = [f"=== {title} ===\n"]
    
    if isinstance(data, pd.Series):
        # For a Series, show basic statistics and a simple ASCII histogram
        stats = data.describe()
        output.append("Basic Statistics:")
        output.append(f"Count: {stats['count']}")
        output.append(f"Mean: {stats['mean']:.4f}")
        output.append(f"Std: {stats['std']:.4f}")
        output.append(f"Min: {stats['min']:.4f}")
        output.append(f"25%: {stats['25%']:.4f}")
        output.append(f"50%: {stats['50%']:.4f}")
        output.append(f"75%: {stats['75%']:.4f}")
        output.append(f"Max: {stats['max']:.4f}")
        
        # Generate a simple ASCII histogram
        output.append("\nDistribution:")
        hist, bins = np.histogram(data.dropna(), bins=10)
        max_count = max(hist)
        width = 40  # Width of the histogram
        
        for i, count in enumerate(hist):
            bar_length = int(count / max_count * width) if max_count > 0 else 0
            bar = '#' * bar_length
            output.append(f"{bins[i]:.2f} - {bins[i+1]:.2f} | {bar} ({count})")
            
    elif isinstance(data, pd.DataFrame):
        # For a DataFrame, show basic info and statistics for each column
        output.append(f"Shape: {data.shape[0]} rows x {data.shape[1]} columns")
        output.append(f"Columns: {', '.join(data.columns)}")
        
        # Show data types
        output.append("\nData Types:")
        for col, dtype in data.dtypes.items():
            output.append(f"{col}: {dtype}")
            
        # Show basic statistics for numeric columns
        numeric_cols = data.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) > 0:
            output.append("\nNumeric Column Statistics:")
            for col in numeric_cols:
                stats = data[col].describe()
                output.append(f"\n{col}:")
                output.append(f"  Count: {stats['count']}")
                output.append(f"  Mean: {stats['mean']:.4f}")
                output.append(f"  Std: {stats['std']:.4f}")
                output.append(f"  Min: {stats['min']:.4f}")
                output.append(f"  Max: {stats['max']:.4f}")
                
        # Show value counts for categorical columns (top 5)
        cat_cols = data.select_dtypes(include=['object']).columns
        if len(cat_cols) > 0:
            output.append("\nCategorical Column Value Counts (top 5):")
            for col in cat_cols:
                output.append(f"\n{col}:")
                value_counts = data[col].value_counts().head(5)
                for value, count in value_counts.items():
                    output.append(f"  {value}: {count}")
    else:
        output.append("Unsupported data type for visualization")
        
    return '\n'.join(output)

def visualize_correlation(df):
    """
    Generate a text-based visualization of correlation matrix
    
    Args:
        df: DataFrame with numeric columns
        
    Returns:
        String with correlation visualization
    """
    numeric_df = df.select_dtypes(include=[np.number])
    if numeric_df.empty:
        return "No numeric columns available for correlation analysis"
        
    corr_matrix = numeric_df.corr()
    
    output = ["=== Correlation Matrix ===\n"]
    
    # Format header row
    header = "       " + " ".join(f"{col[:7]:>8}" for col in corr_matrix.columns)
    output.append(header)
    
    # Format each row
    for i, row_name in enumerate(corr_matrix.index):
        row_values = [f"{row_name[:7]:7}"]
        for j, col_name in enumerate(corr_matrix.columns):
            corr_value = corr_matrix.iloc[i, j]
            # Use different formatting for different correlation strengths
            if i == j:  # Diagonal (always 1.0)
                row_values.append("   1.00 ")
            elif abs(corr_value) > 0.7:
                row_values.append(f"{corr_value:8.2f}*")  # Strong correlation
            else:
                row_values.append(f"{corr_value:8.2f} ")
        output.append("".join(row_values))
    
    output.append("\n* indicates strong correlation (>0.7)")
    
    # Find strong correlations
    strong_corrs = []
    for i in range(len(corr_matrix.columns)):
        for j in range(i):
            if abs(corr_matrix.iloc[i, j]) > 0.7:
                strong_corrs.append((
                    corr_matrix.columns[i],
                    corr_matrix.columns[j],
                    corr_matrix.iloc[i, j]
                ))
    
    # Sort by absolute correlation strength
    strong_corrs.sort(key=lambda x: abs(x[2]), reverse=True)
    
    if strong_corrs:
        output.append("\nStrong Correlations:")
        for col1, col2, corr in strong_corrs:
            output.append(f"{col1} and {col2}: {corr:.4f}")
    else:
        output.append("\nNo strong correlations found.")
        
    return '\n'.join(output)

def visualize_time_series(df, time_col, value_col):
    """
    Generate a text-based visualization of time series data
    
    Args:
        df: DataFrame with time series data
        time_col: Name of the time column
        value_col: Name of the value column
        
    Returns:
        String with time series visualization
    """
    # Ensure time column is datetime
    df = df.copy()
    df[time_col] = pd.to_datetime(df[time_col])
    df = df.sort_values(by=time_col)
    
    # Create time series
    ts = df[[time_col, value_col]].set_index(time_col)[value_col]
    
    output = [f"=== Time Series: {value_col} ===\n"]
    
    # Basic statistics
    output.append("Basic Statistics:")
    output.append(f"Start Date: {ts.index.min()}")
    output.append(f"End Date: {ts.index.max()}")
    output.append(f"Duration: {ts.index.max() - ts.index.min()}")
    output.append(f"Number of Observations: {len(ts)}")
    output.append(f"Mean: {ts.mean():.4f}")
    output.append(f"Std Dev: {ts.std():.4f}")
    output.append(f"Min: {ts.min():.4f}")
    output.append(f"Max: {ts.max():.4f}")
    
    # Calculate trend
    if len(ts) >= 2:
        first_value = ts.iloc[0]
        last_value = ts.iloc[-1]
        change = last_value - first_value
        pct_change = (change / first_value) * 100 if first_value != 0 else float('inf')
        
        output.append(f"\nTrend Analysis:")
        output.append(f"First Value: {first_value:.4f}")
        output.append(f"Last Value: {last_value:.4f}")
        output.append(f"Change: {change:.4f}")
        output.append(f"Percent Change: {pct_change:.2f}%")
        
        if pct_change > 10:
            trend = "Strong Upward"
        elif pct_change > 5:
            trend = "Moderate Upward"
        elif pct_change > 0:
            trend = "Slight Upward"
        elif pct_change == 0:
            trend = "No Change"
        elif pct_change > -5:
            trend = "Slight Downward"
        elif pct_change > -10:
            trend = "Moderate Downward"
        else:
            trend = "Strong Downward"
            
        output.append(f"Trend Direction: {trend}")
    
    # Simple text visualization
    if len(ts) <= 20:
        # If few points, show all
        output.append("\nTime Series Data:")
        for date, value in ts.items():
            output.append(f"{date}: {value:.4f}")
    else:
        # If many points, show summary with ASCII art
        output.append("\nTime Series Visualization:")
        # Divide into 20 bins
        bins = 20
        bin_size = len(ts) // bins
        if bin_size < 1:
            bin_size = 1
            
        min_val = ts.min()
        max_val = ts.max()
        range_val = max_val - min_val
        
        if range_val == 0:
            # Avoid division by zero
            range_val = 1
            
        width = 40  # Width of the visualization
        
        for i in range(0, len(ts), bin_size):
            bin_data = ts.iloc[i:i+bin_size]
            if len(bin_data) == 0:
                continue
                
            avg_val = bin_data.mean()
            date = bin_data.index[0]
            
            # Normalize to width
            bar_pos = int((avg_val - min_val) / range_val * width)
            
            # Create the bar
            bar = ' ' * bar_pos + '*'
            output.append(f"{date}: {avg_val:.4f} |{bar}")
    
    return '\n'.join(output)

if __name__ == "__main__":
    # Example usage
    df = pd.DataFrame({
        'A': np.random.randn(100),
        'B': np.random.randn(100),
        'C': np.random.choice(['X', 'Y', 'Z'], 100)
    })
    
    print(generate_text_visualization(df, "Sample Data"))
    print("\n" + visualize_correlation(df))
    
    # Create time series data
    dates = pd.date_range('2023-01-01', periods=100)
    values = np.cumsum(np.random.randn(100)) + 10
    ts_df = pd.DataFrame({'date': dates, 'value': values})
    
    print("\n" + visualize_time_series(ts_df, 'date', 'value'))
