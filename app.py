import os
import requests
import pandas as pd
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.express as px
from flask_caching import Cache
import urllib.parse

app = dash.Dash(__name__, title="Analítica UTTEC - Institucional", suppress_callback_exceptions=True)
server = app.server
application = server  

cache = Cache(app.server, config={
    'CACHE_TYPE': 'SimpleCache',
    'CACHE_DEFAULT_TIMEOUT': 300
})

URL_MOODLE = "https://virtual2.uttecamac.edu.mx/webservice/rest/server.php"

@cache.memoize(timeout=300)
def obtener_datos_procesados():
    token_moodle = os.environ.get("MOODLE_TOKEN")
    if not token_moodle:
        print("Falta la variable de entorno MOODLE_TOKEN.")
        return pd.DataFrame()

    lista_completa_alumnos = []
    try:
        param_cat = {'wstoken': token_moodle, 'wsfunction': 'core_course_get_categories', 'moodlewsrestformat': 'json'}
        res_cat = requests.get(URL_MOODLE, params=param_cat, timeout=15)
        categorias = res_cat.json()
        if 'exception' in categorias or not isinstance(categorias, list):
            return pd.DataFrame()

        param_cur = {'wstoken': token_moodle, 'wsfunction': 'core_course_get_courses', 'moodlewsrestformat': 'json'}
        res_cur = requests.get(URL_MOODLE, params=param_cur, timeout=15)
        cursos = res_cur.json()
        if 'exception' in cursos or not isinstance(cursos, list):
            return pd.DataFrame()

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

            # Consultar calificaciones por curso
            param_calif = {
                'wstoken': token_moodle,
                'wsfunction': 'gradereport_user_get_grades_table',
                'moodlewsrestformat': 'json',
                'courseid': course_id
            }
            try:
                res_calif = requests.get(URL_MOODLE, params=param_calif, timeout=8)
                data_curso = res_calif.json()
                
                if not isinstance(data_curso, dict) or 'tables' not in data_curso: 
                    continue
                
                for tabla_usuario in data_curso.get('tables', []):
                    user_fullname = tabla_usuario.get('userfullname', '').strip().upper()
                    if not user_fullname: 
                        continue
                        
                    nota_final = 0.0
                    for item in tabla_usuario.get('tabledata', []):
                        if not isinstance(item, dict): continue
                        item_name_dict = item.get('itemname', {})
                        item_text = item_name_dict.get('text', '').lower() if isinstance(item_name_dict, dict) else ""
                        
                        if 'total' in item_text or 'curso' in item_text:
                            try:
                                grade_data = item.get('grade', {})
                                nota_final = float(grade_data.get('text', '0.0'))
                            except:
                                nota_final = 0.0

                    grupo_detectado = "SIN GRUPO ASIGNADO"
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
            except:
                continue 

        return pd.DataFrame(lista_completa_alumnos)
    except Exception as e:
        print(f"Error general: {e}")
        return pd.DataFrame()

app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    dcc.Interval(id='trigger-inicial', interval=1000, max_intervals=1), # Retardo controlado de 1s
    html.Div(id='page-content')
])

def render_panel_principal():
    return html.Div(style={'backgroundColor': '#121212', 'color': '#ffffff', 'fontFamily': 'Segoe UI, Arial', 'padding': '30px'}, children=[
        html.Div(style={'borderBottom': '2px solid #00adb5', 'paddingBottom': '15px', 'marginBottom': '30px'}, children=[
            html.H1("Analítica UTTEC - Control Institucional", style={'margin': '0', 'color': '#00adb5', 'fontWeight': '600'}),
            html.P("Mapeo automatizado global en vivo desde la plataforma Virtual UTTEC", style={'margin': '5px 0 0 0', 'color': '#888888'})
        ]),
        
        # Selectores
        html.Div(style={'display': 'flex', 'gap': '20px', 'marginBottom': '30px'}, children=[
            html.Div(style={'flex': '1'}, children=[
                html.Label("División / Carrera:", style={'fontWeight': '500', 'display': 'block', 'marginBottom': '8px'}),
                dcc.Dropdown(id='carrera-dropdown', placeholder="Sincronizando con Moodle...", style={'color': '#000000'})
            ]),
            html.Div(style={'flex': '1'}, children=[
                html.Label("Curso Moodle:", style={'fontWeight': '500', 'display': 'block', 'marginBottom': '8px'}),
                dcc.Dropdown(id='curso-dropdown', placeholder="Seleccione una carrera primero...", style={'color': '#000000'})
            ]),
            html.Div(style={'flex': '1'}, children=[
                html.Label("Grupo Académico:", style={'fontWeight': '500', 'display': 'block', 'marginBottom': '8px'}),
                dcc.Dropdown(id='grupo-dropdown', placeholder="Seleccione un curso primero...", style={'color': '#000000'})
            ]),
        ]),

        html.Div(id='mensaje-estado-container', style={'textAlign': 'center', 'marginBottom': '20px'}),

        # Gráficos
        html.Div(style={'display': 'flex', 'gap': '25px', 'marginBottom': '30px'}, children=[
            html.Div(style={'width': '40%', 'backgroundColor': '#1e1e1e', 'padding': '20px', 'borderRadius': '8px'}, children=[
                dcc.Graph(id='grafico-pastel-general')
            ]),
            html.Div(style={'width': '60%', 'backgroundColor': '#1e1e1e', 'padding': '20px', 'borderRadius': '8px'}, children=[
                dcc.Graph(id='grafico-barras-general')
            ])
        ]),

        html.Div(style={'backgroundColor': '#1e1e1e', 'padding': '25px', 'borderRadius': '8px'}, children=[
            html.H3("Rendimiento Nominal de Estudiantes Matriculados", style={'color': '#00adb5', 'marginTop': '0'}),
            html.Div(id='tabla-alumnos-container')
        ])
    ])

def render_panel_individual(nombre_alumno):
    df = obtener_datos_procesados()
    if df.empty: return html.Div("Error al cargar base de datos.")
    
    registro = df[df['nombre_alumno'] == nombre_alumno]
    if registro.empty: return html.Div("Estudiante no encontrado.")
    
    datos = registro.iloc[0]
    nota = datos['calificacion_final']
    
    estatus = "Excelente / Destacado" if nota >= 8.5 else "Regular / Aprobado" if nota >= 6.0 else "Alerta: Riesgo de Reprobación"
    color_alert = "#00adb5" if nota >= 6.0 else "#ff414d"

    return html.Div(style={'backgroundColor': '#121212', 'color': '#ffffff', 'fontFamily': 'Arial', 'padding': '40px'}, children=[
        dcc.Link("← Volver a la vista general", href="/", style={'color': '#00adb5', 'fontWeight': 'bold', 'textDecoration': 'none'}),
        html.Div(style={'backgroundColor': '#1e1e1e', 'padding': '30px', 'borderRadius': '8px', 'marginTop': '20px'}, children=[
            html.H2(nombre_alumno, style={'color': '#00adb5', 'margin': '0'}),
            html.P(f"Curso: {datos['curso']} | Grupo: {datos['grupo']}", style={'color': '#888'}),
            html.Hr(style={'borderColor': '#333'}),
            html.H3(f"Calificación Acumulada: {nota:.1f} pts", style={'color': color_alert}),
            html.P(f"Situación Actual: {estatus}", style={'fontWeight': 'bold'})
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

@app.callback(
    [Output('carrera-dropdown', 'options'), Output('curso-dropdown', 'options'), Output('grupo-dropdown', 'options')],
    [Input('trigger-inicial', 'n_intervals'), Input('carrera-dropdown', 'value'), Input('curso-dropdown', 'value')]
)
def manejar_filtros(n, carrera_sel, curso_sel):
    df = obtener_datos_procesados()
    if df is None or df.empty: 
        return [], [], []

    op_carreras = [{'label': c, 'value': c} for c in sorted(df['carrera'].unique())]
    
    df_f = df.copy()
    if carrera_sel: 
        df_f = df_f[df_f['carrera'] == carrera_sel]
    op_cursos = [{'label': c, 'value': c} for c in sorted(df_f['curso'].unique())]

    if curso_sel: 
        df_f = df_f[df_f['curso'] == curso_sel]
    op_grupos = [{'label': g, 'value': g} for g in sorted(df_f['grupo'].unique())]

    return op_carreras, op_cursos, op_grupos

@app.callback(
    [Output('grafico-pastel-general', 'figure'), Output('grafico-barras-general', 'figure'), 
     Output('tabla-alumnos-container', 'children'), Output('mensaje-estado-container', 'children')],
    [Input('carrera-dropdown', 'value'), Input('curso-dropdown', 'value'), Input('grupo-dropdown', 'value')]
)
def actualizar_dashboard(carrera_sel, curso_sel, grupo_sel):
    df = obtener_datos_procesados()
    if df is None or df.empty:
        return {}, {}, html.Div("No hay registros nominales disponibles."), html.Div("Sincronizando base de datos global de Moodle...", style={'color': '#00adb5', 'fontWeight': 'bold'})

    df_render = df.copy()
    if carrera_sel: df_render = df_render[df_render['carrera'] == carrera_sel]
    if curso_sel: df_render = df_render[df_render['curso'] == curso_sel]
    if grupo_sel: df_render = df_render[df_render['grupo'] == grupo_sel]

    if df_render.empty:
        return {}, {}, html.Div("Por favor seleccione un filtro válido en la barra superior para desplegar la lista de alumnos.", style={'color': '#888'}), ""

    df_render['Estatus'] = df_render['calificacion_final'].apply(lambda x: 'Aprobado (>=6.0)' if x >= 6.0 else 'Riesgo (<6.0)')
    
    fig_pie = px.pie(df_render, names='Estatus', title="Distribución de Estatus Académico", color='Estatus',
                     color_discrete_map={'Aprobado (>=6.0)': '#00adb5', 'Riesgo (<6.0)': '#ff414d'}, template='plotly_dark')
    
    fig_bar = px.bar(df_render, x='nombre_alumno', y='calificacion_final', title="Calificaciones Finales", template='plotly_dark')

    elementos_tabla = []
    for _, fila in df_render.iterrows():
        nombre = fila['nombre_alumno']
        elementos_tabla.append(
            html.Div(style={'padding': '12px', 'borderBottom': '1px solid #222', 'display': 'flex', 'justifyContent': 'space-between'}, children=[
                dcc.Link(nombre, href=f"/alumno/{urllib.parse.quote(nombre)}", style={'color': '#00adb5', 'textDecoration': 'none', 'fontWeight': '500'}),
                html.Span(f"{fila['calificacion_final']:.1f} pts", style={'color': '#fff', 'fontWeight': 'bold'})
            ])
        )

    contenedor_lista = html.Div(elementos_tabla, style={'maxHeight': '400px', 'overflowY': 'auto', 'backgroundColor': '#151515', 'borderRadius': '6px', 'padding': '10px'})
    
    return fig_pie, fig_bar, contenedor_lista, ""

if __name__ == '__main__':
    puerto = int(os.environ.get('PORT', 5000))
    app.run_server(debug=False, host='0.0.0.0', port=puerto)
