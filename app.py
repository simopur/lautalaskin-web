import streamlit as st
# Tuodaan funktiot muista tiedostoista
from lautajako import nayta_lautajako
from jalakset import nayta_jalakset
from levyopt import nayta_levyoptimoija

st.set_page_config(page_title="Puutyökalut", layout="wide")

# Luodaan kolme välilehteä
tab1, tab2, tab3 = st.tabs(["🪵 Lautajako", "🦶 Jalasten laskenta", "📐 Levyoptimoija"])

with tab1:
    nayta_lautajako()

with tab2:
    nayta_jalakset()

with tab3:
    nayta_levyoptimoija()
