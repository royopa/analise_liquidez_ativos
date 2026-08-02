import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from typing import Optional

def plot_titulo_plotly(
    df_data: pd.DataFrame,
    isin_to_plot: str,
    codigo_ativo_to_plot: str = None,
    schema: dict = None,
    y_column: str = 'num_de_oper',
    title_suffix: str = "(Últimos 3 Meses)",
    window_size: int = 7,
    window_size_secondary: Optional[int] = None
) -> go.Figure:
    """
    Gera e retorna um gráfico interativo de linha para a quantidade diária negociada
    ou número de negócios de um título e sua(s) média(s) móvel(eis) usando Plotly Express.
    """
    if schema is None:
        raise ValueError("Schema de colunas do ativo deve ser fornecido.")
        
    date_col = schema['date_col']
    isin_col = schema['isin_col']
    
    # Filtrar o DataFrame para o ISIN específico
    df_plot = df_data[df_data[isin_col] == isin_to_plot].copy()
    
    # Garantir ordenação por data
    df_plot = df_plot.sort_values(by=date_col)
    
    # Média móvel primária
    df_plot[f'{y_column}_rolling_mean'] = df_plot[y_column].rolling(window=window_size, min_periods=1).mean()
    value_vars_to_melt = [y_column, f'{y_column}_rolling_mean']
    
    # Média móvel secundária
    if window_size_secondary is not None:
        df_plot[f'{y_column}_rolling_mean_secondary'] = df_plot[y_column].rolling(window=window_size_secondary, min_periods=1).mean()
        value_vars_to_melt.append(f'{y_column}_rolling_mean_secondary')
        
    # Melt
    df_melted = df_plot.melt(
        id_vars=[date_col],
        value_vars=value_vars_to_melt,
        var_name='Tipo', 
        value_name='Valor'
    )
    
    legend_map = {
        'quantidade': 'Quantidade Diária Negociada',
        'quant_negociada': 'Quantidade Diária Negociada',
        'numero_de_negocios': 'Número Diário de Negócios',
        'num_de_oper': 'Número Diário de Negócios'
    }
    
    y_base_label = legend_map.get(y_column, y_column.replace('_', ' ').title())
    
    type_labels = {
        y_column: y_base_label,
        f'{y_column}_rolling_mean': f'Média Móvel ({window_size} Dias) de {y_base_label.split(" ")[0]}'
    }
    if window_size_secondary is not None:
        type_labels[f'{y_column}_rolling_mean_secondary'] = f'Média Móvel ({window_size_secondary} Dias) de {y_base_label.split(" ")[0]}'
        
    df_melted['Tipo'] = df_melted['Tipo'].map(type_labels)
    
    title_text = f'{y_base_label} e Média(s) Móvel(eis) para o Título {isin_to_plot}'
    if codigo_ativo_to_plot:
        title_text += f' ({codigo_ativo_to_plot})'
    title_text += f' {title_suffix}'
    
    fig = px.line(
        df_melted,
        x=date_col,
        y='Valor',
        color='Tipo',
        title=title_text,
        labels={'Valor': y_base_label, date_col: 'Data de Referência'},
        line_dash='Tipo',
        markers=True,
        hover_data={date_col: '|%Y-%m-%d', 'Valor': ':,.0f'}
    )
    
    fig.update_yaxes(tickformat=",.0f")
    fig.update_xaxes(dtick="M1", tickformat="%Y-%m-%d")
    
    fig.update_layout(
        hovermode="x unified",
        legend_title_text='Tipo de Negociação',
        font=dict(size=12),
        title_font_size=16,
        xaxis_title_font_size=14,
        yaxis_title_font_size=14,
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.15,
            xanchor="center",
            x=0.5
        )
    )
    
    return fig
