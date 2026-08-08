"""
Fábrica de Conexões do VitaVoz.
Gerencia a comunicação centralizada com o banco de dados.
"""

import sqlite3
from typing import Callable
from src.config.settings import DB_NAME

# Definição de tipo para injeção de dependência nos repositórios
ConnectionFactory = Callable[[], sqlite3.Connection]

def get_connection() -> sqlite3.Connection:
    """
    Retorna uma conexão ativa com o banco de dados SQLite.
    Configurada para suportar as requisições em tempo real do Streamlit.
    """
    # check_same_thread=False é necessário para o Streamlit não travar com SQLite
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)

    # Permite acessar as colunas pelo nome (ex: row["nome"]) em vez de índice numérico
    conn.row_factory = sqlite3.Row

    return conn