"""
Script principal (CLI) para orquestração da análise de liquidez.
"""

import argparse
import os
from pathlib import Path
from typing import Dict, Any
import numpy as np
import pandas as pd

from analise_liquidez.dados import (
    DEBENTURES_SCHEMA,
    TITULOS_PUBLICOS_SCHEMA,
    carregar_dados_resiliente,
    ajustar_tipos
)
from analise_liquidez.regras import (
    expandir_dias_uteis,
    calcular_medias_e_volumes
)
from analise_liquidez.relatorios import (
    gerar_relatorio_excel,
    exibir_resumo_console
)


def gerar_dados_mock(caminho_saida: Path, schema: Dict[str, Any]) -> None:
    """Gera um arquivo de dados fictícios em conformidade com o schema.

    Args:
        caminho_saida: Caminho para gravação do arquivo CSV.
        schema: Configurações de colunas do ativo.
    """
    np.random.seed(42)
    datas = pd.date_range(start='2026-07-01', periods=21, freq='B')

    # Identificadores de colunas do schema
    date_col = schema['date_col']
    isin_col = schema['isin_col']
    ativo_col = schema['ativo_col']
    qty_col = schema['quantity_col']
    trades_col = schema['trades_col']
    price_col = schema['price_col']

    ativos = [
        ('BR1111111110', 'ATIVO_AAA'),
        ('BR2222222220', 'ATIVO_BBB'),
        ('BR3333333330', 'ATIVO_CCC'),
        ('BR4444444440', 'ATIVO_ILLIQ')
    ]

    linhas = []
    for data in datas:
        for isin, ativo in ativos:
            if ativo == 'ATIVO_AAA':
                vol = np.random.uniform(500000, 2000000)
                neg = np.random.randint(10, 50)
                qtd = np.random.randint(500, 2000)
            elif ativo == 'ATIVO_BBB':
                vol = np.random.uniform(80000, 200000)
                neg = np.random.randint(2, 10)
                qtd = np.random.randint(100, 500)
            elif ativo == 'ATIVO_CCC':
                vol = np.random.uniform(10000, 50000)
                neg = np.random.randint(1, 5)
                qtd = np.random.randint(10, 50)
            else:  # ATIVO_ILLIQ
                if np.random.rand() > 0.85:
                    vol = np.random.uniform(5000, 20000)
                    neg = np.random.randint(1, 3)
                    qtd = np.random.randint(5, 20)
                else:
                    vol = 0.0
                    neg = 0
                    qtd = 0

            if neg > 0:
                linhas.append({
                    date_col: data,
                    isin_col: isin,
                    ativo_col: ativo,
                    qty_col: qtd,
                    trades_col: neg,
                    price_col: (vol / qtd) if qty_col else 1000.0
                })

    df_mock = pd.DataFrame(linhas)
    df_mock.to_csv(caminho_saida, index=False)
    print(f"Dados fictícios gerados em: {caminho_saida}")


def main() -> None:
    """Ponto de entrada principal do orquestrador CLI."""
    parser = argparse.ArgumentParser(
        description="Análise de Liquidez de Títulos"
    )
    parser.add_argument(
        '--tipo',
        choices=['debentures', 'titulos_publicos'],
        default='debentures',
        help='Tipo de ativo a ser analisado (debentures ou titulos_publicos).'
    )
    parser.add_argument(
        '--dados',
        type=str,
        help='Caminho para o arquivo de dados de entrada.'
    )
    parser.add_argument(
        '--saida',
        type=str,
        default='relatorio_liquidez.xlsx',
        help='Caminho para salvar o relatório de saída (Excel).'
    )
    parser.add_argument(
        '--gerar-mock',
        action='store_true',
        help='Gera um arquivo de testes fictício.'
    )

    args = parser.parse_args()

    # Selecionar o schema e os caminhos com base no tipo
    if args.tipo == 'debentures':
        schema = DEBENTURES_SCHEMA
        local_path = (
            "../PulseFlat/data/"
            "debentures_mercado_secundario_precos_negociacao.csv.gz"
        )
        url = (
            "https://raw.githubusercontent.com/royopa/PulseFlat/"
            "main/data/debentures_mercado_secundario_precos_negociacao.csv.gz"
        )
    else:
        schema = TITULOS_PUBLICOS_SCHEMA
        local_path = (
            "../PulseFlat/data/"
            "bacen_negociacao_tpf_extragrupo.csv.gz"
        )
        url = (
            "https://github.com/PulseDataLabs/PulseFlat/"
            "raw/refs/heads/main/data/bacen_negociacao_tpf_extragrupo.csv.gz"
        )

    caminho_dados = args.dados

    # Geração/Verificação de mock
    if args.gerar_mock:
        caminho_mock = Path(f"mock_{args.tipo}.csv")
        gerar_dados_mock(caminho_mock, schema)
        caminho_dados = str(caminho_mock)
    elif not caminho_dados:
        # Tenta carregar os dados locais da base PulseFlat
        if os.path.exists(local_path):
            caminho_dados = local_path
        else:
            # Caso contrário, gera e usa dados de teste locais
            caminho_mock = Path(f"mock_{args.tipo}.csv")
            if not caminho_mock.exists():
                gerar_dados_mock(caminho_mock, schema)
            caminho_dados = str(caminho_mock)

    print(f"Iniciando processamento dos dados: {caminho_dados}")

    # Pipeline de Execução (SOLID / DRY)
    df_raw = carregar_dados_resiliente(caminho_dados, url)
    df_adjusted = ajustar_tipos(df_raw, schema)

    # Obter dias úteis da ANBIMA para expansão
    from bizdays import Calendar
    cal = Calendar.load('ANBIMA')
    min_date = df_adjusted[schema['date_col']].min()
    max_date = df_adjusted[schema['date_col']].max()

    business_days = cal.seq(min_date, max_date)
    business_days_ts = pd.to_datetime(business_days)

    # Processamento
    df_expanded = expandir_dias_uteis(df_adjusted, business_days_ts, schema)
    df_resultado = calcular_medias_e_volumes(df_expanded, schema)

    # Filtrar relatório do Excel apenas para a data mais recente (evita ultrapassar limites)
    df_excel = df_resultado[df_resultado[schema['date_col']] == max_date]

    # Exibir resumo e salvar relatório
    exibir_resumo_console(df_resultado, schema)
    gerar_relatorio_excel(df_excel, args.saida)


if __name__ == '__main__':
    main()
