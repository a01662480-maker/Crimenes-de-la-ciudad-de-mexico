"""
Predicciones Module
Page for displaying predictive model results
"""

import streamlit as st

def show():
    """Display the predictions page with placeholders for model results"""
    
    # Custom CSS for predictions page
    st.markdown("""
        <style>
        .predictions-header {
            background: linear-gradient(135deg, #0066CC 0%, #004C99 100%);
            color: white;
            padding: 2rem;
            border-radius: 12px;
            margin-bottom: 2rem;
            text-align: center;
        }
        
        .placeholder-box {
            background: #F8F9FA;
            border: 2px dashed #0066CC;
            border-radius: 12px;
            padding: 3rem 2rem;
            text-align: center;
            margin: 1rem 0;
            min-height: 400px;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-direction: column;
        }
        
        .placeholder-icon {
            font-size: 4rem;
            margin-bottom: 1rem;
            opacity: 0.5;
        }
        
        .placeholder-text {
            font-size: 1.2rem;
            color: #666;
            font-weight: 500;
        }
        
        .section-title {
            color: #0066CC;
            font-size: 1.5rem;
            font-weight: 600;
            margin: 2rem 0 1rem 0;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Header
    st.markdown("""
        <div class="predictions-header">
            <h1>Predicciones</h1>
            <p>Resultados del Modelo Predictivo de Delitos en CDMX</p>
        </div>
    """, unsafe_allow_html=True)
    
    # Description
    st.markdown("""
        Esta sección presenta los resultados y visualizaciones del modelo predictivo 
        para anticipar patrones delictivos en la Ciudad de México.
    """)
    
    st.markdown("---")
    
    # Placeholder 1: Map/Animation
    st.markdown('<div class="section-title">📍 Mapa / Animación Predictiva</div>', unsafe_allow_html=True)
    
    st.markdown("""
        <div class="placeholder-box">
            <div class="placeholder-icon">🗺️</div>
            <div class="placeholder-text">Aquí se mostrará el mapa interactivo o animación</div>
            <p style="color: #999; margin-top: 1rem;">Visualización geográfica de predicciones de delitos</p>
        </div>
    """, unsafe_allow_html=True)
    
    # Placeholder 2: Extra Data
    st.markdown('<div class="section-title">📊 Datos Adicionales</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
            <div class="placeholder-box" style="min-height: 250px;">
                <div class="placeholder-icon">📈</div>
                <div class="placeholder-text">Gráficas y Métricas</div>
                <p style="color: #999; margin-top: 1rem;">Estadísticas del modelo predictivo</p>
            </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
            <div class="placeholder-box" style="min-height: 250px;">
                <div class="placeholder-icon">🎯</div>
                <div class="placeholder-text">Análisis de Precisión</div>
                <p style="color: #999; margin-top: 1rem;">Métricas de performance del modelo</p>
            </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Additional placeholder section
    st.markdown('<div class="section-title">ℹ️ Información del Modelo</div>', unsafe_allow_html=True)
    
    st.markdown("""
        <div class="placeholder-box" style="min-height: 200px;">
            <div class="placeholder-icon">📝</div>
            <div class="placeholder-text">Detalles y Metodología</div>
            <p style="color: #999; margin-top: 1rem;">Descripción del modelo y metodología utilizada</p>
        </div>
    """, unsafe_allow_html=True)
    
    # Footer info
    st.markdown("---")
    st.info("💡 **Nota:** Esta página está en desarrollo. Las visualizaciones y datos se cargarán próximamente.")

if __name__ == "__main__":
    show()