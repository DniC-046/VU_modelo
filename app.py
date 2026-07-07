import os
import requests
import pandas as pd
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.express as px
from flask_caching import Cache

app = dash.Dash(__name__, title="Analítica UTTEC - Institucional")
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
        return pd.DataFrame()

    lista_completa_alumnos = []
    try:
        param_cat = {'wstoken': token_moodle, 'wsfunction': 'core_course_get_categories', 'moodlewsrestformat': 'json'}
        res_cat = requests.get(URL_MOODLE, params=param_cat, timeout=20)
        categorias = res_cat.json()
        if 'exception' in categorias or not isinstance(categorias, list):
            return pd.DataFrame()

        param_cur = {'wstoken': token_moodle, 'wsfunction': 'core_course_get_courses', 'moodlewsrestformat': 'json'}
        res_cur = requests.get(URL_MOODLE, params=param_cur, timeout=20)
        cursos = res_cur.json()
        if 'exception' in cursos or not isinstance(cursos, list):
            return pd.DataFrame()

        for curso in cursos:
            course_id = curso.get('id')
            nombre_curso = curso.get('fullname', '')
            id_categoria = curso.get('categoryid')
            if course_id == 1: continue

            nombre_carrera = "General / Propedéutico"
            for cat in categorias:
                if cat.get('id') == id_categoria:
                    nombre_carrera = cat.get('name')
                    break

            param_calif = {
                'wstoken': token_moodle,
                'wsfunction': 'gradereport_user_get_grades_table',
                'moodlewsrestformat': 'json',
                'courseid': course_id
            }
            try:
                res_calif = requests.get(URL_MOODLE, params=param_calif, timeout=10)
                data_curso = res_calif.json()
                if 'exception' in data_curso or 'tables' not in data_curso: continue
                
                for tabla_usuario in data_curso.get('tables', []):
                    user_fullname = tabla_usuario.get('userfullname', '')
                    nota_final = 0.0
                    for item in tabla_usuario.get('tabledata', []):
                        item_text = item.get('itemname', {}).get('text', '').lower() if isinstance(item.get('itemname'), dict) else ""
                        if 'total' in item_text or 'curso' in item_text:
                            try:
                                nota_final = float(item.get('grade', {}).get('text', '0.0'))
                            except:
                                nota_final = 0.0

                    grupo_detectado = "Sin Grupo"
                    if "-" in nombre_curso: grupo_detectado = nombre_curso.split("-")[-1].strip().upper()

                    lista_completa_alumnos.append({
                        'carrera': nombre_carrera.strip().upper(),
                        'curso': nombre_curso.strip().upper(),
                        'grupo': grupo_detectado,
                        'nombre_alumno': user_fullname.strip().upper(),
                        'calificacion_final': nota_final
                    })
            except:
                continue
        return pd.DataFrame(lista_completa_alumnos)
    except:
        return pd.DataFrame()

app.layout = html.Div(style={'backgroundColor': '#121212', 'color': '#ffffff', 'fontFamily': 'Arial', 'padding': '30px'}, children=[
    dcc.Interval(id='trigger-inicial', interval=500, max_intervals=1), # Llama a Moodle 500ms después de abrir
    html.H1("Analítica UTTEC - Control Institucional", style={'color': '#00adb5'}),
    
    html.Div(style={'display': 'flex', 'gap': '20px', 'marginBottom': '30px'}, children=[
        html.Div(style={'flex': '1'}, children=[
            html.Label("Carrera:"), dcc.Dropdown(id='carrera-dropdown', placeholder="Cargando desde Moodle...", style={'color': '#000'})
        ]),
        html.Div(style={'flex': '1'}, children=[
            html.Label("Curso:"), dcc.Dropdown(id='curso-dropdown', placeholder="Esperando carrera...", style={'color': '#000'})
        ]),
        html.Div(style={'flex': '1'}, children=[
            html.Label("Grupo:"), dcc.Dropdown(id='grupo-dropdown', placeholder="Esperando curso...", style={'color': '#000'})
        ]),
    ]),
    html.Div(id='mensaje-estado-container'),
    html.Div(style={'display': 'flex', 'gap': '25px', 'marginBottom': '30px'}, children=[
        html.Div(style={'width': '40%'}, children=[dcc.Graph(id='grafico-pastel-general')]),
        html.Div(style={'width': '60%'}, children=[dcc.Graph(id='grafico-barras-general')])
    ]),
    html.Div(id='tabla-alumnos-container')
])

@app.callback(
    Output('carrera-dropdown', 'options'),
    Input('trigger-inicial', 'n_intervals')
)
def cargar_carreras_iniciales(n):
    df = obtener_datos_procesados()
    if df is None or df.empty: return []
    return [{'label': c, 'value': c} for c in sorted(df['carrera'].unique())]

@app.callback(
    [Output('curso-dropdown', 'options'), Output('grupo-dropdown', 'options')],
    [Input('carrera-dropdown', 'value'), Input('curso-dropdown', 'value')]
)
def sincronizar_filtros(carrera_sel, curso_sel):
    df = obtener_datos_procesados()
    if df is None or df.empty: return [], []
    df_f = df.copy()
    if carrera_sel: df_f = df_f[df_f['carrera'] == carrera_sel]
    op_cursos = [{'label': c, 'value': c} for c in sorted(df_f['curso'].unique())]
    if curso_sel: df_f = df_f[df_f['curso'] == curso_sel]
    op_grupos = [{'label': g, 'value': g} for g in sorted(df_f['grupo'].unique())]
    return op_cursos, op_grupos

@app.callback(
    [Output('grafico-pastel-general', 'figure'), Output('grafico-barras-general', 'figure'), 
     Output('tabla-alumnos-container', 'children'), Output('mensaje-estado-container', 'children')],
    [Input('carrera-dropdown', 'value'), Input('curso-dropdown', 'value'), Input('grupo-dropdown', 'value')]
)
def actualizar_dashboard(carrera_sel, curso_sel, grupo_sel):
    df = obtener_datos_procesados()
    if df is None or df.empty:
        return {}, {}, "", html.Div("Sincronizando u obteniendo datos globales de Moodle...", style={'color': '#00adb5'})

    df_render = df.copy()
    if carrera_sel: df_render = df_render[df_render['carrera'] == carrera_sel]
    if curso_sel: df_render = df_render[df_render['curso'] == curso_sel]
    if grupo_sel: df_render = df_render[df_render['grupo'] == grupo_sel]

    df_render['Estatus'] = df_render['calificacion_final'].apply(lambda x: 'Aprobado (>=6.0)' if x >= 6.0 else 'Riesgo (<6.0)')
    fig_pie = px.pie(df_render, names='Estatus', title="Estatus Académico", template='plotly_dark')
    fig_bar = px.bar(df_render, x='nombre_alumno', y='calificacion_final', title="Calificaciones", template='plotly_dark')
    
    filas = [html.Tr([
        html.Td(r['nombre_alumno']), html.Td(r['carrera']), html.Td(r['curso']), html.Td(r['grupo']), html.Td(f"{r['calificacion_final']:.1f}")
    ]) for _, r in df_render.iterrows()]
    
    tabla = html.Table(children=[html.Tbody(filas)], style={'width': '100%', 'color': '#fff'})
    return fig_pie, fig_bar, tabla, ""

if __name__ == '__main__':
    puerto = int(os.environ.get('PORT', 5000))
    app.run_server(debug=False, host='0.0.0.0', port=puerto)
