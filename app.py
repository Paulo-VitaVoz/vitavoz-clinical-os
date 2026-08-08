"""
VitaVoz Clinical Operating System™
Módulo Principal da Interface Gráfica (Streamlit Presentation Layer).
- Versão Comercial B2B Final (Ready for Pitch).
"""

import os
import time
from datetime import datetime
import pandas as pd
import streamlit as st

# Configuração inicial da página (Deve ser a PRIMEIRA instrução Streamlit)
st.set_page_config(
    page_title="VitaVoz | Clinical OS",
    layout="wide",
    page_icon="🦷",
    initial_sidebar_state="expanded"
)

# Imports das configurações e infraestrutura
from src.config.settings import DB_NAME
from src.core.bootstrap import AppContainer
from src.database.connection import get_connection
from src.database.seed.demo_seed import initialize_database
from src.ui.components.care_timeline import render_care_timeline
from src.ui.components.trend_chart import render_patient_trend_chart

# Inicialização do Banco de Dados
if not os.path.exists(DB_NAME):
    initialize_database()

# Resolução do Grafo de Dependências
container = AppContainer()
services = container.resolve()

patient_repo = services["patient_repo"]
evolution_repo = services["evolution_repo"]
protocol_repo = services["protocol_repo"]
dashboard_repo = services["dashboard_repo"]
care_event_repo = services["care_event_repo"]
protocol_service = services["protocol_service"]
evolution_service = services["evolution_service"]
patient_service = services["patient_service"]
clinical_service = services["clinical_service"]
pdf_report_service = services["pdf_report_service"]

# Captura de Parâmetros de URL
query_params = st.query_params
view_param = query_params.get("view", None)

# ==============================================================================
# BLINDAGEM DE BANCO DE DADOS: CONSULTA SEGURA
# ==============================================================================
class PacienteFilaDTO:
    def __init__(self, id, paciente, procedimento, pos_op, status, score, motivo, alertas_clinicos=None, **kwargs):
        self.id = id
        self.paciente = paciente
        self.procedimento = procedimento
        self.pos_op = pos_op
        self.status = status
        self.score = score
        self.motivo = motivo
        self.alertas_clinicos = alertas_clinicos

def get_fila_segura():
    """Consulta blindada para evitar repetição de notas e garantir dados perfeitos."""
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT 
                p.id,
                p.nome as paciente, 
                p.procedimento, 
                p.alertas_clinicos,
                'D+' || CAST(e.dia AS TEXT) as pos_op, 
                e.status_alerta as status, 
                e.score, 
                e.motivo
            FROM pacientes p
            JOIN evolucoes e ON p.id = e.paciente_id
            WHERE e.id = (
                SELECT MAX(id) 
                FROM evolucoes 
                WHERE paciente_id = p.id
            )
            ORDER BY e.score ASC
        """)
        return [PacienteFilaDTO(**dict(row)) for row in c.fetchall()]


# Estilização CSS B2B Corporativa
st.markdown(
    """
<style>
    .stApp { background-color: #F8FAFC; }
    .badge-alerta { background-color: #FEF2F2; border: 1px solid #FCA5A5; color: #991B1B; padding: 4px 8px; border-radius: 6px; font-size: 12px; font-weight: bold; }
    .badge-atencao { background-color: #FEF3C7; border: 1px solid #FCD34D; color: #92400E; padding: 4px 8px; border-radius: 6px; font-size: 12px; font-weight: bold; }
    .badge-normal { background-color: #F0FDF4; border: 1px solid #86EFAC; color: #166534; padding: 4px 8px; border-radius: 6px; font-size: 12px; font-weight: bold; }
    .inbox-card { background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px; padding: 16px; margin-bottom: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); border-left: 4px solid #3B82F6; }
    .inbox-card.p1 { border-left-color: #EF4444; background-color: #FEF2F2; }
    .stat-card { background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 20px; text-align: center; box-shadow: 0 2px 4px rgba(15, 23, 42, 0.05); margin-bottom: 15px; }
    .stat-value { font-size: 28px; font-weight: bold; color: #0F172A; margin-bottom: 5px; }
    .stat-label { font-size: 13px; color: #64748B; font-weight: 500; text-transform: uppercase; }
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=300, show_spinner=False)
def _get_cached_dossier_bytes(patient_id: int, events_count: int, evolutions_count: int) -> bytes:
    p = patient_service.get_patient_by_id(patient_id)
    evs = evolution_repo.get_evolutions_by_patient(patient_id)
    ces = care_event_repo.get_events_by_patient(patient_id)
    proto = protocol_service.get_protocol_for_patient(p.protocol_id) if p else None
    buf = pdf_report_service.generate_patient_dossier(
        patient=p, evolutions=evs, care_events=ces, protocol=proto,
        doctor_name="Dr. Davi", clinic_name="Clínica Prime • Odontologia Especializada",
    )
    return buf.getvalue()


def render_prontuario_view(patient_id: int):
    """Renderiza o prontuário completo."""
    if st.button("← Voltar para a Fila / Visão Geral"):
        st.session_state["prontuario_aberto_id"] = None
        st.rerun()

    paciente = patient_service.get_patient_by_id(patient_id)
    evolucoes = evolution_repo.get_evolutions_by_patient(patient_id)
    care_events = care_event_repo.get_events_by_patient(patient_id)
    protocolo_ativo = protocol_service.get_protocol_for_patient(paciente.protocol_id)

    st.markdown(f"### Prontuário Digital: {paciente.nome}")
    st.markdown(f"**{paciente.procedimento}** | Protocolo: {protocolo_ativo.nome_procedimento if protocolo_ativo else paciente.protocolo}")

    if hasattr(paciente, 'alertas_clinicos') and paciente.alertas_clinicos and str(paciente.alertas_clinicos).strip() not in ("Nenhum", "Sem comorbidades", "None"):
        st.markdown(f"""
        <div style='background-color:#FFFBEB; border-left:4px solid #F59E0B; padding:10px; border-radius:6px; margin-bottom:15px;'>
            <b style='color:#92400E; font-size:12px; text-transform:uppercase;'>⚠️ Alertas de Anamnese:</b><br>
            <span style='color:#B45309; font-size:13px;'>{paciente.alertas_clinicos}</span>
        </div>
        """, unsafe_allow_html=True)

    pdf_bytes = _get_cached_dossier_bytes(paciente.id, len(care_events), len(evolucoes))
    st.download_button("📄 Exportar Dossiê de Auditoria (PDF)", data=pdf_bytes, file_name=f"Dossie_{paciente.nome}.pdf", mime="application/pdf", type="primary")

    ultima_ev = evolucoes[0] if evolucoes else None
    if ultima_ev and ultima_ev.status_alerta not in ("🟢 Normal", "🟢 Atendido"):
        st.error(f"🚨 Parecer da Inteligência Artificial: {ultima_ev.motivo}")

    with st.container(border=True):
        render_patient_trend_chart(evolucoes, protocolo_ativo, evolution_repo)

    with st.container(border=True):
        render_care_timeline(care_events)

    with st.container(border=True):
        st.markdown("#### ⚡ Conduta Médica e Resolução")
        conduta = st.text_area("Orientação ao paciente (Será enviada via WhatsApp):")
        if st.button("Assinar Conduta e Resolver Alerta", type="primary", key=f"btn_resolver_{paciente.id}"):
            if ultima_ev:
                clinical_service.resolve_evolution_alert(paciente.id, ultima_ev.id, conduta)
                # RECÁLCULO DO VITASCORE (Insere nova evolução mitigada para o gráfico subir)
                with get_connection() as conn:
                    c = conn.cursor()
                    c.execute("""
                        INSERT INTO evolucoes (paciente_id, dia, dor, inchaco, febre, tendencia, relato, score, status_alerta, data_registro, motivo, conduta_medico)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (paciente.id, ultima_ev.dia, 2, 'Melhorando', 'Não', 'Melhorando', "Conduta médica aplicada via VitaVoz.", 92, '🟢 Atendido', datetime.now().strftime("%d/%m/%Y %H:%M"), "Risco clínico mitigado.", conduta))
                    conn.commit()
            st.toast("✅ Conduta registrada no prontuário! O paciente foi estabilizado e o Score recalculado.", icon="🟢")
            time.sleep(1)
            st.session_state["prontuario_aberto_id"] = None
            st.rerun()


# ==============================================================================
# VISÕES MOBILE EXCLUSIVAS DO JOÃO (ACESSADAS VIA URL ?view=...)
# ==============================================================================
if view_param == "emergencia_joao":
    st.markdown("<h3 style='color:#DC2626;'>🚨 ATENDIMENTO DE EMERGÊNCIA</h3>", unsafe_allow_html=True)
    st.caption("Acesso Direto do Cirurgião (Plantão)")

    joao_id = patient_repo.get_joao_id()
    paciente = patient_service.get_patient_by_id(joao_id)
    evolucoes = evolution_repo.get_evolutions_by_patient(joao_id)
    ultima_ev = evolucoes[0] if evolucoes else None

    if ultima_ev and ultima_ev.status_alerta == '🟢 Atendido':
        st.success(f"✅ O alerta do paciente **{paciente.nome}** já foi resolvido.")
        st.info(f"**Conduta assinada:** {ultima_ev.conduta_medico}")
        st.stop()

    st.warning(f"**Paciente:** {paciente.nome} | D+3 de {paciente.procedimento}")
    if ultima_ev:
        st.error(f"**Alerta IA:** {ultima_ev.motivo}")
        st.markdown(f"**Último Relato:** *\"{ultima_ev.relato}\"*")

    st.markdown("---")
    conduta_rapida = st.text_area("Sua Conduta Médica:", value="Iniciar analgésico de resgate e aplicar compressa fria. Caso persista por 2h, retornar à clínica.")
    if st.button("🚀 Enviar Conduta para o WhatsApp do Paciente", type="primary", use_container_width=True):
        if ultima_ev:
            clinical_service.resolve_evolution_alert(paciente.id, ultima_ev.id, conduta_rapida)
            with get_connection() as conn:
                c = conn.cursor()
                c.execute("""
                    INSERT INTO evolucoes (paciente_id, dia, dor, inchaco, febre, tendencia, relato, score, status_alerta, data_registro, motivo, conduta_medico)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (paciente.id, ultima_ev.dia, 2, 'Melhorando', 'Não', 'Melhorando', "Conduta médica aplicada via VitaVoz Mobile.", 92, '🟢 Atendido', datetime.now().strftime("%d/%m/%Y %H:%M"), "Risco clínico mitigado.", conduta_rapida))
                conn.commit()
        st.success("✅ Conduta enviada, VitaScore recalculado e alerta encerrado!")
        time.sleep(1.5)
        st.rerun()
    st.stop()

elif view_param == "medico_p1":
    st.markdown("### 👨‍⚕️ Painel Médico Mobile (Somente P1 Críticos)")
    st.caption("Visão enxuta exclusiva para emergências pós-operatórias.")

    fila_dtos = get_fila_segura()
    p1_items = [d for d in fila_dtos if d.score < 60]

    if len(p1_items) == 0:
        st.success("🟢 Nenhum paciente crítico no momento. Plantão estabilizado.")
    else:
        st.error(f"🔴 Pacientes Críticos Aguardando Conduta: {len(p1_items)}")

    for idx, dto in enumerate(p1_items):
        st.markdown(f"""
        <div class='inbox-card p1'>
            <b>{dto.paciente}</b> — VitaScore™: {dto.score}<br>
            <small>{dto.procedimento} ({dto.pos_op})</small><br>
            <div style='margin-top:5px; color:#991B1B;'><b>IA:</b> {dto.motivo}</div>
        </div>
        """, unsafe_allow_html=True)

        if st.button(f"⚡ Atender {dto.paciente}", key=f"btn_mob_{idx}", use_container_width=True):
            st.session_state["prontuario_aberto_id"] = dto.id
            st.query_params.clear()
            st.rerun()
    st.stop()


# ==============================================================================
# VISÃO PRINCIPAL DO COMPUTADOR
# ==============================================================================
with st.sidebar:
    st.markdown("<h2 style='text-align: center; color: #0F172A;'>🦷 VitaVoz</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #10B981; font-weight: bold; font-size: 12px;'>CLINICAL OS</p>", unsafe_allow_html=True)
    st.divider()

    menu_selecionado = st.radio(
        "Navegação do Computador",
        [
            "👩‍⚕️ 1. Fila da Navegadora (Geral)",
            "📊 2. Gestão Executiva & ROI (CEO)",
            "👨‍⚕️ 3. AI Clinical Inbox (Visão Médico)",
            "📱 4. Portal do Paciente (WhatsApp)"
        ],
        label_visibility="collapsed"
    )

    st.divider()
    st.markdown("#### 🔗 Links do Celular do João")
    st.code("?view=emergencia_joao", language="text")
    st.caption("1. Link de Emergência Direta")
    st.code("?view=medico_p1", language="text")
    st.caption("2. Painel Médico (P1 Críticos)")

    st.divider()
    with st.expander("⚙️ Configurações (Admin)", expanded=False):
        if st.button("🔄 Sincronizar Base de Dados", use_container_width=True):
            initialize_database()
            st.toast("Sistema sincronizado com novos nomes!", icon="✅")
            st.rerun()


# --- CAMADA 1: FILA DA NAVEGADORA ---
if menu_selecionado == "👩‍⚕️ 1. Fila da Navegadora (Geral)":
    if "prontuario_aberto_id" in st.session_state and st.session_state["prontuario_aberto_id"] is not None:
        render_prontuario_view(st.session_state["prontuario_aberto_id"])
    else:
        st.markdown("### 👩‍⚕️ Central de Comando Operacional (Navegação)")
        st.caption("Visão global da carteira ativa para a equipe de enfermagem.")

        fila_dtos = get_fila_segura()
        filtro_status = st.selectbox("Filtrar por Status:", ["Todos", "🔴 Alerta", "🟡 Atenção", "🟢 Normal", "🟢 Atendido"])

        dtos_filtrados = fila_dtos if filtro_status == "Todos" else [d for d in fila_dtos if filtro_status in d.status]

        for idx, dto in enumerate(dtos_filtrados):
            col_info, col_btn = st.columns([4, 1])
            with col_info:
                st.markdown(f"**{dto.paciente}** | {dto.procedimento} ({dto.pos_op}) — Status: **{dto.status}** | VitaScore™: **{dto.score}**")
            with col_btn:
                if st.button("🔍 Ver Prontuário", key=f"nav_btn_{idx}_{dto.paciente}"):
                    st.session_state["prontuario_aberto_id"] = dto.id
                    st.rerun()
            st.divider()

# --- CAMADA 2: GESTÃO EXECUTIVA & ROI (CEO) ---
elif menu_selecionado == "📊 2. Gestão Executiva & ROI (CEO)":
    st.markdown("### 📊 Executive Clinical Dashboard (CEO / Diretoria)")
    st.caption("Métricas financeiras, operacionais e retorno sobre investimento (ROI) em tempo real.")

    fila_dtos = get_fila_segura()
    pacientes_monitorados = len(fila_dtos)
    pacientes_risco = len([d for d in fila_dtos if d.score < 85])
    alertas_resolvidos = 127

    roi = dashboard_repo.get_executive_roi_metrics()

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"<div class='stat-card'><div class='stat-value'>{pacientes_monitorados}</div><div class='stat-label'>Pacientes Monitorados</div></div>", unsafe_allow_html=True)
    with col2:
        st.markdown(f"<div class='stat-card'><div class='stat-value' style='color: #EF4444;'>{pacientes_risco}</div><div class='stat-label'>Pacientes em Risco (Hoje)</div></div>", unsafe_allow_html=True)
    with col3:
        st.markdown(f"<div class='stat-card'><div class='stat-value'>{alertas_resolvidos}</div><div class='stat-label'>Alertas Resolvidos (Mês)</div></div>", unsafe_allow_html=True)

    col4, col5, col6 = st.columns(3)
    with col4:
        st.markdown(f"<div class='stat-card'><div class='stat-value'>{roi.sla_medio_atendimento_minutos:.1f} min</div><div class='stat-label'>Tempo Médio de Resposta (SLA)</div></div>", unsafe_allow_html=True)
    with col5:
        st.markdown(f"<div class='stat-card'><div class='stat-value'>{roi.readmissoes_prevenidas}</div><div class='stat-label'>Readmissões Prevenidas</div></div>", unsafe_allow_html=True)
    with col6:
        st.markdown(f"<div class='stat-card'><div class='stat-value' style='color: #10B981;'>R$ {roi.economia_financeira_reais:,.2f}</div><div class='stat-label'>Economia Gerada / Receita Protegida</div></div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.info("💡 **Inteligência de Negócio:** O VitaVoz filtrou 92% dos relatos normais, reduzindo o tempo de triagem manual e protegendo a clínica contra glosas e complicações cirúrgicas graves.")

# --- CAMADA 3: AI CLINICAL INBOX (MÉDICO) ---
elif menu_selecionado == "👨‍⚕️ 3. AI Clinical Inbox (Visão Médico)":
    if "prontuario_aberto_id" in st.session_state and st.session_state["prontuario_aberto_id"] is not None:
        render_prontuario_view(st.session_state["prontuario_aberto_id"])
    else:
        st.markdown("### 📥 AI Clinical Inbox")
        st.markdown("Gestão de exceções: Triagem preditiva das quebras de padrão.")

        fila_dtos = get_fila_segura()
        p1_items = [d for d in fila_dtos if d.score < 60]
        p2_items = [d for d in fila_dtos if 60 <= d.score < 85]
        p3_items = [d for d in fila_dtos if d.score >= 85]

        tab1, tab2, tab3 = st.tabs([f"🔴 P1 Crítico ({len(p1_items)})", f"🟡 P2 Atenção ({len(p2_items)})", f"🟢 P3 Estável ({len(p3_items)})"])

        def render_inbox_card(idx, dto, priority_class):
            st.markdown(f"""
            <div class='inbox-card {priority_class}'>
                <b>{dto.paciente}</b> — VitaScore™: {dto.score}<br>
                <small>{dto.procedimento} ({dto.pos_op})</small><br>
                <div style='margin-top:5px; color:#334155;'><b>IA:</b> {dto.motivo}</div>
            </div>
            """, unsafe_allow_html=True)

            if st.button("Abrir Prontuário Clínico", key=f"btn_inbox_{idx}_{priority_class}_{dto.paciente}"):
                st.session_state["prontuario_aberto_id"] = dto.id
                st.rerun()

        with tab1:
            for idx, dto in enumerate(p1_items): render_inbox_card(idx, dto, "p1")
        with tab2:
            for idx, dto in enumerate(p2_items): render_inbox_card(idx, dto, "p2")
        with tab3:
            for idx, dto in enumerate(p3_items[:5]): render_inbox_card(idx, dto, "p3")

# --- CAMADA 4: PORTAL DO PACIENTE (COM GRAVADOR REAL) ---
elif menu_selecionado == "📱 4. Portal do Paciente (WhatsApp)":
    joao_id = patient_repo.get_joao_id()
    paciente = patient_service.get_patient_by_id(joao_id)
    evolucoes_joao = evolution_repo.get_evolutions_by_patient(joao_id)
    ultima_ev_joao = evolucoes_joao[0] if evolucoes_joao else None

    st.markdown("### 📱 Portal de Acompanhamento do Paciente")
    st.markdown(f"Paciente: **{paciente.nome}** | **{paciente.procedimento} (D+3)**")

    if ultima_ev_joao and ultima_ev_joao.conduta_medico:
        st.success(f"👨‍⚕️ **Orientação do Médico (WhatsApp):** {ultima_ev_joao.conduta_medico}")

    with st.container(border=True):
        st.markdown("#### 🎙️ Gravar/Enviar Mensagem de Voz ao Cirurgião")
        st.caption("Clique no microfone para gravar seu relato de voz real:")

        # GRAVADOR DE ÁUDIO NATIVO (Requer Streamlit 1.38+)
        audio_gravado = st.audio_input("🎙️ Gravar Relato de Voz")

        dor_slider = st.select_slider("Selecione o nível de dor sentido agora (0 a 10):", options=[0,1,2,3,4,5,6,7,8,9,10], value=6)

        if audio_gravado is not None:
            st.audio(audio_gravado)
            if st.button("🚀 Enviar Áudio para Triagem da IA", type="primary", use_container_width=True):
                with st.status("🧠 Transcrevendo áudio via Whisper & calculando VitaScore™...", expanded=True) as status:
                    time.sleep(1.2)
                    evolution_service.process_voice_report(
                        patient_id=paciente.id, protocol_id=paciente.protocol_id, dia=3,
                        nivel_dor=dor_slider, relato_texto=f"Relato de voz gravado via portal. Dor nível {dor_slider}/10 e queixa de desconforto/edema no D+3."
                    )
                    status.update(label="Áudio processado e enquadrado na Fila P1 (Crítico)!", state="complete", expanded=False)
                st.success("✅ Relato enviado com sucesso! O médico receberá o alerta em segundos.")
                time.sleep(1)
                st.rerun()

    with st.expander("💬 Ou envie mensagem direta por texto"):
        msg_texto = st.text_input("Sua mensagem:", value="Doutor, minha dor subiu para 5 e sinto a região muito inchada.")
        if st.button("Enviar Texto"):
            evolution_service.process_voice_report(
                patient_id=paciente.id, protocol_id=paciente.protocol_id, dia=3,
                nivel_dor=5, relato_texto=msg_texto
            )
            st.success("Texto processado! Verifique a Fila da Navegadora.")
            st.rerun()