# Análise de Ativos (`analise_liquidez_ativos`)

Este repositório foi desenvolvido como uma plataforma modular para a realização de análises financeiras, processamento de indicadores e modelagem de carteiras de ativos de mercado. A arquitetura foi projetada para ser altamente extensível, permitindo a fácil incorporação de novos tipos de análises, métricas e classes de ativos no futuro.

Atualmente, o projeto conta com o módulo de **Análise de Liquidez** de ativos de renda fixa (Debêntures e Títulos Públicos Federais), mas sua estrutura de código foi desenhada sob princípios de design que facilitam a criação de novos pacotes analíticos.

A base do projeto segue as boas práticas do **PEP8**, padrões **SOLID** (com foco no Princípio de Responsabilidade Única - SRP e Princípio Aberto/Fechado - OCP) e o princípio **DRY**, garantindo facilidade de manutenção e reaproveitamento de componentes entre diferentes módulos.

---

## 📂 Estrutura do Projeto

O projeto é organizado de forma modular para que novos tipos de análises possam ser facilmente acoplados:

* [analise_liquidez/](file:///home/rodrigo/projects/analise_liquidez_ativos/analise_liquidez/): Pacote contendo a lógica específica para a análise de liquidez de renda fixa.
  * [dados.py](file:///home/rodrigo/projects/analise_liquidez_ativos/analise_liquidez/dados.py): Definição declarativa dos Schemas (`DEBENTURES_SCHEMA` e `TITULOS_PUBLICOS_SCHEMA`), carregamento de dados resiliente (local/remoto) e adequação de tipos.
  * [regras.py](file:///home/rodrigo/projects/analise_liquidez_ativos/analise_liquidez/regras.py): Processamento matemático (expansão por dias úteis com base no calendário de feriados ANBIMA, cálculo de médias móveis de 21 dias úteis, volume líquido diário e análise de liquidez consolidada).
  * [graficos.py](file:///home/rodrigo/projects/analise_liquidez_ativos/analise_liquidez/graficos.py): Visualizações interativas unificadas geradas via Plotly.
  * [relatorios.py](file:///home/rodrigo/projects/analise_liquidez_ativos/analise_liquidez/relatorios.py): Funções genéricas para exibir sumários no console e gravar planilhas Excel formatadas.
* [notebooks/](file:///home/rodrigo/projects/analise_liquidez_ativos/notebooks/): Pasta dedicada a Jupyter Notebooks para exploração interativa das análises disponíveis.
  * [liquidez_debentures.ipynb](file:///home/rodrigo/projects/analise_liquidez_ativos/notebooks/liquidez_debentures.ipynb): Notebook para processamento interativo de Debêntures.
  * [titulos_publicos_liquidez.ipynb](file:///home/rodrigo/projects/analise_liquidez_ativos/notebooks/titulos_publicos_liquidez.ipynb): Notebook para processamento interativo de Títulos Públicos.
* [main.py](file:///home/rodrigo/projects/analise_liquidez_ativos/main.py): Script principal de linha de comando (CLI) que atua como orquestrador das análises disponíveis.
* [requirements.txt](file:///home/rodrigo/projects/analise_liquidez_ativos/requirements.txt): Dependências necessárias do ecossistema de dados Python (Pandas, Plotly, Bizdays, Jupyter, etc.).
* `.gitignore`: Configuração para ignorar arquivos temporários, caches (`__pycache__/`) e relatórios gerados.

### 🔮 Extensibilidade (Como adicionar novas análises)
Para adicionar novas análises ao projeto:
1. Crie uma nova subpasta de pacote (ex: `analise_volatilidade/` ou `analise_retorno/`) na raiz.
2. Implemente os módulos de leitura de dados, regras de negócio e geração de relatórios sob o mesmo padrão modular de responsabilidade única.
3. Estenda o ponto de entrada principal ([main.py](file:///home/rodrigo/projects/analise_liquidez_ativos/main.py)) adicionando novos argumentos/comandos na CLI.

---

## 🛠️ Configuração e Instalação

### 1. Inicializar o Ambiente Virtual Python
Crie e ative o ambiente virtual no terminal:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Instalar as Dependências
```bash
pip install -r requirements.txt
```

---

## 🚀 Execução das Análises Existentes

### 1. Via Linha de Comando (CLI)

O script [main.py](file:///home/rodrigo/projects/analise_liquidez_ativos/main.py) permite executar as análises disponíveis diretamente do terminal. Ele aceita parâmetros flexíveis e detecta a presença de datasets locais em `../PulseFlat/data/` de forma automática.

#### Parâmetros Suportados (Análise de Liquidez):
* `--tipo`: Define o tipo de ativo a analisar (`debentures` ou `titulos_publicos`). Padrão: `debentures`.
* `--dados`: Caminho para o arquivo local contendo os dados brutos. Se não fornecido, o script tenta ler a base local ou gera dados de testes (mock).
* `--saida`: Caminho para salvar a planilha consolidada de saída. Padrão: `relatorio_liquidez.xlsx`.
* `--gerar-mock`: Força a criação de um arquivo de dados fictícios (`mock_debentures.csv` ou `mock_titulos_publicos.csv`) para validação rápida.

#### Exemplos de Execução:
```bash
# Executar com dados reais de Títulos Públicos:
python main.py --tipo titulos_publicos --saida relatorio_tpf.xlsx

# Executar com geração forçada de dados de teste (Mock) para Debêntures:
python main.py --tipo debentures --gerar-mock --saida relatorio_teste_deb.xlsx
```

*Nota: Para evitar exceder o limite físico de 1.048.576 linhas do Excel em grandes volumes de dados reais, a planilha gerada pelo script CLI de liquidez é consolidada e contém as métricas correspondentes apenas à data de referência mais recente disponível no dataset.*

---

## 📓 Execução via Jupyter Notebooks

Os notebooks contidos na pasta [notebooks/](file:///home/rodrigo/projects/analise_liquidez_ativos/notebooks/) fornecem um ambiente interativo completo para visualização de gráficos e análise granular de carteiras de investimento:

1. Inicie o Jupyter:
   ```bash
   jupyter notebook
   ```
2. Abra um dos notebooks desejados na subpasta `notebooks/`.
3. Execute as células sequencialmente. A primeira célula contém a configuração de caminhos necessária (`sys.path`) para que o notebook se comunique diretamente com os pacotes localizados na raiz do projeto.

