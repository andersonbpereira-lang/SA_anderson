"""Sistema de Hospital - Cadastro de pacientes e triagem de gravidade
Aluno: Anderson Becker Pereira
Curso: Técnico em Desenvolvimento de Sistemas (turma M1)
Unidade curricular: Programação de Aplicativos - SA nº 1 (Bloco 2 - Entrega 1)

O que o programa faz:
  1. Cadastra pacientes (nome, nascimento, sexo, peso, altura, tipo sanguíneo,
     alergias) e calcula o IMC automaticamente.
  2. Registra atendimentos (queixa, tipo de ferimento, sinais vitais, dor).
  3. Calcula a GRAVIDADE do paciente (classificação por cores, inspirada no
     Protocolo de Manchester) e monta a fila de atendimento por prioridade.
  4. Guarda tudo em um banco de dados SQLite.

Como executar:
  python app.py            -> abre o menu
  python app.py --testes   -> roda os testes automáticos

Use somente dados fictícios (nada de dados pessoais reais).
"""

import sqlite3
import sys
from flask import Flask, jsonify, request, send_from_directory
from datetime import datetime
from pathlib import Path

# O banco fica na pasta banco_de_dados/ do repositório
CAMINHO_BANCO = Path(__file__).resolve().parent.parent / "banco_de_dados" / "hospital.db"

# ----------------------------------------------------------------------------
# Constantes do sistema de gravidade
# ----------------------------------------------------------------------------

# Pontos de gravidade de cada tipo de ferimento
TIPOS_FERIMENTO = {
    "nenhum": 0,
    "arranhao": 0,
    "corte superficial": 1,
    "contusao": 1,
    "entorse": 2,
    "queimadura leve": 2,
    "fratura": 3,
    "corte profundo": 3,
    "queimadura grave": 4,
    "trauma craniano": 4,
    "hemorragia intensa": 5,
    "ferimento por arma": 5,
}

# nível -> (prioridade, cor, tempo máximo de espera em minutos)
NIVEIS = {
    "emergencia": (1, "VERMELHO", 0),
    "muito urgente": (2, "LARANJA", 10),
    "urgente": (3, "AMARELO", 60),
    "pouco urgente": (4, "VERDE", 120),
    "nao urgente": (5, "AZUL", 240),
}

STATUS_VALIDOS = ("aguardando", "em atendimento", "finalizado")
TIPOS_SANGUINEOS = ("A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-", "NAO SEI")


# ----------------------------------------------------------------------------
# Banco de dados
# ----------------------------------------------------------------------------

def conectar(caminho=CAMINHO_BANCO):
    """Abre a conexão com o banco SQLite (cria a pasta/arquivo se precisar)."""
    if str(caminho) != ":memory:":
        Path(caminho).parent.mkdir(parents=True, exist_ok=True)
    conexao = sqlite3.connect(str(caminho))
    conexao.row_factory = sqlite3.Row
    conexao.execute("PRAGMA foreign_keys = ON")
    return conexao


def criar_tabelas(conexao):
    """Cria as tabelas do sistema, caso ainda não existam."""
    conexao.executescript(
        """
        CREATE TABLE IF NOT EXISTS pacientes (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            nome            TEXT    NOT NULL,
            data_nascimento TEXT    NOT NULL,
            sexo            TEXT    NOT NULL CHECK (sexo IN ('M', 'F')),
            peso_kg         REAL    NOT NULL CHECK (peso_kg > 0),
            altura_m        REAL    NOT NULL CHECK (altura_m > 0),
            imc             REAL    NOT NULL,
            tipo_sanguineo  TEXT    NOT NULL,
            alergias        TEXT    NOT NULL DEFAULT 'nenhuma',
            telefone        TEXT,
            criado_em       TEXT    NOT NULL
        );

        CREATE TABLE IF NOT EXISTS atendimentos (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            paciente_id      INTEGER NOT NULL,
            queixa           TEXT    NOT NULL,
            tipo_ferimento   TEXT    NOT NULL,
            nivel_dor        INTEGER NOT NULL CHECK (nivel_dor BETWEEN 0 AND 10),
            saturacao        INTEGER NOT NULL CHECK (saturacao BETWEEN 0 AND 100),
            freq_cardiaca    INTEGER NOT NULL CHECK (freq_cardiaca > 0),
            temperatura      REAL    NOT NULL,
            pressao_sistolica  INTEGER NOT NULL,
            pressao_diastolica INTEGER NOT NULL,
            consciente       INTEGER NOT NULL CHECK (consciente IN (0, 1)),
            pontos           INTEGER NOT NULL,
            nivel_gravidade  TEXT    NOT NULL,
            cor              TEXT    NOT NULL,
            prioridade       INTEGER NOT NULL,
            status           TEXT    NOT NULL DEFAULT 'aguardando',
            data_hora        TEXT    NOT NULL,
            FOREIGN KEY (paciente_id) REFERENCES pacientes (id) ON DELETE CASCADE
        );
        """
    )
    conexao.commit()


# ----------------------------------------------------------------------------
# Regras de negócio (cálculos)
# ----------------------------------------------------------------------------

def calcular_imc(peso_kg, altura_m):
    """IMC = peso / altura². Retorna o valor com 1 casa decimal."""
    if peso_kg <= 0 or altura_m <= 0:
        raise ValueError("Peso e altura devem ser maiores que zero.")
    return round(peso_kg / (altura_m ** 2), 1)


def classificar_imc(imc):
    """Classificação do IMC segundo a OMS (adultos)."""
    if imc < 18.5:
        return "Abaixo do peso"
    if imc < 25:
        return "Peso normal"
    if imc < 30:
        return "Sobrepeso"
    if imc < 35:
        return "Obesidade grau I"
    if imc < 40:
        return "Obesidade grau II"
    return "Obesidade grau III"


def calcular_idade(data_nascimento):
    """Recebe 'AAAA-MM-DD' e devolve a idade em anos."""
    nasc = datetime.strptime(data_nascimento, "%Y-%m-%d")
    hoje = datetime.now()
    idade = hoje.year - nasc.year
    if (hoje.month, hoje.day) < (nasc.month, nasc.day):
        idade -= 1
    return idade


def calcular_gravidade(tipo_ferimento, nivel_dor, saturacao, freq_cardiaca,
                       temperatura, pressao_sistolica, consciente):
    """
    Calcula a gravidade somando pontos de risco.
    Retorna (nivel, pontos, motivos).

    Pontuação final -> nível:
      >= 10 emergência (vermelho) | 7-9 muito urgente (laranja)
      4-6 urgente (amarelo)       | 2-3 pouco urgente (verde) | 0-1 não urgente (azul)
    """
    if tipo_ferimento not in TIPOS_FERIMENTO:
        raise ValueError(f"Tipo de ferimento inválido: {tipo_ferimento}")

    pontos = 0
    motivos = []

    def somar(valor, texto):
        nonlocal pontos
        if valor:
            pontos += valor
            motivos.append(f"{texto} (+{valor})")

    # 1) Ferimento
    somar(TIPOS_FERIMENTO[tipo_ferimento], f"ferimento: {tipo_ferimento}")

    # 2) Consciência
    if not consciente:
        somar(6, "paciente inconsciente")

    # 3) Saturação de oxigênio
    if saturacao < 90:
        somar(5, f"saturação muito baixa ({saturacao}%)")
    elif saturacao < 94:
        somar(3, f"saturação baixa ({saturacao}%)")

    # 4) Frequência cardíaca
    if freq_cardiaca > 130 or freq_cardiaca < 40:
        somar(4, f"freq. cardíaca crítica ({freq_cardiaca} bpm)")
    elif freq_cardiaca > 110 or freq_cardiaca < 50:
        somar(2, f"freq. cardíaca alterada ({freq_cardiaca} bpm)")

    # 5) Temperatura
    if temperatura >= 39.5 or temperatura < 35:
        somar(3, f"temperatura crítica ({temperatura} °C)")
    elif temperatura >= 38:
        somar(1, f"febre ({temperatura} °C)")

    # 6) Pressão sistólica
    if pressao_sistolica < 90:
        somar(4, f"pressão muito baixa ({pressao_sistolica} mmHg)")
    elif pressao_sistolica >= 180:
        somar(3, f"pressão muito alta ({pressao_sistolica} mmHg)")

    # 7) Dor
    if nivel_dor >= 8:
        somar(3, f"dor intensa ({nivel_dor}/10)")
    elif nivel_dor >= 5:
        somar(2, f"dor moderada ({nivel_dor}/10)")
    elif nivel_dor >= 3:
        somar(1, f"dor leve ({nivel_dor}/10)")

    if pontos >= 10:
        nivel = "emergencia"
    elif pontos >= 7:
        nivel = "muito urgente"
    elif pontos >= 4:
        nivel = "urgente"
    elif pontos >= 2:
        nivel = "pouco urgente"
    else:
        nivel = "nao urgente"

    return nivel, pontos, motivos


# ----------------------------------------------------------------------------
# Operações no banco (CRUD)
# ----------------------------------------------------------------------------

def agora():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def cadastrar_paciente(conexao, nome, data_nascimento, sexo, peso_kg, altura_m,
                       tipo_sanguineo, alergias="nenhuma", telefone=None):
    """Valida os dados e insere um paciente. Retorna o id criado."""
    nome = nome.strip()
    if len(nome) < 3:
        raise ValueError("Nome deve ter pelo menos 3 caracteres.")
    try:
        nasc = datetime.strptime(data_nascimento, "%Y-%m-%d")
    except ValueError:
        raise ValueError("Data de nascimento inválida (use AAAA-MM-DD).")
    if nasc > datetime.now():
        raise ValueError("Data de nascimento não pode estar no futuro.")
    sexo = sexo.strip().upper()
    if sexo not in ("M", "F"):
        raise ValueError("Sexo deve ser M ou F.")
    if not 0.5 <= peso_kg <= 400:
        raise ValueError("Peso deve estar entre 0,5 e 400 kg.")
    if not 0.3 <= altura_m <= 2.6:
        raise ValueError("Altura deve estar entre 0,30 e 2,60 m.")
    tipo_sanguineo = tipo_sanguineo.strip().upper()
    if tipo_sanguineo not in TIPOS_SANGUINEOS:
        raise ValueError("Tipo sanguíneo inválido.")

    cursor = conexao.execute(
        """INSERT INTO pacientes (nome, data_nascimento, sexo, peso_kg, altura_m,
                                  imc, tipo_sanguineo, alergias, telefone, criado_em)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (nome, data_nascimento, sexo, peso_kg, altura_m,
         calcular_imc(peso_kg, altura_m), tipo_sanguineo,
         alergias.strip() or "nenhuma", telefone, agora()),
    )
    conexao.commit()
    return cursor.lastrowid


def buscar_paciente(conexao, termo):
    """Busca por id (número) ou por parte do nome."""
    if str(termo).isdigit():
        return conexao.execute("SELECT * FROM pacientes WHERE id = ?", (int(termo),)).fetchall()
    return conexao.execute(
        "SELECT * FROM pacientes WHERE nome LIKE ? ORDER BY nome", (f"%{termo}%",)
    ).fetchall()


def atualizar_peso_altura(conexao, paciente_id, peso_kg, altura_m):
    """Atualiza peso e altura e recalcula o IMC."""
    if not 0.5 <= peso_kg <= 400 or not 0.3 <= altura_m <= 2.6:
        raise ValueError("Peso ou altura fora do intervalo aceito.")
    cursor = conexao.execute(
        "UPDATE pacientes SET peso_kg = ?, altura_m = ?, imc = ? WHERE id = ?",
        (peso_kg, altura_m, calcular_imc(peso_kg, altura_m), paciente_id),
    )
    conexao.commit()
    if cursor.rowcount == 0:
        raise LookupError("Paciente não encontrado.")


def excluir_paciente(conexao, paciente_id):
    """Exclui o paciente e (em cascata) todos os atendimentos dele."""
    cursor = conexao.execute("DELETE FROM pacientes WHERE id = ?", (paciente_id,))
    conexao.commit()
    if cursor.rowcount == 0:
        raise LookupError("Paciente não encontrado.")


def registrar_atendimento(conexao, paciente_id, queixa, tipo_ferimento, nivel_dor,
                          saturacao, freq_cardiaca, temperatura,
                          pressao_sistolica, pressao_diastolica, consciente):
    """Calcula a gravidade e grava o atendimento. Retorna (id, nivel, pontos, motivos)."""
    if not buscar_paciente(conexao, paciente_id):
        raise LookupError("Paciente não encontrado.")
    if not queixa.strip():
        raise ValueError("Informe a queixa principal.")
    if not 0 <= nivel_dor <= 10:
        raise ValueError("Nível de dor deve ser de 0 a 10.")
    if not 0 <= saturacao <= 100:
        raise ValueError("Saturação deve ser de 0 a 100.")
    if not 20 <= freq_cardiaca <= 300:
        raise ValueError("Frequência cardíaca fora do intervalo (20 a 300).")
    if not 30 <= temperatura <= 45:
        raise ValueError("Temperatura fora do intervalo (30 a 45 °C).")
    if not 30 <= pressao_sistolica <= 300 or not 20 <= pressao_diastolica <= 200:
        raise ValueError("Pressão arterial fora do intervalo.")

    nivel, pontos, motivos = calcular_gravidade(
        tipo_ferimento, nivel_dor, saturacao, freq_cardiaca,
        temperatura, pressao_sistolica, consciente)
    prioridade, cor, _ = NIVEIS[nivel]

    cursor = conexao.execute(
        """INSERT INTO atendimentos
           (paciente_id, queixa, tipo_ferimento, nivel_dor, saturacao, freq_cardiaca,
            temperatura, pressao_sistolica, pressao_diastolica, consciente, pontos,
            nivel_gravidade, cor, prioridade, status, data_hora)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'aguardando', ?)""",
        (paciente_id, queixa.strip(), tipo_ferimento, nivel_dor, saturacao,
         freq_cardiaca, temperatura, pressao_sistolica, pressao_diastolica,
         1 if consciente else 0, pontos, nivel, cor, prioridade, agora()),
    )
    conexao.commit()
    return cursor.lastrowid, nivel, pontos, motivos


def listar_fila(conexao):
    """Fila de espera: mais grave primeiro; empate = quem chegou antes."""
    return conexao.execute(
        """SELECT a.*, p.nome, p.data_nascimento
           FROM atendimentos a JOIN pacientes p ON p.id = a.paciente_id
           WHERE a.status = 'aguardando'
           ORDER BY a.prioridade ASC, a.data_hora ASC, a.id ASC"""
    ).fetchall()


def historico_paciente(conexao, paciente_id):
    return conexao.execute(
        "SELECT * FROM atendimentos WHERE paciente_id = ? ORDER BY data_hora DESC",
        (paciente_id,),
    ).fetchall()


def atualizar_status(conexao, atendimento_id, novo_status):
    if novo_status not in STATUS_VALIDOS:
        raise ValueError(f"Status inválido. Use: {', '.join(STATUS_VALIDOS)}")
    cursor = conexao.execute(
        "UPDATE atendimentos SET status = ? WHERE id = ?", (novo_status, atendimento_id)
    )
    conexao.commit()
    if cursor.rowcount == 0:
        raise LookupError("Atendimento não encontrado.")


# ----------------------------------------------------------------------------
# Entrada de dados com validação (interface de terminal)
# ----------------------------------------------------------------------------

def ler_texto(mensagem, obrigatorio=True):
    while True:
        valor = input(mensagem).strip()
        if valor or not obrigatorio:
            return valor
        print("  ! Campo obrigatório.")


def ler_numero(mensagem, tipo=float, minimo=None, maximo=None):
    """Lê um número, repetindo até o usuário digitar um valor válido."""
    while True:
        bruto = input(mensagem).strip().replace(",", ".")
        try:
            valor = tipo(bruto)
        except ValueError:
            print("  ! Digite um número válido.")
            continue
        if (minimo is not None and valor < minimo) or (maximo is not None and valor > maximo):
            print(f"  ! Valor deve estar entre {minimo} e {maximo}.")
            continue
        return valor


def ler_data(mensagem):
    """Lê DD/MM/AAAA e devolve AAAA-MM-DD."""
    while True:
        bruto = input(mensagem).strip()
        try:
            return datetime.strptime(bruto, "%d/%m/%Y").strftime("%Y-%m-%d")
        except ValueError:
            print("  ! Data inválida. Use DD/MM/AAAA.")


def ler_sim_nao(mensagem):
    while True:
        resposta = input(mensagem + " (s/n): ").strip().lower()
        if resposta in ("s", "n"):
            return resposta == "s"
        print("  ! Responda s ou n.")


def escolher_da_lista(titulo, opcoes):
    print(titulo)
    for i, opcao in enumerate(opcoes, 1):
        print(f"  {i}) {opcao}")
    indice = ler_numero("Escolha: ", int, 1, len(opcoes))
    return opcoes[indice - 1]


# ----------------------------------------------------------------------------
# Telas do menu
# ----------------------------------------------------------------------------

def tela_cadastrar_paciente(conexao):
    print("\n--- Cadastro de paciente ---")
    nome = ler_texto("Nome: ")
    nascimento = ler_data("Data de nascimento (DD/MM/AAAA): ")
    sexo = escolher_da_lista("Sexo:", ["M", "F"])
    peso = ler_numero("Peso (kg): ", float, 0.5, 400)
    altura = ler_numero("Altura (m, ex.: 1,75): ", float, 0.3, 2.6)
    sangue = escolher_da_lista("Tipo sanguíneo:", list(TIPOS_SANGUINEOS))
    alergias = ler_texto("Alergias (Enter = nenhuma): ", obrigatorio=False) or "nenhuma"
    telefone = ler_texto("Telefone (opcional): ", obrigatorio=False) or None
    try:
        novo_id = cadastrar_paciente(conexao, nome, nascimento, sexo, peso, altura,
                                     sangue, alergias, telefone)
    except ValueError as erro:
        print(f"  ! Não foi possível cadastrar: {erro}")
        return
    imc = calcular_imc(peso, altura)
    print(f"\nPaciente cadastrado com ID {novo_id}.")
    print(f"IMC: {imc} ({classificar_imc(imc)})")


def mostrar_paciente(p):
    imc = p["imc"]
    print(f"[{p['id']}] {p['nome']} | {calcular_idade(p['data_nascimento'])} anos | "
          f"sexo {p['sexo']} | {p['peso_kg']} kg | {p['altura_m']} m | "
          f"IMC {imc} ({classificar_imc(imc)}) | sangue {p['tipo_sanguineo']} | "
          f"alergias: {p['alergias']}")


def tela_buscar_paciente(conexao):
    termo = ler_texto("\nDigite o ID ou parte do nome: ")
    resultados = buscar_paciente(conexao, termo)
    if not resultados:
        print("Nenhum paciente encontrado.")
    for p in resultados:
        mostrar_paciente(p)


def tela_novo_atendimento(conexao):
    print("\n--- Novo atendimento / triagem ---")
    paciente_id = ler_numero("ID do paciente: ", int, 1)
    if not buscar_paciente(conexao, paciente_id):
        print("  ! Paciente não encontrado. Cadastre-o primeiro.")
        return
    queixa = ler_texto("Queixa principal: ")
    tipo = escolher_da_lista("Tipo de ferimento:", list(TIPOS_FERIMENTO))
    dor = ler_numero("Nível de dor (0 a 10): ", int, 0, 10)
    saturacao = ler_numero("Saturação de O2 (%): ", int, 0, 100)
    fc = ler_numero("Freq. cardíaca (bpm): ", int, 20, 300)
    temp = ler_numero("Temperatura (°C): ", float, 30, 45)
    sist = ler_numero("Pressão sistólica (mmHg): ", int, 30, 300)
    diast = ler_numero("Pressão diastólica (mmHg): ", int, 20, 200)
    consciente = ler_sim_nao("Paciente está consciente?")

    try:
        atendimento_id, nivel, pontos, motivos = registrar_atendimento(
            conexao, paciente_id, queixa, tipo, dor, saturacao, fc, temp,
            sist, diast, consciente)
    except (ValueError, LookupError) as erro:
        print(f"  ! Erro: {erro}")
        return

    prioridade, cor, espera = NIVEIS[nivel]
    print(f"\nAtendimento {atendimento_id} registrado.")
    print(f"GRAVIDADE: {nivel.upper()} - {cor} ({pontos} pontos)")
    print(f"Tempo máximo de espera: {'imediato' if espera == 0 else str(espera) + ' min'}")
    print("Motivos:")
    for motivo in motivos or ["nenhum fator de risco encontrado"]:
        print(f"  - {motivo}")


def tela_fila(conexao):
    fila = listar_fila(conexao)
    print("\n--- Fila de atendimento (mais grave primeiro) ---")
    if not fila:
        print("Ninguém aguardando.")
        return
    for posicao, a in enumerate(fila, 1):
        print(f"{posicao}º | atend. {a['id']} | {a['cor']:<8} | {a['nome']} | "
              f"{a['tipo_ferimento']} | dor {a['nivel_dor']}/10 | {a['pontos']} pts | "
              f"chegada {a['data_hora']}")


def tela_atualizar_status(conexao):
    atendimento_id = ler_numero("\nID do atendimento: ", int, 1)
    status = escolher_da_lista("Novo status:", list(STATUS_VALIDOS))
    try:
        atualizar_status(conexao, atendimento_id, status)
        print("Status atualizado.")
    except (ValueError, LookupError) as erro:
        print(f"  ! {erro}")


def tela_atualizar_peso_altura(conexao):
    paciente_id = ler_numero("\nID do paciente: ", int, 1)
    peso = ler_numero("Novo peso (kg): ", float, 0.5, 400)
    altura = ler_numero("Nova altura (m): ", float, 0.3, 2.6)
    try:
        atualizar_peso_altura(conexao, paciente_id, peso, altura)
        imc = calcular_imc(peso, altura)
        print(f"Atualizado. Novo IMC: {imc} ({classificar_imc(imc)})")
    except (ValueError, LookupError) as erro:
        print(f"  ! {erro}")


def tela_historico(conexao):
    paciente_id = ler_numero("\nID do paciente: ", int, 1)
    historico = historico_paciente(conexao, paciente_id)
    if not historico:
        print("Sem atendimentos para este paciente.")
    for a in historico:
        print(f"atend. {a['id']} | {a['data_hora']} | {a['cor']} | {a['queixa']} | "
              f"{a['tipo_ferimento']} | status: {a['status']}")


def tela_excluir_paciente(conexao):
    paciente_id = ler_numero("\nID do paciente a excluir: ", int, 1)
    if not ler_sim_nao("Isso apaga também os atendimentos dele. Confirmar?"):
        print("Cancelado.")
        return
    try:
        excluir_paciente(conexao, paciente_id)
        print("Paciente excluído.")
    except LookupError as erro:
        print(f"  ! {erro}")


def menu():
    conexao = conectar()
    criar_tabelas(conexao)
    acoes = {
        "1": tela_cadastrar_paciente,
        "2": tela_buscar_paciente,
        "3": tela_novo_atendimento,
        "4": tela_fila,
        "5": tela_atualizar_status,
        "6": tela_atualizar_peso_altura,
        "7": tela_historico,
        "8": tela_excluir_paciente,
    }
    while True:
        print("\n=========== HOSPITAL - SISTEMA DE TRIAGEM ===========")
        print("1) Cadastrar paciente")
        print("2) Buscar paciente")
        print("3) Novo atendimento (triagem de gravidade)")
        print("4) Ver fila de atendimento")
        print("5) Atualizar status do atendimento")
        print("6) Atualizar peso e altura")
        print("7) Histórico do paciente")
        print("8) Excluir paciente")
        print("0) Sair")
        escolha = input("Opção: ").strip()
        if escolha == "0":
            print("Encerrando. Até logo!")
            break
        acao = acoes.get(escolha)
        if acao:
            acao(conexao)
        else:
            print("  ! Opção inválida.")
    conexao.close()


# ----------------------------------------------------------------------------
# Testes automáticos (python app.py --testes)
# ----------------------------------------------------------------------------

def executar_testes():
    print("Executando testes...")

    # IMC
    assert calcular_imc(70, 1.75) == 22.9
    assert classificar_imc(22.9) == "Peso normal"
    assert classificar_imc(31) == "Obesidade grau I"
    try:
        calcular_imc(0, 1.7)
        assert False, "deveria falhar com peso 0"
    except ValueError:
        pass

    # Gravidade
    nivel, pontos, _ = calcular_gravidade("arranhao", 1, 98, 80, 36.5, 120, True)
    assert nivel == "nao urgente" and pontos == 0
    nivel, _, _ = calcular_gravidade("fratura", 6, 97, 95, 36.8, 125, True)
    assert nivel == "urgente"
    nivel, _, _ = calcular_gravidade("hemorragia intensa", 9, 88, 135, 36, 80, False)
    assert nivel == "emergencia"
    try:
        calcular_gravidade("ferimento inventado", 1, 98, 80, 36.5, 120, True)
        assert False, "deveria falhar com ferimento inválido"
    except ValueError:
        pass

    # Banco em memória
    con = conectar(":memory:")
    criar_tabelas(con)
    pid = cadastrar_paciente(con, "Maria Teste", "1990-05-10", "F", 62.5, 1.65, "O+")
    assert buscar_paciente(con, pid)[0]["imc"] == 23.0
    for dados_invalidos in (
        ("Jo", "1990-05-10", "F", 60, 1.6, "O+"),          # nome curto
        ("Maria Teste", "10/05/1990", "F", 60, 1.6, "O+"),  # data no formato errado
        ("Maria Teste", "1990-05-10", "X", 60, 1.6, "O+"),  # sexo inválido
        ("Maria Teste", "1990-05-10", "F", -5, 1.6, "O+"),  # peso negativo
        ("Maria Teste", "1990-05-10", "F", 60, 5.0, "O+"),  # altura absurda
        ("Maria Teste", "1990-05-10", "F", 60, 1.6, "Z+"),  # sangue inválido
    ):
        try:
            cadastrar_paciente(con, *dados_invalidos)
            assert False, f"deveria rejeitar {dados_invalidos}"
        except ValueError:
            pass

    # Fila: o mais grave deve vir primeiro, mesmo chegando depois
    p2 = cadastrar_paciente(con, "Carlos Teste", "1985-01-20", "M", 90, 1.80, "A+")
    registrar_atendimento(con, pid, "arranhão no braço", "arranhao", 1, 98, 80, 36.5, 120, 80, True)
    registrar_atendimento(con, p2, "acidente de moto", "hemorragia intensa", 9, 88, 135, 36, 80, 50, False)
    fila = listar_fila(con)
    assert fila[0]["nome"] == "Carlos Teste" and fila[0]["cor"] == "VERMELHO"
    assert fila[1]["nome"] == "Maria Teste"

    # Status e exclusão em cascata
    atualizar_status(con, fila[0]["id"], "finalizado")
    assert len(listar_fila(con)) == 1
    try:
        atualizar_status(con, fila[0]["id"], "status errado")
        assert False
    except ValueError:
        pass
    excluir_paciente(con, p2)
    assert historico_paciente(con, p2) == []
    con.close()

    print("Todos os testes passaram.")




# ----------------------------------------------------------------------------
# API WEB - a interface utiliza o mesmo SQLite do programa de terminal.
# O login é apenas demonstrativo; esta aplicação não possui autenticação real.
# ----------------------------------------------------------------------------

app = Flask(__name__, static_folder=None)
PASTA_INTERFACE = Path(__file__).resolve().parent.parent / "interface"


def resposta_erro(mensagem, status=400):
    return jsonify({"erro": mensagem}), status


def paciente_para_json(paciente):
    return {
        "id": paciente["id"],
        "name": paciente["nome"],
        "age": calcular_idade(paciente["data_nascimento"]),
        "weight": paciente["peso_kg"],
        "height": paciente["altura_m"],
        "bmi": paciente["imc"],
        "blood": paciente["tipo_sanguineo"],
        "allergies": paciente["alergias"],
        "createdAt": paciente["criado_em"],
    }


def atendimento_para_json(atendimento):
    return {
        "id": atendimento["id"],
        "patientId": atendimento["paciente_id"],
        "complaint": atendimento["queixa"],
        "injury": atendimento["tipo_ferimento"],
        "pain": atendimento["nivel_dor"],
        "oxygen": atendimento["saturacao"],
        "heartRate": atendimento["freq_cardiaca"],
        "temperature": atendimento["temperatura"],
        "systolic": atendimento["pressao_sistolica"],
        "diastolic": atendimento["pressao_diastolica"],
        "conscious": bool(atendimento["consciente"]),
        "priority": {
            "VERMELHO": "red", "LARANJA": "orange", "AMARELO": "yellow",
            "VERDE": "green", "AZUL": "blue"
        }.get(atendimento["cor"], "blue"),
        "priorityLabel": atendimento["cor"],
        "points": atendimento["pontos"],
        "level": atendimento["nivel_gravidade"],
        "status": {
            "aguardando": "waiting",
            "em atendimento": "active",
            "finalizado": "finished"
        }.get(atendimento["status"], "waiting"),
        "createdAt": atendimento["data_hora"],
    }


@app.route("/")
def pagina_inicial():
    return send_from_directory(PASTA_INTERFACE, "index.html")


@app.route("/<path:arquivo>")
def arquivos_interface(arquivo):
    return send_from_directory(PASTA_INTERFACE, arquivo)


@app.get("/api/dados")
def api_listar_dados():
    conexao = conectar()
    try:
        criar_tabelas(conexao)
        pacientes = conexao.execute(
            "SELECT * FROM pacientes ORDER BY id DESC"
        ).fetchall()
        atendimentos = conexao.execute(
            "SELECT * FROM atendimentos ORDER BY data_hora DESC, id DESC"
        ).fetchall()
        return jsonify({
            "patients": [paciente_para_json(p) for p in pacientes],
            "appointments": [atendimento_para_json(a) for a in atendimentos],
        })
    finally:
        conexao.close()


@app.post("/api/login")
def api_login():
    dados = request.get_json(silent=True) or {}
    valido = (
        dados.get("username") == "admin"
        and dados.get("password") == "hospital123"
    )
    if not valido:
        return resposta_erro("Usuário ou senha incorretos.", 401)
    return jsonify({
        "ok": True,
        "aviso": "Acesso demonstrativo. Não é autenticação segura."
    })


@app.post("/api/pacientes")
def api_cadastrar_paciente():
    dados = request.get_json(silent=True) or {}
    try:
        nome = str(dados.get("name", "")).strip()
        idade = int(dados.get("age"))
        peso = float(dados.get("weight"))
        altura = float(dados.get("height"))
        sexo = str(dados.get("sex", "M")).upper()
        sangue = str(dados.get("blood", "NAO SEI")).upper()
        if sangue == "NÃO INFORMADO":
            sangue = "NAO SEI"
        if not 0 <= idade <= 120:
            raise ValueError("Idade deve estar entre 0 e 120 anos.")
        hoje = datetime.now().date()
        ano = hoje.year - idade
        try:
            nascimento = hoje.replace(year=ano)
        except ValueError:
            nascimento = hoje.replace(year=ano, day=28)
        paciente_id = cadastrar_paciente(
            conectar(), nome, nascimento.isoformat(), sexo, peso, altura,
            sangue, str(dados.get("allergies", "nenhuma"))
        )
        return jsonify({"id": paciente_id, "mensagem": "Paciente cadastrado."}), 201
    except (TypeError, ValueError) as erro:
        return resposta_erro(str(erro))
    except sqlite3.Error:
        return resposta_erro("Não foi possível salvar o paciente.", 500)


@app.delete("/api/pacientes/<int:paciente_id>")
def api_excluir_paciente(paciente_id):
    conexao = conectar()
    try:
        em_andamento = conexao.execute(
            """SELECT COUNT(*) FROM atendimentos
               WHERE paciente_id = ? AND status IN ('aguardando', 'em atendimento')""",
            (paciente_id,)
        ).fetchone()[0]
        if em_andamento:
            return resposta_erro(
                "Finalize os atendimentos antes de excluir o paciente."
            )
        excluir_paciente(conexao, paciente_id)
        return jsonify({"ok": True})
    except LookupError as erro:
        return resposta_erro(str(erro), 404)
    finally:
        conexao.close()


@app.post("/api/atendimentos")
def api_registrar_atendimento():
    dados = request.get_json(silent=True) or {}
    conexao = conectar()
    try:
        paciente_id = int(dados.get("patientId"))
        mapa_ferimentos = {
            "Corte": "corte superficial",
            "Contusão": "contusao",
            "Queda": "entorse",
            "Queimadura": "queimadura leve",
            "Fratura suspeita": "fratura",
            "Outro": "nenhum",
            "Não informado": "nenhum",
        }
        ferimento = mapa_ferimentos.get(
            str(dados.get("injury", "Não informado")), "nenhum"
        )
        atendimento_id, nivel, pontos, motivos = registrar_atendimento(
            conexao,
            paciente_id,
            str(dados.get("complaint", "")),
            ferimento,
            int(dados.get("pain", 0)),
            int(dados.get("oxygen", 98)),
            int(dados.get("heartRate", 80)),
            float(dados.get("temperature", 36.5)),
            int(dados.get("systolic", 120)),
            int(dados.get("diastolic", 80)),
            bool(dados.get("conscious", True)),
        )
        return jsonify({
            "id": atendimento_id,
            "level": nivel,
            "points": pontos,
            "motivos": motivos,
            "mensagem": "Classificação simulada registrada."
        }), 201
    except (TypeError, ValueError, LookupError) as erro:
        return resposta_erro(str(erro))
    except sqlite3.Error:
        return resposta_erro("Não foi possível registrar o atendimento.", 500)
    finally:
        conexao.close()


@app.patch("/api/atendimentos/<int:atendimento_id>")
def api_atualizar_atendimento(atendimento_id):
    dados = request.get_json(silent=True) or {}
    mapa_status = {
        "waiting": "aguardando",
        "active": "em atendimento",
        "finished": "finalizado",
    }
    status = mapa_status.get(dados.get("status"))
    if not status:
        return resposta_erro("Status inválido.")
    conexao = conectar()
    try:
        atualizar_status(conexao, atendimento_id, status)
        return jsonify({"ok": True})
    except LookupError as erro:
        return resposta_erro(str(erro), 404)
    except ValueError as erro:
        return resposta_erro(str(erro))
    finally:
        conexao.close()


@app.delete("/api/dados-demo")
def api_limpar_dados_demo():
    """Remove todos os registros fictícios para reiniciar a demonstração."""
    conexao = conectar()
    try:
        conexao.execute("DELETE FROM atendimentos")
        conexao.execute("DELETE FROM pacientes")
        conexao.commit()
        return jsonify({"ok": True, "mensagem": "Dados de demonstração removidos."})
    finally:
        conexao.close()


def executar_web():
    criar_tabelas(conectar())
    app.run(host="127.0.0.1", port=5000, debug=False)



if __name__ == "__main__":
    if "--testes" in sys.argv:
        executar_testes()
    elif "--web" in sys.argv:
        executar_web()
    else:
        menu()
