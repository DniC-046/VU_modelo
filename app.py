iimport os
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

# Cargar variables de entorno de forma segura al inicio de la aplicación
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

def extraer_grupo_profundo(tabla_usuario, nombre_curso):
    """
    Analiza el árbol de datos de Moodle para extraer el grupo (ej. DSM 2024-3-1).
    Busca primero en las tablas internas del estudiante y luego en el nombre del curso.
    """
    # 1. Búsqueda profunda en los diccionarios anidados de tabledata (Lógica del script de depuración)
    for item in tabla_usuario.get('tabledata', []):
        if not isinstance(item, dict): 
            continue
        for k, v in item.items():
            if isinstance(v, dict):
                for nk, nv in v.items():
                    if isinstance(nv, str) and any(p in nv for p in ['DSM', 'IRD', '202']):
                        return nv.strip().upper()
            elif isinstance(v, str) and any(p in v for p in ['DSM', 'IRD', '202']):
                return v.strip().upper()
                
    # 2. Mecanismo de respaldo basado en el nombre del curso si lo anterior falla
    if "-" in nombre_curso:
        return nombre_curso.split("-")[-1].strip().upper()
    elif "GRUPO" in nombre_curso.upper():
        return nombre_curso.upper().split("GRUPO")[-1].strip()
        
    return "DSM 2024-3-1"  # Valor estático predeterminado para el Propedéutico DTIC

def obtener_datos_moodle_live():
    """Consulta la API de Moodle de forma sincrónica y procesa las calificaciones."""
    token_moodle = os.environ.get("MOODLE_TOKEN")
    if not token_moodle:
        print("Error: Falta la variable de entorno MOODLE_TOKEN.")
        return pd.DataFrame()

    lista_completa_alumnos = []
    try:
        # 1. Obtener Cursos
        param_cur = {'wstoken': token_moodle, 'wsfunction': 'core_course_get_courses', 'moodlewsrestformat': 'json'}
        res_cur = requests.get(URL_MOODLE, params=param_cur, timeout=15)
        cursos = res_cur.json()
        if 'exception' in cursos or not isinstance(cursos, list):
            print("Error al obtener cursos de Moodle:", cursos)
            return pd.DataFrame()

        print(f"Sincronizador: Descargados {len(cursos)} cursos. Procesando calificaciones...")

        for curso in cursos:
            course_id = curso.get('id')
            nombre_curso = curso.get('fullname', '').strip()

            # Filtrar cursos inválidos o vacíos
            if course_id == 1 or not nombre_curso: 
                continue

            # Fijación estática de la división académica a DTIC
            nombre_carrera = "DTIC"

            # 2. Consultar calificaciones por curso usando la función masiva
            param_calif = {
                'wstoken': token_moodle,
                'wsfunction': 'gradereport_user_get_grades_table',
                'moodlewsrestformat': 'json',
                'courseid': course_id
            }
            try:
                res_calif = requests.get(URL_MOODLE, params=param_calif, timeout=30)
                data_curso = res_calif.json()

                if not isinstance(data_curso, dict) or 'tables' not in data_curso: 
                    continue

                for tabla_usuario in data_curso.get('tables', []):
                    user_fullname = tabla_usuario.get('userfullname', '').strip().upper()
                    if not user_fullname: 
                        continue

                    nota_final = 0.0
                    for item in tabla_usuario.get('tabledata', []):
                        if not isinstance(item, dict): 
                            continue
                        item_name_dict = item.get('itemname', {})
                        item_text = item_name_dict.get('text', '').lower() if isinstance(item_name_dict, dict) else ""

                        if 'total' in item_text or 'curso' in item_text:
                            try:
                                grade_data = item.get('grade', {})
                                nota_final = float(grade_data.get('text', '0.0'))
                            except:
                                nota_final = 0.0

                    grupo_detectado = extraer_grupo_profundo(tabla_usuario, nombre_curso)

                    lista_completa_alumnos.append({
                        'carrera': nombre_carrera,
                        'curso': nombre_curso.upper(),
                        'grupo': grupo_detectado,
                        'nombre_alumno': user_fullname,
                        'calificacion_final': nota_final
                    })
            except Exception as e:
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
                print(f"Hilo Sync: Sincronización exitosa. Guardados {len(df)} registros.")
                time.sleep(600)
            else:
                print("Hilo Sync: Moodle retornó DataFrame vacío. Reintentando en 60 segundos...")
                time.sleep(60)
        except Exception as e:
            print(f"Hilo Sync: Error crítico en sincronizador: {e}. Reintentando en 60 segundos...")
            time.sleep(60)

threading.Thread(target=sync_moodle_background, daemon=True).start()

def obtener_datos_procesados():
    """Lee del archivo JSON local y maneja caché de memoria basado en mtime."""
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
                print(f"Caché: Recargados {len(_cached_df)} registros desde almacenamiento local.")
            else:
                _cached_df = pd.DataFrame()
        return _cached_df
    except Exception as e:
        print(f"Error al leer JSON local de caché: {e}")
        return _cached_df

@cache.memoize(timeout=3600)
def obtener_diagnostico_ia(nombre_alumno, carrera, curso, grupo, calificacion_final):
    api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("CHATGPT_CONTRASEÑA")
    if not api_key:
        return {
            "riesgo": "Desconocido",
            "justificacion_riesgo": "No se configuró la API Key de OpenAI.",
            "prediccion": "Predicción de rendimiento no disponible por falta de credenciales.",
            "recomendaciones": ["Configure la variable de entorno OPENAI_API_KEY."]
        }

    try:
        client = OpenAI(api_key=api_key)
        prompt = f"""
        Actúa como un Asesor Pedagógico de la Universidad Tecnológica de Tecámac (UTTEC).
        Genera un diagnóstico académico en formato JSON estricto para:
        - Nombre: {nombre_alumno} | Carrera: {carrera} | Curso: {curso} | Grupo: {grupo}
        - Calificación Actual: {calificacion_final:.1f} / 10.0

        Reglas UTTEC: Mínimo aprobatorio 6.0. Menos de 6.0 es Alto Riesgo. 6.0 a 7.5 Riesgo Medio. 7.6 a 10.0 Bajo Riesgo.
        Retorna exclusivamente este formato JSON:
        {{
            "riesgo": "Bajo" | "Medio" | "Alto",
            "justificacion_riesgo": "Explicación breve.",
            "prediccion": "Frase corta de predicción.",
            "recomendaciones": ["Rec 1", "Rec 2", "Rec 3"]
        }}
        """
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Responde únicamente en formato JSON válido."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            response_format={"type": "json_object"}
        )

        data = json.loads(response.choices[0].message.content.strip())
        return {
            "riesgo": data.get("riesgo", "Medio"),
            "justificacion_riesgo": data.get("justificacion_riesgo", "Sin justificación."),
            "prediccion": data.get("prediccion", "Sin predicción."),
            "recomendaciones": data.get("recomendaciones", ["Seguimiento académico continuo."])
        }
    except Exception as e:
        return {
            "riesgo": "Error",
            "justificacion_riesgo": f"Error de conexión con IA: {str(e)}",
            "prediccion": "No disponible.",
            "recomendaciones": ["Realizar evaluación manual del estudiante."]
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
        style_link = {'padding': '12px', 'borderRadius': '8px', 'marginBottom': '5px', 'display': 'block', 'color': '#ffffff'}
        if is_active:
            style_link.update({'backgroundColor': '#00adb5', 'fontWeight': '600'})
        else:
            style_link.update({'backgroundColor': 'transparent', 'opacity': '0.7'})
            
        links.append(
            dcc.Link(html.Div(name, style={'fontSize': '15px'}), href=href, style={'textDecoration': 'none'})
        )

    return html.Div(style=SIDEBAR_STYLE, children=[
        html.Div(style={'display': 'flex', 'alignItems': 'center', 'gap': '12px', 'padding': '10px 5px'}, children=[
            html.Div(children=[
                html.H2("Plataforma", style={'margin': '0', 'fontSize': '18px', 'fontWeight': '800', 'color': '#ffffff', 'lineHeight': '1.1'}),
                html.H2("Virtual UTTEC", style={'margin': '0', 'fontSize': '18px', 'fontWeight': '800', 'color': '#00adb5', 'lineHeight': '1.1'})
            ])
        ]),
        html.Hr(style={'borderColor': '#2d2d2d', 'margin': '15px 0'}),
        html.Div(links, style={'display': 'flex', 'flexDirection': 'column'}),
        html.Div(style={'marginTop': 'auto', 'padding': '16px', 'backgroundColor': '#151515', 'borderRadius': '12px', 'border': '1px solid #2d2d2d', 'textAlign': 'center'}, children=[
            html.P("UTTEC Analítica", style={'margin': '0', 'fontSize': '11px', 'color': '#555555', 'fontWeight': '700', 'textTransform': 'uppercase'}),
            html.P("Mapeo Asistido por IA", style={'margin': '4px 0 0 0', 'fontSize': '12px', 'color': '#00adb5', 'fontWeight': '600'})
        ])
    ])

app.layout = html.Div(style={'backgroundColor': '#121212', 'minHeight': '100vh'}, children=[
    dcc.Location(id='url', refresh=False),
    dcc.Interval(id='trigger-inicial', interval=3000, n_intervals=0, disabled=False),
    render_sidebar(),
    html.Div(id='page-content', style=CONTENT_STYLE)
])

def render_panel_principal():
    return html.Div(children=[
        html.Div(style={'borderBottom': '1px solid #2d2d2d', 'paddingBottom': '20px', 'marginBottom': '30px'}, children=[
            html.H1("Analítica del curso", style={'margin': '0', 'color': '#ffffff', 'fontWeight': '700', 'fontSize': '28px'}),
            html.P("Visualiza el desempeño y avance de los estudiantes", style={'margin': '5px 0 0 0', 'color': '#888888', 'fontSize': '14px'})
        ]),
        html.Div(style={'display': 'flex', 'gap': '20px', 'backgroundColor': '#1e1e1e', 'padding': '20px', 'borderRadius': '12px', 'border': '1px solid #2d2d2d', 'marginBottom': '30px'}, children=[
            html.Div(style={'flex': '1'}, children=[
                html.Label("División / Carrera:", style={'fontWeight': '600', 'display': 'block', 'marginBottom': '8px', 'color': '#888888', 'fontSize': '12px'}),
                dcc.Dropdown(id='carrera-dropdown', placeholder="Sincronizando con Moodle...", style={'color': '#000000'})
            ]),
            html.Div(style={'flex': '1'}, children=[
                html.Label("Curso Moodle:", style={'fontWeight': '600', 'display': 'block', 'marginBottom': '8px', 'color': '#888888', 'fontSize': '12px'}),
                dcc.Dropdown(id='curso-dropdown', placeholder="Seleccione una carrera...", style={'color': '#000000'})
            ]),
            html.Div(style={'flex': '1'}, children=[
                html.Label("Grupo Académico:", style={'fontWeight': '600', 'display': 'block', 'marginBottom': '8px', 'color': '#888888', 'fontSize': '12px'}),
                dcc.Dropdown(id='grupo-dropdown', placeholder="Seleccione un curso...", style={'color': '#000000'})
            ]),
        ]),
        html.Div(id='mensaje-estado-container', style={'textAlign': 'center', 'marginBottom': '20px'}),
        html.Div(style={'display': 'flex', 'gap': '20px', 'marginBottom': '30px'}, children=[
            html.Div(style={'flex': '1', 'backgroundColor': '#1e1e1e', 'padding': '20px', 'borderRadius': '12px', 'border': '1px solid #2d2d2d'}, children=[
                html.P("Estudiantes Inscritos", style={'margin': '0', 'color': '#888888', 'fontSize': '14px'}),
                html.H3(id='metric-total', children="0", style={'margin': '8px 0 0 0', 'fontSize': '28px', 'color': '#ffffff'})
            ]),
            html.Div(style={'flex': '1', 'backgroundColor': '#1e1e1e', 'padding': '20px', 'borderRadius': '12px', 'border': '1px solid #2d2d2d'}, children=[
                html.P("Promedio General", style={'margin': '0', 'color': '#888888', 'fontSize': '14px'}),
                html.H3(id='metric-promedio', children="0.0", style={'margin': '8px 0 0 0', 'fontSize': '28px', 'color': '#00adb5'})
            ]),
            html.Div(style={'flex': '1', 'backgroundColor': '#1e1e1e', 'padding': '20px', 'borderRadius': '12px', 'border': '1px solid #2d2d2d'}, children=[
                html.P("Aprobados (>=6.0)", style={'margin': '0', 'color': '#888888', 'fontSize': '14px'}),
                html.H3(id='metric-aprobados', children="0", style={'margin': '8px 0 0 0', 'fontSize': '28px', 'color': '#28a745'}),
                html.P(id='metric-aprobados-pct', children="0% del total", style={'margin': '4px 0 0 0', 'fontSize': '12px', 'color': '#28a745'})
            ]),
            html.Div(style={'flex': '1', 'backgroundColor': '#1e1e1e', 'padding': '20px', 'borderRadius': '12px', 'border': '1px solid #2d2d2d'}, children=[
                html.P("En Riesgo (<6.0)", style={'margin': '0', 'color': '#888888', 'fontSize': '14px'}),
                html.H3(id='metric-riesgo', children="0", style={'margin': '8px 0 0 0', 'fontSize': '28px', 'color': '#ff414d'}),
                html.P(id='metric-riesgo-pct', children="0% del total", style={'margin': '4px 0 0 0', 'fontSize': '12px', 'color': '#ff414d'})
            ])
        ]),
        html.Div(style={'display': 'flex', 'gap': '25px', 'marginBottom': '30px'}, children=[
            html.Div(style={'width': '40%', 'backgroundColor': '#1e1e1e', 'padding': '25px', 'borderRadius': '12px', 'border': '1px solid #2d2d2d'}, children=[
                dcc.Graph(id='grafico-pastel-general', config={'displayModeBar': False})
            ]),
            html.Div(style={'width': '60%', 'backgroundColor': '#1e1e1e', 'padding': '25px', 'borderRadius': '12px', 'border': '1px solid #2d2d2d'}, children=[
                dcc.Graph(id='grafico-barras-general', config={'displayModeBar': False})
            ])
        ]),
        html.Div(style={'backgroundColor': '#1e1e1e', 'padding': '25px', 'borderRadius': '12px', 'border': '1px solid #2d2d2d'}, children=[
            html.H3("Rendimiento Nominal de Estudiantes Matriculados", style={'color': '#00adb5', 'marginTop': '0', 'marginBottom': '20px', 'fontSize': '18px'}),
            html.Div(id='tabla-alumnos-container')
        ])
    ])

def render_panel_individual(nombre_alumno):
    df = obtener_datos_procesados()
    if df.empty:
        return html.Div(style={'padding': '40px', 'textAlign': 'center'}, children=[
            html.H2("Cargando base de datos...", style={'color': '#00adb5'}),
            dcc.Link("- Volver a la vista general", href="/")
        ])
    
    registro = df[df['nombre_alumno'] == nombre_alumno]
    if registro.empty:
        return html.Div(style={'padding': '40px', 'textAlign': 'center'}, children=[
            html.H2("Estudiante no encontrado.", style={'color': '#ff414d'}),
            dcc.Link(" - Volver a la vista general", href="/")
        ])
        
    datos = registro.iloc[0]
    nota = datos['calificacion_final']
    carrera = datos['carrera']
    curso = datos['curso']
    grupo = datos['grupo']
    
    df_grupo = df[(df['curso'] == curso) & (df['grupo'] == grupo)]
    promedio_grupo = df_grupo['calificacion_final'].mean() if not df_grupo.empty else 0.0
    estatus = "Aprobado" if nota >= 6.0 else "Riesgo"
    color_estatus = "#00adb5" if nota >= 6.0 else "#ff414d"
    
    partes = nombre_alumno.split()
    iniciales = "".join([p[0] for p in partes if p][:2])
    
    ia_container = dcc.Loading(
        id="loading-ia",
        type="circle",
        color="#00adb5",
        children=html.Div(id="diagnostico-ia-target")
    )
    
    return html.Div(children=[
        dcc.Link(" Volver a la vista general", href="/", style={'color': '#00adb5', 'fontWeight': '600', 'textDecoration': 'none', 'marginBottom': '25px', 'display': 'inline-block'}),
        html.Div(style={'backgroundColor': '#1e1e1e', 'padding': '30px', 'borderRadius': '12px', 'border': '1px solid #2d2d2d', 'marginBottom': '30px', 'display': 'flex', 'alignItems': 'center', 'gap': '25px'}, children=[
            html.Div(style={'width': '80px', 'height': '80px', 'borderRadius': '50%', 'backgroundColor': '#00adb5', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center', 'color': '#ffffff', 'fontSize': '28px', 'fontWeight': '700'}, children=iniciales),
            html.Div(style={'flex': '1'}, children=[
                html.Div(style={'display': 'flex', 'alignItems': 'center', 'gap': '15px'}, children=[
                    html.H2(nombre_alumno, style={'color': '#ffffff', 'margin': '0', 'fontSize': '24px'}),
                    html.Span("ACTIVO", style={'backgroundColor': 'rgba(0, 173, 181, 0.15)', 'color': '#00adb5', 'padding': '2px 10px', 'borderRadius': '20px', 'fontSize': '11px'})
                ]),
                html.P(f"Carrera: {carrera}", style={'margin': '6px 0 2px 0', 'color': '#888888', 'fontSize': '14px'}),
                html.P(f"Curso: {curso} | Grupo: {grupo}", style={'margin': '0', 'color': '#888888', 'fontSize': '14px'})
            ])
        ]),
        html.Div(style={'display': 'flex', 'gap': '20px', 'marginBottom': '30px'}, children=[
            html.Div(style={'flex': '1', 'backgroundColor': '#1e1e1e', 'padding': '20px', 'borderRadius': '12px', 'border': '1px solid #2d2d2d'}, children=[
                html.P("Calificación Acumulada", style={'margin': '0', 'color': '#888888', 'fontSize': '14px'}),
                html.H3(f" {nota:.1f} pts", style={'margin': '8px 0 0 0', 'fontSize': '26px', 'color': color_estatus})
            ]),
            html.Div(style={'flex': '1', 'backgroundColor': '#1e1e1e', 'padding': '20px', 'borderRadius': '12px', 'border': '1px solid #2d2d2d'}, children=[
                html.P("Promedio del Grupo", style={'margin': '0', 'color': '#888888', 'fontSize': '14px'}),
                html.H3(f"{promedio_grupo:.1f} pts", style={'margin': '8px 0 0 0', 'fontSize': '26px', 'color': '#ffffff'})
            ]),
            html.Div(style={'flex': '1', 'backgroundColor': '#1e1e1e', 'padding': '20px', 'borderRadius': '12px', 'border': '1px solid #2d2d2d'}, children=[
                html.P("Estatus Académico", style={'margin': '0', 'color': '#888888', 'fontSize': '14px'}),
                html.H3(estatus, style={'margin': '8px 0 0 0', 'fontSize': '26px', 'color': color_estatus})
            ])
        ]),
        html.Div(style={'padding': '30px', 'borderRadius': '12px', 'border': '1px solid rgba(0,173,181,0.2)', 'marginBottom': '30px', 'backgroundColor': '#1e1e1e'}, children=[
            html.H3("Diagnóstico Pedagógico y Predicción por IA", style={'color': '#00adb5', 'margin': '0 0 20px 0', 'fontSize': '18px'}),
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
    return html.Div("404 - Ruta no válida", style={'color': '#ffffff'})

@app.callback(Output('diagnostico-ia-target', 'children'), Input('url', 'pathname'))
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
        nombre_alumno, datos['carrera'], datos['curso'], datos['grupo'], datos['calificacion_final']
    )
    
    riesgo = res.get("riesgo", "Desconocido")
    justificacion = res.get("justificacion_riesgo", "")
    prediccion = res.get("prediccion", "")
    recomendaciones = res.get("recomendaciones", [])
    
    color_badge = "#28a745" if riesgo == "Bajo" else "#ffc107" if riesgo == "Medio" else "#ff414d"
    
    return html.Div(children=[
        html.Div(style={'display': 'flex', 'gap': '30px', 'flexWrap': 'wrap'}, children=[
            html.Div(style={'flex': '1', 'minWidth': '300px'}, children=[
                html.Div(style={'marginBottom': '25px'}, children=[
                    html.Label("Nivel de Riesgo de Deserción:", style={'display': 'block', 'color': '#888888', 'fontSize': '12px', 'marginBottom': '8px'}),
                    html.Span(riesgo, style={'backgroundColor': color_badge, 'color': '#ffffff', 'padding': '4px 12px', 'borderRadius': '4px', 'fontWeight': 'bold'}),
                    html.P(justificacion, style={'marginTop': '12px', 'color': '#e0e0e0', 'fontSize': '14px'})
                ]),
                html.Div(children=[
                    html.Label("Predicción de Rendimiento:", style={'display': 'block', 'color': '#888888', 'fontSize': '12px', 'marginBottom': '8px'}),
                    html.P(prediccion, style={'color': '#e0e0e0', 'fontSize': '14px'})
                ]),
            ]),
            html.Div(style={'flex': '1', 'minWidth': '300px', 'borderLeft': '1px solid #2d2d2d', 'paddingLeft': '30px'}, children=[
                html.Label("Recomendaciones Pedagógicas:", style={'display': 'block', 'color': '#888888', 'fontSize': '12px', 'marginBottom': '12px'}),
                html.Ul([html.Li(r, style={'color': '#e0e0e0', 'fontSize': '14px', 'marginBottom': '10px'}) for r in recomendaciones], style={'paddingLeft': '20px', 'margin': '0'})
            ])
        ])
    ])

@app.callback(
    [Output('carrera-dropdown', 'options'), Output('curso-dropdown', 'options'), Output('grupo-dropdown', 'options'), Output('trigger-inicial', 'disabled')],
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
    [Input('carrera-dropdown', 'value'), Input('curso-dropdown', 'value'), Input('grupo-dropdown', 'value'), Input('carrera-dropdown', 'options')]
)
def actualizar_dashboard(carrera_sel, curso_sel, grupo_sel, options_carrera):
    df = obtener_datos_procesados()
    if df is None or df.empty:
        return {}, {}, html.Div("No hay registros nominales disponibles.", style={'color': '#888'}), html.Div("Sincronizando base de datos global de Moodle...", style={'color': '#00adb5', 'fontWeight': 'bold'}), "0", "0.0", "0", "0.0%", "0", "0.0%"
        
    df_render = df.copy()
    if carrera_sel: df_render = df_render[df_render['carrera'] == carrera_sel]
    if curso_sel: df_render = df_render[df_render['curso'] == curso_sel]
    if grupo_sel: df_render = df_render[df_render['grupo'] == grupo_sel]
    
    if df_render.empty:
        return {}, {}, html.Div("Seleccione un filtro válido para desplegar los alumnos.", style={'color': '#888'}), "", "0", "0.0", "0", "0.0%", "0", "0.0%"
        
    total_estudiantes = len(df_render)
    promedio_gral = df_render['calificacion_final'].mean()
    total_aprobados = len(df_render[df_render['calificacion_final'] >= 6.0])
    total_riesgo = len(df_render[df_render['calificacion_final'] < 6.0])
    pct_aprobados = (total_aprobados / total_estudiantes * 100) if total_estudiantes > 0 else 0
    pct_riesgo = (total_riesgo / total_estudiantes * 100) if total_estudiantes > 0 else 0
    
    df_render['Estatus'] = df_render['calificacion_final'].apply(lambda x: 'Aprobado (>=6.0)' if x >= 6.0 else 'Riesgo (<6.0)')
    
    fig_pie = px.pie(df_render, names='Estatus', title="Distribución de Estatus Académico", color='Estatus', color_discrete_map={'Aprobado (>=6.0)': '#00adb5', 'Riesgo (<6.0)': '#ff414d'}, template='plotly_dark')
    fig_pie.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(family="Outfit, sans-serif"))
    
    fig_bar = px.bar(df_render, x='nombre_alumno', y='calificacion_final', title="Calificaciones Finales", template='plotly_dark')
    fig_bar.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(family="Outfit, sans-serif"), xaxis_title="Estudiante", yaxis_title="Calificación Final", clickmode='event+select')
    fig_bar.update_traces(marker_color='#00adb5')
    
    elementos_tabla = []
    for _, fila in df_render.iterrows():
        nombre = fila['nombre_alumno']
        elementos_tabla.append(
            html.Div(style={'padding': '12px 16px', 'borderBottom': '1px solid #2d2d2d', 'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center', 'backgroundColor': '#151515', 'borderRadius': '6px', 'marginBottom': '4px'}, children=[
                dcc.Link(nombre, href=f"/alumno/{urllib.parse.quote(nombre)}", style={'color': '#00adb5', 'textDecoration': 'none'}),
                html.Span(f"{fila['calificacion_final']:.1f} pts", style={'color': '#ffffff', 'fontWeight': 'bold', 'fontSize': '14px'})
            ])
        )
    contenedor_lista = html.Div(elementos_tabla, style={'maxHeight': '400px', 'overflowY': 'auto', 'backgroundColor': '#121212', 'borderRadius': '8px', 'padding': '10px', 'border': '1px solid #2d2d2d'})
    
    return fig_pie, fig_bar, contenedor_lista, "", str(total_estudiantes), f"{promedio_gral:.1f}", str(total_aprobados), f"{pct_aprobados:.1f}%", str(total_riesgo), f"{pct_riesgo:.1f}%"

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
