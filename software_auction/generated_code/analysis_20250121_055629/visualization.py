# Plotting the three points on a graph for visual understanding
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

points = [(x1, y1), (x2, y2), (x3, y3)] # replace with actual points

x_values = [point[0] for point in points]
y_values = [point[1] for point in points]

plt.scatter(x_values, y_values)
plt.show()

def text_histogram(data, bins=10, width=50, title=None):
    """
    Generate a text-based histogram.
    
    Args:
        data: Series or array-like of values
        bins: Number of bins
        width: Width of the histogram bars in characters
        title: Optional title
        
    Returns:
        String representation of the histogram
    """
    # Calculate histogram data
    hist, bin_edges = np.histogram(data, bins=bins)
    max_count = max(hist) if len(hist) > 0 else 0
    
    # Generate output
    lines = []
    if title:
        lines.append(title)
        lines.append('=' * len(title))
    
    for i, count in enumerate(hist):
        # Create the bar
        bar_len = int(count / max_count * width) if max_count > 0 else 0
        bar = '█' * bar_len
        
        # Format bin range
        bin_range = f"{bin_edges[i]:.2f} - {bin_edges[i+1]:.2f}"
        
        # Add line to output
        lines.append(f"{bin_range:20s} | {bar} ({count})")
    
    return '\n'.join(lines)

def text_scatter(x, y, width=60, height=20, title=None):
    """
    Generate a text-based scatter plot.
    
    Args:
        x: x-coordinates
        y: y-coordinates
        width: Width of the plot
        height: Height of the plot
        title: Optional title
        
    Returns:
        String representation of the scatter plot
    """
    if len(x) == 0 or len(y) == 0:
        return "No data to plot"
    
    # Scale data to fit in the text area
    x_min, x_max = min(x), max(x)
    y_min, y_max = min(y), max(y)
    
    # Handle cases where all values are the same
    x_range = x_max - x_min
    y_range = y_max - y_min
    
    if x_range == 0:
        x_min -= 1
        x_max += 1
        x_range = 2
    
    if y_range == 0:
        y_min -= 1
        y_max += 1
        y_range = 2
    
    # Create the plot array (filled with spaces)
    plot = [[' ' for _ in range(width)] for _ in range(height)]
    
    # Place points in the array
    for xi, yi in zip(x, y):
        x_pos = int((xi - x_min) / x_range * (width - 1))
        # Invert y-axis so higher values appear at the top
        y_pos = height - 1 - int((yi - y_min) / y_range * (height - 1))
        
        # Check bounds and set point
        if 0 <= x_pos < width and 0 <= y_pos < height:
            plot[y_pos][x_pos] = '•'
    
    # Generate output
    lines = []
    if title:
        lines.append(title)
        lines.append('=' * len(title))
    
    # Add y-axis labels (on left side)
    for i in range(height):
        y_val = y_max - (i / (height - 1)) * y_range
        y_label = f"{y_val:.2f}"
        
        # Join the row characters
        row = ''.join(plot[i])
        lines.append(f"{y_label:8s} | {row}")
    
    # Add x-axis
    lines.append('-' * (width + 10))
    
    # Add x-axis labels
    x_ticks = [f"{x_min + (i / 4) * x_range:.2f}" for i in range(5)]
    tick_positions = [int(i / 4 * width) for i in range(5)]
    
    x_axis = ' ' * 10
    for pos, label in zip(tick_positions, x_ticks):
        label_len = len(label)
        start_pos = pos + 10 - label_len // 2
        if start_pos < len(x_axis):
            x_axis = x_axis[:start_pos] + label + x_axis[start_pos + label_len:]
        else:
            x_axis = x_axis + ' ' * (start_pos - len(x_axis)) + label
    
    lines.append(x_axis)
    
    return '\n'.join(lines)

def text_line_chart(x, y, width=60, height=20, title=None):
    """
    Generate a text-based line chart.
    
    Args:
        x: x-coordinates (typically time points)
        y: y-coordinates (values)
        width: Width of the plot
        height: Height of the plot
        title: Optional title
        
    Returns:
        String representation of the line chart
    """
    if len(x) == 0 or len(y) == 0:
        return "No data to plot"
    
    # Scale data to fit in the text area
    x_min, x_max = min(x), max(x)
    y_min, y_max = min(y), max(y)
    
    # Handle cases where all values are the same
    x_range = x_max - x_min
    y_range = y_max - y_min
    
    if x_range == 0:
        x_min -= 1
        x_max += 1
        x_range = 2
    
    if y_range == 0:
        y_min -= 1
        y_max += 1
        y_range = 2
    
    # Create the plot array (filled with spaces)
    plot = [[' ' for _ in range(width)] for _ in range(height)]
    
    # Calculate point positions
    points = []
    for xi, yi in zip(x, y):
        x_pos = int((xi - x_min) / x_range * (width - 1))
        # Invert y-axis so higher values appear at the top
        y_pos = height - 1 - int((yi - y_min) / y_range * (height - 1))
        points.append((x_pos, y_pos))
    
    # Draw the line by connecting points
    for i in range(len(points) - 1):
        x1, y1 = points[i]
        x2, y2 = points[i + 1]
        
        # Simple line drawing
        if x1 == x2:  # Vertical line
            start_y, end_y = min(y1, y2), max(y1, y2)
            for y in range(start_y, end_y + 1):
                if 0 <= x1 < width and 0 <= y < height:
                    plot[y][x1] = '│'
        elif y1 == y2:  # Horizontal line
            start_x, end_x = min(x1, x2), max(x1, x2)
            for x in range(start_x, end_x + 1):
                if 0 <= x < width and 0 <= y1 < height:
                    plot[y1][x] = '─'
        else:  # Diagonal line (simplified Bresenham's algorithm)
            dx = abs(x2 - x1)
            dy = abs(y2 - y1)
            sx = 1 if x1 < x2 else -1
            sy = 1 if y1 < y2 else -1
            err = dx - dy
            
            while True:
                if 0 <= x1 < width and 0 <= y1 < height:
                    # Choose character based on line direction
                    if dx > dy:
                        plot[y1][x1] = '─'
                    else:
                        plot[y1][x1] = '│'
                
                if x1 == x2 and y1 == y2:
                    break
                    
                e2 = 2 * err
                if e2 > -dy:
                    err -= dy
                    x1 += sx
                if e2 < dx:
                    err += dx
                    y1 += sy
    
    # Mark data points with dots
    for x_pos, y_pos in points:
        if 0 <= x_pos < width and 0 <= y_pos < height:
            plot[y_pos][x_pos] = '•'
    
    # Generate output
    lines = []
    if title:
        lines.append(title)
        lines.append('=' * len(title))
    
    # Add y-axis labels (on left side)
    for i in range(height):
        y_val = y_max - (i / (height - 1)) * y_range
        y_label = f"{y_val:.2f}"
        
        # Join the row characters
        row = ''.join(plot[i])
        lines.append(f"{y_label:8s} | {row}")
    
    # Add x-axis
    lines.append('-' * (width + 10))
    
    # Add x-axis labels (similar to scatter plot)
    x_ticks = [f"{x_min + (i / 4) * x_range:.2f}" for i in range(5)]
    tick_positions = [int(i / 4 * width) for i in range(5)]
    
    x_axis = ' ' * 10
    for pos, label in zip(tick_positions, x_ticks):
        label_len = len(label)
        start_pos = pos + 10 - label_len // 2
        if start_pos < len(x_axis):
            x_axis = x_axis[:start_pos] + label + x_axis[start_pos + label_len:]
        else:
            x_axis = x_axis + ' ' * (start_pos - len(x_axis)) + label
    
    lines.append(x_axis)
    
    return '\n'.join(lines)

def text_bar_chart(categories, values, width=50, title=None):
    """
    Generate a text-based bar chart.
    
    Args:
        categories: List of category names
        values: List of values corresponding to categories
        width: Maximum width of the bars
        title: Optional title
        
    Returns:
        String representation of the bar chart
    """
    if len(categories) == 0 or len(values) == 0:
        return "No data to plot"
    
    # Find the maximum value for scaling
    max_value = max(values) if values else 0
    
    # Find the longest category name for alignment
    max_cat_len = max(len(str(cat)) for cat in categories) if categories else 0
    
    # Generate output
    lines = []
    if title:
        lines.append(title)
        lines.append('=' * len(title))
    
    # Create the bar chart
    for cat, val in zip(categories, values):
        # Calculate bar length
        bar_len = int(val / max_value * width) if max_value > 0 else 0
        bar = '█' * bar_len
        
        # Format the line
        lines.append(f"{str(cat):{max_cat_len}s} | {bar} ({val})")
    
    return '\n'.join(lines)

def text_heatmap(data, row_labels=None, col_labels=None, title=None):
    """
    Generate a text-based heatmap for a 2D array.
    
    Args:
        data: 2D array of values
        row_labels: Optional list of row labels
        col_labels: Optional list of column labels
        title: Optional title
        
    Returns:
        String representation of the heatmap
    """
    if len(data) == 0:
        return "No data to plot"
    
    # Convert to numpy array for easier manipulation
    data_array = np.array(data)
    
    # Set default labels if not provided
    if row_labels is None:
        row_labels = [f"Row {i}" for i in range(data_array.shape[0])]
    if col_labels is None:
        col_labels = [f"Col {i}" for i in range(data_array.shape[1])]
    
    # Find min and max values for color mapping
    min_val = np.min(data_array)
    max_val = np.max(data_array)
    val_range = max_val - min_val
    
    # Function to get a character based on value intensity
    def get_intensity_char(val):
        if val_range == 0:
            return '▓'
        
        # Normalize value to 0-1 range
        normalized = (val - min_val) / val_range
        
        # Choose character based on intensity
        if normalized < 0.2:
            return ' '
        elif normalized < 0.4:
            return '░'
        elif normalized < 0.6:
            return '▒'
        elif normalized < 0.8:
            return '▓'
        else:
            return '█'
    
    # Generate output
    lines = []
    if title:
        lines.append(title)
        lines.append('=' * len(title))
    
    # Calculate column width based on max value length
    col_width = max(max(len(str(val)) for val in row) for row in data_array) + 1
    
    # Add header with column labels
    header = ' ' * (max(len(l) for l in row_labels) + 2)
    for label in col_labels:
        header += f"{str(label):{col_width}s}"
    lines.append(header)
    
    # Add each row
    for i, (row, label) in enumerate(zip(data_array, row_labels)):
        line = f"{label}: "
        for val in row:
            # Add value with intensity character
            char = get_intensity_char(val)
            line += f"{char * 2}{val:{col_width-2}.2f}"
        lines.append(line)
    
    return '\n'.join(lines)

def analyze_and_visualize(df):
    """
    Analyze and generate text visualizations for a DataFrame.
    
    Args:
        df: DataFrame to analyze
        
    Returns:
        String with analysis and visualizations
    """
    results = ["=== Data Analysis Results ===\n"]
    
    # Basic information
    results.append(f"Data Shape: {df.shape[0]} rows x {df.shape[1]} columns")
    results.append(f"Columns: {', '.join(df.columns)}")
    
    # Missing values
    missing = df.isnull().sum()
    if missing.sum() > 0:
        results.append("\nMissing Values:")
        for col, count in missing.items():
            if count > 0:
                results.append(f"  {col}: {count} ({count/len(df)*100:.1f}%)")
    else:
        results.append("\nNo missing values found.")
    
    # Numeric columns analysis
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    if len(numeric_cols) > 0:
        results.append("\nNumeric Columns Summary:")
        stats = df[numeric_cols].describe().T
        
        for col in numeric_cols:
            results.append(f"\n{col}:")
            results.append(f"  Mean: {stats.loc[col, 'mean']:.4f}")
            results.append(f"  Std: {stats.loc[col, 'std']:.4f}")
            results.append(f"  Min: {stats.loc[col, 'min']:.4f}")
            results.append(f"  25%: {stats.loc[col, '25%']:.4f}")
            results.append(f"  50%: {stats.loc[col, '50%']:.4f}")
            results.append(f"  75%: {stats.loc[col, '75%']:.4f}")
            results.append(f"  Max: {stats.loc[col, 'max']:.4f}")
            
            # Add histogram for each numeric column
            results.append("\n" + text_histogram(df[col], title=f"Distribution of {col}"))
    
    # Categorical columns analysis
    cat_cols = df.select_dtypes(exclude=[np.number]).columns
    if len(cat_cols) > 0:
        results.append("\nCategorical Columns Summary:")
        for col in cat_cols:
            value_counts = df[col].value_counts()
            results.append(f"\n{col}:")
            results.append(f"  Unique Values: {df[col].nunique()}")
            results.append(f"  Most Common: {value_counts.index[0]} ({value_counts.values[0]} occurrences)")
            
            # Show top categories with bar chart
            if df[col].nunique() <= 10:
                top_n = df[col].value_counts().head(10)
                results.append("\n" + text_bar_chart(
                    top_n.index.tolist(), 
                    top_n.values.tolist(),
                    title=f"Top Categories in {col}"
                ))
    
    # Correlation analysis for numeric columns
    if len(numeric_cols) >= 2:
        results.append("\nCorrelation Analysis:")
        
        # Find strong correlations
        corr_matrix = df[numeric_cols].corr()
        strong_corrs = []
        
        for i in range(len(corr_matrix.columns)):
            for j in range(i):
                if abs(corr_matrix.iloc[i, j]) > 0.5:  # Consider 0.5 as threshold
                    strong_corrs.append((
                        corr_matrix.columns[i],
                        corr_matrix.columns[j],
                        corr_matrix.iloc[i, j]
                    ))
        
        if strong_corrs:
            results.append("\nStrong Correlations (|r| > 0.5):")
            for var1, var2, val in sorted(strong_corrs, key=lambda x: abs(x[2]), reverse=True):
                results.append(f"  {var1} and {var2}: {val:.4f}")
                
                # Create scatter plot for the strongest correlations
                if abs(val) > 0.7:  # Very strong correlation
                    results.append("\n" + text_scatter(
                        df[var1].values, 
                        df[var2].values,
                        title=f"Scatter Plot: {var1} vs {var2} (r={val:.4f})"
                    ))
        else:
            results.append("No strong correlations found.")
    
    return '\n'.join(results)

if __name__ == "__main__":
    # Example usage
    # Generate sample data
    np.random.seed(42)
    df = pd.DataFrame({
        'A': np.random.normal(0, 1, 100),
        'B': np.random.normal(0, 1, 100),
        'C': np.random.choice(['X', 'Y', 'Z'], 100),
        'D': pd.date_range('2023-01-01', periods=100)
    })
    
    # Create correlated column
    df['E'] = df['A'] * 0.8 + np.random.normal(0, 0.5, 100)
    
    # Print analysis and visualizations
    print(analyze_and_visualize(df))
    
    # Time series example
    x = np.linspace(0, 4*np.pi, 40)
    y = np.sin(x) + np.random.normal(0, 0.1, len(x))
    
    print("\n" + text_line_chart(x, y, title="Sine Wave with Noise"))
    
    # Heatmap example
    data = np.random.rand(5, 5)
    row_labels = ['A', 'B', 'C', 'D', 'E']
    col_labels = ['V', 'W', 'X', 'Y', 'Z']
    
    print("\n" + text_heatmap(data, row_labels, col_labels, title="Random Heatmap"))
