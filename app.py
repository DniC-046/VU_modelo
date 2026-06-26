from flask import Flask, jsonify
import pandas as pd
import os
from dash import Dash, dcc, html
import plotly.express as px

server = Flask(__name__)

def obtener_datos_procesados():
    ruta_archivo = 'datos.ods'
    if not os.path.exists(ruta_archivo):
        return []
    
    df = pd.read_excel(ruta_archivo, engine='odf')
    df = df.dropna(subset=[df.columns[0]]) 
    
    resultados = []
    for index, fila in df.iterrows():
        alumno_nombre = str(fila.get(df.columns[0], f"Alumno_{index}"))
        nota_final = fila.get('Total del curso', 0)
        try:
            nota_final = float(nota_final)
        except:
            nota_final = 0.0
            
        puntos_riesgo = 0
        tareas_not_entregadas = 0
        
        if nota_final < 60.0:
            puntos_riesgo += 4
            
        for col in df.columns:
            if 'Tarea' in col or 'Cuestionario' in col:
                if pd.isna(fila[col]) or fila[col] == '-' or fila[col] == 0:
                    tareas_not_entregadas += 1
                    
        if tareas_not_entregadas > 2:
            puntos_riesgo += 3
            
        if puntos_riesgo >= 7:
            estatus = "Riesgo Alto"
        elif puntos_riesgo >= 4:
            estatus = "Riesgo Medio"
        else:
            estatus = "Regular / Sin Riesgo"
            
        resultados.append({
            "alumno": alumno_nombre,
            "nota_final": nota_final,
            "tareas_faltantes": tareas_not_entregadas,
            "nivel_de_riesgo": estatus
        })
    return resultados

@server.route('/analisis')
def analizar_datos():
    datos = obtener_datos_procesados()
    return jsonify({
        "curso": "Propedéutico DTIC",
        "total_alumnos_analizados": len(datos),
        "alumnos": datos
    })

app_dash = Dash(__name__, server=server, url_base_pathname='/')

datos_alumnos = obtener_datos_procesados()
df_dashboard = pd.DataFrame(datos_alumnos)

if not df_dashboard.empty:
    fig_pastel = px.pie(
        df_dashboard, 
        names='nivel_de_riesgo', 
        title='Distribución de Alumnos por Nivel de Riesgo',
        color='nivel_de_riesgo',
        color_discrete_map={'Riesgo Alto': '#e74c3c', 'Riesgo Medio': '#f39c12', 'Regular / Sin Riesgo': '#2ecc71'}
    )
    
    fig_barras = px.bar(
        df_dashboard, 
        x='alumno', 
        y='nota_final', 
        color='nivel_de_riesgo',
        title='Calificaciones Finales Estimadas del Propedéutico DTIC',
        labels={'nota_final': 'Calificación', 'alumno': 'Estudiante'},
        color_discrete_map={'Riesgo Alto': '#e74c3c', 'Riesgo Medio': '#f39c12', 'Regular / Sin Riesgo': '#2ecc71'}
    )
else:
    fig_pastel = px.scatter(title="Sin datos disponibles")
    fig_barras = px.scatter(title="Sin datos disponibles")

app_dash.layout = html.Div(style={'fontFamily': 'Arial, sans-serif', 'padding': '20px', 'backgroundColor': '#f8f9fa'}, children=[
    
    html.Div(style={'textAlign': 'center', 'marginBottom': '30px', 'padding': '10px', 'backgroundColor': '#003366', 'color': 'white', 'borderRadius': '5px'}, children=[
        html.H1("Dashboard de Analítica de Datos - Virtual UTTEC"),
        html.H3("Curso Propedéutico DTIC - Monitoreo de Alumnos en Riesgo")
    ]),
    
    html.Div(style={'display': 'flex', 'flexDirection': 'row', 'flexWrap': 'wrap', 'justifyContent': 'space-around'}, children=[
        
        html.Div(style={'width': '45%', 'minWidth': '400px', 'backgroundColor': 'white', 'padding': '15px', 'borderRadius': '8px', 'boxShadow': '0px 4px 6px rgba(0,0,0,0.1)'}, children=[
            dcc.Graph(figure=fig_pastel)
        ]),
        
        html.Div(style={'width': '45%', 'minWidth': '400px', 'backgroundColor': 'white', 'padding': '15px', 'borderRadius': '8px', 'boxShadow': '0px 4px 6px rgba(0,0,0,0.1)'}, children=[
            dcc.Graph(figure=fig_barras)
        ])
    ]),
    
    html.Div(style={'textAlign': 'center', 'marginTop': '40px', 'color': '#7f8c8d'}, children=[
        html.P(".")
    ])
])

if __name__ == '__main__':
    server.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
