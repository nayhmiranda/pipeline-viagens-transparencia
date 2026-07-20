# Pipeline de Viagens a Serviço — Portal da Transparência

> ⚠️ Projeto em desenvolvimento (WIP). Este README será atualizado com o
> escopo completo, resultados e conclusões ao final da implementação.

## Sobre o projeto

Pipeline de dados ETL, construído do zero em Python + PostgreSQL, seguindo a
**Arquitetura Medallion** (Raw → Silver → Gold), aplicado à base pública de
**Viagens a Serviço** do Portal da Transparência do Governo Federal.

O objetivo é transformar dados brutos e desorganizados em informação
confiável, respondendo perguntas de negócio sobre custos, destinos e
padrões de viagens a serviço com métricas e gráficos.

## Tecnologias

- Python (pandas, psycopg2, gdown, matplotlib/seaborn)
- PostgreSQL
- Jupyter Notebook
- Git / GitHub

## Estrutura do pipeline

| Arquivo | Camada | Descrição |
|---|---|---|
| `0_criar_banco.sql` | — | Criação das 8 tabelas (4 Raw + 4 Silver) |
| `1_extrair.py` | Raw | Download e carga fiel dos dados brutos |
| `2_transformar.py` | Silver | Limpeza, tipagem e cálculo de colunas derivadas |
| `3_analise.ipynb` | Gold | Perguntas de negócio, gráficos e camada agregada |

## Como executar

```bash
# 1. Clonar o repositório
git clone <url-do-repo>
cd <nome-do-repo>

# 2. Criar ambiente virtual e instalar dependências
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Configurar credenciais
cp .env.example .env
# preencher .env com usuário/senha do PostgreSQL e o DRIVE_FILE_ID

# 4. Criar o banco e as tabelas
createdb transparencia
psql -d transparencia -f 0_criar_banco.sql

# 5. Rodar o pipeline
python 1_extrair.py
python 2_transformar.py
jupyter notebook 3_analise.ipynb
```

## Status

- [x] Modelagem do banco (camadas Raw e Silver)
- [ ] Extração automatizada (camada Raw)
- [ ] Transformação e tipagem (camada Silver)
- [ ] Análise, gráficos e camada Gold
- [ ] Documentação final

## Melhorias futuras

_A preencher ao final do projeto._

## Conclusões

_A preencher ao final do projeto, com base nos resultados da camada Gold._
