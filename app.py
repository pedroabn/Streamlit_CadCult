# app.py
import streamlit as st
import locale
from streamlit_folium import st_folium
from core.carregar import load_cad_data, load_geo, load_teatros, load_sic
from core.metricas import dict_area, dados_Area_bairro
from visuals.mapa import display_mapa
from visuals.graficos import graph_locais,graph_cad,graph_cad_por_bairro, graf_scatter

st.set_page_config(layout="wide", page_title="Cadastros Culturais - Recife")

# --- Carregamento de dados (tudo cacheado) ---
df = load_cad_data()
dfb = load_geo()
teatro = load_teatros()
sic = load_sic()

# --- Sidebar ---
with st.sidebar:
    st.title("Filtros de pesquisa")

    lista_areas = ["TODOS"] + sorted(df["area_atuacao"].dropna().unique().tolist())
    area_a = st.selectbox("Área de atuação", lista_areas)

    lista_bairros = ["TODOS"] + sorted(dfb["EBAIRRNOMEOF"].dropna().unique().tolist())
    bairro_select = st.selectbox("Bairro", lista_bairros)

# --- DataFrames filtrados ---
df_area = df.copy()
dfb_map = dfb.copy()
df_pb = df.copy()       # usado no gráfico que não altera baseado em área
df_soloa = df.copy()    # usado no gráfico que não altera baseado em bairro

# Filtro por bairro
if bairro_select != "TODOS":
    df_area = df_area[df_area["bairro"] == bairro_select]
    dfb_map = dfb_map[dfb_map["EBAIRRNOMEOF"] == bairro_select]
    df_pb = df_pb[df_pb["bairro"] == bairro_select]

# Filtro por área
if area_a != "TODOS":
    df_area = df_area[df_area["area_atuacao"] == area_a]
    df_soloa = df_soloa[df_soloa["area_atuacao"] == area_a]

# --- Métricas principais ---
dicionario = dict_area(df_area, area_a)
dicionario2 = dados_Area_bairro(df_area, dfb_map)

# --- Header ---
st.markdown("# **CADASTRADOS NA SECULT:**")
st.markdown(f"###  Dados das(os) {area_a} e no bairro {bairro_select}")

st.markdown(
    f"""
<style>
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
""",
    unsafe_allow_html=True,
)

# --- Mapa ---
st.markdown(f"### :round_pushpin: **Mapa de Fazedores de cultura {area_a}**")
m = display_mapa(df_area, dfb_map, teatro)
st_folium(m, width="100%", height=700)

# --- Métricas abaixo do mapa ---
st.markdown("### **Dados importantes sobre a Linguagem e Bairro**")
col1, col2 = st.columns(2)

with col1:
    with st.container(border=True):
        st.metric(
            label="% de inscritos no bairro",
            value=dicionario2["PCT_inscritos_bairro"]
        )
        st.metric(
            label="Nº de Idosos e Crianças no bairro",
            value=dicionario2["N_idosos_inf"],
        )

with col2:
    with st.container(border=True):
        st.metric(
            label="Nº de espaços de convivência social",
            value=dicionario2["N_espacos_social"]
        )
        st.metric(
            label="% de pessoas negras",
            value=dicionario2["pct_negros"]
        )

# --- Gráficos ---
st.markdown("### :bar_chart: **Gráficos**")

plot_locais = graph_locais(sic, area_a)
st.plotly_chart(plot_locais, use_container_width=True)

plot_area_a = graph_cad(df_soloa, area_a, bairro_select)
st.plotly_chart(plot_area_a, use_container_width=True)

plot_area_b = graph_cad_por_bairro(df_pb, area_a, bairro_select)
st.plotly_chart(plot_area_b, use_container_width=True)

scatter_plot = graf_scatter(dfb, bairro_select)
st.plotly_chart(scatter_plot, use_container_width=True)
