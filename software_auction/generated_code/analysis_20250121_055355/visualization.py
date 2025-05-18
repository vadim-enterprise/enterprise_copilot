# Visualize the distribution of interest levels among potential customers
import pandas as pd
import numpy as np

def text_visualize_data(df, column=None):
    """
    Create a text-based visualization of data
    
    Args:
        df: DataFrame to visualize
        column: Optional specific column to visualize
        
    Returns:
        Text-based visualization
    """
    if column is not None:
        if column not in df.columns:
            return f"Column '{column}' not found in DataFrame"
        
        series = df[column]
        return text_visualize_series(series, title=f"Column: {column}")
    
    # Visualize entire DataFrame
    output = ["=== DataFrame Overview ==="]
    output.append(f"Shape: {df.shape[0]} rows x {df.shape[1]} columns")
    output.append(f"Columns: {', '.join(df.columns)}")
    
    # Show data types
    output.append("\nData Types:")
    for col, dtype in df.dtypes.items():
        output.append(f"  {col}: {dtype}")
    
    # Show basic stats
    output.append("\nBasic Statistics:")
    
    # For numeric columns
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    if len(numeric_cols) > 0:
        output.append("\nNumeric Columns:")
        for col in numeric_cols:
            stats = df[col].describe()
            output.append(f"  {col}:")
            output.append(f"    Mean: {stats['mean']:.4f}")
            output.append(f"    Std: {stats['std']:.4f}")
            output.append(f"    Min: {stats['min']:.4f}")
            output.append(f"    Max: {stats['max']:.4f}")
    
    # For categorical columns
    cat_cols = df.select_dtypes(exclude=[np.number]).columns
    if len(cat_cols) > 0:
        output.append("\nCategorical Columns:")
        for col in cat_cols:
            value_counts = df[col].value_counts().head(5)
            output.append(f"  {col} (top 5):")
            for val, count in value_counts.items():
                output.append(f"    {val}: {count}")
    
    return "\n".join(output)

def text_visualize_series(series, title="Series Visualization"):
    """
    Create a text-based visualization of a pandas Series
    
    Args:
        series: Series to visualize
        title: Title for the visualization
        
    Returns:
        Text-based visualization
    """
    output = [f"=== {title} ==="]
    
    # Basic statistics
    stats = series.describe()
    output.append("Basic Statistics:")
    output.append(f"Count: {stats['count']}")
    output.append(f"Mean: {stats['mean']:.4f}")
    output.append(f"Std: {stats['std']:.4f}")
    output.append(f"Min: {stats['min']:.4f}")
    output.append(f"25%: {stats['25%']:.4f}")
    output.append(f"50%: {stats['50%']:.4f}")
    output.append(f"75%: {stats['75%']:.4f}")
    output.append(f"Max: {stats['max']:.4f}")
    
    # ASCII Histogram
    output.append("\nHistogram:")
    hist, bins = np.histogram(series.dropna(), bins=10)
    max_count = max(hist) if len(hist) > 0 else 0
    width = 40  # Width of the histogram
    
    for i, count in enumerate(hist):
        bar_length = int(count / max_count * width) if max_count > 0 else 0
        bar = '#' * bar_length
        output.append(f"{bins[i]:.2f} - {bins[i+1]:.2f} | {bar} ({count})")
    
    return "\n".join(output)

def text_visualize_correlation(df):
    """
    Create a text-based visualization of correlation matrix
    
    Args:
        df: DataFrame with numeric columns
        
    Returns:
        Text-based correlation matrix
    """
    numeric_df = df.select_dtypes(include=[np.number])
    
    if numeric_df.empty:
        return "No numeric columns to calculate correlation"
    
    corr = numeric_df.corr()
    
    output = ["=== Correlation Matrix ==="]
    
    # Format column headers
    header = "     " + " ".join(f"{col[:7]:>8}" for col in corr.columns)
    output.append(header)
    
    # Add matrix rows
    for i, row in enumerate(corr.index):
        row_str = f"{row[:7]:<7}"
        for j, col in enumerate(corr.columns):
            val = corr.iloc[i, j]
            # Use different formatting based on correlation strength
            if i == j:  # Diagonal (always 1.0)
                row_str += "   1.00 "
            elif abs(val) > 0.7:
                row_str += f"{val:8.2f}*"  # Strong correlation
            else:
                row_str += f"{val:8.2f} "
        output.append(row_str)
    
    output.append("\n* indicates strong correlation (>0.7)")
    
    # Find strong correlations
    strong_corrs = []
    for i in range(len(corr.columns)):
        for j in range(i):
            if abs(corr.iloc[i, j]) > 0.7:
                strong_corrs.append((corr.columns[i], corr.columns[j], corr.iloc[i, j]))
    
    if strong_corrs:
        output.append("\nStrong Correlations:")
        for var1, var2, val in sorted(strong_corrs, key=lambda x: abs(x[2]), reverse=True):
            output.append(f"{var1} and {var2}: {val:.4f}")
    else:
        output.append("\nNo strong correlations found.")
    
    return "\n".join(output)

def text_visualize_time_series(df, date_col, value_col):
    """
    Create a text-based visualization of time series data
    
    Args:
        df: DataFrame with time series data
        date_col: Name of the date column
        value_col: Name of the value column
        
    Returns:
        Text-based time series visualization
    """
    if date_col not in df.columns or value_col not in df.columns:
        return f"Columns not found. Available columns: {', '.join(df.columns)}"
    
    # Convert to datetime and sort
    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col])
    df = df.sort_values(by=date_col)
    
    # Create time series
    ts = df.set_index(date_col)[value_col]
    
    output = [f"=== Time Series: {value_col} ==="]
    
    # Basic statistics
    output.append("Basic Statistics:")
    output.append(f"Date Range: {ts.index.min()} to {ts.index.max()}")
    output.append(f"Duration: {ts.index.max() - ts.index.min()}")
    output.append(f"Number of Points: {len(ts)}")
    output.append(f"Mean: {ts.mean():.4f}")
    output.append(f"Std: {ts.std():.4f}")
    output.append(f"Min: {ts.min():.4f}")
    output.append(f"Max: {ts.max():.4f}")
    
    # Trend analysis
    if len(ts) >= 2:
        first_val = ts.iloc[0]
        last_val = ts.iloc[-1]
        change = last_val - first_val
        pct_change = (change / abs(first_val)) * 100 if first_val != 0 else float('inf')
        
        output.append("\nTrend Analysis:")
        output.append(f"First Value ({ts.index.min()}): {first_val:.4f}")
        output.append(f"Last Value ({ts.index.max()}): {last_val:.4f}")
        output.append(f"Absolute Change: {change:.4f}")
        output.append(f"Percent Change: {pct_change:.2f}%")
        
        # Determine trend direction
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
    
    # ASCII visualization
    if len(ts) <= 20:
        # If few points, show all
        output.append("\nTime Series Data:")
        for date, value in ts.items():
            output.append(f"{date}: {value:.4f}")
    else:
        # ASCII chart
        output.append("\nTime Series Visualization:")
        
        # Divide into segments for display
        bins = 20
        bin_size = len(ts) // bins
        if bin_size < 1:
            bin_size = 1
            
        min_val = ts.min()
        max_val = ts.max()
        range_val = max_val - min_val
        
        if range_val == 0:
            range_val = 1  # Avoid division by zero
            
        chart_width = 40
        
        for i in range(0, len(ts), bin_size):
            bin_data = ts.iloc[i:i+bin_size]
            if len(bin_data) == 0:
                continue
                
            avg_val = bin_data.mean()
            date = bin_data.index[0]
            
            # Position in chart
            bar_pos = int((avg_val - min_val) / range_val * chart_width)
            
            # Create the bar
            bar = ' ' * bar_pos + '*'
            output.append(f"{date}: {avg_val:.4f} |{bar}")
    
    return "\n".join(output)

if __name__ == "__main__":
    # Example usage
    df = pd.DataFrame({
        'A': np.random.randn(100),
        'B': np.random.randn(100),
        'C': np.random.choice(['X', 'Y', 'Z'], 100)
    })
    
    print(text_visualize_data(df))
    print("\n" + text_visualize_series(df['A'], "Column A"))
    print("\n" + text_visualize_correlation(df))
    
    # Time series example
    dates = pd.date_range('2023-01-01', periods=100)
    values = np.cumsum(np.random.randn(100)) + 10
    ts_df = pd.DataFrame({'date': dates, 'value': values})
    
    print("\n" + text_visualize_time_series(ts_df, 'date', 'value'))
