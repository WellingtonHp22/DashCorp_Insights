"""
Dashboard interativo e avançado para análise de dados empresariais

Este script cria um dashboard web moderno e interativo que exibe os dados
das empresas armazenados no MongoDB ou carregados de arquivos, com visualizações 
dinâmicas e análises avançadas.
"""

import os
import sys
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, html, dcc, dash_table, callback, Output, Input, State
import dash_bootstrap_components as dbc
from dash_bootstrap_templates import load_figure_template
from dash.exceptions import PreventUpdate
import numpy as np
import re
from datetime import datetime
import pycountry
import plotly.colors as pc
import colorsys

# Adicionar o diretório pai ao sys.path para permitir importações relativas
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.mongo_manager import MongoDBManager

# Carregar o template para gráficos
load_figure_template("DARKLY")

# Função para gerar paleta de cores personalizada
def gerar_paleta_cores(n_cores):
    """Gera uma paleta de cores vibrantes e harmoniosas"""
    paleta = []
    for i in range(n_cores):
        # Usar HSV para criar cores bem distribuídas (matiz, saturação, valor)
        h = i/n_cores  # Matiz uniformemente distribuída
        s = 0.7  # Saturação alta para cores vibrantes
        v = 0.9  # Valor alto para cores brilhantes
        r, g, b = colorsys.hsv_to_rgb(h, s, v)
        # Converter para formato hexadecimal usado pelo Plotly
        color = f'#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}'
        paleta.append(color)
    return paleta

# Função para carregar dados do MongoDB ou dos arquivos locais
def carregar_dados():
    """
    Carrega dados do MongoDB ou dos arquivos locais CSV/Excel
    
    Returns:
        pandas.DataFrame: DataFrame com os dados das empresas
    """
    try:
        # Primeiro tenta carregar do MongoDB
        mongo_manager = MongoDBManager()
        dados = mongo_manager.buscar_todos()
        mongo_manager.close()
        
        if dados:
            return pd.DataFrame(dados)
        else:
            # Se não conseguir, tenta carregar do arquivo Excel
            diretorio_data = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
            caminho_excel = os.path.join(diretorio_data, 'dados_empresas.xlsx')
            
            if os.path.exists(caminho_excel):
                df = pd.read_excel(caminho_excel)
                print("Carregou do Excel. Colunas:", df.columns.tolist())
                return df
            else:
                # Se não encontrar o Excel, tenta o CSV
                caminho_csv = os.path.join(diretorio_data, 'dados_empresas.csv')
                if os.path.exists(caminho_csv):
                    df = pd.read_csv(caminho_csv, sep=';', encoding='utf-8-sig')
                    print("Carregou do CSV. Colunas:", df.columns.tolist())
                    return df
                else:
                    raise FileNotFoundError("Arquivos de dados não encontrados")
    except Exception as e:
        print(f"Erro ao carregar dados: {str(e)}")
        return pd.DataFrame()

def converter_para_float(valor):
    """
    Converte um valor monetário em string para float
    """
    if isinstance(valor, (int, float)):
        return float(valor)
    elif isinstance(valor, str):
        # Remove R$, espaços e converte vírgulas para pontos
        limpo = re.sub(r'[R$\s.]', '', valor).replace(',', '.')
        return float(limpo)
    else:
        return np.nan

def normalizar_colunas(df):
    """
    Normaliza os nomes das colunas para um formato padrão
    """
    # Mapeamento de nomes em português para nomes padronizados
    mapeamento = {
        'Nome da Empresa': 'nome_empresa',
        'Setor': 'setor',
        'Receita Anual': 'receita_anual',
        'Nº de Funcionários': 'numero_funcionarios', 
        'Nº Funcionários': 'numero_funcionarios',
        'País': 'pais',
        'Data de Fundação': 'data_fundacao',
        'Ano de Fundação': 'ano_fundacao',
        'Ano Fundação': 'ano_fundacao',
        'ID': 'id'
    }
    
    # Renomear colunas que existem no mapeamento
    colunas_para_renomear = {col: mapeamento[col] for col in df.columns if col in mapeamento}
    if colunas_para_renomear:
        df = df.rename(columns=colunas_para_renomear)
    
    # Verificar se a coluna ano_fundacao existe, caso contrário tentar criá-la
    if 'ano_fundacao' not in df.columns and 'data_fundacao' in df.columns:
        try:
            df['data_fundacao'] = pd.to_datetime(df['data_fundacao'])
            df['ano_fundacao'] = df['data_fundacao'].dt.year
        except:
            print("Não foi possível extrair o ano da data de fundação")
    
    # Adicionar outras colunas derivadas para enriquecer a análise
    if 'receita_anual' in df.columns and 'numero_funcionarios' in df.columns:
        # Calcular receita por funcionário
        df['receita_por_funcionario'] = df['receita_anual'] / df['numero_funcionarios']
    
    # Categorizar empresas por faixa de receita
    if 'receita_anual' in df.columns:
        bins = [0, 10e6, 100e6, 500e6, 1e9, float('inf')]
        labels = ['Micro', 'Pequena', 'Média', 'Grande', 'Corporação']
        df['porte'] = pd.cut(df['receita_anual'], bins=bins, labels=labels)
    
    # Idade da empresa em anos
    if 'ano_fundacao' in df.columns:
        ano_atual = datetime.now().year
        df['idade_empresa'] = ano_atual - df['ano_fundacao']
    
    return df

# Busca o código ISO alpha-3 do país (para o mapa)
def obter_codigo_pais(nome_pais):
    try:
        pais = pycountry.countries.search_fuzzy(nome_pais)
        if pais:
            return pais[0].alpha_3
        return None
    except:
        return None

# Carregar os dados
df = carregar_dados()

# Normalizar os nomes das colunas
df = normalizar_colunas(df)

# Verificar se há colunas específicas para formatação
if 'receita_anual' in df.columns:
    # Converter valores para float
    df['receita_anual'] = df['receita_anual'].apply(converter_para_float)

# Adicionar códigos ISO para países (útil para mapas)
if 'pais' in df.columns:
    df['codigo_pais'] = df['pais'].apply(obter_codigo_pais)

# Criar paleta de cores personalizada para os setores
setores_unicos = df['setor'].unique()
paleta_cores = gerar_paleta_cores(len(setores_unicos))
mapa_cores_setores = dict(zip(setores_unicos, paleta_cores))

# Garantir que temos todas as colunas necessárias
colunas_obrigatorias = ['nome_empresa', 'setor', 'receita_anual', 'numero_funcionarios', 'pais', 'ano_fundacao']
for col in colunas_obrigatorias:
    if col not in df.columns:
        print(f"Atenção: Coluna {col} não encontrada no DataFrame. Colunas disponíveis: {df.columns.tolist()}")

# Definir valores padrão para uso nos sliders
receita_max = 1000
if 'receita_anual' in df.columns:
    receita_max = round(df['receita_anual'].max()/1e6)

funcionarios_max = 500
if 'numero_funcionarios' in df.columns:
    funcionarios_max = df['numero_funcionarios'].max()

ano_min = 1970
ano_max = 2025
if 'ano_fundacao' in df.columns:
    ano_min = df['ano_fundacao'].min()
    ano_max = df['ano_fundacao'].max()

# Criar marcações para os sliders
receita_marks = {i: f'{i}M' for i in range(0, receita_max + 100, 100)}
funcionarios_marks = {i: str(i) for i in range(0, funcionarios_max + 100, 100)}
ano_marks = {i: str(i) for i in range(ano_min, ano_max + 1, 5)}

# Inicializar o app Dash com tema escuro Bootstrap
app = Dash(__name__, external_stylesheets=[dbc.themes.DARKLY])

# Navbar superior
navbar = dbc.NavbarSimple(
    children=[
        dbc.DropdownMenu(
            children=[
                dbc.DropdownMenuItem("Visão Geral", href="#"),
                dbc.DropdownMenuItem("Análise por Setor", href="#"),
                dbc.DropdownMenuItem("Distribuição Geográfica", href="#"),
                dbc.DropdownMenuItem("Desempenho por Porte", href="#"),
            ],
            nav=True,
            in_navbar=True,
            label="Visualizações",
        ),
        dbc.NavItem(dbc.NavLink("Sobre", href="#")),
    ],
    brand="Dashboard Corporativo - Análise de Empresas",
    brand_href="#",
    color="primary",
    dark=True,
)

# Cards para métricas principais
def criar_card_metrica(titulo, valor, subtitulo, icone, cor):
    return dbc.Card(
        [
            dbc.CardBody(
                [
                    html.Div(
                        [
                            html.I(className=f"fas {icone} fa-2x", style={"color": cor}),
                            html.H4(titulo, className="card-title ml-2", style={"color": cor}),
                        ],
                        className="d-flex align-items-center"
                    ),
                    html.H2(valor, className="card-text"),
                    html.P(subtitulo, className="card-text text-muted"),
                ]
            ),
        ],
        className="shadow mb-4 bg-dark",
        style={"border-left": f"4px solid {cor}"}
    )

# Layout do dashboard
app.layout = html.Div([
    navbar,
    dbc.Container([
        # Seção de cartões com métricas-chave
        dbc.Row([
            dbc.Col(
                criar_card_metrica(
                    "Total de Empresas", 
                    f"{len(df)}", 
                    "Cadastradas na base de dados", 
                    "fa-building", 
                    "#3498db"
                ), 
                width=3
            ),
            dbc.Col(
                criar_card_metrica(
                    "Receita Total", 
                    f"R$ {df['receita_anual'].sum()/1e9:.2f} Bi", 
                    "Soma de todas as empresas", 
                    "fa-money-bill-wave", 
                    "#2ecc71"
                ), 
                width=3
            ),
            dbc.Col(
                criar_card_metrica(
                    "Funcionários", 
                    f"{df['numero_funcionarios'].sum():,.0f}", 
                    "Total de colaboradores", 
                    "fa-users", 
                    "#e74c3c"
                ), 
                width=3
            ),
            dbc.Col(
                criar_card_metrica(
                    "Receita Média", 
                    f"R$ {df['receita_anual'].mean()/1e6:.2f} Mi", 
                    "Por empresa", 
                    "fa-chart-line", 
                    "#f39c12"
                ), 
                width=3
            ),
        ], className="mb-4 mt-4"),
        
        # Tabs para diferentes visualizações
        dbc.Tabs([
            dbc.Tab(label="Visão Geral", tab_id="visao-geral", children=[
                dbc.Row([
                    # Painel de filtros
                    dbc.Col([
                        html.Div([
                            html.H5("Filtros de Análise", className="text-center bg-primary text-white p-2 rounded-top"),
                            html.Div([
                                html.Label("Selecione o Setor:", className="font-weight-bold mt-2"),
                                dcc.Dropdown(
                                    id='setor-dropdown',
                                    options=[{'label': setor, 'value': setor} for setor in df['setor'].unique()],
                                    value=[],
                                    multi=True,
                                    className="mb-3"
                                ),
                                
                                html.Label("Faixa de Receita Anual (em milhões R$):", className="font-weight-bold"),
                                dcc.RangeSlider(
                                    id='receita-slider',
                                    min=0,
                                    max=receita_max,
                                    step=10,
                                    marks=receita_marks,
                                    value=[0, receita_max],
                                    className="mb-3"
                                ),
                                
                                html.Label("Faixa de Funcionários:", className="font-weight-bold"),
                                dcc.RangeSlider(
                                    id='funcionarios-slider',
                                    min=0,
                                    max=funcionarios_max,
                                    step=50,
                                    marks=funcionarios_marks,
                                    value=[0, funcionarios_max],
                                    className="mb-3"
                                ),
                                
                                html.Label("Período de Fundação:", className="font-weight-bold"),
                                dcc.RangeSlider(
                                    id='ano-slider',
                                    min=ano_min,
                                    max=ano_max,
                                    step=1,
                                    marks=ano_marks,
                                    value=[ano_min, ano_max],
                                    className="mb-3"
                                ),
                                
                                html.Label("Porte da Empresa:", className="font-weight-bold"),
                                dcc.Checklist(
                                    id='porte-checklist',
                                    options=[{'label': p, 'value': p} for p in df['porte'].unique()],
                                    value=df['porte'].unique().tolist(),
                                    inline=True,
                                    className="mb-3"
                                ),
                                
                                html.Label("Top N Empresas por Receita:", className="font-weight-bold"),
                                dcc.Slider(
                                    id='top-n-slider',
                                    min=5,
                                    max=50,
                                    step=5,
                                    marks={i: str(i) for i in range(5, 51, 5)},
                                    value=10,
                                    className="mb-4"
                                ),
                                
                                html.Button(
                                    "Aplicar Filtros", 
                                    id="aplicar-filtros-btn", 
                                    className="btn btn-primary btn-block mb-2"
                                ),
                                html.Button(
                                    "Limpar Filtros", 
                                    id="limpar-filtros-btn", 
                                    className="btn btn-secondary btn-block"
                                )
                            ], className="p-3 border rounded-bottom")
                        ], className="shadow"),
                        
                        # Resumo de seleção
                        html.Div([
                            html.H5("Resumo da Seleção", className="text-center bg-info text-white p-2 rounded-top mt-4"),
                            html.Div(id='resumo-selecao', className="p-3 border rounded-bottom")
                        ], className="shadow")
                    ], width=3, className="mb-4"),
                    
                    # Gráficos principais
                    dbc.Col([
                        dbc.Row([
                            dbc.Col([
                                dbc.Card([
                                    dbc.CardHeader(html.H5("Distribuição por Setor", className="card-title")),
                                    dbc.CardBody([
                                        dcc.Graph(id='grafico-pizza')
                                    ])
                                ], className="shadow h-100")
                            ], width=6),
                            dbc.Col([
                                dbc.Card([
                                    dbc.CardHeader(html.H5("Receita Média por Setor", className="card-title")),
                                    dbc.CardBody([
                                        dcc.Graph(id='grafico-barras-receita')
                                    ])
                                ], className="shadow h-100")
                            ], width=6),
                        ], className="mb-4"),
                        
                        dbc.Row([
                            dbc.Col([
                                dbc.Card([
                                    dbc.CardHeader(html.H5("Número Médio de Funcionários por Setor", className="card-title")),
                                    dbc.CardBody([
                                        dcc.Graph(id='grafico-barras-funcionarios')
                                    ])
                                ], className="shadow h-100")
                            ], width=6),
                            dbc.Col([
                                dbc.Card([
                                    dbc.CardHeader(html.H5("Tendência de Fundação por Setor", className="card-title")),
                                    dbc.CardBody([
                                        dcc.Graph(id='grafico-linha-tempo')
                                    ])
                                ], className="shadow h-100")
                            ], width=6),
                        ], className="mb-4"),
                    ], width=9),
                ]),
                
                # Nova seção para visualizações adicionais e tabela
                dbc.Row([
                    dbc.Col([
                        dbc.Card([
                            dbc.CardHeader(html.H5("Top Empresas por Receita", className="card-title")),
                            dbc.CardBody([
                                dcc.Graph(id='grafico-top-empresas')
                            ])
                        ], className="shadow")
                    ], width=6),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardHeader(html.H5("Relação Receita vs. Funcionários", className="card-title")),
                            dbc.CardBody([
                                dcc.Graph(id='grafico-scatter')
                            ])
                        ], className="shadow")
                    ], width=6),
                ], className="mb-4"),
                
                dbc.Row([
                    dbc.Col([
                        dbc.Card([
                            dbc.CardHeader([
                                html.Div([
                                    html.H5("Dados Detalhados", className="card-title d-inline"),
                                    html.Div([
                                        dbc.Button("CSV", id="btn-csv", color="primary", className="ml-2"),
                                        dbc.Button("Excel", id="btn-excel", color="success", className="ml-2"),
                                    ], className="float-right")
                                ], className="d-flex justify-content-between")
                            ]),
                            dbc.CardBody([
                                html.Div(id='tabela-dados')
                            ])
                        ], className="shadow")
                    ], width=12),
                ]),
            ]),
            
            # Tab de análise geográfica
            dbc.Tab(label="Distribuição Geográfica", tab_id="distribuicao-geografica", children=[
                dbc.Row([
                    dbc.Col([
                        dbc.Card([
                            dbc.CardHeader(html.H5("Distribuição Global de Empresas", className="card-title")),
                            dbc.CardBody([
                                dcc.Graph(id='mapa-empresas')
                            ])
                        ], className="shadow")
                    ], width=12),
                ], className="mb-4 mt-4"),
                
                dbc.Row([
                    dbc.Col([
                        dbc.Card([
                            dbc.CardHeader(html.H5("Top 10 Países por Receita Total", className="card-title")),
                            dbc.CardBody([
                                dcc.Graph(id='grafico-paises-receita')
                            ])
                        ], className="shadow")
                    ], width=6),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardHeader(html.H5("Top 10 Países por Número de Empresas", className="card-title")),
                            dbc.CardBody([
                                dcc.Graph(id='grafico-paises-quantidade')
                            ])
                        ], className="shadow")
                    ], width=6),
                ], className="mb-4"),
            ]),
            
            # Tab de análise por porte
            dbc.Tab(label="Análise por Porte", tab_id="analise-porte", children=[
                dbc.Row([
                    dbc.Col([
                        dbc.Card([
                            dbc.CardHeader(html.H5("Distribuição de Empresas por Porte", className="card-title")),
                            dbc.CardBody([
                                dcc.Graph(id='grafico-porte-pie')
                            ])
                        ], className="shadow")
                    ], width=6),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardHeader(html.H5("Receita Média por Porte", className="card-title")),
                            dbc.CardBody([
                                dcc.Graph(id='grafico-porte-receita')
                            ])
                        ], className="shadow")
                    ], width=6),
                ], className="mb-4 mt-4"),
                
                dbc.Row([
                    dbc.Col([
                        dbc.Card([
                            dbc.CardHeader(html.H5("Evolução da Composição por Porte ao Longo do Tempo", className="card-title")),
                            dbc.CardBody([
                                dcc.Graph(id='grafico-porte-tempo')
                            ])
                        ], className="shadow")
                    ], width=12),
                ], className="mb-4"),
            ]),
            
            # Tab de insights e previsões
            dbc.Tab(label="Insights", tab_id="insights", children=[
                dbc.Row([
                    dbc.Col([
                        dbc.Card([
                            dbc.CardHeader(html.H5("Principais Insights", className="card-title")),
                            dbc.CardBody([
                                html.Div(id='insights-automaticos')
                            ])
                        ], className="shadow")
                    ], width=12),
                ], className="mb-4 mt-4"),
                
                dbc.Row([
                    dbc.Col([
                        dbc.Card([
                            dbc.CardHeader(html.H5("Correlação entre Métricas", className="card-title")),
                            dbc.CardBody([
                                dcc.Graph(id='grafico-correlacao')
                            ])
                        ], className="shadow")
                    ], width=12),
                ], className="mb-4"),
            ]),
        ], id="tabs-principal", active_tab="visao-geral"),
        
        # Rodapé
        html.Footer([
            html.Hr(),
            html.P([
                "Dashboard Corporativo de Análise de Dados © 2025 | ",
                html.A("Projeto MongoDB", href="#", className="text-light")
            ], className="text-center text-muted")
        ])
    ], fluid=True)
], style={"background-color": "#121212"})

# Callbacks para atualizar os elementos
@app.callback(
    [Output('grafico-pizza', 'figure'),
     Output('grafico-barras-receita', 'figure'),
     Output('grafico-barras-funcionarios', 'figure'),
     Output('grafico-linha-tempo', 'figure'),
     Output('grafico-top-empresas', 'figure'),
     Output('grafico-scatter', 'figure'),
     Output('resumo-selecao', 'children'),
     Output('tabela-dados', 'children')],
    [Input('aplicar-filtros-btn', 'n_clicks')],
    [State('setor-dropdown', 'value'),
     State('receita-slider', 'value'),
     State('funcionarios-slider', 'value'),
     State('ano-slider', 'value'),
     State('porte-checklist', 'value'),
     State('top-n-slider', 'value')]
)
def update_graficos(n_clicks, setores_selecionados, faixa_receita, faixa_funcionarios, faixa_ano, porte_selecionado, top_n):
    # Filtrar o dataframe com base nos inputs
    dff = df.copy()
    
    # Filtrar por setor se algum for selecionado
    if setores_selecionados:
        dff = dff[dff['setor'].isin(setores_selecionados)]
    
    # Filtrar por faixa de receita (convertendo para milhões)
    dff = dff[(dff['receita_anual'] >= faixa_receita[0] * 1e6) & 
              (dff['receita_anual'] <= faixa_receita[1] * 1e6)]
    
    # Filtrar por faixa de funcionários
    dff = dff[(dff['numero_funcionarios'] >= faixa_funcionarios[0]) & 
              (dff['numero_funcionarios'] <= faixa_funcionarios[1])]
    
    # Filtrar por faixa de ano de fundação
    dff = dff[(dff['ano_fundacao'] >= faixa_ano[0]) & 
              (dff['ano_fundacao'] <= faixa_ano[1])]
    
    # Filtrar por porte
    if porte_selecionado:
        dff = dff[dff['porte'].isin(porte_selecionado)]
    
    # Criar gráfico de pizza com design aprimorado
    contagem_setor = dff['setor'].value_counts().reset_index()
    contagem_setor.columns = ['setor', 'contagem']
    
    fig_pizza = px.pie(
        contagem_setor, 
        values='contagem', 
        names='setor',
        color='setor',
        color_discrete_map=mapa_cores_setores,
        hole=0.4,
        template="plotly_dark"
    )
    fig_pizza.update_traces(
        textinfo='percent+label', 
        textfont_size=12,
        marker=dict(line=dict(color='#000000', width=1.5))
    )
    fig_pizza.update_layout(
        legend_title_text='Setores',
        margin=dict(t=30, b=0, l=10, r=10),
        legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5)
    )
    
    # Criar gráfico de barras para receita média com design melhorado
    receita_por_setor = dff.groupby('setor')['receita_anual'].mean().reset_index()
    receita_por_setor = receita_por_setor.sort_values('receita_anual', ascending=False)
    
    fig_barras_receita = go.Figure()
    for i, setor in enumerate(receita_por_setor['setor']):
        valor = receita_por_setor.loc[receita_por_setor['setor'] == setor, 'receita_anual'].values[0]
        fig_barras_receita.add_trace(go.Bar(
            x=[setor],
            y=[valor/1e6],  # Converter para milhões
            name=setor,
            marker_color=mapa_cores_setores.get(setor, '#636EFA'),
            text=f"R$ {valor/1e6:.1f}M",
            textposition='auto'
        ))
    
    fig_barras_receita.update_layout(
        template="plotly_dark",
        xaxis_title="Setor",
        yaxis_title="Receita Média (Milhões R$)",
        showlegend=False,
        margin=dict(t=30, b=0, l=10, r=10),
        yaxis=dict(gridcolor='rgba(255,255,255,0.1)')
    )
    
    # Criar gráfico de barras para número médio de funcionários
    funcionarios_por_setor = dff.groupby('setor')['numero_funcionarios'].mean().reset_index()
    funcionarios_por_setor = funcionarios_por_setor.sort_values('numero_funcionarios', ascending=False)
    
    fig_barras_funcionarios = go.Figure()
    for i, setor in enumerate(funcionarios_por_setor['setor']):
        valor = funcionarios_por_setor.loc[funcionarios_por_setor['setor'] == setor, 'numero_funcionarios'].values[0]
        fig_barras_funcionarios.add_trace(go.Bar(
            x=[setor],
            y=[valor],
            name=setor,
            marker_color=mapa_cores_setores.get(setor, '#636EFA'),
            text=f"{valor:.0f}",
            textposition='auto'
        ))
    
    fig_barras_funcionarios.update_layout(
        template="plotly_dark",
        xaxis_title="Setor",
        yaxis_title="Média de Funcionários",
        showlegend=False,
        margin=dict(t=30, b=0, l=10, r=10),
        yaxis=dict(gridcolor='rgba(255,255,255,0.1)')
    )
    
    # Criar gráfico de linha do tempo avançado
    fundacao_por_ano = dff.groupby(['ano_fundacao', 'setor']).size().reset_index(name='contagem')
    
    fig_linha_tempo = px.line(
        fundacao_por_ano,
        x='ano_fundacao',
        y='contagem',
        color='setor',
        markers=True,
        color_discrete_map=mapa_cores_setores,
        template="plotly_dark"
    )
    
    fig_linha_tempo.update_traces(
        line=dict(width=3),
        marker=dict(size=8)
    )
    
    fig_linha_tempo.update_layout(
        xaxis_title="Ano de Fundação",
        yaxis_title="Número de Empresas",
        legend_title="Setor",
        margin=dict(t=30, b=0, l=10, r=10),
        xaxis=dict(gridcolor='rgba(255,255,255,0.1)'),
        yaxis=dict(gridcolor='rgba(255,255,255,0.1)'),
        legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5)
    )
    
    # Top N empresas por receita (gráfico horizontal)
    top_empresas = dff.sort_values('receita_anual', ascending=False).head(top_n)
    
    fig_top_empresas = px.bar(
        top_empresas,
        y='nome_empresa',
        x='receita_anual',
        color='setor',
        color_discrete_map=mapa_cores_setores,
        orientation='h',
        template="plotly_dark",
        labels={'receita_anual': 'Receita Anual (R$)', 'nome_empresa': 'Empresa', 'setor': 'Setor'},
        height=500
    )
    
    fig_top_empresas.update_layout(
        yaxis={'categoryorder': 'total ascending'},
        margin=dict(t=30, b=0, l=10, r=10),
        xaxis=dict(gridcolor='rgba(255,255,255,0.1)')
    )
    
    # Gráfico de dispersão: receita vs funcionários
    fig_scatter = px.scatter(
        dff, 
        x='numero_funcionarios', 
        y='receita_anual',
        size='receita_anual',
        color='setor',
        color_discrete_map=mapa_cores_setores,
        hover_name='nome_empresa',
        log_y=True,  # Escala logarítmica para melhor visualização
        template="plotly_dark",
        labels={
            'numero_funcionarios': 'Número de Funcionários',
            'receita_anual': 'Receita Anual (R$)',
            'setor': 'Setor'
        }
    )
    
    fig_scatter.update_layout(
        margin=dict(t=30, b=0, l=10, r=10),
        xaxis=dict(gridcolor='rgba(255,255,255,0.1)'),
        yaxis=dict(gridcolor='rgba(255,255,255,0.1)'),
        legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5)
    )
    
    # Resumo da seleção
    resumo = html.Div([
        html.P([
            html.Strong("Empresas selecionadas: "), 
            f"{len(dff)} de {len(df)} ({len(dff)/len(df)*100:.1f}%)"
        ]),
        html.P([
            html.Strong("Receita total: "), 
            f"R$ {dff['receita_anual'].sum()/1e9:.2f} bilhões"
        ]),
        html.P([
            html.Strong("Funcionários: "), 
            f"{dff['numero_funcionarios'].sum():,.0f}"
        ]),
        html.P([
            html.Strong("Média de funcionários: "), 
            f"{dff['numero_funcionarios'].mean():.0f} por empresa"
        ]),
        html.P([
            html.Strong("Setores: "), 
            f"{len(dff['setor'].unique())} diferentes"
        ]),
        html.P([
            html.Strong("Período: "), 
            f"Empresas fundadas entre {dff['ano_fundacao'].min()} e {dff['ano_fundacao'].max()}"
        ]),
    ])
    
    # Criar tabela de dados com design melhorado
    table_df = dff.copy()
    table_df['receita_anual_formatada'] = table_df['receita_anual'].apply(lambda x: f"R$ {x:,.2f}")
    
    # Selecionar colunas para mostrar
    table_df = table_df[['nome_empresa', 'setor', 'receita_anual_formatada', 'numero_funcionarios', 'pais', 'ano_fundacao', 'porte']]
    table_df.columns = ['Nome da Empresa', 'Setor', 'Receita Anual', 'Nº Funcionários', 'País', 'Ano Fundação', 'Porte']
    
    tabela = dash_table.DataTable(
        id='tabela',
        columns=[{"name": i, "id": i} for i in table_df.columns],
        data=table_df.to_dict('records'),
        style_table={'overflowX': 'auto'},
        style_header={
            'backgroundColor': '#2C3E50',
            'color': 'white',
            'fontWeight': 'bold',
            'border': '1px solid #222'
        },
        style_cell={
            'backgroundColor': '#1E293B',
            'color': 'white',
            'border': '1px solid #222',
            'padding': '8px',
            'textAlign': 'left'
        },
        style_data_conditional=[
            {
                'if': {'row_index': 'odd'},
                'backgroundColor': '#172331'
            }
        ],
        page_size=10,
        filter_action="native",
        sort_action="native",
        sort_mode="multi",
        page_action="native"
    )
    
    return fig_pizza, fig_barras_receita, fig_barras_funcionarios, fig_linha_tempo, fig_top_empresas, fig_scatter, resumo, tabela

# Callback para limpar filtros
@app.callback(
    [Output('setor-dropdown', 'value'),
     Output('receita-slider', 'value'),
     Output('funcionarios-slider', 'value'),
     Output('ano-slider', 'value'),
     Output('porte-checklist', 'value')],
    [Input('limpar-filtros-btn', 'n_clicks')]
)
def limpar_filtros(n_clicks):
    if n_clicks is None:
        raise PreventUpdate
    return [], [0, receita_max], [0, funcionarios_max], [ano_min, ano_max], df['porte'].unique().tolist()

# Callbacks para visualizações de distribuição geográfica
@app.callback(
    [Output('mapa-empresas', 'figure'),
     Output('grafico-paises-receita', 'figure'),
     Output('grafico-paises-quantidade', 'figure')],
    [Input('tabs-principal', 'active_tab')]
)
def update_visualizacoes_geograficas(tab):
    if tab != "distribuicao-geografica":
        raise PreventUpdate
    
    # Mapa mundial de empresas
    dff = df.copy()
    
    # Agrupar dados por país
    dados_pais = dff.groupby('pais').agg({
        'nome_empresa': 'count',
        'receita_anual': 'sum',
        'numero_funcionarios': 'sum',
        'codigo_pais': 'first'
    }).reset_index()
    
    dados_pais.columns = ['pais', 'quantidade_empresas', 'receita_total', 'funcionarios_total', 'codigo_pais']
    
    # Criar mapa
    fig_mapa = px.choropleth(
        dados_pais,
        locations="codigo_pais",
        color="receita_total",
        hover_name="pais",
        hover_data={
            "codigo_pais": False,
            "quantidade_empresas": True,
            "receita_total": ':,.2f',
            "funcionarios_total": ':,',
        },
        color_continuous_scale=px.colors.sequential.Plasma,
        template="plotly_dark",
        projection="natural earth"
    )
    
    fig_mapa.update_layout(
        margin=dict(t=0, b=0, l=0, r=0),
        coloraxis_colorbar_title="Receita Total",
        geo=dict(
            showframe=False,
            showcoastlines=True,
            projection_type='equirectangular',
            bgcolor='rgba(0,0,0,0)'
        )
    )
    
    # Top 10 países por receita
    top_paises_receita = dados_pais.sort_values('receita_total', ascending=False).head(10)
    
    fig_paises_receita = px.bar(
        top_paises_receita,
        x='pais',
        y='receita_total',
        color='receita_total',
        color_continuous_scale=px.colors.sequential.Plasma,
        template="plotly_dark",
        labels={
            'pais': 'País',
            'receita_total': 'Receita Total (R$)'
        }
    )
    
    fig_paises_receita.update_layout(
        xaxis_title="País",
        yaxis_title="Receita Total (R$)",
        margin=dict(t=30, b=0, l=10, r=10),
        xaxis=dict(gridcolor='rgba(255,255,255,0.1)'),
        yaxis=dict(gridcolor='rgba(255,255,255,0.1)')
    )
    
    # Top 10 países por quantidade de empresas
    top_paises_quantidade = dados_pais.sort_values('quantidade_empresas', ascending=False).head(10)
    
    fig_paises_quantidade = px.bar(
        top_paises_quantidade,
        x='pais',
        y='quantidade_empresas',
        color='quantidade_empresas',
        color_continuous_scale=px.colors.sequential.Viridis,
        template="plotly_dark",
        labels={
            'pais': 'País',
            'quantidade_empresas': 'Número de Empresas'
        }
    )
    
    fig_paises_quantidade.update_layout(
        xaxis_title="País",
        yaxis_title="Número de Empresas",
        margin=dict(t=30, b=0, l=10, r=10),
        xaxis=dict(gridcolor='rgba(255,255,255,0.1)'),
        yaxis=dict(gridcolor='rgba(255,255,255,0.1)')
    )
    
    return fig_mapa, fig_paises_receita, fig_paises_quantidade

# Callbacks para visualizações de análise por porte
@app.callback(
    [Output('grafico-porte-pie', 'figure'),
     Output('grafico-porte-receita', 'figure'),
     Output('grafico-porte-tempo', 'figure')],
    [Input('tabs-principal', 'active_tab')]
)
def update_visualizacoes_porte(tab):
    if tab != "analise-porte":
        raise PreventUpdate
    
    dff = df.copy()
    
    # Distribuição por porte
    contagem_porte = dff['porte'].value_counts().reset_index()
    contagem_porte.columns = ['porte', 'contagem']
    
    cores_porte = {
        'Micro': '#3498db',
        'Pequena': '#2ecc71',
        'Média': '#f39c12',
        'Grande': '#e74c3c',
        'Corporação': '#9b59b6'
    }
    
    fig_porte_pie = px.pie(
        contagem_porte, 
        names='porte', 
        values='contagem',
        color='porte',
        color_discrete_map=cores_porte,
        template="plotly_dark",
        hole=0.4
    )
    
    fig_porte_pie.update_traces(
        textinfo='percent+label',
        textfont_size=12,
        marker=dict(line=dict(color='#000000', width=1.5))
    )
    
    fig_porte_pie.update_layout(
        legend_title_text='Porte',
        margin=dict(t=30, b=0, l=10, r=10),
        legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5)
    )
    
    # Receita média por porte
    receita_por_porte = dff.groupby('porte')['receita_anual'].mean().reset_index()
    
    # Garantir ordenação correta
    ordem_porte = ['Micro', 'Pequena', 'Média', 'Grande', 'Corporação']
    receita_por_porte['porte'] = pd.Categorical(
        receita_por_porte['porte'], 
        categories=ordem_porte, 
        ordered=True
    )
    receita_por_porte = receita_por_porte.sort_values('porte')
    
    fig_porte_receita = px.bar(
        receita_por_porte,
        x='porte',
        y='receita_anual',
        color='porte',
        color_discrete_map=cores_porte,
        template="plotly_dark",
        labels={
            'porte': 'Porte',
            'receita_anual': 'Receita Média (R$)'
        }
    )
    
    fig_porte_receita.update_layout(
        xaxis_title="Porte",
        yaxis_title="Receita Média (R$)",
        showlegend=False,
        margin=dict(t=30, b=0, l=10, r=10),
        xaxis=dict(gridcolor='rgba(255,255,255,0.1)'),
        yaxis=dict(gridcolor='rgba(255,255,255,0.1)')
    )
    
    # Evolução por porte ao longo do tempo
    evolucao_porte = dff.groupby(['ano_fundacao', 'porte']).size().reset_index(name='contagem')
    evolucao_porte['porte'] = pd.Categorical(
        evolucao_porte['porte'], 
        categories=ordem_porte, 
        ordered=True
    )
    
    fig_porte_tempo = px.area(
        evolucao_porte,
        x="ano_fundacao",
        y="contagem",
        color="porte",
        color_discrete_map=cores_porte,
        template="plotly_dark",
        labels={
            'ano_fundacao': 'Ano de Fundação',
            'contagem': 'Número de Empresas',
            'porte': 'Porte'
        }
    )
    
    fig_porte_tempo.update_layout(
        xaxis_title="Ano de Fundação",
        yaxis_title="Número de Empresas",
        margin=dict(t=30, b=0, l=10, r=10),
        xaxis=dict(gridcolor='rgba(255,255,255,0.1)'),
        yaxis=dict(gridcolor='rgba(255,255,255,0.1)'),
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5)
    )
    
    return fig_porte_pie, fig_porte_receita, fig_porte_tempo

# Callback para gerar insights automáticos
@app.callback(
    [Output('insights-automaticos', 'children'),
     Output('grafico-correlacao', 'figure')],
    [Input('tabs-principal', 'active_tab')]
)
def gerar_insights(tab):
    if tab != "insights":
        raise PreventUpdate
    
    dff = df.copy()
    
    # Lista para armazenar insights
    insights_list = []
    
    # 1. Setor com maior receita média
    setor_maior_receita = dff.groupby('setor')['receita_anual'].mean().idxmax()
    valor_maior_receita = dff.groupby('setor')['receita_anual'].mean().max()
    insights_list.append(
        dbc.Alert(
            [
                html.I(className="fas fa-chart-line mr-2"),
                html.Strong("Setor mais lucrativo: "),
                f"O setor de {setor_maior_receita} apresenta a maior receita média (R$ {valor_maior_receita/1e6:.2f} milhões)."
            ],
            color="success",
            className="mb-3"
        )
    )
    
    # 2. Setor com mais empresas
    setor_mais_empresas = dff['setor'].value_counts().idxmax()
    qtd_empresas = dff['setor'].value_counts().max()
    insights_list.append(
        dbc.Alert(
            [
                html.I(className="fas fa-building mr-2"),
                html.Strong("Setor predominante: "),
                f"O setor de {setor_mais_empresas} possui o maior número de empresas ({qtd_empresas}), representando {qtd_empresas/len(dff)*100:.1f}% do total."
            ],
            color="info",
            className="mb-3"
        )
    )
    
    # 3. Eficiência (receita por funcionário)
    dff['receita_por_funcionario'] = dff['receita_anual'] / dff['numero_funcionarios']
    setor_mais_eficiente = dff.groupby('setor')['receita_por_funcionario'].mean().idxmax()
    valor_eficiencia = dff.groupby('setor')['receita_por_funcionario'].mean().max()
    insights_list.append(
        dbc.Alert(
            [
                html.I(className="fas fa-bolt mr-2"),
                html.Strong("Setor mais eficiente: "),
                f"O setor de {setor_mais_eficiente} apresenta a maior receita por funcionário (R$ {valor_eficiencia/1e3:.2f} mil por funcionário)."
            ],
            color="warning",
            className="mb-3"
        )
    )
    
    # 4. Tendência de crescimento
    anos = sorted(dff['ano_fundacao'].unique())
    setores_recentes = dff[dff['ano_fundacao'] >= anos[-5]]['setor'].value_counts()
    setor_crescimento = setores_recentes.idxmax()
    insights_list.append(
        dbc.Alert(
            [
                html.I(className="fas fa-arrow-trend-up mr-2"),
                html.Strong("Tendência de crescimento: "),
                f"O setor de {setor_crescimento} lidera em número de novas empresas nos últimos 5 anos, indicando uma tendência de expansão."
            ],
            color="primary",
            className="mb-3"
        )
    )
    
    # 5. Distribuição geográfica
    pais_dominante = dff['pais'].value_counts().idxmax()
    qtd_pais = dff['pais'].value_counts().max()
    insights_list.append(
        dbc.Alert(
            [
                html.I(className="fas fa-globe mr-2"),
                html.Strong("Concentração geográfica: "),
                f"{pais_dominante} é o país com maior número de empresas ({qtd_pais}), representando {qtd_pais/len(dff)*100:.1f}% do total."
            ],
            color="secondary",
            className="mb-3"
        )
    )
    
    # Mapa de correlação
    colunas_numericas = ['receita_anual', 'numero_funcionarios', 'ano_fundacao', 'idade_empresa', 'receita_por_funcionario']
    matriz_corr = dff[colunas_numericas].corr()
    
    # Renomear para melhor visualização
    nomes_colunas = {
        'receita_anual': 'Receita Anual',
        'numero_funcionarios': 'Nº Funcionários',
        'ano_fundacao': 'Ano Fundação',
        'idade_empresa': 'Idade Empresa',
        'receita_por_funcionario': 'Receita/Funcionário'
    }
    
    matriz_corr.index = [nomes_colunas[col] for col in matriz_corr.index]
    matriz_corr.columns = [nomes_colunas[col] for col in matriz_corr.columns]
    
    # Criar mapa de calor
    fig_correlacao = px.imshow(
        matriz_corr,
        text_auto='.2f',
        color_continuous_scale='RdBu_r',
        zmin=-1, zmax=1,
        template="plotly_dark"
    )
    
    fig_correlacao.update_layout(
        title_text='Correlação entre Métricas',
        margin=dict(t=40, b=0, l=10, r=10),
    )
    
    return insights_list, fig_correlacao

# Iniciar o app
if __name__ == '__main__':
    app.run(debug=True)