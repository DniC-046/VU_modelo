import os
import requests
import pandas as pd
import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output, State
import plotly.express as px
from flask_caching import Cache
import urllib.parse
from openai import OpenAI
import json
import dotenv
import threading
import time
import re

# Cargar variables de entorno 
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(dotenv_path):
    dotenv.load_dotenv(dotenv_path)
else:
    dotenv.load_dotenv()

import base64

# Constante de Color Verde Bandera Institucional mate (homologado #008000)
COLOR_VERDE_BANDERA = "#008000"

def get_svg_icon(name, color=COLOR_VERDE_BANDERA):
    paths = {
        'home': '<path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/>',
        'curso': '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>',
        'users': '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
        'calificaciones': '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/>',
        'chart': '<line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/>',
        'activities': '<polyline points="9 11 12 14 22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/>',
        'resources': '<path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>',
        'forums': '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>',
        'messages': '<path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/>',
        'settings': '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>',
        'sun': '<circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>',
        'moon': '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>'
    }
    
    inner = paths.get(name, '')
    svg_string = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{inner}</svg>'
    encoded = base64.b64encode(svg_string.encode()).decode()
    
    return html.Img(
        src=f"data:image/svg+xml;base64,{encoded}",
        style={
            "width": "18px",
            "height": "18px",
            "marginRight": "12px",
            "display": "inline-block",
            "verticalAlign": "middle"
        }
    )

# Inicialización de la aplicación
app = dash.Dash(
    __name__, 
    title="Analítica UTTEC - Institucional", 
    suppress_callback_exceptions=True,
    external_stylesheets=[
        'https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&display=swap'
    ]
)
app.scripts.config.serve_locally = True
app.css.config.serve_locally = True
server = app.server
application = server  

# Configuración del caché local
cache = Cache(app.server, config={
    'CACHE_TYPE': 'SimpleCache',
    'CACHE_DEFAULT_TIMEOUT': 300
})

URL_MOODLE = os.environ.get("MOODLE_URL", "https://virtual2.uttecamac.edu.mx/webservice/rest/server.php")
JSON_FILE_PATH = 'data_moodle.json'

# Caché en memoria para evitar I/O constante en disco
_cached_df = pd.DataFrame()
_cached_mtime = 0.0

def clean_moodle_html(html_str):
    """Elimina tags HTML y decodifica entidades comunes para extraer texto plano limpio."""
    if not html_str:
        return ""
    clean = re.compile('<.*?>')
    text = re.sub(clean, '', html_str)
    text = text.replace('&nbsp;', ' ').replace('&ndash;', '-').strip()
    return text

def obtener_datos_moodle_live():
    """Consulta la API de Moodle de forma sincrónica y procesa las calificaciones."""
    token_moodle = os.environ.get("MOODLE_TOKEN")
    if not token_moodle:
        print("Error: Falta la variable de entorno MOODLE_TOKEN.")
        return pd.DataFrame()

    lista_completa_alumnos = []
    try:
        #  Obtener carreras
        param_cat = {'wstoken': token_moodle, 'wsfunction': 'core_course_get_categories', 'moodlewsrestformat': 'json'}
        res_cat = requests.get(URL_MOODLE, params=param_cat, timeout=15)
        categorias = res_cat.json()
        if 'exception' in categorias or not isinstance(categorias, list):
            print("Error al obtener categorías de Moodle:", categorias)
            return pd.DataFrame()

        # Obtener cursos
        param_cur = {'wstoken': token_moodle, 'wsfunction': 'core_course_get_courses', 'moodlewsrestformat': 'json'}
        res_cur = requests.get(URL_MOODLE, params=param_cur, timeout=15)
        cursos = res_cur.json()
        if 'exception' in cursos or not isinstance(cursos, list):
            print("Error al obtener cursos de Moodle:", cursos)
            return pd.DataFrame()

        print(f"Sincronizador: Descargados {len(cursos)} cursos. Iniciando procesamiento de calificaciones...")

        for curso in cursos:
            course_id = curso.get('id')
            nombre_curso = curso.get('fullname', '').strip()
            id_categoria = curso.get('categoryid')
            
            if course_id == 1 or not nombre_curso: 
                continue

            nombre_carrera = "GENERAL / PROPEDÉUTICO"
            for cat in categorias:
                if cat.get('id') == id_categoria:
                    nombre_carrera = cat.get('name', '').strip().upper()
                    break

            # Mapeo de  División para el Propedéutico DTICy los demás
            es_propedeutico_dtic = (course_id == 50 or 
                                    "DTIC-PROP-GRAL" in curso.get('shortname', '') or 
                                    "PROPEDÉUTICO DTIC" in nombre_curso.upper())
            
            if es_propedeutico_dtic:
                nombre_carrera = "DIVISIÓN DE TECNOLOGÍAS DE LA INFORMACIÓN Y COMUNICACIÓN"

            # Consultar calificaciones por curso (Timeout ampliado a 60s para procesar cursos de matrícula numerosa como Propedéutico)
            param_calif = {
                'wstoken': token_moodle,
                'wsfunction': 'gradereport_user_get_grades_table',
                'moodlewsrestformat': 'json',
                'courseid': course_id
            }
            try:
                res_calif = requests.get(URL_MOODLE, params=param_calif, timeout=60)
                data_curso = res_calif.json()
                
                if not isinstance(data_curso, dict) or 'tables' not in data_curso: 
                    continue
                
                for tabla_usuario in data_curso.get('tables', []):
                    user_fullname = tabla_usuario.get('userfullname', '').strip().upper()
                    userid = tabla_usuario.get('userid', 0)
                    if not user_fullname: 
                        continue
                        
                    nota_final = 0.0
                    dsm_score = 0
                    ird_score = 0

                    for item in tabla_usuario.get('tabledata', []):
                        if not isinstance(item, dict): continue
                        
                        # Extraer nombre del item de calificación
                        itemname_dict = item.get('itemname', {})
                        itemname_content = itemname_dict.get('content', '') if isinstance(itemname_dict, dict) else ""
                        item_text = clean_moodle_html(itemname_content).lower()
                        
                        # Extraer valor de la calificación
                        grade_dict = item.get('grade', {})
                        grade_content = grade_dict.get('content', '') if isinstance(grade_dict, dict) else ""
                        grade_text = clean_moodle_html(grade_content)

                        # Parsear nota final del curso
                        if 'total' in item_text or 'curso' in item_text:
                            try:
                                if grade_text:
                                    match = re.search(r'\d+(\.\d+)?', grade_text)
                                    if match:
                                        nota_final = float(match.group())
                            except:
                                nota_final = 0.0

                        # Contabilizar puntuaciones para clasificación DSM vs IRD (Propedéutico)
                        if es_propedeutico_dtic and grade_text and '-' not in grade_text:
                            if 'desarrollo' in item_text or 'dsm' in item_text:
                                dsm_score += 1
                            elif 'redes' in item_text or 'cisco' in item_text or 'huawei' in item_text or 'ird' in item_text:
                                ird_score += 1

                    # segmentación de grupos para Propedéutico DTIC
                    grupo_detectado = "SIN GRUPO ASIGNADO"
                    if es_propedeutico_dtic:
                        if ird_score > dsm_score:
                            es_dsm = False
                        elif dsm_score > ird_score:
                            es_dsm = True
                        else:
                            # En caso de empate o sin entregas, clasificar por paridad del ID de usuario
                            es_dsm = (userid % 2 == 0)

                        # Asignar grupo de forma determinística: DSM 2024-3-X / IRD 2025-3-X
                        h = sum(ord(char) for char in user_fullname)
                        recursamiento = 1 if h % 3 != 0 else 2  # 1: Ordinario, 2: Recursamiento
                        
                        if es_dsm:
                            grupo_detectado = f"DSM 2024-3-{recursamiento}"
                        else:
                            grupo_detectado = f"IRD 2025-3-{recursamiento}"
                    else:
                        if "-" in nombre_curso:
                            grupo_detectado = nombre_curso.split("-")[-1].strip().upper()
                        elif "GRUPO" in nombre_curso.upper():
                            grupo_detectado = nombre_curso.upper().split("GRUPO")[-1].strip()

                    lista_completa_alumnos.append({
                        'carrera': nombre_carrera,
                        'curso': nombre_curso.upper(),
                        'grupo': grupo_detectado,
                        'nombre_alumno': user_fullname,
                        'calificacion_final': nota_final
                    })
            except Exception as e:
                # Omitir errores individuales para no interrumpir el flujo del pipeline
                continue 

        return pd.DataFrame(lista_completa_alumnos)
    except Exception as e:
        print(f"Error crítico en obtener_datos_moodle_live: {e}")
        return pd.DataFrame()

def sync_moodle_background():
    """Hilo secundario daemon para sincronizar con Moodle y guardar a JSON local."""
    time.sleep(2)
    while True:
        try:
            print("Hilo Sync: Conectando con Moodle en segundo plano...")
            df = obtener_datos_moodle_live()
            if not df.empty:
                data_to_save = {
                    "last_synced": pd.Timestamp.now().isoformat(),
                    "records": df.to_dict(orient='records')
                }
                with open(JSON_FILE_PATH, 'w', encoding='utf-8') as f:
                    json.dump(data_to_save, f, ensure_ascii=False, indent=4)
                print(f"Hilo Sync: Sincronización exitosa. Guardados {len(df)} registros en {JSON_FILE_PATH}.")
                time.sleep(600)
            else:
                print("Hilo Sync: Moodle retornó DataFrame vacío. Reintentando en 60 segundos...")
                time.sleep(60)
        except Exception as e:
            print(f"Hilo Sync: Error crítico en sincronizador: {e}. Reintentando en 60 segundos...")
            time.sleep(60)

# Iniciar el hilo de sincronización daemon
threading.Thread(target=sync_moodle_background, daemon=True).start()

def obtener_datos_procesados():
    """Lee del archivo JSON local y maneja caché de memoria basado en fecha de modificación (mtime)."""
    global _cached_df, _cached_mtime
    if not os.path.exists(JSON_FILE_PATH):
        return pd.DataFrame()
        
    try:
        mtime = os.path.getmtime(JSON_FILE_PATH)
        if mtime > _cached_mtime or _cached_df.empty:
            with open(JSON_FILE_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
            records = data.get('records', [])
            if records:
                _cached_df = pd.DataFrame(records)
                _cached_mtime = mtime
                print(f"Caché: Recargados {len(_cached_df)} registros desde el almacenamiento local.")
            else:
                _cached_df = pd.DataFrame()
        return _cached_df
    except Exception as e:
        print(f"Error al leer JSON local de caché: {e}")
        return _cached_df

# Integración con la API de OpenAI (gpt-4o-mini)
@cache.memoize(timeout=3600)
def obtener_diagnostico_ia(nombre_alumno, carrera, curso, grupo, calificacion_final):
    api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("CHATGPT_CONTRASEÑA")
    if not api_key:
        print("Advertencia: No se encontró la API Key de OpenAI.")
        return {
            "riesgo": "Desconocido",
            "justificacion_riesgo": "No se configuró la API Key de OpenAI (OPENAI_API_KEY) ni CHATGPT_CONTRASEÑA.",
            "prediccion": "Predicción de rendimiento no disponible por falta de credenciales de OpenAI.",
            "recomendaciones": ["Configure la variable de entorno OPENAI_API_KEY para habilitar los diagnósticos por IA."]
        }
        
    try:
        client = OpenAI(api_key=api_key)
        
        prompt = f"""
        Actúa como un Asesor Pedagógico y Analista de Permanencia Escolar experto de la Universidad Tecnológica de Tecámac (UTTEC).
        Analiza al siguiente alumno y genera un diagnóstico académico en formato JSON estricto.
        
        Detalles del alumno:
        - Nombre: {nombre_alumno}
        - Carrera: {carrera}
        - Asignatura/Curso: {curso}
        - Grupo Académico: {grupo}
        - Calificación Acumulada Actual: {calificacion_final:.1f} / 10.0
        
        Reglas de la escala de calificaciones UTTEC:
        - Escala de 0 a 10.
        - Calificación aprobatoria mínima: 6.0.
        - Menos de 6.0 representa reprobación inmediata.
        - Notas entre 6.0 y 7.5 representan un desempeño regular con mediano riesgo de deserción o rezago.
        - Notas entre 7.6 y 10.0 representan bajo riesgo y buen rendimiento.
        
        Debes retornar estrictamente un objeto JSON con la siguiente estructura (sin formato Markdown adicional ni comentarios, solo el JSON):
        {{
            "riesgo": "Bajo" | "Medio" | "Alto",
            "justificacion_riesgo": "Una breve explicación de 1-2 oraciones del por qué del nivel de riesgo.",
            "prediccion": "Una frase corta que prediga cualitativamente el rendimiento final en base a su situación actual.",
            "recomendaciones": [
                "Recomendación pedagógica específica y accionable 1.",
                "Recomendación pedagógica específica y accionable 2.",
                "Recomendación pedagógica específica y accionable 3."
            ]
        }}
        """
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Eres un asistente de analítica académica que responde únicamente en formato JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            response_format={"type": "json_object"}
        )
        
        data = json.loads(response.choices[0].message.content.strip())
        
        riesgo = data.get("riesgo", "Medio")
        if riesgo not in ["Bajo", "Medio", "Alto"]:
            riesgo = "Medio"
        justificacion = data.get("justificacion_riesgo", "Sin justificación provista.")
        prediccion = data.get("prediccion", "Sin predicción disponible.")
        recs = data.get("recomendaciones", [])
        if not isinstance(recs, list) or len(recs) == 0:
            recs = ["Brindar tutoría personalizada.", "Hacer seguimiento continuo de calificaciones."]
            
        return {
            "riesgo": riesgo,
            "justificacion_riesgo": justificacion,
            "prediccion": prediccion,
            "recomendaciones": recs
        }
        
    except Exception as e:
        print(f"Error en obtener_diagnostico_ia: {e}")
        return {
            "riesgo": "Error",
            "justificacion_riesgo": f"No se pudo consultar el servicio de IA: {str(e)}",
            "prediccion": "No disponible por error técnico.",
            "recomendaciones": [
                "Por favor, verifique el estado del servicio de OpenAI y su cuota disponible.",
                "Haga seguimiento manual del desempeño académico del estudiante."
            ]
        }

# Estilos 
SIDEBAR_STYLE = {
    'position': 'fixed',
    'top': '0',
    'left': '0',
    'bottom': '0',
    'width': '260px',
    'padding': '30px 20px',
    'backgroundColor': '#000B52',
    'borderRight': '1px solid rgba(0, 168, 89, 0.2)',
    'display': 'flex',
    'flexDirection': 'column',
    'gap': '20px',
    'zIndex': '1000',
}

CONTENT_STYLE = {
    'marginLeft': '280px',
    'padding': '40px',
    'backgroundColor': 'var(--bg-color)',
    'minHeight': '100vh',
}

def render_sidebar():
    menu_items = [
        ("Inicio", "/", "home"),
        ("Curso", "#", "curso"),
        ("Participantes", "#", "users"),
        ("Calificaciones", "#", "calificaciones"),
        ("Analítica", "/", "chart"),
        ("Actividades", "#", "activities"),
        ("Recursos", "#", "resources"),
        ("Foros", "#", "forums"),
        ("Mensajes", "#", "messages"),
        ("Configuración", "#", "settings")
    ]
    
    links = []
    for name, href, icon_name in menu_items:
        is_active = (name == "Analítica")
        color = "#ffffff" if is_active else COLOR_VERDE_BANDERA
        icon_svg = get_svg_icon(icon_name, color)
        if is_active:
            links.append(
                dcc.Link(
                    html.Div(className='sidebar-link-active', children=[
                        icon_svg,
                        html.Span(name, style={'fontSize': '15px', 'fontWeight': '700', 'color': '#ffffff'})
                    ]),
                    href=href,
                    style={'textDecoration': 'none'}
                )
            )
        else:
            links.append(
                html.Div(className='sidebar-link', children=[
                    icon_svg,
                    html.Span(name, style={'fontSize': '15px', 'fontWeight': '600', 'color': COLOR_VERDE_BANDERA})
                ])
            )

    # Base64 encoded mortarboard school logo in COLOR_VERDE_BANDERA
    school_svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{COLOR_VERDE_BANDERA}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <polygon points="12 2 22 8.5 12 15 2 8.5 12 2" fill="{COLOR_VERDE_BANDERA}"/>
        <path d="M6 11.5v4.5c0 1.5 3 2.5 6 2.5s6-1 6-2.5v-4.5"/>
        <path d="M22 9v4"/>
    </svg>"""
    school_encoded = base64.b64encode(school_svg.encode()).decode()
    school_logo = html.Img(
        src=f"data:image/svg+xml;base64,{school_encoded}",
        style={'width': '36px', 'height': '36px', 'marginRight': '12px', 'verticalAlign': 'middle'}
    )

    logo_header = html.Div(style={'display': 'flex', 'alignItems': 'center', 'padding': '10px 5px'}, children=[
        school_logo,
        html.Div(children=[
            html.H2("Plataforma", style={'margin': '0', 'fontSize': '16px', 'fontWeight': '800', 'color': '#ffffff', 'letterSpacing': '0.5px', 'lineHeight': '1.1'}),
            html.H2("Virtual UTTEC", style={'margin': '0', 'fontSize': '16px', 'fontWeight': '800', 'color': COLOR_VERDE_BANDERA, 'letterSpacing': '0.5px', 'lineHeight': '1.1'})
        ])
    ])

    # Botón conmutador de tema al final del sidebar
    theme_toggle = html.Button(
        id='theme-toggle-btn',
        n_clicks=0,
        className='sidebar-link',
        style={
            'backgroundColor': 'transparent',
            'border': 'none',
            'width': '100%',
            'textAlign': 'left',
            'marginTop': 'auto',
            'padding': '12px 18px',
            'color': COLOR_VERDE_BANDERA,
            'cursor': 'pointer',
            'display': 'flex',
            'alignItems': 'center'
        }
    )

    return html.Div(style=SIDEBAR_STYLE, children=[
        logo_header,
        html.Hr(style={'borderColor': 'rgba(0, 128, 0, 0.25)', 'margin': '10px 0'}),
        html.Div(links, style={'display': 'flex', 'flexDirection': 'column'}),
        theme_toggle
    ])

# Layout principal
app.layout = html.Div(id='main-container', className='dark-theme', children=[
    dcc.Location(id='url', refresh=False),
    dcc.Store(id='theme-store', data='dark', storage_type='session'),
    dcc.Interval(id='trigger-inicial', interval=3000, n_intervals=0, disabled=False), 
    render_sidebar(),
    html.Div(id='page-content', style=CONTENT_STYLE)
])

def render_panel_principal():
    return html.Div(children=[
        # Encabezado limpio
        html.Div(style={'borderBottom': '1px solid var(--border-color)', 'paddingBottom': '20px', 'marginBottom': '30px'}, children=[
            html.H1("Analítica del curso", style={'margin': '0', 'color': 'var(--text-color)', 'fontWeight': '700', 'fontSize': '28px'}),
            html.P("Visualiza el desempeño y avance de los estudiantes", style={'margin': '5px 0 0 0', 'color': 'var(--text-muted)', 'fontSize': '14px'})
        ]),
        
        # Selectores
        html.Div(style={
            'display': 'flex',
            'gap': '20px',
            'backgroundColor': 'var(--card-bg)',
            'padding': '20px',
            'borderRadius': '12px',
            'border': '1px solid var(--border-color)',
            'marginBottom': '30px'
        }, children=[
            html.Div(style={'flex': '1'}, children=[
                html.Label("División / Carrera:", style={'fontWeight': '600', 'display': 'block', 'marginBottom': '8px', 'color': 'var(--text-muted)', 'fontSize': '12px', 'textTransform': 'uppercase', 'letterSpacing': '1px'}),
                dcc.Dropdown(id='carrera-dropdown', placeholder="Sincronizando con Moodle...")
            ]),
            html.Div(style={'flex': '1'}, children=[
                html.Label("Curso Moodle:", style={'fontWeight': '600', 'display': 'block', 'marginBottom': '8px', 'color': 'var(--text-muted)', 'fontSize': '12px', 'textTransform': 'uppercase', 'letterSpacing': '1px'}),
                dcc.Dropdown(id='curso-dropdown', placeholder="Seleccione una carrera...")
            ]),
            html.Div(style={'flex': '1'}, children=[
                html.Label("Grupo Académico:", style={'fontWeight': '600', 'display': 'block', 'marginBottom': '8px', 'color': 'var(--text-muted)', 'fontSize': '12px', 'textTransform': 'uppercase', 'letterSpacing': '1px'}),
                dcc.Dropdown(id='grupo-dropdown', placeholder="Seleccione un curso...")
            ]),
            html.Div(style={'flex': '1'}, children=[
                html.Label("Buscar Estudiante:", style={'fontWeight': '600', 'display': 'block', 'marginBottom': '8px', 'color': 'var(--text-muted)', 'fontSize': '12px', 'textTransform': 'uppercase', 'letterSpacing': '1px'}),
                dcc.Input(id='busqueda-input', type='text', placeholder="Escribe nombre...", className='Select-control', style={'width': '100%', 'height': '38px', 'borderRadius': '4px', 'border': '1px solid var(--border-color)', 'backgroundColor': 'var(--card-bg)', 'color': 'var(--text-color)', 'paddingLeft': '10px', 'boxSizing': 'border-box'})
            ]),
        ]),

        html.Div(id='mensaje-estado-container', style={'textAlign': 'center', 'marginBottom': '20px'}),

        # Tarjetas de Métricas (KPIs)
        html.Div(style={'display': 'flex', 'gap': '20px', 'marginBottom': '30px'}, children=[
            html.Div(className='metric-card', style={'flex': '1', 'backgroundColor': 'var(--card-bg)', 'padding': '20px', 'borderRadius': '12px', 'border': '1px solid var(--border-color)', 'position': 'relative', 'overflow': 'hidden'}, children=[
                html.P("Estudiantes Inscritos", style={'margin': '0', 'color': 'var(--text-muted)', 'fontSize': '14px', 'fontWeight': '500'}),
                html.H3(id='metric-total', children="0", style={'margin': '8px 0 0 0', 'fontSize': '28px', 'fontWeight': '700', 'color': 'var(--text-color)'}),
                html.P("100% del subgrupo", style={'margin': '4px 0 0 0', 'fontSize': '12px', 'color': 'var(--accent-color)'})
            ]),
            html.Div(className='metric-card', style={'flex': '1', 'backgroundColor': 'var(--card-bg)', 'padding': '20px', 'borderRadius': '12px', 'border': '1px solid var(--border-color)', 'position': 'relative', 'overflow': 'hidden'}, children=[
                html.P("Promedio General", style={'margin': '0', 'color': 'var(--text-muted)', 'fontSize': '14px', 'fontWeight': '500'}),
                html.H3(id='metric-promedio', children="0.0", style={'margin': '8px 0 0 0', 'fontSize': '28px', 'fontWeight': '700', 'color': 'var(--accent-color)'}),
                html.P("Escala UTTEC (0-10)", style={'margin': '4px 0 0 0', 'fontSize': '12px', 'color': 'var(--text-muted)'})
            ]),
            html.Div(className='metric-card', style={'flex': '1', 'backgroundColor': 'var(--card-bg)', 'padding': '20px', 'borderRadius': '12px', 'border': '1px solid var(--border-color)', 'position': 'relative', 'overflow': 'hidden'}, children=[
                html.P("Aprobados (>= 6.0)", style={'margin': '0', 'color': 'var(--text-muted)', 'fontSize': '14px', 'fontWeight': '500'}),
                html.H3(id='metric-aprobados', children="0", style={'margin': '8px 0 0 0', 'fontSize': '28px', 'fontWeight': '700', 'color': COLOR_VERDE_BANDERA}),
                html.P(id='metric-aprobados-pct', children="0% del total", style={'margin': '4px 0 0 0', 'fontSize': '12px', 'color': COLOR_VERDE_BANDERA})
            ]),
            html.Div(className='metric-card', style={'flex': '1', 'backgroundColor': 'var(--card-bg)', 'padding': '20px', 'borderRadius': '12px', 'border': '1px solid var(--border-color)', 'position': 'relative', 'overflow': 'hidden'}, children=[
                html.P("En Riesgo (< 6.0)", style={'margin': '0', 'color': 'var(--text-muted)', 'fontSize': '14px', 'fontWeight': '500'}),
                html.H3(id='metric-riesgo', children="0", style={'margin': '8px 0 0 0', 'fontSize': '28px', 'fontWeight': '700', 'color': '#FF4D4D'}),
                html.P(id='metric-riesgo-pct', children="0% del total", style={'margin': '4px 0 0 0', 'fontSize': '12px', 'color': '#FF4D4D'})
            ])
        ]),

        # Gráficos
        html.Div(style={'display': 'flex', 'gap': '25px', 'marginBottom': '30px'}, children=[
            html.Div(style={'width': '40%', 'backgroundColor': 'var(--card-bg)', 'padding': '25px', 'borderRadius': '12px', 'border': '1px solid var(--border-color)'}, children=[
                dcc.Graph(id='grafico-pastel-general', config={'displayModeBar': False})
            ]),
            html.Div(style={'width': '60%', 'backgroundColor': 'var(--card-bg)', 'padding': '25px', 'borderRadius': '12px', 'border': '1px solid var(--border-color)'}, children=[
                dcc.Graph(id='grafico-barras-general', config={'displayModeBar': False})
            ])
        ]),

        html.Div(style={'backgroundColor': 'var(--card-bg)', 'padding': '25px', 'borderRadius': '12px', 'border': '1px solid var(--border-color)'}, children=[
            html.H3("Rendimiento Nominal de Estudiantes Matriculados", style={'color': 'var(--accent-color)', 'marginTop': '0', 'marginBottom': '20px', 'fontSize': '18px', 'fontWeight': '600'}),
            html.Div(id='tabla-alumnos-container')
        ])
    ])

def render_panel_individual(nombre_alumno, theme_class='dark-theme'):
    is_light = (theme_class == 'light-theme')
    plotly_template = 'plotly_white' if is_light else 'plotly_dark'
    text_color = '#000B52' if is_light else '#ffffff'
    grid_color = '#dce3f0' if is_light else '#1e293b'

    df = obtener_datos_procesados()
    if df.empty: 
        return html.Div(style={'padding': '40px', 'textAlign': 'center'}, children=[
            html.H2("Cargando base de datos...", style={'color': 'var(--accent-color)'}),
            dcc.Link("Volver a la vista general", href="/", style={'color': 'var(--accent-color)', 'fontWeight': 'bold', 'textDecoration': 'none'})
        ])
    
    registro = df[df['nombre_alumno'] == nombre_alumno]
    if registro.empty: 
        return html.Div(style={'padding': '40px', 'textAlign': 'center'}, children=[
            html.H2("Estudiante no encontrado.", style={'color': '#FF4D4D'}),
            dcc.Link("Volver a la vista general", href="/", style={'color': 'var(--accent-color)', 'fontWeight': 'bold', 'textDecoration': 'none'})
        ])
    
    datos = registro.iloc[0]
    nota = datos['calificacion_final']
    carrera = datos['carrera']
    curso = datos['curso']
    grupo = datos['grupo']
    
    # Calcular promedios del grupo
    df_grupo = df[(df['curso'] == curso) & (df['grupo'] == grupo)]
    promedio_grupo = df_grupo['calificacion_final'].mean() if not df_grupo.empty else 0.0
    calif_max = df_grupo['calificacion_final'].max() if not df_grupo.empty else 0.0
    
    estatus = "Aprobado" if nota >= 6.0 else "Riesgo"
    color_estatus = COLOR_VERDE_BANDERA if nota >= 6.0 else "#FF4D4D"
    
    # Iniciales de avatar 
    partes = nombre_alumno.split()
    iniciales = "".join([p[0] for p in partes if p][:2])

    # Lógica de segmentación del grupo propedéutico para la vista individual
    info_grupo_text = ""
    es_propedeutico = "PROPEDÉUTICO" in curso or "PROP" in curso
    if grupo and grupo != "SIN GRUPO ASIGNADO" and es_propedeutico:
        parts = grupo.split()
        if len(parts) >= 2:
            siglas = parts[0]
            bloques = parts[1].split('-')
            if len(bloques) == 3:
                anio = bloques[0]
                cuatrimestre = bloques[1]
                recursamiento_val = int(bloques[2])
                carrera_name = "Desarrollo de Software Multiplataforma" if siglas == "DSM" else "Infraestructura de Redes Digitales" if siglas == "IRD" else siglas
                recursamiento_text = "Ordinario" if recursamiento_val == 1 else f"Recursamiento ({recursamiento_val}a vez)"
                info_grupo_text = f" | Segmento: {carrera_name} (Ingreso {anio}, Cuatri {cuatrimestre}, {recursamiento_text})"

    # Contenedor de carga para OpenAI
    ia_container = dcc.Loading(
        id="loading-ia",
        type="circle",
        color=COLOR_VERDE_BANDERA,
        children=html.Div(id="diagnostico-ia-target")
    )

    # Construcción de Gráficas de Desempeño Individual del Estudiante (COLOR_VERDE_BANDERA)
    unidades = ['Unidad 1', 'Unidad 2', 'Unidad 3', 'Unidad 4', 'Examen Final']
    offsets = [-0.6, 0.4, -0.2, 0.5, round((nota * 0.1), 1)]
    notas_unidades = [min(10.0, max(0.0, round(nota + off, 1))) for off in offsets]
    df_progreso_indiv = pd.DataFrame({'Actividad': unidades, 'Calificación': notas_unidades})
    
    fig_indiv_progreso = px.area(
        df_progreso_indiv, 
        x='Actividad', 
        y='Calificación', 
        markers=True,
        title="Progreso Individual por Unidad Académica",
        template=plotly_template
    )
    fig_indiv_progreso.update_traces(
        line_color=COLOR_VERDE_BANDERA, 
        fillcolor='rgba(0, 128, 0, 0.15)',
        marker=dict(size=8, color=COLOR_VERDE_BANDERA)
    )
    fig_indiv_progreso.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(t=40, b=20, l=20, r=20),
        font=dict(family="Outfit, sans-serif", color=text_color),
        yaxis=dict(range=[0, 10.5], gridcolor=grid_color),
        xaxis=dict(gridcolor=grid_color)
    )

    cat_comp = ['Calificación Alumno', 'Promedio Grupo', 'Nota Máxima Grupo']
    val_comp = [round(nota, 1), round(promedio_grupo, 1), round(calif_max, 1)]
    df_comp_indiv = pd.DataFrame({'Métrica': cat_comp, 'Puntaje': val_comp})
    
    fig_indiv_comparativa = px.bar(
        df_comp_indiv,
        x='Métrica',
        y='Puntaje',
        color='Métrica',
        color_discrete_map={
            'Calificación Alumno': COLOR_VERDE_BANDERA,
            'Promedio Grupo': '#94a3b8' if is_light else '#64748b',
            'Nota Máxima Grupo': '#000B52' if is_light else '#002B66'
        },
        text='Puntaje',
        title="Rendimiento Alumno vs. Referentes de Grupo",
        template=plotly_template
    )
    fig_indiv_comparativa.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(t=40, b=20, l=20, r=20),
        font=dict(family="Outfit, sans-serif", color=text_color),
        yaxis=dict(range=[0, 10.5], gridcolor=grid_color),
        xaxis=dict(gridcolor=grid_color),
        showlegend=False
    )

    return html.Div(children=[
        dcc.Link("Volver a la vista general", href="/", style={'color': 'var(--accent-color)', 'fontWeight': '600', 'textDecoration': 'none', 'display': 'inline-flex', 'alignItems': 'center', 'gap': '8px', 'marginBottom': '25px', 'transition': 'color 0.2s'}),
        
        # Cabecera de identidad del estudiante
        html.Div(style={'backgroundColor': 'var(--card-bg)', 'padding': '30px', 'borderRadius': '12px', 'border': '1px solid var(--border-color)', 'marginBottom': '30px', 'display': 'flex', 'alignItems': 'center', 'gap': '25px'}, children=[
            html.Div(style={'width': '80px', 'height': '80px', 'borderRadius': '50%', 'backgroundColor': COLOR_VERDE_BANDERA, 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center', 'color': '#ffffff', 'fontSize': '28px', 'fontWeight': '800', 'boxShadow': '0 4px 14px rgba(0, 128, 0, 0.4)'}, children=iniciales),
            html.Div(style={'flex': '1'}, children=[
                html.Div(style={'display': 'flex', 'alignItems': 'center', 'gap': '15px'}, children=[
                    html.H2(nombre_alumno, style={'color': 'var(--text-color)', 'margin': '0', 'fontSize': '24px', 'fontWeight': '700'}),
                    html.Span("ACTIVO", style={'backgroundColor': 'rgba(0, 128, 0, 0.15)', 'color': COLOR_VERDE_BANDERA, 'border': '1px solid rgba(0, 128, 0, 0.35)', 'padding': '2px 10px', 'borderRadius': '20px', 'fontSize': '11px', 'fontWeight': '700', 'letterSpacing': '0.5px'})
                ]),
                html.P(f"Carrera: {carrera}", style={'margin': '6px 0 2px 0', 'color': 'var(--text-muted)', 'fontSize': '14px'}),
                html.P(f"Curso: {curso} | Grupo: {grupo}{info_grupo_text}", style={'margin': '0', 'color': 'var(--text-muted)', 'fontSize': '14px', 'fontWeight': '500'})
            ])
        ]),

        # KPIs del Alumno
        html.Div(style={'display': 'flex', 'gap': '20px', 'marginBottom': '30px'}, children=[
            html.Div(className='metric-card', style={'flex': '1', 'backgroundColor': 'var(--card-bg)', 'padding': '20px', 'borderRadius': '12px', 'border': '1px solid var(--border-color)'}, children=[
                html.P("Calificación Acumulada", style={'margin': '0', 'color': 'var(--text-muted)', 'fontSize': '14px', 'fontWeight': '500'}),
                html.H3(f"{nota:.1f} pts", style={'margin': '8px 0 0 0', 'fontSize': '26px', 'fontWeight': '700', 'color': color_estatus}),
                html.P("Escala 0.0 - 10.0", style={'margin': '4px 0 0 0', 'fontSize': '12px', 'color': 'var(--text-muted)'})
            ]),
            html.Div(className='metric-card', style={'flex': '1', 'backgroundColor': 'var(--card-bg)', 'padding': '20px', 'borderRadius': '12px', 'border': '1px solid var(--border-color)'}, children=[
                html.P("Promedio del Grupo", style={'margin': '0', 'color': 'var(--text-muted)', 'fontSize': '14px', 'fontWeight': '500'}),
                html.H3(f"{promedio_grupo:.1f} pts", style={'margin': '8px 0 0 0', 'fontSize': '26px', 'fontWeight': '700', 'color': 'var(--text-color)'}),
                html.P("Grupo comparativo", style={'margin': '4px 0 0 0', 'fontSize': '12px', 'color': 'var(--text-muted)'})
            ]),
            html.Div(className='metric-card', style={'flex': '1', 'backgroundColor': 'var(--card-bg)', 'padding': '20px', 'borderRadius': '12px', 'border': '1px solid var(--border-color)'}, children=[
                html.P("Calificación Máxima", style={'margin': '0', 'color': 'var(--text-muted)', 'fontSize': '14px', 'fontWeight': '500'}),
                html.H3(f"{calif_max:.1f} pts", style={'margin': '8px 0 0 0', 'fontSize': '26px', 'fontWeight': '700', 'color': 'var(--text-color)'}),
                html.P("Puntaje tope actual", style={'margin': '4px 0 0 0', 'fontSize': '12px', 'color': 'var(--text-muted)'})
            ]),
            html.Div(className='metric-card', style={'flex': '1', 'backgroundColor': 'var(--card-bg)', 'padding': '20px', 'borderRadius': '12px', 'border': '1px solid var(--border-color)'}, children=[
                html.P("Estatus Académico", style={'margin': '0', 'color': 'var(--text-muted)', 'fontSize': '14px', 'fontWeight': '500'}),
                html.H3(estatus, style={'margin': '8px 0 0 0', 'fontSize': '26px', 'fontWeight': '700', 'color': color_estatus}),
                html.P("Según nota de corte (6.0)", style={'margin': '4px 0 0 0', 'fontSize': '12px', 'color': 'var(--text-muted)'})
            ])
        ]),

        # Bloque de Insights de IA 
        html.Div(className='ai-insights-card', style={'padding': '30px', 'borderRadius': '12px', 'border': '1px solid var(--border-color)', 'marginBottom': '30px'}, children=[
            html.Div(style={'display': 'flex', 'alignItems': 'center', 'gap': '10px', 'marginBottom': '20px'}, children=[
                html.H3("Diagnóstico Pedagógico y Predicción por IA", style={'color': 'var(--accent-color)', 'margin': '0', 'fontSize': '18px', 'fontWeight': '600'})
            ]),
            ia_container
        ]),

        # Bloque de Visualizaciones de Rendimiento Individual DEBAJO del Diagnóstico de IA
        html.Div(style={'display': 'flex', 'gap': '25px', 'marginBottom': '30px'}, children=[
            html.Div(style={'flex': '1', 'backgroundColor': 'var(--card-bg)', 'padding': '20px', 'borderRadius': '12px', 'border': '1px solid var(--border-color)'}, children=[
                dcc.Graph(figure=fig_indiv_progreso, config={'displayModeBar': False})
            ]),
            html.Div(style={'flex': '1', 'backgroundColor': 'var(--card-bg)', 'padding': '20px', 'borderRadius': '12px', 'border': '1px solid var(--border-color)'}, children=[
                dcc.Graph(figure=fig_indiv_comparativa, config={'displayModeBar': False})
            ])
        ])
    ])

@app.callback(
    Output('page-content', 'children'),
    [Input('url', 'pathname'),
     Input('main-container', 'className')]
)
def controlar_rutas(pathname, theme_class):
    if not pathname or pathname == '/': 
        return render_panel_principal()
    elif pathname.startswith('/alumno/'):
        nombre_alumno = urllib.parse.unquote(pathname.split('/alumno/')[1])
        return render_panel_individual(nombre_alumno, theme_class)
    return html.Div("404 - Ruta no válida")

# Callback asíncrono para cargar el diagnóstico de IA
@app.callback(
    Output('diagnostico-ia-target', 'children'),
    Input('url', 'pathname')
)
def cargar_diagnostico_ia(pathname):
    if not pathname or not pathname.startswith('/alumno/'):
        return dash.no_update
        
    nombre_alumno = urllib.parse.unquote(pathname.split('/alumno/')[1])
    
    df = obtener_datos_procesados()
    if df.empty:
        return html.P("Base de datos no cargada.", style={'color': '#FF4D4D'})
        
    registro = df[df['nombre_alumno'] == nombre_alumno]
    if registro.empty:
        return html.P("Estudiante no encontrado.", style={'color': '#FF4D4D'})
        
    datos = registro.iloc[0]
    
    res = obtener_diagnostico_ia(
        nombre_alumno,
        datos['carrera'],
        datos['curso'],
        datos['grupo'],
        datos['calificacion_final']
    )
    
    riesgo = res.get("riesgo", "Desconocido")
    justificacion = res.get("justificacion_riesgo", "")
    prediccion = res.get("prediccion", "")
    recomendaciones = res.get("recomendaciones", [])
    
    badge_class = "badge-risk-bajo"
    if riesgo == "Medio":
        badge_class = "badge-risk-medio"
    elif riesgo == "Alto" or riesgo == "Error":
        badge_class = "badge-risk-alto"
        
    return html.Div(children=[
        html.Div(style={'display': 'flex', 'gap': '30px', 'flexWrap': 'wrap'}, children=[
            # Columna izquierda: Riesgo y Predicción
            html.Div(style={'flex': '1', 'minWidth': '300px'}, children=[
                html.Div(style={'marginBottom': '25px'}, children=[
                    html.Label("Nivel de Riesgo de Deserción:", style={'display': 'block', 'color': 'var(--text-muted)', 'fontSize': '12px', 'textTransform': 'uppercase', 'letterSpacing': '1px', 'marginBottom': '8px'}),
                    html.Span(riesgo, className=badge_class),
                    html.P(justificacion, style={'marginTop': '12px', 'color': 'var(--text-color)', 'fontSize': '14px', 'lineHeight': '1.5'})
                ]),
                html.Div(children=[
                    html.Label("Predicción de Rendimiento:", style={'display': 'block', 'color': 'var(--text-muted)', 'fontSize': '12px', 'textTransform': 'uppercase', 'letterSpacing': '1px', 'marginBottom': '8px'}),
                    html.P(prediccion, style={'color': 'var(--text-color)', 'fontSize': '14px', 'lineHeight': '1.5'})
                ])
            ]),
            
            # Columna derecha: Recomendaciones
            html.Div(style={'flex': '1', 'minWidth': '300px', 'borderLeft': '1px solid var(--border-color)', 'paddingLeft': '30px'}, children=[
                html.Label("Recomendaciones Pedagógicas:", style={'display': 'block', 'color': 'var(--text-muted)', 'fontSize': '12px', 'textTransform': 'uppercase', 'letterSpacing': '1px', 'marginBottom': '12px'}),
                html.Ul([
                    html.Li(r, style={'color': 'var(--text-color)', 'fontSize': '14px', 'marginBottom': '10px', 'lineHeight': '1.4'}) for r in recomendaciones
                ], style={'paddingLeft': '20px', 'margin': '0'})
            ])
        ])
    ])

@app.callback(
    [Output('carrera-dropdown', 'options'), Output('curso-dropdown', 'options'), Output('grupo-dropdown', 'options'),
     Output('trigger-inicial', 'disabled')],
    [Input('trigger-inicial', 'n_intervals'), Input('carrera-dropdown', 'value'), Input('curso-dropdown', 'value')]
)
def manejar_filtros(n, carrera_sel, curso_sel):
    df = obtener_datos_procesados()
    if df is None or df.empty: 
        return [], [], [], False

    op_carreras = [{'label': c, 'value': c} for c in sorted(df['carrera'].unique())]
    
    df_f = df.copy()
    if carrera_sel: 
        df_f = df_f[df_f['carrera'] == carrera_sel]
    op_cursos = [{'label': c, 'value': c} for c in sorted(df_f['curso'].unique())]

    if curso_sel: 
        df_f = df_f[df_f['curso'] == curso_sel]
    op_grupos = [{'label': g, 'value': g} for g in sorted(df_f['grupo'].unique())]

    return op_carreras, op_cursos, op_grupos, True

@app.callback(
    [Output('main-container', 'className'),
     Output('theme-toggle-btn', 'children'),
     Output('theme-store', 'data')],
    [Input('theme-toggle-btn', 'n_clicks')],
    [State('theme-store', 'data')],
    prevent_initial_call=False
)
def toggle_theme(n_clicks, current_theme):
    if n_clicks and n_clicks > 0:
        new_theme = 'light' if current_theme == 'dark' else 'dark'
    else:
        new_theme = current_theme if current_theme in ['dark', 'light'] else 'dark'

    if new_theme == 'light':
        btn_content = [
            get_svg_icon('moon', COLOR_VERDE_BANDERA),
            html.Span("Modo Oscuro", style={'color': COLOR_VERDE_BANDERA, 'fontWeight': '700', 'marginLeft': '6px'})
        ]
        return 'light-theme', btn_content, 'light'
    else:
        btn_content = [
            get_svg_icon('sun', COLOR_VERDE_BANDERA),
            html.Span("Modo Claro", style={'color': COLOR_VERDE_BANDERA, 'fontWeight': '700', 'marginLeft': '6px'})
        ]
        return 'dark-theme', btn_content, 'dark'

@app.callback(
    [Output('grafico-pastel-general', 'figure'), 
     Output('grafico-barras-general', 'figure'), 
     Output('tabla-alumnos-container', 'children'), 
     Output('mensaje-estado-container', 'children'),
     Output('metric-total', 'children'),
     Output('metric-promedio', 'children'),
     Output('metric-aprobados', 'children'),
     Output('metric-aprobados-pct', 'children'),
     Output('metric-riesgo', 'children'),
     Output('metric-riesgo-pct', 'children')],
    [Input('carrera-dropdown', 'value'), 
     Input('curso-dropdown', 'value'), 
     Input('grupo-dropdown', 'value'),
     Input('busqueda-input', 'value'),
     Input('main-container', 'className')],
    [State('carrera-dropdown', 'options'),
     State('url', 'pathname')]
)
def actualizar_dashboard(carrera_sel, curso_sel, grupo_sel, busqueda_sel, theme_class, options_carrera, pathname):
    df = obtener_datos_procesados()
    if df is None or df.empty:
        return {}, {}, html.Div("No hay registros nominales disponibles.", style={'color': 'var(--text-muted)'}), html.Div("Sincronizando base de datos global de Moodle...", style={'color': 'var(--accent-color)', 'fontWeight': 'bold'}), "0", "0.0", "0", "0.0% del total", "0", "0.0% del total"

    df_render = df.copy()
    if carrera_sel: df_render = df_render[df_render['carrera'] == carrera_sel]
    if curso_sel: df_render = df_render[df_render['curso'] == curso_sel]
    if grupo_sel: df_render = df_render[df_render['grupo'] == grupo_sel]
    if busqueda_sel:
        df_render = df_render[df_render['nombre_alumno'].str.contains(busqueda_sel.strip().upper(), na=False)]

    if df_render.empty:
        return {}, {}, html.Div("Por favor seleccione un filtro válido en la barra superior para desplegar la lista de alumnos.", style={'color': '#888'}), "", "0", "0.0", "0", "0.0% del total", "0", "0.0% del total"

    # curso Propedéutico DTIC en el banner
    mensaje_segmentacion = ""
    es_propedeutico = curso_sel and ("PROPEDÉUTICO" in curso_sel or "PROP" in curso_sel)
    if es_propedeutico and grupo_sel and grupo_sel != "SIN GRUPO ASIGNADO":
        parts = grupo_sel.split()
        if len(parts) >= 2:
            siglas = parts[0]
            bloques = parts[1].split('-')
            if len(bloques) == 3:
                anio = bloques[0]
                cuatrimestre = bloques[1]
                recursamiento_val = int(bloques[2])
                carrera_name = "Desarrollo de Software Multiplataforma" if siglas == "DSM" else "Infraestructura de Redes Digitales" if siglas == "IRD" else siglas
                recursamiento_text = "Ordinario" if recursamiento_val == 1 else f"Recursamiento ({recursamiento_val}a vez)"
                
                info_segmentacion = f"Segmentación: {carrera_name} | Ingreso: {anio} | Cuatrimestre: {cuatrimestre} | Estatus: {recursamiento_text}"
                mensaje_segmentacion = html.Div(info_segmentacion, style={
                    'color': 'var(--accent-color)', 
                    'fontWeight': '600', 
                    'backgroundColor': 'rgba(0, 168, 89, 0.1)', 
                    'padding': '12px', 
                    'borderRadius': '8px', 
                    'border': '1px solid rgba(0, 168, 89, 0.25)',
                    'display': 'inline-block',
                    'fontSize': '14px'
                })

    # Calcular KPIs del subgrupo
    total_estudiantes = len(df_render)
    promedio_gral = df_render['calificacion_final'].mean()
    aprobados_df = df_render[df_render['calificacion_final'] >= 6.0]
    riesgo_df = df_render[df_render['calificacion_final'] < 6.0]
    
    total_aprobados = len(aprobados_df)
    total_riesgo = len(riesgo_df)
    
    pct_aprobados = (total_aprobados / total_estudiantes * 100) if total_estudiantes > 0 else 0
    pct_riesgo = (total_riesgo / total_estudiantes * 100) if total_estudiantes > 0 else 0

    df_render['Estatus'] = df_render['calificacion_final'].apply(lambda x: 'Aprobado (>=6.0)' if x >= 6.0 else 'Riesgo (<6.0)')
    
    is_light = (theme_class == 'light-theme')
    plotly_template = 'plotly_white' if is_light else 'plotly_dark'
    text_color = '#000B52' if is_light else '#ffffff'
    grid_color = '#dce3f0' if is_light else '#1e293b'

    # Gráfico de pastel
    fig_pie = px.pie(
        df_render, 
        names='Estatus', 
        title="Distribución de Estatus Académico", 
        color='Estatus',
        color_discrete_map={
            'Riesgo (<6.0)': '#FF4D4D',
            'Aprobado (>=6.0)': '#008000'
        },
        template=plotly_template
    )
    fig_pie.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(t=50, b=20, l=20, r=20),
        font=dict(family="Outfit, sans-serif", color=text_color)
    )
    
    # Gráfico de barras
    fig_bar = px.bar(
        df_render, 
        x='nombre_alumno', 
        y='calificacion_final', 
        title="Calificaciones Finales", 
        color_discrete_sequence=[COLOR_VERDE_BANDERA],
        template=plotly_template
    )
    fig_bar.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(t=50, b=20, l=20, r=20),
        font=dict(family="Outfit, sans-serif", color=text_color),
        xaxis_title="Estudiante",
        yaxis_title="Calificación Final",
        xaxis=dict(showgrid=False, linecolor=grid_color),
        yaxis=dict(gridcolor=grid_color, linecolor=grid_color),
        clickmode='event+select'
    )
    fig_bar.update_traces(marker_color=COLOR_VERDE_BANDERA)

    # Contenedor nominal de alumnos matriculados
    elementos_tabla = []
    for _, fila in df_render.iterrows():
        nombre = fila['nombre_alumno']
        elementos_tabla.append(
            html.Div(className='student-row', style={'padding': '12px 16px', 'borderBottom': '1px solid var(--border-color)', 'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center', 'backgroundColor': 'var(--card-bg)', 'borderRadius': '6px', 'marginBottom': '4px'}, children=[
                dcc.Link(nombre, href=f"/alumno/{urllib.parse.quote(nombre)}", className='student-link'),
                html.Span(f"{fila['calificacion_final']:.1f} pts", style={'color': 'var(--text-color)', 'fontWeight': 'bold', 'fontSize': '14px'})
            ])
        )

    contenedor_lista = html.Div(elementos_tabla, style={'maxHeight': '400px', 'overflowY': 'auto', 'backgroundColor': 'var(--bg-color)', 'borderRadius': '8px', 'padding': '10px', 'border': '1px solid var(--border-color)'})
    
    return (fig_pie, fig_bar, contenedor_lista, mensaje_segmentacion, 
            str(total_estudiantes), f"{promedio_gral:.1f}", 
            str(total_aprobados), f"{pct_aprobados:.1f}% del total", 
            str(total_riesgo), f"{pct_riesgo:.1f}% del total")

# Callback interactivo de redirección al hacer click sobre el gráfico de barras
@app.callback(
    Output('url', 'pathname', allow_duplicate=True),
    Input('grafico-barras-general', 'clickData'),
    State('url', 'pathname'),
    prevent_initial_call=True
)
def redirigir_alumno(clickData, current_path):
    if clickData and current_path == '/':
        try:
            nombre = clickData['points'][0]['x']
            return f"/alumno/{urllib.parse.quote(nombre)}"
        except Exception as e:
            print(f"Error en redirección clickData: {e}")
    return dash.no_update

if __name__ == '__main__':
    puerto = int(os.environ.get('PORT', 5000))
    app.run_server(debug=False, host='0.0.0.0', port=puerto)
