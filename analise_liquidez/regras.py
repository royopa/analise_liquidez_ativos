"""
Módulo contendo regras de negócio para análise de liquidez.
"""

from typing import List, Dict, Any
import numpy as np
import pandas as pd


def expandir_dias_uteis(
    df: pd.DataFrame,
    business_days: List[pd.Timestamp],
    schema: Dict[str, Any]
) -> pd.DataFrame:
    """Expande o DataFrame para incluir todos os dias úteis para cada ativo.

    Args:
        df: DataFrame original.
        business_days: Lista de dias úteis (ANBIMA).
        schema: Configurações de colunas do ativo.

    Returns:
        DataFrame contendo todas as datas úteis preenchidas.
    """
    date_col = schema['date_col']
    isin_col = schema['isin_col']

    all_dates_df = pd.DataFrame({date_col: business_days})
    expanded_df_list = []

    for name, group in df.groupby(isin_col):
        merged_group = pd.merge(
            all_dates_df,
            group,
            on=date_col,
            how='left'
        )

        # Preenche a coluna ISIN para as novas linhas
        merged_group[isin_col] = name

        # Ordena por data e aplica forward/backward fill
        merged_group = merged_group.sort_values(by=date_col)
        merged_group = merged_group.ffill().bfill()

        # Reconverte colunas inteiras
        for col in schema['int_cols']:
            if col in merged_group.columns:
                merged_group[col] = (
                    merged_group[col].fillna(0).astype(int)
                )

        expanded_df_list.append(merged_group)

    return pd.concat(expanded_df_list)


def filtrar_periodo_recente(
    df: pd.DataFrame,
    reference_date: pd.Timestamp,
    months_ago: int,
    schema: Dict[str, Any]
) -> pd.DataFrame:
    """Filtra o DataFrame para um período recente de meses.

    Args:
        df: DataFrame expandido.
        reference_date: Data limite superior do período.
        months_ago: Quantidade de meses para olhar para trás.
        schema: Configurações de colunas do ativo.

    Returns:
        DataFrame contendo apenas dados do período de interesse.
    """
    date_col = schema['date_col']
    max_date_analise = reference_date
    recent_start_date = max_date_analise - pd.DateOffset(months=months_ago)

    df_filtered = df[
        (df[date_col] >= recent_start_date) &
        (df[date_col] <= max_date_analise)
    ].copy()

    print(
        f"DataFrame filtrado para o período: "
        f"{recent_start_date.date()} a {max_date_analise.date()}"
    )
    return df_filtered


def calcular_medias_e_volumes(
    df: pd.DataFrame,
    schema: Dict[str, Any]
) -> pd.DataFrame:
    """Calcula médias móveis de 21 dias úteis e volumes de liquidez.

    Args:
        df: DataFrame contendo o histórico.
        schema: Configurações de colunas do ativo.

    Returns:
        DataFrame contendo a quantidade média móvel e volumes calculados.
    """
    date_col = schema['date_col']
    isin_col = schema['isin_col']
    qty_col = schema['quantity_col']
    price_col = schema['price_col']

    df_result = df.copy()
    df_result = df_result.sort_values(by=date_col)

    # Média móvel da quantidade negociada agrupada por ISIN
    rolling_qty = (
        df_result.groupby(isin_col)[qty_col]
        .transform(
            lambda x: np.floor(x.rolling(window=21, min_periods=1).mean())
        )
    )
    df_result['quantidade_media_21_dias'] = rolling_qty.astype('Int64')

    # Calcular volumes
    df_result['valor_total_sem_desconto'] = (
        df_result[price_col] * df_result['quantidade_media_21_dias']
    )
    df_result['volume_liquido_1dia_calculado'] = (
        df_result[price_col] * df_result['quantidade_media_21_dias']
    )

    return df_result


def calcular_liquidez_carteira(
    parametros: dict,
    df_dados_liquidez: pd.DataFrame,
    schema: Dict[str, Any]
) -> pd.DataFrame:
    """Calcula e retorna a liquidez para a carteira do fundo.

    Args:
        parametros: Dicionário contendo os parâmetros de carteira e prazos.
        df_dados_liquidez: DataFrame com médias móveis e volumes calculados.
        schema: Configurações de colunas do ativo.

    Returns:
        DataFrame com o resultado consolidado da liquidez por título.
    """
    date_col = schema['date_col']
    isin_col = schema['isin_col']
    price_col = schema['price_col']

    # Verifica se a chave é de debêntures ou de títulos públicos
    carteira = (
        parametros.get("carteira_de_acoes") or
        parametros.get("carteira_de_titulos_publicos") or
        parametros.get("carteira_de_debentures")
    )
    if not carteira:
        raise ValueError("Nenhuma carteira de ativos encontrada nos parâmetros.")

    data_referencia_global = pd.Timestamp(parametros["data_referencia"])
    prazo_de_cotizacao_fundo = parametros["prazo_de_cotizacao"]

    multiplicador = (
        1 if prazo_de_cotizacao_fundo <= 1
        else prazo_de_cotizacao_fundo
    )
    resultados_liquidez = []

    df_dados_liquidez = df_dados_liquidez.sort_values(by=date_col)

    print(
        f"\n--- Análise de Liquidez para a Carteira do Fundo na data "
        f"{data_referencia_global.strftime('%Y-%m-%d')} ---"
    )

    for titulo_info in carteira:
        if len(titulo_info) < 3:
            continue

        isin, codigo_ativo, quantidade_fundo = titulo_info

        # Filtrar dados de liquidez para o ISIN e data
        dados_liquidez_ativo = df_dados_liquidez[
            (df_dados_liquidez[isin_col] == isin) &
            (df_dados_liquidez[date_col] == data_referencia_global)
        ]

        if dados_liquidez_ativo.empty:
            resultados_liquidez.append({
                'isin': isin,
                'codigo_ativo': codigo_ativo,
                'quantidade_fundo': quantidade_fundo,
                'data_referencia': data_referencia_global.strftime('%Y-%m-%d'),
                price_col: np.nan,
                'liquidez_media_21_dias': 0,
                'volume_liquido_1dia_calculado': 0.0,
                'valor_total_alocado': np.nan,
                'valor_total_prazo_cotizacao': np.nan,
                'valor_total_liquido': np.nan,
                'percentual_liquido_alocado': 0.0
            })
            print(
                f"  Ativo: {codigo_ativo} (ISIN: {isin}) - Dados de "
                f"liquidez não encontrados para "
                f"{data_referencia_global.strftime('%Y-%m-%d')}"
            )
            continue

        quantidade_media_21_dias_from_df = (
            dados_liquidez_ativo['quantidade_media_21_dias'].iloc[0]
        )
        volume_liquido_1dia_calculado = (
            dados_liquidez_ativo['volume_liquido_1dia_calculado'].iloc[0]
        )
        pu_med = dados_liquidez_ativo[price_col].iloc[0]

        valor_total_alocado = pu_med * quantidade_fundo
        valor_total_prazo_cotizacao_calculado = (
            volume_liquido_1dia_calculado * multiplicador
        )
        valor_total_liquido_calculado = min(
            valor_total_alocado,
            valor_total_prazo_cotizacao_calculado
        )

        if valor_total_alocado != 0 and not np.isnan(valor_total_alocado):
            percentual_liquido_alocado = (
                (valor_total_liquido_calculado / valor_total_alocado) * 100
            )
        else:
            percentual_liquido_alocado = 0.0

        resultados_liquidez.append({
            'isin': isin,
            'codigo_ativo': codigo_ativo,
            'quantidade_fundo': quantidade_fundo,
            'data_referencia': data_referencia_global.strftime('%Y-%m-%d'),
            price_col: pu_med,
            'liquidez_media_21_dias': quantidade_media_21_dias_from_df,
            'volume_liquido_1dia_calculado': volume_liquido_1dia_calculado,
            'valor_total_alocado': valor_total_alocado,
            'valor_total_prazo_cotizacao':
                valor_total_prazo_cotizacao_calculado,
            'valor_total_liquido': valor_total_liquido_calculado,
            'percentual_liquido_alocado': percentual_liquido_alocado
        })
        print(
            f"  Ativo: {codigo_ativo} (ISIN: {isin}) - Dados de "
            f"liquidez encontrados."
        )

    return pd.DataFrame(resultados_liquidez)
