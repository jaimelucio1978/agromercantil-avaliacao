# -*- coding: utf-8 -*-
"""
Baixa séries CEPEA via Selenium, converte .xls -> .xlsx com Excel (win32com),
remove .xls e mantém apenas o .xlsx mais recente por commodity.
"""

from pathlib import Path
from datetime import datetime
import time
import shutil
import os
import glob

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import win32com.client as win32  # Excel automation (win32com)

# ----------------------------------------------------------------------
# Pastas
ROOT = Path(__file__).resolve().parents[2]
RAW_ROOT = ROOT / "data" / "raw" / "cepea"

DESTS = {
    "MILHO": RAW_ROOT / "milho",
    "SOJA_PARANA": RAW_ROOT / "soja" / "parana",
    "SOJA_PARANAGUA": RAW_ROOT / "soja" / "paranagua",
}

for p in DESTS.values():
    p.mkdir(parents=True, exist_ok=True)

# Páginas e anchors (href) dos botões "SÉRIE DE PREÇOS"
PAGES = {
    "MILHO": {
        "page": "https://www.cepea.org.br/br/indicador/milho.aspx",
        "href_sub": "/indicador/series/milho.aspx?id=77",
    },
    "SOJA_PARANA": {
        "page": "https://www.cepea.org.br/br/indicador/soja.aspx",
        "href_sub": "/indicador/series/soja.aspx?id=12",
    },
    "SOJA_PARANAGUA": {
        "page": "https://www.cepea.org.br/br/indicador/soja.aspx",
        "href_sub": "/indicador/series/soja.aspx?id=92",
    },
}


# ----------------------------------------------------------------------
def _init_driver(download_dir: Path) -> webdriver.Chrome:
    """Configura Chrome para baixar direto na pasta indicada."""
    opts = Options()
    # Se desejar headless, descomente:
    # opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-gpu")
    opts.add_experimental_option("prefs", {
        "download.default_directory": str(download_dir),
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
    })
    driver = webdriver.Chrome(options=opts)
    driver.set_page_load_timeout(90)
    return driver


def _wait_for_download(dirpath: Path, pattern: str = "CEPEA_*.xls", timeout: int = 120) -> Path:
    """Aguarda um CEPEA_*.xls aparecer e terminar (.crdownload sumir)."""
    t0 = time.time()
    last = None
    while time.time() - t0 < timeout:
        files = sorted(dirpath.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
        # ignora temporários .crdownload
        tmp = list(dirpath.glob("*.crdownload"))
        if files and not tmp:
            last = files[0]
            # pequena margem para flush de disco
            time.sleep(0.8)
            return last
        time.sleep(0.5)
    raise TimeoutError(f"Timeout aguardando download em {dirpath}")


def _convert_xls_to_xlsx_and_cleanup(xls_path: Path) -> Path:
    """
    Abre o .xls no Excel e salva como .xlsx (FileFormat=51).
    Remove o .xls após conversão. Retorna o caminho do .xlsx.
    """
    print(f"[CONVERTER] {xls_path.name} -> .xlsx (Excel)")
    excel = win32.Dispatch("Excel.Application")
    excel.DisplayAlerts = False
    try:
        wb = excel.Workbooks.Open(str(xls_path))
        xlsx_path = xls_path.with_suffix(".xlsx")
        wb.SaveAs(str(xlsx_path), FileFormat=51)  # 51 = xlOpenXMLWorkbook (.xlsx)
        wb.Close(SaveChanges=False)
    finally:
        excel.Quit()

    # Remove o .xls original
    try:
        xls_path.unlink(missing_ok=True)
    except Exception:
        pass

    return xlsx_path


def _keep_only_latest_xlsx(dirpath: Path):
    """Mantém somente o CEPEA_*.xlsx mais recente; remove os demais."""
    files = sorted(dirpath.glob("CEPEA_*.xlsx"), key=lambda p: p.stat().st_mtime, reverse=True)
    if len(files) > 1:
        for f in files[1:]:
            try:
                f.unlink(missing_ok=True)
                print(f"[LIMPEZA] Removido antigo: {f}")
            except Exception:
                pass


def _click_series_and_download(driver: webdriver.Chrome, page_url: str, href_sub: str, download_dir: Path) -> Path:
    """Abre a página, clica no anchor de 'SÉRIE DE PREÇOS' (pelo href) e aguarda o .xls."""
    driver.get(page_url)
    # Aguarda anchor com o href específico
    sel = f"a[href*=\"{href_sub}\"]"
    link = WebDriverWait(driver, 30).until(EC.element_to_be_clickable((By.CSS_SELECTOR, sel)))
    link.click()
    # Aguarda arquivo .xls
    xls_path = _wait_for_download(download_dir)
    return xls_path


def _clean_folder(dirpath: Path):
    """Remove CEPEA_*.xls e CEPEA_*.xlsx da pasta (limpeza antes do novo download)."""
    for patt in ("CEPEA_*.xls", "CEPEA_*.xlsx"):
        for f in dirpath.glob(patt):
            try:
                f.unlink(missing_ok=True)
                print(f"[LIMPEZA] Removido: {f}")
            except Exception:
                pass


def baixar_serie(nome: str, page_url: str, href_sub: str, destino: Path):
    """Executa fluxo completo: limpa pasta, baixa .xls, converte para .xlsx e mantém só o mais recente."""
    print(f"\n⏬ Baixando {nome} ...")
    _clean_folder(destino)
    driver = _init_driver(destino)
    try:
        xls_path = _click_series_and_download(driver, page_url, href_sub, destino)
        print(f"✔️  {nome} salvo: {xls_path}")
    finally:
        try:
            driver.quit()
        except Exception:
            pass

    # Converte .xls -> .xlsx via Excel (win32com) e remove .xls
    xlsx_path = _convert_xls_to_xlsx_and_cleanup(xls_path)
    print(f"✔️  Convertido: {xlsx_path}")

    # Mantém só o mais recente .xlsx
    _keep_only_latest_xlsx(destino)


if __name__ == "__main__":
    print("🚀 Iniciando coleta CEPEA (Selenium + Excel)...")
    for key, meta in PAGES.items():
        baixar_serie(key, meta["page"], meta["href_sub"], DESTS[key])
    print("\n✅ DOWNLOAD + CONVERSÃO CONCLUÍDOS — 1 arquivo .xlsx por commodity mantido.")