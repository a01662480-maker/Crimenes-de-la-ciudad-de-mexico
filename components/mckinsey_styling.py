"""
McKinsey-style theming and components for Streamlit dashboards
Supports both light and dark themes automatically via Streamlit's theme system
"""

import streamlit as st

# ===============================
# Color Constants
# ===============================
MCKINSEY_COLORS = {
    'primary_blue': '#0066CC',
    'dark_blue': '#003D7A',
    'light_blue': '#4D94E0',
    'accent_gold': '#D4A017',
    'text': '#1A1A1A',
    'text_light': '#6B7280',
    'background': '#F8F9FA',
    'card_bg': '#FAFBFC',
    'border': '#E5E7EB',
    'success': '#10B981',
    'warning': '#F59E0B',
    'danger': '#EF4444',
}

# ===============================
# Main Styling Function
# ===============================
def apply_mckinsey_styles():
    """
    Apply McKinsey-inspired styling with automatic light/dark theme support
    Uses Streamlit's native theme variables for seamless theme switching
    Call this once at the beginning of your dashboard
    """
    st.markdown(f"""
        <style>
        /* Import professional font */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        
        /* ============================================
           THEME-AWARE STYLING
           Uses Streamlit's CSS variables for auto-adaptation
           ============================================ */
        
        /* Global styling */
        .main {{
            font-family: 'Inter', sans-serif;
        }}
        
        /* Title styling */
        h1 {{
            color: var(--text-color) !important;
            font-family: 'Inter', sans-serif !important;
            font-weight: 600 !important;
            font-size: 2.2rem !important;
            margin-bottom: 0.5rem !important;
        }}
        
        /* Section headers */
        h2, h3 {{
            color: var(--text-color) !important;
            font-family: 'Inter', sans-serif !important;
            font-weight: 600 !important;
            margin-top: 1.5rem !important;
            margin-bottom: 0.8rem !important;
        }}
        
        h3 {{
            font-size: 1.3rem !important;
            border-bottom: 2px solid {MCKINSEY_COLORS['primary_blue']};
            padding-bottom: 0.4rem;
        }}
        
        /* KPI Card Styling - Theme Aware */
        .kpi-card {{
            background: var(--secondary-background-color);
            border: 1px solid rgba(128, 128, 128, 0.2);
            border-left: 4px solid {MCKINSEY_COLORS['primary_blue']};
            border-radius: 10px;
            padding: 1.5rem;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
            margin-bottom: 1rem;
            transition: all 0.3s ease;
            height: 100%;
        }}
        
        .kpi-card:hover {{
            transform: translateY(-3px);
            box-shadow: 0 4px 16px rgba(0, 102, 204, 0.15);
            border-left-color: {MCKINSEY_COLORS['light_blue']};
        }}
        
        .kpi-label {{
            font-family: 'Inter', sans-serif;
            font-size: 0.75rem;
            color: var(--text-color);
            opacity: 0.7;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.8px;
            margin-bottom: 0.5rem;
        }}
        
        .kpi-value {{
            font-family: 'Inter', sans-serif;
            font-size: 2.2rem;
            color: var(--text-color);
            font-weight: 700;
            line-height: 1.2;
            margin-bottom: 0.3rem;
        }}
        
        .kpi-delta {{
            font-family: 'Inter', sans-serif;
            font-size: 0.9rem;
            font-weight: 500;
            margin-bottom: 0.3rem;
        }}
        
        .kpi-delta.positive {{
            color: {MCKINSEY_COLORS['success']};
        }}
        
        .kpi-delta.negative {{
            color: {MCKINSEY_COLORS['danger']};
        }}
        
        .kpi-delta.neutral {{
            color: var(--text-color);
            opacity: 0.7;
        }}
        
        .kpi-caption {{
            font-family: 'Inter', sans-serif;
            font-size: 0.75rem;
            color: var(--text-color);
            opacity: 0.7;
            margin-top: 0.3rem;
            display: flex;
            align-items: center;
            gap: 0.3rem;
        }}
        
        /* Divider styling */
        hr {{
            margin: 1.5rem 0;
            border: none;
            border-top: 1px solid rgba(128, 128, 128, 0.2);
        }}
        
        /* Streamlit metric override for consistency */
        [data-testid="stMetricValue"] {{
            font-size: 2.2rem;
            color: var(--text-color) !important;
            font-weight: 700;
            font-family: 'Inter', sans-serif;
        }}
        
        [data-testid="stMetricLabel"] {{
            font-size: 0.75rem;
            color: var(--text-color) !important;
            opacity: 0.7;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.8px;
            font-family: 'Inter', sans-serif;
        }}
        
        /* Responsive adjustments */
        @media (max-width: 768px) {{
            .kpi-value {{
                font-size: 1.8rem;
            }}
            
            .kpi-card {{
                padding: 1rem;
            }}
        }}
        </style>
    """, unsafe_allow_html=True)

# ===============================
# KPI Card Component
# ===============================
def create_kpi_card(label, value, delta=None, delta_color="off", caption=None, icon=None):
    """
    Create a styled KPI card with McKinsey theme
    
    Args:
        label (str): KPI label/title
        value (str/int/float): Main KPI value
        delta (str, optional): Delta text (e.g., "+5.2% vs 2023")
        delta_color (str): "positive", "negative", "neutral", or "off"
        caption (str, optional): Additional caption text
        icon (str, optional): Emoji icon to display
    
    Returns:
        Renders the KPI card in Streamlit
    """
    
    # Determine delta class
    delta_class = "neutral"
    if delta and delta_color != "off":
        if delta_color == "positive" or (isinstance(delta, str) and '+' in delta):
            delta_class = "positive"
        elif delta_color == "negative" or (isinstance(delta, str) and '-' in delta):
            delta_class = "negative"
    
    # Build HTML
    icon_html = f'<span style="font-size: 1.2rem; margin-right: 0.3rem;">{icon}</span>' if icon else ''
    delta_html = f'<div class="kpi-delta {delta_class}">{delta}</div>' if delta else ''
    caption_html = f'<div class="kpi-caption">{caption}</div>' if caption else ''
    
    kpi_html = f"""
    <div class="kpi-card">
        <div class="kpi-label">{icon_html}{label}</div>
        <div class="kpi-value">{value}</div>
        {delta_html}
        {caption_html}
    </div>
    """
    
    st.markdown(kpi_html, unsafe_allow_html=True)

# ===============================
# Utility Functions
# ===============================
def format_number(num):
    """Format large numbers with commas"""
    if num is None:
        return "N/A"
    return f"{int(num):,}"

def format_percentage(num, decimals=1):
    """Format number as percentage"""
    if num is None:
        return "N/A"
    return f"{num:+.{decimals}f}%"

def format_delta_text(current, previous, period_label="vs previous", show_percentage=True):
    """
    Calculate and format delta text
    
    Args:
        current: Current period value
        previous: Previous period value
        period_label: Label for comparison (e.g., "vs 2023", "YoY")
        show_percentage: Whether to show percentage change
    
    Returns:
        Formatted delta string
    """
    if previous is None or previous == 0:
        return f"N/A {period_label}"
    
    change = current - previous
    pct_change = (change / previous) * 100
    
    if show_percentage:
        return f"{pct_change:+.1f}% {period_label}"
    else:
        return f"{change:+,} {period_label}"