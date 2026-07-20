# Pipeline de Viagens a Serviço — Portal da Transparência
## Projeto avaliativo do módulo 1 do curso de Analise de Dados com Python do SCTEC

Pipeline de dados ETL, construído do zero em **Python + PostgreSQL**, seguindo a
**Arquitetura Medallion** (Raw → Silver → Gold), aplicado à base pública de
**Viagens a Serviço** do Portal da Transparência do Governo Federal (jan-jun/2025).


## O problema que resolve

O órgão responsável publica os dados de viagens a serviço no Portal da Transparência,
mas eles chegam **brutos e desorganizados**: texto puro, datas em formato `DD/MM/AAAA`,
valores com vírgula decimal, sem tipagem nem integridade referencial entre as tabelas.
Isso torna praticamente inviável responder perguntas simples de gestão, como "quais
órgãos mais gastam?" ou "quais destinos custam mais em média?", direto do dado bruto.

Este projeto automatiza todo o caminho entre o dado bruto público e informação
confiável para tomada de decisão: baixa os dados direto da fonte (sem intervenção
manual), preserva o histórico original, limpa e tipa os dados, e constrói métricas de
negócio com gráficos.

## Técnicas e tecnologias utilizadas

- **Python** (pandas para manipulação de dados, psycopg2 para PostgreSQL, gdown para
  download automatizado do Google Drive)
- **PostgreSQL**, com modelagem relacional (PK, FK, constraints `NOT NULL`, `CHECK`,
  `UNIQUE`)
- **SQL avançado**: `CTE` (Common Table Expressions), `JOIN`, `GROUP BY`, criação de
  `VIEW` e tabela agregada
- **Jupyter Notebook** para a camada de análise, com **matplotlib** e **seaborn** para
  visualização de dados
- **Git/GitHub**, com controle de versão por branches nomeadas por funcionalidade e
  commits pequenos e descritivos

### Arquitetura (Medallion)

```
                 ┌──────────────────┐
  Google Drive   │   1_extrair.py   │   Download automatizado (gdown) + leitura
  (.zip com 4 ───▶  Idempotente      │   em blocos dos 4 CSVs originais
   CSVs)         │  (TRUNCATE)      │
                 └────────┬─────────┘
                          ▼
                 ┌──────────────────┐
                 │   CAMADA RAW     │   Cópia fiel dos CSVs (tudo VARCHAR,
                 │  raw_viagem      │   sem constraints, sem alterar conteúdo)
                 │  raw_pagamento   │
                 │  raw_passagem    │
                 │  raw_trecho      │
                 └────────┬─────────┘
                          ▼
                 ┌──────────────────┐
                 │ 2_transformar.py │   Conversão de tipos (texto → DECIMAL/DATE),
                 │  Idempotente     │   cálculo de valor_total e duracao_dias
                 └────────┬─────────┘
                          ▼
                 ┌──────────────────┐
                 │  CAMADA SILVER   │   Dados limpos e tipados, com PK, FK e
                 │  silver_viagem   │   constraints (NOT NULL, CHECK, UNIQUE)
                 │  silver_pagamento│
                 │  silver_passagem │
                 │  silver_trecho   │
                 └────────┬─────────┘
                          ▼
                 ┌──────────────────┐
                 │ 3_analise.ipynb  │   7 perguntas de negócio, gráficos e
                 └────────┬─────────┘   criação da camada Gold via JOIN+GROUP BY
                          ▼
                 ┌──────────────────┐
                 │   CAMADA GOLD    │   gold_destino_uf (tabela + view),
                 │ gold_destino_uf  │   métricas agregadas por UF de destino
                 └──────────────────┘
```

## Como executar

```bash
# 1. Clonar o repositório
git clone https://github.com/nayhmiranda/pipeline-viagens-transparencia.git
cd pipeline-viagens-transparencia

# 2. Criar ambiente virtual e instalar dependências
python -m venv venv
venv\Scripts\Activate.ps1        # Windows (PowerShell)
# source venv/bin/activate       # Mac/Linux
pip install -r requirements.txt

# 3. Configurar credenciais
cp env.example .env
# preencher .env com usuário/senha do PostgreSQL e config.py com o DRIVE_FILE_ID

# 4. Criar o banco e as 8 tabelas (4 Raw + 4 Silver)
psql -U postgres -c "CREATE DATABASE transparencia"
psql -U postgres -d transparencia -f 0_criar_banco.sql

# 5. Rodar o pipeline
python 1_extrair.py       # baixa o zip do Drive e carrega a camada Raw
python 2_transformar.py   # limpa, tipa e carrega a camada Silver

# 6. Abrir 3_analise.ipynb no VSCode (kernel: venv) e rodar todas as células
#    -> cria a camada Gold e responde as perguntas de negócio com gráficos
```

## Melhorias futuras

- Automatizar a Fase 3 (hoje manual via notebook) com um script agendável, gerando um
  relatório/dashboard atualizado periodicamente
- Adicionar testes automatizados (ex. `pytest`) para as funções de conversão de tipo
  (`converter_valor`, `converter_data`) do `2_transformar.py`
- Tratar de forma mais explícita os registros com valor `"Inválido"` na origem (hoje
  apenas filtrados na camada Gold) — idealmente sinalizando-os já na Silver com uma
  coluna de qualidade de dado
- Expandir a base para os 12 meses do ano, e permitir comparação entre semestres
- Publicar os resultados da camada Gold como dashboard interativo (ex. Streamlit),
  em vez de gráficos estáticos no notebook

## Conclusões e insights

O pipeline processou **341.860 viagens**, **606.916 pagamentos**, **167.260 passagens**
e **763.349 trechos** referentes ao primeiro semestre de 2025.

**Respostas às perguntas de negócio:**

1. **Órgão com maior custo total:** Ministério da Justiça e Segurança Pública —
   R$ 486.933.121,65, cerca de **3x o valor do segundo colocado** (Ministério da
   Defesa, R$ 156.070.304,49).
2. **Destinos (UF) com maior custo médio por viagem:** Distrito Federal (R$ 10.153,20),
   Roraima (R$ 7.464,50) e Amazonas (R$ 4.325,37) — o alto custo médio no DF reflete a
   concentração de órgãos federais em Brasília, enquanto RR e AM refletem o custo
   logístico de acesso à região Norte.
3. **Viagem de maior duração:** 384 dias, com **custo total de R$ 0,00** — na
   verificação da fonte, confirmamos que o próprio registro bruto já traz zero em
   todos os campos de valor. O motivo indicava uma relotação/cessão de longo prazo da
   servidora, não uma viagem tradicional com diárias e passagens — um bom lembrete de
   que extremos estatísticos merecem investigação antes de virar conclusão.
4. **Tipo de pagamento com maior valor médio:** Diárias (R$ 2.078,28), ligeiramente à
   frente de Passagem (R$ 1.878,34).
5. **Meio de transporte mais usado nos trechos:** Veículo Oficial (386.424 trechos),
   à frente de Aéreo (232.666) — a maior parte da movimentação é local/regional, não
   viagem aérea de longa distância.
6. **UF de destino que mais aparece em trechos:** São Paulo (82.722), seguida de
   Distrito Federal (79.962).
7. **Órgão que mais pagou no total:** Ministério da Justiça e Segurança Pública —
   R$ 488.831.110,61, calculado de forma independente (via a tabela de pagamentos),
   confirmando o resultado da pergunta 1 e reforçando a **consistência dos dados**
   entre as tabelas Silver.

**Insights gerais:**

- Um único órgão concentra quase metade do gasto total do semestre — vale investigar
  se isso reflete uma operação pontual (reforço de segurança em grandes eventos, por
  exemplo) ou é um padrão constante ao longo do ano.
- A base bruta trouxe valores de preenchimento inválido (`"Inválido"`) em campos de UF
  e meio de transporte, tratados nas agregações de negócio — uma limitação conhecida
  da fonte, não do pipeline.
- O fato de duas fontes diferentes (custo declarado na viagem vs. soma de pagamentos
  efetivos) convergirem para o mesmo órgão no topo do ranking é um bom indício de que
  a transformação Raw → Silver preservou a integridade dos dados.