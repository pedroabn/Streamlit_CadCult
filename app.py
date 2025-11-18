#%% Importando bibliotecas
import streamlit as st
import pandas as pd
from typing import Dict, Union
import geopandas as gpd
import plotly.express as px
from utils import recife, dic_sic_cad, colgate, limpar_acento
from streamlit_folium import st_folium
import folium
from folium.plugins import MarkerCluster, MiniMap, GroupedLayerControl
import branca.colormap as cm
import locale
locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
#%% Base de dados

pb_demo = r'C:\Users\pedro.bastos\Documents\vscode\streamlit\dados\Infopbruto.geojson'

sic = pd.read_excel(r'C:\Users\pedro.bastos\Documents\vscode\streamlit\dados\SIC.xlsx')
teatro = pd.read_excel(r'C:\Users\pedro.bastos\Documents\vscode\streamlit\dados\teatros.xlsx')
cad_f = (r'C:\Users\pedro.bastos\Documents\vscode\streamlit\dados\Cadastrados.xlsx')


@st.cache_data
def load_cad_data(path_cad, recife):
    df = pd.read_excel(path_cad)
    df['bairro'] = df['bairro'].apply(limpar_acento).str.upper()
    return df.query('bairro in @recife')

@st.cache_data
def load_pb_demo(path_demo):
    return gpd.read_file(path_demo,engine="pyogrio")

df = load_cad_data(cad_f, recife)
dfb = load_pb_demo(pb_demo)

#%% Construção da parte lateral do streamlit
with st.sidebar:
    st.title("Filtros de pesquisa")

    # opções
    lista_areas = sorted(df["area_atuacao"].dropna().unique().tolist()) + ["TODOS"]
    area_a = st.selectbox("Área de atuação", lista_areas)
    
    lista_bairros = sorted(dfb["EBAIRRNOMEOF"].dropna().unique().tolist()) + ["TODOS"]
    bairro_select = st.selectbox("Bairro", lista_bairros)

df_area = df.copy()
dfb_map = dfb.copy()
# Usado para o gráfico que não altera baseado em area_atuacao 
df_pb  = df.copy()  
# Usado para o gráfico que não altera baseado em bairro 
df_soloa = df.copy()

# FILTRO POR BAIRRO
if bairro_select != "TODOS":
    df_area = df_area[df_area["bairro"] == bairro_select]
    dfb_map = dfb_map[dfb_map["EBAIRRNOMEOF"] == bairro_select]
    df_pb  = df_pb[df_pb["bairro"] == bairro_select]

# FILTRO POR ÁREA
if area_a != "TODOS":
    df_area = df_area[df_area["area_atuacao"] == area_a]
    df_soloa = df_soloa[df_soloa["area_atuacao"] == area_a]
#%% Construção do mapa
def display_mapa(df_area, dfb, df_t):
    
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
    for row in df_t.itertuples():
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

#%%Dicionário 1:  Header
# FICHA DA AREA DE ATUAÇÃ0
## Criando a função para obtenção dos dados SOBRE A AREA DE ATUAÇÃO (HEADER)
def dict_area(df):
    df = df.copy()
    #Categorica
    for col in ['genero', 'bairro', 'raca', 'escolaridade']:
        if col in df.columns:
            df[col] = df[col].fillna("Não informado")
    
    #Numérica
    df['idade'] = pd.to_numeric(df['idade'], errors='coerce')
                
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
#%% Dicionário 2: Abaixo do mapa
# Dados por bairro - Usar a DF direta por bairro aqui
def dados_Area_bairro(_df_filtrado: pd.DataFrame, _dfb_filtrado: pd.DataFrame) -> Dict[str, Union[str, int]]:

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
#%% Gráficos da área x bairro
# DADOS DE COMPARATIVO ENTRE O GERAL E A AREA DE ATUAÇÃO ESCOLHIDA 
def graph_cad(base):
    df = base.copy()
    df['bairros_cep'] = df['bairros_cep'].apply(limpar_acento).str.upper().replace({'COHAB':'COHAB - IBURA DE CIMA',
                                                                'SÍTIO DOS PINTOS':'SÍTIO DOS PINTOS - SÃO BRÁS'})
    # Organizando dados          
    dff = df.groupby(["bairros_cep","area_atuacao"]).agg(
        cadastros = ('nome', "size")).reset_index()
    dff = dff.sort_values(by='cadastros', ascending=False)
    dff = dff.head(5)
    
    # Organizando o Plot
    fig = px.bar(dff, x='bairros_cep', y='cadastros', text_auto='cadastros',
                 title=f"Top 5 bairros com mais cadastrados em {area_a}",
                 labels ={"bairros_cep":"Bairros", "cadastros":"Quantidade de cadastrados"})
    cores = ['#ffffff' if b != bairro_select else "#27b3d6" for b in dff['bairros_cep']]
    fig.update_traces(marker_color=cores)

    return fig
#%% Gráfico de maiores cadastrados no bairro
def graph_cad_por_bairro(base):
    df = base.copy()
    df['bairros_cep'] = df['bairros_cep'].apply(limpar_acento).str.upper().replace({'COHAB':'COHAB - IBURA DE CIMA',
                                                                'SÍTIO DOS PINTOS':'SÍTIO DOS PINTOS - SÃO BRÁS'})
    # Organizando dados          
    dff = df.groupby(["bairros_cep","area_atuacao"]).agg(
        cadastros = ('nome', "size")).reset_index()
    dff = dff.sort_values(by='cadastros', ascending=False)
    dff = dff.head(3)
    
    # Organizando o Plot
    fig = px.bar(dff, y='area_atuacao', x='cadastros', orientation= 'h',
                 title=f"Top 5 áreas de atuação com mais cadastrados em {bairro_select}",text_auto='cadastros',
                 labels ={ "cadastros":"Quantidade de cadastrados", "area_atuacao":"Área de atuação"}
                ).update_yaxes(type="category",         
                categoryorder="category ascending" )
    cores = ['#ffffff' if b != area_a else "#27b3d6" for b in dff['area_atuacao']]
    fig.update_traces(marker_color=cores)

    return fig

#%% Scatter
def graf_scatter(base):
    df = base.copy()
    # Espaços sociais
    cols = ["n_escolas", "qtd_Pracas", "Qtd_equipamentos", "compaz"]
    df['conv_social'] = df[cols].fillna(0).sum(axis=1)
    
    fig = px.scatter(df, x="inscritos", y="total_pessoas",
                     title="Nº de Cadastrados, por Nº de total de pessoas, e Espaços de convivência",
                     size="conv_social", hover_name="EBAIRRNOMEOF", labels=({}))
    cores = ['#ffffff' if b != bairro_select else "#27b3d6" for b in df['EBAIRRNOMEOF']]
    fig.update_traces(marker_color=cores)
    return fig
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
        y='inv',
        text_auto=True,
        labels={"ano":"Ano","inv":"Investimento"},
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

m = display_mapa(df_area, dfb_map, teatro)

st_data = st_folium(m, width="100%", height=700)
#%% Abaixo do mapa, com os blocos de informação
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

#%% GRÁFICOS
st.markdown("### :bar_chart: **Gráficos**")

plot_locais = graph_locais(sic)
st.plotly_chart(plot_locais)
plot_area_a = graph_cad(df_soloa)
st.plotly_chart(plot_area_a)
plot_area_b = graph_cad_por_bairro(df_pb)
st.plotly_chart(plot_area_b)
scatter_plot = graf_scatter(dfb)
st.plotly_chart(scatter_plot)