"""
==============================================================================
VitaVoz Clinical OS™ - Database Seeding (demo_seed.py)
Massa de Dados B2B para Demonstração: Nomes Realistas e Variabilidade
==============================================================================
"""

import json
import sqlite3
import random
from contextlib import closing
from src.config.settings import DB_NAME


def initialize_database() -> None:
    with closing(sqlite3.connect(DB_NAME)) as conn:
        with conn:
            c = conn.cursor()

            c.execute("DROP TABLE IF EXISTS care_events")
            c.execute("DROP TABLE IF EXISTS evolucoes")
            c.execute("DROP TABLE IF EXISTS pacientes")
            c.execute("DROP TABLE IF EXISTS protocolos")

            c.execute("""
                CREATE TABLE IF NOT EXISTS protocolos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome_procedimento TEXT NOT NULL,
                    dias_acompanhamento_padrao INTEGER NOT NULL,
                    regras_json TEXT NOT NULL
                )
            """)

            c.execute("""
                CREATE TABLE IF NOT EXISTS pacientes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tenant_id TEXT DEFAULT 'tenant_prime_clinic',
                    nome TEXT NOT NULL,
                    idade INTEGER NOT NULL,
                    procedimento TEXT NOT NULL,
                    data_cirurgia TEXT NOT NULL,
                    data_retorno TEXT NOT NULL,
                    protocolo TEXT NOT NULL,
                    protocol_id INTEGER,
                    alertas_clinicos TEXT,
                    notas_medico TEXT,
                    avatar TEXT,
                    telefone TEXT,
                    FOREIGN KEY (protocol_id) REFERENCES protocolos (id)
                )
            """)

            c.execute("""
                CREATE TABLE IF NOT EXISTS evolucoes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    paciente_id INTEGER NOT NULL,
                    dia INTEGER NOT NULL,
                    dor INTEGER NOT NULL,
                    inchaco TEXT NOT NULL,
                    febre TEXT NOT NULL,
                    tendencia TEXT NOT NULL,
                    relato TEXT NOT NULL,
                    score INTEGER NOT NULL,
                    status_alerta TEXT NOT NULL,
                    data_registro TEXT NOT NULL,
                    motivo TEXT,
                    conduta_medico TEXT,
                    data_conduta TEXT,
                    FOREIGN KEY (paciente_id) REFERENCES pacientes (id)
                )
            """)

            c.execute("""
                CREATE TABLE IF NOT EXISTS care_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    patient_id INTEGER NOT NULL,
                    event_type TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    author TEXT NOT NULL,
                    badge_color TEXT NOT NULL,
                    FOREIGN KEY (patient_id) REFERENCES pacientes (id)
                )
            """)

            regras_implante = json.dumps({
                "limiares_dor": {"1": 7, "2": 5, "3": 3, "4": 2, "7": 1},
                "febre_permitida": False,
                "inchaco_tolerado_ate_dia": 3
            })
            regras_enxerto = json.dumps({
                "limiares_dor": {"1": 8, "2": 6, "3": 5, "4": 4, "7": 2},
                "febre_permitida": False,
                "inchaco_tolerado_ate_dia": 5
            })

            c.execute(
                "INSERT INTO protocolos (nome_procedimento, dias_acompanhamento_padrao, regras_json) VALUES (?, ?, ?)",
                ("Implante Dentário Padrão", 14, regras_implante)
            )
            proto_implante_id = c.lastrowid

            c.execute(
                "INSERT INTO protocolos (nome_procedimento, dias_acompanhamento_padrao, regras_json) VALUES (?, ?, ?)",
                ("Enxerto Ósseo Complexo", 21, regras_enxerto)
            )
            proto_enxerto_id = c.lastrowid

            # PACIENTE PROTAGONISTA: JOÃO SILVA
            c.execute("""
                INSERT INTO pacientes (
                    tenant_id, nome, idade, procedimento, data_cirurgia, data_retorno,
                    protocolo, protocol_id, alertas_clinicos, notas_medico, avatar, telefone
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                "tenant_prime_clinic", "João Silva", 52, "Implante Dentário", "20/07/2026", "05/08/2026",
                "Implante Dentário Padrão", proto_implante_id, "Alergia a Amoxicilina | Ansiedade elevada",
                "Paciente indicado pelo Dr. Carlos. Apresentou histórico de complicação em 2024.",
                "https://cdn-icons-png.flaticon.com/512/3135/3135715.png", "5511999998888"
            ))
            joao_id = c.lastrowid

            c.execute("""
                INSERT INTO evolucoes (paciente_id, dia, dor, inchaco, febre, tendencia, relato, score, status_alerta, data_registro, motivo)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (joao_id, 1, 6, 'Pouco', 'Não', 'Igual', "Dói um pouco, mas suportável.", 90, '🟢 Normal', "21/07/2026", "Recuperação inicial esperada."))

            c.execute("""
                INSERT INTO evolucoes (paciente_id, dia, dor, inchaco, febre, tendencia, relato, score, status_alerta, data_registro, motivo)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (joao_id, 2, 2, 'Não', 'Não', 'Melhorando', "Hoje está bem melhor doutor, quase sem dor.", 95, '🟢 Normal', "22/07/2026", "Evolução dentro do esperado."))

            c.execute("""
                INSERT INTO care_events (patient_id, event_type, timestamp, title, description, author, badge_color)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (joao_id, 'SURGERY_COMPLETED', '20/07/2026 09:00', 'Cirurgia de Implante Realizada', 'Procedimento de implante concluído sem intercorrências.', 'Dr. Davi', '#10B981'))


            # MASSA DE PACIENTES COM NOMES REAIS
            nomes_implante = ["Maria Oliveira", "Carlos Eduardo", "Fernanda Costa", "Roberto Alves", "Ana Beatriz", "Rafael Souza", "Patrícia Ribeiro", "Marcelo Pereira", "Camila Santos", "Lucas Almeida"]
            nomes_enxerto = ["Juliana Mendes", "Gustavo Rocha", "Luciana Carvalho", "Thiago Martins", "Amanda Barbosa", "Diego Fernandes", "Beatriz Gomes"]
            nomes_orto = ["Rodrigo Silva", "Mariana Costa", "Bruno Ferreira", "Leticia Souza"]

            pacientes_massa = []

            for i, nome in enumerate(nomes_implante):
                pacientes_massa.append((
                    "tenant_prime_clinic", nome, random.randint(30, 65), "Implante Dentário",
                    "18/07/2026", "02/08/2026", "Implante Dentário Padrão", proto_implante_id,
                    "Sem comorbidades", "Evolução habitual", "https://cdn-icons-png.flaticon.com/512/3135/3135715.png",
                    f"551198888{i:04d}"
                ))

            for i, nome in enumerate(nomes_enxerto):
                pacientes_massa.append((
                    "tenant_prime_clinic", nome, random.randint(40, 70), "Enxerto Ósseo Complexo",
                    "15/07/2026", "30/07/2026", "Enxerto Ósseo Complexo", proto_enxerto_id,
                    "Hipertensão leve" if i % 3 == 0 else "Nenhum", "Acompanhamento regular", "https://cdn-icons-png.flaticon.com/512/3135/3135789.png",
                    f"551197777{i:04d}"
                ))

            for i, nome in enumerate(nomes_orto):
                pacientes_massa.append((
                    "tenant_prime_clinic", nome, random.randint(18, 35), "Cirurgia Ortognática",
                    "12/07/2026", "27/07/2026", "Implante Dentário Padrão", proto_implante_id,
                    "Nenhum", "Pós-op excelente", "https://cdn-icons-png.flaticon.com/512/3135/3135715.png",
                    f"551196666{i:04d}"
                ))

            c.executemany("""
                INSERT INTO pacientes (
                    tenant_id, nome, idade, procedimento, data_cirurgia, data_retorno,
                    protocolo, protocol_id, alertas_clinicos, notas_medico, avatar, telefone
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, pacientes_massa)

            c.execute("SELECT id FROM pacientes WHERE nome != 'João Silva'")
            outros_ids = [r[0] for r in c.fetchall()]

            evolucoes_massa = []

            # Distribuição Controlada de Gravidade
            for index, p_id in enumerate(outros_ids):
                dia_pos_op = random.randint(2, 8)

                if index == 0:
                    score = random.randint(50, 59)
                    status = '🔴 Alerta'
                    motivo = "Relato de dor acima do esperado e febre. Quebra de protocolo."
                    dor = random.randint(5, 8)
                    inchaco = 'Sim'
                    tendencia = 'Piorando'

                elif 1 <= index <= 3:
                    score = random.randint(70, 84)
                    status = '🟡 Atenção'
                    motivo = "Leve inchaço reportado. Requer acompanhamento nas próximas 24h."
                    dor = random.randint(3, 5)
                    inchaco = 'Pouco'
                    tendencia = 'Estável'

                else:
                    score = random.randint(85, 100)
                    status = '🟢 Normal'
                    motivo = "Evolução clínica dentro do esperado para o protocolo."
                    dor = random.randint(0, 2)
                    inchaco = 'Não'
                    tendencia = 'Melhorando'

                evolucoes_massa.append((
                    p_id, dia_pos_op, dor, inchaco, 'Não', tendencia,
                    "Paciente evoluindo conforme a curva esperada." if score >= 85 else "Paciente relatou desconforto fora do padrão.",
                    score, status, "23/07/2026", motivo
                ))

            c.executemany("""
                INSERT INTO evolucoes (paciente_id, dia, dor, inchaco, febre, tendencia, relato, score, status_alerta, data_registro, motivo)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, evolucoes_massa)