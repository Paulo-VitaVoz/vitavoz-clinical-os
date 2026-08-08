"""Analytics Cards UI Component."""
import streamlit as st
def render_kpis_header(summary):
    c1, c2, c3 = st.columns(3)
    with c1: st.metric("Pacientes Ativos", summary.total_pacientes_ativos)
    with c2: st.metric("Em Alerta", summary.pacientes_em_alerta)
    with c3: st.metric("Score Médio", f"{summary.media_vitascore}/100")
