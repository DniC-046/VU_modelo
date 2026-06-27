from flask import Flask
import pandas as pd
import os
import urllib.parse
from dash import Dash, dcc, html, Input, Output
import plotly.express as px

server = Flask(__name__)

def obtener_datos_procesados():
    ruta_archivo = 'datos.ods'
    if not os.path.exists(ruta_archivo):
        return pd.DataFrame()
    
    df = pd.read_excel(ruta_archivo, engine='odf')
    
    df.columns = [str(c).strip() for c in df.columns]
    
    if 'nombre' in df.columns and 'apellido' in df.columns:
        df['alumno'] = (df['nombre'].astype(str) + ' ' + df['apellido'].astype(str)).str.strip().str.upper()
    else:
        df['alumno'] = df[df.columns[0]].astype(str).str.strip().str.upper()
    
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
        df['grupo'] = df[columnas_grupo[0]].fillna('Sin Grupo').astype(str).str.upper()
    else:
        df['grupo'] = 'GRUPO ÚNICO'
        
    return df

app = Dash(__name__, server=server, url_base_pathname='/', suppress_callback_exceptions=True)
application = app.server

app.layout = html.Div([
    dcc.Location(id='url', refresh=False), 
    html.Div(id='page-content')           
])

def render_pagina_general():
    df = obtener_datos_procesados()
    if df.empty:
        return html.Div("Error: No se encontró el archivo datos.ods en el servidor.")
        
    lista_grupos = sorted(df['grupo'].unique())
    
    return html.Div(style={'fontFamily': 'Segoe UI, Arial', 'padding': '30px', 'backgroundColor': '#f8f9fa'}, children=[
        html.Div(style={'backgroundColor': '#003366', 'color': 'white', 'padding': '25px', 'borderRadius': '10px', 'marginBottom': '25px', 'boxShadow': '0 4px 6px rgba(0,0,0,0.1)'}, children=[
            html.H1("Analítica del curso", style={'margin': '0', 'fontSize': '28px', 'fontWeight': '600'}),
            html.P("Visualiza el desempeño global y selecciona estudiantes para su seguimiento", style={'margin': '5px 0 0 0', 'opacity': '0.9'})
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

def render_pagina_individual(nombre_alumno):
    df = obtener_datos_procesados()
    if df.empty:
        return html.Div("Error en la carga de datos.")
        
    registro = df[df['alumno'] == nombre_alumno]
    if registro.empty:
        return html.Div("Estudiante no encontrado en la base de datos.")
        
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
        
    fig_pastel = px.pie(
        names=['Calificación Obtenida', 'Puntos Restantes'],
        values=[nota, max(10.0 - nota, 0)],
        color_discrete_sequence=[color_alert, '#e2e8f0'],
        hole=0.6,
        title="Distribución de Calificaciones por Tipo"
    )
    fig_pastel.update_layout(showlegend=False, margin=dict(t=40, b=10, l=10, r=10))

    return html.Div(style={'fontFamily': 'Segoe UI, Arial', 'padding': '30px', 'backgroundColor': '#f8f9fa'}, children=[
        dcc.Link("← Volver a la vista general", href="/", style={'textDecoration': 'none', 'color': '#003366', 'fontWeight': 'bold', 'display': 'inline-block', 'marginBottom': '20px'}),
        
        html.Div(style={'backgroundColor': 'white', 'padding': '30px', 'borderRadius': '10px', 'boxShadow': '0 4px 6px rgba(0,0,0,0.05)', 'display': 'grid', 'gridTemplateColumns': '1.2fr 0.8fr', 'gap': '30px'}, children=[
            
            html.Div(children=[
                html.H2(nombre_alumno, style={'color': '#003366', 'margin': '0 0 5px 0', 'fontSize': '28px'}),
                html.P(f"Grupo: {grupo}", style={'color': '#7f8c8d', 'margin': '0 0 25px 0', 'fontSize': '16px'}),
                
                html.Div(style={'display': 'grid', 'gridTemplateColumns': '1fr 1fr', 'gap': '20px', 'marginBottom': '25px'}, children=[
                    html.Div(style={'backgroundColor': '#f8f9fa', 'padding': '15px', 'borderRadius': '6px', 'borderLeft': f'5px solid {color_alert}'}, children=[
                        html.Small("PROMEDIO GENERAL", style={'color': '#7f8c8d', 'fontWeight': 'bold'}),
                        html.H3(f"{nota} pts", style={'margin': '5px 0 0 0', 'color': '#2c3e50'})
                    ]),
                    html.Div(style={'backgroundColor': '#f8f9fa', 'padding': '15px', 'borderRadius': '6px'}, children=[
                        html.Small("SITUACIÓN DE AVANCE", style={'color': '#7f8c8d', 'fontWeight': 'bold'}),
                        html.H4(estatus, style={'margin': '5px 0 0 0', 'color': color_alert})
                    ])
                ]),
                
                html.H4("Recomendación del Modelo Analítico:", style={'color': '#003366', 'marginBottom': '8px'}),
                html.P(
                    "Urgente revisar a alumno en posibilidades de baja." if nota < 6.0 else "Estudiante con avance regular." if nota < 8.5 else "Excelente rendimiento.",
                    style={'color': '#555', 'lineHeight': '1.5', 'fontSize': '15px'}
                )
            ]),
            
            html.Div(style={'borderLeft': '1px solid #eee', 'paddingLeft': '20px'}, children=[
                dcc.Graph(figure=fig_pastel, config={'displayModeBar': False})
            ])
        ])
    ])


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
        
    
    df['rango'] = pd.cut(df['nota_final'], bins=[-1, 5.9, 7.9, 8.9, 10], labels=['Menor a 6', '7 - 7.9', '8 - 8.9', '9 - 10'])
    conteos = df['rango'].value_counts().reset_index()
    conteos.columns = ['Estatus', 'Cantidad']
    
    fig_pastel = px.pie(conteos, names='Estatus', values='Cantidad', title='Distribución de Calificaciones', hole=0.4)
    
    
    fig_barras = px.bar(df, x='alumno', y='nota_final', color='nota_final', title='Calificaciones del Curso',
                        labels={'nota_final': 'Calificación', 'alumno': 'Estudiante'})
    fig_barras.update_layout(xaxis_tickangle=-45)
    
    
    elementos_lista = []
    for _, fila in df.iterrows():
        nombre_completo = fila['alumno']
        elementos_lista.append(
            html.Div(style={'padding': '12px 15px', 'borderBottom': '1px solid #eee', 'display': 'flex', 'justifyContent': 'between', 'alignItems': 'center'}, children=[
                dcc.Link(nombre_completo, href=f"/alumno/{urllib.parse.quote(nombre_completo)}", 
                         style={'textDecoration': 'none', 'color': '#0056b3', 'fontWeight': '500', 'fontSize': '15px'}),
                html.Span(f"{fila['nota_final']} pts", style={'backgroundColor': '#e9ecef', 'padding': '4px 10px', 'borderRadius': '12px', 'fontSize': '13px', 'fontWeight': 'bold'})
            ])
        )
        
    return fig_pastel, fig_barras, html.Div(elementos_lista, style={'maxHeight': '400px', 'overflowY': 'auto', 'border': '1px solid #ddd', 'borderRadius': '6px'})

if __name__ == '__main__':
    server.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
