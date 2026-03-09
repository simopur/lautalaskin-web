import streamlit as st
from lautajako import nayta_lautajako
from jalakset import nayta_jalakset
from levyopt import nayta_levyoptimoija

st.set_page_config(page_title="Pakkauslaskin v4.9", layout="wide")

# Sivupalkin painike kenttien tyhjentämiseen
with st.sidebar:
    if st.button("🗑️ Tyhjennä kaikki kentät"):
        for key in st.session_state.keys():
            del st.session_state[key]
        st.rerun()

st.title("🏗️ Pakkausvalmistuksen Työkalut")

# Välilehdet
tab1, tab2, tab3 = st.tabs(["📊 Lautajako", "🪵 Jalakset", "📐 Levyoptimoija"])

with tab1:
    nayta_lautajako()

with tab2:
    nayta_jalakset()

with tab3:
    nayta_levyoptimoija()
