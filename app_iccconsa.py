import streamlit as st
import pandas as pd
from pyproj import Proj, Transformer
import matplotlib.pyplot as plt
from matplotlib.ticker import ScalarFormatter
from openpyxl import load_workbook
from openpyxl.drawing.image import Image as xlImage
import os
from datetime import datetime
import plotly.express as px # Importar Plotly Express
import tempfile
import numpy as np

# ================================================================
# CONFIGURACIÓN GENERAL
# ================================================================
st.set_page_config(
    page_title=" Calculadora Geodésica UTM - ICCCONSA EIRL",
    layout="wide",
    page_icon="📐"
)

# ================================================================
# ESTILOS PERSONALIZADOS (COLORES CORPORATIVOS)
# ================================================================
st.markdown("""
<style>
/* Fondo principal */
[data-testid="stAppViewContainer"] {
    background: linear-gradient(135deg, #f9fafb 0%, #eef1f5 100%);
    color: #111827;
    font-family: 'Segoe UI', sans-serif;
}

/* Cabecera */
.header-container {
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: #003366;
    color: white;
    padding: 0.8rem 1.5rem;
    border-radius: 12px;
    box-shadow: 0 3px 10px rgba(0,0,0,0.2);
}
.header-title {
    font-size: 1.4rem;
    font-weight: 600;
    letter-spacing: 0.5px;
}
.logo {
    height: 50px;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    gap: 1rem;
}
.stTabs [data-baseweb="tab"] {
    padding: 0.8rem 1.2rem;
    border-radius: 8px;
    background-color: #f3f4f6;
    color: #111827;
    font-weight: 500;
}
.stTabs [data-baseweb="tab"][aria-selected="true"] {
    background-color: #003366;
    color: white;
}

/* Botones */
.stButton > button {
    background-color: #003366;
    color: white;
    border-radius: 8px;
    font-weight: 600;
    padding: 0.6rem 1.2rem;
}
.stButton > button:hover {
    background-color: #0055a4;
    color: white;
}
</style>
""", unsafe_allow_html=True)

# ================================================================
# CABECERA CON LOGO
# ================================================================
col1, col2 = st.columns([6, 1])
with col1:
    st.markdown("""
    <div class='header-container'>
        <div class='header-title'>
            📐 Calculadora Geodésica UTM - <b>ICCCONSA E.I.R.L.</b><br>
            <small>      Ingeniería, Construcción y Consultoría</small>
        </div>
    </div>
    """, unsafe_allow_html=True)
with col2:
    st.image("https://i.ibb.co/hV6Gh4y/iccconsa-logo.png", width=90)

st.markdown("")

# ================================================================
# FUNCIONES
# ================================================================
def decimal_a_dms(valor, latitud=True, num_decimales=5):
    try:
        valor = float(valor)
    except ValueError:
        return "Error"
    grados = int(valor)
    minutos_dec = abs((valor - grados) * 60)
    minutos = int(minutos_dec)
    segundos = (minutos_dec - minutos) * 60
    hemi = ("N" if valor >= 0 else "S") if latitud else ("E" if valor >= 0 else "W")
    return f"{abs(grados)}° {minutos}' {segundos:.{num_decimales}f}\" {hemi}"

def calcular_factor_escala(utm_proj, lat, lon, alt1):
    factors = utm_proj.get_factors(lon, lat)
    factor_map = factors.meridional_scale
    factor_nivelmar = 6378000 / (6378000 + alt1)
    factor_comb = factor_map * factor_nivelmar
    return factor_comb, factor_map, factor_nivelmar

# ================================================================
# SIDEBAR
# ================================================================
st.sidebar.header("⚙️ Parámetros")
zona = st.sidebar.selectbox("Zona UTM (Sur)", ["17", "18", "19"], index=1)
dec_factor = st.sidebar.number_input("Decimales - Factores", min_value=0, max_value=15, value=10)
dec_dms = st.sidebar.number_input("Decimales - Geodésicas (DMS)", min_value=0, max_value=10, value=5)
uploaded_file = st.sidebar.file_uploader("📂 Cargar archivo CSV con Encabezado E,N,H,Descripcion", type=["csv"])

st.sidebar.markdown("---")
st.sidebar.info("💡 Desarrollado Por:  ICCCONSA E.I.R.L.   \nVersión: 2025.11")

# ================================================================
# PESTAÑAS
# ================================================================
tab1, tab2, tab3, tab4 = st.tabs(["📄 Vista Previa", "🧮 Cálculo", "🗺️ Gráfico", "💾 Exportar"])

if "df_input" not in st.session_state:
    st.session_state.df_input = None
if "df_results" not in st.session_state:
    st.session_state.df_results = None
if "plotly_fig" not in st.session_state: # Para guardar la figura de Plotly
    st.session_state.plotly_fig = None

# ================================================================
 ##### COLOCA COLOR VERDE EN BOTON DE DESCARGA PLANTILLA
# ================================================================
# Definición del color corporativo y el CSS inyectado
# 🎨 1. Inyección de CSS para colorear SÓLO el botón de descarga con un Verde Corporativo
COLOR_VERDE_CORPORATIVO = "#00A36C" # Puedes cambiar este código por tu verde exacto

st.markdown(
    f"""
    <style>
    /* Apuntamos al último botón de descarga primario (type="primary") en la página.
    Esto aísla el estilo para que solo afecte a este botón y no a otros botones primarios.
    */
    div[data-testid="stDownloadButton-primary"]:last-of-type > button {{
        background-color: {COLOR_VERDE_CORPORATIVO} !important;
        border-color: {COLOR_VERDE_CORPORATIVO} !important;
        color: white !important;
    }}
    /* Estilo para el estado 'hover' (ratón encima) */
    div[data-testid="stDownloadButton-primary"]:last-of-type > button:hover {{
        background-color: #008759 !important; /* Un tono un poco más oscuro */
        border-color: #008759 !important;
        color: white !important;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)


# ================================================================
# TAB 1 - VISTA PREVIA
# ================================================================
with tab1:
    st.subheader("📄 Vista previa de datos")
    
    # FUNCIÓN PARA MOSTRAR EJEMPLO
    def mostrar_ejemplo_formato():
        st.subheader("📋 Formato correcto requerido:")
        ejemplo_data = {
            'E': [353531.9709, 353810.183, 354100.500, 354250.750],
            'N': [9263921.948, 9264002.834, 9264100.250, 9264250.100],
            'H': [248.6361, 247.3008, 246.1500, 245.8000],
            'Descripcion': ['SNM09022', 'SNM09023R', 'SNM09024', 'SNM09025']
        }
        df_ejemplo = pd.DataFrame(ejemplo_data)
        
        # 🟢 2. Ocultar la primera columna (el índice) al mostrar el DataFrame
        st.dataframe(df_ejemplo, use_container_width=True, hide_index=True)
        
        # Opción para descargar template
        csv_template = df_ejemplo.to_csv(index=False)
        st.download_button(
            label="📥 Descargar Plantilla de Ejemplo",
            data=csv_template,
            file_name="template_formato_correcto.csv",
            mime="text/csv",
            # Se usa type="primary" para que el CSS inyectado pueda identificarlo y colorearlo.
            type="primary"
        )
    
    # EL RESTO DEL CÓDIGO PERMANECE IGUAL
    if uploaded_file:
        try:
            df_input = pd.read_csv(uploaded_file)
            required_cols = {'E', 'N', 'H', 'Descripcion'}
            
            if not required_cols.issubset(df_input.columns):
                st.error(f"❌ El Archivo .CSV debe de tener como encabezado: E,N,H,Descripcion")
                mostrar_ejemplo_formato()
                
            else:
                # Convertir a numérico
                df_input['E'] = pd.to_numeric(df_input['E'], errors='coerce')
                df_input['N'] = pd.to_numeric(df_input['N'], errors='coerce')
                df_input['H'] = pd.to_numeric(df_input['H'], errors='coerce')
                
                if df_input[['E', 'N', 'H']].isnull().values.any():
                    st.error("🚨 Error: Las columnas 'E', 'N' y 'H' deben contener solo valores numéricos.")
                    mostrar_ejemplo_formato()
                else:
                    st.session_state.df_input = df_input
                    st.dataframe(df_input, use_container_width=True)
                    st.success("✅ Archivo cargado correctamente.")
                    
        except pd.errors.ParserError:
            st.error("❌ Error al leer el archivo CSV. Verifica el formato (delimitador, encoding, etc.).")
            mostrar_ejemplo_formato()
            
        except Exception as e:
            st.error(f"❌ Error inesperado: {e}")
            mostrar_ejemplo_formato()
            
    else:
        st.info("👆 Carga un archivo CSV desde la barra lateral.")

# ================================================================
# TAB 2 - CÁLCULO
# ================================================================
with tab2:
    st.subheader("🧮 Resultados geodésicos y factores de escala")
    if st.session_state.df_input is not None:
        if st.button("Calcular"):
            try:
                df_input = st.session_state.df_input.copy() # Usar una copia
                epsg_code = f"327{zona}"
                utm_proj = Proj(proj='utm', zone=int(zona), south=True, ellps='WGS84')
                transformer = Transformer.from_crs(f"EPSG:{epsg_code}", "EPSG:4326", always_xy=True)

                resultados = []
                for _, row in df_input.iterrows():
                    E_utm, N_utm, alt1, desc = row['E'], row['N'], row['H'], row['Descripcion']
                    lon, lat = transformer.transform(E_utm, N_utm)
                    factor_comb, factor_map, factor_nivelmar = calcular_factor_escala(utm_proj, lat, lon, alt1)
                    
                    factor_comb_str = f"{factor_comb:.{dec_factor}f}"
                    factor_map_str = f"{factor_map:.{dec_factor}f}"
                    factor_nivelmar_str = f"{factor_nivelmar:.{dec_factor}f}"

                    resultados.append({
                        "Codigo": desc,
                        "E_utm": E_utm,
                        "N_utm": N_utm,
                        "Altura_m": alt1,
                        "Latitud (DEC)": lat,
                        "Longitud (DEC)": lon,
                        "Latitud (DMS)": decimal_a_dms(lat, True, dec_dms),
                        "Longitud (DMS)": decimal_a_dms(lon, False, dec_dms),
                        "Factor_combinado": factor_comb_str, 
                        "Factor_escala": factor_map_str,      
                        "Factor_altura": factor_nivelmar_str  
                    })

                st.session_state.df_results = pd.DataFrame(resultados)
                st.success("✅ Cálculo completado correctamente.")
                st.dataframe(st.session_state.df_results, use_container_width=True)
            except Exception as e:
                st.error(f"Ocurrió un error: {e}")
    else:
        st.warning("⚠️ Carga un archivo en la pestaña 'Vista Previa'.")

# ================================================================
# TAB 3 - GRÁFICO (AHORA CON PLOTLY)
# ================================================================
with tab3:
    st.subheader("🗺️ Distribución de puntos UTM (Interactivo)")
    if st.session_state.df_results is not None:
        df = st.session_state.df_results.copy() # Trabajar con una copia

        # Asegurarse de que las columnas E_utm y N_utm sean numéricas
        df['E_utm'] = pd.to_numeric(df['E_utm'], errors='coerce')
        df['N_utm'] = pd.to_numeric(df['N_utm'], errors='coerce')

        # Crear el gráfico de dispersión interactivo con Plotly Express
        fig_plotly = px.scatter(df, 
                                x="E_utm", 
                                y="N_utm", 
                                text="Codigo", 
                                title=f"Puntos UTM - Zona {zona}S",
                                labels={"E_utm": "Este (m)", "N_utm": "Norte (m)"},
                                hover_data={
                                    "Codigo": True,
                                    "E_utm": ":.2f", 
                                    "N_utm": ":.2f", 
                                    "Altura_m": ":.2f",
                                    "Latitud (DMS)": True,
                                    "Longitud (DMS)": True
                                },
                                height=600 
                               )
        
        # 1. ESTILO DE LOS PUNTOS (ROJO Y TRIÁNGULO)
        fig_plotly.update_traces(
            marker=dict(
                size=12, 
                symbol='triangle-up', 
                color='red'           
            ),
            textposition='middle right'
        )
        
        # 2. AJUSTE DE EJES (ASPECTO 1:1 Y FORMATO COMPLETO)
        fig_plotly.update_layout(
            hovermode="closest", 
            xaxis_title="Este (m)",
            yaxis_title="Norte (m)",
            template="plotly_white" 
        )
        
        # *** MODIFICACIÓN CLAVE: Aplicar tickformat para números completos con separador de miles ***
        fig_plotly.update_xaxes(tickformat = ',.0f') # Ejemplo: 350,000
        fig_plotly.update_yaxes(
            tickformat = ',.0f', # Ejemplo: 9,260,000
            scaleanchor="x", 
            scaleratio=1     
        )
        
        # Guardar la figura de Plotly en el estado de la sesión
        st.session_state.plotly_fig = fig_plotly
        
        st.plotly_chart(fig_plotly, use_container_width=True)
    else:
        st.info("👆 Calcula los resultados antes de mostrar el gráfico.")

with tab4:
    st.subheader("💾 Exportar resultados a Excel")
    
    # Se cambia el texto del botón para reflejar que solo exporta datos
    if st.session_state.df_results is not None:
        if st.button("Generar Excel con datos"):
# ... (Bloque TAB 4 - EXPORTAR)

            try:
                df_results = st.session_state.df_results.copy()
                excel_file = f"Resultados_UTM_ICCCONSA_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                
                # Convertir las columnas de factores de STRING a numérico (float)
                for col in ["Factor_combinado", "Factor_escala", "Factor_altura"]:
                    # Ahora 'np' está definido y funciona
                    df_results[col] = pd.to_numeric(df_results[col], errors='coerce').astype(np.float64) 
                
# ... (El resto del código de exportación permanece igual)
                
                # Eliminar las columnas de Latitud/Longitud Decimal si existen
                df_export = df_results.drop(columns=["Latitud (DEC)", "Longitud (DEC)"], errors='ignore')
                
                # Usar ExcelWriter para gestionar hojas y formatos
                with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
                    # Escribir datos, aplicando el formato de decimales del parámetro 'dec_factor'
                    df_export.to_excel(
                        writer, 
                        sheet_name='Resultados UTM', 
                        index=False, 
                        float_format=f"%.{dec_factor}f" # Aplica el formato de decimales del parámetro
                    )
                
                # Enlace de descarga
                with open(excel_file, "rb") as f:
                    st.download_button(
                        label="⬇️ Descargar Excel",
                        data=f,
                        file_name=excel_file,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                st.success("Archivo Excel generado con éxito ✅")
                
                # OPCIONAL: Se elimina el archivo .xlsx generado si ya se descargó
                # os.remove(excel_file) 
                
            except Exception as e:
                st.error(f"Error al exportar: {e}")
    else:
        st.info("👆 Calcula primero los resultados antes de exportar.")

# =====================================================
# 🔗 Redes Sociales (con íconos oficiales)
# =====================================================
st.sidebar.markdown("## Conéctate con Nosotros")

# Usamos columnas pequeñas para colocar los íconos en fila
col_yt, col_wa, col_fb, col_tk = st.sidebar.columns(4)

# --- YouTube ---
col_yt.markdown(
    """
    <a href="https://www.youtube.com/@ICCCONSAEIRL" target="_blank">
        <img src="https://cdn-icons-png.flaticon.com/512/1384/1384060.png" width="25">
    </a>
    """,
    unsafe_allow_html=True
)

# --- WhatsApp ---
col_wa.markdown(
    """
    <a href="https://wa.link/gwbj7w" target="_blank">
        <img src="https://cdn-icons-png.flaticon.com/512/733/733585.png" width="25">
    </a>
    """,
    unsafe_allow_html=True
)

# --- Facebook ---
col_fb.markdown(
    """
    <a href="https://www.facebook.com/nexon.vilca" target="_blank">
        <img src="https://cdn-icons-png.flaticon.com/512/733/733547.png" width="25">
    </a>
    """,
    unsafe_allow_html=True
)

# --- TikTok ---
col_tk.markdown(
    """
    <a href="https://www.tiktok.com/@nexonvilca" target="_blank">
        <img src="https://cdn-icons-png.flaticon.com/512/3046/3046121.png" width="25">
    </a>
    """,
    unsafe_allow_html=True
)

# Separador visual
st.sidebar.markdown("---")

# ================================================================
#  correr el codigo :::   streamlit run app_iccconsa.py
# ================================================================ 