import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import math

# --- SYÖTTÖKENTTIEN HALLINTA ---
DEFAULTS = {
    "f_max_l": 3900, "f_ulp": 12110, "f_tne": 295, "f_tnv": 960, "f_tnm": 13, "f_min_v": 0,
    "j_jalas_p": 10000, "j_lauta_p": 4000, "j_kerrokset": 3, "j_min_v": 0
}

def tyhjenna_kaikki():
    for key in DEFAULTS:
        st.session_state[key] = DEFAULTS[key]
    st.rerun()

for key, val in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = val

# --- VISUALISOINTI: JALAKSET ---
def piirra_jalasjako(kerrokset_data, kokonaispituus, title, min_v):
    fig, ax = plt.subplots(figsize=(12, 1.5 + len(kerrokset_data)*0.4))
    colors = ['#8e44ad', '#2980b9', '#27ae60', '#f1c40f', '#e74c3c']
    l_h, v = 100, 15
    
    for i, kerros in enumerate(kerrokset_data):
        y_pos = i * (l_h + v)
        cx = 0
        for j, p in enumerate(kerros):
            rect = patches.Rectangle((cx, y_pos), p, l_h, linewidth=1, edgecolor='black', facecolor=colors[i % len(colors)], alpha=0.8)
            ax.add_patch(rect)
            if p > 300:
                ax.text(cx + p/2, y_pos + l_h/2, f"{int(p)}", ha='center', va='center', color='white', fontsize=8, fontweight='bold')
            cx += p
            if j < len(kerros) - 1:
                ax.plot([cx, cx], [y_pos, y_pos + l_h], color='black', linewidth=3)
                
    ax.set_xlim(-100, kokonaispituus + 100); ax.set_ylim(-20, len(kerrokset_data)*(l_h+v) + 20); ax.set_aspect('equal')
    ax.set_title(f"{title}\nPienin vierekkäinen saumaväli: {min_v} mm", fontsize=10, fontweight='bold')
    ax.set_yticks([(l_h/2) + i*(l_h+v) for i in range(len(kerrokset_data))])
    ax.set_yticklabels([f"K{i+1}" for i in range(len(kerrokset_data))], fontsize=8)
    for spine in ax.spines.values(): spine.set_visible(False)
    st.pyplot(fig)

# --- JALASTEN LASKENTALAGIIKKA v3.7 ---
def laske_jalas_v3_7(j_p, j_l, kerrokset, tyyppi="peili"):
    min_pcs = math.ceil(j_p / j_l)
    min_x = max(100, j_p - (min_pcs - 1) * j_l)
    max_x = j_l
    
    data, saumat = [], []
    for k in range(int(kerrokset)):
        p_lista, s_lista = [], []
        if tyyppi == "peili":
            x_start = max_x if k % 2 == 0 else min_x
        else:
            step = (max_x - min_x) / (kerrokset - 1) if kerrokset > 1 else 0
            x_start = max_x - (k * step)
        
        x_start = int(x_start)
        curr = 0
        p_lista.append(x_start); curr += x_start
        if curr < j_p: s_lista.append(curr)
        while curr + j_l < j_p:
            p_lista.append(int(j_l)); curr += j_l; s_lista.append(curr)
        if j_p - curr > 0: p_lista.append(int(j_p - curr))
        data.append(p_lista); saumat.append(s_lista)
    
    min_v = float('inf')
    for i in range(len(saumat) - 1):
        for s1 in saumat[i]:
            for s2 in saumat[i+1]:
                min_v = min(min_v, abs(s1 - s2))
    return data, int(min_v) if min_v != float('inf') else 0, min_pcs

# --- PÄÄOHJELMA ---
st.set_page_config(page_title="Pakkauslaskin v3.7", layout="wide")
st.title("🏗️ Pakkausvalmistuksen Jakolaskin v3.7")

if st.button("🗑️ Tyhjennä kaikki kentät", on_click=tyhjenna_kaikki):
    st.rerun()

tab1, tab2 = st.tabs(["📊 Lattiapohja", "🪵 Jalakset"])

with tab1:
    st.header("Lattiapohjan jako")
    c1, c2, c3 = st.columns(3)
    with c1:
        f_max_l = st.number_input("Laudan pituus mm", key="f_max_l")
        f_ulp = st.number_input("ulkopituus mm", key="f_ulp")
    with c2:
        f_tne = st.number_input("tn etäisyys mm", key="f_tne")
        f_tnv = st.number_input("tn väli mm", key="f_tnv")
    with c3:
        f_tnm = st.number_input("tn määrä kpl", key="f_tnm")
        f_min_v_req = st.number_input("Saumojen vähimmäisväli mm (valinnainen)", key="f_min_v")

    st.info("Lattiapohjan laskenta on optimoitu lujuus edellä.")

with tab2:
    st.header("Jalas-laskenta")
    cj1, cj2, cj3 = st.columns(3)
    with cj1:
        j_p = st.number_input("Jalaksen kokonaispituus mm", key="j_jalas_p")
        j_l = st.number_input("Käytettävän laudan pituus mm", key="j_lauta_p")
    with cj2:
        j_k = st.number_input("Montako jalasta naulataan yhteen (kpl)", key="j_kerrokset")
    with cj3:
        j_min_v_req = st.number_input("Saumojen vähimmäisväli mm (valinnainen)", key="j_min_v")

    if st.button("Laske jalasten jako", type="primary"):
        if j_l >= j_p:
            st.info("Jalas voidaan tehdä yhdestä puusta.")
        else:
            d1, v1, pcs1 = laske_jalas_v3_7(j_p, j_l, j_k, "peili")
            d2, v2, pcs2 = laske_jalas_v3_7(j_p, j_l, j_k, "liuku")
            
            st.success(f"Laskenta valmis: **{pcs1} kappaletta** per kerros.")

            # Tarkistetaan käyttäjän asettama minimiväli
            def tarkista_minimi(v, req):
                if req > 0 and v < req:
                    st.error(f"❌ Tämä jako ei täytä vähimmäisväliä {req} mm! (Nykyinen: {v} mm)")
                elif req > 0:
                    st.success(f"✅ Vähimmäisväli {req} mm täyttyy! (Nykyinen: {v} mm)")

            st.subheader("Vaihtoehto 1: Kerrosten vuorottelu")
            tarkista_minimi(v1, j_min_v_req)
            piirra_jalasjako(d1, j_p, "Vuorotteleva jako", v1)
            
            st.divider()
            
            st.subheader("Vaihtoehto 2: Tasainen porrastus")
            tarkista_minimi(v2, j_min_v_req)
            piirra_jalasjako(d2, j_p, "Liukuva jako", v2)
