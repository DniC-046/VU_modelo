import os
import requests
import pandas as pd
import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output, State
import plotly.express as px
from flask_caching import Cache
import urllib.parse
from openai import OpenAI
import json
import dotenv
import threading
import logging
import secrets
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from html import unescape
from flask import session as flask_session, has_request_context, request
import time
import re
try:
    # Si existe el modulo original, conservar sus funciones visuales.
    from participantes import render_participantes as _render_participantes_original
except ImportError:
    _render_participantes_original = None
# Todas las consultas institucionales estan integradas en este app.py.


#cargar variables de entorno 
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.isfile(dotenv_path):
    dotenv.load_dotenv(dotenv_path)
else:
    dotenv.load_dotenv()

import base64

# Constante 
COLOR_VERDE_BANDERA = "#008000"

def get_svg_icon(name, color=COLOR_VERDE_BANDERA):
    paths = {
        'home': '<path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/>',
        'curso': '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>',
        'users': '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
        'calificaciones': '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/>',
        'chart': '<line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/>',
        'activities': '<polyline points="9 11 12 14 22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/>',
        'resources': '<path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>',
        'forums': '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>',
        'messages': '<path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/>',
        'settings': '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>',
        'sun': '<circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>',
        'moon': '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>',
        'logout': '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/>'
    }
    
    inner = paths.get(name, '')
    svg_string = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{inner}</svg>'
    encoded = base64.b64encode(svg_string.encode()).decode()
    
    return html.Img(
        src=f"data:image/svg+xml;base64,{encoded}",
        style={
            "width": "18px",
            "height": "18px",
            "marginRight": "12px",
            "display": "inline-block",
            "verticalAlign": "middle"
        }
    )

#inicialización de la aplicación
app = dash.Dash(
    __name__, 
    title="Analítica UTTEC - Institucional", 
    suppress_callback_exceptions=True,
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
    external_stylesheets=[
        'https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&display=swap'
    ]
)
app.scripts.config.serve_locally = True
app.css.config.serve_locally = True
server = app.server
server.secret_key = os.environ.get('APP_SESSION_SECRET') or secrets.token_hex(32)
server.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax',
                     SESSION_COOKIE_SECURE=os.environ.get('RENDER', '').lower() == 'true')
if not os.environ.get('APP_SESSION_SECRET'):
    print('ADVERTENCIA: configura APP_SESSION_SECRET en Render para mantener las sesiones estables.')
application = server  

# Estilos y animaciones incluidos directamente en este archivo.
UTTEC_CSS_INTEGRADO = r'''
/* Mejoras visuales integradas: paleta UTTEC azul + verde, sin assets externos */
*{box-sizing:border-box}
body{margin:0;font-family:'Outfit',system-ui,sans-serif}
#main-container{min-height:100vh;--bg-color:#0b1327;--card-bg:#14223a;--dropdown-bg:#172844;--hover-bg:#203457;--border-color:#2d4263;--text-color:#f6f9ff;--text-muted:#a9bed8;--accent-color:#18d593;--shadow-color:rgba(0,0,0,.22);background:var(--bg-color);color:var(--text-color)}
#main-container.light-theme{--bg-color:#f2f7fd;--card-bg:#ffffff;--dropdown-bg:#f5f9ff;--hover-bg:#e8f4ff;--border-color:#d7e3f0;--text-color:#11243d;--text-muted:#586e86;--accent-color:#008650;--shadow-color:rgba(4,30,72,.12)}
#page-content{transition:background .25s,color .25s}
.sidebar-link{display:flex;align-items:center;gap:3px;padding:11px 15px;border-radius:12px;margin:2px 0;color:white;text-decoration:none;transition:background .2s ease,transform .2s ease,box-shadow .2s ease;cursor:pointer}
.sidebar-link:hover{background:rgba(0,209,139,.17)!important;transform:translateX(4px)}
.sidebar-link-active{display:flex;align-items:center;gap:3px;padding:11px 15px;border-radius:12px;margin:2px 0;background:linear-gradient(95deg,rgba(0,193,120,.37),rgba(30,112,210,.19));box-shadow:inset 3px 0 #32e5a9;color:white}
.sidebar-link-active img{filter:drop-shadow(0 0 6px rgba(36,229,151,.4))}
#sidebar-container{background:#000b52!important;overflow-y:auto!important}
.metric-card,.ut-card,.ut-kpi{transition:transform .25s ease,border-color .25s ease,box-shadow .25s ease}
.metric-card:hover,.ut-card:hover,.ut-kpi:hover{transform:translateY(-3px);box-shadow:0 12px 34px rgba(0,147,126,.11);border-color:rgba(38,218,162,.5)!important}
.ut-page{width:100%;max-width:1500px;margin:auto;padding-bottom:40px;animation:utPageEnter .38s ease both}
.ut-hero{position:relative;isolation:isolate;min-height:190px;display:flex;align-items:center;justify-content:space-between;overflow:hidden;background:linear-gradient(112deg,#001550 0%,#063966 60%,#067650 132%);border:1px solid rgba(49,226,166,.34);border-radius:22px;padding:30px 35px;margin-bottom:20px;box-shadow:0 16px 40px rgba(3,19,68,.2)}
.ut-hero:before{content:'';position:absolute;inset:0;background:radial-gradient(circle at 85% 32%,rgba(29,225,163,.16),transparent 42%);pointer-events:none}
.ut-hero-orb{position:absolute;width:270px;height:270px;border:1px solid rgba(97,236,202,.24);border-radius:50%;right:-65px;top:-95px;box-shadow:0 0 0 35px rgba(62,196,205,.045),0 0 0 85px rgba(62,196,205,.03);animation:utOrb 7s ease-in-out infinite alternate}
.ut-hero-title{color:#fff;font-size:clamp(28px,3vw,38px);font-weight:800;margin:12px 0 10px;letter-spacing:-.5px}
.ut-hero-desc{color:#d7e9fa;line-height:1.6;margin:0;max-width:680px;font-size:14px}
.ut-eyebrow{display:flex;align-items:center;color:#45e9af;font-size:11px;letter-spacing:1.8px;font-weight:800}
.ut-eyebrow img{width:18px;height:18px}
.ut-hero-icon{flex-shrink:0;display:flex;align-items:center;justify-content:center;background:rgba(22,219,152,.14);width:98px;height:98px;border:1px solid rgba(85,233,195,.35);border-radius:28px;transform:rotate(-8deg)}
.ut-hero-icon img{width:53px!important;height:53px!important;margin:0!important}
.ut-notice{display:flex;align-items:flex-start;gap:7px;padding:14px 18px;border:1px solid rgba(32,211,155,.22);border-radius:13px;background:rgba(4,155,115,.075);color:var(--text-muted);font-size:13px;line-height:1.6;margin-bottom:20px}
.ut-notice img{margin-top:2px;flex-shrink:0}
.ut-card{background:var(--card-bg);border:1px solid var(--border-color);border-radius:18px;padding:24px;margin-bottom:20px;box-shadow:0 4px 17px var(--shadow-color)}
.ut-card-head{margin-bottom:20px}.ut-card-title{color:var(--text-color);font-size:19px;font-weight:750;margin:0 0 6px}.ut-card-subtitle{color:var(--text-muted);font-size:12px;margin:0;line-height:1.5}
.ut-kpi-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:16px;margin:22px 0}
.ut-kpi{min-width:0;background:var(--card-bg);border:1px solid var(--border-color);padding:21px;border-radius:17px;position:relative;overflow:hidden}
.ut-kpi:after{content:'';width:100px;height:100px;border-radius:50%;position:absolute;top:-55px;right:-55px;background:radial-gradient(circle,rgba(27,228,149,.18),transparent 71%)}
.ut-kpi-icon{margin-bottom:8px}.ut-kpi-label{color:var(--text-muted);font-size:13px;font-weight:650;margin:0 0 8px}.ut-kpi-value{font-size:30px;font-weight:850;letter-spacing:-1px;margin:0 0 8px}.ut-kpi-note{font-size:11px;line-height:1.4;color:var(--text-muted);margin:0}
.ut-form-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:18px;margin-bottom:17px}.ut-field{min-width:0;margin-bottom:13px}.ut-label{display:block;color:var(--text-muted);font-size:11px;font-weight:800;text-transform:uppercase;letter-spacing:.65px;margin-bottom:9px}.ut-input,.ut-textarea{width:100%;max-width:100%;font:inherit;font-size:13px;color:var(--text-color);background:var(--dropdown-bg);border:1px solid var(--border-color);padding:12px 14px;border-radius:10px;outline:none;min-height:43px;transition:border-color .2s,box-shadow .2s}.ut-input:focus,.ut-textarea:focus{border-color:#23dca0;box-shadow:0 0 0 3px rgba(35,220,160,.13)}.ut-textarea{min-height:110px;resize:vertical;line-height:1.6}
.ut-form-footer,.ut-inline-action{display:flex;align-items:center;flex-wrap:wrap;gap:13px;margin-top:17px}.ut-inline-action{border-top:1px solid var(--border-color);padding-top:21px;margin-top:20px}.ut-feedback{font-size:12px;color:#28d89c}.ut-btn{border:1px solid transparent;border-radius:10px;background:linear-gradient(100deg,#008d5b,#03bb85);color:#fff;font-family:inherit;font-size:13px;letter-spacing:.15px;font-weight:750;padding:12px 20px;cursor:pointer;transition:transform .2s,filter .2s,box-shadow .2s;box-shadow:0 6px 16px rgba(0,151,97,.17)}.ut-btn:hover{transform:translateY(-2px);filter:brightness(1.12);box-shadow:0 10px 22px rgba(0,151,97,.26)}.ut-btn:active{transform:translateY(0)}.ut-btn-outline{background:transparent;color:#29dda0;border-color:#1fc793;box-shadow:none}
.ut-empty{text-align:center;border:1px dashed var(--border-color);background:rgba(18,147,136,.045);padding:40px 24px;margin:8px 0 15px;border-radius:15px;color:var(--text-muted)}.ut-empty>img{width:31px!important;height:31px!important;margin:0!important}
.ut-list-row{display:flex;align-items:center;gap:13px;padding:17px 13px;border-bottom:1px solid var(--border-color);animation:utItemEnter .25s ease both;min-width:0}.ut-list-row:last-child{border-bottom:0}.ut-row-icon{height:39px;width:39px;display:flex;align-items:center;justify-content:center;border-radius:12px;background:rgba(36,215,153,.11);flex-shrink:0}.ut-row-icon img{margin:0!important}.ut-row-title{color:var(--text-color);font-size:14px;line-height:1.45;margin:0 0 5px;overflow-wrap:anywhere}.ut-row-meta{color:var(--text-muted);font-size:11px;margin:0;overflow-wrap:anywhere}.ut-pill{flex-shrink:0;border:1px solid var(--border-color);border-radius:999px;padding:5px 9px;font-size:10px;font-weight:800;color:#49d9a7;white-space:nowrap}
.ut-resource-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(215px,1fr));gap:15px}.ut-resource{background:var(--dropdown-bg);border:1px solid var(--border-color);padding:20px;border-radius:14px;transition:transform .2s,border-color .2s;min-width:0}.ut-resource:hover{transform:translateY(-3px);border-color:#25d69b}.ut-resource-top{display:flex;justify-content:space-between;align-items:center;margin-bottom:18px}.ut-resource-url{font-size:11px;white-space:nowrap;text-overflow:ellipsis;overflow:hidden;color:var(--text-muted);margin:9px 0 18px}.ut-text-link{color:#2ce4a5;text-decoration:none;font-size:12px;font-weight:750}.ut-text-link:hover{text-decoration:underline}
.ut-thread{background:var(--dropdown-bg);border:1px solid var(--border-color);border-radius:13px;padding:18px 20px;margin-bottom:13px}.ut-thread-top{display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;gap:8px}.ut-thread-description{font-size:13px;line-height:1.7;color:var(--text-muted);white-space:pre-wrap;overflow-wrap:anywhere}.ut-reply{color:var(--text-color);font-size:12px;background:rgba(11,159,116,.11);padding:11px 13px;border-left:3px solid #29d89a;border-radius:8px;white-space:pre-wrap;overflow-wrap:anywhere}
.ut-preview{color:var(--text-muted);font-size:12px;line-height:1.6;white-space:pre-wrap;overflow-wrap:anywhere;margin:8px 0 0}.ut-radio,.ut-check{color:var(--text-color);font-size:13px;margin:10px 0 18px}.ut-radio label,.ut-check label{display:inline-block;margin-right:18px;margin-bottom:9px;cursor:pointer}.ut-radio input,.ut-check input{accent-color:#00bd79;margin-right:5px}
#main-container .custom-dropdown .Select-control{background:var(--dropdown-bg);border-color:var(--border-color);color:var(--text-color);border-radius:9px;min-height:42px}
#main-container .custom-dropdown .Select-placeholder,#main-container .custom-dropdown .Select-value-label,#main-container .custom-dropdown .Select-input>input{color:var(--text-color)!important}
#main-container .custom-dropdown .Select-menu-outer{background:var(--dropdown-bg);border-color:var(--border-color)}#main-container .custom-dropdown .VirtualizedSelectOption{color:var(--text-color)}#main-container .custom-dropdown .VirtualizedSelectFocusedOption{background:var(--hover-bg)}
#main-container .DateInput_input{background:var(--dropdown-bg);color:var(--text-color);font-family:inherit;font-size:13px}.SingleDatePickerInput{background:var(--dropdown-bg);border:1px solid var(--border-color);border-radius:9px}
.ut-main-content.ui-compact .ut-card{padding:17px}.ut-main-content.ui-compact .ut-kpi{padding:14px}.ut-main-content.ui-compact .ut-hero{padding:22px 27px;min-height:145px}.ut-main-content.ui-compact .ut-list-row{padding:11px}
.ut-main-content.ui-motion-off *,.ut-main-content.ui-motion-off *:before,.ut-main-content.ui-motion-off *:after{animation:none!important;transition:none!important}
@keyframes utPageEnter{from{opacity:0;transform:translateY(11px)}to{opacity:1;transform:translateY(0)}}@keyframes utItemEnter{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}@keyframes utOrb{from{transform:translateY(-7px) scale(.98)}to{transform:translateY(15px) scale(1.08)}}
@media(max-width:1190px){.ut-kpi-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:860px){#sidebar-container{position:relative!important;width:100%!important;min-height:unset!important;height:auto!important;bottom:auto!important;padding:15px!important;overflow:visible!important}#sidebar-container>div{position:relative!important;width:100%!important;bottom:auto!important;top:auto!important;left:auto!important;min-height:unset!important;height:auto!important;padding:12px!important}#sidebar-container>div>div:nth-child(3){flex-direction:row!important;overflow:auto;gap:7px}#sidebar-container>div>div:nth-child(3)>a{flex-shrink:0}#sidebar-container>div>div:last-child{margin-top:7px!important;flex-direction:row!important}#page-content{margin-left:0!important;padding:18px!important}.ut-hero{padding:25px 21px}.ut-hero-icon{display:none}}
@media(max-width:540px){.ut-kpi-grid{grid-template-columns:1fr 1fr;gap:10px}.ut-kpi{padding:13px}.ut-kpi-value{font-size:24px}.ut-card{padding:17px}.ut-form-grid{grid-template-columns:1fr}.ut-list-row{flex-wrap:wrap}.ut-hero-title{font-size:27px}}
@media(prefers-reduced-motion:reduce){*,*:before,*:after{animation-duration:.01ms!important;animation-iteration-count:1!important;transition-duration:.01ms!important}}

'''
app.index_string = app.index_string.replace('</head>', '<style id="uttec-estilos">' + UTTEC_CSS_INTEGRADO + '</style></head>')

# ================================================
# INTEGRACIÓN MOODLE (solo lectura; sin datos inventados)
# ================================================
cache = Cache(app.server, config={'CACHE_TYPE': 'SimpleCache', 'CACHE_DEFAULT_TIMEOUT': 300})
URL_MOODLE = os.environ.get('MOODLE_URL', 'https://virtual2.uttecamac.edu.mx/webservice/rest/server.php')
BASE_MOODLE = URL_MOODLE.split('/webservice/rest/')[0].rstrip('/')
DATA_DIR = os.environ.get('UTTEC_DATA_DIR', os.path.dirname(os.path.abspath(__file__)))
os.makedirs(DATA_DIR, exist_ok=True)
JSON_FILE_PATH = os.path.join(DATA_DIR, 'data_moodle.json')
CATALOGO_PATH = os.path.join(DATA_DIR, 'catalogo_moodle.json')
SYNC_INTERVAL_SECONDS = max(300, int(os.environ.get('MOODLE_SYNC_INTERVAL', '1800')))
MOODLE_WORKERS = max(1, min(6, int(os.environ.get('MOODLE_WORKERS', '3'))))
MAX_COURSES = max(0, int(os.environ.get('MOODLE_MAX_COURSES', '0')))
MAX_GRADE_USERS = max(0, int(os.environ.get('MOODLE_MAX_GRADE_USERS', '0')))
MOODLE_GRADE_DETAILS_ALL = os.environ.get('MOODLE_GRADE_DETAILS_ALL', 'false').lower() in ('1', 'true', 'yes')
# Evita miles de peticiones individuales al iniciar; primero se obtienen los reportes por curso.
MOODLE_INDIVIDUAL_GRADE_LOOKUP = os.environ.get('MOODLE_INDIVIDUAL_GRADE_LOOKUP', 'false').lower() in ('1','true','yes')
_cached_df = pd.DataFrame()
_cached_mtime = -1.0
_lock_datos = threading.RLock()
_logger = logging.getLogger('uttec.moodle')
_logger.setLevel(logging.INFO)
if not _logger.handlers:
    _console = logging.StreamHandler()
    _console.setFormatter(logging.Formatter('%(asctime)s %(levelname)s uttec.moodle: %(message)s'))
    _logger.addHandler(_console)
_logger.propagate = False


def _user_authorized():
    # Autorización verificada contra sesión firmada del servidor, nunca contra dcc.Store.
    if not has_request_context():
        return True  # Procesos internos de sincronización.
    return bool(flask_session.get('uttec_authorized') is True)


def _moodle_request(function, params=None, token=None, timeout=25):
    token = token or os.environ.get('MOODLE_TOKEN')
    if not token:
        raise RuntimeError('Falta MOODLE_TOKEN en variables de entorno')
    payload = {'wstoken': token, 'wsfunction': function, 'moodlewsrestformat': 'json'}
    payload.update(params or {})
    # POST evita colocar tokens en URLs de historial y logs de proxy.
    try:
        response = requests.post(URL_MOODLE, data=payload, timeout=timeout)
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise RuntimeError(f'Fallo de red o JSON en {function}: {type(exc).__name__}') from exc
    if isinstance(data, dict) and ('exception' in data or 'errorcode' in data and 'message' in data):
        raise RuntimeError(f'{function}: {data.get("errorcode") or data.get("exception")}: {str(data.get("message", "Sin acceso"))[:180]}')
    return data


def clean_moodle_html(html_str):
    if not html_str:
        return ''
    return re.sub(r'<[^>]*>', '', unescape(str(html_str))).strip()


def _valor_numerico(text):
    if text is None or isinstance(text, bool):
        return None
    if isinstance(text, (int, float)):
        return float(text) if pd.notna(text) else None
    t = clean_moodle_html(str(text)).replace('\u00a0', ' ').strip()
    if not t or t in {'-', '–', '—'}:
        return None
    t = t.replace(' ', '')
    if ',' in t and '.' in t:
        t = t.replace(',', '') if t.rfind('.') > t.rfind(',') else t.replace('.', '').replace(',', '.')
    elif ',' in t:
        t = t.replace(',', '.')
    match = re.fullmatch(r'[+-]?\d+(?:\.\d+)?', t)
    return float(t) if match else None


def _nota_de_item(raw, min_value, max_value):
    nota = _valor_numerico(raw)
    minimo, maximo = _valor_numerico(min_value), _valor_numerico(max_value)
    if nota is None or maximo is None or minimo is None or maximo <= minimo:
        return None
    # Se normaliza a 0..10 usando exactamente la escala publicada por Moodle.
    norm = (nota - minimo) * 10.0 / (maximo - minimo)
    if not -0.001 <= norm <= 10.001:
        return None
    return round(min(10.0, max(0.0, norm)), 3)


def _extraer_calificacion(user_id, course_id):
    """Devuelve nota de curso y elementos evaluados. Los fallos quedan sin nota."""
    try:
        obj = _moodle_request('gradereport_user_get_grade_items',
                              {'courseid': course_id, 'userid': user_id})
        bloques = obj.get('usergrades', []) if isinstance(obj, dict) else []
        if not bloques:
            raise RuntimeError('Sin elementos de calificación por grade_items')
        grade_items = bloques[0].get('gradeitems', [])
        curso = None
        actividades = []
        for item in grade_items:
            if not isinstance(item, dict):
                continue
            raw = item.get('graderaw')
            # Para algunos servicios, el raw puede no estar visible.
            if raw is None:
                continue
            nota = _nota_de_item(raw, item.get('grademin', 0), item.get('grademax'))
            if nota is None:
                continue
            typ = item.get('itemtype', '')
            nombre = clean_moodle_html(item.get('itemname') or item.get('itemmodule') or 'Actividad')
            if typ == 'course':
                curso = nota
            elif typ == 'mod':
                actividades.append({'nombre': nombre[:130], 'calificacion': nota})
        if curso is None:
            try:
                report = _moodle_request('gradereport_user_get_grades_table',
                                         {'courseid': course_id, 'userid': user_id})
                for tabla in (report.get('tables', []) if isinstance(report, dict) else []):
                    if str(tabla.get('userid')) == str(user_id):
                        curso = _nota_tabla_moodle(tabla)
                        break
            except RuntimeError:
                pass
        return curso, actividades[:100], None
    except RuntimeError as exc:
        try:
            obj = _moodle_request('gradereport_user_get_grades_table',
                                  {'courseid': course_id, 'userid': user_id})
            for tabla in (obj.get('tables', []) if isinstance(obj, dict) else []):
                if str(tabla.get('userid')) == str(user_id):
                    return _nota_tabla_moodle(tabla), [], None
        except RuntimeError:
            pass
        return None, [], str(exc)[:150]


def _nota_tabla_moodle(tabla):
    """Recupera TOTAL DE CURSO cuando trae rango explícito. No supone 0-10."""
    for item in tabla.get('tabledata', []) or []:
        if not isinstance(item, dict):
            continue
        def content(key):
            obj = item.get(key, {})
            return clean_moodle_html(obj.get('content', '') if isinstance(obj, dict) else obj)
        titulo = content('itemname').lower()
        if not any(marker in titulo for marker in ('total del curso', 'total de curso',
                                                   'total curso', 'course total', 'total course')):
            continue
        grade = content('grade').strip()
        rango = content('range').strip().replace('–', '-').replace('—', '-')
        # Ej. 8.5 / 10 o 84.1% admiten escala determinada por formato.
        match_fraction = re.match(r'^\s*([0-9][0-9.,]*)\s*/\s*([0-9][0-9.,]*)', grade)
        if match_fraction:
            return _nota_de_item(match_fraction.group(1), 0, match_fraction.group(2))
        if grade.endswith('%'):
            return _nota_de_item(grade[:-1], 0, 100)
        match_range = re.search(r'(-?\d+(?:[.,]\d+)?)\s*-\s*(-?\d+(?:[.,]\d+)?)', rango)
        if match_range:
            return _nota_de_item(grade, match_range.group(1), match_range.group(2))
        # Un valor sin escala confirmada no se debe representar como nota de 0 a 10.
        return None
    return None


def _es_estudiante(user):
    roles = user.get('roles') or []
    if not roles:
        return True  # Moodle podría ocultar el rol al token; se anota en diagnóstico.
    return any(str(r.get('shortname', '')).lower() == 'student' or str(r.get('roleid')) == '5' for r in roles)


def _safe_link(url):
    u = urllib.parse.urlparse(str(url or ''))
    base = urllib.parse.urlparse(BASE_MOODLE)
    if u.scheme not in ('https', 'http') or u.hostname != base.hostname:
        return None
    # Nunca se muestran URLs que incluyen tokens de acceso.
    if any(k.lower() in ('token', 'wstoken', 'sesskey') for k in urllib.parse.parse_qs(u.query)):
        return None
    return str(url)


def _get_course_content(course):
    cid = course['id']
    activities, resources, forums = [], [], []
    try:
        sections = _moodle_request('core_course_get_contents', {'courseid': cid})
        if not isinstance(sections, list):
            return activities, resources, forums, 'Respuesta inesperada de contenidos'
        for sec in sections:
            for module in sec.get('modules', []) or []:
                if not isinstance(module, dict):
                    continue
                kind = str(module.get('modname', '')).lower()
                title = clean_moodle_html(module.get('name', ''))[:180]
                url = _safe_link(module.get('url'))
                if not url and module.get('id') and kind in {'forum','assign','quiz','lesson','workshop','choice','h5pactivity','resource','page','url','folder','book'}:
                    url = f'{BASE_MOODLE}/mod/{kind}/view.php?id={int(module["id"])}'
                row = {'curso': course['fullname'], 'carrera': course['carrera'],
                       'course_id': cid, 'nombre': title, 'tipo': kind,
                       'url': url, 'section': sec.get('name', '')}
                if kind in ('assign', 'quiz', 'lesson', 'workshop', 'choice', 'h5pactivity'):
                    dates = module.get('dates') or []
                    for date in dates:
                        if date.get('timestamp'):
                            row['fecha'] = date.get('timestamp')
                            break
                    activities.append(row)
                elif kind == 'forum':
                    forums.append(row)
                elif kind in ('resource', 'page', 'url', 'folder', 'book', 'label', 'file'):
                    resources.append(row)
        return activities, resources, forums, None
    except (RuntimeError, TypeError, ValueError) as exc:
        return activities, resources, forums, str(exc)[:160]


def _atomic_json_write(path, data):
    temp = f'{path}.{os.getpid()}.{threading.get_ident()}.tmp'
    try:
        with open(temp, 'w', encoding='utf-8') as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2, allow_nan=False)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def _leer_catalogo():
    if not _user_authorized():
        return {}
    try:
        with open(CATALOGO_PATH, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError, TypeError):
        return {}


def _marca_sincronizacion():
    cat = _leer_catalogo()
    return cat.get('last_synced') or 'Pendiente de sincronización'


def obtener_datos_moodle_live(progress_callback=None):
    """Sincroniza por lotes: guarda pronto registros de Moodle, sin notas ni grupos ficticios.

    progress_callback acepta (DataFrame, catalogo) y escribe cortes parciales en disco.
    """
    categorias = _moodle_request('core_course_get_categories')
    cursos_raw = _moodle_request('core_course_get_courses')
    if not isinstance(categorias, list) or not isinstance(cursos_raw, list):
        raise RuntimeError('Moodle no devolvió categorías y cursos válidos')
    cats = {c.get('id'): c for c in categorias if isinstance(c, dict)}

    def division(cid):
        nombres, visitados = [], set()
        while cid in cats and cid not in visitados:
            visitados.add(cid)
            cat = cats[cid]
            nombres.append(clean_moodle_html(cat.get('name', '')))
            cid = cat.get('parent')
        return (nombres[-1] if nombres else 'SIN DIVISIÓN DISPONIBLE').upper()

    courses = []
    for course in cursos_raw:
        if not isinstance(course, dict) or not course.get('id') or int(course['id']) == 1:
            continue
        courses.append({'id': int(course['id']),
                        'fullname': clean_moodle_html(course.get('fullname', '')).upper(),
                        'carrera': division(course.get('categoryid')),
                        'categoryid': course.get('categoryid'),
                        'url': f'{BASE_MOODLE}/course/view.php?id={int(course["id"])}'})
    if MAX_COURSES:
        courses = courses[:MAX_COURSES]
    _logger.info('Moodle: %s cursos detectados. Iniciando lectura progresiva.', len(courses))
    data, full_courses, errores = [], [], []
    registros_solo_reporte, correct_enrol_calls = 0, 0
    cached_bulk_reports = {}
    actividades, recursos, foros = [], [], []
    consultas_notas_realizadas = 0

    def snapshot(in_progress=True):
        now = datetime.now(timezone.utc).isoformat(timespec='seconds')
        return {'last_synced': now, 'sync_in_progress': in_progress,
                'courses': list(full_courses),
                'activities': list(actividades), 'resources': list(recursos),
                'forums': list(foros),
                'total_matriculas': len(data) - registros_solo_reporte,
                'registros_solo_reporte': registros_solo_reporte,
                'consultas_notas': consultas_notas_realizadas,
                'calificaciones_disponibles': sum(r['calificacion_final'] is not None for r in data),
                'sin_calificacion': sum(r['calificacion_final'] is None for r in data),
                'matriculas_por_consultar': len(courses) - correct_enrol_calls,
                'errores': list(errores[:80]),
                'cursos_consultados': len(full_courses),
                'cursos_totales': len(courses),
                'cursos_matriculas_consultadas': correct_enrol_calls}

    def publish_progress(stage):
        if progress_callback is not None:
            progress_callback(pd.DataFrame(data), snapshot(in_progress=True))
        _logger.info('%s: %s/%s cursos, %s registros, %s notas, %s fallos',
                     stage, len(full_courses), len(courses), len(data),
                     sum(r['calificacion_final'] is not None for r in data), len(errores))

    # Consultar matrículas con un límite de concurrencia bajo para no saturar Moodle.
    # Sin permisos de matrícula se utiliza únicamente el reporte que antes empleaba Odalys.
    def cargar_curso(course):
        cid = course['id']
        local_errors, local_data, report = [], [], None
        enrol_ok = False
        try:
            enrolled = _moodle_request('core_enrol_get_enrolled_users', {'courseid': cid}, timeout=18)
            if not isinstance(enrolled, list):
                raise RuntimeError('Formato de participantes inesperado')
            enrol_ok = True
        except RuntimeError as exc:
            local_errors.append(f'Matrícula curso {cid}: {exc}')
            enrolled = []
        students = [u for u in enrolled if isinstance(u, dict) and _es_estudiante(u)]
        full = {**course,
                'matriculados': len(students) if enrol_ok else None,
                'estado_matriculas': 'Consultado' if enrol_ok else 'Sin permiso / error',
                'grupos': sorted(set(str(g.get('name','')).strip() for u in students
                                     for g in (u.get('groups') or [])
                                     if isinstance(g, dict) and g.get('name')))}
        for u in students:
            groups = [clean_moodle_html(g.get('name')) for g in (u.get('groups') or [])
                      if isinstance(g, dict) and g.get('name')]
            local_data.append({'user_id': u.get('id'), 'course_id': cid,
                               'carrera': course['carrera'], 'curso': course['fullname'],
                               'grupo': groups[0].upper() if groups else 'SIN GRUPO ASIGNADO',
                               'nombre_alumno': clean_moodle_html(u.get('fullname','')).upper(),
                               'calificacion_final': None, 'items_calificados': [],
                               'origen': 'matricula_verificada'})
        if not enrol_ok:
            try:
                report = _moodle_request('gradereport_user_get_grades_table', {'courseid': cid}, timeout=18)
                tables = report.get('tables',[]) if isinstance(report,dict) else []
                tables = tables if isinstance(tables,list) else []
                for tab in tables:
                    if not isinstance(tab,dict):
                        continue
                    nombre = clean_moodle_html(tab.get('userfullname','')).upper()
                    if not nombre:
                        continue
                    local_data.append({'user_id': tab.get('userid'), 'course_id': cid,
                                       'carrera': course['carrera'], 'curso': course['fullname'],
                                       'grupo': 'GRUPO NO DISPONIBLE', 'nombre_alumno': nombre,
                                       'calificacion_final': _nota_tabla_moodle(tab),
                                       'items_calificados': [], 'origen': 'reporte_calificaciones'})
                if tables:
                    full['estado_matriculas'] = 'Informe de calificaciones; matrícula no verificada'
                    full['registros_de_reporte'] = len(tables)
            except RuntimeError as exc:
                local_errors.append(f'Informe curso {cid}: {exc}')
        return full, local_data, enrol_ok, report, local_errors

    with ThreadPoolExecutor(max_workers=MOODLE_WORKERS) as executor:
        futures = {executor.submit(cargar_curso, c): c for c in courses}
        for future in as_completed(futures):
            course = futures[future]
            try:
                full, rows, enrol_ok, report, local_errors = future.result()
                full_courses.append(full)
                data.extend(rows)
                correct_enrol_calls += int(enrol_ok)
                registros_solo_reporte += sum(r['origen'] == 'reporte_calificaciones' for r in rows)
                if report is not None:
                    cached_bulk_reports[course['id']] = report
                for err in local_errors:
                    if len(errores) < 80:
                        errores.append(err)
            except Exception as exc:
                if len(errores) < 80:
                    errores.append(f'Curso {course["id"]}: {type(exc).__name__}')
                full_courses.append({**course, 'matriculados': None,
                                     'grupos':[], 'estado_matriculas':'Error'})
            if len(full_courses) == 1 or len(full_courses) % 5 == 0:
                publish_progress('Matrículas')
    publish_progress('Matrículas completas')

    # Si no hay permiso de ningún tipo, explicar el error en los logs y al usuario.
    if not data and courses:
        _logger.warning('Sin registros: revisa en Logs los errores de Moodle y permisos del token.')

    indices_por_curso = {}
    for index, registro in enumerate(data):
        if registro.get('user_id') is not None:
            indices_por_curso.setdefault(registro['course_id'], {})[str(registro['user_id'])] = index

    def cargar_reporte(cid):
        if cid in cached_bulk_reports:
            return cached_bulk_reports[cid]
        return _moodle_request('gradereport_user_get_grades_table', {'courseid': cid}, timeout=18)

    # El reporte por curso sustituye miles de llamadas por estudiante.
    with ThreadPoolExecutor(max_workers=MOODLE_WORKERS) as executor:
        pending = {executor.submit(cargar_reporte, cid): cid for cid in indices_por_curso}
        done = 0
        for future in as_completed(pending):
            cid = pending[future]
            consultas_notas_realizadas += 1
            done += 1
            try:
                report = future.result()
                tables = report.get('tables', []) if isinstance(report, dict) else []
                if not isinstance(tables, list):
                    tables = []
                for tab in tables:
                    target = indices_por_curso[cid].get(str(tab.get('userid')))
                    if target is not None:
                        nota = _nota_tabla_moodle(tab)
                        if nota is not None:
                            data[target]['calificacion_final'] = nota
            except RuntimeError as exc:
                if len(errores) < 80:
                    errores.append(f'Calificaciones curso {cid}: {exc}')
            if done == 1 or done % 8 == 0:
                publish_progress('Calificaciones')
    publish_progress('Calificaciones completas')

    # La consulta individual es opcional, no debe impedir el primer render del dashboard.
    if MOODLE_INDIVIDUAL_GRADE_LOOKUP:
        consulta = data[:MAX_GRADE_USERS] if MAX_GRADE_USERS else data
        with ThreadPoolExecutor(max_workers=MOODLE_WORKERS) as executor:
            pending = {executor.submit(_extraer_calificacion, r['user_id'], r['course_id']): i
                       for i, r in enumerate(consulta)
                       if r['user_id'] is not None and
                       (r['calificacion_final'] is None or MOODLE_GRADE_DETAILS_ALL)}
            for n, future in enumerate(as_completed(pending), 1):
                i = pending[future]
                consultas_notas_realizadas += 1
                try:
                    nota, items, err = future.result()
                    if nota is not None:
                        data[i]['calificacion_final'] = nota
                    data[i]['items_calificados'] = items
                    if err and len(errores) < 80:
                        errores.append(f'Nota curso {data[i]["course_id"]}: {err}')
                except Exception as exc:
                    if len(errores) < 80:
                        errores.append(f'Nota individual: {type(exc).__name__}')
                if n == 1 or n % 30 == 0:
                    publish_progress('Notas individuales')

    # Los contenidos son complementarios y nunca deben bloquear la publicación de notas.
    with ThreadPoolExecutor(max_workers=MOODLE_WORKERS) as executor:
        futures = {executor.submit(_get_course_content, c): c for c in courses}
        done = 0
        for future in as_completed(futures):
            done += 1
            try:
                a, r, f, err = future.result()
                actividades.extend(a)
                recursos.extend(r)
                foros.extend(f)
                if err and len(errores) < 80:
                    errores.append(f'Contenido curso {futures[future]["id"]}: {err}')
            except Exception as exc:
                if len(errores) < 80:
                    errores.append(f'Contenido curso {futures[future]["id"]}: {type(exc).__name__}')
            if done == 1 or done % 20 == 0:
                publish_progress('Contenidos')

    full_courses.sort(key=lambda c: c.get('id',0))
    catalogo_final = snapshot(in_progress=False)
    _logger.info('Sincronización completada: %s registros, %s notas, %s cursos; %s errores.',
                 len(data), catalogo_final['calificaciones_disponibles'],
                 len(courses), len(errores))
    return pd.DataFrame(data), catalogo_final

def sync_moodle_background():
    """Actualiza en disco con escrituras atómicas; nunca borra una sincronización válida por error."""
    time.sleep(2)
    while True:
        proxima_consulta = SYNC_INTERVAL_SECONDS
        try:
            if not os.environ.get('MOODLE_TOKEN'):
                _logger.warning('Sin MOODLE_TOKEN: no es posible sincronizar.')
                proxima_consulta = 60
            else:
                def guardar_avance(df_avance, catalogo_avance):
                    # El dashboard puede mostrar alumnos aun si faltan otros cursos o notas.
                    _atomic_json_write(JSON_FILE_PATH, {
                        'schema_version': 3,
                        'last_synced': catalogo_avance['last_synced'],
                        'records': json.loads(df_avance.to_json(orient='records', force_ascii=False))
                    })
                    _atomic_json_write(CATALOGO_PATH, catalogo_avance)
                    global _cached_mtime
                    with _lock_datos:
                        _cached_mtime = -1

                df, catalogo = obtener_datos_moodle_live(progress_callback=guardar_avance)
                if df.empty and catalogo.get('cursos_consultados') and not catalogo.get('cursos_matriculas_consultadas'):
                    # Si el servicio rechaza todas las matrículas Y los informes,
                    # no reemplazar por un archivo vacío un resultado anterior válido.
                    raise RuntimeError('No se pudieron consultar matrículas ni informes: se conserva última sincronización')
                # Se preservan las matrículas aunque todavía no tengan calificación.
                _atomic_json_write(JSON_FILE_PATH, {'schema_version': 3, 'last_synced': catalogo['last_synced'],
                                                    'records': json.loads(df.to_json(orient='records', force_ascii=False))})
                _atomic_json_write(CATALOGO_PATH, catalogo)
                global _cached_mtime
                with _lock_datos:
                    _cached_mtime = -1
                _logger.info('Sincronizado: %s matrículas, %s notas, %s cursos',
                             len(df), catalogo['calificaciones_disponibles'], catalogo['cursos_consultados'])
        except Exception as exc:
            # Registrar una causa consultable en Configuración aunque ninguna fila se haya descargado.
            _logger.error('Sincronización Moodle falló: %s', str(exc)[:350])
            try:
                estado = _leer_catalogo()
                estado['sync_in_progress'] = False
                estado['sync_error_at'] = datetime.now(timezone.utc).isoformat(timespec='seconds')
                estado['errores'] = (estado.get('errores') or [])[-15:] + [str(exc)[:200]]
                _atomic_json_write(CATALOGO_PATH, estado)
            except Exception:
                _logger.exception('No se pudo escribir el diagnóstico de sincronización')
            proxima_consulta = 90
        time.sleep(proxima_consulta)


if os.environ.get('MOODLE_AUTO_SYNC', 'true').strip().lower() in ('1', 'yes', 'true'):
    threading.Thread(target=sync_moodle_background, daemon=True, name='MoodleSync').start()


def obtener_datos_procesados():
    """Devuelve datos almacenados, únicamente cuando hay sesión autorizada."""
    if not _user_authorized():
        return pd.DataFrame()
    global _cached_df, _cached_mtime
    if not os.path.exists(JSON_FILE_PATH):
        return pd.DataFrame()
    with _lock_datos:
        try:
            mtime = os.path.getmtime(JSON_FILE_PATH)
            if mtime != _cached_mtime:
                with open(JSON_FILE_PATH, 'r', encoding='utf-8') as fh:
                    obj = json.load(fh)
                # Las versiones antiguas convertían ausencia de nota en 0: no reutilizar esos datos.
                if obj.get('schema_version') != 3:
                    _cached_df = pd.DataFrame()
                    _cached_mtime = mtime
                    return _cached_df.copy()
                new_df = pd.DataFrame(obj.get('records', []))
                if not new_df.empty:
                    if 'grupo' in new_df:
                        new_df['grupo'] = new_df['grupo'].fillna('SIN GRUPO ASIGNADO')
                    new_df['calificacion_final'] = pd.to_numeric(new_df.get('calificacion_final'), errors='coerce')
                    # Evita que lecturas de versiones anteriores muestren 84/10 como aprobado.
                    new_df.loc[~new_df['calificacion_final'].between(0, 10), 'calificacion_final'] = float('nan')
                _cached_df, _cached_mtime = new_df, mtime
            return _cached_df.copy()
        except (OSError, ValueError, TypeError, KeyError) as exc:
            _logger.error('Caché ilegible: %s', type(exc).__name__)
            return _cached_df.copy()


#Integración con la API de OpenAI
@cache.memoize(timeout=3600)
def obtener_diagnostico_ia(nombre_alumno, carrera, curso, grupo, calificacion_final):
    if os.environ.get('ENABLE_AI_DIAGNOSTICS', 'false').lower() not in ('true', '1', 'yes'):
        return {'riesgo': 'No evaluado', 'justificacion_riesgo': 'El diagnóstico externo está desactivado hasta autorizar el tratamiento de datos académicos.',
                'prediccion': 'No hay predicción automática.',
                'recomendaciones': ['Revisar evidencias académicas y ofrecer asesoría individual.']}
    if pd.isna(calificacion_final):
        return {'riesgo': 'No evaluado', 'justificacion_riesgo': 'No existe una nota válida.',
                'prediccion': 'No disponible', 'recomendaciones': ['Verificar si hay calificaciones pendientes.']}
    api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("CHATGPT_CONTRASEÑA")
    if not api_key:
        print("Advertencia: No se encontró la API Key de OpenAI.")
        return {
            "riesgo": "Desconocido",
            "justificacion_riesgo": "No se configuró la API Key de OpenAI (OPENAI_API_KEY) ni CHATGPT_CONTRASEÑA.",
            "prediccion": "Predicción de rendimiento no disponible por falta de credenciales de OpenAI.",
            "recomendaciones": ["Configure la variable de entorno OPENAI_API_KEY para habilitar los diagnósticos por IA."]
        }
        
    try:
        client = OpenAI(api_key=api_key)
        
        prompt = f"""
        Actúa como un Asesor Pedagógico y Analista de Permanencia Escolar experto de la Universidad Tecnológica de Tecámac (UTTEC).
        Analiza al siguiente alumno y genera un diagnóstico académico en formato JSON estricto.
        
        Detalles del alumno:
        - Identificador: estudiante anónimo
        - Carrera: {carrera}
        - Asignatura/Curso: {curso}
        - Grupo Académico: no transmitido
        - Calificación Acumulada Actual: {calificacion_final:.1f} / 10.0
        
        Reglas de la escala de calificaciones UTTEC:
        - Escala de 0 a 10.
        - Calificación aprobatoria mínima: 6.0.
        - Menos de 6.0 representa reprobación inmediata.
        - Notas entre 6.0 y 7.5 representan un desempeño regular con mediano riesgo de deserción o rezago.
        - Notas entre 7.6 y 10.0 representan bajo riesgo y buen rendimiento.
        
        Debes retornar estrictamente un objeto JSON con la siguiente estructura (sin formato Markdown adicional ni comentarios, solo el JSON):
        {{
            "riesgo": "Bajo" | "Medio" | "Alto",
            "justificacion_riesgo": "Una breve explicación de 1-2 oraciones del por qué del nivel de riesgo.",
            "prediccion": "Una frase corta que prediga cualitativamente el rendimiento final en base a su situación actual.",
            "recomendaciones": [
                "Recomendación pedagógica específica y accionable 1.",
                "Recomendación pedagógica específica y accionable 2.",
                "Recomendación pedagógica específica y accionable 3."
            ]
        }}
        """
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Eres un asistente de analítica académica que responde únicamente en formato JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            response_format={"type": "json_object"}
        )
        
        data = json.loads(response.choices[0].message.content.strip())
        
        riesgo = data.get("riesgo", "Medio")
        if riesgo not in ["Bajo", "Medio", "Alto"]:
            riesgo = "Medio"
        justificacion = data.get("justificacion_riesgo", "Sin justificación provista.")
        prediccion = data.get("prediccion", "Sin predicción disponible.")
        recs = data.get("recomendaciones", [])
        if not isinstance(recs, list) or len(recs) == 0:
            recs = ["Brindar tutoría personalizada.", "Hacer seguimiento continuo de calificaciones."]
            
        return {
            "riesgo": riesgo,
            "justificacion_riesgo": justificacion,
            "prediccion": prediccion,
            "recomendaciones": recs
        }
        
    except Exception as e:
        print(f"Error en obtener_diagnostico_ia: {e}")
        return {
            "riesgo": "Error",
            "justificacion_riesgo": f"No se pudo consultar el servicio de IA: {str(e)}",
            "prediccion": "No disponible por error técnico.",
            "recomendaciones": [
                "Por favor, verifique el estado del servicio de OpenAI y su cuota disponible.",
                "Haga seguimiento manual del desempeño académico del estudiante."
            ]
        }

# Estilos 
SIDEBAR_STYLE = {
    'position': 'fixed',
    'top': '0',
    'left': '0',
    'bottom': '0',
    'width': '260px',
    'padding': '30px 20px',
    'backgroundColor': '#000B52',
    'borderRight': '1px solid rgba(0, 168, 89, 0.2)',
    'display': 'flex',
    'flexDirection': 'column',
    'gap': '20px',
    'zIndex': '1000',
}

CONTENT_STYLE = {
    'marginLeft': '280px',
    'padding': '40px',
    'backgroundColor': 'var(--bg-color)',
    'minHeight': '100vh',
}

def render_sidebar():
    menu_items = [
        ("Inicio", "/inicio", "home"),
        ("Cursos", "/cursos", "curso"),
        ("Participantes", "/participantes", "users"),
        ("Calificaciones", "/calificaciones", "calificaciones"),
        ("Analítica", "/", "chart"),
        ("Actividades", "/actividades", "activities"),
        ("Recursos", "/recursos", "resources"),
        ("Foros", "/foros", "forums"),
        ("Mensajes", "/mensajes", "messages"),
        ("Configuración", "/configuracion", "settings")
    ]
    
    links = []
    for name, href, icon_name in menu_items:
        icon_svg = get_svg_icon(icon_name, "#ffffff")
        contenido = [
            icon_svg,
            html.Span(name, style={
                'fontSize': '15px', 'fontWeight': '600', 'color': '#ffffff'
            })
        ]
        id_nav = {
            'Inicio': 'nav-inicio',
            'Cursos': 'nav-cursos',
            'Participantes': 'nav-participantes',
            'Calificaciones': 'nav-calificaciones',
            'Analítica': 'nav-analitica',
            'Actividades': 'nav-actividades',
            'Recursos': 'nav-recursos',
            'Foros': 'nav-foros',
            'Mensajes': 'nav-mensajes',
            'Configuración': 'nav-configuracion'
        }[name]
        links.append(dcc.Link(
            html.Div(id=id_nav, className='sidebar-link', children=contenido),
            href=href, style={'textDecoration': 'none'}
        ))

    # Base64 encoded mortarboard 
    school_svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{COLOR_VERDE_BANDERA}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <polygon points="12 2 22 8.5 12 15 2 8.5 12 2" fill="{COLOR_VERDE_BANDERA}"/>
        <path d="M6 11.5v4.5c0 1.5 3 2.5 6 2.5s6-1 6-2.5v-4.5"/>
        <path d="M22 9v4"/>
    </svg>"""
    school_encoded = base64.b64encode(school_svg.encode()).decode()
    school_logo = html.Img(
        src=f"data:image/svg+xml;base64,{school_encoded}",
        style={'width': '36px', 'height': '36px', 'marginRight': '12px', 'verticalAlign': 'middle'}
    )

    logo_header = html.Div(style={'display': 'flex', 'alignItems': 'center', 'padding': '10px 5px'}, children=[
        school_logo,
        html.Div(children=[
            html.H2("Plataforma", style={'margin': '0', 'fontSize': '16px', 'fontWeight': '800', 'color': '#ffffff', 'letterSpacing': '0.5px', 'lineHeight': '1.1'}),
            html.H2("Virtual UTTEC", style={'margin': '0', 'fontSize': '16px', 'fontWeight': '800', 'color': COLOR_VERDE_BANDERA, 'letterSpacing': '0.5px', 'lineHeight': '1.1'})
        ])
    ])

    # Botón conmutador de tema al final del sidebar
    theme_toggle = html.Button(
        id='theme-toggle-btn',
        n_clicks=0,
        className='sidebar-link',
        style={
            'backgroundColor': 'transparent',
            'border': 'none',
            'width': '100%',
            'textAlign': 'left',
            'marginTop': 'auto',
            'padding': '12px 18px',
            'color': COLOR_VERDE_BANDERA,
            'cursor': 'pointer',
            'display': 'flex',
            'alignItems': 'center'
        }
    )

    # Botón de cerrar sesión
    logout_button = html.Button(
        id='logout-btn',
        n_clicks=0,
        className='sidebar-link',
        children=[
            get_svg_icon('logout', '#ffffff'),
            html.Span("Cerrar Sesión", style={'fontSize': '15px', 'fontWeight': '600', 'color': '#ffffff'})
        ],
        style={
            'backgroundColor': 'transparent',
            'border': 'none',
            'width': '100%',
            'textAlign': 'left',
            'padding': '12px 18px',
            'color': '#ffffff',
            'cursor': 'pointer',
            'display': 'flex',
            'alignItems': 'center',
            'marginTop': '8px'
        }
    )

    return html.Div(style=SIDEBAR_STYLE, children=[
        logo_header,
        html.Hr(style={'borderColor': 'rgba(0, 128, 0, 0.25)', 'margin': '10px 0'}),
        html.Div(links, style={'display': 'flex', 'flexDirection': 'column'}),
        html.Div(style={'marginTop': 'auto', 'display': 'flex', 'flexDirection': 'column'}, children=[
            theme_toggle,
            logout_button
        ])
    ])

# Resaltar la opción seleccionada sin recargar la aplicación.
@app.callback(
    [Output(id_nav, 'className') for id_nav in (
        'nav-inicio', 'nav-cursos', 'nav-participantes', 'nav-calificaciones',
        'nav-analitica', 'nav-actividades', 'nav-recursos', 'nav-foros',
        'nav-mensajes', 'nav-configuracion'
    )],
    Input('url', 'pathname')
)
def actualizar_menu_inicio(pathname):
    equivalencias = {'/curso': '/cursos', '/login': '/', None: '/'}
    ruta = equivalencias.get(pathname, pathname)
    if ruta and ruta.startswith('/alumno/'):
        ruta = '/'
    opciones = ('/inicio', '/cursos', '/participantes', '/calificaciones', '/',
                '/actividades', '/recursos', '/foros', '/mensajes', '/configuracion')
    return tuple('sidebar-link-active' if opcion == ruta else 'sidebar-link'
                 for opcion in opciones)


# ====================================================================
# INTERFAZ INICIO (integrada aqui, sin archivos adicionales)
# Indicadores vacios hasta que se conecte la informacion de Moodle.
# ====================================================================
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
            _tarjeta('Estudiantes identificados', _valor(datos, 'estudiantes'), 'Identidades en datos consultados de Moodle'),
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



# ====================================================================
# INTERFAZ CURSOS
# Sólo presentación: no extraen información de Moodle, no crean
# estudiantes y no almacenan datos personales en el navegador.
# Sus parámetros permiten entregar información real más adelante.
# ====================================================================

def _titulo_modulo(subtitulo, titulo, descripcion, icono):
    return html.Div(style={
        'display': 'flex', 'alignItems': 'center', 'flexWrap': 'wrap',
        'justifyContent': 'space-between', 'gap': '20px',
        'borderBottom': BORDE, 'paddingBottom': '22px', 'marginBottom': '28px'
    }, children=[
        html.Div(children=[
            html.P(subtitulo, style={
                'color': VERDE, 'fontWeight': '800', 'fontSize': '12px',
                'letterSpacing': '1.6px', 'margin': '0 0 9px'
            }),
            html.H1(titulo, style={
                'fontSize': '30px', 'color': TEXTO, 'margin': '0 0 8px',
                'fontWeight': '800'
            }),
            html.P(descripcion, style={
                'fontSize': '14px', 'color': SUAVE, 'margin': 0
            })
        ]),
        html.Div(style={
            'display': 'flex', 'alignItems': 'center', 'gap': '9px',
            'padding': '12px 15px', 'border': BORDE, 'borderRadius': '12px',
            'backgroundColor': TARJETA
        }, children=[
            get_svg_icon(icono, VERDE),
            html.Span('Conectado a los datos de Moodle' if _leer_catalogo().get('last_synced') else 'Pendiente de sincronización', style={
                'color': SUAVE, 'fontSize': '12px', 'fontWeight': '600'
            })
        ])
    ])


def _filtro_modulo(titulo, identificador, texto, es_busqueda=False):
    cat = _leer_catalogo()
    cursos = cat.get('courses') or []
    if identificador == 'cursos-filtro-division':
        valores = sorted({str(c.get('carrera', '')) for c in cursos if c.get('carrera')})
    elif identificador == 'cursos-filtro-grupo':
        valores = sorted({str(g) for c in cursos for g in (c.get('grupos') or []) if g})
    else:
        valores = []
    control = (dcc.Input(id=identificador, type='text', placeholder=texto, disabled=not bool(cursos),
                         style={'width': '100%', 'height': '43px', 'padding': '0 12px',
                                'borderRadius': '8px', 'border': BORDE, 'backgroundColor': 'var(--dropdown-bg)',
                                'color': TEXTO, 'boxSizing': 'border-box', 'fontSize': '13px'})
               if es_busqueda else dcc.Dropdown(id=identificador, options=_opciones(valores),
                                                placeholder=texto, disabled=not bool(cursos),
                                                className='custom-dropdown', clearable=True))
    return html.Div(style={'flex': '1 1 185px', 'minWidth': 0}, children=[
        html.Label(titulo, style={'display': 'block', 'fontSize': '11px',
                                  'fontWeight': '700', 'color': SUAVE, 'marginBottom': '9px'}), control])


def _encabezado_tabla(titulo, descripcion):
    return html.Div(style={
        'display': 'flex', 'justifyContent': 'space-between',
        'gap': '10px', 'flexWrap': 'wrap', 'marginBottom': '18px'
    }, children=[
        html.Div(children=[
            html.H3(titulo, style={
                'margin': '0 0 6px', 'fontSize': '18px', 'color': TEXTO
            }),
            html.P(descripcion, style={
                'margin': 0, 'fontSize': '13px', 'color': SUAVE
            })
        ]),
        html.Span('Consultar y filtrar', style={
            'fontSize': '12px', 'fontWeight': '600', 'color': SUAVE,
            'padding': '8px 12px', 'borderRadius': '30px',
            'border': BORDE, 'alignSelf': 'flex-start'
        })
    ])


def _tabla_modulo(identificador, columnas, registros=None):
    # El campo datos puede recibir registros autorizados posteriormente.
    registros = registros if isinstance(registros, list) else []
    campos = [c['id'] for c in columnas]
    filas = [
        {campo: fila.get(campo) for campo in campos}
        for fila in registros if isinstance(fila, dict)
    ]
    return html.Div(children=[
        dash_table.DataTable(
            id=identificador,
            columns=columnas,
            data=filas,
            page_size=10,
            sort_action='native' if filas else 'none',
            style_as_list_view=True,
            style_table={'overflowX': 'auto'},
            style_header={
                'backgroundColor': 'var(--hover-bg)',
                'color': TEXTO, 'padding': '16px',
                'fontWeight': '700', 'border': 'none',
                'fontSize': '12px', 'textAlign': 'left'
            },
            style_cell={
                'backgroundColor': TARJETA, 'color': TEXTO,
                'padding': '15px', 'fontSize': '13px',
                'textAlign': 'left', 'fontFamily': 'Outfit, sans-serif',
                'border': 'none', 'minWidth': '135px',
                'whiteSpace': 'normal', 'height': 'auto'
            },
            style_data_conditional=[
                {'if': {'row_index': 'odd'},
                 'backgroundColor': 'var(--hover-bg)'}
            ]
        ),
        html.Div(style={
            'textAlign': 'center', 'padding': '34px 15px',
            'borderTop': BORDE
        }, children=[
            html.Div(style={'display': 'flex', 'justifyContent': 'center'},
                     children=[get_svg_icon('resources', VERDE)]),
            html.P('Todavía no hay información para mostrar', style={
                'color': TEXTO, 'fontSize': '14px',
                'fontWeight': '600', 'marginBottom': '7px'
            }),
            html.P('No hay datos sincronizados que coincidan con la búsqueda.',
                   style={'color': SUAVE, 'fontSize': '12px', 'margin': 0})
        ]) if not filas else html.Div()
    ])


def render_cursos(datos=None):
    """Pantalla Cursos: interfaz lista para mostrar datos sin fabricarlos.

    datos opcional: dict con 'total_cursos', 'total_divisiones',
    'total_grupos', 'total_matriculados' y 'registros' (lista de dicts).
    Columnas del registro: nombre, division, grupo, matriculados, estado.
    """
    datos = datos if isinstance(datos, dict) else {}
    registros = datos.get('registros') or []
    columnas = [
        {'name': 'Curso / Asignatura', 'id': 'nombre'},
        {'name': 'División / Carrera', 'id': 'division'},
        {'name': 'Grupo', 'id': 'grupo'},
        {'name': 'Estudiantes', 'id': 'matriculados'},
        {'name': 'Estado', 'id': 'estado'}
    ]
    return html.Div(id='vista-cursos', children=[
        _titulo_modulo('GESTIÓN ACADÉMICA', 'Cursos',
                       'Consulta y organiza las asignaturas, grupos y matrículas de Virtual UTTEC.',
                       'curso'),
        html.Div(style={
            'display': 'flex', 'gap': '16px', 'flexWrap': 'wrap',
            'marginBottom': '26px'
        }, children=[
            _tarjeta('Cursos registrados', _valor(datos, 'total_cursos'),
                     'Asignaturas disponibles'),
            _tarjeta('Divisiones académicas', _valor(datos, 'total_divisiones'),
                     'Áreas y carreras'),
            _tarjeta('Grupos vinculados', _valor(datos, 'total_grupos'),
                     'Grupos académicos'),
            _tarjeta('Matrícula vinculada', _valor(datos, 'total_matriculados'),
                     'Inscripciones en los cursos')
        ]),
        html.Div(style={
            'backgroundColor': TARJETA, 'border': BORDE,
            'padding': '22px', 'borderRadius': '15px',
            'marginBottom': '24px'
        }, children=[
            html.H3('Explorar cursos', style={
                'fontSize': '17px', 'color': TEXTO, 'margin': '0 0 18px'
            }),
            html.Div(style={
                'display': 'flex', 'gap': '16px', 'flexWrap': 'wrap'
            }, children=[
                _filtro_modulo('División / Carrera', 'cursos-filtro-division',
                              'Selecciona una división'),
                _filtro_modulo('Grupo', 'cursos-filtro-grupo',
                              'Selecciona un grupo'),
                _filtro_modulo('Buscar curso', 'cursos-buscar',
                              'Nombre de la asignatura...', True)
            ]),
            html.P('Filtra los registros reales sincronizados de Moodle.',
                   style={'color': SUAVE, 'fontSize': '12px',
                          'margin': '15px 0 0'})
        ]),
        html.Div(style={
            'backgroundColor': TARJETA, 'border': BORDE,
            'borderRadius': '15px', 'padding': '24px',
            'marginBottom': '24px'
        }, children=[
            _encabezado_tabla('Listado de cursos',
                             'Catálogo académico disponible para consulta.'),
            _tabla_modulo('cursos-tabla', columnas, registros)
        ]),
        html.Div(style={
            'display': 'flex', 'gap': '20px', 'flexWrap': 'wrap'
        }, children=[
            _bloque('Distribución por división',
                    'Datos sincronizados por división.', [f"{k}: {v}" for k,v in sorted(__import__('collections').Counter(r.get('division') for r in registros).items()) if k]),
            _bloque('Actividad académica',
                    'Actividades y recursos obtenidos.', [f"Actividades: {len(_leer_catalogo().get('activities', []))}", f"Recursos: {len(_leer_catalogo().get('resources', []))}", f"Foros: {len(_leer_catalogo().get('forums', []))}"])
        ])
    ])


# ===========================================================================
# NUEVAS INTERFACES — Integradas dentro de app.py (sin módulos adicionales)
# ===========================================================================

def _mod_hero(etiqueta, titulo, descripcion, icono, color='#21db90'):
    return html.Div(className='ut-hero', children=[
        html.Div(className='ut-hero-orb'),
        html.Div(style={'position': 'relative', 'zIndex': 1}, children=[
            html.Div(className='ut-eyebrow', children=[get_svg_icon(icono, color), etiqueta]),
            html.H1(titulo, className='ut-hero-title'),
            html.P(descripcion, className='ut-hero-desc')
        ]),
        html.Div(className='ut-hero-icon', children=[get_svg_icon(icono, '#ffffff')])
    ])


def _mod_card(titulo, contenido, descripcion=None, extra_class=''):
    return html.Div(className='ut-card ' + extra_class, children=[
        html.Div(className='ut-card-head', children=[
            html.Div(children=[
                html.H3(titulo, className='ut-card-title'),
                html.P(descripcion, className='ut-card-subtitle') if descripcion else None
            ])
        ]),
        contenido
    ])


def _mod_kpi(etiqueta, valor, leyenda, icono, color='#1adf92'):
    return html.Div(className='ut-kpi', children=[
        html.Div(className='ut-kpi-icon', style={'color': color}, children=get_svg_icon(icono, color)),
        html.P(etiqueta, className='ut-kpi-label'),
        html.H2(str(valor), className='ut-kpi-value', style={'color': color}),
        html.P(leyenda, className='ut-kpi-note')
    ])


def _mod_field(etiqueta, elemento):
    return html.Div(className='ut-field', children=[
        html.Label(etiqueta, className='ut-label'), elemento
    ])


def _mod_empty(titulo, detalle, icono='resources'):
    return html.Div(className='ut-empty', children=[
        get_svg_icon(icono, '#29ce89'),
        html.H3(titulo, style={'margin': '13px 0 6px', 'color': 'var(--text-color)'}),
        html.P(detalle, style={'margin': 0, 'color': 'var(--text-muted)', 'lineHeight': 1.6})
    ])


def _mod_notice(texto, icono='settings'):
    return html.Div(className='ut-notice', children=[
        get_svg_icon(icono, '#2fe5a2'), html.Span(texto)
    ])


def _lista_cursos_moodle():
    df = obtener_datos_procesados()
    if df.empty or 'curso' not in df.columns:
        return []
    return sorted(str(x) for x in df['curso'].dropna().unique())


def _input(id_, placeholder, tipo='text'):
    return dcc.Input(id=id_, type=tipo, placeholder=placeholder, className='ut-input')


def _opciones(valores):
    return [{'label': str(x), 'value': str(x)} for x in valores]


# 1) CALIFICACIONES: datos reales del archivo local sincronizado desde Moodle.
def render_calificaciones():
    df = obtener_datos_procesados()
    carreras = sorted(df['carrera'].dropna().astype(str).unique()) if not df.empty and 'carrera' in df else []
    cursos = sorted(df['curso'].dropna().astype(str).unique()) if not df.empty and 'curso' in df else []
    grupos = sorted(df['grupo'].dropna().astype(str).unique()) if not df.empty and 'grupo' in df else []
    return html.Div(className='ut-page', children=[
        _mod_hero('CONTROL ACADÉMICO', 'Calificaciones',
                  'Consulta resultados, identifica prioridades y exporta el registro disponible.', 'calificaciones'),
        _mod_notice('Esta sección consulta las calificaciones sincronizadas del sistema Moodle; no las modifica.', 'calificaciones'),
        _mod_card('Explorar calificaciones', html.Div(className='ut-form-grid', children=[
            _mod_field('División / Carrera', dcc.Dropdown(id='calif-filtro-carrera', options=_opciones(carreras),
                                                         placeholder='Todas las divisiones', clearable=True, className='custom-dropdown')),
            _mod_field('Asignatura', dcc.Dropdown(id='calif-filtro-curso', options=_opciones(cursos),
                                                 placeholder='Todos los cursos', clearable=True, className='custom-dropdown')),
            _mod_field('Grupo', dcc.Dropdown(id='calif-filtro-grupo', options=_opciones(grupos),
                                            placeholder='Todos los grupos', clearable=True, className='custom-dropdown')),
            _mod_field('Buscar estudiante', _input('calif-buscar', 'Nombre del estudiante...'))
        ]), 'Filtra los resultados y descarga la tabla en CSV.'),
        dcc.Loading(html.Div(id='calif-contenido'), type='circle', color='#00b873')
    ])


def _estadisticas_calificaciones(carrera, curso, grupo, buscar):
    df = obtener_datos_procesados()
    campos = {'carrera', 'curso', 'grupo', 'nombre_alumno', 'calificacion_final'}
    if df.empty or not campos.issubset(df.columns):
        return _mod_empty('Sin calificaciones sincronizadas',
                          'Cuando finalice la primera sincronización con Moodle, los resultados se mostrarán aquí.',
                          'calificaciones')
    df = df.copy()
    df['calificacion_final'] = pd.to_numeric(df['calificacion_final'], errors='coerce')
    for campo, valor in (('carrera', carrera), ('curso', curso), ('grupo', grupo)):
        if valor:
            df = df[df[campo].astype(str) == str(valor)]
    if buscar and str(buscar).strip():
        df = df[df['nombre_alumno'].astype(str).str.contains(str(buscar).strip(), case=False, regex=False, na=False)]
    if df.empty:
        return _mod_empty('No hay resultados para esos filtros', 'Prueba otra carrera, curso, grupo o nombre.', 'calificaciones')
    datos_con_nota = df.dropna(subset=['calificacion_final']).copy()

    # Un estudiante puede tener más de una asignatura; los registros se conservan por curso.
    cantidad = int(len(df))
    estudiantes = int(_identidad_para_agrupacion(df).nunique())
    promedio = float(datos_con_nota['calificacion_final'].mean()) if not datos_con_nota.empty else float('nan')
    aprobados = int((datos_con_nota['calificacion_final'] >= 6.0).sum())
    riesgo = int((datos_con_nota['calificacion_final'] < 6.0).sum())
    resumen_curso = (datos_con_nota.groupby('curso', as_index=False)['calificacion_final']
                       .mean().sort_values('calificacion_final', ascending=False).head(12))
    grafico = px.bar(resumen_curso, y='curso', x='calificacion_final', orientation='h',
                     color='calificacion_final', color_continuous_scale=['#e85e75', '#33bdf1', '#18d99a'],
                     labels={'curso': 'Curso', 'calificacion_final': 'Calificación media'},
                     template='plotly_dark')
    grafico.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                          margin=dict(l=12, r=12, t=20, b=35), showlegend=False,
                          coloraxis_showscale=False, font=dict(family='Outfit, sans-serif', color='#cbd9ec'),
                          xaxis=dict(range=[0, 10], gridcolor='rgba(148,163,184,.18)'),
                          yaxis=dict(categoryorder='total ascending', automargin=True))
    grafico.update_traces(marker_line_width=0, hovertemplate='%{y}<br>Promedio: %{x:.2f}<extra></extra>')
    rows = []
    for fila in df[['nombre_alumno', 'carrera', 'curso', 'grupo', 'calificacion_final']].to_dict('records'):
        raw = fila.get('calificacion_final')
        nota = round(float(raw), 2) if pd.notna(raw) else None
        rows.append({**fila, 'calificacion_final': nota, 'estatus': ('Sin calificar' if nota is None else 'Aprobado' if nota >= 6 else 'Por debajo de 6')})
    tabla = dash_table.DataTable(
        id='calif-tabla', columns=[
            {'name': 'Estudiante', 'id': 'nombre_alumno'},
            {'name': 'División', 'id': 'carrera'},
            {'name': 'Curso', 'id': 'curso'},
            {'name': 'Grupo', 'id': 'grupo'},
            {'name': 'Calificación', 'id': 'calificacion_final', 'type': 'numeric'},
            {'name': 'Resultado', 'id': 'estatus'}
        ], data=rows, page_size=12, page_action='native', filter_action='native', sort_action='native',
        export_format='csv', export_headers='display',
        style_table={'overflowX': 'auto'}, style_header={
            'backgroundColor': '#12284a', 'color': '#ffffff', 'fontWeight': '700', 'padding': '14px', 'border': 'none'
        }, style_cell={
            'backgroundColor': 'var(--card-bg)', 'color': 'var(--text-color)', 'border': 'none',
            'borderBottom': '1px solid var(--border-color)', 'padding': '13px',
            'fontFamily': 'Outfit, sans-serif', 'fontSize': '12px', 'textAlign': 'left',
            'maxWidth': '280px', 'minWidth': '120px', 'whiteSpace': 'normal', 'height': 'auto'
        }, style_data_conditional=[
            {'if': {'filter_query': '{estatus} = "Por debajo de 6"', 'column_id': 'estatus'}, 'color': '#ff7689', 'fontWeight': '700'},
            {'if': {'filter_query': '{estatus} = "Aprobado"', 'column_id': 'estatus'}, 'color': '#33dd9c', 'fontWeight': '700'}
        ])
    return html.Div(children=[
        html.Div(className='ut-kpi-grid', children=[
            _mod_kpi('Estudiantes', estudiantes, f'{cantidad} registros consultados', 'users', '#6fb7ff'),
            _mod_kpi('Promedio académico', f'{promedio:.2f}' if pd.notna(promedio) else '—', 'Escala de 0 a 10', 'chart', '#28e4a3'),
            _mod_kpi('Aprobados', aprobados, 'Calificación de 6 o más', 'activities', '#25da91'),
            _mod_kpi('En riesgo', riesgo, 'Calificación inferior a 6', 'calificaciones', '#ff7a8a')
        ]),
        _mod_card('Promedios por asignatura', dcc.Graph(figure=grafico, config={'displayModeBar': False},
                                                       style={'height': '380px'}),
                  'Se muestran hasta 12 cursos del resultado filtrado.'),
        _mod_card('Registro de calificaciones', tabla,
                  'Ordena o busca en la tabla; también puedes exportar los datos visibles.')
    ])


# 2) ACTIVIDADES: gestor de borradores guardados en la sesión del navegador.
def render_actividades():
    cursos = _lista_cursos_moodle()
    return html.Div(className='ut-page', children=[
        _mod_hero('ORGANIZACIÓN DOCENTE', 'Actividades',
                  'Organiza entregas y fechas importantes en un tablero de planificación.', 'activities'),
        _mod_notice('Las actividades que registres aquí son borradores locales de tu sesión. No se crean tareas en Moodle.', 'activities'),
        _mod_card('Nueva actividad', html.Div(children=[
            html.Div(className='ut-form-grid', children=[
                _mod_field('Nombre de la actividad', _input('actividad-titulo', 'Ej. Evaluación de unidad 2')),
                _mod_field('Curso vinculado', dcc.Dropdown(id='actividad-curso', options=_opciones(cursos),
                                                           placeholder='Curso (opcional)', className='custom-dropdown')),
                _mod_field('Fecha objetivo', dcc.DatePickerSingle(id='actividad-fecha',
                                                                   placeholder='Selecciona una fecha', display_format='DD/MM/YYYY')),
                _mod_field('Prioridad', dcc.Dropdown(id='actividad-prioridad',
                                                   options=_opciones(['Alta', 'Media', 'Baja']), value='Media',
                                                   clearable=False, className='custom-dropdown'))
            ]),
            html.Div(className='ut-form-footer', children=[
                html.Button('Guardar borrador', id='actividad-guardar', n_clicks=0, className='ut-btn'),
                html.Span(id='actividad-feedback', className='ut-feedback', role='status')
            ])
        ]), 'Planifica sin modificar los contenidos del aula virtual.'),
        _mod_card('Mis actividades', html.Div(children=[
            html.Div(id='actividad-listado'),
            html.Div(className='ut-inline-action', children=[
                dcc.Dropdown(id='actividad-seleccionar', options=[], placeholder='Actividad pendiente...',
                             className='custom-dropdown', style={'flex': '1 1 240px'}),
                html.Button('Marcar como terminada', id='actividad-completar', n_clicks=0, className='ut-btn ut-btn-outline')
            ])
        ]), 'Estado de las tareas planificadas en esta sesión.')
    ])


def _render_actividad_lista(registros):
    if not registros:
        return _mod_empty('Todavía no hay actividades', 'Añade una actividad para comenzar tu planificación.', 'activities')
    elementos = []
    for a in reversed(registros):
        terminado = a.get('estado') == 'Terminada'
        color = {'Alta': '#ff7b89', 'Media': '#f8cc64', 'Baja': '#34dba0'}.get(a.get('prioridad'), '#7fb7ff')
        elementos.append(html.Div(className='ut-list-row', children=[
            html.Div(className='ut-row-icon', children=get_svg_icon('activities', '#28d99c')),
            html.Div(style={'flex': '1', 'minWidth': 0}, children=[
                html.H4(a.get('titulo', ''), className='ut-row-title'),
                html.P(f"{a.get('curso') or 'Sin asignatura'} · Fecha: {a.get('fecha') or 'Sin definir'}", className='ut-row-meta')
            ]),
            html.Span(a.get('prioridad', 'Media'), className='ut-pill', style={'color': color, 'borderColor': color}),
            html.Span('✓ Terminada' if terminado else 'Pendiente',
                      className='ut-pill', style={'color': '#27dc9b' if terminado else '#80baff'})
        ]))
    return html.Div(elementos)


# 3) RECURSOS: biblioteca de enlaces personales, sin datos inventados de Moodle.
def render_recursos():
    return html.Div(className='ut-page', children=[
        _mod_hero('BIBLIOTECA ACADÉMICA', 'Recursos',
                  'Reúne lecturas, videos y herramientas relevantes para tus cursos.', 'resources'),
        _mod_notice('Los enlaces guardados son personales de esta sesión; no se publican en Moodle.', 'resources'),
        _mod_card('Añadir recurso', html.Div(children=[
            html.Div(className='ut-form-grid', children=[
                _mod_field('Título del recurso', _input('recurso-titulo', 'Ej. Guía de prácticas')),
                _mod_field('Enlace web', _input('recurso-enlace', 'https://...')),
                _mod_field('Tipo de material', dcc.Dropdown(id='recurso-tipo', value='Lectura',
                    options=_opciones(['Lectura', 'Video', 'Herramienta', 'Documento', 'Otro']),
                    clearable=False, className='custom-dropdown'))
            ]),
            html.Div(className='ut-form-footer', children=[
                html.Button('Guardar recurso', id='recurso-guardar', n_clicks=0, className='ut-btn'),
                html.Span(id='recurso-feedback', className='ut-feedback', role='status')
            ])
        ]), 'Agrega solo direcciones HTTP o HTTPS de sitios confiables.'),
        _mod_card('Mi colección', html.Div(id='recurso-listado'),
                  'Abre tus enlaces en una pestaña nueva cuando los necesites.')
    ])


def _render_recursos_lista(registros):
    if not registros:
        return _mod_empty('Tu biblioteca está vacía', 'Guarda tu primer enlace para verlo aquí.', 'resources')
    return html.Div(className='ut-resource-grid', children=[
        html.Div(className='ut-resource', children=[
            html.Div(className='ut-resource-top', children=[
                get_svg_icon('resources', '#27db9e'),
                html.Span(r.get('tipo', 'Recurso'), className='ut-pill')
            ]),
            html.H4(r.get('titulo', ''), className='ut-row-title'),
            html.P(r.get('enlace', ''), className='ut-resource-url'),
            html.A('Abrir recurso ↗', href=r.get('enlace'), target='_blank',
                   rel='noopener noreferrer', className='ut-text-link')
        ]) for r in reversed(registros) if isinstance(r, dict) and
        urllib.parse.urlparse(str(r.get('enlace', ''))).scheme in ('http', 'https')
    ])


# 4) FOROS: discusiones y respuestas en una misma sesión; no compartidas por Moodle.
def render_foros():
    return html.Div(className='ut-page', children=[
        _mod_hero('COMUNIDAD ACADÉMICA', 'Foros',
                  'Prepara debates, temas de discusión y respuestas.', 'forums'),
        _mod_notice('Este es un espacio de preparación local. Las publicaciones y respuestas no son visibles para otros usuarios.', 'forums'),
        _mod_card('Crear tema de discusión', html.Div(children=[
            html.Div(className='ut-form-grid', children=[
                _mod_field('Título del tema', _input('foro-titulo', '¿Qué tema deseas debatir?')),
                _mod_field('Categoría', dcc.Dropdown(id='foro-categoria', value='General',
                    options=_opciones(['General', 'Dudas académicas', 'Propuestas', 'Avisos']),
                    clearable=False, className='custom-dropdown'))
            ]),
            _mod_field('Descripción', dcc.Textarea(id='foro-descripcion',
                    placeholder='Escribe el objetivo y el contexto del debate...', className='ut-textarea')),
            html.Div(className='ut-form-footer', children=[
                html.Button('Guardar discusión', id='foro-crear', n_clicks=0, className='ut-btn'),
                html.Span(id='foro-feedback', className='ut-feedback', role='status')
            ])
        ]), 'Diseña la conversación antes de publicarla mediante los canales oficiales.'),
        _mod_card('Discusiones preparadas', html.Div(id='foro-listado'),
                  'Cada tema puede tener respuestas guardadas en esta sesión.'),
        _mod_card('Añadir respuesta', html.Div(children=[
            _mod_field('Seleccionar discusión', dcc.Dropdown(id='foro-seleccionar', options=[],
                                                             placeholder='Elige un tema...', className='custom-dropdown')),
            _mod_field('Respuesta', dcc.Textarea(id='foro-respuesta', placeholder='Escribe una respuesta...', className='ut-textarea')),
            html.Div(className='ut-form-footer', children=[
                html.Button('Guardar respuesta', id='foro-responder', n_clicks=0, className='ut-btn ut-btn-outline')
            ])
        ]), 'Las respuestas permanecen asociadas al tema elegido.')
    ])


def _render_foros_lista(registros):
    if not registros:
        return _mod_empty('No hay discusiones preparadas', 'Crea un tema para comenzar.', 'forums')
    elementos = []
    for r in reversed(registros):
        respuestas = r.get('respuestas') or []
        elementos.append(html.Div(className='ut-thread', children=[
            html.Div(className='ut-thread-top', children=[
                html.Span(r.get('categoria', 'General'), className='ut-pill'),
                html.Span(f'{len(respuestas)} respuestas', className='ut-row-meta')
            ]),
            html.H3(r.get('titulo', ''), className='ut-row-title'),
            html.P(r.get('descripcion', ''), className='ut-thread-description'),
            html.Div([html.P('↳ ' + str(v), className='ut-reply') for v in respuestas]) if respuestas else None
        ]))
    return html.Div(elementos)


# 5) MENSAJES: bandeja de borradores sin envío ni acceso a buzones de Moodle.
def render_mensajes():
    return html.Div(className='ut-page', children=[
        _mod_hero('COMUNICACIÓN', 'Mensajes',
                  'Redacta comunicaciones, organiza borradores y conserva ideas de seguimiento.', 'messages'),
        _mod_notice('Esta pantalla no envía mensajes a Moodle ni a correos. Todo lo guardado son borradores de tu navegador.', 'messages'),
        _mod_card('Redactar mensaje', html.Div(children=[
            html.Div(className='ut-form-grid', children=[
                _mod_field('Destinatario / Referencia', _input('mensaje-destinatario', 'Ej. Grupo DSM 2026')),
                _mod_field('Asunto', _input('mensaje-asunto', 'Asunto del mensaje'))
            ]),
            _mod_field('Mensaje', dcc.Textarea(id='mensaje-texto', placeholder='Escribe tu mensaje...', className='ut-textarea')),
            html.Div(className='ut-form-footer', children=[
                html.Button('Guardar borrador', id='mensaje-guardar', n_clicks=0, className='ut-btn'),
                html.Span(id='mensaje-feedback', className='ut-feedback', role='status')
            ])
        ]), 'Prepara tus mensajes antes de enviarlos por un canal institucional.'),
        _mod_card('Bandeja personal', html.Div(children=[
            dcc.RadioItems(id='mensaje-filtro', options=_opciones(['Borradores', 'Archivados']),
                           value='Borradores', inline=True, className='ut-radio'),
            html.Div(id='mensaje-listado'),
            html.Div(className='ut-inline-action', children=[
                dcc.Dropdown(id='mensaje-seleccionar', options=[], placeholder='Selecciona un borrador...',
                             className='custom-dropdown', style={'flex': '1 1 240px'}),
                html.Button('Archivar', id='mensaje-archivar', n_clicks=0, className='ut-btn ut-btn-outline')
            ])
        ]), 'Los mensajes archivados siguen disponibles en esta sesión.')
    ])


def _render_mensajes_lista(registros, filtro):
    estado = 'Archivados' if filtro == 'Archivados' else 'Borradores'
    seleccionados = [r for r in registros if r.get('estado', 'Borradores') == estado]
    if not seleccionados:
        return _mod_empty('No hay mensajes en esta bandeja',
                          'Guarda un borrador para comenzar a organizar tus comunicaciones.', 'messages')
    return html.Div(children=[
        html.Div(className='ut-list-row', children=[
            html.Div(className='ut-row-icon', children=get_svg_icon('messages', '#26e0a2')),
            html.Div(style={'flex': '1', 'minWidth': 0}, children=[
                html.H4(m.get('asunto', ''), className='ut-row-title'),
                html.P('Para: ' + m.get('destinatario', ''), className='ut-row-meta'),
                html.P(m.get('texto', ''), className='ut-preview')
            ]),
            html.Span('Archivado' if estado == 'Archivados' else 'Sin enviar', className='ut-pill')
        ]) for m in reversed(seleccionados)
    ])


# 6) CONFIGURACIÓN: opciones de presentación persistentes por sesión.
def render_configuracion():
    df = obtener_datos_procesados()
    registros = len(df) if not df.empty else 0
    ultima_fecha = 'Pendiente de sincronización'
    if os.path.exists(JSON_FILE_PATH):
        try:
            with open(JSON_FILE_PATH, encoding='utf-8') as archivo:
                ultima_fecha = json.load(archivo).get('last_synced') or 'Sin fecha registrada'
        except (OSError, ValueError, TypeError):
            ultima_fecha = 'Fecha no disponible'
    return html.Div(className='ut-page', children=[
        _mod_hero('PREFERENCIAS DEL PANEL', 'Configuración',
                  'Personaliza la experiencia de navegación y consulta el estado de los datos.', 'settings'),
        _mod_card('Apariencia y movimiento', html.Div(children=[
            _mod_field('Animaciones', dcc.Checklist(id='config-animaciones',
                options=[{'label': ' Habilitar transiciones y animaciones', 'value': 'si'}],
                value=['si'], className='ut-check')),
            _mod_field('Espaciado del panel', dcc.RadioItems(id='config-densidad',
                options=[{'label': ' Cómodo', 'value': 'normal'}, {'label': ' Compacto', 'value': 'compacto'}],
                value='normal', inline=True, className='ut-radio')),
            html.P('El modo claro y oscuro se sigue controlando desde el menú lateral, como antes.',
                   className='ut-card-subtitle'),
            html.Div(className='ut-form-footer', children=[
                html.Button('Guardar preferencias', id='config-guardar', n_clicks=0, className='ut-btn'),
                html.Span(id='config-feedback', className='ut-feedback', role='status')
            ])
        ]), 'El azul institucional y los acentos verdes se conservan.'),
        _mod_card('Estado de Moodle', html.Div(className='ut-kpi-grid', children=[
            _mod_kpi('Registros cargados', registros, 'Desde la caché local de calificaciones', 'users', '#70baff'),
            _mod_kpi('Integración', 'Moodle' if _leer_catalogo().get('last_synced') else 'Sin verificar', 'Se consulta con permisos autorizados', 'curso', '#27dda0')
        ]), f'Última sincronización: {ultima_fecha}'),
        _mod_notice('Por seguridad, las credenciales y las llaves de acceso no se muestran ni se editan desde esta pantalla.')
    ])


# ============================================================
# VISTAS REALES DE MOODLE: usa solo endpoints autorizados
# ============================================================
def _identidad_para_agrupacion(df):
    """Agrupa por ID Moodle cuando está disponible; si falta, por nombre mostrado.

    El nombre no es un ID institucional ni garantiza identidad única: sirve solo
    para no descartar registros sin identificador en las estadísticas visibles.
    """
    if df.empty:
        return pd.Series(dtype=str)
    ids = (df['user_id'].astype('string').fillna('').str.strip()
           if 'user_id' in df.columns else pd.Series('', index=df.index))
    nombres = (df['nombre_alumno'].fillna('').astype(str).str.strip().str.upper()
               if 'nombre_alumno' in df.columns else pd.Series('', index=df.index))
    return ('ID:' + ids).where(ids != '', 'NOMBRE:' + nombres)


def _datos_de_inicio():
    df = obtener_datos_procesados()
    cat = _leer_catalogo()
    if not cat and df.empty:
        return {}
    notas = (pd.to_numeric(df['calificacion_final'], errors='coerce').dropna()
             if not df.empty and 'calificacion_final' in df else pd.Series(dtype=float))
    alumnos = _identidad_para_agrupacion(df).nunique() if not df.empty else 0
    # Promediar por alumno para que una persona con varios cursos no se cuente como
    # varios estudiantes en el indicador de seguimiento.
    calificados_por_alumno = pd.Series(dtype=float)
    if not df.empty and 'calificacion_final' in df:
        df_cal = df.copy()
        df_cal['calificacion_final'] = pd.to_numeric(df_cal['calificacion_final'], errors='coerce')
        df_cal = df_cal[df_cal['calificacion_final'].between(0, 10)]
        if not df_cal.empty:
            df_cal['_identidad_resumen'] = _identidad_para_agrupacion(df_cal)
            calificados_por_alumno = df_cal.groupby('_identidad_resumen')['calificacion_final'].mean()
    return {'estudiantes': int(alumnos), 'cursos': len(cat.get('courses', [])),
            'promedio': f'{float(notas.mean()):.2f}' if len(notas) else '—',
            'riesgo': int((calificados_por_alumno < 6).sum()) if not calificados_por_alumno.empty else '—',
            'ultima_sincronizacion': cat.get('last_synced') or 'Pendiente',
            'estado_sincronizacion': f'{len(notas)} calificaciones disponibles; {max(0, len(df)-len(notas))} sin nota',
            'lista_cursos': [c.get('fullname', '') for c in (cat.get('courses') or [])[:5]],
            'avisos': [f'{a.get("nombre", "Actividad")} — {a.get("curso", "")}'
                      for a in (cat.get('activities') or [])[:5]]}


def _datos_de_cursos():
    courses = _leer_catalogo().get('courses', [])
    grupos = {g for c in courses for g in (c.get('grupos') or [])}
    registros = [{'nombre': c.get('fullname'), 'division': c.get('carrera'),
                  'grupo': ', '.join(c.get('grupos') or []) or 'Sin grupo asignado',
                  'matriculados': c.get('matriculados') if c.get('matriculados') is not None else '—',
                  'estado': c.get('estado_matriculas', 'No verificado')} for c in courses]
    return {'total_cursos': len(courses),
            'total_divisiones': len({c.get('carrera') for c in courses}),
            'total_grupos': len(grupos),
            'total_matriculados': (sum(int(c['matriculados']) for c in courses if c.get('matriculados') is not None)
                                   if any(c.get('matriculados') is not None for c in courses) else None),
            'registros': registros}


def _render_participantes_moodle():
    df = obtener_datos_procesados()
    if df.empty:
        return html.Div(className='ut-page', children=[
            _mod_hero('CONSULTA ACADÉMICA', 'Participantes', 'Alumnos matriculados según Moodle.', 'users'),
            _mod_empty('Sin estudiantes sincronizados', 'Comprueba MOODLE_TOKEN y el permiso core_enrol_get_enrolled_users.', 'users')])
    cols = [c for c in ['nombre_alumno', 'carrera', 'curso', 'grupo', 'origen'] if c in df]
    filas = df[cols].drop_duplicates().fillna('').to_dict('records')
    return html.Div(className='ut-page', children=[
        _mod_hero('CONSULTA ACADÉMICA', 'Participantes',
                  'Lista de matriculaciones autorizadas extraídas de Moodle.', 'users'),
        _mod_notice('Se diferencian matrículas verificadas de registros de informes. Si no hay información sobre el grupo, se muestra SIN GRUPO ASIGNADO o GRUPO NO DISPONIBLE.', 'users'),
        html.Div(className='ut-kpi-grid', children=[
            _mod_kpi('Identidades registradas', _identidad_para_agrupacion(df).nunique(),
                     'Identidades registradas', 'users', '#55b7ff'),
            _mod_kpi('Registros por curso', len(df), 'Matrícula o reporte académico', 'curso'),
            _mod_kpi('Cursos', df['curso'].nunique(), 'Con participantes', 'chart'),
            _mod_kpi('Grupos reales', df.loc[~df['grupo'].isin(['SIN GRUPO ASIGNADO', 'GRUPO NO DISPONIBLE']), 'grupo'].nunique(),
                     'Informados por Moodle', 'users')]),
        _mod_card('Participantes por curso', dash_table.DataTable(
            id='tabla-participantes', columns=[{'id': c, 'name': {'nombre_alumno': 'Estudiante',
              'carrera': 'División', 'curso': 'Curso', 'grupo': 'Grupo', 'origen': 'Fuente'}.get(c, c)} for c in cols],
            data=filas, filter_action='native', sort_action='native', export_format='csv',
            page_size=15, style_table={'overflowX': 'auto'},
            style_header={'backgroundColor': '#12284a', 'color': 'white', 'padding': '12px'},
            style_cell={'backgroundColor': 'var(--card-bg)', 'color': 'var(--text-color)',
                        'padding': '10px', 'textAlign': 'left', 'border': '1px solid var(--border-color)'}),
            'Filtra directamente en la tabla. La exportación contiene los resultados visibles.')])


def render_participantes():
    """Conserva la pantalla anterior cuando esta disponible; no depende de otro archivo."""
    principal = _render_participantes_moodle()
    if _render_participantes_original is None:
        return principal
    try:
        adicional = _render_participantes_original()
        return html.Div(children=[principal, adicional])
    except Exception as exc:
        _logger.warning('Interfaz anterior de participantes no disponible: %s', type(exc).__name__)
        return principal


def _tabla_moodle_rows(rows, cols, limit=150):
    if not rows:
        return _mod_empty('No hay registros disponibles',
                          'Es posible que falten permisos para consultar este módulo.')
    return dash_table.DataTable(data=rows[:limit],
        columns=[{'name': label, 'id': key, 'presentation': 'markdown' if key == 'enlace' else 'input'}
                 for key, label in cols], page_size=12, sort_action='native', filter_action='native',
        style_table={'overflowX': 'auto'},
        style_header={'backgroundColor': '#12284a', 'color': '#fff', 'padding': '12px'},
        style_cell={'backgroundColor': 'var(--card-bg)', 'color': 'var(--text-color)',
                    'padding': '12px', 'textAlign': 'left', 'border': '1px solid var(--border-color)',
                    'maxWidth': '320px', 'whiteSpace': 'normal'})


def _convertir_catalogo_rows(kind):
    cat = _leer_catalogo()
    rows = cat.get(kind, []) or []
    output = []
    for row in rows:
        fecha = ''
        if row.get('fecha'):
            try:
                fecha = datetime.fromtimestamp(float(row['fecha']), tz=timezone.utc).strftime('%d/%m/%Y')
            except (ValueError, TypeError, OverflowError):
                pass
        url = _safe_link(row.get('url'))
        output.append({'nombre': row.get('nombre', ''), 'curso': row.get('curso', ''),
                       'tipo': row.get('tipo', ''), 'fecha': fecha,
                       'enlace': f'[Abrir en Moodle]({url})' if url else 'No disponible'})
    return output


_base_render_actividades = render_actividades
_base_render_recursos = render_recursos
_base_render_foros = render_foros
_base_render_mensajes = render_mensajes
_base_render_configuracion = render_configuracion


def _resumen_kpis_catalogo(rows, nombre, icono):
    """Contadores respaldados por registros de contenidos de Moodle, no estimaciones."""
    cursos = len({str(x.get('curso')) for x in rows if x.get('curso')})
    tipos = len({str(x.get('tipo')) for x in rows if x.get('tipo')})
    enlaces = sum(bool(_safe_link(x.get('url'))) for x in rows)
    return html.Div(className='ut-kpi-grid', children=[
        _mod_kpi(nombre, len(rows), 'Registros publicados en cursos accesibles', icono),
        _mod_kpi('Cursos vinculados', cursos, 'Cursos con registros consultables', 'curso', '#6eb8ff'),
        _mod_kpi('Tipos disponibles', tipos, 'Categorías reales de Moodle', 'chart', '#39d49f'),
        _mod_kpi('Enlaces disponibles', enlaces, 'Enlaces institucionales identificados', 'resources', '#e5b96e')
    ])


def render_actividades():
    page = _base_render_actividades()
    raw = _leer_catalogo().get('activities', []) or []
    rows = _convertir_catalogo_rows('activities')
    page.children.insert(2, _resumen_kpis_catalogo(raw, 'Actividades', 'activities'))
    page.children.insert(3, _mod_card('Actividades reales de Moodle',
        _tabla_moodle_rows(rows, [('nombre','Actividad'),('curso','Curso'),('tipo','Tipo'),
                                  ('fecha','Fecha registrada'),('enlace','Abrir')]),
        'Actividades publicadas en cursos accesibles; no significa que estén pendientes o entregadas.'))
    return page


def render_recursos():
    page = _base_render_recursos()
    raw = _leer_catalogo().get('resources', []) or []
    rows = _convertir_catalogo_rows('resources')
    page.children.insert(2, _resumen_kpis_catalogo(raw, 'Recursos', 'resources'))
    page.children.insert(3, _mod_card('Materiales publicados en Moodle',
        _tabla_moodle_rows(rows, [('nombre','Material'),('curso','Curso'),('tipo','Tipo'),('enlace','Abrir')]),
        'Los enlaces protegidos requieren una sesión institucional válida en Moodle.'))
    return page


def render_foros():
    page = _base_render_foros()
    raw = _leer_catalogo().get('forums', []) or []
    rows = _convertir_catalogo_rows('forums')
    page.children.insert(2, _resumen_kpis_catalogo(raw, 'Foros', 'forums'))
    page.children.insert(3, _mod_card('Foros existentes en Moodle',
        _tabla_moodle_rows(rows, [('nombre','Foro'),('curso','Curso'),('enlace','Abrir')]),
        'Se muestran foros existentes. El número de respuestas requiere permisos adicionales; los borradores no se publican.'))
    return page


def render_mensajes():
    page = _base_render_mensajes()
    page.children.insert(2, _mod_notice('La mensajería privada de Moodle NO se consulta con el token administrativo. '
        'Para habilitarla se requiere vincular la identidad y permisos del usuario en una integración separada.', 'messages'))
    return page


def render_configuracion():
    page = _base_render_configuracion()
    cat = _leer_catalogo()
    items = [f'Última sincronización: {cat.get("last_synced", "Pendiente")}',
             f'Cursos consultados: {cat.get("cursos_consultados", 0)}',
             f'Matriculaciones verificadas: {cat.get("total_matriculas", 0)}',
             f'Registros de notas sin matrícula confirmada: {cat.get("registros_solo_reporte", 0)}',
             f'Notas recuperadas: {cat.get("calificaciones_disponibles", 0)}',
             f'Consultas de notas: {cat.get("consultas_notas", 0)}',
             f'Cursos con permiso de matrícula: {cat.get("cursos_matriculas_consultadas", 0)}',
             f'Cursos sin matrícula verificable: {cat.get("matriculas_por_consultar", 0)}',
             f'Actividades de Moodle: {len(cat.get("activities") or [])}',
             f'Recursos de Moodle: {len(cat.get("resources") or [])}',
             f'Foros de Moodle: {len(cat.get("forums") or [])}',
             'Estado del token: configurado' if os.environ.get('MOODLE_TOKEN') else 'Token Moodle: FALTA',
             'Errores en última sincronización: ' + str(len(cat.get('errores') or []))]
    error_items = cat.get('errores') or []
    page.children.append(_mod_card('Diagnóstico de conexión Moodle', html.Div([
        html.Ul([html.Li(x) for x in items], style={'color': 'var(--text-color)'}),
        html.H4('Advertencias / funciones no disponibles', style={'color':'var(--text-color)'}),
        html.Ul([html.Li(x) for x in error_items[:12]], style={'color': 'var(--text-muted)'})
        if error_items else html.P('No se registraron errores en la última sincronización.',
                                   style={'color': 'var(--text-muted)'})]),
        'Solo se muestran diagnósticos, nunca credenciales.'))
    return page


@app.callback(Output('cursos-tabla', 'data'),
              Input('cursos-filtro-division', 'value'), Input('cursos-filtro-grupo', 'value'),
              Input('cursos-buscar', 'value'))
def actualizar_tabla_cursos(division, grupo, buscar):
    rows = _datos_de_cursos().get('registros', [])
    if division:
        rows = [r for r in rows if r['division'] == division]
    if grupo:
        rows = [r for r in rows if grupo in r.get('grupo', '').split(', ')]
    if buscar:
        rows = [r for r in rows if str(buscar).lower() in str(r.get('nombre','')).lower()]
    return rows


# Callbacks de los nuevos módulos: ninguna acción publica en Moodle.
@app.callback(
    Output('calif-contenido', 'children'),
    Input('calif-filtro-carrera', 'value'), Input('calif-filtro-curso', 'value'),
    Input('calif-filtro-grupo', 'value'), Input('calif-buscar', 'value')
)
def ut_actualizar_calificaciones(carrera, curso, grupo, buscar):
    return _estadisticas_calificaciones(carrera, curso, grupo, buscar)


@app.callback(
    Output('actividades-borradores', 'data'), Output('actividad-feedback', 'children'),
    Input('actividad-guardar', 'n_clicks'), Input('actividad-completar', 'n_clicks'),
    State('actividad-titulo', 'value'), State('actividad-curso', 'value'),
    State('actividad-fecha', 'date'), State('actividad-prioridad', 'value'),
    State('actividad-seleccionar', 'value'), State('actividades-borradores', 'data'),
    prevent_initial_call=True
)
def ut_guardar_actividad(clicks_guardar, clicks_terminar, titulo, curso, fecha, prioridad, seleccion, registros):
    registros = list(registros or [])
    origen = dash.ctx.triggered_id
    if origen == 'actividad-guardar':
        if not titulo or not str(titulo).strip():
            return dash.no_update, 'Escribe el título de la actividad.'
        registros.append({'id': f'a-{time.time_ns()}', 'titulo': str(titulo).strip()[:180],
                          'curso': curso, 'fecha': fecha, 'prioridad': prioridad or 'Media',
                          'estado': 'Pendiente'})
        return registros, 'Actividad guardada en tu sesión.'
    if origen == 'actividad-completar':
        if not seleccion:
            return dash.no_update, 'Selecciona primero una actividad pendiente.'
        for registro in registros:
            if registro.get('id') == seleccion:
                registro['estado'] = 'Terminada'
                return registros, 'Actividad marcada como terminada.'
        return dash.no_update, 'No se encontró la actividad.'
    return dash.no_update, dash.no_update


@app.callback(
    Output('actividad-listado', 'children'), Output('actividad-seleccionar', 'options'),
    Input('actividades-borradores', 'data')
)
def ut_listar_actividades(registros):
    registros = registros or []
    pendientes = [a for a in registros if a.get('estado') != 'Terminada']
    return _render_actividad_lista(registros), [
        {'label': a.get('titulo', ''), 'value': a.get('id')} for a in pendientes
    ]


@app.callback(
    Output('recursos-borradores', 'data'), Output('recurso-feedback', 'children'),
    Input('recurso-guardar', 'n_clicks'),
    State('recurso-titulo', 'value'), State('recurso-enlace', 'value'),
    State('recurso-tipo', 'value'), State('recursos-borradores', 'data'),
    prevent_initial_call=True
)
def ut_guardar_recurso(clicks, titulo, enlace, tipo, registros):
    if not clicks:
        return dash.no_update, dash.no_update
    if not titulo or not str(titulo).strip():
        return dash.no_update, 'Indica el título del recurso.'
    enlace = str(enlace or '').strip()
    parsed = urllib.parse.urlparse(enlace)
    if parsed.scheme not in ('http', 'https') or not parsed.netloc:
        return dash.no_update, 'Ingresa una URL válida que comience con https:// o http://.'
    registros = list(registros or [])
    registros.append({'id': f'r-{time.time_ns()}', 'titulo': str(titulo).strip()[:180],
                      'enlace': enlace, 'tipo': tipo or 'Otro'})
    return registros, 'Recurso guardado en tu sesión.'


@app.callback(Output('recurso-listado', 'children'), Input('recursos-borradores', 'data'))
def ut_listar_recursos(registros):
    return _render_recursos_lista(registros or [])


@app.callback(
    Output('foros-borradores', 'data'), Output('foro-feedback', 'children'),
    Input('foro-crear', 'n_clicks'), Input('foro-responder', 'n_clicks'),
    State('foro-titulo', 'value'), State('foro-categoria', 'value'),
    State('foro-descripcion', 'value'), State('foro-seleccionar', 'value'),
    State('foro-respuesta', 'value'), State('foros-borradores', 'data'),
    prevent_initial_call=True
)
def ut_guardar_foro(clicks_crear, clicks_responder, titulo, categoria, descripcion, seleccion, respuesta, registros):
    registros = list(registros or [])
    origen = dash.ctx.triggered_id
    if origen == 'foro-crear':
        if not titulo or not str(titulo).strip() or not descripcion or not str(descripcion).strip():
            return dash.no_update, 'Escribe un título y una descripción.'
        registros.append({'id': f'f-{time.time_ns()}', 'titulo': str(titulo).strip()[:180],
                          'categoria': categoria or 'General', 'descripcion': str(descripcion).strip()[:4000],
                          'respuestas': []})
        return registros, 'Discusión guardada como borrador.'
    if origen == 'foro-responder':
        if not seleccion or not respuesta or not str(respuesta).strip():
            return dash.no_update, 'Selecciona una discusión y redacta la respuesta.'
        for r in registros:
            if r.get('id') == seleccion:
                r.setdefault('respuestas', []).append(str(respuesta).strip()[:2000])
                return registros, 'Respuesta guardada en esta sesión.'
        return dash.no_update, 'No se encontró la discusión.'
    return dash.no_update, dash.no_update


@app.callback(
    Output('foro-listado', 'children'), Output('foro-seleccionar', 'options'),
    Input('foros-borradores', 'data')
)
def ut_listar_foros(registros):
    registros = registros or []
    return _render_foros_lista(registros), [
        {'label': r.get('titulo', ''), 'value': r.get('id')} for r in registros
    ]


@app.callback(
    Output('mensajes-borradores', 'data'), Output('mensaje-feedback', 'children'),
    Input('mensaje-guardar', 'n_clicks'), Input('mensaje-archivar', 'n_clicks'),
    State('mensaje-destinatario', 'value'), State('mensaje-asunto', 'value'),
    State('mensaje-texto', 'value'), State('mensaje-seleccionar', 'value'),
    State('mensajes-borradores', 'data'), prevent_initial_call=True
)
def ut_guardar_mensaje(clicks_guardar, clicks_archivar, destino, asunto, cuerpo, seleccion, registros):
    registros = list(registros or [])
    origen = dash.ctx.triggered_id
    if origen == 'mensaje-guardar':
        if not asunto or not str(asunto).strip() or not cuerpo or not str(cuerpo).strip():
            return dash.no_update, 'Escribe el asunto y el mensaje.'
        registros.append({'id': f'm-{time.time_ns()}', 'destinatario': str(destino or 'Sin destinatario')[:180],
                          'asunto': str(asunto).strip()[:180], 'texto': str(cuerpo).strip()[:5000],
                          'estado': 'Borradores'})
        return registros, 'Borrador guardado. No se ha enviado.'
    if origen == 'mensaje-archivar':
        if not seleccion:
            return dash.no_update, 'Selecciona un borrador para archivarlo.'
        for r in registros:
            if r.get('id') == seleccion:
                r['estado'] = 'Archivados'
                return registros, 'Mensaje archivado.'
        return dash.no_update, 'No se encontró el mensaje.'
    return dash.no_update, dash.no_update


@app.callback(
    Output('mensaje-listado', 'children'), Output('mensaje-seleccionar', 'options'),
    Input('mensajes-borradores', 'data'), Input('mensaje-filtro', 'value')
)
def ut_listar_mensajes(registros, filtro):
    registros = registros or []
    borradores = [r for r in registros if r.get('estado') == 'Borradores']
    return _render_mensajes_lista(registros, filtro), [
        {'label': r.get('asunto', ''), 'value': r.get('id')} for r in borradores
    ] if filtro == 'Borradores' else []


@app.callback(
    Output('ui-preferencias-store', 'data'), Output('config-feedback', 'children'),
    Input('config-guardar', 'n_clicks'), State('config-animaciones', 'value'),
    State('config-densidad', 'value'), prevent_initial_call=True
)
def ut_guardar_configuracion(clicks, animaciones, densidad):
    if not clicks:
        return dash.no_update, dash.no_update
    return {'animaciones': 'si' in (animaciones or []),
            'densidad': 'compacto' if densidad == 'compacto' else 'normal'}, 'Preferencias guardadas.'


@app.callback(Output('page-content', 'className'), Input('ui-preferencias-store', 'data'))
def ut_aplicar_configuracion(preferencias):
    preferencias = preferencias or {}
    clases = ['ut-main-content']
    if not preferencias.get('animaciones', True):
        clases.append('ui-motion-off')
    if preferencias.get('densidad') == 'compacto':
        clases.append('ui-compact')
    return ' '.join(clases)


@app.callback(
    Output('config-animaciones', 'value'), Output('config-densidad', 'value'),
    Input('config-densidad', 'id'), State('ui-preferencias-store', 'data')
)
def ut_cargar_configuracion(_montado, preferencias):
    preferencias = preferencias or {}
    return (['si'] if preferencias.get('animaciones', True) else [],
            preferencias.get('densidad', 'normal'))


@app.callback(
    Output('actividades-borradores', 'data', allow_duplicate=True),
    Output('recursos-borradores', 'data', allow_duplicate=True),
    Output('foros-borradores', 'data', allow_duplicate=True),
    Output('mensajes-borradores', 'data', allow_duplicate=True),
    Input('auth-store', 'data'), prevent_initial_call=True
)
def ut_limpiar_borradores_al_cerrar_sesion(auth_data):
    """Evita que un usuario posterior del mismo navegador lea los borradores anteriores."""
    if auth_data and auth_data.get('logged_in'):
        return (dash.no_update,) * 4
    return [], [], [], []


#Layout principal
app.layout = html.Div(id='main-container', className='dark-theme', children=[
    dcc.Location(id='url', refresh=False),
    dcc.Store(id='theme-store', data='dark', storage_type='session'),
    dcc.Store(id='auth-store', data={'logged_in': False, 'role': None, 'username': None}, storage_type='session'),
    # Datos de las seis interfaces nuevas: almacenamiento aislado por sesión.
    dcc.Store(id='actividades-borradores', data=[], storage_type='session'),
    dcc.Store(id='recursos-borradores', data=[], storage_type='session'),
    dcc.Store(id='foros-borradores', data=[], storage_type='session'),
    dcc.Store(id='mensajes-borradores', data=[], storage_type='session'),
    dcc.Store(id='ui-preferencias-store', data={'animaciones': True, 'densidad': 'normal'}, storage_type='session'),
    dcc.Interval(id='trigger-inicial', interval=30000, n_intervals=0, disabled=False), 
    html.Div(id='sidebar-container', style={'display': 'none'}, children=[render_sidebar()]),
    html.Div(id='page-content', style={'padding': '40px', 'backgroundColor': 'var(--bg-color)', 'minHeight': '100vh'})
])

def render_panel_principal():
    return html.Div(children=[
        html.Div(style={'borderBottom': '1px solid var(--border-color)', 'paddingBottom': '20px', 'marginBottom': '30px', 'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center'}, children=[
            html.Div(children=[
                html.H1("Analítica del curso", style={'margin': '0', 'color': 'var(--text-color)', 'fontWeight': '700', 'fontSize': '28px'}),
                html.P("Visualiza el desempeño y avance de los estudiantes", style={'margin': '5px 0 0 0', 'color': 'var(--text-muted)', 'fontSize': '14px'})
            ]),
            html.Div(id='user-profile-header', className='d-flex align-items-center gap-2')
        ]),
        

        #Selectores
        html.Div(style={
            'display': 'flex',
            'gap': '20px',
            'backgroundColor': 'var(--card-bg)',
            'padding': '20px',
            'borderRadius': '12px',
            'border': '1px solid var(--border-color)',
            'marginBottom': '30px'
        }, children=[
            html.Div(style={'flex': '1'}, children=[
                html.Label("División / Carrera:", style={'fontWeight': '600', 'display': 'block', 'marginBottom': '8px', 'color': 'var(--text-muted)', 'fontSize': '12px', 'textTransform': 'uppercase', 'letterSpacing': '1px'}),
                dcc.Dropdown(id='carrera-dropdown', placeholder="Sincronizando con Moodle...", className='custom-dropdown', persistence=True, persistence_type='session')
            ]),
            html.Div(style={'flex': '1'}, children=[
                html.Label("Curso Moodle:", style={'fontWeight': '600', 'display': 'block', 'marginBottom': '8px', 'color': 'var(--text-muted)', 'fontSize': '12px', 'textTransform': 'uppercase', 'letterSpacing': '1px'}),
                dcc.Dropdown(id='curso-dropdown', placeholder="Seleccione una carrera...", className='custom-dropdown', persistence=True, persistence_type='session')
            ]),
            html.Div(style={'flex': '1'}, children=[
                html.Label("Grupo Académico:", style={'fontWeight': '600', 'display': 'block', 'marginBottom': '8px', 'color': 'var(--text-muted)', 'fontSize': '12px', 'textTransform': 'uppercase', 'letterSpacing': '1px'}),
                dcc.Dropdown(id='grupo-dropdown', placeholder="Seleccione un curso...", className='custom-dropdown', persistence=True, persistence_type='session')
            ]),
            html.Div(style={'flex': '1'}, children=[
                html.Label("Buscar Estudiante:", style={'fontWeight': '600', 'display': 'block', 'marginBottom': '8px', 'color': 'var(--text-muted)', 'fontSize': '12px', 'textTransform': 'uppercase', 'letterSpacing': '1px'}),
                dcc.Dropdown(id='busqueda-input', placeholder="Escribe nombre...", className='custom-dropdown', persistence=True, persistence_type='session', searchable=True, clearable=True)
            ]),
        ]),

        html.Div(id='mensaje-estado-container', style={'textAlign': 'center', 'marginBottom': '20px'}),

        # Tarjetas de métricas (KPIs)
        html.Div(style={'display': 'flex', 'gap': '20px', 'marginBottom': '30px'}, children=[
            html.Div(className='metric-card', style={'flex': '1', 'backgroundColor': 'var(--card-bg)', 'padding': '20px', 'borderRadius': '12px', 'border': '1px solid var(--border-color)', 'position': 'relative', 'overflow': 'hidden'}, children=[
                html.P("Estudiantes con registro", style={'margin': '0', 'color': 'var(--text-muted)', 'fontSize': '14px', 'fontWeight': '500'}),
                html.H3(id='metric-total', children="0", style={'margin': '8px 0 0 0', 'fontSize': '28px', 'fontWeight': '700', 'color': 'var(--text-color)'}),
                html.P("100% del subgrupo", style={'margin': '4px 0 0 0', 'fontSize': '12px', 'color': 'var(--accent-color)'})
            ]),
            html.Div(className='metric-card', style={'flex': '1', 'backgroundColor': 'var(--card-bg)', 'padding': '20px', 'borderRadius': '12px', 'border': '1px solid var(--border-color)', 'position': 'relative', 'overflow': 'hidden'}, children=[
                html.P("Promedio General", style={'margin': '0', 'color': 'var(--text-muted)', 'fontSize': '14px', 'fontWeight': '500'}),
                html.H3(id='metric-promedio', children="0.0", style={'margin': '8px 0 0 0', 'fontSize': '28px', 'fontWeight': '700', 'color': 'var(--accent-color)'}),
                html.P("Escala UTTEC (0-10)", style={'margin': '4px 0 0 0', 'fontSize': '12px', 'color': 'var(--text-muted)'})
            ]),
            html.Div(className='metric-card', style={'flex': '1', 'backgroundColor': 'var(--card-bg)', 'padding': '20px', 'borderRadius': '12px', 'border': '1px solid var(--border-color)', 'position': 'relative', 'overflow': 'hidden'}, children=[
                html.P("Aprobados (>= 6.0)", style={'margin': '0', 'color': 'var(--text-muted)', 'fontSize': '14px', 'fontWeight': '500'}),
                html.H3(id='metric-aprobados', children="0", style={'margin': '8px 0 0 0', 'fontSize': '28px', 'fontWeight': '700', 'color': COLOR_VERDE_BANDERA}),
                html.P(id='metric-aprobados-pct', children="0% del total", style={'margin': '4px 0 0 0', 'fontSize': '12px', 'color': COLOR_VERDE_BANDERA})
            ]),
            html.Div(className='metric-card', style={'flex': '1', 'backgroundColor': 'var(--card-bg)', 'padding': '20px', 'borderRadius': '12px', 'border': '1px solid var(--border-color)', 'position': 'relative', 'overflow': 'hidden'}, children=[
                html.P("En Riesgo (< 6.0)", style={'margin': '0', 'color': 'var(--text-muted)', 'fontSize': '14px', 'fontWeight': '500'}),
                html.H3(id='metric-riesgo', children="0", style={'margin': '8px 0 0 0', 'fontSize': '28px', 'fontWeight': '700', 'color': '#FF4D4D'}),
                html.P(id='metric-riesgo-pct', children="0% del total", style={'margin': '4px 0 0 0', 'fontSize': '12px', 'color': '#FF4D4D'})
            ])
        ]),

        # graficos
        html.Div(style={'display': 'flex', 'gap': '25px', 'marginBottom': '30px'}, children=[
            html.Div(style={'width': '40%', 'backgroundColor': 'var(--card-bg)', 'padding': '25px', 'borderRadius': '12px', 'border': '1px solid var(--border-color)'}, children=[
                dcc.Graph(id='grafico-pastel-general', config={'displayModeBar': False, 'responsive': True})
            ]),
            html.Div(style={'width': '60%', 'backgroundColor': 'var(--card-bg)', 'padding': '25px', 'borderRadius': '12px', 'border': '1px solid var(--border-color)'}, children=[
                dcc.Graph(id='grafico-barras-general', config={'displayModeBar': False, 'responsive': True})
            ])
        ]),

        html.Div(style={'backgroundColor': 'var(--card-bg)', 'padding': '25px', 'borderRadius': '12px', 'border': '1px solid var(--border-color)'}, children=[
            html.H3("Rendimiento Nominal de Estudiantes Matriculados", style={'color': 'var(--accent-color)', 'marginTop': '0', 'marginBottom': '20px', 'fontSize': '18px', 'fontWeight': '600'}),
            html.Div(id='tabla-alumnos-container')
        ])
    ])

def render_panel_individual(nombre_alumno, theme_class='dark-theme', curso_seleccionado=None, division_seleccionada=None):
    is_light = (theme_class == 'light-theme')
    plotly_template = 'plotly_white' if is_light else 'plotly_dark'
    text_color = '#000B52' if is_light else '#ffffff'
    grid_color = '#dce3f0' if is_light else '#1e293b'

    df = obtener_datos_procesados()
    if df.empty: 
        return html.Div(style={'padding': '40px', 'textAlign': 'center'}, children=[
            html.H2("Cargando base de datos...", style={'color': 'var(--accent-color)'}),
            dcc.Link("Volver a la vista general", href="/", style={'color': 'var(--accent-color)', 'fontWeight': 'bold', 'textDecoration': 'none'})
        ])
    
    # Normalización para búsqueda insensible a mayúsculas y espacios
    nombre_limpio = urllib.parse.unquote(str(nombre_alumno)).strip().lower()
    df_nombres_norm = df['nombre_alumno'].astype(str).str.strip().str.lower()

    # lectura del curso en el perfil
    if curso_seleccionado and division_seleccionada:
        registro = df[(df_nombres_norm == nombre_limpio) & (df['curso'] == curso_seleccionado) & (df['carrera'] == division_seleccionada)]
        if registro.empty:
            registro = df[(df_nombres_norm == nombre_limpio) & (df['curso'] == curso_seleccionado)]
    elif curso_seleccionado:
        registro = df[(df_nombres_norm == nombre_limpio) & (df['curso'] == curso_seleccionado)]
        
    if 'registro' not in locals() or registro.empty:
        registro = df[df_nombres_norm == nombre_limpio]
        
    if registro.empty: 
        return html.Div(style={'padding': '40px', 'textAlign': 'center'}, children=[
            html.H3("No se encontraron datos para este estudiante", style={'color': '#FF4D4D'}),
            dcc.Link("Volver a la vista general", href="/", style={'color': 'var(--accent-color)', 'fontWeight': 'bold', 'textDecoration': 'none'})
        ])
    
    try:
        datos = registro.iloc[0]
        nota = datos['calificacion_final']
        if pd.isna(nota) or not (0 <= float(nota) <= 10):
            return html.Div(className='ut-page', children=[
                _mod_hero('PERFIL ACADÉMICO', str(nombre_alumno),
                    'El alumno aparece matriculado, pero Moodle no proporcionó su nota final.', 'users'),
                _mod_empty('Sin calificación final', 'No se utilizarán ceros ni notas simuladas.', 'calificaciones'),
                dcc.Link('Volver a analítica', href='/', style={'color':'var(--accent-color)'})])
        carrera = division_seleccionada if division_seleccionada else datos['carrera']
        curso = curso_seleccionado if curso_seleccionado else datos['curso']
        grupo = datos['grupo']
        
        #calcular promedios del grupo
        df_grupo = df[(df['curso'] == curso) & (df['grupo'] == grupo)]
        notas_grupo = pd.to_numeric(df_grupo['calificacion_final'], errors='coerce').dropna()
        promedio_grupo = float(notas_grupo.mean()) if not notas_grupo.empty else float('nan')
        calif_max = float(notas_grupo.max()) if not notas_grupo.empty else float('nan')
        
        estatus = "Aprobado" if nota >= 6.0 else "Riesgo"
        color_estatus = COLOR_VERDE_BANDERA if nota >= 6.0 else "#FF4D4D"
        
        # Iniciales de avatar 
        partes = nombre_alumno.split()
        iniciales = "".join([p[0] for p in partes if p][:2])
    
        #segmentación del grupo propedéutico para la vista individual
        info_grupo_text = ""
        es_propedeutico = "PROPEDÉUTICO" in curso or "PROP" in curso
        if grupo and grupo != "SIN GRUPO ASIGNADO" and es_propedeutico:
            parts = grupo.split()
            if len(parts) >= 2:
                siglas = parts[0]
                bloques = parts[1].split('-')
                if len(bloques) == 3:
                    anio = bloques[0]
                    cuatrimestre = bloques[1]
                    recursamiento_val = int(bloques[2]) if bloques[2].isdigit() else None
                    carrera_name = "Desarrollo de Software Multiplataforma" if siglas == "DSM" else "Infraestructura de Redes Digitales" if siglas == "IRD" else siglas
                    recursamiento_text = ("Ordinario" if recursamiento_val == 1
                                           else f"Recursamiento ({recursamiento_val}a vez)" if recursamiento_val is not None
                                           else 'Periodo no especificado')
                    info_grupo_text = f" | Segmento: {carrera_name} (Ingreso {anio}, Cuatri {cuatrimestre}, {recursamiento_text})"
    
        #Contenedor de carga para OpenAI
        ia_container = dcc.Loading(
            id="loading-ia",
            type="circle",
            color=COLOR_VERDE_BANDERA,
            children=html.Div(id="diagnostico-ia-target")
        )
    
        # Serie académica REAL. Nunca se generan notas sintéticas por unidad.
        items = datos.get('items_calificados') if isinstance(datos.get('items_calificados'), list) else []
        df_progreso_indiv = pd.DataFrame(items)
        if not df_progreso_indiv.empty:
            fig_indiv_progreso = px.line(df_progreso_indiv, x='nombre', y='calificacion', markers=True,
                title='Calificaciones de actividades disponibles en Moodle', template=plotly_template)
        else:
            fig_indiv_progreso = px.scatter(title='Actividades sin información de notas', template=plotly_template)
            fig_indiv_progreso.add_annotation(text='Moodle no entregó calificaciones desglosadas por actividad',
                xref='paper',yref='paper',x=.5,y=.5,showarrow=False)
        fig_indiv_progreso.update_layout(plot_bgcolor='rgba(0,0,0,0)',paper_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=20,r=20,t=35,b=35),font_color=text_color,
                yaxis=dict(range=[0,10.5],gridcolor=grid_color), xaxis=dict(gridcolor=grid_color))

        comparativos = [('Calificación Alumno', round(float(nota), 1))]
        if pd.notna(promedio_grupo):
            comparativos.append(('Promedio Grupo', round(promedio_grupo, 1)))
        if pd.notna(calif_max):
            comparativos.append(('Nota Máxima Grupo', round(calif_max, 1)))
        df_comp_indiv = pd.DataFrame(comparativos, columns=['Métrica', 'Puntaje'])
        
        fig_indiv_comparativa = px.bar(
            df_comp_indiv,
            x='Métrica',
            y='Puntaje',
            color='Métrica',
            color_discrete_map={
                'Calificación Alumno': COLOR_VERDE_BANDERA,
                'Promedio Grupo': '#94a3b8' if is_light else '#64748b',
                'Nota Máxima Grupo': '#000B52' if is_light else '#002B66'
            },
            text='Puntaje',
            title="Rendimiento Alumno vs. Referentes de Grupo",
            template=plotly_template
        )
        fig_indiv_comparativa.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=20, r=20, t=30, b=30),
            font=dict(family="Outfit, sans-serif", color=text_color),
            yaxis=dict(range=[0, 10.5], gridcolor=grid_color),
            xaxis=dict(gridcolor=grid_color),
            showlegend=False
        )
    
        return html.Div(children=[
            dcc.Link("Volver a la vista general", href="/", style={'color': 'var(--accent-color)', 'fontWeight': '600', 'textDecoration': 'none', 'display': 'inline-flex', 'alignItems': 'center', 'gap': '8px', 'marginBottom': '25px', 'transition': 'color 0.2s'}),
            
            #identidad del estudiante
            html.Div(style={'backgroundColor': 'var(--card-bg)', 'padding': '30px', 'borderRadius': '12px', 'border': '1px solid var(--border-color)', 'marginBottom': '30px', 'display': 'flex', 'alignItems': 'center', 'gap': '25px'}, children=[
                html.Div(style={'width': '80px', 'height': '80px', 'borderRadius': '50%', 'backgroundColor': COLOR_VERDE_BANDERA, 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center', 'color': '#ffffff', 'fontSize': '28px', 'fontWeight': '800', 'boxShadow': '0 4px 14px rgba(0, 128, 0, 0.4)'}, children=iniciales),
                html.Div(style={'flex': '1'}, children=[
                    html.Div(style={'display': 'flex', 'alignItems': 'center', 'gap': '15px'}, children=[
                        html.H2(nombre_alumno, style={'color': 'var(--text-color)', 'margin': '0', 'fontSize': '24px', 'fontWeight': '700'}),
                        html.Span("MATRICULADO", style={'backgroundColor': 'rgba(0, 128, 0, 0.15)', 'color': COLOR_VERDE_BANDERA, 'border': '1px solid rgba(0, 128, 0, 0.35)', 'padding': '2px 10px', 'borderRadius': '20px', 'fontSize': '11px', 'fontWeight': '700', 'letterSpacing': '0.5px'})
                    ]),
                    html.P(f"Carrera: {carrera}", style={'margin': '6px 0 2px 0', 'color': 'var(--text-muted)', 'fontSize': '14px'}),
                    html.P([
                        html.Strong("Asignatura Auditada: ", style={'color': 'var(--accent-color)'}), f"{curso} ",
                        html.Span(f"| Grupo: {grupo}{info_grupo_text}", style={'marginLeft': '8px'})
                    ], style={'margin': '0', 'color': 'var(--text-muted)', 'fontSize': '14px', 'fontWeight': '500'})
                ])
            ]),
    
            # KPIs del alumno
            html.Div(style={'display': 'flex', 'gap': '20px', 'marginBottom': '30px'}, children=[
                html.Div(className='metric-card', style={'flex': '1', 'backgroundColor': 'var(--card-bg)', 'padding': '20px', 'borderRadius': '12px', 'border': '1px solid var(--border-color)'}, children=[
                    html.P("Calificación Acumulada", style={'margin': '0', 'color': 'var(--text-muted)', 'fontSize': '14px', 'fontWeight': '500'}),
                    html.H3(f"{nota:.1f} pts", style={'margin': '8px 0 0 0', 'fontSize': '26px', 'fontWeight': '700', 'color': color_estatus}),
                    html.P("Escala 0.0 - 10.0", style={'margin': '4px 0 0 0', 'fontSize': '12px', 'color': 'var(--text-muted)'})
                ]),
                html.Div(className='metric-card', style={'flex': '1', 'backgroundColor': 'var(--card-bg)', 'padding': '20px', 'borderRadius': '12px', 'border': '1px solid var(--border-color)'}, children=[
                    html.P("Promedio del Grupo", style={'margin': '0', 'color': 'var(--text-muted)', 'fontSize': '14px', 'fontWeight': '500'}),
                    html.H3(f"{promedio_grupo:.1f} pts" if pd.notna(promedio_grupo) else '—', style={'margin': '8px 0 0 0', 'fontSize': '26px', 'fontWeight': '700', 'color': 'var(--text-color)'}),
                    html.P("Grupo comparativo", style={'margin': '4px 0 0 0', 'fontSize': '12px', 'color': 'var(--text-muted)'})
                ]),
                html.Div(className='metric-card', style={'flex': '1', 'backgroundColor': 'var(--card-bg)', 'padding': '20px', 'borderRadius': '12px', 'border': '1px solid var(--border-color)'}, children=[
                    html.P("Calificación Máxima", style={'margin': '0', 'color': 'var(--text-muted)', 'fontSize': '14px', 'fontWeight': '500'}),
                    html.H3(f"{calif_max:.1f} pts" if pd.notna(calif_max) else '—', style={'margin': '8px 0 0 0', 'fontSize': '26px', 'fontWeight': '700', 'color': 'var(--text-color)'}),
                    html.P("Puntaje tope actual", style={'margin': '4px 0 0 0', 'fontSize': '12px', 'color': 'var(--text-muted)'})
                ]),
                html.Div(className='metric-card', style={'flex': '1', 'backgroundColor': 'var(--card-bg)', 'padding': '20px', 'borderRadius': '12px', 'border': '1px solid var(--border-color)'}, children=[
                    html.P("Estatus Académico", style={'margin': '0', 'color': 'var(--text-muted)', 'fontSize': '14px', 'fontWeight': '500'}),
                    html.H3(estatus, style={'margin': '8px 0 0 0', 'fontSize': '26px', 'fontWeight': '700', 'color': color_estatus}),
                    html.P("Según nota de corte (6.0)", style={'margin': '4px 0 0 0', 'fontSize': '12px', 'color': 'var(--text-muted)'})
                ])
            ]),
    
            # Bloque de insights de IA 
            html.Div(className='ai-insights-card', style={'padding': '30px', 'borderRadius': '12px', 'border': '1px solid var(--border-color)', 'marginBottom': '30px'}, children=[
                html.Div(style={'display': 'flex', 'alignItems': 'center', 'gap': '10px', 'marginBottom': '20px'}, children=[
                    html.H3("Diagnóstico Pedagógico y Predicción por IA", style={'color': 'var(--accent-color)', 'margin': '0', 'fontSize': '18px', 'fontWeight': '600'})
                ]),
                ia_container
            ]),
    
            # Bloque de vsualizaciones de rendimiento individual con el diagnóstico de IA
            html.Div(style={'display': 'flex', 'gap': '25px', 'marginBottom': '30px'}, children=[
                html.Div(style={'flex': '1', 'backgroundColor': 'var(--card-bg)', 'padding': '20px', 'borderRadius': '12px', 'border': '1px solid var(--border-color)'}, children=[
                    dcc.Graph(figure=fig_indiv_progreso, config={'displayModeBar': False})
                ]),
                html.Div(style={'flex': '1', 'backgroundColor': 'var(--card-bg)', 'padding': '20px', 'borderRadius': '12px', 'border': '1px solid var(--border-color)'}, children=[
                    dcc.Graph(figure=fig_indiv_comparativa, config={'displayModeBar': False})
                ])
                ])
        ])
    except Exception as e:
        print(f"Error renderizando panel individual para {nombre_alumno}: {e}")
        return html.Div(style={'padding': '40px', 'textAlign': 'center'}, children=[
            html.H3("Ocurrió un error al cargar el perfil de este estudiante.", style={'color': '#FF4D4D'}),
            html.P('Revisa los registros del servidor.', style={'color':'var(--text-muted)', 'marginBottom':'20px'}),
            dcc.Link("Volver a la vista general", href="/", style={'color': 'var(--accent-color)', 'fontWeight': 'bold', 'textDecoration': 'none'})
        ])

def render_login_screen():
    """Inicio de sesión: campos amplios, Enter y contraseña visible/oculta."""
    input_style = {
        'width': '100%',
        'height': '54px',
        'padding': '12px 16px',
        'borderRadius': '10px',
        'border': '1px solid var(--border-color)',
        'backgroundColor': 'var(--dropdown-bg)',
        'color': 'var(--text-color)',
        'fontSize': '16px',
        'boxSizing': 'border-box'
    }
    label_style = {
        'display': 'block',
        'textAlign': 'left',
        'color': 'var(--text-color)',
        'fontSize': '15px',
        'fontWeight': '600',
        'marginBottom': '8px'
    }

    return html.Div(style={
        'display': 'flex',
        'justifyContent': 'center',
        'alignItems': 'center',
        'minHeight': '100vh',
        'padding': '24px',
        'boxSizing': 'border-box',
        'backgroundColor': 'var(--bg-color)'
    }, children=[
        html.Div(id='login-box', style={
            'backgroundColor': 'var(--card-bg)',
            'padding': '48px',
            'borderRadius': '18px',
            'boxShadow': '0 12px 40px var(--shadow-color)',
            'width': '100%',
            'maxWidth': '540px',
            'border': '1px solid var(--border-color)',
            'textAlign': 'center',
            'boxSizing': 'border-box'
        }, children=[
            html.H2('Analítica UTTEC', style={
                'color': 'var(--text-color)',
                'fontSize': '32px',
                'fontWeight': '800',
                'marginBottom': '12px'
            }),
            html.P('Inicie sesión para continuar', style={
                'color': 'var(--text-muted)',
                'fontSize': '16px',
                'marginBottom': '34px'
            }),
            html.Label('Usuario institucional', htmlFor='login-username', style=label_style),
            dcc.Input(
                id='login-username',
                type='text',
                placeholder='Ingrese su usuario',
                autoComplete='username',
                style={**input_style, 'marginBottom': '22px'}
            ),
            html.Label('Contraseña', htmlFor='login-password', style=label_style),
            html.Div(style={
                'position': 'relative',
                'marginBottom': '26px'
            }, children=[
                dcc.Input(
                    id='login-password',
                    type='password',
                    placeholder='Ingrese su contraseña',
                    autoComplete='current-password',
                    style={**input_style, 'paddingRight': '62px'}
                ),
                html.Button(
                    '👁',
                    id='toggle-password-btn',
                    type='button',
                    n_clicks=0,
                    title='Mostrar contraseña',
                    **{'aria-label': 'Mostrar u ocultar contraseña'},
                    style={
                        'position': 'absolute',
                        'right': '10px',
                        'top': '50%',
                        'transform': 'translateY(-50%)',
                        'border': 'none',
                        'backgroundColor': 'transparent',
                        'color': 'var(--text-color)',
                        'fontSize': '24px',
                        'cursor': 'pointer',
                        'padding': '8px',
                        'lineHeight': '1'
                    }
                )
            ]),
            html.Button('Acceder', id='login-submit-btn', n_clicks=0, type='button', style={
                'width': '100%',
                'padding': '16px',
                'backgroundColor': COLOR_VERDE_BANDERA,
                'color': '#ffffff',
                'border': 'none',
                'borderRadius': '10px',
                'fontSize': '18px',
                'fontWeight': '700',
                'cursor': 'pointer'
            }),
            html.Div(id='login-error', style={
                'color': '#FF4D4D',
                'marginTop': '20px',
                'fontWeight': 'bold',
                'minHeight': '20px'
            })
        ])
    ])


@app.callback(
    Output('login-password', 'type'),
    Input('toggle-password-btn', 'n_clicks'),
    prevent_initial_call=True
)
def mostrar_ocultar_password(n_clicks):
    """Al pulsar el ojo, muestra u oculta la contraseña escrita."""
    return 'text' if n_clicks and n_clicks % 2 else 'password'


def render_access_denied_screen(username):
    return html.Div(style={
        'display': 'flex', 'justifyContent': 'center', 'alignItems': 'center', 'height': '100vh', 'backgroundColor': 'var(--bg-color)'
    }, children=[
        html.Div(style={
            'backgroundColor': 'var(--card-bg)', 'padding': '40px', 'borderRadius': '12px', 'boxShadow': '0 8px 32px var(--shadow-color)',
            'width': '100%', 'maxWidth': '500px', 'border': '1px solid rgba(255, 77, 77, 0.3)', 'textAlign': 'center'
        }, children=[
            html.Div(style={'fontSize': '50px', 'marginBottom': '10px'}, children=""),
            html.H2("Acceso Denegado", style={'color': '#FF4D4D', 'marginBottom': '15px'}),
            html.P(f"Usuario autenticado: {username}", style={'color': 'var(--text-color)', 'marginBottom': '10px', 'fontWeight': 'bold'}),
            html.P("Esta plataforma está reservada exclusivamente para profesores con autoridad y/o Mánager.", 
                   style={'color': 'var(--text-muted)', 'marginBottom': '30px', 'lineHeight': '1.5'}),
            html.Button("Cerrar Sesión", id='logout-btn-denied', n_clicks=0,
                        style={'padding': '10px 20px', 'backgroundColor': 'var(--hover-bg)', 'color': 'var(--text-color)', 
                               'border': '1px solid var(--border-color)', 'borderRadius': '8px', 'fontWeight': 'bold', 'cursor': 'pointer'})
        ])
    ])

@app.callback(
    Output('page-content', 'children'),
    [Input('url', 'pathname'),
     Input('url', 'search'),
     Input('main-container', 'className'),
     Input('auth-store', 'data')]
)
def controlar_rutas(pathname, search, theme_class, auth_data):
    if not _user_authorized() or not auth_data or not auth_data.get('logged_in'):
        return render_login_screen()
    
    role = auth_data.get('role')
    allowed_roles = ['manager', 'editingteacher', 'teacher', 'coursecreator']
    
    # palabras clave y lista de roles permitidos
    has_access = False
    if isinstance(role, list):
        has_access = any(r in allowed_roles for r in role)
    elif isinstance(role, str):
        has_access = role in allowed_roles
        
    if not has_access:
        return render_access_denied_screen(auth_data.get('username', 'Desconocido'))

    if pathname == '/inicio':
        return render_inicio(_datos_de_inicio())
    if pathname in ('/cursos', '/curso'):
        return render_cursos(_datos_de_cursos())
    if pathname == '/participantes':
        return render_participantes()
    if pathname == '/calificaciones':
        return render_calificaciones()
    if pathname == '/actividades':
        return render_actividades()
    if pathname == '/recursos':
        return render_recursos()
    if pathname == '/foros':
        return render_foros()
    if pathname == '/mensajes':
        return render_mensajes()
    if pathname == '/configuracion':
        return render_configuracion()
    if not pathname or pathname in ['/', '/login']:
        return render_panel_principal()
    elif pathname.startswith('/alumno/'):
        from urllib.parse import unquote, parse_qs
        nombre_estudiante = unquote(pathname.split('/')[-1])
        
        curso_seleccionado = None
        division_seleccionada = None
        if search:
            qs = parse_qs(search.lstrip('?'))
            if 'curso' in qs:
                curso_seleccionado = unquote(qs['curso'][0])
            if 'division' in qs:
                division_seleccionada = unquote(qs['division'][0])
                
        return render_panel_individual(nombre_estudiante, theme_class, curso_seleccionado, division_seleccionada)
    return html.Div("404 - Ruta no válida")



# Callback asíncrono para cargar el diagnóstico de IA
@app.callback(
    Output('diagnostico-ia-target', 'children'),
    [Input('url', 'pathname'),
     Input('url', 'search')]
)
def cargar_diagnostico_ia(pathname, search):
    if not _user_authorized() or not pathname or not pathname.startswith('/alumno/'):
        return dash.no_update
        
    nombre_alumno = urllib.parse.unquote(pathname.split('/alumno/')[1])
    
    df = obtener_datos_procesados()
    if df.empty:
        return html.P("Base de datos no cargada.", style={'color': '#FF4D4D'})
        
    nombre_limpio = urllib.parse.unquote(str(nombre_alumno)).strip().lower()
    df_nombres_norm = df['nombre_alumno'].astype(str).str.strip().str.lower()
        
    curso_seleccionado = None
    division_seleccionada = None
    if search:
        from urllib.parse import parse_qs
        qs = parse_qs(search.lstrip('?'))
        if 'curso' in qs:
            curso_seleccionado = urllib.parse.unquote(qs['curso'][0])
        if 'division' in qs:
            division_seleccionada = urllib.parse.unquote(qs['division'][0])
            
    if curso_seleccionado and division_seleccionada:
        registro = df[(df_nombres_norm == nombre_limpio) & (df['curso'] == curso_seleccionado) & (df['carrera'] == division_seleccionada)]
        if registro.empty:
            registro = df[(df_nombres_norm == nombre_limpio) & (df['curso'] == curso_seleccionado)]
    elif curso_seleccionado:
        registro = df[(df_nombres_norm == nombre_limpio) & (df['curso'] == curso_seleccionado)]
        
    if 'registro' not in locals() or registro.empty:
        registro = df[df_nombres_norm == nombre_limpio]
        
    if registro.empty:
        return html.P("Estudiante no encontrado.", style={'color': '#FF4D4D'})
        
    datos = registro.iloc[0]
    
    res = obtener_diagnostico_ia(
        nombre_alumno,
        datos['carrera'],
        datos['curso'],
        datos['grupo'],
        datos['calificacion_final']
    )
    
    riesgo = res.get("riesgo", "Desconocido")
    justificacion = res.get("justificacion_riesgo", "")
    prediccion = res.get("prediccion", "")
    recomendaciones = res.get("recomendaciones", [])
    
    badge_class = "badge-risk-bajo"
    if riesgo == "Medio":
        badge_class = "badge-risk-medio"
    elif riesgo == "Alto" or riesgo == "Error":
        badge_class = "badge-risk-alto"
        
    return html.Div(children=[
        html.Div(style={'display': 'flex', 'gap': '30px', 'flexWrap': 'wrap'}, children=[
            #columna izquierda: Riesgo y Predicción
            html.Div(style={'flex': '1', 'minWidth': '300px'}, children=[
                html.Div(style={'marginBottom': '25px'}, children=[
                    html.Label("Alerta de desempeño (no predice deserción):", style={'display': 'block', 'color': 'var(--text-muted)', 'fontSize': '12px', 'textTransform': 'uppercase', 'letterSpacing': '1px', 'marginBottom': '8px'}),
                    html.Span(riesgo, className=badge_class),
                    html.P(justificacion, style={'marginTop': '12px', 'color': 'var(--text-color)', 'fontSize': '14px', 'lineHeight': '1.5'})
                ]),
                html.Div(children=[
                    html.Label("Predicción de Rendimiento:", style={'display': 'block', 'color': 'var(--text-muted)', 'fontSize': '12px', 'textTransform': 'uppercase', 'letterSpacing': '1px', 'marginBottom': '8px'}),
                    html.P(prediccion, style={'color': 'var(--text-color)', 'fontSize': '14px', 'lineHeight': '1.5'})
                ])
            ]),
            
            # Columna derecha: Recomendaciones
            html.Div(style={'flex': '1', 'minWidth': '300px', 'borderLeft': '1px solid var(--border-color)', 'paddingLeft': '30px'}, children=[
                html.Label("Recomendaciones Pedagógicas:", style={'display': 'block', 'color': 'var(--text-muted)', 'fontSize': '12px', 'textTransform': 'uppercase', 'letterSpacing': '1px', 'marginBottom': '12px'}),
                html.Ul([
                    html.Li(r, style={'color': 'var(--text-color)', 'fontSize': '14px', 'marginBottom': '10px', 'lineHeight': '1.4'}) for r in recomendaciones
                ], style={'paddingLeft': '20px', 'margin': '0'})
            ])
        ])
    ])

@app.callback(
    [Output('carrera-dropdown', 'options'), Output('curso-dropdown', 'options'), Output('grupo-dropdown', 'options'),
     Output('busqueda-input', 'options'), Output('trigger-inicial', 'disabled')],
    [Input('trigger-inicial', 'n_intervals'), Input('carrera-dropdown', 'value'), Input('curso-dropdown', 'value'), Input('grupo-dropdown', 'value')]
)
def manejar_filtros(n, carrera_sel, curso_sel, grupo_sel):
    df = obtener_datos_procesados()
    if df is None or df.empty: 
        return [], [], [], [], False

    op_carreras = [{'label': c, 'value': c} for c in sorted(df['carrera'].unique())]
    
    df_f = df.copy()
    if carrera_sel: 
        df_f = df_f[df_f['carrera'] == carrera_sel]
    op_cursos = [{'label': c, 'value': c} for c in sorted(df_f['curso'].unique())]

    if curso_sel: 
        df_f = df_f[df_f['curso'] == curso_sel]
    
    # Procesar grupos tipo string
    op_grupos = []
    for g in sorted(df_f['grupo'].dropna().unique(), key=lambda x: str(x)):
        g_str = str(g).strip()
        op_grupos.append({'label': g_str, 'value': g_str})

    if grupo_sel:
        df_f = df_f[df_f['grupo'] == grupo_sel]
        
    op_alumnos = [{'label': str(nombre), 'value': str(nombre)} for nombre in sorted(df_f['nombre_alumno'].dropna().unique())]

    return op_carreras, op_cursos, op_grupos, op_alumnos, False

@app.callback(
    [Output('main-container', 'className'),
     Output('theme-toggle-btn', 'children'),
     Output('theme-store', 'data')],
    [Input('theme-toggle-btn', 'n_clicks')],
    [State('theme-store', 'data')],
    prevent_initial_call=False
)
def toggle_theme(n_clicks, current_theme):
    if n_clicks and n_clicks > 0:
        new_theme = 'light' if current_theme == 'dark' else 'dark'
    else:
        new_theme = current_theme if current_theme in ['dark', 'light'] else 'dark'

    if new_theme == 'light':
        btn_content = [
            get_svg_icon('moon', COLOR_VERDE_BANDERA),
            html.Span("Modo Oscuro", style={'color': COLOR_VERDE_BANDERA, 'fontWeight': '700', 'marginLeft': '6px'})
        ]
        return 'light-theme', btn_content, 'light'
    else:
        btn_content = [
            get_svg_icon('sun', COLOR_VERDE_BANDERA),
            html.Span("Modo Claro", style={'color': COLOR_VERDE_BANDERA, 'fontWeight': '700', 'marginLeft': '6px'})
        ]
        return 'dark-theme', btn_content, 'dark'

@app.callback(
    [Output('grafico-pastel-general', 'figure'), 
     Output('grafico-barras-general', 'figure'), 
     Output('tabla-alumnos-container', 'children'), 
     Output('mensaje-estado-container', 'children'),
     Output('metric-total', 'children'),
     Output('metric-promedio', 'children'),
     Output('metric-aprobados', 'children'),
     Output('metric-aprobados-pct', 'children'),
     Output('metric-riesgo', 'children'),
     Output('metric-riesgo-pct', 'children')],
    [Input('carrera-dropdown', 'value'), 
     Input('curso-dropdown', 'value'), 
     Input('grupo-dropdown', 'value'),
     Input('busqueda-input', 'value'),
     Input('main-container', 'className'),
     Input('trigger-inicial', 'n_intervals')],
    [State('carrera-dropdown', 'options'),
     State('url', 'pathname')]
)
def actualizar_dashboard(carrera_sel, curso_sel, grupo_sel, busqueda_sel, theme_class, _intervalo, options_carrera, pathname):
    df = obtener_datos_procesados()
    estado_moodle = _leer_catalogo()
    detalle = ('Sincronizando: ' + str(estado_moodle.get('cursos_consultados',0)) + ' de ' + str(estado_moodle.get('cursos_totales','?')) + ' cursos consultados.'
               if estado_moodle.get('sync_in_progress') else
               ('Moodle no entregó registros. Revisa Configuración y los Logs de Render.' if estado_moodle.get('errores') else
                'Esperando primera sincronización de Moodle.'))
    empty_ret = ({}, {}, html.Div(detalle, style={'color':'var(--text-muted)'}),
                 html.Div(detalle, style={'color':'var(--text-muted)'}),
                 '—', '—', '—', '—', '—', '—')
    if df.empty or not {'nombre_alumno','curso','grupo','calificacion_final'}.issubset(df.columns):
        return empty_ret
    for key, value in [('carrera', carrera_sel), ('curso', curso_sel), ('grupo', grupo_sel)]:
        if value and key in df:
            df = df[df[key] == value]
    if df.empty:
        return empty_ret
    # Un alumno matriculado en varios cursos cuenta una vez en la vista institucional,
    # pero solo los que tienen nota se consideran para el porcentaje de aprobados.
    df = df.copy()
    df['_clave_identidad'] = _identidad_para_agrupacion(df)
    agg = df.groupby('_clave_identidad', dropna=True).agg(nombre_alumno=('nombre_alumno','first'),
        calificacion_final=('calificacion_final','mean'), grupo=('grupo','first')).reset_index()
    agg['calificacion_final'] = pd.to_numeric(agg['calificacion_final'], errors='coerce')
    con_nota = agg[agg['calificacion_final'].between(0, 10)].copy()
    sin_nota = int(len(agg)-len(con_nota))
    aprob = int((con_nota['calificacion_final'] >= 6).sum())
    debajo = int((con_nota['calificacion_final'] < 6).sum())
    denominator = len(con_nota)
    pct_ap = 100*aprob/denominator if denominator else 0
    pct_deb = 100*debajo/denominator if denominator else 0
    promedio = f"{con_nota['calificacion_final'].mean():.2f}" if denominator else '—'
    statuses = pd.DataFrame({'Estado':['Aprobado (≥6)','Por debajo de 6','Sin calificar'],
                              'Registros':[aprob,debajo,sin_nota]})
    light = theme_class == 'light-theme'
    template = 'plotly_white' if light else 'plotly_dark'
    fontcolor = '#10213c' if light else '#f2f6ff'
    fig_pie = px.pie(statuses, names='Estado', values='Registros',
                    color='Estado', color_discrete_map={'Aprobado (≥6)':'#008000',
                    'Por debajo de 6':'#ff4d4d','Sin calificar':'#94a3b8'},
                    title='Distribución de resultados académicos', template=template)
    fig_pie.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                          font_color=fontcolor, margin=dict(l=10,r=10,t=55,b=20))
    # Evitar un gráfico ilegible con miles de estudiantes.
    graficables = con_nota.nsmallest(60, 'calificacion_final')
    fig_bar = px.bar(graficables, x='nombre_alumno', y='calificacion_final',
                     title='Calificaciones (hasta 60 registros con menor nota)',
                     color_discrete_sequence=[COLOR_VERDE_BANDERA], template=template)
    fig_bar.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                          font_color=fontcolor, yaxis=dict(range=[0,10]),
                          margin=dict(l=12,r=12,t=55,b=65), clickmode='event+select')
    rows = []
    for _, r in agg.sort_values('nombre_alumno').iterrows():
        grade = r['calificacion_final']
        params = {}
        if curso_sel: params['curso'] = str(curso_sel)
        if carrera_sel: params['division'] = str(carrera_sel)
        qstr = '?' + urllib.parse.urlencode(params) if params else ''
        name = str(r['nombre_alumno'])
        rows.append(html.Div(className='student-row', style={'padding': '12px 15px',
            'borderBottom': '1px solid var(--border-color)', 'display':'flex',
            'alignItems':'center','justifyContent':'space-between','gap':'14px'}, children=[
            dcc.Link(name, href='/alumno/'+urllib.parse.quote(name)+qstr,
                     style={'color':'var(--accent-color)'}),
            html.Span(f"{float(grade):.2f} / 10" if pd.notna(grade) else 'Sin calificar',
                      style={'color':'var(--text-muted)'})]))
    registros_ui = html.Div(rows, style={'height':'400px', 'overflowY':'auto',
                       'border':'1px solid var(--border-color)', 'borderRadius':'10px'})
    notice = html.Div(f'{denominator} estudiantes con nota; {sin_nota} sin calificación. '
                      f'Última sincronización: {_marca_sincronizacion()}. '
                      'Los porcentajes usan solo las notas válidas (0 a 10).',
                      style={'color':'var(--text-muted)', 'fontSize':'13px'})
    return fig_pie,fig_bar,registros_ui,notice,str(len(agg)),promedio,str(aprob),           f'{pct_ap:.1f}% de calificados',str(debajo),f'{pct_deb:.1f}% de calificados'

#callback interactivo de redirección al hacer click sobre el gráfico de barras
@app.callback(
    [Output('url', 'pathname', allow_duplicate=True),
     Output('url', 'search', allow_duplicate=True)],
    Input('grafico-barras-general', 'clickData'),
    [State('carrera-dropdown', 'value'),
     State('curso-dropdown', 'value'),
     State('url', 'pathname')],
    prevent_initial_call=True
)
def redirigir_alumno(clickData, carrera_sel, curso_sel, current_path):
    if clickData and current_path == '/':
        try:
            nombre = str(clickData['points'][0]['x'])
            import urllib.parse
            params = {}
            if curso_sel: params['curso'] = str(curso_sel)
            if carrera_sel: params['division'] = str(carrera_sel)
            search_str = "?" + urllib.parse.urlencode(params) if params else ""
            
            return f"/alumno/{urllib.parse.quote(nombre)}", search_str
        except Exception as e:
            print(f"Error en redirección clickData: {e}")
    return dash.no_update, dash.no_update

#callback de redirección al seleccionar un alumno en la barra de búsqueda
@app.callback(
    [Output('url', 'pathname', allow_duplicate=True),
     Output('url', 'search', allow_duplicate=True)],
    Input('busqueda-input', 'value'),
    [State('carrera-dropdown', 'value'),
     State('curso-dropdown', 'value')],
    prevent_initial_call=True
)
def redirigir_desde_busqueda(busqueda_sel, carrera_sel, curso_sel):
    if busqueda_sel:
        nombre = str(busqueda_sel).strip().upper()
        import urllib.parse
        params = {}
        if curso_sel: params['curso'] = str(curso_sel)
        if carrera_sel: params['division'] = str(carrera_sel)
        search_str = "?" + urllib.parse.urlencode(params) if params else ""
        return f"/alumno/{urllib.parse.quote(nombre)}", search_str
    return dash.no_update, dash.no_update

#control de layout (Sidebar y Margen) según autenticación
@app.callback(
    [Output('sidebar-container', 'style'),
     Output('page-content', 'style')],
    [Input('auth-store', 'data')]
)
def update_layout_auth(auth_data):
    if _user_authorized() and auth_data and auth_data.get('logged_in'):
        role = auth_data.get('role')
        allowed_roles = ['manager', 'editingteacher', 'teacher', 'coursecreator']
        
        has_access = False
        if isinstance(role, list):
            has_access = any(r in allowed_roles for r in role)
        elif isinstance(role, str):
            has_access = role in allowed_roles
            
        if has_access:
            return SIDEBAR_STYLE, CONTENT_STYLE
            
    return {'display': 'none'}, {'padding': '40px', 'backgroundColor': 'var(--bg-color)', 'minHeight': '100vh'}

#manejo de Login y Logout
@app.callback(
    [Output('auth-store', 'data', allow_duplicate=True),
     Output('login-error', 'children'),
     Output('url', 'pathname', allow_duplicate=True)],
    [Input('login-submit-btn', 'n_clicks'),
     Input('login-username', 'n_submit'),
     Input('login-password', 'n_submit')],
    [State('login-username', 'value'),
     State('login-password', 'value'),
     State('auth-store', 'data')],
    prevent_initial_call=True
)
def handle_login(n_clicks, enter_usuario, enter_password, username, password, auth_data):
    if not (n_clicks or enter_usuario or enter_password) or not username or not password:
        return dash.no_update, 'Escribe usuario y contraseña.', dash.no_update
    username = str(username).strip().lower()
    flask_session.pop('uttec_authorized', None)
    flask_session.pop('uttec_user_id', None)
    # Mantener el acceso local de prueba de la versión que entregó el usuario.
    # Solo el equipo local puede usarlo; nunca se habilita en Render ni desde la LAN.
    localhost_real = (has_request_context()
                      and request.remote_addr in ('127.0.0.1', '::1')
                      and request.host.split(':')[0].lower() in ('127.0.0.1', 'localhost', '[::1]'))
    if localhost_real and username in ('profesor', 'manager', 'maestro', 'docente'):
        flask_session['uttec_authorized'] = True
        flask_session['uttec_role'] = 'editingteacher'
        flask_session['uttec_user_id'] = 'local-demo'
        flask_session.permanent = False
        return {'logged_in': True, 'role': 'editingteacher', 'username': username.capitalize()}, '', '/inicio'
    if not os.environ.get('MOODLE_TOKEN'):
        return dash.no_update, ('No hay conexión autorizada a Moodle en este entorno. '
                                'Para datos reales configura MOODLE_TOKEN en el servidor.'), dash.no_update
    service_name = os.environ.get('MOODLE_LOGIN_SERVICE', 'moodle_mobile_app')
    try:
        url = BASE_MOODLE + '/login/token.php'
        response = requests.post(url, data={'username': username, 'password': password,
                                            'service': service_name}, timeout=20)
        response.raise_for_status()
        data = response.json()
        user_token = data.get('token') if isinstance(data, dict) else None
        if not user_token:
            return dash.no_update, 'Credenciales incorrectas o servicio de acceso no habilitado en Moodle.', dash.no_update
        profile = _moodle_request('core_webservice_get_site_info', token=user_token)
        user_id = profile.get('userid')
        if not user_id:
            return dash.no_update, 'Moodle no pudo identificar el usuario.', dash.no_update
        is_admin = bool(profile.get('userissiteadmin'))
        # Whitelist administrada solo desde variables de entorno en Render.
        whitelisted = {x.strip() for x in os.environ.get('UTTEC_ALLOWED_USER_IDS', '').split(',') if x.strip()}
        role_assigned = 'manager' if is_admin or str(user_id) in whitelisted else None
        if not role_assigned:
            cat = _leer_catalogo()  # Sin sesión aún devuelve {}; consultar matrículas directamente.
            cursos = _moodle_request('core_course_get_courses')
            if not isinstance(cursos, list):
                raise RuntimeError('No se pudo consultar cursos para autorización')
            max_roles = max(1, int(os.environ.get('MOODLE_ROLE_CHECK_COURSES', '80')))
            for course in cursos[:max_roles]:
                if not isinstance(course, dict) or int(course.get('id') or 1) == 1:
                    continue
                try:
                    enrolled = _moodle_request('core_enrol_get_enrolled_users', {'courseid': course['id']})
                    for entry in enrolled if isinstance(enrolled, list) else []:
                        if str(entry.get('id')) == str(user_id):
                            roles = {str(r.get('shortname','')).lower() for r in (entry.get('roles') or [])}
                            allowed = roles.intersection({'editingteacher','teacher','manager','coursecreator'})
                            if allowed:
                                role_assigned = next(iter(allowed))
                                break
                    if role_assigned:
                        break
                except RuntimeError:
                    continue
        if not role_assigned:
            return dash.no_update, 'Acceso reservado a docentes y personal administrativo autorizado.', dash.no_update
        flask_session['uttec_authorized'] = True
        flask_session['uttec_user_id'] = str(user_id)
        flask_session['uttec_role'] = role_assigned
        flask_session.permanent = False
        return {'logged_in': True, 'role': role_assigned,
                'username': str(profile.get('fullname') or username)}, '', '/inicio'
    except (requests.RequestException, RuntimeError, ValueError, TypeError) as exc:
        _logger.error('Error autenticación: %s', str(exc)[:230])
        return dash.no_update, 'No se pudo verificar el acceso con Moodle. Revise Logs y permisos del servicio.', dash.no_update

@app.callback(
    [Output('auth-store', 'data', allow_duplicate=True),
     Output('url', 'pathname', allow_duplicate=True)],
    [Input('logout-btn', 'n_clicks')],
    prevent_initial_call=True
)
def handle_logout_main(n_clicks):
    if n_clicks:
        flask_session.clear()
        return {'logged_in': False, 'role': None, 'username': None}, '/login'
    return dash.no_update, dash.no_update

@app.callback(
    [Output('auth-store', 'data', allow_duplicate=True),
     Output('url', 'pathname', allow_duplicate=True)],
    [Input('logout-btn-denied', 'n_clicks')],
    prevent_initial_call=True
)
def handle_logout_denied(n_clicks):
    if n_clicks:
        flask_session.clear()
        return {'logged_in': False, 'role': None, 'username': None}, '/login'
    return dash.no_update, dash.no_update

@app.callback(
    Output('user-profile-header', 'children'),
    [Input('auth-store', 'data')]
)
def update_user_header(auth_data):
    if not auth_data or not auth_data.get('logged_in'):
        nombre = "Profesor / Manager"
    else:
        nombre = auth_data.get('username', "Profesor / Manager")
        # Si el nombre viene como correo
        if '@' in nombre:
            nombre = nombre.split('@')[0]
        nombre = nombre.replace('.', ' ').title()
        
    return html.Div(style={
        'display': 'flex',
        'alignItems': 'center',
        'gap': '12px',
        'padding': '8px 16px',
        'backgroundColor': 'var(--card-bg)',
        'borderRadius': '30px',
        'border': '1px solid var(--border-color)',
        'boxShadow': '0 2px 8px var(--shadow-color)'
    }, children=[
        html.Div(children=[
            html.Span("Bienvenido(a),", style={'display': 'block', 'fontSize': '11px', 'color': 'var(--text-muted)', 'marginBottom': '2px', 'lineHeight': '1'}),
            html.Span(nombre, style={'display': 'block', 'fontSize': '14px', 'fontWeight': '600', 'color': 'var(--text-color)', 'lineHeight': '1'})
        ])
    ])

if __name__ == '__main__':
    puerto = int(os.environ.get('PORT', 5000))
    en_render = bool(os.environ.get('PORT') or os.environ.get('RENDER'))
    host = '0.0.0.0' if en_render else '127.0.0.1'
    if not en_render:
        # Si quedó abierta una versión antigua en 5000, utilizar un puerto libre.
        import socket
        for candidato in range(puerto, puerto + 10):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as prueba:
                try:
                    prueba.bind(('127.0.0.1', candidato))
                except OSError:
                    continue
            puerto = candidato
            break
        print(f'Dashboard local: http://127.0.0.1:{puerto}/')
        print('Acceso de prueba local: usuario profesor; contraseña de prueba no vacía.')
        if not os.environ.get('MOODLE_TOKEN'):
            print('MOODLE_TOKEN no configurado: se mostrará la interfaz, pero sin datos reales.')
    app.run(debug=False, host=host, port=puerto)