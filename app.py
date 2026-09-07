"""
VitaVoz — Plataforma de Gestão Operacional do Acompanhamento Pós-Procedimento
Versão Piloto Operacional / Multi-Tenant Hardened
"""

import os
import re
import time
import sqlite3
import uuid
import hashlib
import bcrypt
import secrets
import io
import html
from datetime import datetime, timedelta, timezone
import urllib.parse
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
import streamlit as st
import speech_recognition as sr

# Cria a pasta para armazenar os áudios fisicamente no servidor
os.makedirs("patient_audios", exist_ok=True)

# ==============================================================================
# 1. CONSTANTES E VALIDAÇÃO ESTRITA DE AMBIENTE
# ==============================================================================
DB_NAME = "vitavoz_prod_v27.db"
SLA_MINUTOS_PADRAO = 30
SESSION_TIMEOUT_MINUTES = 30
MAX_REPORT_CHARS = 3000
MAX_CONDUCT_CHARS = 3000
IDEMPOTENCY_SECONDS = 30

BOOTSTRAP_SECRET = os.environ.get("VITAVOZ_BOOTSTRAP_SECRET", "DEV_SECRET_KEY")
BACKUP_ENCRYPTION_KEY = os.environ.get("VITAVOZ_BACKUP_KEY", BOOTSTRAP_SECRET)
PUBLIC_BASE_URL = os.environ.get("VITAVOZ_BASE_URL", "https://www.vitavoz.com.br")

if not BOOTSTRAP_SECRET:
    st.error("🚨 ERRO DE INFRAESTRUTURA: A variável 'VITAVOZ_BOOTSTRAP_SECRET' é obrigatória no servidor.")
    st.stop()

SLA_BY_PRIORITY = {1: 5, 2: 15, 3: 30}
STATUS_RECEIVED = "RECEIVED"
STATUS_ACKNOWLEDGED = "ACKNOWLEDGED"
STATUS_ESCALATED = "ESCALATED"
STATUS_PENDING_NURSE = "PENDING_NURSE"
STATUS_RESOLVED = "RESOLVED"
ACTIVE_STATUSES = (STATUS_RECEIVED, STATUS_ACKNOWLEDGED, STATUS_ESCALATED, STATUS_PENDING_NURSE)

ACTOR_PATIENT = "PATIENT"
ACTOR_DOCTOR = "DOCTOR"
ACTOR_INTERNAL = "INTERNAL_USER"
ACTOR_SYSTEM = "SYSTEM"

VALID_TRANSITIONS = {
    STATUS_RECEIVED: [STATUS_ACKNOWLEDGED],
    STATUS_ACKNOWLEDGED: [STATUS_ESCALATED, STATUS_RESOLVED],
    STATUS_ESCALATED: [STATUS_ESCALATED, STATUS_RESOLVED, STATUS_PENDING_NURSE],
    STATUS_PENDING_NURSE: [STATUS_RESOLVED],
    STATUS_RESOLVED: []
}

ROLE_PERMISSIONS = {
    f"{STATUS_RECEIVED}->{STATUS_ACKNOWLEDGED}": ["NURSE", "ASSISTANT", "ADMIN"],
    f"{STATUS_ACKNOWLEDGED}->{STATUS_ESCALATED}": ["NURSE", "ADMIN"],
    f"{STATUS_ACKNOWLEDGED}->{STATUS_RESOLVED}": ["NURSE", "ASSISTANT", "ADMIN"],
    f"{STATUS_ESCALATED}->{STATUS_ESCALATED}": ["NURSE", "ADMIN"],
    f"{STATUS_ESCALATED}->{STATUS_PENDING_NURSE}": ["DOCTOR"],
    f"{STATUS_ESCALATED}->{STATUS_RESOLVED}": ["DOCTOR"],
    f"{STATUS_PENDING_NURSE}->{STATUS_RESOLVED}": ["NURSE", "ASSISTANT", "ADMIN"]
}

# ==============================================================================
# CONFIGURAÇÃO DE TELA E TEMA VISUAL (UI/UX)
# ==============================================================================
st.set_page_config(page_title="VitaVoz | Gestão Operacional", layout="wide", page_icon="🛡️")

# INSERINDO A LOGO OFICIAL NATIVA DO STREAMLIT NA SIDEBAR
try:
    st.logo("logo_vitavoz.png.jfif", size="large")
except Exception:
    pass # Ignora se a imagem não for encontrada

# CSS MESTRE - TEMA FUTURISTA B2B E LEGIBILIDADE
st.markdown("""
    <style>
    /* Esconde marcações inúteis do Streamlit */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}

    /* Fundo Global da App (O Azul Marinho Profundo da Logo) */
    .stApp { background-color: #0b1329; }

    /* Forçando a cor dos textos centrais para Branco/Cinza Claro */
    h1, h2, h3, h4, h5, h6, p, span, div { color: #e2e8f0; font-family: 'Inter', sans-serif; }
    
    /* Textos do Painel Central e Títulos */
    .main-header { font-size: 32px; font-weight: 900; color: #ffffff; margin-bottom: 4px; letter-spacing: -0.5px;}
    .sub-header { font-size: 15px; color: #94a3b8; margin-bottom: 25px; line-height: 1.5; }
    
    /* Cards de Métricas (Dashboard) */
    .metric-card { 
        padding: 16px; 
        border-radius: 12px; 
        border: 1px solid rgba(56, 189, 248, 0.2); 
        text-align: center; 
        background: linear-gradient(145deg, #0f172a 0%, #1e293b 100%); 
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
    }
    .metric-val { font-size: 28px; font-weight: 900; margin-bottom: 5px; color: #38bdf8; text-shadow: 0 0 10px rgba(56,189,248,0.2);}
    .metric-card p { color: #94a3b8 !important; font-size: 13px; font-weight: 600;}
    
    /* Estilização da Barra Lateral */
    [data-testid="stSidebar"] {
        background-color: #050d18 !important;
        border-right: 1px solid rgba(56, 189, 248, 0.15);
    }

    /* Container da Logo na Sidebar (ULTRA COMPACTO) */
    .sidebar-logo-container {
        display: flex;
        justify-content: center;
        align-items: center;
        padding: 5px 0 15px 0;
        border-bottom: 1px solid rgba(255,255,255,0.05);
        margin-bottom: 15px;
    }
    .sidebar-logo { 
        width: 100px !important; /* <--- ULTRA PEQUENA E ELEGANTE */
        height: auto;
    }

    /* Transformando os Radio Buttons da Sidebar em Blocos Neon (FINOS E LEVES) */
    [data-testid="stSidebar"] div[role="radiogroup"] > label > div:first-child { display: none !important; }
    
    [data-testid="stSidebar"] div[role="radiogroup"] > label {
        background: rgba(15, 23, 42, 0.4);
        border: 1px solid rgba(148, 163, 184, 0.1);
        border-radius: 8px; /* Menos arredondado */
        padding: 10px 14px; /* <--- BEM MAIS FINO AQUI */
        margin-bottom: 8px; /* Menos espaço entre botões */
        transition: all 0.2s ease;
        cursor: pointer;
    }
    
    [data-testid="stSidebar"] div[role="radiogroup"] > label:hover {
        border-color: rgba(56, 189, 248, 0.5);
        background: rgba(56, 189, 248, 0.05);
        transform: translateX(4px);
    }

    [data-testid="stSidebar"] div[role="radiogroup"] > label[data-baseweb="radio"][aria-checked="true"] {
        background: linear-gradient(90deg, rgba(56,189,248,0.15) 0%, rgba(139,92,246,0.15) 100%);
        border: 1px solid #38bdf8;
        box-shadow: 0 0 10px rgba(56, 189, 248, 0.15);
    }
    
    /* Fonte dos botões menor e mais limpa */
    [data-testid="stSidebar"] div[role="radiogroup"] > label p {
        color: #e2e8f0 !important;
        font-weight: 600 !important;
        font-size: 13px !important; /* <--- FONTE MENOR */
        margin: 0;
    }
    </style>
""", unsafe_allow_html=True)


# ==============================================================================
# 3. CORE SERVICES E BANCO DE DADOS
# ==============================================================================
def utc_now() -> datetime: return datetime.now(timezone.utc)
def format_local_time(iso_utc_str: str) -> str:
    if not iso_utc_str: return "-"
    try:
        dt = datetime.fromisoformat(iso_utc_str)
        if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone(timedelta(hours=-3))).strftime('%d/%m/%Y %H:%M')
    except Exception: return iso_utc_str

def format_iso_to_br_date(iso_date_str: str) -> str:
    if not iso_date_str: return "-"
    try: return datetime.strptime(iso_date_str, "%Y-%m-%d").strftime("%d/%m/%Y")
    except ValueError: return iso_date_str

def normalize_phone(phone: str) -> str: return re.sub(r"\D", "", phone)
def hash_password(password: str) -> str: return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
def verify_password(password: str, hashed: str) -> bool: return bcrypt.checkpw(password.encode(), hashed.encode())
def hash_token(token: str) -> str: return hashlib.sha256(token.encode()).hexdigest()
def generate_secure_token() -> str: return secrets.token_urlsafe(32)

class AudioTranscriptionService:
    @staticmethod
    def transcribe(audio_bytes: bytes) -> str:
        r = sr.Recognizer()
        try:
            with sr.AudioFile(io.BytesIO(audio_bytes)) as source:
                audio_data = r.record(source)
            return r.recognize_google(audio_data, language="pt-BR")
        except sr.UnknownValueError: raise ValueError("Áudio não compreendido")
        except sr.RequestError as e: raise ConnectionError(f"Erro na API de transcrição: {e}")
        except Exception as e: raise RuntimeError(f"Falha técnica ao processar áudio: {e}")

class BackupService:
    MAGIC = b"VTVZ"
    VERSION = b"\x01"
    @staticmethod
    def _derive_key(secret: str, salt: bytes) -> bytes:
        kdf = Scrypt(salt=salt, length=32, n=2**14, r=8, p=1)
        return kdf.derive(secret.encode())
    @staticmethod
    def generate_backup_encrypted(secret: str) -> bytes:
        salt = secrets.token_bytes(16)
        nonce = secrets.token_bytes(12)
        key = BackupService._derive_key(secret, salt)
        aesgcm = AESGCM(key)
        with get_db() as src_conn:
            mem_db = sqlite3.connect(":memory:")
            src_conn.backup(mem_db)
            db_bytes = mem_db.serialize()
            mem_db.close()
        ciphertext = aesgcm.encrypt(nonce, db_bytes, None)
        return BackupService.MAGIC + BackupService.VERSION + salt + nonce + ciphertext

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA busy_timeout = 5000;")
    return conn

@st.cache_resource
def run_migrations():
    with get_db() as conn:
        c = conn.cursor()
        c.execute("BEGIN EXCLUSIVE")
        c.execute("CREATE TABLE IF NOT EXISTS schema_version (version INTEGER)")
        ver_row = c.execute("SELECT MAX(version) as v FROM schema_version").fetchone()
        current_version = ver_row['v'] if ver_row['v'] else 0
        if current_version < 1:
            c.execute("""CREATE TABLE clinics (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, protocol_duration_days INTEGER DEFAULT 15, created_at TEXT)""")
            c.execute("""CREATE TABLE users (id INTEGER PRIMARY KEY AUTOINCREMENT, clinic_id INTEGER REFERENCES clinics(id) ON DELETE RESTRICT, name TEXT, username TEXT UNIQUE, password_hash TEXT, role TEXT CHECK(role IN ('NURSE', 'ASSISTANT', 'DOCTOR', 'ADMIN')), failed_login_attempts INTEGER DEFAULT 0, locked_until TEXT, active INTEGER DEFAULT 1)""")
            c.execute("""CREATE TABLE patients (id INTEGER PRIMARY KEY AUTOINCREMENT, clinic_id INTEGER REFERENCES clinics(id) ON DELETE RESTRICT, name TEXT, phone TEXT, procedure_name TEXT, procedure_date TEXT, allergies TEXT, notes TEXT, token_hash TEXT UNIQUE, token_expires_at TEXT, revoked_at TEXT, active INTEGER DEFAULT 1, created_at TEXT)""")
            c.execute("""CREATE TABLE patient_reports_log (id INTEGER PRIMARY KEY AUTOINCREMENT, patient_id INTEGER REFERENCES patients(id), submission_uuid TEXT UNIQUE, timestamp TEXT)""")
            c.execute("""CREATE TABLE reports (id INTEGER PRIMARY KEY AUTOINCREMENT, report_uuid TEXT UNIQUE, patient_id INTEGER REFERENCES patients(id) ON DELETE RESTRICT, clinic_id INTEGER REFERENCES clinics(id) ON DELETE RESTRICT, operational_priority INTEGER CHECK(operational_priority BETWEEN 1 AND 3) DEFAULT 3, priority_reason TEXT, patient_declared_emergency INTEGER DEFAULT 0, sla_target_minutes INTEGER DEFAULT 30, sla_breached INTEGER DEFAULT 0, pain INTEGER CHECK(pain BETWEEN 0 AND 10), trend TEXT, symptoms TEXT, transcript_original TEXT, transcript_source TEXT, status TEXT CHECK(status IN ('RECEIVED', 'ACKNOWLEDGED', 'ESCALATED', 'PENDING_NURSE', 'RESOLVED')), assigned_user_id INTEGER REFERENCES users(id) ON DELETE RESTRICT, conduct TEXT, resolution_source TEXT, received_at TEXT, acknowledged_at TEXT, escalated_at TEXT, doctor_viewed_at TEXT, doctor_responded_at TEXT, resolved_at TEXT, doctor_token_hash TEXT, doctor_link_expires_at TEXT)""")
            c.execute("""CREATE TABLE audit_events (id INTEGER PRIMARY KEY AUTOINCREMENT, clinic_id INTEGER REFERENCES clinics(id), report_uuid TEXT, patient_id INTEGER, actor_type TEXT, actor_name TEXT, actor_user_id INTEGER, action TEXT, old_status TEXT, new_status TEXT, details TEXT, timestamp TEXT, previous_hash TEXT, event_hash TEXT)""")
            c.execute("CREATE TRIGGER IF NOT EXISTS prevent_audit_update BEFORE UPDATE ON audit_events BEGIN SELECT RAISE(ABORT, 'Operação proibida: Tabela audit_events é append-only.'); END;")
            c.execute("CREATE TRIGGER IF NOT EXISTS prevent_audit_delete BEFORE DELETE ON audit_events BEGIN SELECT RAISE(ABORT, 'Operação proibida: Tabela audit_events é append-only.'); END;")
            c.execute("CREATE INDEX IF NOT EXISTS idx_patients_clinic ON patients(clinic_id)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_reports_patient ON reports(patient_id)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_reports_clinic ON reports(clinic_id)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_reports_status ON reports(status)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_audit_clinic ON audit_events(clinic_id, timestamp)")
            c.execute("INSERT INTO schema_version (version) VALUES (1)")
        conn.commit()

run_migrations()

class DatabaseService:
    @staticmethod
    def log_audit(clinic_id, report_uuid, patient_id, actor_type, actor_name, actor_user_id, action, old_status, new_status, details, conn_override=None):
        ts = utc_now().isoformat()
        def _execute_log(c):
            last_event = c.execute("SELECT event_hash FROM audit_events WHERE clinic_id = ? ORDER BY id DESC LIMIT 1", (clinic_id,)).fetchone()
            prev_hash = last_event['event_hash'] if last_event else "GENESIS_HASH"
            data_str = f"{clinic_id}|{report_uuid}|{patient_id}|{actor_type}|{actor_name}|{actor_user_id}|{action}|{old_status}|{new_status}|{details}|{ts}|{prev_hash}"
            event_hash = hashlib.sha256(data_str.encode()).hexdigest()
            c.execute("""INSERT INTO audit_events (clinic_id, report_uuid, patient_id, actor_type, actor_name, actor_user_id, action, old_status, new_status, details, timestamp, previous_hash, event_hash) 
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                      (clinic_id, report_uuid, patient_id, actor_type, actor_name, actor_user_id, action, old_status, new_status, details, ts, prev_hash, event_hash))
        if conn_override: _execute_log(conn_override)
        else:
            with get_db() as conn:
                conn.execute("BEGIN IMMEDIATE")
                _execute_log(conn.cursor())
                conn.commit()

    @staticmethod
    def verify_hash_chain(clinic_id):
        with get_db() as conn:
            audits = conn.cursor().execute("SELECT * FROM audit_events WHERE clinic_id = ? ORDER BY id ASC", (clinic_id,)).fetchall()
        prev_hash = "GENESIS_HASH"
        for aud in audits:
            if aud['previous_hash'] != prev_hash: return False, f"Violação de sequência no log ID #{aud['id']}."
            data_str = f"{aud['clinic_id']}|{aud['report_uuid']}|{aud['patient_id']}|{aud['actor_type']}|{aud['actor_name']}|{aud['actor_user_id']}|{aud['action']}|{aud['old_status']}|{aud['new_status']}|{aud['details']}|{aud['timestamp']}|{aud['previous_hash']}"
            if aud['event_hash'] != hashlib.sha256(data_str.encode()).hexdigest(): return False, f"Adulteração de dados detectada no evento ID #{aud['id']}!"
            prev_hash = aud['event_hash']
        return True, f"Integridade confirmada."

    @staticmethod
    def submit_patient_report(clinic_id, patient_id, submission_uuid, pain, trend, symptoms_list, transcript_original, is_emergency, audio_bytes=None):
        now_dt = utc_now()
        now_str = now_dt.isoformat()
        dez_min_atras = (now_dt - timedelta(minutes=10)).isoformat()
        oper_priority, priority_reason = 3, "NORMAL_FOLLOWUP"
        if pain >= 7 or trend == "🔴 Piorou": oper_priority, priority_reason = 2, "HIGH_PAIN_OR_CLINICAL_WORSENING"
        if is_emergency: oper_priority, priority_reason = 1, "PATIENT_DECLARED_EMERGENCY"
        sla_alvo = SLA_BY_PRIORITY[oper_priority]
        report_uuid = str(uuid.uuid4())

        if audio_bytes:
            with open(f"patient_audios/{report_uuid}.wav", "wb") as f: f.write(audio_bytes)

        with get_db() as conn:
            c = conn.cursor()
            c.execute("BEGIN IMMEDIATE")
            patient_check = c.execute("SELECT id FROM patients WHERE id = ? AND clinic_id = ? AND active = 1", (patient_id, clinic_id)).fetchone()
            if not patient_check:
                conn.rollback(); return False, "Paciente não pertence à operação informada ou está inativo."
            already_processed = c.execute("SELECT COUNT(*) FROM patient_reports_log WHERE submission_uuid = ?", (submission_uuid,)).fetchone()[0]
            if already_processed > 0:
                conn.rollback(); return False, "Este relato já foi processado na rede."
            count = c.execute("SELECT COUNT(*) FROM patient_reports_log WHERE patient_id = ? AND timestamp > ?", (patient_id, dez_min_atras)).fetchone()[0]
            if count >= 5:
                conn.rollback(); return False, "Limite de envios excedido."
            c.execute("INSERT INTO patient_reports_log (patient_id, submission_uuid, timestamp) VALUES (?, ?, ?)", (patient_id, submission_uuid, now_str))
            c.execute("""
                INSERT INTO reports (
                    clinic_id, report_uuid, patient_id, operational_priority, priority_reason,
                    patient_declared_emergency, sla_target_minutes, pain, trend, symptoms,
                    transcript_original, status, received_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'RECEIVED', ?)
            """, (clinic_id, report_uuid, patient_id, oper_priority, priority_reason, 1 if is_emergency else 0, sla_alvo, pain, trend, ",".join(symptoms_list), transcript_original, now_str))
            DatabaseService.log_audit(clinic_id, report_uuid, patient_id, ACTOR_PATIENT, "Paciente", None, "REPORT_SUBMITTED", "NONE", STATUS_RECEIVED, f"Relato submetido.", conn_override=c)
            conn.commit()
        return True, "OK"

    @staticmethod
    def transition_internal_report(clinic_id, report_uuid, new_status, actor_user_id, actor_role, actor_name, details, conduct=None, resolution_source=None):
        with get_db() as conn:
            c = conn.cursor()
            c.execute("BEGIN IMMEDIATE")
            rep_data = c.execute("SELECT status, patient_id, received_at, sla_target_minutes, patient_declared_emergency FROM reports WHERE report_uuid = ? AND clinic_id = ?", (report_uuid, clinic_id)).fetchone()
            if not rep_data:
                conn.rollback(); return False, "Relato de protocolo não encontrado."
            current_status = rep_data['status']
            patient_id = rep_data['patient_id']
            if new_status not in VALID_TRANSITIONS.get(current_status, []):
                conn.rollback(); return False, f"Transição inválida."
            required_roles = ROLE_PERMISSIONS.get(f"{current_status}->{new_status}", [])
            if actor_role not in required_roles:
                conn.rollback(); return False, f"Acesso Negado."
            if conduct and (not conduct.strip() or len(conduct) > MAX_CONDUCT_CHARS):
                conn.rollback(); return False, f"Conduta inválida."
            now = utc_now()
            now_str = now.isoformat()
            timestamp_field = {STATUS_ACKNOWLEDGED: "acknowledged_at", STATUS_RESOLVED: "resolved_at"}.get(new_status)
            updates, params = ["status = ?"], [new_status]
            if timestamp_field: updates.extend([f"{timestamp_field} = ?"]); params.append(now_str)
            if conduct: updates.extend(["conduct = ?"]); params.append(conduct)
            if resolution_source: updates.extend(["resolution_source = ?"]); params.append(resolution_source)
            if new_status == STATUS_ACKNOWLEDGED: updates.extend(["assigned_user_id = ?"]); params.append(actor_user_id)
            if current_status == STATUS_RECEIVED and new_status == STATUS_ACKNOWLEDGED:
                espera_min = (now - datetime.fromisoformat(rep_data['received_at'])).total_seconds() / 60
                is_breached = 1 if espera_min > rep_data['sla_target_minutes'] else 0
                updates.extend(["sla_breached = ?"]); params.append(is_breached)
            if rep_data['patient_declared_emergency'] == 1 and new_status == STATUS_RESOLVED and current_status != STATUS_PENDING_NURSE:
                conn.rollback(); return False, "Bloqueio: Exige conduta médica."
            params.extend([report_uuid, current_status, clinic_id])
            c.execute(f"UPDATE reports SET {', '.join(updates)} WHERE report_uuid = ? AND status = ? AND clinic_id = ?", tuple(params))
            if c.rowcount != 1:
                conn.rollback(); return False, "Concorrência operacional."
            DatabaseService.log_audit(clinic_id, report_uuid, patient_id, ACTOR_INTERNAL, actor_name, actor_user_id, "STATUS_CHANGE", current_status, new_status, details, conn_override=c)
            conn.commit()
        return True, "Sucesso"

    @staticmethod
    def reassign_internal_report(clinic_id, report_uuid, actor_user_id, actor_role, actor_name, target_user_id):
        if actor_role not in ["NURSE", "ADMIN"]: return False, "Acesso Negado."
        with get_db() as conn:
            c = conn.cursor()
            c.execute("BEGIN IMMEDIATE")
            target_user = c.execute("SELECT name, role FROM users WHERE id = ? AND clinic_id = ? AND active = 1", (target_user_id, clinic_id)).fetchone()
            if not target_user:
                conn.rollback(); return False, "Usuário alvo é inválido."
            if target_user['role'] not in ["NURSE", "ASSISTANT", "ADMIN"]:
                conn.rollback(); return False, "Papel incompatível."
            rep_data = c.execute("SELECT status, patient_id, assigned_user_id FROM reports WHERE report_uuid = ? AND clinic_id = ?", (report_uuid, clinic_id)).fetchone()
            if not rep_data:
                conn.rollback(); return False, "Relato não encontrado."
            current_status = rep_data['status']
            old_assignee_id = rep_data['assigned_user_id']
            patient_id = rep_data['patient_id']
            old_name = "Ninguém"
            if old_assignee_id:
                old_user_row = c.execute("SELECT name FROM users WHERE id = ?", (old_assignee_id,)).fetchone()
                if old_user_row: old_name = old_user_row['name']
            c.execute("UPDATE reports SET assigned_user_id = ? WHERE report_uuid = ? AND status = ? AND clinic_id = ?", (target_user_id, report_uuid, current_status, clinic_id))
            if c.rowcount != 1:
                conn.rollback(); return False, "Falha atômica."
            DatabaseService.log_audit(clinic_id, report_uuid, patient_id, ACTOR_INTERNAL, actor_name, actor_user_id, "REASSIGNMENT", current_status, current_status, f"Reatribuído de {old_name} para {target_user['name']}.", conn_override=c)
            conn.commit()
        return True, "Sucesso"

    @staticmethod
    def escalate_to_doctor(clinic_id, report_uuid, actor_user_id, actor_name, actor_role):
        has_perm = actor_role in ROLE_PERMISSIONS.get(f"{STATUS_ACKNOWLEDGED}->{STATUS_ESCALATED}", []) or \
                   actor_role in ROLE_PERMISSIONS.get(f"{STATUS_ESCALATED}->{STATUS_ESCALATED}", [])
        if not has_perm: return None
        doc_token = generate_secure_token()
        exp = (utc_now() + timedelta(minutes=30)).isoformat()
        with get_db() as conn:
            c = conn.cursor()
            c.execute("BEGIN IMMEDIATE")
            rep_data = c.execute("SELECT patient_id, status FROM reports WHERE report_uuid = ? AND clinic_id = ? AND status IN (?, ?)", (report_uuid, clinic_id, STATUS_ACKNOWLEDGED, STATUS_ESCALATED)).fetchone()
            if not rep_data:
                conn.rollback(); return None
            patient_id = rep_data['patient_id']
            old_status = rep_data['status']
            c.execute("""UPDATE reports SET status = ?, escalated_at = ?, doctor_token_hash = ?, doctor_link_expires_at = ? 
                         WHERE report_uuid = ? AND status = ? AND clinic_id = ?""",
                      (STATUS_ESCALATED, utc_now().isoformat(), hash_token(doc_token), exp, report_uuid, old_status, clinic_id))
            if c.rowcount != 1:
                conn.rollback(); return None
            DatabaseService.log_audit(clinic_id, report_uuid, patient_id, ACTOR_INTERNAL, actor_name, actor_user_id, "REPORT_ESCALATED", old_status, STATUS_ESCALATED, "Escalonado para médico.", conn_override=c)
            conn.commit()
        return doc_token

    @staticmethod
    def consume_doctor_token(report_uuid, clinic_id, conduct, doc_name="Médico"):
        if not conduct or not conduct.strip() or len(conduct) > MAX_CONDUCT_CHARS: return False, "Conduta inválida."
        now_str = utc_now().isoformat()
        new_status = STATUS_PENDING_NURSE
        timestamp_field = "doctor_responded_at"
        with get_db() as conn:
            c = conn.cursor()
            c.execute("BEGIN IMMEDIATE")
            rep_data = c.execute("SELECT patient_id FROM reports WHERE report_uuid = ? AND clinic_id = ? AND status = 'ESCALATED'", (report_uuid, clinic_id)).fetchone()
            if not rep_data:
                conn.rollback(); return False, "Interface corrompida ou acesso consumido."
            patient_id = rep_data['patient_id']
            c.execute(f"""UPDATE reports SET status = ?, {timestamp_field} = ?, conduct = ?, resolution_source = 'DOCTOR', doctor_token_hash = NULL, doctor_link_expires_at = NULL 
                          WHERE report_uuid = ? AND status = ? AND doctor_token_hash IS NOT NULL AND doctor_link_expires_at > ? AND clinic_id = ?""",
                      (new_status, now_str, conduct, report_uuid, STATUS_ESCALATED, now_str, clinic_id))
            if c.rowcount != 1:
                conn.rollback(); return False, "Expiração de Token."
            DatabaseService.log_audit(clinic_id, report_uuid, patient_id, ACTOR_DOCTOR, doc_name, None, "DOCTOR_CONDUCT", STATUS_ESCALATED, new_status, f"Conduta: {conduct}", conn_override=c)
            conn.commit()
        return True, "Sucesso"

class HealthService:
    @staticmethod
    def get_status(clinic_id=None) -> dict:
        try:
            with get_db() as conn:
                c = conn.cursor()
                db_ok = c.execute("SELECT 1").fetchone()[0] == 1
                journal_mode = c.execute("PRAGMA journal_mode").fetchone()[0]
                schema_ver = c.execute("SELECT MAX(version) FROM schema_version").fetchone()[0]
                last_backup = "-"
                pending_count, breached_count = 0, 0
                if clinic_id:
                    l_b = c.execute("SELECT timestamp FROM audit_events WHERE clinic_id = ? AND action = 'DATABASE_BACKUP' ORDER BY id DESC LIMIT 1", (clinic_id,)).fetchone()
                    if l_b: last_backup = format_local_time(l_b['timestamp'])
                    pending_count = c.execute(f"SELECT COUNT(*) FROM reports WHERE clinic_id = ? AND status IN {ACTIVE_STATUSES}", (clinic_id,)).fetchone()[0]
                    breached_count = c.execute("SELECT COUNT(*) FROM reports WHERE clinic_id = ? AND (sla_breached = 1 OR (status = 'RECEIVED' AND (julianday('now') - julianday(received_at))*1440 > sla_target_minutes))", (clinic_id,)).fetchone()[0]
            return {"healthy": True, "db_connection": "OK" if db_ok else "ERROR", "journal_mode": journal_mode.upper(), "schema_version": f"v{schema_ver}", "last_backup": last_backup, "pending_reports": pending_count, "breached_slas": breached_count}
        except Exception:
            return {"healthy": False, "error": "Falha de telemetria."}

def require_auth():
    if not st.session_state.get("autenticado", False):
        st.error("Acesso Negado. Faça login.")
        st.stop()
    with get_db() as conn:
        user_check = conn.cursor().execute("SELECT id, clinic_id, active, role FROM users WHERE id = ?", (st.session_state.get("user_id"),)).fetchone()
    if (not user_check or user_check['active'] != 1 or user_check['clinic_id'] != st.session_state.get("clinic_id") or user_check['role'] != st.session_state.get("user_role")):
        st.session_state.clear()
        st.error("🔒 Sessão inválida ou revogada.")
        st.stop()
    if "last_activity" in st.session_state:
        if (utc_now() - st.session_state.last_activity).total_seconds() / 60 > SESSION_TIMEOUT_MINUTES:
            st.session_state.clear()
            st.error("🔒 Sessão expirada por inatividade.")
            st.stop()
    st.session_state.last_activity = utc_now()

def require_role(*allowed_roles):
    require_auth()
    if st.session_state.get("user_role") not in allowed_roles:
        st.error("🔒 Acesso Negado: Perfil sem privilégios.")
        st.stop()

def check_bootstrap():
    with get_db() as conn:
        has_users = conn.cursor().execute("SELECT COUNT(*) FROM users").fetchone()[0] > 0
    if not has_users:
        st.warning("⚠️ Setup Inicial do Sistema (Primeira Instalação)")
        with st.form("bootstrap_form"):
            b_secret = st.text_input("Chave Mestre de Instalação (Bootstrap Secret)", type="password")
            clinic_name = st.text_input("Nome da Operação/Clínica")
            admin_user = st.text_input("Credencial Admin (ex: admin)")
            admin_pwd = st.text_input("Senha Master (Mínimo 12 caracteres)", type="password")
            if st.form_submit_button("Inicializar Ambiente Seguro"):
                if b_secret != BOOTSTRAP_SECRET: st.error("Chave de instalação mestre incorreta.")
                elif not clinic_name.strip(): st.error("O nome da operação/clínica é obrigatório.")
                elif not admin_user.strip(): st.error("O usuário Admin é obrigatório.")
                elif len(admin_pwd) < 12: st.error("A arquitetura exige mínimo de 12 caracteres.")
                else:
                    norm_admin = admin_user.strip().lower()
                    with get_db() as conn:
                        c = conn.cursor()
                        c.execute("BEGIN IMMEDIATE")
                        user_count = c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
                        if user_count > 0:
                            conn.rollback(); st.error("Ambiente já inicializado."); st.stop()
                        c.execute("INSERT INTO clinics (name, created_at) VALUES (?, ?)", (clinic_name.strip(), utc_now().isoformat()))
                        cid = c.lastrowid
                        c.execute("INSERT INTO users (clinic_id, name, username, password_hash, role) VALUES (?, 'Administração Central', ?, ?, 'ADMIN')", (cid, norm_admin, hash_password(admin_pwd)))
                        conn.commit()
                    st.success("Ambiente inicializado. Faça login como Admin.")
                    st.rerun()
        st.stop()

check_bootstrap()

# ==============================================================================
# 4. PORTAL DO CIRURGIÃO EXTERNO E PACIENTE (Omitido visual extra, lida via DB)
# ==============================================================================
query_params = st.query_params

if query_params.get("view") == "doctor" and "doc_validated_token" not in st.session_state:
    raw_doc_token = query_params.get("token")
    if raw_doc_token:
        doc_token_hash = hash_token(raw_doc_token)
        now_utc_str = utc_now().isoformat()
        with get_db() as conn:
            valid_report = conn.cursor().execute("SELECT r.report_uuid FROM reports r WHERE r.doctor_token_hash = ? AND r.status = ? AND r.doctor_link_expires_at > ?", (doc_token_hash, STATUS_ESCALATED, now_utc_str)).fetchone()
        if valid_report:
            st.session_state.doc_validated_token = raw_doc_token
            st.query_params.clear()
        else:
            st.markdown('<div class="hide-sidebar"></div>', unsafe_allow_html=True)
            st.error("🔒 Acesso Negado: O token do avaliador médico é inválido ou expirou.")
            st.stop()

if "doc_validated_token" in st.session_state:
    st.markdown('<div class="hide-sidebar"></div>', unsafe_allow_html=True)
    doc_token = st.session_state.get("doc_validated_token")
    now_utc_str = utc_now().isoformat()
    with get_db() as conn:
        report = conn.cursor().execute("""
            SELECT r.*, p.name as patient_name, p.procedure_name, p.procedure_date 
            FROM reports r JOIN patients p ON r.patient_id = p.id 
            WHERE r.doctor_token_hash = ? AND r.status = ? AND r.doctor_link_expires_at > ?
        """, (hash_token(doc_token), STATUS_ESCALATED, now_utc_str)).fetchone()
    if not report:
        del st.session_state.doc_validated_token
        st.error("🔒 Token inválido ou conduta já registrada. Acesso descartado.")
        st.stop()

    if not report['doctor_viewed_at']:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("BEGIN IMMEDIATE")
            c.execute("UPDATE reports SET doctor_viewed_at = ? WHERE report_uuid = ? AND doctor_viewed_at IS NULL AND clinic_id = ?", (now_utc_str, report['report_uuid'], report['clinic_id']))
            if c.rowcount == 1:
                DatabaseService.log_audit(report['clinic_id'], report['report_uuid'], report['patient_id'], ACTOR_DOCTOR, "Médico Externo", None, "DOCTOR_ACCESS", report['status'], report['status'], "Link médico aberto.", conn_override=c)
            conn.commit()

    try: d_plus = (utc_now().date() - datetime.strptime(report['procedure_date'], "%Y-%m-%d").date()).days
    except ValueError: d_plus = "?"

    st.markdown("<div style='background-color: #991B1B; color: white; padding: 10px; border-radius: 5px; text-align: center; font-weight: bold; margin-bottom: 20px;'>🚨 SOLICITAÇÃO DE AVALIAÇÃO MÉDICA</div>", unsafe_allow_html=True)
    st.markdown(f"### {html.escape(report['patient_name'])}")
    st.markdown(f"**{html.escape(report['procedure_name'])} (D+{d_plus})**")
    st.divider()
    st.error(f"**Dor Escala Numérica:** {report['pain']}/10 | **Evolução Declarada:** {html.escape(report['trend'])} | **Sintomas Extras:** {html.escape(report['symptoms'])}")
    if report['transcript_original']: st.markdown(f"> *\"{html.escape(report['transcript_original'])}\"*")
    audio_path = f"patient_audios/{report['report_uuid']}.wav"
    if os.path.exists(audio_path): st.audio(audio_path)

    st.divider()
    st.markdown("### 📝 Registro de Orientação / Conduta Médica (Acesso Único)")
    with st.form("doctor_conduct_form"):
        c_med1, c_med2, c_med3 = st.columns([2, 1, 1])
        with c_med1: med_nome = st.text_input("Identificação do Profissional (Nome):")
        with c_med2: med_crm = st.text_input("CRM (Opcional):")
        with c_med3: med_crm_uf = st.text_input("UF CRM (Opcional):")
        conduta_acao = st.radio("Ação de Retorno à Equipe Operacional:", [
            "Manter acompanhamento remoto padronizado",
            "Orientação clínica à equipe assistencial",
            "Retorno presencial ambulatorial",
            "Encaminhar para Pronto Atendimento Imediato"
        ])
        observacao = st.text_area("Observação/Conduta registrada (Obrigatório):")
        if st.form_submit_button("Registrar e Enviar Conduta", type="primary"):
            if not med_nome.strip() or not observacao.strip(): st.error("Identificação e observação clínica são obrigatórias.")
            else:
                doc_ident = med_nome.strip()
                if med_crm.strip():
                    uf_str = f"/{med_crm_uf.strip().upper()}" if med_crm_uf.strip() else ""
                    doc_ident += f" (CRM {med_crm.strip()}{uf_str})"
                conduta_formatada = f"[{conduta_acao}] {observacao.strip()}"
                ok, msg = DatabaseService.consume_doctor_token(report['report_uuid'], report['clinic_id'], conduta_formatada, doc_name=doc_ident)
                if ok:
                    del st.session_state.doc_validated_token
                    st.success("Conduta registrada com sucesso. Acesso revogado.")
                    time.sleep(2); st.rerun()
                else: st.error(f"Falha técnica: {msg}")
    st.stop()

if query_params.get("view") == "portal" and "patient_session" not in st.session_state:
    raw_token = query_params.get("token")
    if not raw_token: st.error("Token de acesso base ausente na string."); st.stop()
    with get_db() as conn:
        patient = conn.cursor().execute("SELECT id, clinic_id, active, revoked_at, token_expires_at FROM patients WHERE token_hash = ? AND active = 1", (hash_token(raw_token),)).fetchone()
    if not patient or patient['revoked_at']: st.error("Acesso revogado."); st.stop()
    if utc_now() > datetime.fromisoformat(patient['token_expires_at']): st.error("Acompanhamento concluído."); st.stop()

    st.session_state.patient_session = {"id": patient['id'], "clinic_id": patient['clinic_id']}
    st.session_state.patient_session_last_activity = utc_now()
    st.session_state.form_submission_uuid = str(uuid.uuid4())
    st.query_params.clear()

if "patient_session" in st.session_state:
    st.markdown('<div class="hide-sidebar"></div>', unsafe_allow_html=True)
    pid = st.session_state.patient_session['id']
    cid = st.session_state.patient_session['clinic_id']
    with get_db() as conn:
        patient_db = conn.cursor().execute("SELECT * FROM patients WHERE id = ? AND clinic_id = ?", (pid, cid)).fetchone()
    if not patient_db or patient_db['active'] != 1 or patient_db['revoked_at'] or utc_now() > datetime.fromisoformat(patient_db['token_expires_at']):
        del st.session_state.patient_session
        st.error("🔒 Sua sessão foi revogada, inativada ou expirou.")
        st.stop()
    if (utc_now() - st.session_state.patient_session_last_activity).total_seconds() / 60 > 30:
        del st.session_state.patient_session
        st.error("🔒 Sessão expirada por inatividade.")
        st.stop()
    st.session_state.patient_session_last_activity = utc_now()

    try: d_plus = (utc_now().date() - datetime.strptime(patient_db['procedure_date'], "%Y-%m-%d").date()).days
    except ValueError: d_plus = "?"

    st.markdown("### VitaVoz")
    st.markdown(f"Olá, **{html.escape(patient_db['name'].split()[0])}** 👋")
    st.info("Este canal organiza o fluxo de comunicação entre você e a clínica. **Ele não é monitorado 24 horas por dia.**")

    with get_db() as conn:
        ultimo_relato = conn.cursor().execute("SELECT status FROM reports WHERE patient_id = ? AND clinic_id = ? ORDER BY id DESC LIMIT 1", (pid, cid)).fetchone()

    if ultimo_relato:
        st.markdown("#### Status do Seu Último Acompanhamento")
        st_val = ultimo_relato['status']
        s1 = "step-done" if st_val != STATUS_RECEIVED else "step-active"
        s2 = "step-done" if st_val in [STATUS_ESCALATED, STATUS_PENDING_NURSE, STATUS_RESOLVED] else ("step-active" if st_val == STATUS_ACKNOWLEDGED else "step-idle")
        s3 = "step-done" if st_val == STATUS_RESOLVED else ("step-active" if st_val in [STATUS_ESCALATED, STATUS_PENDING_NURSE] else "step-idle")
        s4 = "step-done" if st_val == STATUS_RESOLVED else "step-idle"
        st.markdown(f"""
            <span class="step-pill {s1}">1. Recebido</span>
            <span class="step-pill {s2}">2. Em Análise</span>
            <span class="step-pill {s3}">3. Avaliação Médica</span>
            <span class="step-pill {s4}">4. Concluído</span>
            <br><br>
        """, unsafe_allow_html=True)

    dor_val = int(st.select_slider("Nível de dor local ou difusa (0 a 10):", options=[str(i) for i in range(11)], value="0"))
    tendencia = st.radio("Comparando com as últimas 24h:", ["🟢 Melhorou", "⚪ Igual", "🔴 Piorou"], horizontal=True, label_visibility="collapsed", index=1)
    sintomas = st.multiselect("Sintomas Adicionais Observados:", ["Sangramento", "Inchaço", "Febre", "Dormência", "Outro"], label_visibility="collapsed")

    st.divider()
    st.markdown("📝 **Evolução Clínica** (Grave um áudio ou digite)")
    audio_val = st.audio_input("🎤 Clique no microfone para gravar seu relato")

    if "texto_transcrito" not in st.session_state:
        st.session_state["texto_transcrito"] = ""

    if audio_val:
        audio_bytes = audio_val.getvalue()
        current_audio_hash = hashlib.md5(audio_bytes).hexdigest()
        if st.session_state.get("last_audio_hash") != current_audio_hash:
            with st.spinner("🧠 Transcrevendo áudio..."):
                try:
                    texto_resultado = AudioTranscriptionService.transcribe(audio_bytes)
                    st.session_state["texto_transcrito"] = texto_resultado
                    st.session_state["last_audio_hash"] = current_audio_hash
                    st.rerun()
                except ValueError:
                    st.warning("Não foi possível compreender o áudio. Ajuste o texto abaixo.")
                    st.session_state["last_audio_hash"] = current_audio_hash
                except ConnectionError:
                    st.warning("Serviço de transcrição indisponível. Digite o relato.")
                    st.session_state["last_audio_hash"] = current_audio_hash

    texto_final = st.text_area("Verifique e edite o texto antes de enviar (Ou digite manualmente):", key="texto_transcrito")
    is_emergency = st.checkbox("🚨 Considero que preciso de atendimento médico imediato.")
    if is_emergency:
        st.error("🚨 **ISTO NÃO É UM SERVIÇO DE EMERGÊNCIA.** Procure o SAMU (192) ou o hospital imediatamente.")

    st.caption("🔒 **Aviso de Privacidade:** Suas respostas são processadas sob sigilo.")

    if st.button("Submeter Evolução do Quadro", type="primary", use_container_width=True):
        if not texto_final.strip() and not audio_val and dor_val < 3 and not is_emergency:
            st.warning("Grave um áudio, digite um texto ou indique uma evolução perceptível."); st.stop()
        if len(texto_final) > MAX_REPORT_CHARS:
            st.error(f"Limite excedido. Sintetize em menos de {MAX_REPORT_CHARS} caracteres."); st.stop()

        submission_id = st.session_state.get("form_submission_uuid", str(uuid.uuid4()))
        raw_audio_data = audio_val.getvalue() if audio_val else None

        ok_spam, msg_spam = DatabaseService.submit_patient_report(
            cid, pid, submission_id, dor_val, tendencia, sintomas, texto_final, is_emergency, raw_audio_data
        )

        if not ok_spam: st.error(msg_spam); st.stop()
        st.session_state.form_submission_uuid = str(uuid.uuid4())

        if is_emergency: st.error("🚨 **SINALIZAÇÃO OPERACIONAL REGISTRADA NA FILA.** Procure o SAMU (192) ou o hospital.")
        else:
            st.success("✓ Seu relato foi recebido e encaminhado para avaliação na fila da equipe técnica.")
    st.stop()

# ==============================================================================
# 5. BACKOFFICE LOGIN
# ==============================================================================
if not st.session_state.get("autenticado", False):
    st.markdown('<div class="main-header" style="text-align: center; margin-top: 50px;">VitaVoz Operacional</div>', unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        with st.form("login_form"):
            usuario = st.text_input("Usuário do Sistema")
            senha = st.text_input("Credencial", type="password")
            if st.form_submit_button("Autenticar Conexão Segura", use_container_width=True):
                norm_user = usuario.strip().lower()
                with get_db() as conn:
                    user_db = conn.cursor().execute("SELECT * FROM users WHERE username = ? AND active = 1", (norm_user,)).fetchone()
                if user_db:
                    if user_db['locked_until'] and utc_now() < datetime.fromisoformat(user_db['locked_until']):
                        st.error("Serviço bloqueado temporariamente (Security Limit).")
                    elif verify_password(senha, user_db["password_hash"]):
                        with get_db() as conn:
                            conn.cursor().execute("UPDATE users SET failed_login_attempts = 0, locked_until = NULL WHERE id = ?", (user_db['id'],))
                            conn.commit()
                        st.session_state.update({"autenticado": True, "user_name": user_db["name"], "user_id": user_db["id"], "clinic_id": user_db["clinic_id"], "user_role": user_db["role"], "last_activity": utc_now()})
                        DatabaseService.log_audit(user_db['clinic_id'], "NONE", None, ACTOR_INTERNAL, user_db['name'], user_db['id'], "LOGIN_SUCCESS", "NONE", "NONE", "Autenticação sucesso.")
                        st.rerun()
                    else:
                        attempts = user_db['failed_login_attempts'] + 1
                        lock = (utc_now() + timedelta(minutes=15)).isoformat() if attempts >= 5 else None
                        with get_db() as conn:
                            conn.cursor().execute("UPDATE users SET failed_login_attempts = ?, locked_until = ? WHERE id = ?", (attempts, lock, user_db['id']))
                            conn.commit()
                        st.error("Credenciais inválidas.")
                else: st.error("Credenciais inválidas ou usuário inativo.")
    st.stop()

require_auth()
OPERADOR_ATUAL = st.session_state["user_name"]
OPERADOR_ID = st.session_state["user_id"]
CLINICA_ATUAL_ID = st.session_state["clinic_id"]
ROLE_ATUAL = st.session_state["user_role"]

st.markdown('<div class="main-header">VitaVoz</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Plataforma de Gestão Operacional do Acompanhamento Pós-Procedimento</div>', unsafe_allow_html=True)

with st.sidebar:
    # DESENHO DIRETO DA LOGO NATIVA NO CANTO SUPERIOR ESQUERDO
    st.markdown("""
        <div style="display: flex; justify-content: flex-start; align-items: center; padding-bottom: 15px; border-bottom: 1px solid rgba(255,255,255,0.05); margin-bottom: 15px;">
            <svg width="60px" height="60px" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
                <!-- Escudo de fundo -->
                <path d="M50 10 C 72 10, 85 20, 85 42 C 85 68, 50 88, 50 88 C 50 88, 15 68, 15 42 C 15 20, 28 10, 50 10 Z" stroke="#38bdf8" stroke-width="6" fill="#0b1329"/>
                <!-- Onda sonora central -->
                <path d="M26 36 L 38 64 L 46 48" stroke="#38bdf8" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/>
                <!-- Barras do microfone/SLA -->
                <rect x="43" y="38" width="4" height="24" rx="2" fill="#38bdf8"/>
                <rect x="51" y="32" width="4" height="36" rx="2" fill="#38bdf8"/>
                <rect x="59" y="42" width="4" height="16" rx="2" fill="#38bdf8"/>
            </svg>
            <div style="margin-left: 10px;">
                <span style="font-size: 20px; font-weight: 900; color: white;">Vita<span style="color: #38bdf8;">Voz</span></span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Informação do Usuário alinhada à esquerda
    st.markdown(f"<div style='color:#e2e8f0; font-size: 13px; font-weight:600; margin-bottom:20px;'>👤 {html.escape(OPERADOR_ATUAL)} <br><span style='color:#94a3b8; font-size:11px;'>({ROLE_ATUAL})</span></div>", unsafe_allow_html=True)

    # Menu Normal
    menu_opcoes = ["📊 Dashboard Inteligente", "📥 Fila Operacional"]
    if ROLE_ATUAL in ["NURSE", "ASSISTANT", "ADMIN"]: menu_opcoes.append("🗂️ Histórico de Pacientes")
    if ROLE_ATUAL in ["NURSE", "ADMIN"]: menu_opcoes.append("🔗 Cadastrar Paciente")
    if ROLE_ATUAL == "ADMIN":
        menu_opcoes.append("👥 Usuários e Acessos")
        menu_opcoes.append("🩺 Health Check Operacional")
    menu_opcoes.append("⚙️ Segurança da Conta")
    menu = st.radio("Navegação Restrita", menu_opcoes)
    
    if st.button("Finalizar Sessão Protegida", type="secondary", use_container_width=True):
        st.session_state.clear(); st.rerun()

# ==============================================================================
# 6. DASHBOARD E FERRAMENTAS DO BACKOFFICE
# ==============================================================================
if menu == "📊 Dashboard Inteligente":
    require_role("NURSE", "ASSISTANT", "ADMIN")
    st.markdown("## 📊 Inteligência de Adoção e Performance (T1-T4)")

    hoje = utc_now().replace(hour=0, minute=0, second=0).isoformat()
    with get_db() as conn:
        c = conn.cursor()
        t_hoje = c.execute("SELECT COUNT(*) FROM reports WHERE clinic_id = ? AND received_at >= ?", (CLINICA_ATUAL_ID, hoje)).fetchone()[0]
        t_pend = c.execute(f"SELECT COUNT(*) FROM reports WHERE clinic_id = ? AND status IN {ACTIVE_STATUSES}", (CLINICA_ATUAL_ID,)).fetchone()[0]
        reports_geral = c.execute("SELECT * FROM reports WHERE clinic_id = ?", (CLINICA_ATUAL_ID,)).fetchall()
        t_pats = c.execute("SELECT COUNT(*) FROM patients WHERE clinic_id = ?", (CLINICA_ATUAL_ID,)).fetchone()[0]
        t_engag = c.execute("SELECT COUNT(DISTINCT patient_id) FROM reports WHERE clinic_id = ?", (CLINICA_ATUAL_ID,)).fetchone()[0]

    sla_violados_historicos = 0
    t1_list, t2_list, t3_list, t4_list = [], [], [], []

    for r in reports_geral:
        rec_dt = datetime.fromisoformat(r['received_at'])
        sla_alvo = r['sla_target_minutes'] if r['sla_target_minutes'] else SLA_BY_PRIORITY.get(r['operational_priority'], SLA_MINUTOS_PADRAO)

        if r['sla_breached'] == 1 or (r['status'] == STATUS_RECEIVED and (utc_now() - rec_dt).total_seconds() / 60 > sla_alvo):
            sla_violados_historicos += 1

        if r['acknowledged_at']:
            ack_dt = datetime.fromisoformat(r['acknowledged_at'])
            t1_list.append((ack_dt - rec_dt).total_seconds() / 60)
            if r['escalated_at']:
                esc_dt = datetime.fromisoformat(r['escalated_at'])
                t2_list.append((esc_dt - ack_dt).total_seconds() / 60)
                if r['doctor_responded_at']:
                    doc_dt = datetime.fromisoformat(r['doctor_responded_at'])
                    t3_list.append((doc_dt - esc_dt).total_seconds() / 60)
        if r['resolved_at']:
            res_dt = datetime.fromisoformat(r['resolved_at'])
            t4_list.append((res_dt - rec_dt).total_seconds() / 60)

    avg_t1 = int(sum(t1_list)/len(t1_list)) if t1_list else 0
    avg_t2 = int(sum(t2_list)/len(t2_list)) if t2_list else 0
    avg_t3 = int(sum(t3_list)/len(t3_list)) if t3_list else 0
    avg_t4 = round((sum(t4_list)/len(t4_list))/60, 1) if t4_list else 0
    perc_engajamento = int((t_engag / t_pats) * 100) if t_pats > 0 else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(f"<div class='metric-card'><div class='metric-val'>{t_hoje}</div><p>Entradas Hoje</p></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='metric-card'><div class='metric-val'>{t_pend}</div><p>Ativos na Fila</p></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='metric-card'><div class='metric-val' style='color:#EF4444;'>{sla_violados_historicos}</div><p>SLA Violados</p></div>", unsafe_allow_html=True)
    c4.markdown(f"<div class='metric-card'><div class='metric-val' style='color:#10B981;'>{perc_engajamento}%</div><p>Engajamento</p></div>", unsafe_allow_html=True)

elif menu == "📥 Fila Operacional":
    require_role("NURSE", "ASSISTANT", "ADMIN")
    st.markdown("## 📥 Triagem Operacional")
    
    col_title, col_btn = st.columns([4, 1])
    with col_btn:
        if st.button("🔄 Atualizar Fila", use_container_width=True): st.rerun()

    with get_db() as conn:
        active_users = conn.cursor().execute("SELECT id, name, role FROM users WHERE clinic_id = ? AND active = 1 AND role IN ('NURSE', 'ASSISTANT', 'ADMIN')", (CLINICA_ATUAL_ID,)).fetchall()
        reports = conn.cursor().execute(f"""
            SELECT r.*, p.name as patient_name, p.phone as patient_phone, u.name as assigned_user_name
            FROM reports r 
            JOIN patients p ON r.patient_id = p.id 
            LEFT JOIN users u ON r.assigned_user_id = u.id
            WHERE r.status IN {ACTIVE_STATUSES} AND r.clinic_id = ?
            ORDER BY 
                CASE 
                    WHEN r.operational_priority = 1 THEN 1
                    WHEN r.status = 'PENDING_NURSE' THEN 2
                    WHEN r.operational_priority = 2 THEN 3
                    ELSE 4
                END, r.received_at ASC
        """, (CLINICA_ATUAL_ID,)).fetchall()

    if not reports: st.success("🎉 Fila limpa e organizada. Nenhum paciente aguardando.")

    for r in reports:
        ref_date = r['received_at']
        if r['status'] == STATUS_ACKNOWLEDGED and r['acknowledged_at']: ref_date = r['acknowledged_at']
        elif r['status'] == STATUS_ESCALATED and r['escalated_at']: ref_date = r['escalated_at']
        elif r['status'] == STATUS_PENDING_NURSE and r['doctor_responded_at']: ref_date = r['doctor_responded_at']

        if not ref_date: ref_date = r['received_at']

        espera = int((utc_now() - datetime.fromisoformat(ref_date)).total_seconds() / 60)
        box_style = "border: 1px solid #1e293b; background-color: #0f172a; color: white;"
        sla_alvo = r['sla_target_minutes'] if r['sla_target_minutes'] else SLA_BY_PRIORITY.get(r['operational_priority'], SLA_MINUTOS_PADRAO)
        minutos_restantes = sla_alvo - espera

        safe_patient_name = html.escape(r['patient_name'])
        expander_title = ""
        
        if r['operational_priority'] == 1: expander_title = f"🚨 EMERGÊNCIA: {safe_patient_name} | Há {espera}m"
        elif r['status'] == STATUS_RECEIVED: expander_title = f"🟢 NOVO: {safe_patient_name} | Há {espera}m"
        elif r['status'] == STATUS_ACKNOWLEDGED: expander_title = f"🔵 EM ATENDIMENTO: {safe_patient_name}"
        elif r['status'] == STATUS_ESCALATED: expander_title = f"🟠 AVALIAÇÃO MÉDICA: {safe_patient_name}"
        elif r['status'] == STATUS_PENDING_NURSE: expander_title = f"🟣 ORDEM MÉDICA: {safe_patient_name}"
        else: expander_title = f"✅ {safe_patient_name}"

        if r['status'] == STATUS_RECEIVED:
            if minutos_restantes > 5:
                status_display = f"🟢 Normal (Espera: {espera}m / Alvo: {sla_alvo}m)"
            elif minutos_restantes >= 0:
                status_display = f"🟡 Atenção (Espera: {espera}m / Alvo: {sla_alvo}m)"
                box_style = "border: 2px solid #F59E0B; background-color: #0f172a; color: white;"
            else:
                status_display = f"🔴 Atrasado (Atraso: {abs(minutos_restantes)}m)"
                box_style = "border: 2px solid #EF4444; background-color: #0f172a; color: white;"
        elif r['status'] == STATUS_ACKNOWLEDGED: status_display = f"🔵 Em Atendimento (Há {espera}m)"
        elif r['status'] == STATUS_ESCALATED: status_display = f"🟠 Com Médico (Há {espera}m)"
        elif r['status'] == STATUS_PENDING_NURSE: status_display = f"🟣 Executar Conduta (Há {espera}m)"

        if r['operational_priority'] == 1:
            box_style = "border: 2px solid #991B1B; background-color: #450a0a; color: white;"
            status_display = f"🚨 PRIORIDADE 1 <br> {status_display}"

        with st.expander(f"**{expander_title}**", expanded=False):
            st.markdown(f"<div style='padding:15px; border-radius:8px; margin-bottom:15px; {box_style}'><b>{safe_patient_name}</b> — {status_display}</div>", unsafe_allow_html=True)
            if r['status'] == STATUS_PENDING_NURSE: st.info(f"👨‍⚕️ Instrução Médica: **{html.escape(r['conduct'])}**")
            elif r['status'] != STATUS_ESCALATED:
                st.markdown(f"**Dor:** {r['pain']}/10 | **Evolução:** {html.escape(r['trend'])}")
                if r['transcript_original']: st.caption(f"📝 *\"{html.escape(r['transcript_original'])}\"*")
                audio_path = f"patient_audios/{r['report_uuid']}.wav"
                if os.path.exists(audio_path): st.audio(audio_path)

            st.divider()
            if r['status'] == STATUS_RECEIVED:
                if st.button("Assumir Responsabilidade", key=f"rev_{r['id']}", type="primary"):
                    ok, msg = DatabaseService.transition_internal_report(CLINICA_ATUAL_ID, r['report_uuid'], STATUS_ACKNOWLEDGED, OPERADOR_ID, ROLE_ATUAL, OPERADOR_ATUAL, "Assumiu acompanhamento.")
                    if ok: st.rerun()
                    else: st.error(msg)
            elif r['status'] in [STATUS_ACKNOWLEDGED, STATUS_PENDING_NURSE]:
                if r['assigned_user_id'] != OPERADOR_ID:
                    if ROLE_ATUAL in ["NURSE", "ADMIN"]:
                        with st.popover("🔄 Reatribuir Responsável"):
                            user_opts = [(u['id'], f"{u['name']} ({u['role']})") for u in active_users]
                            sel_user_id = st.selectbox("Novo responsável:", options=[u[0] for u in user_opts], format_func=lambda x: [u[1] for u in user_opts if u[0] == x][0])
                            if st.button("Confirmar", key=f"reassign_{r['id']}"):
                                ok, msg = DatabaseService.reassign_internal_report(CLINICA_ATUAL_ID, r['report_uuid'], OPERADOR_ID, ROLE_ATUAL, OPERADOR_ATUAL, sel_user_id)
                                if ok: st.rerun()
                                else: st.error(msg)
                else:
                    if r['status'] == STATUS_ACKNOWLEDGED:
                        c1, c2, c3 = st.columns(3)
                        with c1:
                            if r['patient_declared_emergency'] == 1: st.warning("⚠️ Exige Médico.")
                            else:
                                with st.popover("✅ Encerrar"):
                                    acao = st.selectbox("Ação", ["Dúvida Sanada Remotamente", "Agendamento Efetuado"])
                                    if st.button("Confirmar", key=f"res_{r['id']}", type="primary"):
                                        ok, msg = DatabaseService.transition_internal_report(CLINICA_ATUAL_ID, r['report_uuid'], STATUS_RESOLVED, OPERADOR_ID, ROLE_ATUAL, OPERADOR_ATUAL, f"Workflow Encerrado: [{acao}]", conduct=acao, resolution_source="TEAM")
                                        if ok: st.rerun()
                                        else: st.error(msg)
                        with c2:
                            with st.popover("💬 WhatsApp"):
                                custom_msg = st.text_area("Mensagem:", key=f"wpp_msg_{r['id']}")
                                if custom_msg.strip():
                                    link_wpp = f"https://wa.me/{r['patient_phone']}?text={urllib.parse.quote(custom_msg.strip())}"
                                    st.markdown(f'<a href="{link_wpp}" target="_blank" style="display:inline-block; background-color:#38bdf8; color:#0f172a; padding:8px 12px; border-radius:5px; text-decoration:none; font-weight:bold;">🚀 Abrir WhatsApp Web</a>', unsafe_allow_html=True)
                        with c3:
                            if ROLE_ATUAL in ["NURSE", "ADMIN"]:
                                with st.popover("🩺 Escalonar"):
                                    obs_medico = st.text_area("Observação curta:", key=f"obs_doc_{r['id']}")
                                    if st.button("Gerar Link", key=f"esc_{r['id']}", type="primary"):
                                        doc_tk = DatabaseService.escalate_to_doctor(CLINICA_ATUAL_ID, r['report_uuid'], OPERADOR_ID, OPERADOR_ATUAL, ROLE_ATUAL)
                                        if doc_tk:
                                            full_doc_url = f"{PUBLIC_BASE_URL}/?view=doctor&token={doc_tk}"
                                            st.success("Link gerado!")
                                            msg_final = f"🚨 *Avaliação Médica - VitaVoz*\n*Paciente:* {safe_patient_name}\n*Obs:* {obs_medico.strip()}\n\nAcesse: {full_doc_url}"
                                            st.markdown(f'<a href="https://wa.me/?text={urllib.parse.quote(msg_final)}" target="_blank" style="display:inline-block; background-color:#38bdf8; color:#0f172a; padding:8px 12px; border-radius:5px; text-decoration:none; font-weight:bold;">📲 Enviar</a>', unsafe_allow_html=True)
                                        else: st.error("Erro no escalonamento.")

                    elif r['status'] == STATUS_PENDING_NURSE:
                        c1, c2 = st.columns(2)
                        with c1:
                            if st.button("Confirmar Execução", key=f"resn_{r['id']}", type="primary"):
                                ok, msg = DatabaseService.transition_internal_report(CLINICA_ATUAL_ID, r['report_uuid'], STATUS_RESOLVED, OPERADOR_ID, ROLE_ATUAL, OPERADOR_ATUAL, "Equipe executou instrução.", resolution_source="TEAM_VIA_DOCTOR")
                                if ok: st.rerun()
                                else: st.error(msg)
                        with c2:
                            with st.popover("💬 Repassar Ordem"):
                                custom_msg = st.text_area("Mensagem:", key=f"wpp_doc_msg_{r['id']}")
                                if custom_msg.strip():
                                    link_wpp = f"https://wa.me/{r['patient_phone']}?text={urllib.parse.quote(custom_msg.strip())}"
                                    st.markdown(f'<a href="{link_wpp}" target="_blank" style="display:inline-block; background-color:#38bdf8; color:#0f172a; padding:8px 12px; border-radius:5px; text-decoration:none; font-weight:bold;">🚀 Abrir WhatsApp Web</a>', unsafe_allow_html=True)

elif menu == "🗂️ Histórico de Pacientes":
    require_role("NURSE", "ASSISTANT", "ADMIN")
    st.markdown("## 🗂️ Rastreabilidade Clínica")
    with get_db() as conn:
        patients = conn.cursor().execute("SELECT id, name, procedure_date, phone, allergies, revoked_at FROM patients WHERE clinic_id = ? AND active = 1 ORDER BY id DESC", (CLINICA_ATUAL_ID,)).fetchall()
    if not patients: st.info("Nenhum paciente cadastrado."); st.stop()
    patient_opts = {p['id']: f"{p['name']} ({format_iso_to_br_date(p['procedure_date'])})" for p in patients}
    sel_pid = st.selectbox("Selecione o Paciente:", options=list(patient_opts.keys()), format_func=lambda x: patient_opts[x])

    if sel_pid:
        p = [p for p in patients if p['id'] == sel_pid][0]
        if ROLE_ATUAL in ["NURSE", "ADMIN"]:
            st.caption(f"📞 Contato: {p['phone']} | Alergias: {p['allergies']}")
        st.markdown("##### Auditoria de Eventos (SHA-256)")
        with get_db() as conn:
            audits = conn.cursor().execute("SELECT * FROM audit_events WHERE patient_id = ? AND clinic_id = ? ORDER BY timestamp ASC", (p['id'], CLINICA_ATUAL_ID)).fetchall()
        for aud in audits: st.write(f"`{format_local_time(aud['timestamp'])}` — **{aud['action']}** ({aud['actor_name']}): {aud['details']}")

elif menu == "🔗 Cadastrar Paciente":
    require_role("NURSE", "ADMIN")
    st.markdown("## Novo Protocolo de Acompanhamento")
    with st.form("form_pac"):
        n = st.text_input("Identificação do Paciente")
        tel = st.text_input("Contato Telefônico (WhatsApp com DDD)")
        proc = st.text_input("Procedimento Realizado")
        d_proc = st.date_input("Data da Cirurgia")
        alergias = st.text_input("Alergias Sistêmicas (Opcional)")
        if st.form_submit_button("Gerar Acesso"):
            tel_normalized = normalize_phone(tel)
            if n and tel_normalized and proc and d_proc:
                raw_token = generate_secure_token()
                exp = (datetime.now(timezone.utc) + timedelta(days=15)).isoformat()
                with get_db() as conn:
                    c = conn.cursor()
                    c.execute("BEGIN IMMEDIATE")
                    c.execute("UPDATE patients SET active = 0, revoked_at = ? WHERE phone = ? AND clinic_id = ? AND revoked_at IS NULL", (utc_now().isoformat(), tel_normalized, CLINICA_ATUAL_ID))
                    c.execute("INSERT INTO patients (clinic_id, name, phone, procedure_name, procedure_date, allergies, token_hash, token_expires_at, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (CLINICA_ATUAL_ID, n, tel_normalized, proc, d_proc.strftime("%Y-%m-%d"), alergias, hash_token(raw_token), exp, utc_now().isoformat()))
                    conn.commit()
                st.success("Link gerado com sucesso!")
                patient_link = f"{PUBLIC_BASE_URL}/?view=portal&token={raw_token}"
                wpp_patient = f"https://wa.me/{tel_normalized}?text={urllib.parse.quote(f'Olá {n}, seu link do VitaVoz: {patient_link}')}"
                st.markdown(f'<a href="{wpp_patient}" target="_blank" style="display:inline-block; background-color:#38bdf8; color:#0f172a; padding:8px 12px; border-radius:5px; text-decoration:none; font-weight:bold;">💬 Enviar Link via WhatsApp</a>', unsafe_allow_html=True)
            else: st.error("Todos os campos básicos são obrigatórios.")

elif menu == "👥 Usuários e Acessos":
    require_role("ADMIN")
    st.markdown("## 👥 Gestão de Usuários da Clínica")
    with st.expander("➕ Cadastrar Novo Profissional"):
        with st.form("new_user_form"):
            new_name = st.text_input("Nome")
            new_username = st.text_input("Usuário (Login)")
            new_pwd = st.text_input("Senha (Mín. 12 carac.)", type="password")
            new_role = st.selectbox("Papel", ["NURSE", "ASSISTANT"])
            if st.form_submit_button("Criar Acesso", type="primary"):
                if len(new_pwd) >= 12 and new_name and new_username:
                    try:
                        with get_db() as conn:
                            c = conn.cursor()
                            c.execute("INSERT INTO users (clinic_id, name, username, password_hash, role) VALUES (?, ?, ?, ?, ?)", (CLINICA_ATUAL_ID, new_name, new_username.strip().lower(), hash_password(new_pwd), new_role))
                            conn.commit()
                        st.success(f"Usuário criado com sucesso.")
                        st.rerun()
                    except sqlite3.IntegrityError: st.error("Usuário já em uso.")
                else: st.error("Dados inválidos.")

    st.markdown("##### Equipe Cadastrada")
    with get_db() as conn: users_list = conn.cursor().execute("SELECT id, name, username, role, active FROM users WHERE clinic_id = ?", (CLINICA_ATUAL_ID,)).fetchall()
    for u in users_list:
        st.write(f"• **{u['name']}** (`{u['username']}`) — Papel: **{u['role']}** | Status: {'🟢 Ativo' if u['active']==1 else '🔴 Inativo'}")

elif menu == "🩺 Health Check Operacional":
    require_role("ADMIN")
    st.markdown("## 🩺 Observabilidade & Health Check")
    h_status = HealthService.get_status(CLINICA_ATUAL_ID)
    if h_status.get("healthy"):
        st.success("🟢 Infraestrutura Íntegra")
        st.write(f"Conexão Banco: {h_status['db_connection']} | Modo: {h_status['journal_mode']} | Versão Schema: {h_status['schema_version']}")
    else: st.error("🔴 Erro de Serviço")

elif menu == "⚙️ Segurança da Conta":
    st.markdown("## Segurança e Backups")
    if ROLE_ATUAL == "ADMIN":
        if st.button("Gerar Cópia do Banco (.enc)", type="primary"):
            try:
                enc_data = BackupService.generate_backup_encrypted(BACKUP_ENCRYPTION_KEY)
                st.download_button("📥 Baixar Backup", enc_data, file_name=f"backup_vitavoz_{int(time.time())}.enc", mime="application/octet-stream")
            except Exception as e: st.error(f"Erro: {e}")
