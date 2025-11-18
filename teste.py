#%%
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
#%%
sic = pd.read_excel(r'C:\Users\pedro.bastos\Documents\vscode\streamlit\dados\SIC.xlsx')
df = sic.copy()  # segurança nível 1 
# Mapeia estilos
df['Estilo'] = df['Estilo'].map(dic_sic_cad)
# Converte número de série do Excel -> datetime -> ano
df['ano'] = (
    pd.to_datetime(df['ano'], unit='D', origin='1899-12-30').dt.year
)
df = (df
        .groupby(["Estilo", "ano"], as_index=False)
        .agg(
            inv = ('valor', sum),
            projetos = ('projeto','size')
        ).sort_values(by='ano', ascending=False))

# %%
cad = r'C:\Users\pedro.bastos\Documents\vscode\streamlit\dados\Cadastrados.xlsx'
pb_demo = r'C:\Users\pedro.bastos\Documents\vscode\streamlit\dados\Infopbruto.geojson'

def load_sic_data(path_cad, recife):
    df = pd.read_excel(path_cad)
    df['bairro'] = df['bairro'].apply(limpar_acento).str.upper()
    return df.query('bairro in @recife')

@st.cache_data
def load_pb_demo(path_demo):
    return gpd.read_file(path_demo,engine="pyogrio")

df = load_sic_data(cad, recife)
dfb = load_pb_demo(pb_demo)

df = df[df['area_atuacao']=='Cultura Popular']  # segurança nível 1
dfb = dfb[dfb['EBAIRRNOMEOF'] == 'AFLITOS']

def dados_Area_bairro(_df_filtrado: pd.DataFrame, _dfb_filtrado: pd.DataFrame) -> Dict[str, Union[str, int]]:
    if _df_filtrado.empty:
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
        
dicionario2 = dados_Area_bairro(df, dfb)
# %%
cad_f = pd.read_excel(cad)
area_a ="Cultura Popular"
def graph_candidatos(base):
    df = base.copy()
    # Organizando dados  
    if area_a != 'TODOS':
        df = df[df['area_atuacao'] == area_a]
    else: 
        df = df.copy()
        
    dff = df.groupby(["bairros_cep","area_atuacao"]).agg(
        cadastro = ('nome', "size")).reset_index()
    dff = dff.sort_values(by='cadastro', ascending=False)
    dff = dff.head(5)
    return dff
teste1 = graph_candidatos(cad_f)
    
# %%
df = cad_f.groupby(["bairros_cep","area_atuacao"]).agg(
    cadastro = ('nome', "size")
).reset_index()
df = df.sort_values(by='cadastro', ascending=False)
df = df[df['area_atuacao'] == 'Cultura Popular']
df = df.head(10)
# %%
