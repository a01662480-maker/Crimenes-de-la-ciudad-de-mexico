import streamlit as st
import os
import json

def show():
    """Main EDA display function"""
    
    # ==========================
    #   CSS PARA ANIMACIONES Y TARJETA
    # ==========================
    st.markdown("""
    <style>

    .fade-in {
        animation: fadeIn 1s ease-in-out;
    }

    @keyframes fadeIn {
        from { opacity: 0; }
        to   { opacity: 1; }
    }

    .card-desc {
        background: #f8f9fa;
        padding: 20px;
        margin-top: 15px;
        margin-bottom: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        font-size: 16px;
        font-weight: 400;
        font-family: 'Segoe UI', sans-serif;
        color: #444;
        line-height: 1.6;
    }

    .graph-divider {
        height: 2px;
        background: linear-gradient(90deg, transparent 0%, #0066CC 50%, transparent 100%);
        margin: 40px 0;
        opacity: 0.4;
    }

    .eda-image-container img {
        max-height: 450px;
        width: auto;
        margin: 0 auto;
        display: block;
        object-fit: contain;
    }

    </style>
    """, unsafe_allow_html=True)

    # ==========================
    #   TÍTULO
    # ==========================
    st.markdown("""
    <div style="text-align:center; padding: 20px 0;">
        <h1 style="font-size: 42px; margin-bottom:5px;">
            🚗📊 Radiografía del Robo de Vehículos en la CDMX
        </h1>
        <h3 style="color:gray; margin-top:0;">
            Un recorrido visual por patrones, tendencias y zonas críticas
        </h3>
        <hr style="margin-top:20px;">
    </div>
    """, unsafe_allow_html=True)


    # ==========================
    #   LEER DESCRIPCIONES
    # ==========================
    DESC_FILE = "descriptions.json"
    descripciones = {}

    if os.path.exists(DESC_FILE):
        try:
            with open(DESC_FILE, "r", encoding="utf-8") as f:
                descripciones = json.load(f)
        except:
            st.warning("⚠ No se pudo leer descriptions.json, revisa su formato.")
    else:
        st.warning("⚠ No se encontró descriptions.json. Se usarán descripciones por nombre.")


    # ==========================
    #   CARGAR IMÁGENES
    # ==========================
    GRAPH_FOLDER = "graphs"
    valid_ext = (".png", ".jpg", ".jpeg")

    imagenes = []
    
    # Check if graphs folder exists
    if not os.path.exists(GRAPH_FOLDER):
        st.error(f"⚠ La carpeta '{GRAPH_FOLDER}/' no existe. Por favor créala y agrega imágenes.")
        st.stop()
    
    for file in sorted(os.listdir(GRAPH_FOLDER)):
        if file.lower().endswith(valid_ext):
            path = os.path.join(GRAPH_FOLDER, file)
            desc = descripciones.get(
                file,
                file.replace("_", " ").rsplit(".", 1)[0].capitalize()
            )
            imagenes.append((file, path, desc))

    if not imagenes:
        st.error("⚠ No hay imágenes dentro de la carpeta 'graphs/'.")
        st.stop()


    # ==========================
    #   MOSTRAR TODAS LAS IMÁGENES
    # ==========================
    for idx, (filename, img_path, desc) in enumerate(imagenes):
        # Display image with fade-in animation and max-height constraint
        st.markdown('<div class="fade-in eda-image-container">', unsafe_allow_html=True)
        st.image(img_path, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Display description in card
        st.markdown('<div class="card-desc fade-in">', unsafe_allow_html=True)
        st.markdown(desc, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Add blue divider after description (except for last image)
        if idx < len(imagenes) - 1:
            st.markdown('<div class="graph-divider"></div>', unsafe_allow_html=True)