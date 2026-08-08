"""Care Timeline UI Component."""
import streamlit as st
def render_care_timeline(events):
    st.markdown("#### Trilha de Auditoria Clínica")
    for e in events:
        st.markdown(f"**{e.timestamp}** - {e.title} ({e.author})<br><small>{e.description}</small>", unsafe_allow_html=True)
