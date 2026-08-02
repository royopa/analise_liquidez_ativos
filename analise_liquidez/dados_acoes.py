"""
Módulo para utilitários específicos de ações, FIIs e ETFs via COTAHIST da B3.
"""

from __future__ import annotations

import io
import os
import zipfile
from typing import Iterable

import pandas as pd
import requests

from analise_liquidez.dados import ACOES_SCHEMA, ajustar_tipos

URL_FORMAT = "https://bvmf.bmfbovespa.com.br/InstDados/SerHist/COTAHIST_A{ano}.ZIP"
COTAHIST_WIDTHS = [
    2, 8, 2, 12, 3, 12, 10, 3, 4, 13, 13, 13, 13, 13, 13, 13,
    5, 18, 18, 13, 1, 8, 7, 13, 12, 3
]
COTAHIST_FIELDS = [
    "regtype", "refdate", "bdi_code", "symbol", "instrument_market", "corporation_name",
    "specification_code", "days_to_settlement", "trading_currency", "open", "high", "low",
    "average", "close", "best_bid", "best_ask", "trade_quantity", "traded_contracts",
    "volume", "strike_price", "strike_price_adjustment_indicator", "maturity_date",
    "allocation_lot_size", "strike_price_in_points", "isin", "distribution_id",
]
HEADERS_HTTP = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "text/plain, */*",
    "Referer": "https://www.b3.com.br/",
    "Origin": "https://www.b3.com.br",
}

# Regras configuráveis de liquidação por classe de ativo.
# Ações, FIIs e ETFs negociados na B3 tipicamente liquidam em D+2.
# Se o fundo tiver prazo de cotização/pagamento menor do que isso, a liquidez deve zerar.
PRAZO_LIQUIDACAO_POR_TIPO = {
    "acao": 2,
    "acoes": 2,
    "fii": 2,
    "fiis": 2,
    "etf": 2,
    "etfs": 2,
    "titulo_publico": 1,
    "titulos_publicos": 1,
    "debenture": 1,
    "debentures": 1,
}


def decode_bytes(content: bytes) -> str:
    """Decodifica o conteúdo bruto do COTAHIST (latin1/cp1252/utf-8)."""
    for enc in ("utf-8-sig", "latin1", "cp1252"):
        try:
            return content.decode(enc)
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", errors="replace")


def baixar_cotahist(ano: int) -> pd.DataFrame:
    """Baixa o COTAHIST anual da B3 e retorna os registros de negócios (regtype 01)."""
    url = URL_FORMAT.format(ano=ano)
    print(f"Baixando {url}")
    resp = requests.get(url, headers=HEADERS_HTTP, timeout=600)
    resp.raise_for_status()
    print(f"  {len(resp.content) / 1e6:.1f} MB recebidos")

    frames = []
    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        for info in zf.infolist():
            if info.is_dir() or info.file_size == 0:
                continue
            text = decode_bytes(zf.read(info.filename))
            df = pd.read_fwf(
                io.StringIO(text),
                widths=COTAHIST_WIDTHS,
                names=COTAHIST_FIELDS,
                dtype=str,
                header=None,
                skiprows=1,
            )
            df = df[df["regtype"] == "01"].copy()
            print(f"  {info.filename}: {len(df):,} registros de negócios")
            frames.append(df)
    return pd.concat(frames, ignore_index=True)


def tratar_acoes(df: pd.DataFrame) -> pd.DataFrame:
    """Filtra ações à vista em lote padrão e converte tipos/preços."""
    df = df[(df["instrument_market"] == "010") & (df["bdi_code"] == "02")].copy()
    spec = df["specification_code"].str.strip().str.upper()
    df = df[spec.str.startswith(("ON", "PN", "UNT"))].copy()
    df = df.rename(columns={
        "refdate": "data_referencia",
        "symbol": "codigo_ativo",
        "isin": "isin",
        "open": "preco_abertura",
        "high": "preco_maximo",
        "low": "preco_minimo",
        "average": "preco_medio",
        "close": "preco_ultimo",
        "trade_quantity": "trad_qty",
        "traded_contracts": "fin_instrm_qty",
        "volume": "ntl_fin_vol",
    })
    for col in ACOES_SCHEMA["price_cols"]:
        df[col] = pd.to_numeric(df[col], errors="coerce") / 100
    df["ntl_fin_vol"] = pd.to_numeric(df["ntl_fin_vol"], errors="coerce") / 100

    df = ajustar_tipos(df, ACOES_SCHEMA)
    colunas = ["data_referencia", "codigo_ativo", "isin"] + ACOES_SCHEMA["price_cols"] + ACOES_SCHEMA["int_cols"] + ["ntl_fin_vol"]
    df = df[colunas]
    df = df.drop_duplicates(subset=["data_referencia", "codigo_ativo"], keep="last")
    return df.sort_values(["codigo_ativo", "data_referencia"]).reset_index(drop=True)


def carregar_cotahist(anos: Iterable[int], cache_path: str) -> pd.DataFrame:
    """Baixa os anos solicitados (com cache local) e retorna as ações tratadas."""
    if os.path.exists(cache_path):
        print(f"Usando cache local: {cache_path}")
        df = pd.read_csv(cache_path, compression="gzip", dtype=str, low_memory=False)
        df = ajustar_tipos(df, ACOES_SCHEMA)
        df["ntl_fin_vol"] = pd.to_numeric(df["ntl_fin_vol"], errors="coerce").fillna(0.0)
        return df.sort_values(["codigo_ativo", "data_referencia"]).reset_index(drop=True)

    df_bruto = pd.concat([baixar_cotahist(a) for a in anos], ignore_index=True)
    df = tratar_acoes(df_bruto)
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    df.to_csv(cache_path, index=False, compression="gzip")
    print(f"Cache salvo em: {cache_path}")
    return df


def obter_prazo_liquidacao(tipo_ativo: str, valor_padrao: int = 2) -> int:
    """Retorna o prazo de liquidação financeira por tipo de ativo."""
    return PRAZO_LIQUIDACAO_POR_TIPO.get(tipo_ativo.lower(), valor_padrao)
