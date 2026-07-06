from flask import Flask
from flask_caching import Cache  
import pandas as pd
import os
import urllib.parse
import requests
from dash import Dash, dcc, html, Input, Output
import plotly.express as px
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
TOKEN_MOODLE = os.environ.get("MOODLE_TOKEN")
URL_MOODLE = os.environ.get("MOODLE_URL")
ID_CURSO_DTIC = 45  

server = Flask(__name__)

cache = Cache(server, config={
    'CACHE_TYPE': 'SimpleCache',
    'CACHE_DEFAULT_TIMEOUT': 600  # 600 segundos = 10 minutos. Los datos se actualizarán de Moodle cada 10 min.
})

app = Dash(__name__, server=server, url_base_pathname='/', suppress_callback_exceptions=True)
application = app.server

@cache.memoize(timeout=600) 
def obtener_datos_procesados():
    """
    Esta función va a Moodle, pero gracias a @cache.memoize, si se vuelve a llamar antes de 10 minutos,
    devuelve la información instantáneamente desde la memoria RAM del servidor sin viajar por internet.
    """
    if not TOKEN_MOODLE or not URL_MOODLE:
        print("Falta configurar MOODLE_TOKEN o MOODLE_URL.")
        return pd.DataFrame()

    parametros = {
        'wstoken': TOKEN_MOODLE,
        'wsfunction': 'gradereport_user_get_grade_items',
        'moodlewsrestformat': 'json',
        'courseid': ID_CURSO_DTIC
    }

    try:
        respuesta = requests.get(URL_MOODLE, params=parametros, timeout=30)
        datos_moodle = respuesta.json()
        lista_estudiantes = []
        
        if 'usergrades' in datos_moodle:
            for usuario in datos_moodle['usergrades']:
                nombre_completo = str(usuario.get('userfullname', 'ESTUDIANTE ANÓNIMO')).strip().upper()
                
                nombre_grupo = 'SIN GRUPO ASIGNADO'
                if 'groups' in usuario and usuario['groups']:
                    nombre_grupo = str(usuario['groups'][0].get('name', 'SIN GRUPO ASIGNADO')).strip().upper()
                elif 'groupname' in usuario:
                    nombre_grupo = str(usuario.get('groupname', 'SIN GRUPO ASIGNADO')).strip().upper()
                
                nota_final, quizz_software, quizz_redes, quizz_modelo, quizz_ambiental = 0.0, 0.0, 0.0, 0.0, 0.0
                
                for item in usuario.get('gradeitems', []):
                    nombre_item = item.get('itemname', '') or ''
                    valor_nota = item.get('graderaw', 0.0)
                    try:
                        valor_nota = float(valor_nota) if valor_nota is not None else 0.0
                    except:
                        valor_nota = 0.0
                        
                    if item.get('itemtype') == 'course' or 'TOTAL DEL CURSO' in nombre_item.upper():
                        nota_final = valor_nota
                    elif 'SOFTWARE' in nombre_item.upper() or 'DESARROLLO' in nombre_item.upper():
                        quizz_software = valor_nota
                    elif 'REDES' in nombre_item.upper():
                        quizz_redes = valor_nota
                    elif 'MODELO' in nombre_item.upper() or 'EDUCATIVO' in nombre_item.upper():
                        quizz_modelo = valor_nota
                    elif 'AMBIENTAL' in nombre_item.upper() or 'EDUCACIÓN AMBIENTAL' in nombre_item.upper():
                        quizz_ambiental = valor_nota

                lista_estudiantes.append({
                    'alumno': nombre_completo, 'grupo': nombre_grupo, 'nota_final': nota_final,
                    'Examen:Quizz Desarrollo Software (Real)': quizz_software, 'Examen:Quizz - Redes (Real)': quizz_redes,
                    'Examen:Quizz - Modelo Educativo (Real)': quizz_modelo, 'Examen:Quizz - Educación Ambiental (Real)': quizz_ambiental
                })
            
            return pd.DataFrame(lista_estudiantes)
        return pd.DataFrame()
    except Exception as e:
        print(f"Error en API Moodle: {str(e)}")
        return pd.DataFrame()

app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    html.Div(id='page-content')
])

def render_pagina_general():
    df = obtener_datos_procesados()
    if df.empty:
        return html.Div("Error: No se pudieron recuperar datos desde Moodle.", style={'padding': '30px', 'color': 'red'})
        
    lista_grupos = sorted(df['grupo'].unique())
    
    return html.Div(style={'fontFamily': 'Segoe UI, Arial', 'padding': '30px', 'backgroundColor': '#f8f9fa'}, children=[
        html.Div(style={'backgroundColor': '#003366', 'color': 'white', 'padding': '25px', 'borderRadius': '10px', 'marginBottom': '25px'}, children=[
            html.H1("Analítica del curso - En vivo desde Virtual UTTEC", style={'margin': '0', 'fontSize': '28px', 'fontWeight': '600'}),
            html.P("Monitoreo en tiempo real con sistema de caché de alta velocidad", style={'margin': '5px 0 0 0', 'opacity': '0.9'})
        ]),
        html.Div(style={'backgroundColor': 'white', 'padding': '20px', 'borderRadius': '8px', 'marginBottom': '25px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.05)'}, children=[
            html.Label("Filtrar Análisis por Grupo Académico:", style={'fontWeight': 'bold', 'color': '#333', 'display': 'block', 'marginBottom': '8px'}),
            dcc.Dropdown(
                id='grupo-dropdown',
                options=[{'label': f'Grupo: {g}', 'value': g} for g in lista_grupos] + [{'label': 'Mostrar Todos los Alumnos', 'value': 'TODOS'}],
                value='TODOS',
                clearable=False,
                style={'width': '100%', 'maxWidth': '400px'}
            )
        ]),
        html.Div(style={'display': 'grid', 'gridTemplateColumns': '1fr 1fr', 'gap': '25px', 'marginBottom': '30px'}, children=[
            html.Div(style={'backgroundColor': 'white', 'padding': '20px', 'borderRadius': '8px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.05)'}, children=[dcc.Graph(id='grafico-pastel-general')]),
            html.Div(style={'backgroundColor': 'white', 'padding': '20px', 'borderRadius': '8px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.05)'}, children=[dcc.Graph(id='grafico-barras-general')])
        ]),
        html.Div(style={'backgroundColor': 'white', 'padding': '25px', 'borderRadius': '8px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.05)'}, children=[
            html.H3("Listado de Estudiantes Inscritos", style={'color': '#003366', 'marginTop': '0', 'marginBottom': '20px'}),
            html.Div(id='tabla-alumnos-container')
        ])
    ])

def render_pagina_individual(nombre_alumno):
    df = obtener_datos_procesados()
    if df.empty: return html.Div("Error en la carga de datos.")
    registro = df[df['alumno'] == nombre_alumno]
    if registro.empty: return html.Div("Estudiante no encontrado.")
    
    datos = registro.iloc[0]
    nota = datos['nota_final']
    grupo = datos['grupo']
    
    estatus = "Excelente / Destacado" if nota >= 8.5 else "Regular / Aprobado" if nota >= 6.0 else "Alerta: Riesgo de Reprobación"
    color_alert = "#2ecc71" if nota >= 8.5 else "#f39c12" if nota >= 6.0 else "#e74c3c"
        
    quizzes = {
        'Desarrollo Software': datos.get('Examen:Quizz Desarrollo Software (Real)', 0.0),
        'Redes': datos.get('Examen:Quizz - Redes (Real)', 0.0),
        'Modelo Educativo': datos.get('Examen:Quizz - Modelo Educativo (Real)', 0.0),
        'Educación Ambiental': datos.get('Examen:Quizz - Educación Ambiental (Real)', 0.0)
    }
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Eres un tutor académico experto de la UTTEC. Da una recomendación breve (máximo 3 renglones) según las notas de los quizzes del curso propedéutico de la Dirección de TIC."},
                {"role": "user", "content": f"Estudiante con Promedio Final: {nota}. Quizzes: Desarrollo Software: {quizzes['Desarrollo Software']}, Redes: {quizzes['Redes']}, Modelo Educativo: {quizzes['Modelo Educativo']}, Educación Ambiental: {quizzes['Educación Ambiental']}. Genera una estrategia corta."}
            ],
            max_tokens=150,
            temperature=0.7
        )
        recomendacion_ia = response.choices[0].message.content.strip()
    except:
        recomendacion_ia = "Sugerencia estándar: Monitorear entregas en plataforma Moodle."
    
    fig_pastel_individual = px.pie(names=list(quizzes.keys()), values=list(quizzes.values()), title="Desglose de Rendimiento", hole=0.4)
    fig_pastel_individual.update_layout(margin=dict(t=50, b=10, l=10, r=10))

    return html.Div(style={'fontFamily': 'Segoe UI, Arial', 'padding': '30px', 'backgroundColor': '#f8f9fa'}, children=[
        dcc.Link("← Volver a la vista general", href="/", style={'textDecoration': 'none', 'color': '#003366', 'fontWeight': 'bold', 'display': 'inline-block', 'marginBottom': '20px'}),
        html.Div(style={'backgroundColor': 'white', 'padding': '30px', 'borderRadius': '10px', 'boxShadow': '0 4px 6px rgba(0,0,0,0.05)', 'display': 'grid', 'gridTemplateColumns': '1.2fr 0.8fr', 'gap': '30px'}, children=[
            html.Div(children=[
                html.H2(nombre_alumno, style={'color': '#003366', 'margin': '0 0 5px 0'}),
                html.P(f"Grupo Moodle: {grupo}", style={'color': '#7f8c8d', 'margin': '0 0 25px 0'}),
                html.Div(style={'display': 'grid', 'gridTemplateColumns': '1fr 1fr', 'gap': '20px', 'marginBottom': '25px'}, children=[
                    html.Div(style={'backgroundColor': '#f8f9fa', 'padding': '15px', 'borderRadius': '6px', 'borderLeft': f'5px solid {color_alert}'}, children=[
                        html.Small("PROMEDIO FINAL", style={'color': '#7f8c8d', 'fontWeight': 'bold'}),
                        html.H3(f"{nota} pts")
                    ]),
                    html.Div(style={'backgroundColor': '#f8f9fa', 'padding': '15px', 'borderRadius': '6px'}, children=[
                        html.Small("SITUACIÓN", style={'color': '#7f8c8d', 'fontWeight': 'bold'}),
                        html.H4(estatus, style={'color': color_alert, 'margin': '5px 0 0 0'})
                    ])
                ]),
                html.H4("💡 Recomendación de Tutoría Inteligente (OpenAI GPT):", style={'color': '#003366', 'marginBottom': '8px'}),
                html.P(recomendacion_ia, style={'color': '#2c3e50', 'lineHeight': '1.6', 'backgroundColor': '#eef2f7', 'padding': '15px', 'borderRadius': '6px', 'fontStyle': 'italic'})
            ]),
            html.Div(style={'borderLeft': '1px solid #eee', 'paddingLeft': '20px'}, children=[
                dcc.Graph(figure=fig_pastel_individual, config={'displayModeBar': False})
            ])
        ])
    ])

@app.callback(Output('page-content', 'children'), Input('url', 'pathname'))
def controlar_rutas(pathname):
    if not pathname or pathname == '/': return render_pagina_general()
    elif pathname.startswith('/alumno/'):
        nombre_alumno = urllib.parse.unquote(pathname.split('/alumno/')[1])
        return render_pagina_individual(nombre_alumno)
    return html.Div("404 - Página no encontrada")

@app.callback(
    [Output('grafico-pastel-general', 'figure'), Output('grafico-barras-general', 'figure'), Output('tabla-alumnos-container', 'children')],
    Input('grupo-dropdown', 'value')
)
def actualizar_panel_general(grupo_seleccionado):
    df = obtener_datos_procesados()
    if df.empty: return {}, {}, ""
    if grupo_seleccionado != 'TODOS': df = df[df['grupo'] == grupo_seleccionado]
        
    df['rango'] = pd.cut(df['nota_final'], bins=[-1, 5.9, 7.9, 8.9, 10], labels=['Menor a 6 (Reprobado)', '7 - 7.9 (Regular)', '8 - 8.9 (Bueno)', '9 - 10 (Excelente)'])
    conteos = df['rango'].value_counts().reset_index()
    conteos.columns = ['Estatus', 'Cantidad']
    
    fig_pastel = px.pie(conteos, names='Estatus', values='Cantidad', title='Distribución General', hole=0.4, color_discrete_sequence=['#e74c3c', '#f39c12', '#3498db', '#2ecc71'])
    fig_barras = px.bar(df, x='alumno', y='nota_final', color='nota_final', title='Rendimiento por Estudiante')
    fig_barras.update_layout(xaxis_tickangle=-45, margin=dict(b=120))
    
    elementos_lista = []
    for _, fila in df.iterrows():
        nombre_completo = fila['alumno']
        elementos_lista.append(
            html.Div(style={'padding': '12px 15px', 'borderBottom': '1px solid #eee', 'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center'}, children=[
                dcc.Link(nombre_completo, href=f"/alumno/{urllib.parse.quote(nombre_completo)}", style={'textDecoration': 'none', 'color': '#0056b3', 'fontWeight': '500'}),
                html.Span(f"{fila['nota_final']} pts", style={'backgroundColor': '#e9ecef', 'padding': '4px 10px', 'borderRadius': '12px', 'fontSize': '13px', 'fontWeight': 'bold'})
            ])
        )
    return fig_pastel, fig_barras, html.Div(elementos_lista, style={'maxHeight': '400px', 'overflowY': 'auto', 'border': '1px solid #ddd', 'borderRadius': '6px'})

if __name__ == '__main__':
    server.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
