"""Interfaz visual de Participantes para Analítica UTTEC.

No consulta Moodle ni guarda datos en el navegador.
La función render_participantes(datos) admite información autorizada en el futuro.
Mientras no se conecten datos, muestra indicadores vacíos y controles deshabilitados.
"""

from dash import dash_table, dcc, html

VERDE = "#008000"
TEXTO = "var(--text-color, #f8fafc)"
SECUNDARIO = "var(--text-muted, #9caec5)"
TARJETA = "var(--card-bg, #151e31)"
BORDE = "1px solid var(--border-color, #26334a)"


def _numero(datos, clave):
    valor = datos.get(clave)
    return str(valor) if valor is not None and valor != "" else "—"


def _tarjeta(titulo, dato, subtitulo, color=VERDE):
    return html.Div(
        style={
            "backgroundColor": TARJETA,
            "border": BORDE,
            "borderRadius": "15px",
            "padding": "24px",
            "flex": "1 1 190px",
            "minWidth": "0",
        },
        children=[
            html.P(titulo, style={
                "color": SECUNDARIO, "fontWeight": "600",
                "fontSize": "13px", "margin": "0 0 12px",
            }),
            html.H2(dato, style={
                "color": color, "fontWeight": "800",
                "fontSize": "32px", "margin": "0 0 8px",
            }),
            html.P(subtitulo, style={
                "color": SECUNDARIO, "fontSize": "12px", "margin": "0",
            }),
        ],
    )


def _selector(etiqueta, identificador, pista, opciones=None):
    # Los filtros se habilitarán al conectar callbacks con los datos de Moodle.
    return html.Div(
        style={"flex": "1 1 195px", "minWidth": "0"},
        children=[
            html.Label(etiqueta, htmlFor=identificador, style={
                "display": "block", "textTransform": "uppercase",
                "fontSize": "11px", "fontWeight": "700",
                "letterSpacing": "0.8px", "marginBottom": "9px",
                "color": SECUNDARIO,
            }),
            dcc.Dropdown(
                id=identificador,
                options=opciones or [],
                value=None,
                placeholder=pista,
                disabled=True,
                clearable=True,
                className="custom-dropdown",
            ),
        ],
    )


def _panel_pendiente(titulo, descripcion):
    return html.Div(
        style={
            "flex": "1 1 320px", "minWidth": "0",
            "padding": "25px", "minHeight": "215px",
            "border": BORDE, "borderRadius": "15px",
            "backgroundColor": TARJETA,
            "boxSizing": "border-box",
        },
        children=[
            html.H3(titulo, style={
                "color": TEXTO, "fontSize": "18px", "margin": "0 0 18px",
            }),
            html.Div(style={
                "border": "1px dashed var(--border-color, #26334a)",
                "borderRadius": "10px", "padding": "28px 16px",
                "textAlign": "center",
            }, children=[
                html.P("Sin información disponible", style={
                    "fontSize": "14px", "fontWeight": "700",
                    "color": TEXTO, "margin": "0 0 8px",
                }),
                html.P(descripcion, style={
                    "color": SECUNDARIO, "fontSize": "13px", "margin": "0",
                }),
            ]),
        ],
    )


def render_participantes(datos=None):
    """Construye la vista de Participantes.

    Opcionalmente acepta un diccionario con las claves:
        total_estudiantes, total_grupos, total_cursos, en_riesgo,
        ultima_sincronizacion, registros

    Cada registro puede tener:
        nombre_alumno, carrera, curso, grupo, estado

    No se muestra información real hasta que app.py la proporcione
    mediante una integración autorizada.
    """
    datos = datos if isinstance(datos, dict) else {}
    registros_recibidos = datos.get("registros") or []
    registros = []
    if isinstance(registros_recibidos, list):
        campos = ("nombre_alumno", "carrera", "curso", "grupo", "estado")
        registros = [
            {campo: fila.get(campo, "") for campo in campos}
            for fila in registros_recibidos if isinstance(fila, dict)
        ]

    columnas = [
        {"name": "Nombre del estudiante", "id": "nombre_alumno"},
        {"name": "División / Carrera", "id": "carrera"},
        {"name": "Curso", "id": "curso"},
        {"name": "Grupo académico", "id": "grupo"},
        {"name": "Estado", "id": "estado"},
    ]

    return html.Div(id="vista-participantes", children=[
        # Encabezado de la sección
        html.Div(style={
            "display": "flex", "justifyContent": "space-between",
            "alignItems": "center", "flexWrap": "wrap", "gap": "16px",
            "borderBottom": BORDE, "paddingBottom": "23px",
            "marginBottom": "28px",
        }, children=[
            html.Div(children=[
                html.P("GESTIÓN ACADÉMICA", style={
                    "fontSize": "12px", "fontWeight": "800", "color": VERDE,
                    "letterSpacing": "1.6px", "margin": "0 0 8px",
                }),
                html.H1("Participantes", style={
                    "fontSize": "30px", "fontWeight": "800",
                    "color": TEXTO, "margin": "0 0 8px",
                }),
                html.P(
                    "Consulta participantes, grupos y seguimiento académico de Virtual UTTEC.",
                    style={"color": SECUNDARIO, "fontSize": "14px", "margin": 0},
                ),
            ]),
            html.Div(style={
                "border": BORDE, "borderRadius": "12px",
                "backgroundColor": TARJETA, "padding": "13px 16px",
            }, children=[
                html.Span("● ", style={"color": VERDE}),
                html.Span("Pendiente de sincronización", style={
                    "color": SECUNDARIO, "fontSize": "12px",
                    "fontWeight": "600",
                }),
            ]),
        ]),

        # Estadísticas: vacías por defecto
        html.Div(style={
            "display": "flex", "flexWrap": "wrap", "gap": "17px",
            "marginBottom": "26px",
        }, children=[
            _tarjeta("Estudiantes registrados", _numero(datos, "total_estudiantes"),
                     "Participantes disponibles"),
            _tarjeta("Grupos académicos", _numero(datos, "total_grupos"),
                     "Grupos vinculados a cursos"),
            _tarjeta("Cursos con participantes", _numero(datos, "total_cursos"),
                     "Cursos presentes en matrícula"),
            _tarjeta("Estudiantes en riesgo", _numero(datos, "en_riesgo"),
                     "Pendiente de información académica", "#ff6b6b"),
        ]),

        # Filtros: visuales hasta implementar la consulta de datos
        html.Div(style={
            "backgroundColor": TARJETA, "border": BORDE,
            "borderRadius": "15px", "padding": "23px",
            "marginBottom": "24px",
        }, children=[
            html.H3("Buscar participantes", style={
                "color": TEXTO, "fontSize": "18px", "margin": "0 0 18px",
            }),
            html.Div(style={
                "display": "flex", "gap": "16px", "flexWrap": "wrap",
            }, children=[
                _selector("División / Carrera", "participantes-division",
                          "Selecciona una carrera"),
                _selector("Curso Moodle", "participantes-curso",
                          "Selecciona un curso"),
                _selector("Grupo académico", "participantes-grupo",
                          "Selecciona un grupo"),
                html.Div(style={"flex": "1 1 195px", "minWidth": "0"}, children=[
                    html.Label("Buscar estudiante", htmlFor="participantes-buscar",
                        style={
                            "display": "block", "color": SECUNDARIO,
                            "fontSize": "11px", "fontWeight": "700",
                            "letterSpacing": "0.8px", "textTransform": "uppercase",
                            "marginBottom": "9px",
                        }),
                    dcc.Input(
                        id="participantes-buscar", type="text",
                        placeholder="Nombre del estudiante...", disabled=True,
                        style={
                            "width": "100%", "height": "43px",
                            "boxSizing": "border-box", "padding": "0 12px",
                            "borderRadius": "8px", "border": BORDE,
                            "backgroundColor": "var(--dropdown-bg)",
                            "color": TEXTO, "fontSize": "13px",
                        },
                    ),
                ]),
            ]),
            html.P(
                "Los filtros se habilitarán cuando esta vista reciba datos autorizados de Moodle.",
                style={"color": SECUNDARIO, "fontSize": "12px", "margin": "15px 0 0"},
            ),
        ]),

        # Directorio: sin filas ni nombres inventados
        html.Div(style={
            "backgroundColor": TARJETA, "border": BORDE,
            "borderRadius": "15px", "padding": "25px",
            "marginBottom": "24px",
        }, children=[
            html.Div(style={
                "display": "flex", "justifyContent": "space-between",
                "flexWrap": "wrap", "gap": "10px", "marginBottom": "18px",
            }, children=[
                html.Div(children=[
                    html.H3("Directorio de participantes", style={
                        "color": TEXTO, "fontSize": "18px", "margin": "0 0 6px",
                    }),
                    html.P("Relación de estudiantes y grupos académicos.",
                           style={"color": SECUNDARIO, "fontSize": "13px", "margin": 0}),
                ]),
                html.Span(
                    f"{len(registros)} registros" if registros else "Sin registros",
                    style={
                        "color": SECUNDARIO, "fontSize": "12px",
                        "border": BORDE, "padding": "9px 13px",
                        "borderRadius": "25px", "alignSelf": "flex-start",
                    },
                ),
            ]),
            dash_table.DataTable(
                id="participantes-tabla",
                columns=columnas,
                data=registros,
                page_size=10,
                sort_action="native" if registros else "none",
                style_as_list_view=True,
                style_table={"overflowX": "auto"},
                style_header={
                    "backgroundColor": "var(--hover-bg)",
                    "color": TEXTO, "fontWeight": "700",
                    "textAlign": "left", "padding": "15px",
                    "fontSize": "12px", "border": "none",
                },
                style_cell={
                    "backgroundColor": TARJETA, "color": TEXTO,
                    "textAlign": "left", "padding": "14px",
                    "fontSize": "13px", "border": "none",
                    "minWidth": "130px", "whiteSpace": "normal",
                    "height": "auto", "fontFamily": "Outfit, sans-serif",
                },
            ),
            html.Div(style={
                "padding": "33px 15px", "textAlign": "center",
                "borderTop": BORDE,
            }, children=[
                html.H4("Sin participantes para mostrar", style={
                    "color": TEXTO, "fontSize": "15px", "margin": "0 0 8px",
                }),
                html.P("Los registros aparecerán cuando se conecte la información de Moodle.",
                       style={"color": SECUNDARIO, "fontSize": "13px", "margin": 0}),
            ]) if not registros else html.Div(),
        ]),

        html.Div(style={
            "display": "flex", "flexWrap": "wrap", "gap": "20px",
        }, children=[
            _panel_pendiente("Distribución por grupos",
                             "Aquí aparecerá el resumen de estudiantes por grupo."),
            _panel_pendiente("Seguimiento de participantes",
                             "Aquí se mostrarán avisos y estados de seguimiento autorizados."),
        ]),

        html.P(
            "Última sincronización: " + _numero(datos, "ultima_sincronizacion"),
            style={"color": SECUNDARIO, "fontSize": "12px", "marginTop": "26px"},
        ),
    ])
