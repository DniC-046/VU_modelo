from flask import Flask
import pandas as pd
import os
import urllib.parse
from dash import Dash, dcc, html, Input, Output
import plotly.express as px

# NUEVO: Importamos las librerías de OpenAI y control de entorno
from openai import OpenAI
from dotenv import load_dotenv

# Cargamos el archivo .env local (en Render se cargará el Env Group automáticamente)
load_dotenv()

# Conexión Segura a la API Key de OpenAI mediante variables de entorno
# Nota: "OPENAI_API_KEY" debe ser el nombre exacto que pusiste en tu grupo de Render
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# 1. Configuración del Servidor Flask base
server = Flask(__name__)

def obtener_datos_procesados():
    ruta_archivo = 'Calificaciones de Virtual.ods'
    if not os.path.exists(ruta_archivo):
        if os.path.exists('calificaciones de virtual.ods'):
            ruta_archivo = 'calificaciones de virtual.ods'
        else:
            return pd.DataFrame()
    
    df = pd.read_excel(ruta_archivo, engine='odf')
    df.columns = [str(c).strip() for c in df.columns]
    
    if 'nombre' in df.columns and 'apellido' in df.columns:
        df['alumno'] = (df['nombre'].astype(str) + ' ' + df['apellido'].astype(str)).str.strip().str.upper()
    else:
        df['alumno'] = df[df.columns[0]].astype(str).str.strip().str.upper()
    
    columnas_examenes = [
        'Examen:Quizz Desarrollo Software (Real)',
        'Examen:Quizz - Redes (Real)',
        'Examen:Quizz - Modelo Educativo (Real)',
        'Examen:Quizz - Educación Ambiental (Real)'
    ]
    
    for col in columnas_examenes:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
            
    if 'Total del curso (Real)' in df.columns:
        df['nota_final'] = pd.to_numeric(df['Total del curso (Real)'], errors='coerce').fillna(0.0)
    else:
        df['nota_final'] = 0.0
    
    columnas_grupo = [c for c in df.columns if 'grupo' in c.lower()]
    if columnas_grupo:
        df['grupo'] = df[columnas_grupo[0]].fillna('Sin Grupo').astype(str).str.upper()
    else:
        df['grupo'] = 'GRUPO ÚNICO'
        
    return df

# 2. Inicialización de Dash multipágina
app = Dash(__name__, server=server, url_base_pathname='/', suppress_callback_exceptions=True)
application = app.server

app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    html.Div(id='page-content')
])

# ----------------------------------------------------------------------------
# VISTA 1: ANALÍTICA GENERAL DEL CURSO
# ----------------------------------------------------------------------------
def render_pagina_general():
    df = obtener_datos_procesados()
    if df.empty:
        return html.Div("Error: No se encontró el archivo 'Calificaciones de Virtual.ods' en el servidor.")
        
    lista_grupos = sorted(df['grupo'].unique())
    
    return html.Div(style={'fontFamily': 'Segoe UI, Arial', 'padding': '30px', 'backgroundColor': '#f8f9fa'}, children=[
        html.Div(style={'backgroundColor': '#003366', 'color': 'white', 'padding': '25px', 'borderRadius': '10px', 'marginBottom': '25px'}, children=[
            html.H1("Analítica del curso - Virtual UTTEC", style={'margin': '0', 'fontSize': '28px', 'fontWeight': '600'}),
            html.P("Monitoreo inteligente asistido por IA de OpenAI para el Propedéutico DTIC", style={'margin': '5px 0 0 0', 'opacity': '0.9'})
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
            html.Div(style={'backgroundColor': 'white', 'padding': '20px', 'borderRadius': '8px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.05)'}, children=[
                dcc.Graph(id='grafico-pastel-general')
            ]),
            html.Div(style={'backgroundColor': 'white', 'padding': '20px', 'borderRadius': '8px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.05)'}, children=[
                dcc.Graph(id='grafico-barras-general')
            ])
        ]),
        
        html.Div(style={'backgroundColor': 'white', 'padding': '25px', 'borderRadius': '8px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.05)'}, children=[
            html.H3("Listado de Estudiantes Inscritos (Haz clic en un nombre para ver su análisis)", style={'color': '#003366', 'marginTop': '0', 'marginBottom': '20px'}),
            html.Div(id='tabla-alumnos-container')
        ])
    ])

# ----------------------------------------------------------------------------
# VISTA 2: FICHA DE ANÁLISIS INDIVIDUAL CON CONSULTA EN TIEMPO REAL A OPENAI
# ----------------------------------------------------------------------------
def render_pagina_individual(nombre_alumno):
    df = obtener_datos_procesados()
    if df.empty:
        return html.Div("Error en la carga de datos.")
        
    registro = df[df['alumno'] == nombre_alumno]
    if registro.empty:
        return html.Div("Estudiante no encontrado.")
        
    datos = registro.iloc[0]
    nota = datos['nota_final']
    grupo = datos['grupo']
    
    if nota >= 8.5:
        estatus = "Excelente / Destacado"
        color_alert = "#2ecc71"
    elif nota >= 6.0:
        estatus = "Regular / Aprobado"
        color_alert = "#f39c12"
    else:
        estatus = "Alerta: Riesgo de Reprobación"
        color_alert = "#e74c3c"
        
    quizzes = {
        'Desarrollo Software': datos.get('Examen:Quizz Desarrollo Software (Real)', 0.0),
        'Redes': datos.get('Examen:Quizz - Redes (Real)', 0.0),
        'Modelo Educativo': datos.get('Examen:Quizz - Modelo Educativo (Real)', 0.0),
        'Educación Ambiental': datos.get('Examen:Quizz - Educación Ambiental (Real)', 0.0)
    }
    
    # --- CONEXIÓN E INTEGRACIÓN CON LA API DE OPENAI ---
    try:
        # Le pedimos a GPT que actúe como un tutor analítico de la UTTEC
        response = client.chat.completions.create(
            model="gpt-4o-mini", # Usamos el modelo rápido y optimizado para producción
            messages=[
                {"role": "system", "content": "Eres un tutor académico experto de la Universidad Tecnológica de Tecámac (UTTEC). Tu labor es dar una recomendación pedagógica breve y directa (máximo 3 renglones) según las calificaciones obtenidas por el alumno en sus quizzes del curso propedéutico de la Dirección de TIC."},
                {"role": "user", "content": f"Por favor analiza al estudiante con Promedio Final: {nota}. Sus calificaciones individuales en Quizzes son: Desarrollo Software: {quizzes['Desarrollo Software']}, Redes: {quizzes['Redes']}, Modelo Educativo: {quizzes['Modelo Educativo']}, Educación Ambiental: {quizzes['Educación Ambiental']}. Genera una acción o estrategia de mejora específica."}
            ],
            max_tokens=150,
            temperature=0.7
        )
        recomendacion_ia = response.choices[0].message.content.strip()
    except Exception as e:
        # Respaldo seguro por si la API llegara a fallar por falta de saldo o conexión
        recomendacion_ia = f"Sugerencia estándar: Monitorear entregas en plataforma. (Nota técnica: No se pudo conectar con OpenAI: {str(e)})"
    
    fig_pastel_individual = px.pie(
        names=list(quizzes.keys()),
        values=list(quizzes.values()),
        title="Desglose del Rendimiento en Quizzes (Puntos Obtenidos)",
        hole=0.4,
        color_discrete_sequence=px.colors.qualitative.Safe
    )
    fig_pastel_individual.update_layout(margin=dict(t=50, b=10, l=10, r=10))

    return html.Div(style={'fontFamily': 'Segoe UI, Arial', 'padding': '30px', 'backgroundColor': '#f8f9fa'}, children=[
        dcc.Link("← Volver a la vista general", href="/", style={'textDecoration': 'none', 'color': '#003366', 'fontWeight': 'bold', 'display': 'inline-block', 'marginBottom': '20px'}),
        
        html.Div(style={'backgroundColor': 'white', 'padding': '30px', 'borderRadius': '10px', 'boxShadow': '0 4px 6px rgba(0,0,0,0.05)', 'display': 'grid', 'gridTemplateColumns': '1.2fr 0.8fr', 'gap': '30px'}, children=[
            
            html.Div(children=[
                html.H2(nombre_alumno, style={'color': '#003366', 'margin': '0 0 5px 0', 'fontSize': '28px'}),
                html.P(f"Grupo: {grupo}", style={'color': '#7f8c8d', 'margin': '0 0 25px 0', 'fontSize': '16px'}),
                
                html.Div(style={'display': 'grid', 'gridTemplateColumns': '1fr 1fr', 'gap': '20px', 'marginBottom': '25px'}, children=[
                    html.Div(style={'backgroundColor': '#f8f9fa', 'padding': '15px', 'borderRadius': '6px', 'borderLeft': f'5px solid {color_alert}'}, children=[
                        html.Small("PROMEDIO FINAL DEL CURSO", style={'color': '#7f8c8d', 'fontWeight': 'bold'}),
                        html.H3(f"{nota} pts", style={'margin': '5px 0 0 0', 'color': '#2c3e50'})
                    ]),
                    html.Div(style={'backgroundColor': '#f8f9fa', 'padding': '15px', 'borderRadius': '6px'}, children=[
                        html.Small("SITUACIÓN DE AVANCE", style={'color': '#7f8c8d', 'fontWeight': 'bold'}),
                        html.H4(estatus, style={'margin': '5px 0 0 0', 'color': color_alert})
                    ])
                ]),
                
                # Despliegue de la Recomendación de la IA de OpenAI
                html.H4("💡 Recomendación de Tutoría Inteligente (OpenAI GPT):", style={'color': '#003366', 'marginBottom': '8px'}),
                html.P(
                    recomendacion_ia,
                    style={'color': '#2c3e50', 'lineHeight': '1.6', 'fontSize': '15px', 'backgroundColor': '#eef2f7', 'padding': '15px', 'borderRadius': '6px', 'fontStyle': 'italic'}
                )
            ]),
            
            html.Div(style={'borderLeft': '1px solid #eee', 'paddingLeft': '20px'}, children=[
                dcc.Graph(figure=fig_pastel_individual, config={'displayModeBar': False})
            ])
        ])
    ])

# ----------------------------------------------------------------------------
# REGLAS DE CALLBACKS
# ----------------------------------------------------------------------------
@app.callback(
    Output('page-content', 'children'),
    Input('url', 'pathname')
)
def controlar_rutas(pathname):
    if not pathname or pathname == '/':
        return render_pagina_general()
    elif pathname.startswith('/alumno/'):
        nombre_alumno = urllib.parse.unquote(pathname.split('/alumno/')[1])
        return render_pagina_individual(nombre_alumno)
    else:
        return html.Div("404 - Página no encontrada")

@app.callback(
    [Output('grafico-pastel-general', 'figure'),
     Output('grafico-barras-general', 'figure'),
     Output('tabla-alumnos-container', 'children')],
    Input('grupo-dropdown', 'value')
)
def actualizar_panel_general(grupo_seleccionado):
    df = obtener_datos_procesados()
    if df.empty:
        return {}, {}, ""
        
    if grupo_seleccionado != 'TODOS':
        df = df[df['grupo'] == grupo_seleccionado]
        
    df['rango'] = pd.cut(df['nota_final'], bins=[-1, 5.9, 7.9, 8.9, 10], labels=['Menor a 6 (Reprobado)', '7 - 7.9 (Regular)', '8 - 8.9 (Bueno)', '9 - 10 (Excelente)'])
    conteos = df['rango'].value_counts().reset_index()
    conteos.columns = ['Estatus', 'Cantidad']
    
    fig_pastel = px.pie(conteos, names='Estatus', values='Cantidad', title='Distribución General de Calificaciones', hole=0.4,
                        color_discrete_sequence=['#e74c3c', '#f39c12', '#3498db', '#2ecc71'])
    
    fig_barras = px.bar(df, x='alumno', y='nota_final', color='nota_final', title='Rendimiento de Calificaciones por Estudiante',
                        labels={'nota_final': 'Puntuación', 'alumno': 'Estudiante'},
                        color_continuous_scale=px.colors.sequential.Viridis)
    fig_barras.update_layout(xaxis_tickangle=-45, margin=dict(b=120))
    
    elementos_lista = []
    for _, fila in df.iterrows():
        nombre_completo = fila['alumno']
        elementos_lista.append(
            html.Div(style={'padding': '12px 15px', 'borderBottom': '1px solid #eee', 'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center'}, children=[
                dcc.Link(nombre_completo, href=f"/alumno/{urllib.parse.quote(nombre_completo)}", 
                         style={'textDecoration': 'none', 'color': '#0056b3', 'fontWeight': '500', 'fontSize': '15px'}),
                html.Span(f"{fila['nota_final']} pts", style={'backgroundColor': '#e9ecef', 'padding': '4px 10px', 'borderRadius': '12px', 'fontSize': '13px', 'fontWeight': 'bold'})
            ])
        )
        
    return fig_pastel, fig_barras, html.Div(elementos_lista, style={'maxHeight': '400px', 'overflowY': 'auto', 'border': '1px solid #ddd', 'borderRadius': '6px'})

if __name__ == '__main__':
    server.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
