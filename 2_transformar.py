"""
Fase 2 do pipeline (camada Silver).

Le os dados da camada Raw (texto puro), converte os tipos (texto -> DECIMAL,
texto -> DATE), calcula as colunas derivadas e carrega na camada Silver,
respeitando a ordem de integridade referencial: Viagem primeiro (tabela
pai), depois Pagamento / Passagem / Trecho (tabelas filhas).

Regras de negocio assumidas para as colunas calculadas:
- valor_total    = valor_diarias + valor_passagens + valor_outros_gastos
                    - valor_devolucao
- duracao_dias   = (data_fim - data_inicio) + 1 dia, contando o dia de ida
                    e o dia de volta como parte da viagem
"""

from datetime import datetime
from decimal import Decimal, InvalidOperation

from config import TAMANHO_BLOCO
from banco import conectar, executar, inserir_em_lote


# ---------------------------------------------------------------------------
# Funcoes de conversao
# ---------------------------------------------------------------------------
def converter_valor(texto):
    """'1272,97' (texto, virgula decimal) -> Decimal('1272.97'). Vazio -> None."""
    if texto is None or str(texto).strip() == "":
        return None
    try:
        limpo = str(texto).strip().replace(".", "").replace(",", ".")
        return Decimal(limpo)
    except InvalidOperation:
        return None


def converter_data(texto):
    """'17/09/2024' (texto, DD/MM/AAAA) -> date. Vazio/invalido -> None."""
    if texto is None or str(texto).strip() == "":
        return None
    try:
        return datetime.strptime(str(texto).strip(), "%d/%m/%Y").date()
    except ValueError:
        return None


def converter_inteiro(texto):
    """'3' (texto) -> 3 (int). Vazio/invalido -> None."""
    if texto is None or str(texto).strip() == "":
        return None
    try:
        return int(str(texto).strip())
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Leitura em blocos da camada Raw (cursor nomeado = streaming, nao carrega
# a tabela inteira na memoria de uma vez)
# ---------------------------------------------------------------------------
def buscar_em_blocos(conexao_leitura, sql_select):
    cursor = conexao_leitura.cursor(name="cursor_transformacao")
    cursor.itersize = TAMANHO_BLOCO
    cursor.execute(sql_select)
    while True:
        bloco = cursor.fetchmany(TAMANHO_BLOCO)
        if not bloco:
            break
        yield bloco
    cursor.close()


# ---------------------------------------------------------------------------
# Viagem (tabela pai)
# ---------------------------------------------------------------------------
def transformar_viagem(conexao_leitura, conexao_escrita):
    sql_select = """
        SELECT id_viagem, num_proposta, situacao, viagem_urgente,
               cod_orgao_superior, nome_orgao_superior, nome_viajante, cargo,
               data_inicio, data_fim, destinos, motivo,
               valor_diarias, valor_passagens, valor_devolucao, valor_outros_gastos
        FROM raw_viagem
    """
    sql_insert = """
        INSERT INTO silver_viagem (
            id_viagem, num_proposta, situacao, viagem_urgente,
            cod_orgao_superior, nome_orgao_superior, nome_viajante, cargo,
            data_inicio, data_fim, destinos, motivo,
            valor_diarias, valor_passagens, valor_devolucao, valor_outros_gastos,
            valor_total, duracao_dias
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """

    total = 0
    for bloco in buscar_em_blocos(conexao_leitura, sql_select):
        linhas = []
        for row in bloco:
            (id_viagem, num_proposta, situacao, viagem_urgente,
             cod_orgao_superior, nome_orgao_superior, nome_viajante, cargo,
             data_inicio_txt, data_fim_txt, destinos, motivo,
             valor_diarias_txt, valor_passagens_txt,
             valor_devolucao_txt, valor_outros_txt) = row

            data_inicio = converter_data(data_inicio_txt)
            data_fim = converter_data(data_fim_txt)
            valor_diarias = converter_valor(valor_diarias_txt) or Decimal("0")
            valor_passagens = converter_valor(valor_passagens_txt) or Decimal("0")
            valor_devolucao = converter_valor(valor_devolucao_txt) or Decimal("0")
            valor_outros = converter_valor(valor_outros_txt) or Decimal("0")

            valor_total = valor_diarias + valor_passagens + valor_outros - valor_devolucao
            duracao_dias = (
                (data_fim - data_inicio).days + 1
                if data_inicio and data_fim else None
            )

            linhas.append((
                id_viagem, num_proposta, situacao, viagem_urgente,
                cod_orgao_superior, nome_orgao_superior, nome_viajante, cargo,
                data_inicio, data_fim, destinos, motivo,
                valor_diarias, valor_passagens, valor_devolucao, valor_outros,
                valor_total, duracao_dias,
            ))

        inserir_em_lote(conexao_escrita, sql_insert, linhas)
        total += len(linhas)
        print(f"  silver_viagem: +{len(linhas)} linhas (total {total})")
    return total


# ---------------------------------------------------------------------------
# Pagamento
# ---------------------------------------------------------------------------
def transformar_pagamento(conexao_leitura, conexao_escrita):
    sql_select = """
        SELECT id_viagem, num_proposta, nome_orgao_pagador, nome_ug_pagadora,
               tipo_pagamento, valor
        FROM raw_pagamento
    """
    sql_insert = """
        INSERT INTO silver_pagamento (
            id_viagem, num_proposta, nome_orgao_pagador, nome_ug_pagadora,
            tipo_pagamento, valor
        ) VALUES (%s,%s,%s,%s,%s,%s)
    """

    total = 0
    for bloco in buscar_em_blocos(conexao_leitura, sql_select):
        linhas = []
        for (id_viagem, num_proposta, nome_orgao_pagador, nome_ug_pagadora,
             tipo_pagamento, valor_txt) in bloco:
            linhas.append((
                id_viagem, num_proposta, nome_orgao_pagador, nome_ug_pagadora,
                tipo_pagamento, converter_valor(valor_txt),
            ))
        inserir_em_lote(conexao_escrita, sql_insert, linhas)
        total += len(linhas)
        print(f"  silver_pagamento: +{len(linhas)} linhas (total {total})")
    return total


# ---------------------------------------------------------------------------
# Passagem
# ---------------------------------------------------------------------------
def transformar_passagem(conexao_leitura, conexao_escrita):
    sql_select = """
        SELECT id_viagem, meio_transporte, pais_origem_ida, uf_origem_ida,
               cidade_origem_ida, pais_destino_ida, uf_destino_ida,
               cidade_destino_ida, valor_passagem, taxa_servico, data_emissao
        FROM raw_passagem
    """
    sql_insert = """
        INSERT INTO silver_passagem (
            id_viagem, meio_transporte, pais_origem_ida, uf_origem_ida,
            cidade_origem_ida, pais_destino_ida, uf_destino_ida,
            cidade_destino_ida, valor_passagem, taxa_servico, data_emissao
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """

    total = 0
    for bloco in buscar_em_blocos(conexao_leitura, sql_select):
        linhas = []
        for (id_viagem, meio_transporte, pais_origem_ida, uf_origem_ida,
             cidade_origem_ida, pais_destino_ida, uf_destino_ida,
             cidade_destino_ida, valor_passagem_txt, taxa_servico_txt,
             data_emissao_txt) in bloco:
            linhas.append((
                id_viagem, meio_transporte, pais_origem_ida, uf_origem_ida,
                cidade_origem_ida, pais_destino_ida, uf_destino_ida,
                cidade_destino_ida,
                converter_valor(valor_passagem_txt),
                converter_valor(taxa_servico_txt),
                converter_data(data_emissao_txt),
            ))
        inserir_em_lote(conexao_escrita, sql_insert, linhas)
        total += len(linhas)
        print(f"  silver_passagem: +{len(linhas)} linhas (total {total})")
    return total


# ---------------------------------------------------------------------------
# Trecho
# ---------------------------------------------------------------------------
def transformar_trecho(conexao_leitura, conexao_escrita):
    sql_select = """
        SELECT id_viagem, sequencia_trecho, origem_data, origem_uf,
               origem_cidade, destino_data, destino_uf, destino_cidade,
               meio_transporte, numero_diarias
        FROM raw_trecho
    """
    sql_insert = """
        INSERT INTO silver_trecho (
            id_viagem, sequencia_trecho, origem_data, origem_uf,
            origem_cidade, destino_data, destino_uf, destino_cidade,
            meio_transporte, numero_diarias
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """

    total = 0
    for bloco in buscar_em_blocos(conexao_leitura, sql_select):
        linhas = []
        for (id_viagem, sequencia_txt, origem_data_txt, origem_uf,
             origem_cidade, destino_data_txt, destino_uf, destino_cidade,
             meio_transporte, numero_diarias_txt) in bloco:
            linhas.append((
                id_viagem,
                converter_inteiro(sequencia_txt),
                converter_data(origem_data_txt),
                origem_uf, origem_cidade,
                converter_data(destino_data_txt),
                destino_uf, destino_cidade,
                meio_transporte,
                converter_valor(numero_diarias_txt),
            ))
        inserir_em_lote(conexao_escrita, sql_insert, linhas)
        total += len(linhas)
        print(f"  silver_trecho: +{len(linhas)} linhas (total {total})")
    return total


# ---------------------------------------------------------------------------
def main():
    # Duas conexoes separadas: a de leitura mantem o cursor nomeado (server-
    # side) aberto para ler a Raw em blocos; a de escrita faz os commits a
    # cada lote inserido na Silver. Um commit() invalida um cursor nomeado
    # na MESMA conexao, entao elas precisam ser conexoes distintas.
    conexao_leitura = conectar()
    conexao_escrita = conectar()
    try:
        # Idempotente: limpa as 4 tabelas Silver (e reseta os SERIAL) antes
        # de recarregar. CASCADE cobre as FKs de pagamento/passagem/trecho.
        executar(
            conexao_escrita,
            "TRUNCATE TABLE silver_viagem, silver_pagamento, "
            "silver_passagem, silver_trecho RESTART IDENTITY CASCADE",
        )

        print("Transformando viagem -> silver_viagem")
        transformar_viagem(conexao_leitura, conexao_escrita)  # tabela pai / FK primeiro

        print("\nTransformando pagamento -> silver_pagamento")
        transformar_pagamento(conexao_leitura, conexao_escrita)

        print("\nTransformando passagem -> silver_passagem")
        transformar_passagem(conexao_leitura, conexao_escrita)

        print("\nTransformando trecho -> silver_trecho")
        transformar_trecho(conexao_leitura, conexao_escrita)

        print("\nTransformacao concluida com sucesso.")
    except Exception as erro:
        conexao_escrita.rollback()
        print(f"ERRO na transformacao, alteracoes desfeitas: {erro}")
        raise
    finally:
        conexao_leitura.close()
        conexao_escrita.close()


if __name__ == "__main__":
    main()