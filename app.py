#%% Importando bibliotecas
import streamlit as st
import pandas as pd
from typing import Dict, Union
import geopandas as gpd
import plotly.express as px
from utils import recife, dic_sic_cad, colgate, limpar_acento
from streamlit_folium import st_folium
import folium
from folium.plugins import MarkerCluster, HeatMap, MiniMap, GroupedLayerControl
import branca.colormap as cm
import locale
locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
#%% Base de dados

pb_demo = r'C:\Users\pedro.bastos\Documents\vscode\streamlit\dados\Infopbruto.geojson'

sic = pd.read_excel(r'C:\Users\pedro.bastos\Documents\vscode\streamlit\dados\SIC.xlsx')
teatro = pd.read_excel(r'C:\Users\pedro.bastos\Documents\vscode\streamlit\dados\teatros.xlsx')
cad_f = (r'C:\Users\pedro.bastos\Documents\vscode\streamlit\dados\Cadastrados.xlsx')


@st.cache_data
def load_sic_data(path_cad, recife):
    df = pd.read_excel(path_cad)
    df['bairro'] = df['bairro'].apply(limpar_acento).str.upper()
    return df.query('bairro in @recife')

@st.cache_data
def load_pb_demo(path_demo):
    return gpd.read_file(path_demo,engine="pyogrio")

df = load_sic_data(cad_f, recife)
dfb = load_pb_demo(pb_demo)

#%% Construção da parte lateral do streamlit
with st.sidebar:
    st.title("Filtros de pesquisa")

    # --- listas ---
    lista_areas = sorted(df["area_atuacao"].dropna().unique().tolist()) + ["TODOS"]
    area_a = st.selectbox("Área de atuação", lista_areas)
    
    lista_bairros = sorted(dfb["EBAIRRNOMEOF"].dropna().unique().tolist()) + ["TODOS"]
    bairro_select = st.selectbox("Bairro", lista_bairros)

# --- criar dataframes filtráveis ---
df_area = df.copy()
dfb_map = dfb.copy()
df_pb  = df.copy()   

# FILTRO POR BAIRRO
if bairro_select != "TODOS":
    df_area = df_area[df_area["bairro"] == bairro_select]
    dfb_map = dfb_map[dfb_map["EBAIRRNOMEOF"] == bairro_select]
    df_pb  = df_pb[df_pb["bairro"] == bairro_select]

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
    df = df.copy()
    #Categorica
    for col in ['genero', 'bairro', 'raca', 'escolaridade']:
        if col in df.columns:
            df[col] = df[col].fillna("Não informado")
    
    #Numérica
    df['idade'] = pd.to_numeric(df['idade'], errors='coerce').dropna()
                
    gb_cads = df.groupby(['area_atuacao']).agg(
        inscritos=('nome', 'size'),
        genero_mv=('genero', pd.Series.mode),
        bairro_mv=('bairro', pd.Series.mode),
        idade_mv=('idade', 'mean'),
        raca_mv=('raca', pd.Series.mode),
        escolaridade_mv=('escolaridade', pd.Series.mode)
    ).reset_index()
    
    if area_a != "TODOS":
        filtro = gb_cads[gb_cads['area_atuacao'] == area_a]
        if filtro.empty:
            return {
                "NOME": area_a,
                "INSCRITOS": 0,
                "BAIRRO MAIS PRESENTE": 0,
                "IDADE": 0,
                "GÊNERO": 0,
                "RAÇA": 0,
                "ESCOLARIDADE": 0
            }
        else:
            linha = filtro.iloc[0]
    else:
        linha = None
    dicionario = {
        "NOME": area_a,

        "INSCRITOS": (
            gb_cads['inscritos'].sum()
            if area_a == "TODOS"
            else int(linha['inscritos'])
        ),

        "BAIRRO MAIS PRESENTE": (
            df['bairro'].mode().iloc[0]
            if area_a == "TODOS"
            else pd.Series(linha['bairro_mv']).iloc[0]
        ),

        "IDADE": (
            round(df['idade'].mean(), 1)
            if area_a == "TODOS"
            else round(linha['idade_mv'], 1)
        ),

        "GÊNERO": (
            df['genero'].mode().iloc[0]
            if area_a == "TODOS"
            else pd.Series(linha['genero_mv']).iloc[0]
        ),

        "RAÇA": (
            df['raca'].mode().iloc[0]
            if area_a == "TODOS"
            else pd.Series(linha['raca_mv']).iloc[0]
        ),

        "ESCOLARIDADE": (
            df['escolaridade'].mode().iloc[0]
            if area_a == "TODOS"
            else pd.Series(linha['escolaridade_mv']).iloc[0]
        )
    }


    return dicionario

dicionario = dict_area(df_area)

####################----------------------------###########################
#%% Parte inferior ao mapa
# Dados por bairro - Usar a DF direta por bairro aqui
def dados_Area_bairro(_df_filtrado: pd.DataFrame, _dfb_filtrado: pd.DataFrame) -> Dict[str, Union[str, int]]:
    if _df_filtrado.empty or _dfb_filtrado.empty:
        return {
            "PCT_inscritos_bairro": "0%",
            "N_idosos_inf": 0,
            "pct_negros":0,
            "N_espacos_social": 0,
        }
    try:
        # Totais
        total_no_bairro = _dfb_filtrado["inscritos"].sum()
        na_area = len(_df_filtrado)
        
        # Percentual
        pct = (na_area / total_no_bairro * 100) if total_no_bairro > 0 else 0
        
        # População vulnerável
        cols = ["Idosos", "Infancia"]
        n_idosos_inf = _dfb_filtrado[cols].fillna(0).sum().sum()
        # Espaços sociais
        cols = ["n_escolas", "qtd_Pracas", "Qtd_equipamentos", "compaz"]
        n_espacos_social = _dfb_filtrado[cols].fillna(0).sum().sum()
        # Pct de negros
        _dfb_filtrado["pct_pretos"] = pd.to_numeric(_dfb_filtrado["pct_pretos"], errors='coerce')
        pct_negros = (_dfb_filtrado["pct_pretos"] * 100).mean()
        
        return {
            "PCT_inscritos_bairro": f"{pct:.1f}%",
            "N_idosos_inf": f'{int(n_idosos_inf)}',
            "N_espacos_social": int(n_espacos_social),
            "pct_negros":f"{pct_negros:.1f}%",
        }
    except Exception as e:
        st.error(f"❌ Erro ao calcular métricas: {str(e)}")
        return {
            "PCT_inscritos_bairro": "0%",
            "pct_negros":0,
            "N_idosos_inf": 0,
            "N_espacos_social": 0,
        }
        
dicionario2 = dados_Area_bairro(df_area, dfb_map)

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
#%% SIC
def graph_locais(df):
    # Organizando dados
    df = colgate(df)
    if area_a != "TODOS": 
        df = df.query("Estilo == @area_a")
    else: df = df
   
    fig = px.histogram(
        df,
        x='ano',
        y='valor',
        text_auto=True,
        title=f"Investimento da área no SIC ao longo dos anos: {area_a}"
    ).update_xaxes(type="category",        
    title_text="Ano", 
    categoryorder="category ascending" )

    return fig



#%% Criando a cara da app
## Escrevendo a ficha
st.markdown(f""" # **CADASTRADOS NA SECULT:**""")
st.markdown(f""" ###  Dados das(os) {area_a} e no bairro {bairro_select}""")
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
# Mapa

st.markdown(f"### :round_pushpin: **Mapa de Fazedores de cultura {area_a}**")
m = display_mapa(df_area, dfb_map)
st_data = st_folium(m, width="100%", height=700)

# Abaixo do mapa, com os blocos de informação
st.markdown("### **Dados importantes sobre a Linguagem e Bairro**")
# #Definindo estrutura de exposição
col1,col2 = st.columns(2) #Adicionar as colunsa ao lo

with col1:
    st.metric(
        label = "% de inscritos no bairro",
        value = dicionario2["PCT_inscritos_bairro"],
        border = True
    )
    st.metric(
        label = "Nº de Idosos e Crianças no bairro",
        value = dicionario2["N_idosos_inf"],
        border = True
    )
    
with col2:
    st.metric(
        label = "Nº de espaços de convivência social",
        value = dicionario2["N_espacos_social"],
        border = True
    )
    st.metric(
        label = "% de pessoas negras",
        value = dicionario2['pct_negros'],
        border = True
    )


# GRÁFICOS
st.markdown("### :bar_chart: **Gráficos**")
sic
plot_locais = graph_locais(sic)
# with col2:
#     st.plotly_chart(plot_votos_chapa)

st.plotly_chart(plot_locais)