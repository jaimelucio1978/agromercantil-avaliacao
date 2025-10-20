# -*- coding: utf-8 -*-
import os
from pathlib import Path
from datetime import date, timedelta
import base64
import mimetypes
import re
import hashlib

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

# =========================================================
# CONFIGURAÇÃO DO APP
# =========================================================
st.set_page_config(
    page_title="Agromercantil | Indicadores CEPEA",
    page_icon="🌾",
    layout="wide"
)

st.title("🌾 Indicadores CEPEA — Milho & Soja")
st.caption("Inteligência de Mercado para Decisão Estratégica no Agronegócio")

# =========================================================
# LOCALIZAÇÃO DO CSV CURATED
# =========================================================
ROOT = Path(__file__).resolve().parents[2]
CURATED_PATH = ROOT / "data" / "curated" / "cepea" / "cepea_curated.csv"
ATTACHMENTS_DIR = ROOT / "data" / "attachments"
# Limpa anexos em disco para evitar duplicações históricas
try:
    if ATTACHMENTS_DIR.exists():
        for _p in ATTACHMENTS_DIR.glob("*"):
            if _p.is_file():
                _p.unlink(missing_ok=True)
    else:
        ATTACHMENTS_DIR.mkdir(parents=True, exist_ok=True)
except Exception:
    pass

# =============================
# Anexos: utilitários
# =============================
def _safe_filename(name: str) -> str:
    name = name.strip().replace("\\", "/").split("/")[-1]
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", name)
    return safe[:150] if len(safe) > 150 else safe

def _guess_mime(path: Path) -> str:
    mt, _ = mimetypes.guess_type(str(path))
    return mt or "application/octet-stream"

def save_uploaded_files(files) -> list[dict]:
    saved = []
    for f in files:
        fname = _safe_filename(f.name)
        dest = ATTACHMENTS_DIR / fname
        if dest.exists():
            stem, ext = dest.stem, dest.suffix
            i = 1
            while (ATTACHMENTS_DIR / f"{stem}_{i}{ext}").exists():
                i += 1
            dest = ATTACHMENTS_DIR / f"{stem}_{i}{ext}"
        dest.write_bytes(f.getbuffer())
        saved.append({
            "name": dest.name,
            "path": str(dest),
            "mime": _guess_mime(dest),
            "size": dest.stat().st_size,
        })
    return saved

def list_attachments() -> list[dict]:
    items = []
    for p in sorted(ATTACHMENTS_DIR.glob("*")):
        if p.is_file():
            items.append({
                "name": p.name,
                "path": str(p),
                "mime": _guess_mime(p),
                "size": p.stat().st_size,
            })
    return items

def render_attachments(items: list[dict]):
    if not items:
        st.info("Nenhum anexo disponível.")
        return
    st.subheader("📁 Anexos do Projeto")
    for it in items:
        mime = it.get("mime")
        size_mb = it["size"] / (1024 * 1024)
        with st.expander(f"📎 {it['name']} — {mime} — {size_mb:.1f} MB", expanded=False):
            if "bytes" in it:
                data_bytes = it["bytes"]
            else:
                # fallback para compatibilidade antiga
                p = Path(it.get("path", ""))
                data_bytes = p.read_bytes() if p.is_file() else b""
            if mime and mime.startswith("image/"):
                st.image(data_bytes, use_column_width=True)
            elif mime and mime.startswith("audio/"):
                st.audio(data_bytes, format=mime)
            elif mime and mime.startswith("video/"):
                st.video(data_bytes, format=mime)
            elif mime == "application/pdf":
                if it["size"] <= 8 * 1024 * 1024:
                    b64 = base64.b64encode(data_bytes).decode("utf-8")
                    html = f"""
                    <iframe src='data:application/pdf;base64,{b64}' width='100%' height='700' style='border:1px solid #ddd;border-radius:6px;'></iframe>
                    """
                    st.components.v1.html(html, height=720)
                else:
                    st.warning("PDF grande para pré-visualização. Utilize o botão de download.")
            else:
                st.write("Pré-visualização não suportada. Faça o download abaixo.")
            st.download_button(
                label="⬇️ Baixar",
                data=data_bytes,
                file_name=it["name"],
                mime=mime or "application/octet-stream"
            )

# =========================================================
# FUNÇÃO PARA CARREGAR DADOS
# =========================================================
@st.cache_data(show_spinner=True)
def load_data():
    df = pd.read_csv(CURATED_PATH, encoding="utf-8")

    # normalização e ordenação
    df.columns = [c.lower().strip() for c in df.columns]
    df["data"] = pd.to_datetime(df["data"], errors="coerce")
    df = df.dropna(subset=["data"])
    df = df.sort_values("data")

    df["regiao"] = df["regiao"].astype(str)
    df["commodity"] = df["commodity"].astype(str)
    
    # Substitui siglas por nomes completos
    df["regiao"] = df["regiao"].replace({"PR": "PARANÁ", "PRG": "PARANAGUÁ"})

    return df.reset_index(drop=True)

df = load_data()

# =========================================================
# SIDEBAR – FILTROS
# =========================================================
st.sidebar.header("Filtros")

# Upload de anexos (somente sessão; não salva em disco)
uploaded = st.sidebar.file_uploader(
    "Anexar arquivos (PDF, áudio, vídeo, imagens, Office)",
    type=[
        "pdf","doc","docx","xls","xlsx","ppt","pptx",
        "mp3","wav","m4a","ogg",
        "mp4","mov","mkv","webm",
        "png","jpg","jpeg","gif","webp","bmp","tif","tiff",
    ],
    accept_multiple_files=True,
    help="Os arquivos ficam apenas nesta sessão (não são salvos no disco)"
)

# Sessão: mantém anexos em memória e evita duplicatas
ss_key = "attachments_mem"
if ss_key not in st.session_state:
    st.session_state[ss_key] = []

if uploaded:
    current = st.session_state[ss_key]
    existing_hashes = {it.get("hash") for it in current}
    added = 0
    for f in uploaded:
        data_bytes = f.getvalue()
        file_hash = hashlib.sha256(data_bytes).hexdigest()
        if file_hash in existing_hashes:
            continue
        size = len(data_bytes)
        mime, _ = mimetypes.guess_type(f.name)
        current.append({
            "name": f.name,
            "bytes": data_bytes,
            "mime": mime or getattr(f, "type", None) or "application/octet-stream",
            "size": size,
            "hash": file_hash,
        })
        existing_hashes.add(file_hash)
        added += 1
    if added:
        st.sidebar.success(f"{added} arquivo(s) anexado(s) nesta sessão.")

if st.sidebar.button("🧹 Limpar anexos desta sessão", use_container_width=True):
    st.session_state[ss_key] = []
    st.sidebar.info("Anexos da sessão removidos.")

# intervalo real do dataset
min_d, max_d = df["data"].min().date(), df["data"].max().date()
# Define período padrão: início = menor data do dataset (13/03/2006)
default_ini = min_d  # Sempre começa da menor data disponível

periodo = st.sidebar.date_input(
    "Período",
    value=(default_ini, max_d),
    min_value=min_d,
    max_value=max_d,
    format="DD/MM/YYYY"
)

if isinstance(periodo, tuple):
    din, dfi = periodo
else:
    din, dfi = min_d, max_d

# commodities filtráveis
commodities = sorted(df["commodity"].unique().tolist())
sel_commodities = st.sidebar.multiselect("Commodity", commodities, default=commodities)

# regiões filtráveis
regioes = sorted(df["regiao"].unique().tolist())
sel_regioes = st.sidebar.multiselect("Região", regioes, default=regioes)

# seleção da moeda
moeda = st.sidebar.radio("Moeda", ["R$ (BRL)", "US$ (USD)"], index=0, horizontal=True)
col_valor = "valor_brl" if moeda.startswith("R$") else "valor_usd"

# periodicidade (granularidade)
freq = st.sidebar.selectbox("Periodicidade", ["Diária", "Semanal", "Mensal"], index=0)

# aplica filtros
mask = (
    (df["data"].dt.date >= din) &
    (df["data"].dt.date <= dfi) &
    (df["commodity"].isin(sel_commodities)) &
    (df["regiao"].isin(sel_regioes))
)
dff_daily = df.loc[mask].copy()
# =========================================================
# KPI's — sempre com base DIÁRIA real
# =========================================================
def kpi_metrics_daily(_df: pd.DataFrame, col: str):
    if _df.empty:
        return None

    g = _df.sort_values("data")

    last_day = g["data"].max()
    g_last = g[g["data"] == last_day]
    ult = g_last[col].mean()

    prev = g[g["data"] < last_day]
    if not prev.empty:
        prev_day = prev["data"].max()
        d1 = prev[prev["data"] == prev_day][col].mean()
        var_d1 = (ult / d1 - 1.0) * 100 if d1 != 0 else np.nan
    else:
        d1 = np.nan
        var_d1 = np.nan

    media_30 = g.tail(30)[col].mean()
    max_p = g[col].max()
    min_p = g[col].min()

    return {
        "ultimo": ult,
        "var_d1": var_d1,
        "media_30": media_30,
        "max": max_p,
        "min": min_p,
        "data_ult": last_day.date()
    }

col1, col2, col3, col4, col5 = st.columns(5)
kpi = kpi_metrics_daily(dff_daily, col_valor)
if kpi:
    col1.metric("Último Preço", f"{kpi['ultimo']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    col2.metric("Variação D-1 (%)", f"{kpi['var_d1']:,.2f}%".replace(",", "X").replace(".", ",").replace("X", "."))
    col3.metric("Média 30 dias", f"{kpi['media_30']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    col4.metric("Máximo", f"{kpi['max']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    col5.metric("Mínimo", f"{kpi['min']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

st.write(f"**Período exibido:** {din} → {dfi} | **Moeda:** {moeda}")
st.divider()

# =========================================================
# AGREGAÇÃO PARA GRÁFICOS (SEMANAL/MENSAL)
# =========================================================
def resample_mean(_df: pd.DataFrame, rule: str):
    if _df.empty:
        return _df
    out = []
    for (c, r), g in _df.groupby(["commodity", "regiao"]):
        g = g.sort_values("data").set_index("data")
        # Reamostra mantendo todas as colunas necessárias
        agg = g[["valor_brl", "valor_usd"]].resample(rule).mean().dropna()
        agg = agg.reset_index()
        agg["commodity"] = c
        agg["regiao"] = r
        out.append(agg)
    return pd.concat(out, ignore_index=True) if out else _df

if freq == "Semanal":
    dff = resample_mean(dff_daily, "W")
elif freq == "Mensal":
    dff = resample_mean(dff_daily, "M")
else:
    dff = dff_daily.copy()

# =========================================================
# Gráfico 1 — Tendência Histórica
# =========================================================
st.subheader("Tendência Histórica (Linha)")
if dff.empty:
    st.info("Nenhum dado para exibir no gráfico.")
else:
    plot_df = dff.copy().sort_values("data")

    fig = px.line(
        plot_df,
        x="data",
        y=col_valor,
        color="commodity",
        line_dash="regiao",
        labels={"data": "Data", col_valor: f"Preço ({moeda})", "commodity": "Commodity", "regiao": "Região"},
    )

    fig.update_traces(
    hovertemplate="<br>".join([
        "Data: %{x|%d/%m/%Y}",
        "Preço: %{y:.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    ])
)

    fig.update_xaxes(rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# =========================================================
# Gráfico 2 — Comparação entre Commodities
# =========================================================
st.subheader("Comparação entre Commodities (Média por Data)")
if dff.empty:
    st.info("Sem dados para comparação.")
else:
    cmp = dff.groupby(["data", "commodity"], as_index=False)[col_valor].mean()
    fig2 = px.line(
        cmp,
        x="data",
        y=col_valor,
        color="commodity",
        labels={"data": "Data", col_valor: f"Preço Médio ({moeda})", "commodity": "Commodity"},
    )
    fig2.update_traces(
        hovertemplate="<br>".join([
            "Data: %{x|%d/%m/%Y}",
            "Preço: %{y:.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        ])
    )
    fig2.update_xaxes(rangeslider_visible=False)
    st.plotly_chart(fig2, use_container_width=True)

st.divider()

# =========================================================
# Gráfico 3 — BRL x USD
# =========================================================
st.subheader("Preço em R&#36; × US&#36; (Média por Data)")
if dff.empty:
    st.info("Sem dados.")
else:
    c_opts = sorted(dff["commodity"].unique().tolist())
    c_sel = st.selectbox("Escolha a Commodity", c_opts, index=0)

    base = dff[dff["commodity"] == c_sel]
    if not base.empty:
        # Garante que temos as colunas necessárias
        g3 = base.groupby("data", as_index=False).agg({
            "valor_brl": "mean",
            "valor_usd": "mean"
        })
        long = g3.melt(id_vars="data", var_name="moeda", value_name="preco")

        long["moeda"] = long["moeda"].map({"valor_brl": "R$ (BRL)", "valor_usd": "US$ (USD)"})

        fig3 = px.line(
            long,
            x="data",
            y="preco",
            color="moeda",
            labels={"data": "Data", "preco": "Preço", "moeda": "Moeda"},
        )
        fig3.update_traces(
            hovertemplate="<br>".join([
                "Data: %{x|%d/%m/%Y}",
                "Preço: %{y:.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            ])
        )
        fig3.update_xaxes(rangeslider_visible=False)
        st.plotly_chart(fig3, use_container_width=True)

st.divider()
# =========================================================
# TABELA + DOWNLOAD
# =========================================================

# Função para formatar moeda pt-BR
def fmt_brl(x: float):
    if pd.isna(x):
        return ""
    return f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# Mês abreviado (pt-BR)
PT_BR_MONTH_ABBR = ["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"]

def semana_label(dt: pd.Timestamp):
    n_sem = 1 + (dt.day - 1) // 7
    mes_lbl = PT_BR_MONTH_ABBR[dt.month - 1]
    return f"{n_sem}ª semana {mes_lbl}/{dt.year}"

def data_display_column(df_in: pd.DataFrame, freq: str):
    if freq == "Diária":
        return df_in["data"].dt.strftime("%d/%m/%Y")
    elif freq == "Semanal":
        return df_in["data"].apply(lambda d: semana_label(pd.to_datetime(d)))
    else:
        return df_in["data"].apply(lambda d: f"{PT_BR_MONTH_ABBR[pd.to_datetime(d).month-1]}/{pd.to_datetime(d).year}")

# TABELA
st.subheader("Tabela Segmentada por Período e Região")

# Ordena em ordem decrescente (mais recente primeiro)
table_base = dff.sort_values(["data","commodity","regiao"], ascending=[False, True, True]).copy()
table_base["Data Formatada"] = data_display_column(table_base, freq)

table_df = table_base.rename(columns={
    "data": "Data",
    "commodity": "Commodity",
    "regiao": "Região",
}).copy()

table_df["Preço (R$)"] = table_base["valor_brl"].map(fmt_brl)
table_df["Preço (US$)"] = table_base["valor_usd"].map(fmt_brl)

# Seleciona colunas na ordem desejada, usando Data (datetime) e Data Formatada (string)
table_df = table_df[["Data", "Data Formatada", "Commodity", "Região", "Preço (R$)", "Preço (US$)"]]

st.dataframe(
    table_df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Data": st.column_config.DatetimeColumn(
            "Data",
            format="DD/MM/YYYY",
            help="Período - clique para ordenar cronologicamente",
            width="small"
        ),
        "Data Formatada": None,  # Oculta esta coluna
        "Commodity": st.column_config.TextColumn(width="medium"),
        "Região": st.column_config.TextColumn(width="small"),
        "Preço (R$)": st.column_config.TextColumn(width="small"),
        "Preço (US$)": st.column_config.TextColumn(width="small"),
    }
)

# DOWNLOAD CSV
@st.cache_data
def to_csv_bytes(_df: pd.DataFrame) -> bytes:
    export_df = dff.sort_values(["data","commodity","regiao"]).rename(columns={
        "data": "Data",
        "commodity": "Commodity",
        "regiao": "Região",
        "valor_brl": "Preço (R$)",
        "valor_usd": "Preço (US$)"
    })
    return export_df.to_csv(index=False, encoding="utf-8").encode("utf-8")

st.download_button(
    label="⬇️ Baixar CSV filtrado",
    data=to_csv_bytes(dff),
    file_name=f"cepea_filtrado_{date.today().isoformat()}.csv",
    mime="text/csv"
)

# =============================
# Seção de Anexos (somente sessão)
# =============================
st.divider()
render_attachments(st.session_state.get(ss_key, []))

# =========================================================
# Rodapé
# =========================================================
st.caption("© Agromercantil — Avaliação Técnica. Dashboard desenvolvido para análise de indicadores CEPEA.")