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
    'CACHE_DEFAULT_TIMEOUT': 300  # 5 minutos en memoria
})

URL_MOODLE = "https://virtual2.uttecamac.edu.mx/webservice/rest/server.php"

@cache.memoize(timeout=300)
def obtener_datos_procesados():
    token_moodle = os.environ.get("MOODLE_TOKEN")
    if not token_moodle:
        print("Moodle Cache Error: No se encontró la variable MOODLE_TOKEN.")
        return pd.DataFrame()

    lista_completa_alumnos = []

    try:
        param_cat = {
            'wstoken': token_moodle,
            'wsfunction': 'core_course_get_categories',
            'moodlewsrestformat': 'json'
        }
        res_cat = requests.get(URL_MOODLE, params=param_cat, timeout=25)
        categorias = res_cat.json()
        
        if 'exception' in categorias or not isinstance(categorias, list):
            print(f"Moodle API Exception en categorías: {categorias}")
            return pd.DataFrame()

        param_cur = {
            'wstoken': token_moodle,
            'wsfunction': 'core_course_get_courses',
            'moodlewsrestformat': 'json'
        }
        res_cur = requests.get(URL_MOODLE, params=param_cur, timeout=25)
        cursos = res_cur.json()

        if 'exception' in cursos or not isinstance(cursos, list):
            print(f"Moodle API Exception en cursos: {cursos}")
            return pd.DataFrame()

        for curso in cursos:
            course_id = curso.get('id')
            nombre_curso = curso.get('fullname', 'Curso sin nombre')
            id_categoria = curso.get('categoryid')
            
            if course_id == 1:
                continue

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
                res_calif = requests.get(URL_MOODLE, params=param_calif, timeout=15)
                data_curso = res_calif.json()
                
                if 'exception' in data_curso or 'tables' not in data_curso:
                    continue
                
                for tabla_usuario in data_curso.get('tables', []):
                    user_fullname = tabla_usuario.get('userfullname', 'Estudiante anónimo')
                    
                    nota_final = 0.0
                    for item in tabla_usuario.get('tabledata', []):
                        item_name_dict = item.get('itemname', {})
                        item_text = ""
                        if isinstance(item_name_dict, dict):
                            item_text = item_name_dict.get('text', '').lower()
                        
                        if 'total' in item_text or 'curso' in item_text:
                            try:
                                grade_dict = item.get('grade', {})
                                nota_final = float(grade_dict.get('text', '0.0'))
                            except:
                                nota_final = 0.0

                    grupo_detectado = "Sin Grupo Asignado"
                    if "-" in nombre_curso:
                        grupo_detectado = nombre_curso.split("-")[-1].strip().upper()
                    elif "GRUPO" in nombre_curso.upper():
                        grupo_detectado = nombre_curso.upper().split("GRUPO")[-1].strip()

                    lista_completa_alumnos.append({
                        'carrera': nombre_carrera.strip().upper(),
                        'curso': nombre_curso.strip().upper(),
                        'grupo': grupo_detectado,
                        'nombre_alumno': user_fullname.strip().upper(),
                        'calificacion_final': nota_final
                    })
            except Exception as inner_error:
                print(f"Error procesando curso ID {course_id}: {inner_error}")
                continue

        return pd.DataFrame(lista_completa_alumnos)

    except Exception as e:
        print(f"Excepción general en recolección Moodle: {e}")
        return pd.DataFrame()

app.layout = html.Div(style={'backgroundColor': '#121212', 'color': '#ffffff', 'fontFamily': 'Segoe UI, Arial', 'padding': '30px'}, children=[
    html.Div(style={'borderBottom': '2px solid #00adb5', 'paddingBottom': '15px', 'marginBottom': '30px'}, children=[
        html.H1("Analítica UTTEC - Control Institucional", style={'margin': '0', 'color': '#00adb5', 'fontWeight': '600'}),
        html.P("Mapeo automatizado global en vivo desde la plataforma Virtual UTTEC", style={'margin': '5px 0 0 0', 'color': '#888888'})
    ]),
    
    html.Div(style={'display': 'flex', 'gap': '20px', 'marginBottom': '30px'}, children=[
        html.Div(style={'flex': '1'}, children=[
            html.Label("División / Carrera:", style={'fontWeight': '500', 'display': 'block', 'marginBottom': '8px'}),
            dcc.Dropdown(id='carrera-dropdown', placeholder="Cargando divisiones...", style={'color': '#000000'})
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


@app.callback(
    [Output('carrera-dropdown', 'options'),
     Output('curso-dropdown', 'options'),
     Output('grupo-dropdown', 'options')],
    [Input('carrera-dropdown', 'value'),
     Input('curso-dropdown', 'value')]
)
def poblar_filtros(carrera_sel, curso_sel):
    df = obtener_datos_procesados()
    if df is None or df.empty:
        return [], [], []

    opciones_carreras = [{'label': c, 'value': c} for c in sorted(df['carrera'].unique())]
    
    df_filtrado = df.copy()
    if carrera_sel:
        df_filtrado = df_filtrado[df_filtrado['carrera'] == carrera_sel]
    opciones_cursos = [{'label': c, 'value': c} for c in sorted(df_filtrado['curso'].unique())]

    if curso_sel:
        df_filtrado = df_filtrado[df_filtrado['curso'] == curso_sel]
    opciones_grupos = [{'label': g, 'value': g} for g in sorted(df_filtrado['grupo'].unique())]

    return opciones_carreras, opciones_cursos, opciones_grupos


@app.callback(
    [Output('grafico-pastel-general', 'figure'),
     Output('grafico-barras-general', 'figure'),
     Output('tabla-alumnos-container', 'children'),
     Output('mensaje-estado-container', 'children')],
    [Input('carrera-dropdown', 'value'),
     Input('curso-dropdown', 'value'),
     Input('grupo-dropdown', 'value')]
)
def actualizar_dashboard(carrera_sel, curso_sel, grupo_sel):
    df = obtener_datos_procesados()
    
    if df is None or df.empty:
        return {}, {}, "", html.Div("Fallo de sincronización con Moodle. Verifique los alcances globales del Token en Virtual UTTEC.", style={'color': '#ff414d', 'fontWeight': 'bold'})

    df_render = df.copy()
    if carrera_sel:
        df_render = df_render[df_render['carrera'] == carrera_sel]
    if curso_sel:
        df_render = df_render[df_render['curso'] == curso_sel]
    if grupo_sel:
        df_render = df_render[df_render['grupo'] == grupo_sel]

    if df_render.empty:
        return {}, {}, html.Div("No hay registros que coincidan con la selección.", style={'color': '#888'}), ""

    df_render['Estatus'] = df_render['calificacion_final'].apply(lambda x: 'Aprobado (>=6.0)' if x >= 6.0 else 'Riesgo / Alerta (<6.0)')

    fig_pie = px.pie(
        df_render, names='Estatus', 
        title="Distribución de Estatus Académico",
        color='Estatus',
        color_discrete_map={'Aprobado (>=6.0)': '#00adb5', 'Riesgo / Alerta (<6.0)': '#ff414d'},
        template='plotly_dark'
    )

    fig_bar = px.bar(
        df_render, x='nombre_alumno', y='calificacion_final',
        color='calificacion_final',
        title="Calificaciones Finales de Alumnos",
        template='plotly_dark',
        color_continuous_scale=px.colors.sequential.Teal
    )
    fig_bar.update_layout(xaxis_tickangle=-45)

    # Construcción de la Tabla HTML
    filas = []
    for _, fila in df_render.iterrows():
        filas.append(html.Tr(style={'borderBottom': '1px solid #222'}, children=[
            html.Td(fila['nombre_alumno'], style={'padding': '10px'}),
            html.Td(fila['carrera'], style={'padding': '10px'}),
            html.Td(fila['curso'], style={'padding': '10px'}),
            html.Td(fila['grupo'], style={'padding': '10px', 'textAlign': 'center'}),
            html.Td(f"{fila['calificacion_final']:.1f}", style={
                'padding': '10px', 'textAlign': 'center', 'fontWeight': 'bold',
                'color': '#00adb5' if fila['calificacion_final'] >= 6.0 else '#ff414d'
            })
        ]))

    tabla = html.Table(style={'width': '100%', 'borderCollapse': 'collapse', 'color': '#fff'}, children=[
        html.Thead(html.Tr([
            html.Th("Estudiante", style={'textAlign': 'left', 'padding': '10px', 'borderBottom': '2px solid #00adb5'}),
            html.Th("Carrera", style={'textAlign': 'left', 'padding': '10px', 'borderBottom': '2px solid #00adb5'}),
            html.Th("Curso", style={'textAlign': 'left', 'padding': '10px', 'borderBottom': '2px solid #00adb5'}),
            html.Th("Grupo", style={'textAlign': 'center', 'padding': '10px', 'borderBottom': '2px solid #00adb5'}),
            html.Th("Calificación", style={'textAlign': 'center', 'padding': '10px', 'borderBottom': '2px solid #00adb5'})
        ])),
        html.Tbody(filas)
    ])

    return fig_pie, fig_bar, tabla, ""

if __name__ == '__main__':
    puerto = int(os.environ.get('PORT', 5000))
    app.run_server(debug=False, host='0.0.0.0', port=puerto)
