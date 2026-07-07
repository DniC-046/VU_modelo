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
    'CACHE_TYPE': 'FileSystemCache',
    'CACHE_DIR': 'cache-directory',
    'CACHE_DEFAULT_TIMEOUT': 600 # 10 minutos en memoria
})

URL_MOODLE = "https://virtual2.uttecamac.edu.mx/webservice/rest/server.php"
MOODLE_TOKEN = os.environ.get("MOODLE_TOKEN")

@cache.memoize(timeout=600)
def obtener_datos_procesados():
    """
    Recupera dinámicamente todas las categorías (carreras), cursos y calificaciones 
    desde el Web Service de Virtual UTTEC.
    """
    if not MOODLE_TOKEN:
        print("Error: No se encontró el MOODLE_TOKEN en las variables de entorno.")
        return pd.DataFrame()

    lista_completa_alumnos = []
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}

    try:
        param_cat = {
            'wstoken': MOODLE_TOKEN,
            'wsfunction': 'core_course_get_categories',
            'moodlewsrestformat': 'json'
        }
        res_cat = requests.get(URL_MOODLE, params=param_cat, timeout=30)
        categorias = res_cat.json()
        
        if not isinstance(categorias, list) or "exception" in categorias:
            print("Error al recuperar categorías o token inválido.")
            return pd.DataFrame()

        param_cur = {
            'wstoken': MOODLE_TOKEN,
            'wsfunction': 'core_course_get_courses',
            'moodlewsrestformat': 'json'
        }
        res_cur = requests.get(URL_MOODLE, params=param_cur, timeout=30)
        cursos = res_cur.json()

        if not isinstance(cursos, list):
            print("No se encontraron cursos mapeables.")
            return pd.DataFrame()

        for curso in cursos:
            course_id = curso.get('id')
            nombre_curso = curso.get('fullname')
            id_categoria = curso.get('categoryid')
            
            nombre_carrera = next((cat['name'] for cat in categorias if cat['id'] == id_categoria), "General / Propedéutico")

            if course_id == 1:
                continue

            param_calif = {
                'wstoken': MOODLE_TOKEN,
                'wsfunction': 'gradereport_user_get_grades_table',
                'moodlewsrestformat': 'json',
                'courseid': course_id
            }
            
            res_calif = requests.get(URL_MOODLE, params=param_calif, timeout=30)
            data_curso = res_calif.json()

            if not data_curso or "tables" not in data_curso:
                continue

            for tabla_usuario in data_curso.get('tables', []):
                user_id = tabla_usuario.get('userid')
                user_fullname = tabla_usuario.get('userfullname')
                
                nota_final = 0.0
                for item in tabla_usuario.get('tabledata', []):
                    if item.get('itemname') and 'total' in item.get('itemname').get('text', '').lower():
                        try:
                            nota_final = float(item.get('grade', {}).get('text', '0.0'))
                        except ValueError:
                            nota_final = 0.0

                grupo_detectado = "Sin Grupo Asignado"
                if "-" in nombre_curso:
                    partes = nombre_curso.split("-")
                    grupo_detectado = partes[-1].strip()
                elif "grupo" in nombre_curso.lower():
                    grupo_detectado = nombre_curso.split()[-1]

                lista_completa_alumnos.append({
                    'id_estudiante': user_id,
                    'nombre_alumno': user_fullname,
                    'carrera': nombre_carrera,
                    'curso': nombre_curso,
                    'grupo': grupo_detectado,
                    'calificacion_final': nota_final
                })

        df_institucional = pd.DataFrame(lista_completa_alumnos)
        return df_institucional

    except Exception as e:
        print(f"Excepción crítica durante la recolección masiva: {e}")
        return pd.DataFrame()


df_inicial = obtener_datos_procesados()

app.layout = html.Div(style={'backgroundColor': '#1e1e1e', 'color': '#ffffff', 'fontFamily': 'Arial', 'padding': '20px'}, children=[
    html.H1("Analítica Institucional - Dashboard Universidad", style={'textAlign': 'center', 'color': '#00adb5'}),
    html.P("Monitoreo automatizado global de rendimiento por Carrera, Curso y Grupo", style={'textAlign': 'center'}),
    
    html.Div(style={'display': 'flex', 'gap': '15px', 'marginBottom': '30px', 'justifyContent': 'center'}, children=[
        html.Div(style={'width': '30%'}, children=[
            html.Label("1. Filtrar por Carrera / División:", style={'fontWeight': 'bold'}),
            dcc.Dropdown(
                id='carrera-dropdown',
                options=[] if df_inicial.empty else [{'label': c, 'value': c} for c in df_inicial['carrera'].unique()],
                placeholder="Selecciona una Carrera",
                style={'color': '#000000'}
            )
        ]),
        html.Div(style={'width': '30%'}, children=[
            html.Label("2. Filtrar por Curso:", style={'fontWeight': 'bold'}),
            dcc.Dropdown(
                id='curso-dropdown',
                placeholder="Selecciona un Curso",
                style={'color': '#000000'}
            )
        ]),
        html.Div(style={'width': '30%'}, children=[
            html.Label("3. Filtrar por Grupo Académico:", style={'fontWeight': 'bold'}),
            dcc.Dropdown(
                id='grupo-dropdown',
                placeholder="Selecciona un Grupo",
                style={'color': '#000000'}
            )
        ]),
    ]),

    html.Div(id='mensaje-estado-container', style={'color': '#ff414d', 'textAlign': 'center', 'fontWeight': 'bold'}),

    html.Div(style={'display': 'flex', 'gap': '20px'}, children=[
        html.Div(style={'width': '50%', 'backgroundColor': '#252525', 'padding': '15px', 'borderRadius': '8px'}, children=[
            dcc.Graph(id='grafico-pastel-general')
        ]),
        html.Div(style={'width': '50%', 'backgroundColor': '#252525', 'padding': '15px', 'borderRadius': '8px'}, children=[
            dcc.Graph(id='grafico-barras-general')
        ])
    ]),

    html.Div(style={'marginTop': '30px', 'backgroundColor': '#252525', 'padding': '20px', 'borderRadius': '8px'}, children=[
        html.H3("Desglose Nominal de Rendimiento Académico", style={'color': '#00adb5'}),
        html.Div(id='tabla-alumnos-container')
    ])
])


@app.callback(
    [Output('curso-dropdown', 'options'), Output('grupo-dropdown', 'options')],
    [Input('carrera-dropdown', 'value'), Input('curso-dropdown', 'value')]
)
def set_dropdown_options(carrera_sel, curso_sel):
    df = obtener_datos_procesados()
    if df is None or df.empty:
        return [], []
    
    df_filtrado = df.copy()
    if carrera_sel:
        df_filtrado = df_filtrado[df_filtrado['carrera'] == carrera_sel]
    
    opciones_cursos = [{'label': c, 'value': c} for c in df_filtrado['curso'].unique()]
    
    if curso_sel:
        df_filtrado = df_filtrado[df_filtrado['curso'] == curso_sel]
        
    opciones_grupos = [{'label': g, 'value': g} for g in df_filtrado['grupo'].unique()]
    
    return opciones_cursos, opciones_grupos


@app.callback(
    [Output('grafico-pastel-general', 'figure'), 
     Output('grafico-barras-general', 'figure'), 
     Output('tabla-alumnos-container', 'children'),
     Output('mensaje-estado-container', 'children')],
    [Input('carrera-dropdown', 'value'), 
     Input('curso-dropdown', 'value'), 
     Input('grupo-dropdown', 'value')]
)
def actualizar_dashboard_global(carrera_sel, curso_sel, grupo_sel):
    df = obtener_datos_procesados()
    
    if df is None or df.empty:
        return {}, {}, html.Div("Fallo de sincronización con Moodle. Revisa el estatus del token corporativo."), "Error: No se pudieron recuperar datos institucionales de Virtual UTTEC."

    df_render = df.copy()
    if carrera_sel:
        df_render = df_render[df_render['carrera'] == carrera_sel]
    if curso_sel:
        df_render = df_render[df_render['curso'] == curso_sel]
    if grupo_sel:
        df_render = df_render[df_render['grupo'] == grupo_sel]

    if df_render.empty:
        return {}, {}, html.Div("No hay alumnos matriculados con este set de filtros."), "Alerta: No hay datos para la combinación seleccionada."

    df_render['Estatus'] = df_render['calificacion_final'].apply(lambda x: 'Aprobado (>=6.0)' if x >= 6.0 else 'Riesgo de Reprobación (<6.0)')
    
    fig_pie = px.pie(
        df_render, names='Estatus', 
        title="Estatus de Permanencia Académica",
        color='Estatus',
        color_discrete_map={'Aprobado (>=6.0)': '#00adb5', 'Riesgo de Reprobación (<6.0)': '#ff414d'},
        template='plotly_dark'
    )

    fig_bar = px.bar(
        df_render, x='nombre_alumno', y='calificacion_final',
        color='calificacion_final',
        title="Promedio Acumulado por Estudiante",
        labels={'nombre_alumno': 'Estudiante', 'calificacion_final': 'Calificación Cruda'},
        template='plotly_dark',
        color_continuous_scale=px.colors.sequential.Viridis
    )

    tabla_html = html.Table(
        style={'width': '100%', 'borderCollapse': 'collapse', 'marginTop': '10px', 'color': '#ffffff'},
        children=[
            html.Thead(html.Tr([
                html.Th("Estudiante", style={'borderBottom': '2px solid #00adb5', 'padding': '10px', 'textAlign': 'left'}),
                html.Th("Carrera / División", style={'borderBottom': '2px solid #00adb5', 'padding': '10px', 'textAlign': 'left'}),
                html.Th("Asignatura / Curso", style={'borderBottom': '2px solid #00adb5', 'padding': '10px', 'textAlign': 'left'}),
                html.Th("Grupo", style={'borderBottom': '2px solid #00adb5', 'padding': '10px', 'textAlign': 'center'}),
                html.Th("Calificación", style={'borderBottom': '2px solid #00adb5', 'padding': '10px', 'textAlign': 'center'})
            ])),
            html.Tbody([
                html.Tr(style={'borderBottom': '1px solid #333333'}, children=[
                    html.Td(row['nombre_alumno'], style={'padding': '8px'}),
                    html.Td(row['carrera'], style={'padding': '8px'}),
                    html.Td(row['curso'], style={'padding': '8px'}),
                    html.Td(row['grupo'], style={'padding': '8px', 'textAlign': 'center'}),
                    html.Td(f"{row['calificacion_final']:.1f} pts", style={
                        'padding': '8px', 'textAlign': 'center', 'fontWeight': 'bold',
                        'color': '#00adb5' if row['calificacion_final'] >= 6.0 else '#ff414d'
                    })
                ]) for _, row in df_render.iterrows()
            ])
        ]
    )

    return fig_pie, fig_bar, tabla_html, ""

if __name__ == '__main__':
    puerto = int(os.environ.get('PORT', 5000))
    app.run_server(debug=False, host='0.0.0.0', port=puerto)
