# Remove rows with empty first serve points
df = df[df['first_serve_points'].notna()]
