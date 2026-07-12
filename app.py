import os
import requests
import pandas as pd
import dash
from dash import dcc, html
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

# Cargar variables de entorno de forma segura al inicio de la aplicación (Local y Producción)
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(dotenv_path):
    dotenv.load_dotenv(dotenv_path)
else:
    dotenv.load_dotenv()

# Inicialización de la aplicación con la fuente premium Outfit
app = dash.Dash(
    __name__, 
    title="Analítica UTTEC - Institucional", 
    suppress_callback_exceptions=True,
    external_stylesheets=[
        'https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&display=swap'
    ]
)
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
        # 1. Obtener Categorías (Carreras)
        param_cat = {'wstoken': token_moodle, 'wsfunction': 'core_course_get_categories', 'moodlewsrestformat': 'json'}
        res_cat = requests.get(URL_MOODLE, params=param_cat, timeout=15)
        categorias = res_cat.json()
        if 'exception' in categorias or not isinstance(categorias, list):
            print("Error al obtener categorías de Moodle:", categorias)
            return pd.DataFrame()

        # 2. Obtener Cursos
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

            # Mapeo estático de División para el Propedéutico DTIC (ID 50) y derivados
            es_propedeutico_dtic = (course_id == 50 or 
                                    "DTIC-PROP-GRAL" in curso.get('shortname', '') or 
                                    "PROPEDÉUTICO DTIC" in nombre_curso.upper())
            
            if es_propedeutico_dtic:
                nombre_carrera = "DIVISIÓN DE TECNOLOGÍAS DE LA INFORMACIÓN Y COMUNICACIÓN"

            # 3. Consultar calificaciones por curso (Timeout ampliado a 60s para procesar cursos de matrícula numerosa como Propedéutico)
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

                    # Lógica avanzada de segmentación de grupos para Propedéutico DTIC
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
                # Omitir silenciosamente errores individuales para no interrumpir el flujo del pipeline
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

# Estilos CSS de Posicionamiento General
SIDEBAR_STYLE = {
    'position': 'fixed',
    'top': '0',
    'left': '0',
    'bottom': '0',
    'width': '260px',
    'padding': '30px 20px',
    'backgroundColor': '#1e1e1e',
    'borderRight': '1px solid #2d2d2d',
    'display': 'flex',
    'flexDirection': 'column',
    'gap': '20px',
    'zIndex': '1000',
}

CONTENT_STYLE = {
    'marginLeft': '280px',
    'padding': '40px',
    'backgroundColor': '#121212',
    'minHeight': '100vh',
}

def render_sidebar():
    # Menú depurado estéticamente: Se retiraron todos los emojis e íconos y el banner inferior
    menu_items = [
        ("Inicio", "/"),
        ("Curso", "#"),
        ("Participantes", "#"),
        ("Calificaciones", "#"),
        ("Analítica", "/"),
        ("Actividades", "#"),
        ("Recursos", "#"),
        ("Foros", "#"),
        ("Mensajes", "#"),
        ("Configuración", "#")
    ]
    
    links = []
    for name, href in menu_items:
        is_active = (name == "Analítica")
        if is_active:
            links.append(
                dcc.Link(
                    html.Div(className='sidebar-link-active', children=[
                        html.Span(name, style={'fontSize': '15px'})
                    ]),
                    href=href,
                    style={'textDecoration': 'none'}
                )
            )
        else:
            links.append(
                html.Div(className='sidebar-link', children=[
                    html.Span(name, style={'fontSize': '15px'})
                ])
            )

    return html.Div(style=SIDEBAR_STYLE, children=[
        html.Div(style={'padding': '10px 5px'}, children=[
            html.H2("Plataforma", style={'margin': '0', 'fontSize': '18px', 'fontWeight': '800', 'color': '#ffffff', 'letterSpacing': '0.5px', 'lineHeight': '1.1'}),
            html.H2("Virtual UTTEC", style={'margin': '0', 'fontSize': '18px', 'fontWeight': '800', 'color': '#00adb5', 'letterSpacing': '0.5px', 'lineHeight': '1.1'})
        ]),
        html.Hr(style={'borderColor': '#2d2d2d', 'margin': '15px 0'}),
        html.Div(links, style={'display': 'flex', 'flexDirection': 'column'})
    ])

# Layout principal
app.layout = html.Div(style={'backgroundColor': '#121212', 'minHeight': '100vh'}, children=[
    dcc.Location(id='url', refresh=False),
    # Intervalo inicial que corre cada 3 segundos hasta desactivarse cuando cargan los datos
    dcc.Interval(id='trigger-inicial', interval=3000, n_intervals=0, disabled=False), 
    render_sidebar(),
    html.Div(id='page-content', style=CONTENT_STYLE)
])

def render_panel_principal():
    return html.Div(children=[
        # Encabezado limpio (Excluido icono notificaciones y avatar perfil)
        html.Div(style={'borderBottom': '1px solid #2d2d2d', 'paddingBottom': '20px', 'marginBottom': '30px'}, children=[
            html.H1("Analítica del curso", style={'margin': '0', 'color': '#ffffff', 'fontWeight': '700', 'fontSize': '28px'}),
            html.P("Visualiza el desempeño y avance de los estudiantes", style={'margin': '5px 0 0 0', 'color': '#888888', 'fontSize': '14px'})
        ]),
        
        # Selectores
        html.Div(style={
            'display': 'flex',
            'gap': '20px',
            'backgroundColor': '#1e1e1e',
            'padding': '20px',
            'borderRadius': '12px',
            'border': '1px solid #2d2d2d',
            'marginBottom': '30px'
        }, children=[
            html.Div(style={'flex': '1'}, children=[
                html.Label("División / Carrera:", style={'fontWeight': '600', 'display': 'block', 'marginBottom': '8px', 'color': '#888888', 'fontSize': '12px', 'textTransform': 'uppercase', 'letterSpacing': '1px'}),
                dcc.Dropdown(id='carrera-dropdown', placeholder="Sincronizando con Moodle...", style={'color': '#000000'})
            ]),
            html.Div(style={'flex': '1'}, children=[
                html.Label("Curso Moodle:", style={'fontWeight': '600', 'display': 'block', 'marginBottom': '8px', 'color': '#888888', 'fontSize': '12px', 'textTransform': 'uppercase', 'letterSpacing': '1px'}),
                dcc.Dropdown(id='curso-dropdown', placeholder="Seleccione una carrera...", style={'color': '#000000'})
            ]),
            html.Div(style={'flex': '1'}, children=[
                html.Label("Grupo Académico:", style={'fontWeight': '600', 'display': 'block', 'marginBottom': '8px', 'color': '#888888', 'fontSize': '12px', 'textTransform': 'uppercase', 'letterSpacing': '1px'}),
                dcc.Dropdown(id='grupo-dropdown', placeholder="Seleccione un curso...", style={'color': '#000000'})
            ]),
            html.Div(style={'flex': '1'}, children=[
                html.Label("Buscar Estudiante:", style={'fontWeight': '600', 'display': 'block', 'marginBottom': '8px', 'color': '#888888', 'fontSize': '12px', 'textTransform': 'uppercase', 'letterSpacing': '1px'}),
                dcc.Input(id='busqueda-input', type='text', placeholder="Escribe nombre...", className='Select-control', style={'width': '100%', 'height': '38px', 'borderRadius': '4px', 'border': '1px solid #2d2d2d', 'backgroundColor': '#1e1e1e', 'color': '#ffffff', 'paddingLeft': '10px', 'boxSizing': 'border-box'})
            ]),
        ]),

        html.Div(id='mensaje-estado-container', style={'textAlign': 'center', 'marginBottom': '20px'}),

        # Tarjetas de Métricas (KPIs) (Se removieron todos los emojis/iconos de fondo)
        html.Div(style={'display': 'flex', 'gap': '20px', 'marginBottom': '30px'}, children=[
            html.Div(className='metric-card', style={'flex': '1', 'backgroundColor': '#1e1e1e', 'padding': '20px', 'borderRadius': '12px', 'border': '1px solid #2d2d2d', 'position': 'relative', 'overflow': 'hidden'}, children=[
                html.P("Estudiantes Inscritos", style={'margin': '0', 'color': '#888888', 'fontSize': '14px', 'fontWeight': '500'}),
                html.H3(id='metric-total', children="0", style={'margin': '8px 0 0 0', 'fontSize': '28px', 'fontWeight': '700', 'color': '#ffffff'}),
                html.P("100% del subgrupo", style={'margin': '4px 0 0 0', 'fontSize': '12px', 'color': '#00adb5'})
            ]),
            html.Div(className='metric-card', style={'flex': '1', 'backgroundColor': '#1e1e1e', 'padding': '20px', 'borderRadius': '12px', 'border': '1px solid #2d2d2d', 'position': 'relative', 'overflow': 'hidden'}, children=[
                html.P("Promedio General", style={'margin': '0', 'color': '#888888', 'fontSize': '14px', 'fontWeight': '500'}),
                html.H3(id='metric-promedio', children="0.0", style={'margin': '8px 0 0 0', 'fontSize': '28px', 'fontWeight': '700', 'color': '#00adb5'}),
                html.P("Escala UTTEC (0-10)", style={'margin': '4px 0 0 0', 'fontSize': '12px', 'color': '#888888'})
            ]),
            html.Div(className='metric-card', style={'flex': '1', 'backgroundColor': '#1e1e1e', 'padding': '20px', 'borderRadius': '12px', 'border': '1px solid #2d2d2d', 'position': 'relative', 'overflow': 'hidden'}, children=[
                html.P("Aprobados (>= 6.0)", style={'margin': '0', 'color': '#888888', 'fontSize': '14px', 'fontWeight': '500'}),
                html.H3(id='metric-aprobados', children="0", style={'margin': '8px 0 0 0', 'fontSize': '28px', 'fontWeight': '700', 'color': '#28a745'}),
                html.P(id='metric-aprobados-pct', children="0% del total", style={'margin': '4px 0 0 0', 'fontSize': '12px', 'color': '#28a745'})
            ]),
            html.Div(className='metric-card', style={'flex': '1', 'backgroundColor': '#1e1e1e', 'padding': '20px', 'borderRadius': '12px', 'border': '1px solid #2d2d2d', 'position': 'relative', 'overflow': 'hidden'}, children=[
                html.P("En Riesgo (< 6.0)", style={'margin': '0', 'color': '#888888', 'fontSize': '14px', 'fontWeight': '500'}),
                html.H3(id='metric-riesgo', children="0", style={'margin': '8px 0 0 0', 'fontSize': '28px', 'fontWeight': '700', 'color': '#ff414d'}),
                html.P(id='metric-riesgo-pct', children="0% del total", style={'margin': '4px 0 0 0', 'fontSize': '12px', 'color': '#ff414d'})
            ])
        ]),

        # Gráficos
        html.Div(style={'display': 'flex', 'gap': '25px', 'marginBottom': '30px'}, children=[
            html.Div(style={'width': '40%', 'backgroundColor': '#1e1e1e', 'padding': '25px', 'borderRadius': '12px', 'border': '1px solid #2d2d2d'}, children=[
                dcc.Graph(id='grafico-pastel-general', config={'displayModeBar': False})
            ]),
            html.Div(style={'width': '60%', 'backgroundColor': '#1e1e1e', 'padding': '25px', 'borderRadius': '12px', 'border': '1px solid #2d2d2d'}, children=[
                dcc.Graph(id='grafico-barras-general', config={'displayModeBar': False})
            ])
        ]),

        html.Div(style={'backgroundColor': '#1e1e1e', 'padding': '25px', 'borderRadius': '12px', 'border': '1px solid #2d2d2d'}, children=[
            html.H3("Rendimiento Nominal de Estudiantes Matriculados", style={'color': '#00adb5', 'marginTop': '0', 'marginBottom': '20px', 'fontSize': '18px', 'fontWeight': '600'}),
            html.Div(id='tabla-alumnos-container')
        ])
    ])

def render_panel_individual(nombre_alumno):
    df = obtener_datos_procesados()
    if df.empty: 
        return html.Div(style={'padding': '40px', 'textAlign': 'center'}, children=[
            html.H2("Cargando base de datos...", style={'color': '#00adb5'}),
            dcc.Link("Volver a la vista general", href="/", style={'color': '#00adb5', 'fontWeight': 'bold', 'textDecoration': 'none'})
        ])
    
    registro = df[df['nombre_alumno'] == nombre_alumno]
    if registro.empty: 
        return html.Div(style={'padding': '40px', 'textAlign': 'center'}, children=[
            html.H2("Estudiante no encontrado.", style={'color': '#ff414d'}),
            dcc.Link("Volver a la vista general", href="/", style={'color': '#00adb5', 'fontWeight': 'bold', 'textDecoration': 'none'})
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
    color_estatus = "#00adb5" if nota >= 6.0 else "#ff414d"
    
    # Initials for avatar
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
        color="#00adb5",
        children=html.Div(id="diagnostico-ia-target")
    )

    return html.Div(children=[
        dcc.Link("Volver a la vista general", href="/", style={'color': '#00adb5', 'fontWeight': '600', 'textDecoration': 'none', 'display': 'inline-flex', 'alignItems': 'center', 'gap': '8px', 'marginBottom': '25px', 'transition': 'color 0.2s'}),
        
        # Cabecera de identidad del estudiante (excluido perfil e iconos generales)
        html.Div(style={'backgroundColor': '#1e1e1e', 'padding': '30px', 'borderRadius': '12px', 'border': '1px solid #2d2d2d', 'marginBottom': '30px', 'display': 'flex', 'alignItems': 'center', 'gap': '25px'}, children=[
            html.Div(style={'width': '80px', 'height': '80px', 'borderRadius': '50%', 'backgroundColor': '#00adb5', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center', 'color': '#ffffff', 'fontSize': '28px', 'fontWeight': '700', 'boxShadow': '0 4px 14px rgba(0, 173, 181, 0.3)'}, children=iniciales),
            html.Div(style={'flex': '1'}, children=[
                html.Div(style={'display': 'flex', 'alignItems': 'center', 'gap': '15px'}, children=[
                    html.H2(nombre_alumno, style={'color': '#ffffff', 'margin': '0', 'fontSize': '24px', 'fontWeight': '700'}),
                    html.Span("ACTIVO", style={'backgroundColor': 'rgba(0, 173, 181, 0.15)', 'color': '#00adb5', 'border': '1px solid rgba(0, 173, 181, 0.3)', 'padding': '2px 10px', 'borderRadius': '20px', 'fontSize': '11px', 'fontWeight': '700', 'letterSpacing': '0.5px'})
                ]),
                html.P(f"Carrera: {carrera}", style={'margin': '6px 0 2px 0', 'color': '#888888', 'fontSize': '14px'}),
                html.P(f"Curso: {curso} | Grupo: {grupo}{info_grupo_text}", style={'margin': '0', 'color': '#888888', 'fontSize': '14px', 'fontWeight': '500'})
            ])
        ]),

        # KPIs del Alumno
        html.Div(style={'display': 'flex', 'gap': '20px', 'marginBottom': '30px'}, children=[
            html.Div(className='metric-card', style={'flex': '1', 'backgroundColor': '#1e1e1e', 'padding': '20px', 'borderRadius': '12px', 'border': '1px solid #2d2d2d'}, children=[
                html.P("Calificación Acumulada", style={'margin': '0', 'color': '#888888', 'fontSize': '14px', 'fontWeight': '500'}),
                html.H3(f"{nota:.1f} pts", style={'margin': '8px 0 0 0', 'fontSize': '26px', 'fontWeight': '700', 'color': color_estatus}),
                html.P("Escala 0.0 - 10.0", style={'margin': '4px 0 0 0', 'fontSize': '12px', 'color': '#555555'})
            ]),
            html.Div(className='metric-card', style={'flex': '1', 'backgroundColor': '#1e1e1e', 'padding': '20px', 'borderRadius': '12px', 'border': '1px solid #2d2d2d'}, children=[
                html.P("Promedio del Grupo", style={'margin': '0', 'color': '#888888', 'fontSize': '14px', 'fontWeight': '500'}),
                html.H3(f"{promedio_grupo:.1f} pts", style={'margin': '8px 0 0 0', 'fontSize': '26px', 'fontWeight': '700', 'color': '#ffffff'}),
                html.P("Grupo comparativo", style={'margin': '4px 0 0 0', 'fontSize': '12px', 'color': '#888888'})
            ]),
            html.Div(className='metric-card', style={'flex': '1', 'backgroundColor': '#1e1e1e', 'padding': '20px', 'borderRadius': '12px', 'border': '1px solid #2d2d2d'}, children=[
                html.P("Calificación Máxima", style={'margin': '0', 'color': '#888888', 'fontSize': '14px', 'fontWeight': '500'}),
                html.H3(f"{calif_max:.1f} pts", style={'margin': '8px 0 0 0', 'fontSize': '26px', 'fontWeight': '700', 'color': '#ffffff'}),
                html.P("Puntaje tope actual", style={'margin': '4px 0 0 0', 'fontSize': '12px', 'color': '#888888'})
            ]),
            html.Div(className='metric-card', style={'flex': '1', 'backgroundColor': '#1e1e1e', 'padding': '20px', 'borderRadius': '12px', 'border': '1px solid #2d2d2d'}, children=[
                html.P("Estatus Académico", style={'margin': '0', 'color': '#888888', 'fontSize': '14px', 'fontWeight': '500'}),
                html.H3(estatus, style={'margin': '8px 0 0 0', 'fontSize': '26px', 'fontWeight': '700', 'color': color_estatus}),
                html.P("Según nota de corte (6.0)", style={'margin': '4px 0 0 0', 'fontSize': '12px', 'color': '#555555'})
            ])
        ]),

        # Bloque de Insights de IA (Sin emoji de estrella)
        html.Div(className='ai-insights-card', style={'padding': '30px', 'borderRadius': '12px', 'border': '1px solid rgba(0,173,181,0.2)', 'marginBottom': '30px'}, children=[
            html.Div(style={'display': 'flex', 'alignItems': 'center', 'gap': '10px', 'marginBottom': '20px'}, children=[
                html.H3("Diagnóstico Pedagógico y Predicción por IA", style={'color': '#00adb5', 'margin': '0', 'fontSize': '18px', 'fontWeight': '600'})
            ]),
            
            # Contenedor dinámico de IA
            ia_container
        ])
    ])

@app.callback(Output('page-content', 'children'), Input('url', 'pathname'))
def controlar_rutas(pathname):
    if not pathname or pathname == '/': 
        return render_panel_principal()
    elif pathname.startswith('/alumno/'):
        nombre_alumno = urllib.parse.unquote(pathname.split('/alumno/')[1])
        return render_panel_individual(nombre_alumno)
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
        return html.P("Base de datos no cargada.", style={'color': '#ff414d'})
        
    registro = df[df['nombre_alumno'] == nombre_alumno]
    if registro.empty:
        return html.P("Estudiante no encontrado.", style={'color': '#ff414d'})
        
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
                    html.Label("Nivel de Riesgo de Deserción:", style={'display': 'block', 'color': '#888888', 'fontSize': '12px', 'textTransform': 'uppercase', 'letterSpacing': '1px', 'marginBottom': '8px'}),
                    html.Span(riesgo, className=badge_class),
                    html.P(justificacion, style={'marginTop': '12px', 'color': '#e0e0e0', 'fontSize': '14px', 'lineHeight': '1.5'})
                ]),
                html.Div(children=[
                    html.Label("Predicción de Rendimiento:", style={'display': 'block', 'color': '#888888', 'fontSize': '12px', 'textTransform': 'uppercase', 'letterSpacing': '1px', 'marginBottom': '8px'}),
                    html.P(prediccion, style={'color': '#e0e0e0', 'fontSize': '14px', 'lineHeight': '1.5'})
                ])
            ]),
            
            # Columna derecha: Recomendaciones
            html.Div(style={'flex': '1', 'minWidth': '300px', 'borderLeft': '1px solid #2d2d2d', 'paddingLeft': '30px'}, children=[
                html.Label("Recomendaciones Pedagógicas:", style={'display': 'block', 'color': '#888888', 'fontSize': '12px', 'textTransform': 'uppercase', 'letterSpacing': '1px', 'marginBottom': '12px'}),
                html.Ul([
                    html.Li(r, style={'color': '#e0e0e0', 'fontSize': '14px', 'marginBottom': '10px', 'lineHeight': '1.4'}) for r in recomendaciones
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
     Input('busqueda-input', 'value')],
    [State('carrera-dropdown', 'options')]
)
def actualizar_dashboard(carrera_sel, curso_sel, grupo_sel, busqueda_sel, options_carrera):
    df = obtener_datos_procesados()
    if df is None or df.empty:
        return {}, {}, html.Div("No hay registros nominales disponibles.", style={'color': '#888'}), html.Div("Sincronizando base de datos global de Moodle...", style={'color': '#00adb5', 'fontWeight': 'bold'}), "0", "0.0", "0", "0.0% del total", "0", "0.0% del total"

    df_render = df.copy()
    if carrera_sel: df_render = df_render[df_render['carrera'] == carrera_sel]
    if curso_sel: df_render = df_render[df_render['curso'] == curso_sel]
    if grupo_sel: df_render = df_render[df_render['grupo'] == grupo_sel]
    if busqueda_sel:
        df_render = df_render[df_render['nombre_alumno'].str.contains(busqueda_sel.strip().upper(), na=False)]

    if df_render.empty:
        return {}, {}, html.Div("Por favor seleccione un filtro válido en la barra superior para desplegar la lista de alumnos.", style={'color': '#888'}), "", "0", "0.0", "0", "0.0% del total", "0", "0.0% del total"

    # Procesar segmentación avanzada para el curso Propedéutico DTIC en el banner de estado
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
                    'color': '#00adb5', 
                    'fontWeight': '600', 
                    'backgroundColor': 'rgba(0,173,181,0.08)', 
                    'padding': '12px', 
                    'borderRadius': '8px', 
                    'border': '1px solid rgba(0,173,181,0.18)',
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
    
    # Gráfico de pastel
    fig_pie = px.pie(df_render, names='Estatus', title="Distribución de Estatus Académico", color='Estatus',
                     color_discrete_map={'Aprobado (>=6.0)': '#00adb5', 'Riesgo (<6.0)': '#ff414d'}, template='plotly_dark')
    fig_pie.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(t=50, b=20, l=20, r=20),
        font=dict(family="Outfit, sans-serif")
    )
    
    # Gráfico de barras
    fig_bar = px.bar(df_render, x='nombre_alumno', y='calificacion_final', title="Calificaciones Finales", template='plotly_dark')
    fig_bar.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(t=50, b=20, l=20, r=20),
        font=dict(family="Outfit, sans-serif"),
        xaxis_title="Estudiante",
        yaxis_title="Calificación Final",
        clickmode='event+select'
    )
    fig_bar.update_traces(marker_color='#00adb5')

    # Contenedor nominal de alumnos matriculados
    elementos_tabla = []
    for _, fila in df_render.iterrows():
        nombre = fila['nombre_alumno']
        elementos_tabla.append(
            html.Div(className='student-row', style={'padding': '12px 16px', 'borderBottom': '1px solid #2d2d2d', 'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center', 'backgroundColor': '#151515', 'borderRadius': '6px', 'marginBottom': '4px'}, children=[
                dcc.Link(nombre, href=f"/alumno/{urllib.parse.quote(nombre)}", className='student-link'),
                html.Span(f"{fila['calificacion_final']:.1f} pts", style={'color': '#ffffff', 'fontWeight': 'bold', 'fontSize': '14px'})
            ])
        )

    contenedor_lista = html.Div(elementos_tabla, style={'maxHeight': '400px', 'overflowY': 'auto', 'backgroundColor': '#121212', 'borderRadius': '8px', 'padding': '10px', 'border': '1px solid #2d2d2d'})
    
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
