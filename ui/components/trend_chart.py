"""Trend Chart UI Component."""
import streamlit as st
import pandas as pd
def render_patient_trend_chart(evolucoes, protocolo, evo_repo):
    st.markdown("#### Tendência de Dor")
    if not evolucoes: st.info("Sem dados"); return

    dados = [{"Dia": f"D+{e.dia}", "Dor": e.dor} for e in sorted(evolucoes, key=lambda x: x.dia)]
    st.line_chart(pd.DataFrame(dados).set_index("Dia"))
