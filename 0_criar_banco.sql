-- ==========================================================
-- Pipeline de Viagens a Serviço - Portal da Transparência
-- Arquitetura Medallion (Raw -> Silver -> Gold)
-- Banco: PostgreSQL
-- ==========================================================
-- OBSERVAÇÕES:
-- Rode "CREATE DATABASE viagens_servico;" separadamente (fora
-- de uma transação) e depois conecte nele antes de rodar este
-- script, ex.: psql -U seu_usuario -d viagens_servico -f 0_criar_banco.sql

-- ==========================================================
-- CAMADA RAW
-- Cópia fiel dos CSVs: todas as colunas VARCHAR, sem constraints.
-- Replica o CSV inteiro (inclui colunas que a Silver não usa).
-- ==========================================================

DROP TABLE IF EXISTS raw_trecho;
DROP TABLE IF EXISTS raw_passagem;
DROP TABLE IF EXISTS raw_pagamento;
DROP TABLE IF EXISTS raw_viagem;

CREATE TABLE raw_viagem (
    id_viagem                 VARCHAR,
    num_proposta               VARCHAR,
    situacao                   VARCHAR,
    viagem_urgente              VARCHAR,
    justificativa_urgencia      VARCHAR,
    cod_orgao_superior          VARCHAR,
    nome_orgao_superior         VARCHAR,
    cod_orgao_solicitante       VARCHAR,
    nome_orgao_solicitante      VARCHAR,
    cpf_viajante                VARCHAR,
    nome_viajante                VARCHAR,
    cargo                       VARCHAR,
    funcao                     VARCHAR,
    descricao_funcao            VARCHAR,
    data_inicio                 VARCHAR,
    data_fim                    VARCHAR,
    destinos                   VARCHAR,
    motivo                     VARCHAR,
    valor_diarias                VARCHAR,
    valor_passagens              VARCHAR,
    valor_devolucao              VARCHAR,
    valor_outros_gastos          VARCHAR
);

CREATE TABLE raw_pagamento (
    id_viagem            VARCHAR,
    num_proposta          VARCHAR,
    cod_orgao_superior     VARCHAR,
    nome_orgao_superior    VARCHAR,
    cod_orgao_pagador       VARCHAR,
    nome_orgao_pagador      VARCHAR,
    cod_ug_pagadora         VARCHAR,
    nome_ug_pagadora        VARCHAR,
    tipo_pagamento         VARCHAR,
    valor                  VARCHAR
);

CREATE TABLE raw_passagem (
    id_viagem              VARCHAR,
    num_proposta            VARCHAR,
    meio_transporte          VARCHAR,
    pais_origem_ida          VARCHAR,
    uf_origem_ida            VARCHAR,
    cidade_origem_ida         VARCHAR,
    pais_destino_ida         VARCHAR,
    uf_destino_ida           VARCHAR,
    cidade_destino_ida        VARCHAR,
    pais_origem_volta         VARCHAR,
    uf_origem_volta          VARCHAR,
    cidade_origem_volta       VARCHAR,
    pais_destino_volta        VARCHAR,
    uf_destino_volta         VARCHAR,
    cidade_destino_volta      VARCHAR,
    valor_passagem           VARCHAR,
    taxa_servico             VARCHAR,
    data_emissao             VARCHAR,
    hora_emissao             VARCHAR
);

CREATE TABLE raw_trecho (
    id_viagem            VARCHAR,
    num_proposta          VARCHAR,
    sequencia_trecho       VARCHAR,
    origem_data            VARCHAR,
    origem_pais            VARCHAR,
    origem_uf              VARCHAR,
    origem_cidade           VARCHAR,
    destino_data           VARCHAR,
    destino_pais            VARCHAR,
    destino_uf             VARCHAR,
    destino_cidade          VARCHAR,
    meio_transporte         VARCHAR,
    numero_diarias          VARCHAR,
    missao                 VARCHAR
);

-- ==========================================================
-- CAMADA SILVER
-- Dados limpos e tipados, com PK, FK e constraints.
-- ==========================================================

DROP TABLE IF EXISTS silver_trecho;
DROP TABLE IF EXISTS silver_passagem;
DROP TABLE IF EXISTS silver_pagamento;
DROP TABLE IF EXISTS silver_viagem;

CREATE TABLE silver_viagem (
    id_viagem            VARCHAR(20)   PRIMARY KEY NOT NULL,
    num_proposta          VARCHAR(20),
    situacao              VARCHAR(50),
    viagem_urgente         VARCHAR(5),
    cod_orgao_superior      VARCHAR(20),
    nome_orgao_superior     VARCHAR(255)  NOT NULL,
    nome_viajante            VARCHAR(255),
    cargo                  VARCHAR(255),
    data_inicio             DATE,
    data_fim                DATE,
    destinos               VARCHAR(4000),
    motivo                 VARCHAR(4000),
    valor_diarias            DECIMAL(10,2) CHECK (valor_diarias >= 0),
    valor_passagens          DECIMAL(10,2),
    valor_devolucao          DECIMAL(10,2),
    valor_outros_gastos      DECIMAL(10,2),
    valor_total             DECIMAL(12,2),   -- calculado na etapa 2
    duracao_dias            INT              -- calculado na etapa 2
);

CREATE TABLE silver_pagamento (
    id_pagamento         SERIAL         PRIMARY KEY,
    id_viagem            VARCHAR(20)    NOT NULL REFERENCES silver_viagem(id_viagem),
    num_proposta          VARCHAR(20),
    nome_orgao_pagador      VARCHAR(255),
    nome_ug_pagadora        VARCHAR(255),
    tipo_pagamento         VARCHAR(50)    NOT NULL,
    valor                 DECIMAL(10,2)  CHECK (valor >= 0)
);

CREATE TABLE silver_passagem (
    id_passagem           SERIAL         PRIMARY KEY,
    id_viagem             VARCHAR(20)    NOT NULL REFERENCES silver_viagem(id_viagem),
    meio_transporte          VARCHAR(50),
    pais_origem_ida          VARCHAR(60),
    uf_origem_ida            VARCHAR(40),
    cidade_origem_ida         VARCHAR(80),
    pais_destino_ida         VARCHAR(60),
    uf_destino_ida           VARCHAR(40),
    cidade_destino_ida        VARCHAR(80),
    valor_passagem           DECIMAL(10,2)  CHECK (valor_passagem >= 0),
    taxa_servico             DECIMAL(10,2)  CHECK (taxa_servico >= 0),
    data_emissao             DATE
);

CREATE TABLE silver_trecho (
    id_trecho            SERIAL         PRIMARY KEY,
    id_viagem            VARCHAR(20)    NOT NULL REFERENCES silver_viagem(id_viagem),
    sequencia_trecho       INT,
    origem_data            DATE,
    origem_uf              VARCHAR(40),
    origem_cidade           VARCHAR(80),
    destino_data           DATE,
    destino_uf             VARCHAR(40),
    destino_cidade          VARCHAR(80),
    meio_transporte         VARCHAR(50),
    numero_diarias          DECIMAL(10,2)  CHECK (numero_diarias >= 0),
    UNIQUE (id_viagem, sequencia_trecho)
);

-- ==========================================================
-- Índices auxiliares nas FKs (melhora performance dos JOINs
-- na camada Gold
-- ==========================================================
CREATE INDEX idx_pagamento_id_viagem ON silver_pagamento(id_viagem);
CREATE INDEX idx_passagem_id_viagem  ON silver_passagem(id_viagem);
CREATE INDEX idx_trecho_id_viagem    ON silver_trecho(id_viagem);
