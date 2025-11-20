"""
charts.py - Main chart helper module

This module serves as the central import point for all chart rendering functions.
It imports chart functions from the charts/ subdirectory and exposes them for use
in the main application.

Usage in your app:
    from components.charts import render_crime_timeline_chart
"""

# Import all chart rendering functions from charts subdirectory
from components.charts.crime_timeline_chart import render_crime_timeline_chart

# Future imports (uncomment as you create them):
# from components.charts.heatmap_chart import render_heatmap_chart
# from components.charts.bar_chart import render_alcaldia_bar_chart
# from components.charts.pie_chart import render_crime_type_pie_chart

# Export all chart functions
__all__ = [
    'render_crime_timeline_chart',
    # Add future chart functions here as you create them
]