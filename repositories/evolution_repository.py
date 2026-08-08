"""Implementação concreta do repositório de evoluções para SQLite/PostgreSQL."""

from contextlib import closing
from typing import List
from src.database.connection import ConnectionFactory
from src.domain.entities.evolution import Evolution


class EvolutionRepository:
    """Repositório de dados da entidade Evolution."""

    def __init__(self, connection_factory: ConnectionFactory) -> None:
        self._connection_factory = connection_factory

    def get_evolutions_by_patient(self, patient_id: int) -> List[Evolution]:
        """Retorna todas as evoluções clínicas cadastradas para um paciente."""
        with closing(self._connection_factory()) as conn:
            c = conn.cursor()
            c.execute(
                "SELECT * FROM evolucoes WHERE paciente_id=? ORDER BY dia DESC, id DESC",
                (patient_id,),
            )
            rows = c.fetchall()
            return [Evolution(**dict(row)) for row in rows]

    def has_evolution_for_day(self, patient_id: int, dia: int) -> bool:
        """Verifica se já existe um relato cadastrado para o dia informado."""
        with closing(self._connection_factory()) as conn:
            c = conn.cursor()
            c.execute(
                "SELECT COUNT(*) as count FROM evolucoes WHERE paciente_id=? AND dia=?",
                (patient_id, dia),
            )
            res = c.fetchone()
            count_val = res["count"] if isinstance(res, dict) or hasattr(res, "keys") else res[0]
            return count_val > 0

    def save_evolution(self, evolution: Evolution) -> None:
        """Insere e persiste uma nova evolução no banco de dados."""
        with closing(self._connection_factory()) as conn:
            with conn:
                c = conn.cursor()
                c.execute(
                    """
                    INSERT INTO evolucoes (
                        paciente_id, dia, dor, inchaco, febre, 
                        tendencia, relato, score, status_alerta, data_registro, motivo,
                        conduta_medico, data_conduta
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        evolution.paciente_id,
                        evolution.dia,
                        evolution.dor,
                        evolution.inchaco,
                        evolution.febre,
                        evolution.tendencia,
                        evolution.relato,
                        evolution.score,
                        evolution.status_alerta,
                        evolution.data_registro,
                        evolution.motivo,
                        evolution.conduta_medico,
                        evolution.data_conduta,
                    ),
                )

    def save_doctor_conduct(
        self, evolution_id: int, conduct_text: str, timestamp: str
    ) -> bool:
        """Atualiza a evolução gravando a conduta do médico e baixando o alerta para '🟢 Atendido'."""
        with closing(self._connection_factory()) as conn:
            with conn:
                c = conn.cursor()
                c.execute(
                    """
                    UPDATE evolucoes 
                    SET conduta_medico = ?, data_conduta = ?, status_alerta = '🟢 Atendido'
                    WHERE id = ?
                """,
                    (conduct_text, timestamp, evolution_id),
                )
                return c.rowcount > 0

    def get_average_pain_by_protocol_and_day(
        self, protocol_id: int, dia: int
    ) -> float:
        """Calcula a média populacional histórica de dor para o mesmo protocolo e dia D+X."""
        with closing(self._connection_factory()) as conn:
            c = conn.cursor()
            c.execute(
                """
                SELECT AVG(e.dor) as media_dor
                FROM evolucoes e
                JOIN pacientes p ON e.paciente_id = p.id
                WHERE p.protocol_id = ? AND e.dia = ?
            """,
                (protocol_id, dia),
            )
            res = c.fetchone()
            val = res["media_dor"] if isinstance(res, dict) or hasattr(res, "keys") else (res[0] if res else None)
            if val is not None:
                return round(float(val), 1)
            return 2.5
