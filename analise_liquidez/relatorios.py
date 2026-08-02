"""
Módulo para geração de relatórios de liquidez (Console e Excel).
"""

import os
from pathlib import Path
from typing import Union, Dict, Any
import pandas as pd


def gerar_relatorio_excel(
    df_resultado: pd.DataFrame,
    caminho_saida: Union[str, Path]
) -> None:
    """Gera um relatório Excel com o resultado da classificação de liquidez.

    Args:
        df_resultado: DataFrame contendo as métricas calculadas.
        caminho_saida: Caminho para gravação do arquivo Excel.
    """
    caminho = Path(caminho_saida)

    # Cria o diretório de saída se não existir
    caminho.parent.mkdir(parents=True, exist_ok=True)

    with pd.ExcelWriter(caminho, engine='openpyxl') as writer:
        df_resultado.to_excel(writer, sheet_name='Analise de Liquidez')

    print(f"Relatório de liquidez gerado com sucesso em: {caminho}")


def exibir_resumo_console(
    df_resultado: pd.DataFrame,
    schema: Dict[str, Any]
) -> None:
    """Exibe um resumo simplificado da análise de liquidez no console.

    Args:
        df_resultado: DataFrame contendo as métricas de liquidez.
        schema: Configurações de colunas do ativo.
    """
    isin_col = schema['isin_col']
    qty_col = 'quantidade_media_21_dias'
    vol_col = 'volume_liquido_1dia_calculado'

    print("\n" + "=" * 60)
    print(" RESUMO DA ANÁLISE DE LIQUIDEZ ".center(60, "="))
    print("=" * 60)
    print(f"Total de ativos analisados: {len(df_resultado)}")
    print("-" * 60)

    # Exibir detalhes de cada título no console
    # Se a coluna 'codigo_ativo' existir, usa, senão usa 'codigo'
    cod_col = schema['ativo_col']
    
    # Se o dataframe tiver os resultados da carteira
    if 'quantidade_fundo' in df_resultado.columns:
        print("Detalhamento da Liquidez da Carteira:")
        for _, row in df_resultado.iterrows():
            print(
                f" - {row['codigo_ativo']} ({row['isin']}): "
                f"Quantidade: {row['quantidade_fundo']:,} | "
                f"Média 21d: {row['liquidez_media_21_dias']:,} | "
                f"Vol Líquido: R$ {row['volume_liquido_1dia_calculado']:,.2f} | "
                f"Cobertura Alocada: {row['percentual_liquido_alocado']:.1f}%"
            )
    else:
        # Se for o dataframe geral do histórico (ex: df_analise)
        print("Top Títulos mais Líquidos (Volume Médio):")
        top_liquidos = df_resultado.groupby([isin_col, cod_col])[vol_col].mean().nlargest(5)
        for (isin, cod), vol in top_liquidos.items():
            print(f" - Ativo: {cod} ({isin}) | Volume Médio: R$ {vol:,.2f}")

    print("=" * 60 + "\n")
