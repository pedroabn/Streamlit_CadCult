# core/metrics.py
from typing import Dict, Union
import pandas as pd
import streamlit as st

def _mode_safe(s: pd.Series, default: str = "Não informado") -> Union[str, int, float]:
    s = s.dropna()
    if s.empty:
        return default
    moda = s.mode()
    if moda.empty:
        return default
    return moda.iloc[0]

def dict_area(df: pd.DataFrame, area_a: str) -> Dict[str, Union[str, int, float]]:
    df = df.copy()

    if df.empty:
        return {
            "NOME": area_a,
            "INSCRITOS": 0,
            "BAIRRO MAIS PRESENTE": "Não informado",
            "IDADE": 0,
            "GÊNERO": "Não informado",
            "RAÇA": "Não informado",
            "ESCOLARIDADE": "Não informado",
        }

    # Categóricas
    for col in ["genero", "bairro", "raca", "escolaridade"]:
        if col in df.columns:
            df[col] = df[col].fillna("Não informado")

    # Numérica
    df["idade"] = pd.to_numeric(df["idade"], errors="coerce")

    gb_cads = (
        df.groupby(["area_atuacao"])
        .agg(
            inscritos=("nome", "size"),
            genero_mv=("genero", pd.Series.mode),
            bairro_mv=("bairro", pd.Series.mode),
            idade_mv=("idade", "mean"),
            raca_mv=("raca", pd.Series.mode),
            escolaridade_mv=("escolaridade", pd.Series.mode),
        )
        .reset_index()
    )

    if area_a != "TODOS":
        filtro = gb_cads[gb_cads["area_atuacao"] == area_a]
        if filtro.empty:
            return {
                "NOME": area_a,
                "INSCRITOS": 0,
                "BAIRRO MAIS PRESENTE": "Não informado",
                "IDADE": 0,
                "GÊNERO": "Não informado",
                "RAÇA": "Não informado",
                "ESCOLARIDADE": "Não informado",
            }
        linha = filtro.iloc[0]

        return {
            "NOME": area_a,
            "INSCRITOS": int(linha["inscritos"]),
            "BAIRRO MAIS PRESENTE": _mode_safe(pd.Series(linha["bairro_mv"])),
            "IDADE": round(linha["idade_mv"], 1) if pd.notnull(linha["idade_mv"]) else 0,
            "GÊNERO": _mode_safe(pd.Series(linha["genero_mv"])),
            "RAÇA": _mode_safe(pd.Series(linha["raca_mv"])),
            "ESCOLARIDADE": _mode_safe(pd.Series(linha["escolaridade_mv"])),
        }

    # Caso area_a == "TODOS"
    idade_media = df["idade"].mean()
    return {
        "NOME": "TODOS",
        "INSCRITOS": int(gb_cads["inscritos"].sum()),
        "BAIRRO MAIS PRESENTE": _mode_safe(df["bairro"]),
        "IDADE": round(idade_media, 1) if pd.notnull(idade_media) else 0,
        "GÊNERO": _mode_safe(df["genero"]),
        "RAÇA": _mode_safe(df["raca"]),
        "ESCOLARIDADE": _mode_safe(df["escolaridade"]),
    }


def dados_Area_bairro(
    _df_filtrado: pd.DataFrame, _dfb_filtrado: pd.DataFrame
) -> Dict[str, Union[str, int, float]]:

    try:
        total_no_bairro = _dfb_filtrado["inscritos"].sum()
        na_area = len(_df_filtrado)

        pct = (na_area / total_no_bairro * 100) if total_no_bairro > 0 else 0

        # População vulnerável
        cols_vuln = ["Idosos", "Infancia"]
        n_idosos_inf = _dfb_filtrado[cols_vuln].fillna(0).sum().sum()

        # Espaços sociais
        cols_sociais = ["n_escolas", "qtd_Pracas", "Qtd_equipamentos", "compaz"]
        n_espacos_social = _dfb_filtrado[cols_sociais].fillna(0).sum().sum()

        # Pct de negros
        _dfb_filtrado = _dfb_filtrado.copy()
        _dfb_filtrado["pct_pretos"] = pd.to_numeric(
            _dfb_filtrado["pct_pretos"], errors="coerce"
        )
        pct_negros_val = (_dfb_filtrado["pct_pretos"] * 100).mean()
        pct_negros_str = f"{pct_negros_val:.1f}%" if pd.notnull(pct_negros_val) else "0.0%"

        return {
            "PCT_inscritos_bairro": f"{pct:.1f}%",
            "N_idosos_inf": int(n_idosos_inf),
            "N_espacos_social": int(n_espacos_social),
            "pct_negros": pct_negros_str,
        }
    except Exception as e:
        st.error(f"❌ Erro ao calcular métricas: {str(e)}")
        return {
            "PCT_inscritos_bairro": "0%",
            "N_idosos_inf": 0,
            "N_espacos_social": 0,
            "pct_negros": "0.0%",
        }
