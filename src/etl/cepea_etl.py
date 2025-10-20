# -*- coding: utf-8 -*-
"""
ETL CEPEA — versão final

Responsabilidades:
- Ler arquivos .xlsx do scraper
- Padronizar colunas
- Converter valores numéricos
- Cortar histórico anterior a 13/03/2006
- Exportar cepea_processed.csv e cepea_curated.csv
  com ponto decimal e 2 casas decimais
- Manter compatibilidade total com o Streamlit
"""

import argparse
import os
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv

# ===================== Config =====================
ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw" / "cepea"
PROC_DIR = ROOT / "data" / "processed" / "cepea"
CURATED_DIR = ROOT / "data" / "curated" / "cepea"

PROC_DIR.mkdir(parents=True, exist_ok=True)
CURATED_DIR.mkdir(parents=True, exist_ok=True)

MILHO_DIR = RAW_DIR / "milho"
SOJA_PARANA_DIR = RAW_DIR / "soja" / "parana"
SOJA_PARANAGUA_DIR = RAW_DIR / "soja" / "paranagua"

MIN_DATE = pd.to_datetime("2006-03-13")  # corte padronizado

# ===================== Helpers =====================
def _read_folder(folder: Path, commodity: str, regiao: str) -> pd.DataFrame:
    dfs = []
    for xlsx in sorted(folder.glob("*.xlsx")):
        df = pd.read_excel(
            xlsx,
            skiprows=3,
            header=0,
            sheet_name=0,
            engine="openpyxl",
            dtype={"Data": "string"}
        )
        df.columns = [c.strip() for c in df.columns]
        df = df.rename(columns={
            "Data": "data",
            "À vista R$": "valor_brl",
            "À vista US$": "valor_usd"
        })
        df["data"] = pd.to_datetime(df["data"], errors="coerce", dayfirst=True)
        
        # Conversão melhorada para preservar decimais
        # Se já vier como número do Excel, mantém; se vier como string, converte
        if df["valor_brl"].dtype == 'object':
            df["valor_brl"] = (
                df["valor_brl"].astype(str)
                .str.replace(".", "", regex=False)
                .str.replace(",", ".", regex=False)
            )
        df["valor_brl"] = pd.to_numeric(df["valor_brl"], errors="coerce")
        
        if df["valor_usd"].dtype == 'object':
            df["valor_usd"] = (
                df["valor_usd"].astype(str)
                .str.replace(".", "", regex=False)
                .str.replace(",", ".", regex=False)
            )
        df["valor_usd"] = pd.to_numeric(df["valor_usd"], errors="coerce")
        
        # Arredonda explicitamente para 2 casas decimais mantendo precisão
        df["valor_brl"] = df["valor_brl"].round(2)
        df["valor_usd"] = df["valor_usd"].round(2)

        df = df.dropna(subset=["data"]).copy()
        df["commodity"] = commodity
        df["regiao"] = regiao
        df["__fonte__"] = "CEPEA"
        dfs.append(df)

    if not dfs:
        return pd.DataFrame(columns=["data","commodity","regiao","valor_brl","valor_usd","__fonte__"])
    return pd.concat(dfs, ignore_index=True)

def _clean_csvs(dirpath: Path):
    """Remove arquivos CSV antigos, ignorando se estiverem abertos"""
    for f in dirpath.glob("*.csv"):
        try:
            f.unlink(missing_ok=True)
        except PermissionError:
            print(f"[AVISO] Arquivo {f.name} está em uso, será sobrescrito")

# ===================== Pipeline =====================
def main(to_postgres: bool):
    df_milho = _read_folder(MILHO_DIR, "MILHO", "BRASIL")
    df_soja_pr = _read_folder(SOJA_PARANA_DIR, "SOJA", "PR")
    df_soja_prg = _read_folder(SOJA_PARANAGUA_DIR, "SOJA", "PRG")

    df_all = pd.concat([df_milho, df_soja_pr, df_soja_prg], ignore_index=True)
    df_all = df_all.dropna(subset=["data"]).sort_values(["data","commodity","regiao"])

    # CORTE
    df_all = df_all[df_all["data"] >= MIN_DATE].reset_index(drop=True)

    _clean_csvs(PROC_DIR)
    _clean_csvs(CURATED_DIR)

    processed_path = PROC_DIR / "cepea_processed.csv"
    curated_path = CURATED_DIR / "cepea_curated.csv"

    # Garante arredondamento final antes de salvar
    df_all["valor_brl"] = df_all["valor_brl"].round(2)
    df_all["valor_usd"] = df_all["valor_usd"].round(2)
    
    # Salva com formato decimal correto (ponto como separador, 2 casas)
    try:
        df_all.to_csv(
            processed_path, 
            index=False, 
            encoding="utf-8", 
            float_format="%.2f",
            decimal='.'  # Garante ponto como separador decimal
        )
        print(f"[OK] processed → {processed_path}")
    except PermissionError:
        # Se o arquivo estiver aberto, tenta salvar com novo nome
        processed_path_temp = PROC_DIR / f"cepea_processed_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv"
        df_all.to_csv(
            processed_path_temp, 
            index=False, 
            encoding="utf-8", 
            float_format="%.2f",
            decimal='.'
        )
        print(f"[AVISO] Arquivo original em uso, salvo como: {processed_path_temp}")
    
    try:
        df_all.to_csv(
            curated_path, 
            index=False, 
            encoding="utf-8", 
            float_format="%.2f",
            decimal='.'  # Garante ponto como separador decimal
        )
        print(f"[OK] curated → {curated_path}")
    except PermissionError:
        # Se o arquivo estiver aberto, tenta salvar com novo nome
        curated_path_temp = CURATED_DIR / f"cepea_curated_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv"
        df_all.to_csv(
            curated_path_temp, 
            index=False, 
            encoding="utf-8", 
            float_format="%.2f",
            decimal='.'
        )
        print(f"[AVISO] Arquivo original em uso, salvo como: {curated_path_temp}")

    print(f"[INFO] Total de registros: {len(df_all)}")
    print(f"[INFO] Período: {df_all['data'].min()} a {df_all['data'].max()}")
    print("🚀 ETL concluído com sucesso (com decimal correto).")

# =====================
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--to-postgres", type=str, default="false")
    args = parser.parse_args()
    main(to_postgres=str(args.to_postgres).lower() == "true")