"""
Implementação do repositório de Pacientes.
Gerencia a persistência, resgate e a fila de triagem da clínica.
"""

from typing import List, Optional
from contextlib import closing
from src.database.connection import ConnectionFactory
from src.domain.dtos.patient_queue_dto import PatientQueueDTO
from src.domain.entities.patient import Patient

class PatientRepository:
    """Repositório de dados e métricas para a entidade Paciente."""

    def __init__(self, connection_factory: ConnectionFactory) -> None:
        self._connection_factory = connection_factory

    def get_joao_id(self) -> int:
        with closing(self._connection_factory()) as conn:
            c = conn.cursor()
            c.execute("SELECT id FROM pacientes WHERE nome LIKE '%João Silva%' LIMIT 1")
            res = c.fetchone()
            if not res:
                return 1
            return res["id"] if isinstance(res, dict) or hasattr(res, "keys") else res[0]

    def get_by_id(self, patient_id: int) -> Patient:
        with closing(self._connection_factory()) as conn:
            c = conn.cursor()
            c.execute(
                """
                SELECT id, tenant_id, nome, idade, procedimento, data_cirurgia, 
                       data_retorno, protocolo, protocol_id, alertas_clinicos, 
                       notas_medico, avatar, telefone 
                FROM pacientes WHERE id = ?
                """,
                (patient_id,)
            )
            row = c.fetchone()
            if not row:
                raise ValueError(f"Paciente com ID {patient_id} não encontrado.")

            return Patient(
                id=row["id"] if hasattr(row, "keys") else row[0],
                tenant_id=row["tenant_id"] if hasattr(row, "keys") else row[1],
                nome=row["nome"] if hasattr(row, "keys") else row[2],
                idade=row["idade"] if hasattr(row, "keys") else row[3],
                procedimento=row["procedimento"] if hasattr(row, "keys") else row[4],
                data_cirurgia=row["data_cirurgia"] if hasattr(row, "keys") else row[5],
                data_retorno=row["data_retorno"] if hasattr(row, "keys") else row[6],
                protocolo=row["protocolo"] if hasattr(row, "keys") else row[7],
                protocol_id=row["protocol_id"] if hasattr(row, "keys") else row[8],
                alertas_clinicos=row["alertas_clinicos"] if hasattr(row, "keys") else row[9],
                notas_medico=row["notas_medico"] if hasattr(row, "keys") else row[10],
                avatar=row["avatar"] if hasattr(row, "keys") else row[11],
                telefone=row["telefone"] if hasattr(row, "keys") else row[12],
            )

    def get_patient_by_id(self, patient_id: int) -> Patient:
        return self.get_by_id(patient_id)

    def get_patient_by_phone(self, phone: str) -> Optional[Patient]:
        with closing(self._connection_factory()) as conn:
            c = conn.cursor()
            c.execute(
                """
                SELECT id, tenant_id, nome, idade, procedimento, data_cirurgia, 
                       data_retorno, protocolo, protocol_id, alertas_clinicos, 
                       notas_medico, avatar, telefone 
                FROM pacientes WHERE telefone = ? LIMIT 1
                """,
                (phone,)
            )
            row = c.fetchone()
            if not row:
                return None
            return Patient(
                id=row["id"] if hasattr(row, "keys") else row[0],
                tenant_id=row["tenant_id"] if hasattr(row, "keys") else row[1],
                nome=row["nome"] if hasattr(row, "keys") else row[2],
                idade=row["idade"] if hasattr(row, "keys") else row[3],
                procedimento=row["procedimento"] if hasattr(row, "keys") else row[4],
                data_cirurgia=row["data_cirurgia"] if hasattr(row, "keys") else row[5],
                data_retorno=row["data_retorno"] if hasattr(row, "keys") else row[6],
                protocolo=row["protocolo"] if hasattr(row, "keys") else row[7],
                protocol_id=row["protocol_id"] if hasattr(row, "keys") else row[8],
                alertas_clinicos=row["alertas_clinicos"] if hasattr(row, "keys") else row[9],
                notas_medico=row["notas_medico"] if hasattr(row, "keys") else row[10],
                avatar=row["avatar"] if hasattr(row, "keys") else row[11],
                telefone=row["telefone"] if hasattr(row, "keys") else row[12],
            )

    def get_fila_completa(self) -> List[PatientQueueDTO]:
        with closing(self._connection_factory()) as conn:
            c = conn.cursor()
            c.execute(
                """
                WITH RankedEvolutions AS (
                    SELECT 
                        p.nome, p.procedimento, p.alertas_clinicos, e.dia, e.score, e.status_alerta, e.motivo,
                        ROW_NUMBER() OVER(PARTITION BY p.id ORDER BY e.dia DESC, e.id DESC) as rn
                    FROM pacientes p
                    LEFT JOIN evolucoes e ON p.id = e.paciente_id
                )
                SELECT nome, procedimento, alertas_clinicos, dia, score, status_alerta, motivo
                FROM RankedEvolutions
                WHERE rn = 1
                ORDER BY 
                    CASE WHEN status_alerta IN ('🟢 Normal', '🟢 Atendido') THEN 1 ELSE 0 END ASC,
                    score ASC
                """
            )
            rows = c.fetchall()

            return [
                PatientQueueDTO(
                    paciente=r["nome"] if hasattr(r, "keys") else r[0],
                    procedimento=r["procedimento"] if hasattr(r, "keys") else r[1],
                    pos_op=f"D+{r['dia']}" if (hasattr(r, "keys") and r["dia"]) or (not hasattr(r, "keys") and r[3]) else "S/D",
                    status=r["status_alerta"] if hasattr(r, "keys") and r["status_alerta"] else "🟢 Normal",
                    score=r["score"] if hasattr(r, "keys") and r["score"] else 100,
                    alertas_clinicos=r["alertas_clinicos"] if hasattr(r, "keys") else r[2],
                    motivo=r["motivo"] if hasattr(r, "keys") else r[6],
                )
                for r in rows
            ]