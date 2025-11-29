def format_column_names(columns):
    """Example utility: format column names to be cleaner."""
    return [col.strip().replace(" ", "_") for col in columns]
