"""
Módulo para carregamento, estruturação e tratamento de dados de ativos.
"""

import os
from typing import Dict, Any
import numpy as np
import pandas as pd

DEBENTURES_SCHEMA: Dict[str, Any] = {
    'type': 'debentures',
    'date_col': 'data_referencia',
    'isin_col': 'isin',
    'ativo_col': 'codigo_ativo',
    'quantity_col': 'quantidade',
    'trades_col': 'numero_de_negocios',
    'price_col': 'pu_medio',
    'price_cols': ['pu_minimo', 'pu_medio', 'pu_maximo', 'pu_da_curva'],
    'date_cols': ['data_referencia', 'data_captura'],
    'int_cols': ['quantidade', 'numero_de_negocios']
}

TITULOS_PUBLICOS_SCHEMA: Dict[str, Any] = {
    'type': 'titulos_publicos',
    'date_col': 'data_mov',
    'isin_col': 'codigo_isin',
    'ativo_col': 'codigo',
    'quantity_col': 'quant_negociada',
    'trades_col': 'num_de_oper',
    'price_col': 'pu_med',
    'price_cols': [
        'valor_negociado',
        'pu_min',
        'pu_med',
        'pu_max',
        'pu_lastro',
        'valor_par',
        'taxa_min',
        'taxa_med',
        'taxa_max'
    ],
    'date_cols': ['data_mov', 'emissao', 'vencimento'],
    'int_cols': [
        'num_de_oper',
        'quant_negociada',
        'num_oper_com_corretagem',
        'quant_neg_com_corretagem'
    ]
}


def carregar_dados_resiliente(local_path: str, url: str) -> pd.DataFrame:
    """Carrega dados localmente se o arquivo existir, senão faz o download.

    Args:
        local_path: Caminho local do arquivo.
        url: URL remota caso o arquivo local não exista.

    Returns:
        DataFrame com os dados brutos carregados.
    """
    path_to_load = local_path if os.path.exists(local_path) else url
    print(f"Carregando dados de: {path_to_load}")
    
    compression = 'gzip' if path_to_load.endswith('.gz') else None
    return pd.read_csv(path_to_load, compression=compression, low_memory=False)


def ajustar_tipos(df: pd.DataFrame, schema: Dict[str, Any]) -> pd.DataFrame:
    """Ajusta os tipos de dados conforme o schema fornecido.

    Args:
        df: DataFrame original.
        schema: Dicionário contendo as configurações de colunas do ativo.

    Returns:
        DataFrame com os tipos devidamente convertidos e limpos.
    """
    df_adjusted = df.copy()

    # Converter datas
    for col in schema['date_cols']:
        if col in df_adjusted.columns:
            df_adjusted[col] = pd.to_datetime(df_adjusted[col], errors='coerce')

    # Converter inteiros
    for col in schema['int_cols']:
        if col in df_adjusted.columns:
            df_adjusted[col] = df_adjusted[col].astype(str).replace('', np.nan)
            df_adjusted[col] = (
                pd.to_numeric(df_adjusted[col], errors='coerce')
                .fillna(0)
                .astype(int)
            )

    # Converter floats (preços e taxas)
    for col in schema['price_cols']:
        if col in df_adjusted.columns:
            if schema['type'] == 'debentures':
                # Remove separador de milhar (ponto) e substitui vírgula por ponto
                df_adjusted[col] = (
                    df_adjusted[col]
                    .astype(str)
                    .str.replace('.', '', regex=False)
                    .str.replace(',', '.', regex=False)
                )
            df_adjusted[col] = pd.to_numeric(df_adjusted[col], errors='coerce')

    return df_adjusted
