"""
1_extrair.py
------------
Fase 1 do pipeline (camada Raw).

Baixa o .zip do Google Drive (config.DRIVE_FILE_ID), extrai os 4 CSVs e
carrega o conteudo, SEM QUALQUER TRANSFORMACAO, nas tabelas Raw.

- Idempotente: faz TRUNCATE na tabela antes de recarregar, entao rodar o
  script varias vezes nao duplica registros.
- Resiliente: cada arquivo e carregado dentro de um try/except; um erro em
  um CSV nao derruba o carregamento dos demais.
"""

import sys
import zipfile

import gdown
import pandas as pd

from config import (
    PASTA_DADOS,
    DRIVE_FILE_ID,
    ARQUIVOS,
    TAMANHO_BLOCO,
    CSV_SEPARADOR,
    CSV_ENCODING,
)
from banco import conectar, executar, inserir_em_lote

# ---------------------------------------------------------------------------
# Nome das colunas de cada tabela Raw, na MESMA ordem em que aparecem no CSV
# original e na mesma ordem do CREATE TABLE em 0_criar_banco.sql. Usar a
# ordem posicional (em vez de casar pelo nome do cabecalho) evita problemas
# de acentuacao/encoding no cabecalho do CSV.
# ---------------------------------------------------------------------------
COLUNAS_RAW = {
    "viagem": [
        "id_viagem", "num_proposta", "situacao", "viagem_urgente",
        "justificativa_urgencia", "cod_orgao_superior", "nome_orgao_superior",
        "cod_orgao_solicitante", "nome_orgao_solicitante", "cpf_viajante",
        "nome_viajante", "cargo", "funcao", "descricao_funcao",
        "data_inicio", "data_fim", "destinos", "motivo", "valor_diarias",
        "valor_passagens", "valor_devolucao", "valor_outros_gastos",
    ],
    "pagamento": [
        "id_viagem", "num_proposta", "cod_orgao_superior", "nome_orgao_superior",
        "cod_orgao_pagador", "nome_orgao_pagador", "cod_ug_pagadora",
        "nome_ug_pagadora", "tipo_pagamento", "valor",
    ],
    "passagem": [
        "id_viagem", "num_proposta", "meio_transporte", "pais_origem_ida",
        "uf_origem_ida", "cidade_origem_ida", "pais_destino_ida",
        "uf_destino_ida", "cidade_destino_ida", "pais_origem_volta",
        "uf_origem_volta", "cidade_origem_volta", "pais_destino_volta",
        "uf_destino_volta", "cidade_destino_volta", "valor_passagem",
        "taxa_servico", "data_emissao", "hora_emissao",
    ],
    "trecho": [
        "id_viagem", "num_proposta", "sequencia_trecho", "origem_data",
        "origem_pais", "origem_uf", "origem_cidade", "destino_data",
        "destino_pais", "destino_uf", "destino_cidade", "meio_transporte",
        "numero_diarias", "missao",
    ],
}


def baixar_e_extrair_zip():
    """Baixa o .zip do Google Drive (se ainda nao existir localmente) e extrai os CSVs."""
    PASTA_DADOS.mkdir(exist_ok=True)
    caminho_zip = PASTA_DADOS / "viagens.zip"

    if not caminho_zip.exists():
        print("Baixando .zip do Google Drive...")
        url = f"https://drive.google.com/uc?id={DRIVE_FILE_ID}"
        gdown.download(url, str(caminho_zip), quiet=False)
    else:
        print("Zip ja baixado em data/, pulando download.")

    print("Extraindo CSVs...")
    with zipfile.ZipFile(caminho_zip, "r") as zip_ref:
        zip_ref.extractall(PASTA_DADOS)


def carregar_csv_na_raw(conexao, chave, info):
    """Le um CSV em blocos e insere (sem transformar) na tabela Raw correspondente."""
    caminho_csv = PASTA_DADOS / info["csv"]
    tabela = info["tabela_raw"]
    colunas = COLUNAS_RAW[chave]
    placeholders = ", ".join(["%s"] * len(colunas))
    sql_insert = f"INSERT INTO {tabela} ({', '.join(colunas)}) VALUES ({placeholders})"

    # Idempotente: limpa a tabela antes de recarregar (evita duplicar em reexecucoes)
    executar(conexao, f"TRUNCATE TABLE {tabela}")

    leitor = pd.read_csv(
        caminho_csv,
        sep=CSV_SEPARADOR,
        encoding=CSV_ENCODING,
        header=0,               # pula a linha de cabecalho original do CSV
        names=colunas,           # renomeia posicionalmente para os nomes da Raw
        dtype=str,               # Raw: tudo como texto, sem conversao de tipo
        keep_default_na=False,
        na_values=[""],          # string vazia vira nulo (NULL no banco)
        chunksize=TAMANHO_BLOCO,
    )

    total_linhas = 0
    for bloco in leitor:
        bloco = bloco.where(pd.notnull(bloco), None)
        linhas = list(bloco.itertuples(index=False, name=None))
        inserir_em_lote(conexao, sql_insert, linhas)
        total_linhas += len(linhas)
        print(f"  {tabela}: +{len(linhas)} linhas (total {total_linhas})")

    return total_linhas


def main():
    baixar_e_extrair_zip()

    conexao = conectar()
    try:
        for chave, info in ARQUIVOS.items():
            print(f"\nCarregando {info['csv']} -> {info['tabela_raw']}")
            try:
                total = carregar_csv_na_raw(conexao, chave, info)
                print(f"OK: {total} linhas carregadas em {info['tabela_raw']}")
            except Exception as erro:
                # Resiliente: um erro num arquivo nao interrompe os demais
                print(f"ERRO ao carregar {info['csv']}: {erro}", file=sys.stderr)
                conexao.rollback()
    finally:
        conexao.close()


if __name__ == "__main__":
    main()
