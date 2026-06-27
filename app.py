from flask import Flask, jsonify
import pandas as pd
import os
from dash import Dash, dcc, html, Input, Output

server = Flask(__name__)

def obtener_datos_procesados():
    ruta_archivo = 'datos.ods'
    if not os.path.exists(ruta_archivo):
        return pd.DataFrame()
    
    df = pd.read_excel(ruta_archivo, engine='odf')
    df = df.dropna(subset=[df.columns[0]]) 
    
    df = df.rename(columns={df.columns[0]: 'alumno'})
    
    if 'Total del curso' in df.columns:
        df['nota_final'] = df['Total del curso']
    elif 'Calificación final' in df.columns:
        df['nota_final'] = df['Calificación final']
    elif 'Course total' in df.columns:
        df['nota_final'] = df['Course total']
    else:
        df['nota_final'] = 0.0

    df['nota_final'] = pd.to_numeric(df['nota_final'], errors='coerce').fillna(0.0)
    
    columnas_grupo = [c for c in df.columns if 'grupo' in c.lower()]
    if columnas_grupo:
        df['grupo'] = df[columnas_grupo[0]].fillna('Sin Grupo').astype(str)
    else:
        df['grupo'] = 'Grupo Único'
        
    return df

@server.route('/analisis')
def analizar_datos():
    df = obtener_datos_procesados()
    if df.empty:
        return jsonify({"error": "No hay datos"})
    return jsonify({
        "curso": "Propedéutico DTIC",
        "total": len(df),
        "alumnos": df[['alumno', 'nota_final', 'grupo']].to_dict(orient='records')
    })

app = Dash(__name__, server=server, url_base_pathname='/')
application = app.server

df_inicial = obtener_datos_procesados()
lista_grupos = sorted(df_inicial['grupo'].unique()) if not df_inicial.empty else ['Todos']
lista_alumnos = sorted(df_inicial['alumno'].unique()) if not df_inicial.empty else []

app.layout = html.Div(style={'fontFamily': 'Arial, sans-serif', 'padding': '25px', 'backgroundColor': '#f4f6f9'}, children=[
    
    html.Div(style={'backgroundColor': '#003366', 'color': 'white', 'padding': '20px', 'borderRadius': '8px', 'marginBottom': '20px'}, children=[
        html.H1("Analítica del Curso - Plataforma Virtual UTTEC", style={'margin': '0', 'fontSize': '26px'}),
        html.P("Visualiza el desempeño, filtra por grupos y genera análisis por estudiante", style={'margin': '5px 0 0 0', 'opacity': '0.8'})
    ]),
    
    html.Div(style={'display': 'flex', 'gap': '20px', 'backgroundColor': 'white', 'padding': '20px', 'borderRadius': '8px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.05)', 'marginBottom': '25px'}, children=[
        
        html.Div(style={'flex': '1'}, children=[
            html.Label("1. Filtrar por Grupo:", style={'fontWeight': 'bold', 'color': '#333'}),
            dcc.Dropdown(
                id='filtro-grupo',
                options=[{'label': g, 'value': g} for g in lista_grupos] + [{'label': 'Ver Todos los Grupos', 'value': 'TODOS'}],
                value='TODOS',
                clearable=False,
                style={'marginTop': '5px'}
            )
        ]),
        
        html.Div(style={'flex': '1'}, children=[
            html.Label("2. Seleccionar Estudiante para Análisis Individual:", style={'fontWeight': 'bold', 'color': '#333'}),
            dcc.Dropdown(
                id='filtro-alumno',
                options=[{'label': a, 'value': a} for a in lista_alumnos],
                placeholder="Selecciona un alumno...",
                style={'marginTop': '5px'}
            )
        ])
        
    ]),
    
    html.Div(style={'display': 'flex', 'flexDirection': 'column', 'gap': '25px'}, children=[
        
        html.Div(style={'backgroundColor': 'white', 'padding': '20px', 'borderRadius': '8px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.05)'}, children=[
            dcc.Graph(id='grafico-calificaciones', config={'displayModeBar': False})
        ]),
        
        html.Div(id='reporte-individual', style={'backgroundColor': 'white', 'padding': '25px', 'borderRadius': '8px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.05)'})
        
    ])
])

@app.callback(
    Output('grafico-calificaciones', 'figure'),
    Input('filtro-grupo', 'value')
)
def actualizar_grafico(grupo_seleccionado):
    df = obtener_datos_procesados()
    if df.empty:
        return {}
    
    if grupo_seleccionado != 'TODOS':
        df = df[df['grupo'] == grupo_seleccionado]
        
    import plotly.express as px
    fig = px.bar(
        df, 
        x='alumno', 
        y='nota_final', 
        color='nota_final',
        title=f'Calificaciones del Curso ({grupo_seleccionado})',
        labels={'nota_final': 'Calificación Final', 'alumno': 'Nombre Completo del Estudiante'},
        color_continuous_scale=px.colors.sequential.Viridis
    )
    fig.update_layout(xaxis_tickangle=-45, margin=dict(b=100))
    return fig

@app.callback(
    Output('reporte-individual', 'children'),
    Input('filtro-alumno', 'value')
)
def generar_analisis_individual(alumno_seleccionado):
    if not alumno_seleccionado:
        return html.Div(style={'textAlign': 'center', 'color': '#7f8c8d'}, children=[
            html.H4("Por favor, selecciona un estudiante en el menú de arriba para desplegar su reporte detallado.")
        ])
        
    df = obtener_datos_procesados()
    datos_alumno = df[df['alumno'] == alumno_seleccionado].iloc[0]
    
    nota = datos_alumno['nota_final']
    grupo = datos_alumno['grupo']
    
    if nota >= 8.5:
        estatus = "Excelente / Destacado"
        color_alerta = "#2ecc71"
        recomendacion = "Excelente."
    elif nota >= 6.0:
        estatus = "Regular / Aprobado"
        color_alerta = "#f39c12"
        recomendacion = "Aprobado, pero se debe cuidar"
    else:
        estatus = "Alerta: Riesgo de Reprobación"
        color_alerta = "#e74c3c"
        recomendacion = "Urgente, necesita apoyo."

    
    return html.Div(children=[
        html.H3(f" Ficha  Individual: {alumno_seleccionado}", style={'color': '#003366', 'borderBottom': '2px solid #003366', 'paddingBottom': '10px'}),
        
        html.Div(style={'display': 'flex', 'gap': '20px', 'marginTop': '20px'}, children=[
            
            html.Div(style={'flex': '1', 'backgroundColor': '#f8f9fa', 'padding': '15px', 'borderRadius': '6px', 'borderLeft': f'5px solid {color_alerta}'}, children=[
                html.P(html.Strong("Grupo Perteneciente:"), style={'margin': '0 0 5px 0'}),
                html.H4(grupo, style={'margin': '0', 'color': '#333'}),
                
                html.P(html.Strong("Calificación Registrada:"), style={'margin': '15px 0 5px 0'}),
                html.H4(f"{nota} pts", style={'margin': '0', 'color': '#333'}),
            ]),
            
            html.Div(style={'flex': '2', 'backgroundColor': '#f8f9fa', 'padding': '15px', 'borderRadius': '6px'}, children=[
                html.P(html.Strong("Situación de Avance:"), style={'margin': '0 0 5px 0'}),
                html.Span(estatus, style={'backgroundColor': color_alerta, 'color': 'white', 'padding': '5px 12px', 'borderRadius': '15px', 'fontWeight': 'bold', 'fontSize': '14px'}),
                
                html.P(html.Strong("Acción / Recomendación sugerida por el Modelo:"), style={'margin': '15px 0 5px 0'}),
                html.P(recomendacion, style={'margin': '0', 'color': '#555', 'fontSize': '15px', 'lineHeight': '1.4'})
            ])
            
        ])
    ])

if __name__ == '__main__':
    server.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
