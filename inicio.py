"""Pantalla de inicio de Analítica UTTEC.

No consulta Moodle ni almacena información: recibe los valores en `datos`.
Las métricas sin información se representan con un guion, nunca con cero.
"""
from dash import dcc, html


TEXTO = 'var(--text-color, #f8fafc)'
SUAVE = 'var(--text-muted, #9caec5)'
TARJETA = 'var(--card-bg, #151e31)'
BORDE = '1px solid var(--border-color, #26334a)'
VERDE = '#008000'


def _valor(datos, clave, sufijo=''):
    valor = datos.get(clave)
    return f'{valor}{sufijo}' if valor is not None and valor != '' else '—'


def _tarjeta(titulo, valor, nota, color=VERDE):
    return html.Div(
        style={
            'backgroundColor': TARJETA, 'border': BORDE, 'borderRadius': '15px',
            'padding': '24px', 'flex': '1 1 195px', 'minWidth': '0'
        },
        children=[
            html.P(titulo, style={
                'color': SUAVE, 'fontSize': '13px', 'fontWeight': '600',
                'margin': '0 0 12px'
            }),
            html.H2(valor, style={
                'color': color, 'fontSize': '32px', 'fontWeight': '800',
                'margin': '0 0 8px'
            }),
            html.P(nota, style={'color': SUAVE, 'fontSize': '12px', 'margin': 0})
        ]
    )


def _bloque(titulo, descripcion, elementos=None):
    return html.Div(
        style={
            'backgroundColor': TARJETA, 'border': BORDE,
            'borderRadius': '15px', 'padding': '26px',
            'flex': '1 1 300px', 'minHeight': '200px',
            'boxSizing': 'border-box'
        },
        children=[
            html.H3(titulo, style={
                'color': TEXTO, 'fontSize': '18px', 'margin': '0 0 20px'
            }),
            (html.Ul([
                html.Li(str(item), style={
                    'color': TEXTO, 'padding': '8px 0', 'fontSize': '14px'
                }) for item in elementos[:5]
            ], style={'margin': 0, 'paddingLeft': '18px'}) if elementos else
             html.Div(style={
                 'padding': '35px 12px',
                 'border': '1px dashed var(--border-color, #34435c)',
                 'borderRadius': '10px', 'textAlign': 'center'
             }, children=[
                 html.P('Sin información disponible', style={
                     'color': SUAVE, 'fontWeight': '600', 'margin': '0 0 8px'
                 }),
                 html.P(descripcion, style={
                     'color': SUAVE, 'fontSize': '13px', 'margin': 0
                 })
             ]))
        ]
    )


def render_inicio(datos=None):
    """Pinta la portada. En el futuro puede recibir un diccionario de Moodle.

    Claves esperadas: estudiantes, cursos, promedio, riesgo,
    ultima_sincronizacion, estado_sincronizacion, lista_cursos, avisos.
    """
    datos = datos or {}
    tiene_datos = any(datos.get(k) is not None for k in
                      ('estudiantes', 'cursos', 'promedio', 'riesgo'))

    return html.Div(id='vista-inicio', children=[
        html.Div(style={
            'background': 'linear-gradient(115deg, #00194d 0%, #053269 100%)',
            'border': '1px solid rgba(0,128,0,.35)', 'borderRadius': '18px',
            'padding': '32px', 'marginBottom': '26px'
        }, children=[
            html.P('PLATAFORMA VIRTUAL UTTEC', style={
                'color': '#4ade80', 'fontSize': '12px', 'fontWeight': '700',
                'letterSpacing': '2px', 'margin': '0 0 12px'
            }),
            html.H1('Bienvenido al panel de inicio', style={
                'color': '#fff', 'fontSize': '30px', 'margin': '0 0 12px'
            }),
            html.P('Consulta el resumen académico y accede a las herramientas de analítica.',
                   style={'color': '#cbd5e1', 'fontSize': '15px', 'margin': '0 0 24px'}),
            dcc.Link('Ir a Analítica  →', href='/', style={
                'display': 'inline-block', 'backgroundColor': VERDE,
                'color': 'white', 'fontWeight': '700', 'padding': '12px 20px',
                'borderRadius': '9px', 'textDecoration': 'none'
            })
        ]),

        html.Div(style={
            'display': 'flex', 'alignItems': 'center', 'justifyContent': 'space-between',
            'gap': '12px', 'flexWrap': 'wrap', 'marginBottom': '18px'
        }, children=[
            html.H2('Resumen institucional', style={
                'color': TEXTO, 'fontSize': '22px', 'margin': 0
            }),
            html.Span('Datos disponibles' if tiene_datos else 'Pendiente de sincronización',
                      style={
                          'color': '#4ade80' if tiene_datos else SUAVE,
                          'border': BORDE, 'borderRadius': '20px',
                          'fontSize': '12px', 'padding': '7px 12px'
                      })
        ]),
        html.Div(style={
            'display': 'flex', 'flexWrap': 'wrap', 'gap': '16px', 'marginBottom': '26px'
        }, children=[
            _tarjeta('Estudiantes inscritos', _valor(datos, 'estudiantes'), 'Total de alumnos registrados'),
            _tarjeta('Cursos disponibles', _valor(datos, 'cursos'), 'Cursos registrados en Moodle'),
            _tarjeta('Promedio general', _valor(datos, 'promedio'), 'Escala institucional de 0 a 10'),
            _tarjeta('Alumnos en riesgo', _valor(datos, 'riesgo'), 'Pendientes de seguimiento', '#ff6b6b')
        ]),

        html.Div(style={
            'backgroundColor': TARJETA, 'border': BORDE, 'borderRadius': '15px',
            'padding': '22px', 'marginBottom': '26px', 'display': 'flex',
            'flexWrap': 'wrap', 'justifyContent': 'space-between', 'gap': '16px'
        }, children=[
            html.Div(children=[
                html.H3('Estado de los datos académicos', style={
                    'color': TEXTO, 'fontSize': '17px', 'margin': '0 0 8px'
                }),
                html.P(_valor(datos, 'estado_sincronizacion') if datos.get('estado_sincronizacion')
                       else 'Esperando información de Moodle',
                       style={'color': SUAVE, 'margin': 0})
            ]),
            html.Div(children=[
                html.P('Última sincronización', style={
                    'color': SUAVE, 'fontSize': '12px', 'margin': '0 0 6px'
                }),
                html.Strong(_valor(datos, 'ultima_sincronizacion'), style={'color': TEXTO})
            ])
        ]),

        html.Div(style={'display': 'flex', 'gap': '20px', 'flexWrap': 'wrap'}, children=[
            _bloque('Cursos y grupos', 'Aquí aparecerán los cursos cuando estén conectados.',
                    datos.get('lista_cursos')),
            _bloque('Avisos y actividad reciente', 'Aquí aparecerán novedades institucionales.',
                    datos.get('avisos'))
        ])
    ])
