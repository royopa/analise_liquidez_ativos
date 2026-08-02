"""
Utilitários compartilhados para padronizar pipelines nos notebooks.
"""

import io
import os
import zipfile
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import pandas as pd
import plotly.express as px
import requests
from bizdays import Calendar

from analise_liquidez.dados import ajustar_tipos, carregar_dados_resiliente
from analise_liquidez.regras import expandir_dias_uteis, filtrar_periodo_recente

URL_COTAHIST_FORMAT = (
    "https://bvmf.bmfbovespa.com.br/InstDados/SerHist/COTAHIST_A{ano}.ZIP"
)
HEADERS_HTTP = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "text/plain, */*",
    "Referer": "https://www.b3.com.br/",
    "Origin": "https://www.b3.com.br",
}
COTAHIST_WIDTHS = [
    2, 8, 2, 12, 3, 12, 10, 3, 4, 13, 13, 13, 13,
    13, 13, 13, 5, 18, 18, 13, 1, 8, 7, 13, 12, 3
]
COTAHIST_FIELDS = [
    "regtype", "refdate", "bdi_code", "symbol", "instrument_market",
    "corporation_name", "specification_code", "days_to_settlement",
    "trading_currency", "open", "high", "low", "average", "close",
    "best_bid", "best_ask", "trade_quantity", "traded_contracts", "volume",
    "strike_price", "strike_price_adjustment_indicator", "maturity_date",
    "allocation_lot_size", "strike_price_in_points", "isin",
    "distribution_id",
]


def resolver_caminho_local(caminhos: Sequence[str]) -> str:
    """Retorna o primeiro caminho local existente."""
    for caminho in caminhos:
        if os.path.exists(caminho):
            return caminho
    return caminhos[0]


def carregar_dados_ativo_com_cache(
    schema: Dict[str, Any],
    cache_path: str,
    url: str,
    local_paths: Sequence[str],
    drop_cols: Optional[Iterable[str]] = None
) -> pd.DataFrame:
    """Carrega dados com cache local e aplica limpeza/tipagem padronizada."""
    if os.path.exists(cache_path):
        print(f"Usando cache local: {cache_path}")
        df_cache = pd.read_csv(cache_path, compression="gzip", low_memory=False)
        return ajustar_tipos(df_cache, schema)

    local_path = resolver_caminho_local(local_paths)
    df_raw = carregar_dados_resiliente(local_path, url)

    if drop_cols:
        for col in drop_cols:
            if col in df_raw.columns:
                del df_raw[col]

    df_adjusted = ajustar_tipos(df_raw, schema)
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    df_adjusted.to_csv(cache_path, index=False, compression="gzip")
    print(f"Cache salvo em: {cache_path}")
    return df_adjusted


def preparar_historico_expandido(
    df: pd.DataFrame,
    schema: Dict[str, Any],
    cache_path: Optional[str] = None
) -> pd.DataFrame:
    """Expande por dias úteis com cache opcional."""
    if cache_path and os.path.exists(cache_path):
        print(f"Usando cache expandido: {cache_path}")
        df_cache = pd.read_csv(cache_path, compression="gzip", low_memory=False)
        return ajustar_tipos(df_cache, schema)

    date_col = schema["date_col"]
    cal = Calendar.load("ANBIMA")
    min_date = df[date_col].min()
    max_date = df[date_col].max()
    business_days = pd.to_datetime(cal.seq(min_date, max_date))

    print(f"Data mínima: {min_date.date()} | Data máxima: {max_date.date()}")
    df_expanded = expandir_dias_uteis(df, business_days, schema)

    if cache_path:
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        df_expanded.to_csv(cache_path, index=False, compression="gzip")
        print(f"Cache expandido salvo em: {cache_path}")

    return df_expanded


def preparar_recorte_recente(
    df: pd.DataFrame,
    schema: Dict[str, Any],
    data_referencia: pd.Timestamp,
    meses: int
) -> pd.DataFrame:
    """Aplica recorte temporal e ajuste de tipos de forma padronizada."""
    df_recente = filtrar_periodo_recente(
        df=df,
        reference_date=pd.Timestamp(data_referencia),
        months_ago=meses,
        schema=schema
    )
    return ajustar_tipos(df_recente, schema)


def aplicar_filtro_outlier_quantidade(
    df: pd.DataFrame,
    schema: Dict[str, Any],
    quantile: float = 0.999
) -> pd.DataFrame:
    """Remove valores extremos de quantidade que distorcem métricas agregadas."""
    qty_col = schema["quantity_col"]
    if qty_col not in df.columns:
        return df

    serie_base = df.loc[df[qty_col] > 0, qty_col]
    if serie_base.empty:
        return df

    limite_superior = serie_base.quantile(quantile)
    if pd.isna(limite_superior) or limite_superior <= 0:
        return df

    mask = (df[qty_col] <= limite_superior) | (df[qty_col] <= 0)
    removidos = (~mask).sum()
    if removidos > 0:
        print(
            f"Removendo {removidos} linhas com {qty_col} acima de "
            f"{quantile:.3f} (limite={limite_superior:,.0f})."
        )
    return df.loc[mask].copy()


def calcular_top_negociados(
    df: pd.DataFrame,
    schema: Dict[str, Any],
    top_n: int
) -> Tuple[List[str], pd.DataFrame]:
    """Retorna ranking dos ativos mais negociados por número de negócios."""
    isin_col = schema["isin_col"]
    ativo_col = schema["ativo_col"]
    trades_col = schema["trades_col"]

    top_series = (
        df.groupby(isin_col)[trades_col]
        .sum()
        .nlargest(top_n)
    )
    top_isins = top_series.index.tolist()
    top_info = (
        df[df[isin_col].isin(top_isins)][[isin_col, ativo_col]]
        .drop_duplicates()
        .set_index(isin_col)
        .reindex(top_isins)
        .reset_index()
        .merge(top_series.rename("total_negocios"), on=isin_col, how="left")
    )
    return top_isins, top_info


def gerar_grafico_top_quantidade_media(
    df_analise: pd.DataFrame,
    schema: Dict[str, Any],
    top_n: int,
    title: str
):
    """Gera DataFrame + gráfico de barras do top N por média de 21 dias."""
    isin_col = schema["isin_col"]
    ativo_col = schema["ativo_col"]
    top_media = (
        df_analise.groupby(isin_col)["quantidade_media_21_dias"]
        .sum()
        .nlargest(top_n)
        .reset_index()
    )
    top_info = top_media.merge(
        df_analise[[isin_col, ativo_col]].drop_duplicates(),
        on=isin_col,
        how="left"
    )
    top_info["isin_codigo"] = (
        top_info[isin_col] + " (" + top_info[ativo_col].astype(str) + ")"
    )

    fig = px.bar(
        top_info,
        x="isin_codigo",
        y="quantidade_media_21_dias",
        title=title,
        labels={
            "isin_codigo": "ISIN (Código Ativo)",
            "quantidade_media_21_dias": "Soma da Quantidade Média de 21 Dias"
        }
    )
    fig.update_layout(xaxis={"categoryorder": "total descending"})
    return top_info, fig


def decode_bytes(content: bytes) -> str:
    """Decodifica o conteúdo bruto do COTAHIST."""
    for enc in ("utf-8-sig", "latin1", "cp1252"):
        try:
            return content.decode(enc)
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", errors="replace")


def baixar_cotahist(ano: int) -> pd.DataFrame:
    """Baixa o COTAHIST anual da B3 e retorna negócios (regtype 01)."""
    url = URL_COTAHIST_FORMAT.format(ano=ano)
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


def tratar_cotahist_acoes(
    df: pd.DataFrame,
    schema: Dict[str, Any]
) -> pd.DataFrame:
    """Filtra ações à vista em lote padrão e converte tipos/preços."""
    df = df[(df["instrument_market"] == "010") & (df["bdi_code"] == "02")].copy()
    spec = df["specification_code"].str.strip().str.upper()
    df = df[spec.str.startswith(("ON", "PN", "UNT"))].copy()
    df = df.rename(
        columns={
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
        }
    )

    for col in schema["price_cols"]:
        df[col] = pd.to_numeric(df[col], errors="coerce") / 100
    df["ntl_fin_vol"] = pd.to_numeric(df["ntl_fin_vol"], errors="coerce") / 100

    df = ajustar_tipos(df, schema)
    colunas = (
        ["data_referencia", "codigo_ativo", "isin"]
        + schema["price_cols"]
        + schema["int_cols"]
        + ["ntl_fin_vol"]
    )
    df = df[colunas].drop_duplicates(
        subset=["data_referencia", "codigo_ativo"], keep="last"
    )
    return df.sort_values(["codigo_ativo", "data_referencia"]).reset_index(drop=True)


def carregar_cotahist_acoes(
    anos: Sequence[int],
    cache_path: str,
    schema: Dict[str, Any]
) -> pd.DataFrame:
    """Baixa anos do COTAHIST com cache local e retorna ações tratadas."""
    if os.path.exists(cache_path):
        print(f"Usando cache local: {cache_path}")
        df_cache = pd.read_csv(cache_path, compression="gzip", low_memory=False)
        return ajustar_tipos(df_cache, schema).sort_values(
            ["codigo_ativo", "data_referencia"]
        ).reset_index(drop=True)

    df_bruto = pd.concat([baixar_cotahist(ano) for ano in anos], ignore_index=True)
    df_acoes = tratar_cotahist_acoes(df_bruto, schema)
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    df_acoes.to_csv(cache_path, index=False, compression="gzip")
    print(f"Cache salvo em: {cache_path}")
    return df_acoes
