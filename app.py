import base64
import io
import os
import pandas as pd
import plotly.express as px
from dash import Dash, dcc, html, Input, Output, State

# --- CONFIGURACIÓN INICIAL ---
app = Dash(__name__)
app.title = "Tablero Escolar"

estilo_tabs = {'height': '44px'}
estilo_tab = {'borderBottom': '1px solid #d6d6d6', 'padding': '6px', 'fontWeight': 'bold'}
estilo_tab_selec = {'borderTop': '1px solid #d6d6d6', 'borderBottom': '1px solid #d6d6d6', 'backgroundColor': '#119DFF', 'color': 'white', 'padding': '6px'}

df_global = None
NOTA_APROBATORIA = 70
ARCHIVO_LOCAL = 'bd_dash.xlsx'

# Carga automática
if os.path.exists(ARCHIVO_LOCAL):
    try:
        print(f"Cargando archivo local: {ARCHIVO_LOCAL}...")
        df_global = pd.read_excel(ARCHIVO_LOCAL)
        df_global.columns = df_global.columns.str.upper().str.strip()
        print(f"✅ Carga exitosa. {len(df_global)} registros cargados.")
    except Exception as e:
        print(f"Error al cargar archivo local: {e}")

# ---------------------------------------------------------
# LAYOUT
# ---------------------------------------------------------
app.layout = html.Div([
    html.H1("Sistema de Análisis Escolar", style={'textAlign': 'center', 'fontFamily': 'Arial', 'color': '#333'}),

    html.Div([
        dcc.Upload(
            id='upload-data',
            children=html.Div(['Arrastra y suelta o ', html.A('Selecciona otro Archivo')]),
            style={
                'width': '60%', 'height': '60px', 'lineHeight': '60px',
                'borderWidth': '1px', 'borderStyle': 'dashed', 'borderRadius': '5px',
                'textAlign': 'center', 'margin': '10px auto', 'cursor': 'pointer'
            },
            multiple=False
        ),
        html.Div(id='output-data-upload', style={'textAlign': 'center', 'margin': '10px', 'fontWeight': 'bold'})
    ]),

    dcc.Tabs(id="tabs-menu", value='tab-generacion', children=[
        dcc.Tab(label='Generación (Línea)', value='tab-generacion', style=estilo_tab, selected_style=estilo_tab_selec),
        dcc.Tab(label='Género (Anillo)', value='tab-sexo', style=estilo_tab, selected_style=estilo_tab_selec),
        dcc.Tab(label='Programa (PE)', value='tab-pe', style=estilo_tab, selected_style=estilo_tab_selec),
        dcc.Tab(label='Preparatoria', value='tab-prepa', style=estilo_tab, selected_style=estilo_tab_selec),
        dcc.Tab(label='Reprobación Asignatura', value='tab-repro-asig', style=estilo_tab, selected_style=estilo_tab_selec),
        dcc.Tab(label='Reprobación Docente', value='tab-repro-doc', style=estilo_tab, selected_style=estilo_tab_selec),
    ], style={'marginTop': '20px'}),

    html.Div(id='tabs-content-graph', style={'padding': '20px'})
])

# ---------------------------------------------------------
# CALLBACKS
# ---------------------------------------------------------

@app.callback(
    Output('output-data-upload', 'children'),
    Input('upload-data', 'contents'),
    State('upload-data', 'filename')
)
def update_output(contents, filename):
    global df_global
    if contents is None:
        if df_global is not None:
            return f"Usando archivo local: {ARCHIVO_LOCAL}"
        return "Esperando archivo..."
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    try:
        df_global = pd.read_excel(io.BytesIO(decoded))
        df_global.columns = df_global.columns.str.upper().str.strip()
        return f"Archivo '{filename}' cargado correctamente."
    except Exception as e:
        return f"Error procesando el archivo: {e}"

@app.callback(
    Output('tabs-content-graph', 'children'),
    Input('tabs-menu', 'value'),
    Input('output-data-upload', 'children')
)
def render_graph(tab, status):
    global df_global
    
    if df_global is None:
        return html.Div("⚠️ No hay datos cargados.", style={'color': 'red', 'textAlign': 'center'})

    # --- 1. GRÁFICA DE GENERACIÓN (LÍNEA + CRONOLÓGICO) ---
    if tab == 'tab-generacion':
        columna = 'GENERACION'
        if columna not in df_global.columns: return html.Div(f"Falta columna {columna}")
        
        # Agrupar
        df_graf = df_global.groupby(columna)['ALUCTR'].nunique().reset_index()
        df_graf.columns = [columna, 'Cantidad Alumnos']
        
        # ORDENAR CRONOLÓGICAMENTE (Ascendente)
        df_graf = df_graf.sort_values(columna, ascending=True)

        fig = px.line(df_graf, x=columna, y='Cantidad Alumnos',
                      title="Evolución de Matrícula por Generación",
                      markers=True, # Puntos en la línea
                      text='Cantidad Alumnos') # Etiqueta de datos
        
        fig.update_traces(textposition="bottom right")
        fig.update_layout(xaxis_type='category') # Para mostrar todos los años

    # --- 2. GRÁFICA DE GÉNERO (ANILLO + COLORES H/M) ---
    elif tab == 'tab-sexo':
        columna = 'ALUSEX'
        if columna not in df_global.columns: return html.Div(f"Falta columna {columna}")

        df_graf = df_global.groupby(columna)['ALUCTR'].nunique().reset_index()
        df_graf.columns = [columna, 'Cantidad Alumnos']

        # Definir colores específicos (Mapa de colores)
        colores = {
            'H': 'blue', 
            'M': 'hotpink',
            'F': 'hotpink',      # Por si acaso viene como Femenino
            'Hombre': 'blue',    # Por si acaso viene completo
            'Mujer': 'hotpink'
        }

        fig = px.pie(df_graf, values='Cantidad Alumnos', names=columna,
                     title="Distribución de Matrícula por Género",
                     hole=0.5, # Esto crea el anillo (Donut Chart)
                     color=columna,
                     color_discrete_map=colores) # Aplicar colores personalizados

    # --- 3. OTRAS GRÁFICAS DE BARRAS (PE, PREPA) ---
    elif tab in ['tab-pe', 'tab-prepa']:
        col_map = {'tab-pe': 'PE', 'tab-prepa': 'PREPARATORIA'}
        columna = col_map[tab]
        
        df_graf = df_global.groupby(columna)['ALUCTR'].nunique().reset_index()
        df_graf.columns = [columna, 'Cantidad Alumnos']
        df_graf = df_graf.sort_values('Cantidad Alumnos', ascending=False)
        
        if len(df_graf) > 15:
            df_graf = df_graf.head(15) # Top 15

        fig = px.bar(df_graf, x=columna, y='Cantidad Alumnos', 
                     text='Cantidad Alumnos', title=f"Matrícula por {columna}",
                     color='Cantidad Alumnos', color_continuous_scale='Viridis')

    # --- 4. GRÁFICAS DE REPROBACIÓN ---
    else:
        col_map = {'tab-repro-asig': 'ASIGNATURA', 'tab-repro-doc': 'DOCENTE'}
        columna = col_map.get(tab)
        col_calif = 'KARCAL'

        df_clean = df_global.dropna(subset=[col_calif])
        total = df_clean.groupby(columna)[col_calif].count()
        reprobados = df_clean[df_clean[col_calif] < NOTA_APROBATORIA]
        total_reprobados = reprobados.groupby(columna)[col_calif].count()

        tasa = (total_reprobados / total * 100).fillna(0).reset_index()
        tasa.columns = [columna, '% Reprobación']
        tasa = tasa.sort_values('% Reprobación', ascending=False).head(15)

        fig = px.bar(tasa, x=columna, y='% Reprobación',
                     text=tasa['% Reprobación'].apply(lambda x: '{0:1.2f}%'.format(x)),
                     title=f"Top 15 Índice de Reprobación por {columna}",
                     color='% Reprobación', color_continuous_scale='Reds')
        fig.update_layout(yaxis_range=[0, 100])

    return dcc.Graph(figure=fig, style={'height': '70vh'})

if __name__ == '__main__':
    app.run(debug=True)