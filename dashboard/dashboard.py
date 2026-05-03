"""
============================================================
CP5 - Vinheria Agnello | Dashboard IoT
============================================================
Integrantes:
  Joao Victor Melo  (566640)
  Gustavo Macedo    (567594)
  Gustavo Hiruo     (567625)
  Yan Lucas         (567046)

Turma: 1ESPA - FIAP 2026
Professor: Fabio Henrique Cabrini
============================================================
"""

import requests
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objs as go
from datetime import datetime
import logging
import paho.mqtt.publish as publish

# ============================================================
# CONFIGURACOES
# ============================================================

FIWARE_IP   = "20.124.178.183"
MQTT_PORT   = 1883
HEADERS     = {"fiware-service": "smart", "fiware-servicepath": "/"}
ENTITY_ID   = "urn:ngsi-ld:Vinheria:001"
ENTITY_TYPE = "SensorLDR"
LAST_N      = 20
INTERVALO_ATUALIZACAO = 5000

MQTT_TOPIC_CMD = "/TEF/vinheria001/cmd"

# ============================================================
# THRESHOLDS
# ============================================================
THRESH = {
    "luminosity":  {"min": 0,  "max": 30},
    "temperature": {"min": 10, "max": 15},
    "humidity":    {"min": 50, "max": 70},
}

# ============================================================
# LOGGING
# ============================================================
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)
logging.getLogger("werkzeug").setLevel(logging.ERROR)

# ============================================================
# FUNCOES DE COMUNICACAO
# ============================================================

def buscar_historico(atributo):
    url = (
        f"http://{FIWARE_IP}:8666/STH/v1/contextEntities"
        f"/type/{ENTITY_TYPE}/id/{ENTITY_ID}"
        f"/attributes/{atributo}?lastN={LAST_N}"
    )
    try:
        resp = requests.get(url, headers=HEADERS, timeout=5)
        resp.raise_for_status()
        valores = (
            resp.json()
            .get("contextResponses", [{}])[0]
            .get("contextElement", {})
            .get("attributes", [{}])[0]
            .get("values", [])
        )
        resultado = []
        for v in valores:
            try:
                resultado.append({
                    "timestamp": datetime.strptime(v["recvTime"], "%Y-%m-%dT%H:%M:%S.%fZ"),
                    "valor": float(v["attrValue"])
                })
            except (KeyError, ValueError):
                continue
        return resultado
    except requests.exceptions.ConnectionError:
        log.warning(f"Sem conexao com STH-Comet ao buscar '{atributo}'")
        return []
    except Exception as e:
        log.error(f"Erro ao buscar historico de '{atributo}': {e}")
        return []


def enviar_comando(comando):
    mensagem = f"vinheria001@{comando}|"
    try:
        publish.single(MQTT_TOPIC_CMD, mensagem, hostname=FIWARE_IP, port=MQTT_PORT)
        log.info(f"Comando '{comando}' enviado via MQTT.")
    except Exception as e:
        log.error(f"Erro ao enviar comando '{comando}': {e}")


def analisar_e_alertar(lum, temp, hum):
    alertas = {"luminosity": False, "temperature": False, "humidity": False}
    if lum is not None:
        alertas["luminosity"] = not (THRESH["luminosity"]["min"] <= lum <= THRESH["luminosity"]["max"])
    if temp is not None:
        alertas["temperature"] = not (THRESH["temperature"]["min"] <= temp <= THRESH["temperature"]["max"])
    if hum is not None:
        alertas["humidity"] = not (THRESH["humidity"]["min"] <= hum <= THRESH["humidity"]["max"])
    enviar_comando("on" if any(alertas.values()) else "off")
    return alertas


def status_badge(em_alerta, valor, unidade, minv, maxv):
    if valor is None:
        return "Sem dados", "sem-dados"
    if em_alerta:
        return f"FORA DO LIMITE ({valor:.1f}{unidade})", "alerta"
    return f"Normal ({valor:.1f}{unidade}  |  {minv}-{maxv}{unidade})", "normal"


# ============================================================
# APLICACAO DASH
# ============================================================

app = dash.Dash(__name__, title="Vinheria Agnello", update_title=None)

# CSS global para evitar overflow horizontal
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
            html, body {
                margin: 0;
                padding: 0;
                overflow-x: hidden;
                width: 100%;
                max-width: 100vw;
                box-sizing: border-box;
            }
            *, *::before, *::after {
                box-sizing: border-box;
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

app.layout = html.Div(
    style={
        "fontFamily": "Segoe UI, sans-serif",
        "backgroundColor": "#0f0f14",
        "minHeight": "100vh",
        "padding": "24px",
        "color": "#e8e6df",
        "maxWidth": "100%",
        "boxSizing": "border-box",
        "overflowX": "hidden",
    },
    children=[
        html.Div(
            style={"display": "flex", "alignItems": "center", "justifyContent": "space-between",
                   "marginBottom": "28px", "borderBottom": "1px solid #2a2a35",
                   "paddingBottom": "16px", "flexWrap": "wrap", "gap": "12px"},
            children=[
                html.Div([
                    html.H1("Vinheria Agnello",
                            style={"margin": 0, "fontSize": "26px", "fontWeight": "600"}),
                    html.P("Monitoramento IoT em tempo real - CP5 FIAP 2026",
                           style={"margin": "4px 0 0", "color": "#888", "fontSize": "13px"}),
                ]),
                html.Div(id="ultimo-update", style={"fontSize": "12px", "color": "#555"})
            ]
        ),

        html.Div(
            style={"display": "grid", "gridTemplateColumns": "repeat(auto-fit, minmax(280px, 1fr))",
                   "gap": "16px", "marginBottom": "28px", "width": "100%"},
            children=[
                html.Div(id="card-lum",  style={"background": "#1a1a24", "borderRadius": "12px",
                                                "padding": "20px", "border": "1px solid #2a2a35",
                                                "minWidth": 0}),
                html.Div(id="card-temp", style={"background": "#1a1a24", "borderRadius": "12px",
                                                "padding": "20px", "border": "1px solid #2a2a35",
                                                "minWidth": 0}),
                html.Div(id="card-hum",  style={"background": "#1a1a24", "borderRadius": "12px",
                                                "padding": "20px", "border": "1px solid #2a2a35",
                                                "minWidth": 0}),
            ]
        ),

        html.Div(
            style={"display": "grid", "gridTemplateColumns": "1fr", "gap": "16px",
                   "width": "100%", "minWidth": 0},
            children=[
                html.Div(style={"background": "#1a1a24", "borderRadius": "12px", "padding": "20px",
                                "border": "1px solid #2a2a35", "minWidth": 0, "overflow": "hidden"},
                         children=[html.H3("Luminosidade (%)",
                                           style={"margin": "0 0 12px", "fontSize": "14px", "color": "#aaa"}),
                                   dcc.Graph(id="grafico-lum",
                                             config={"displayModeBar": False, "responsive": True},
                                             style={"width": "100%"})]),
                html.Div(style={"background": "#1a1a24", "borderRadius": "12px", "padding": "20px",
                                "border": "1px solid #2a2a35", "minWidth": 0, "overflow": "hidden"},
                         children=[html.H3("Temperatura (C)",
                                           style={"margin": "0 0 12px", "fontSize": "14px", "color": "#aaa"}),
                                   dcc.Graph(id="grafico-temp",
                                             config={"displayModeBar": False, "responsive": True},
                                             style={"width": "100%"})]),
                html.Div(style={"background": "#1a1a24", "borderRadius": "12px", "padding": "20px",
                                "border": "1px solid #2a2a35", "minWidth": 0, "overflow": "hidden"},
                         children=[html.H3("Umidade (%)",
                                           style={"margin": "0 0 12px", "fontSize": "14px", "color": "#aaa"}),
                                   dcc.Graph(id="grafico-hum",
                                             config={"displayModeBar": False, "responsive": True},
                                             style={"width": "100%"})]),
            ]
        ),

        dcc.Interval(id="intervalo", interval=INTERVALO_ATUALIZACAO, n_intervals=0),
    ]
)


def criar_grafico(dados, cor, label, thresh_min, thresh_max, unidade):
    if not dados:
        fig = go.Figure(layout=go.Layout(
            paper_bgcolor="#1a1a24", plot_bgcolor="#1a1a24", font={"color": "#888"},
            annotations=[{"text": "Aguardando dados do STH-Comet...", "showarrow": False,
                          "font": {"color": "#555"}}],
            autosize=True, height=220,
            margin={"t": 10, "b": 40, "l": 50, "r": 20}
        ))
        return fig

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=[d["timestamp"] for d in dados], y=[d["valor"] for d in dados],
        mode="lines+markers", name=label,
        line={"color": cor, "width": 2}, marker={"size": 5},
    ))
    fig.add_hline(y=thresh_max, line_dash="dash", line_color="#E24B4A",
                  annotation_text=f"Max: {thresh_max}{unidade}",
                  annotation_position="top right", annotation_font_color="#E24B4A")
    fig.add_hline(y=thresh_min, line_dash="dash", line_color="#378ADD",
                  annotation_text=f"Min: {thresh_min}{unidade}",
                  annotation_position="bottom right", annotation_font_color="#378ADD")
    fig.update_layout(
        paper_bgcolor="#1a1a24", plot_bgcolor="#1a1a24",
        font={"color": "#aaa", "size": 12},
        margin={"t": 10, "b": 40, "l": 50, "r": 20}, height=220,
        xaxis={"gridcolor": "#2a2a35", "automargin": True, "fixedrange": True},
        yaxis={"gridcolor": "#2a2a35", "automargin": True, "fixedrange": True},
        showlegend=False,
        autosize=True,
    )
    return fig


def criar_card(titulo, texto_status, classe_status):
    cores = {
        "normal":    {"bg": "#0d2b1a", "border": "#1D9E75", "text": "#5DCAA5"},
        "alerta":    {"bg": "#2b0d0d", "border": "#E24B4A", "text": "#F09595"},
        "sem-dados": {"bg": "#1a1a24", "border": "#2a2a35", "text": "#555"},
    }
    c = cores.get(classe_status, cores["sem-dados"])
    return html.Div([
        html.Div(style={"display": "flex", "alignItems": "center", "gap": "10px",
                        "marginBottom": "12px"},
                 children=[html.Span(titulo, style={"fontWeight": "600", "fontSize": "15px"})]),
        html.Div(texto_status, style={"fontSize": "13px", "padding": "8px 12px",
                                      "borderRadius": "8px", "background": c["bg"],
                                      "border": f"1px solid {c['border']}", "color": c["text"],
                                      "wordBreak": "break-word"})
    ])


@app.callback(
    [Output("card-lum", "children"), Output("card-temp", "children"),
     Output("card-hum", "children"), Output("grafico-lum", "figure"),
     Output("grafico-temp", "figure"), Output("grafico-hum", "figure"),
     Output("ultimo-update", "children")],
    Input("intervalo", "n_intervals")
)
def atualizar_dashboard(n):
    hist_lum  = buscar_historico("luminosity")
    hist_temp = buscar_historico("temperature")
    hist_hum  = buscar_historico("humidity")

    lum_atual  = hist_lum[-1]["valor"]  if hist_lum  else None
    temp_atual = hist_temp[-1]["valor"] if hist_temp else None
    hum_atual  = hist_hum[-1]["valor"]  if hist_hum  else None

    alertas = analisar_e_alertar(lum_atual, temp_atual, hum_atual)

    txt_lum,  cls_lum  = status_badge(alertas["luminosity"],  lum_atual,  "%",  THRESH["luminosity"]["min"],  THRESH["luminosity"]["max"])
    txt_temp, cls_temp = status_badge(alertas["temperature"], temp_atual, "C",  THRESH["temperature"]["min"], THRESH["temperature"]["max"])
    txt_hum,  cls_hum  = status_badge(alertas["humidity"],    hum_atual,  "%",  THRESH["humidity"]["min"],    THRESH["humidity"]["max"])

    return (
        criar_card("Luminosidade", txt_lum,  cls_lum),
        criar_card("Temperatura",  txt_temp, cls_temp),
        criar_card("Umidade",      txt_hum,  cls_hum),
        criar_grafico(hist_lum,  "#EF9F27", "Luminosidade", THRESH["luminosity"]["min"],  THRESH["luminosity"]["max"],  "%"),
        criar_grafico(hist_temp, "#E24B4A", "Temperatura",  THRESH["temperature"]["min"], THRESH["temperature"]["max"], "C"),
        criar_grafico(hist_hum,  "#378ADD", "Umidade",      THRESH["humidity"]["min"],    THRESH["humidity"]["max"],    "%"),
        f"Ultima atualizacao: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
    )


if __name__ == "__main__":
    log.info("=== Vinheria Agnello Dashboard iniciando na porta 5000 ===")
    log.info(f"Acesse: http://{FIWARE_IP}:5000")
    app.run(host="0.0.0.0", port=5000, debug=False)
