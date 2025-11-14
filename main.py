#%% Importando bibliotecas
import streamlit as st
import pandas as pd
import unicodedata
import geopandas as gpd
import plotly.express as px
from defs import recife
from streamlit_folium import st_folium
import folium
from folium.plugins import MarkerCluster, HeatMap, MiniMap, GroupedLayerControl
import branca.colormap as cm

#%% Base de dados
def limpar_acento(txt):
    if pd.isnull(txt):
        return txt
    txt = ''.join(ch for ch in unicodedata.normalize('NFKD', txt) 
        if not unicodedata.combining(ch))
    return txt

pb_demo = r'C:\Users\pedro.bastos\Documents\vscode\streamlit\dados\Infopbruto.geojson'

teatro = pd.read_excel(r'C:\Users\pedro.bastos\Documents\vscode\streamlit\dados\teatros.xlsx')
sic_f = (r'C:\Users\pedro.bastos\Documents\vscode\streamlit\dados\Cadastrados.xlsx')
sic_f


@st.cache_data
def load_sic_data(path_sic, recife):
    df = pd.read_excel(path_sic)
    df['bairro'] = df['bairro'].apply(limpar_acento).str.upper()
    return df.query('bairro in @recife')

@st.cache_data
def load_pb_demo(path_demo):
    return gpd.read_file(path_demo,engine="pyogrio")

df = load_sic_data(sic_f, recife)
dfb = load_pb_demo(pb_demo)

#%% Construção da parte lateral do streamlit
with st.sidebar:
    st.title("Cadastros Cultura do Recife")

    # --- listas ---
    lista_areas = sorted(df["area_atuacao"].dropna().unique().tolist()) + ["TODOS"]
    area_a = st.selectbox("Área de atuação", lista_areas)
    
    lista_bairros = sorted(dfb["EBAIRRNOMEOF"].dropna().unique().tolist()) + ["TODOS"]
    bairro = st.selectbox("Bairro", lista_bairros)

# --- criar dataframes filtráveis ---
df_area = df.copy()
dfb_map = dfb.copy()
df_pb  = df.copy()   

# FILTRO POR BAIRRO
if bairro != "TODOS":
    df_area = df_area[df_area["bairro"] == bairro]
    dfb_map = dfb_map[dfb_map["EBAIRRNOMEOF"] == bairro]
    df_pb  = df_pb[df_pb["bairro"] == bairro]

# FILTRO POR ÁREA
if area_a != "TODOS":
    df_area = df_area[df_area["area_atuacao"] == area_a]
#%% Construção do mapa

def display_mapa(df_area, dfb):
    
    # 1. Coordenadas para centralização do mapa.
    recife_coords = [-8.05428, -34.88126]
    m = folium.Map(location=recife_coords, zoom_start=13, tiles="OpenStreetMap")

    # Plugins
    marker_cluster = MarkerCluster(name='Cadastros totais', show=True).add_to(m)
    MiniMap(toggle_display=True).add_to(m)

    linear = cm.linear.Oranges_06.scale(0,20)
    linear.add_to(m)

    # ---- Resumo por bairro ----

    fgpb = folium.FeatureGroup(name='Resumo por Bairro', show=True)

    folium.GeoJson(
        dfb,
        name="Bairros",
        style_function=lambda f: {
            "color": "black",
            "weight": 0.5,
            "fillOpacity": 0.1
        },
        tooltip=folium.GeoJsonTooltip(
            fields=["EBAIRRNOMEOF", "inscritos", "total_pessoas"],
            aliases=["Bairro:", "Inscritos:", "Total Pessoas:"]
        ),
    ).add_to(fgpb)
    m.add_child(fgpb)

    # ---- Cluster geral ----
    for row in df_area.itertuples():
        popup = folium.Popup(
            f"Genero: {row.genero} \n Raça: {row.raca} \n Estilo: {row.area_atuacao}",
            parse_html=True, max_width="100"
        )
        folium.Circle(
            location=(row.latitude, row.longitude),
            radius=10,
            fill_color="green",
            fill_opacity=0.4,
            color="white",
            popup=popup
        ).add_to(marker_cluster)
    
    # Por grupo selecionado
    grupos_area = {}
    # Usar somente áreas contidas em df_area (corrige cluster duplicado/vazio)
    areas_unicas = df_area['area_atuacao'].dropna().unique()
    for area in areas_unicas:
        fcad = folium.FeatureGroup(name=area, show=False)
        cluster = MarkerCluster().add_to(fcad)
        # Agora filtra corretamente PARA CADA ÁREA
        df_area_unica = df_area[df_area['area_atuacao'] == area]
        for _, row in df_area_unica.iterrows():
            location = (row.latitude, row.longitude)
            popup_textl = folium.Popup(
                f"Genero: {row.genero} \n Raça: {row.raca} \n Estilo: {row.area_atuacao}",
                parse_html=True, max_width="100")
            folium.Circle(
                location=location,
                popup=popup_textl,
                radius=10,
                fill_color="white",
                fill_opacity=1,
                color="black",
                weight=1).add_to(cluster)
        grupos_area[area] = fcad
        m.add_child(fcad)
    
    # Equipamentos culturais
    fgt = folium.FeatureGroup(name='Teatro', show = True)
    for row in teatro.itertuples():
        #Definição de onde se encontra o local
        location_e = (row.latitude, row.longitude)
        popup_textep = folium.Popup(
            f"Nome: {row.equipamento}  \n Tipo: {row.tipo} \n Natureza: {row.natureza}",
                    parse_html=True, max_width="100%")
        folium.Marker(
            location=location_e,
            popup=popup_textep,
            tooltip=row.equipamento
        ).add_to(fgt)
    fgt.add_to(m)

    # ---- Painéis de seleção ----
    GroupedLayerControl(
        exclusive_groups=False,
        groups={
            'Individuais': [ fgt ],
            'Por Bairro': [fgpb],
        },
        collapsed=False
    ).add_to(m)

    GroupedLayerControl(exclusive_groups= False,
        groups={ 'Total': [marker_cluster],
            'Por Área de Atuação': list(grupos_area.values())},
        collapsed=False,
        position = 'topleft'
    ).add_to(m)

    return m

#%%Interior do site
# FICHA DA AREA DE ATUAÇÃ0
## Criando a função para obtenção dos dados SOBRE A AREA DE ATUAÇÃO (HEADER)
def dict_area(df):
    gb_cads = df.groupby(['area_atuacao']).agg(
            inscritos = ('nome','size'),
            genero_mv = ('genero', pd.Series.mode),
            bairro_mv = ('bairro', pd.Series.mode),
            idade_mv = ('idade', 'mean'),
            raca_mv = ('raca',  pd.Series.mode),
            escolaridade_mv = ('escolaridade',  pd.Series.mode)
            ).reset_index()
    
    nome = area_a
    inscritos = gb_cads['inscritos'].sum()
    genero_mv =  gb_cads['genero_mv'].iat[0]
    idade_mv = gb_cads['idade_mv'].iat[0].round(2)
    raca_mv =  gb_cads['raca_mv'].iat[0]
    escolaridade_mv =  gb_cads['escolaridade_mv'].iat[0]
    bairro_mv = gb_cads['bairro_mv'].iat[0]
    
    dicionario = {
        "NOME":nome,
        "INSCRITOS": inscritos,
        "BAIRRO MAIS PRESENTE":bairro_mv,
        "IDADE":idade_mv,
        "GÊNERO":genero_mv,
        "RAÇA":raca_mv,
        "ESCOLARIDADE":escolaridade_mv
    }

    return dicionario

dicionario = dict_area(df_area)

####################----------------------------###########################
#%% Parte inferior ao mapa
# # Dados por bairro - Usar a DF direta por bairro aqui
# def display_big_numbers_cand(df):
#     #Organizando planilha de dados
#     df = df.groupby(['NM_LOCAL_VOTACAO','BAIRRO'],as_index=False)['QT_VOTOS'].sum()
    
#     #Separando dados
#     total_votos = df["QT_VOTOS"].sum()
#     mediana_votos = df["QT_VOTOS"].median()
#     locais_votacao = len((df["NM_LOCAL_VOTACAO"].unique()).tolist())

#     dicionario2 = {
#         "Total de votos":total_votos,
#         "Mediana": mediana_votos,
#         "N Locais de votação":locais_votacao
#     }

#     return dicionario2

# #Retornando o dicionário dados candidato - Ele faz o recorte para pegar apenas
# #                                          os dados escolhidos pela sidebar. Não sei se quero isso
# #Recorte de dados de bairro se for escolhido um bairro específico, ou geral
# dicionario2 = display_big_numbers_cand(df_pb)

# # Vou apagar isso aqui, já que vou usar apenas dados de bairro. Aqui ele integra dados gerais que batem com a opção de escolha do cadidato, posso fazer o mesmo,
# # mas por enquanto, não. Vou deixar aberto, e se eu voltar, saiba:
# #
# # DADOS DE COMPARATIVO ENTRE O GERAL E A AREA DE ATUAÇÃO ESCOLHIDA
# def display_dados_eleitorais(df):
#     # Minerando dados
#     sigla_partido = df_area["SG_PARTIDO"].values[0]
#     df_partido = df[df["SG_PARTIDO"] == sigla_partido]
#     df_partido = df_partido.groupby(['NM_URNA_CANDIDATO','NR_CANDIDATO','DS_SIT_TOT_TURNO'
#     ],as_index=False)['QT_VOTOS'].sum()

#     # Separando dados
#     perct_votos = f"{(dicionario2["Total de votos"]/df_partido["QT_VOTOS"].sum())*100 :.1f} %"
#     numero_cadeiras = df_partido["DS_SIT_TOT_TURNO"].isin(["ELEITO POR QP",
#     "ELEITO POR MÉDIA"]).sum()
#     votos_totais_chapa = df_partido["QT_VOTOS"].sum()

#     dicionario3 = {
#         "Percentual votos":perct_votos,
#         "Quantidade de cadeiras": numero_cadeiras,
#         "Votos totais da chapa": votos_totais_chapa
#     }

#     return dicionario3

# dicionario3 = display_dados_eleitorais(df)

# # Definindo funções
# def graph_candidatos(df):
#     # Organizando dados
#     df = df.groupby(["NM_URNA_CANDIDATO","SG_PARTIDO"],as_index=False)['QT_VOTOS'].sum()
#     df = df.sort_values(by='QT_VOTOS', ascending=False)
#     df = df.head(10)
    
#     #Definindo cores - posso fazer isso com area de atuação
#     cores_partidos = {
#     "MDB": "blue",
#     "NOVO": "orange",
#     "PSD": "cyan",
#     "PDT": "pink",
#     "PODE": "coral",
#     "REPUBLICANOS": "gold",
#     "CIDADANIA": "brown",
#     "PL": "goldenrod",
#     "PV": "lime",
#     "PP": "teal",
#     "PRD": "green",
#     "DC": "olive",
#     "PRTB": "navy",
#     "UP": "maroon",
#     "PT": "red",
#     "REDE": "indigo",
#     "PSOL": "purple",
#     "AGIR": "skyblue",
#     "PSDB": "darkgreen",
#     "PSB": "salmon",
#     "UNIÃO": "darkblue",
#     "AVANTE": "darkred",
#     "PSTU": "darkorange",
#     "PC do B": "darkviolet"
#     }
    
#     # Organizando o Plot
#     fig = px.bar(df, x='QT_VOTOS', y='NM_URNA_CANDIDATO', orientation = 'h',
#     hover_data="SG_PARTIDO",title=f"Top 10 mais votados", labels ={"NM_URNA_CANDIDATO":"",
#     "QT_VOTOS":"Quantidade de votos"})

#     fig.update_traces(marker_color=[cores_partidos[p] for p in df['SG_PARTIDO']])

#     return fig


# def graph_candidatos_chapa(df):
#     # Organizando dados
#     sigla_partido = df_area["SG_PARTIDO"].values[0]
#     df = df[df["SG_PARTIDO"] == sigla_partido]
#     df = df.groupby(["NM_URNA_CANDIDATO","DS_GENERO"],as_index=False)['QT_VOTOS'].sum()
#     df = df.sort_values(by='QT_VOTOS', ascending=False)
#     df = df.head(10)

#     # Definindo as cores
#     cores_genero = {"MASCULINO":"blue","FEMININO":"pink"}

#     # Organizando plot
#     fig = px.bar(df, x='QT_VOTOS', y='NM_URNA_CANDIDATO', orientation = 'h',
#     hover_data="DS_GENERO",title=f"Top 10 mais votados do {sigla_partido}",
#      labels ={"NM_URNA_CANDIDATO":"", "QT_VOTOS":"Quantidade de votos"})

#     fig.update_traces(marker_color=[cores_genero[p] for p in df['DS_GENERO']])

#     return fig

# def graph_bairros(df):
#     # Organizando dados
#     df = df.groupby(["DISTRITO_ADM","BAIRRO"],as_index=False)['QT_VOTOS'].sum()
#     df = df.sort_values(by='QT_VOTOS', ascending=False)
#     df = df.head(10)

#     # Posso fazer isso aqui com as informações de genero - raça - escolaridade - idosos/crianças
#     cores_itens = {
#     "DABEL": "#1f77b4",  # Azul
#     "DABEN": "#ff7f0e",  # Laranja
#     "DAENT": "#2ca02c",  # Verde
#     "DAGUA": "#d62728",  # Vermelho
#     "DAICO": "#9467bd",  # Roxo
#     "DAMOS": "#8c564b",  # Marrom
#     "DAOUT": "#e377c2",  # Rosa
#     "DASAC": "#7f7f7f"   # Cinza
#     }
    
#     # Organizando plot
#     fig = px.bar(df, x='QT_VOTOS', y='BAIRRO', orientation = 'h',
#     hover_data="DISTRITO_ADM",title=f"Top 10 bairros {area_a}",
#      labels ={"BAIRRO":"", "QT_VOTOS":"Quantidade de votos"})

#     fig.update_traces(marker_color=[cores_itens[p] for p in df['DISTRITO_ADM']])

#     return fig

# def graph_locais(df):
#     # Organizando dados
#     df = df.groupby(["NM_LOCAL_VOTACAO","BAIRRO","DISTRITO_ADM"],as_index=False)['QT_VOTOS'].sum()
#     df = df.sort_values(by='QT_VOTOS', ascending=False)
#     df = df.head(10)

#     # Definindo as cores
#     cores_itens = {
#     "DABEL": "#1f77b4",  # Azul
#     "DABEN": "#ff7f0e",  # Laranja
#     "DAENT": "#2ca02c",  # Verde
#     "DAGUA": "#d62728",  # Vermelho
#     "DAICO": "#9467bd",  # Roxo
#     "DAMOS": "#8c564b",  # Marrom
#     "DAOUT": "#e377c2",  # Rosa
#     "DASAC": "#7f7f7f"   # Cinza
#     }

#     # Organizando plots
#     fig = px.bar(df, x='QT_VOTOS', y='NM_LOCAL_VOTACAO', orientation = 'h',
#     hover_data=["BAIRRO","DISTRITO_ADM"],title=f"Top 10 locais de votação {area_a}",
#      labels ={"NM_LOCAL_VOTACAO":"", "QT_VOTOS":"Votos"})

#     fig.update_traces(marker_color=[cores_itens[p] for p in df['DISTRITO_ADM']])

#     return fig


#%% Criando a cara da app
## Escrevendo a ficha
st.markdown(f"""<style>
.table-full {{
    width: 100%;
    border-collapse: collapse;
}}
.table-full th, .table-full td {{
    border: 0.5px solid #ddd;
    padding: 8px;

}}
.table-full th {{
    font-weight: bold;
    text-align: center;
}}

.table-full td:nth-child(2) {{
    text-align: center;
}}
</style>

<table class="table-full">
    <tr><th>Métrica</th><th>Valor</th></tr>
    <tr><td>Número de inscritos</td><td>{dicionario["INSCRITOS"]}</td></tr>
    <tr><td>Bairro mais presente</td><td>{dicionario["BAIRRO MAIS PRESENTE"]}</td></tr>
    <tr><td>Escolaridade média</td><td>{dicionario["ESCOLARIDADE"]}</td></tr>
    <tr><td>Idade média</td><td>{dicionario["IDADE"]} anos</td></tr>
    <tr><td>Gênero</td><td>{dicionario["GÊNERO"]}</td></tr>
    <tr><td>Raça</td><td>{dicionario["RAÇA"]}</td></tr>
</table>
""", unsafe_allow_html=True)

# Fim do header
############### Mapa

st.markdown(f"### :round_pushpin: **Mapa de Fazedores de cultura {area_a}**")
m = display_mapa(df_area, dfb_map)
st_data = st_folium(m, width="100%", height=700)

############### Abaixo do mapa, com os blocos de informação ##############
st.markdown("### :ballot_box_with_ballot: **Dados eleitorais & Partidários**")
# #Definindo estrutura de exposição
# col1, col2, col3 = st.columns(3)

# with col1:
#     st.metric(
#         label = "Total de votos",
#         value = dicionario2["Total de votos"],
#         border = True
#     )
#     st.metric(
#         label = "% votos em relação à chapa",
#         value = dicionario3["Percentual votos"],
#         border = True
#     )

# with col2:
#     st.metric(
#         label = "Mediana dos votos",
#         value = dicionario2["Mediana"],
#         border = True
#     )
#     st.metric(
#         label = "Quantidade de cadeiras",
#         value = dicionario3["Quantidade de cadeiras"],
#         border = True
#     )

# with col3:
#     st.metric(
#         label = "Locais de votação atendidos",
#         value = dicionario2["N Locais de votação"],
#         border = True
#     )
#     st.metric(
#         label = "Total votos da chapa",
#         value = dicionario3["Votos totais da chapa"],
#         border = True
#     )

# st.markdown(":keycap_star: Nesta análise foram considerados apenas os votos nominais para vereador.")

# ############## GRÁFICOS

# st.markdown("""\n""")
# st.markdown("### :bar_chart: **Gráficos**")

# col1, col2 = st.columns(2)

# plot_votos_candidatos = graph_candidatos(df)
# plot_bairros = graph_bairros(df_area)
# with col1:
#     st.plotly_chart(plot_votos_candidatos)

#     st.plotly_chart(plot_bairros)


# plot_votos_chapa = graph_candidatos_chapa(df)
# plot_locais = graph_locais(df_area)
# with col2:
#     st.plotly_chart(plot_votos_chapa)

#     st.plotly_chart(plot_locais)