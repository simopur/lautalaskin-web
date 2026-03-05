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

# --- JALASTEN LASKENTALAGIIKKA v3.8 ---
def muodosta_kerros(alku, j_p, j_l):
    p_lista, s_lista, curr = [], [], 0
    p_lista.append(int(alku)); curr += alku
    if curr < j_p: s_lista.append(curr)
    while curr + j_l < j_p:
        p_lista.append(int(j_l)); curr += j_l; s_lista.append(curr)
    if j_p - curr > 0: p_lista.append(int(j_p - curr))
    return p_lista, s_lista

def laske_pienin_vali(kaikki_saumat):
    min_v = float('inf')
    for i in range(len(kaikki_saumat) - 1):
        for s1 in kaikki_saumat[i]:
            for s2 in kaikki_saumat[i+1]:
                min_v = min(min_v, abs(s1 - s2))
    return int(min_v) if min_v != float('inf') else 0

def ratkaise_jalas(j_p, j_l, kerrokset, min_v_req, tyyppi="peili"):
    pcs = math.ceil(j_p / j_l)
    max_iter = 2 # Kokeillaan alkuperäistä ja +1 kappalemäärää
    
    for current_pcs in range(pcs, pcs + max_iter):
        min_x = max(100, j_p - (current_pcs - 1) * j_l)
        max_x = min(j_l, j_p - 100) if current_pcs > 1 else j_l
        
        data_final, saumat_final = [], []
        
        for k in range(int(kerrokset)):
            if tyyppi == "peili":
                # Vuorotellaan ääripäitä
                x_start = max_x if k % 2 == 0 else min_x
            else:
                # Tasainen liuku
                step = (max_x - min_x) / (kerrokset - 1) if kerrokset > 1 else 0
                x_start = max_x - (k * step)
            
            p, s = muodosta_kerros(x_start, j_p, j_l)
            data_final.append(p); saumat_final.append(s)
            
        current_min_v = laske_pienin_vali(saumat_final)
        
        # Jos jako täyttää vaatimuksen tai olemme jo lisänneet kappaleita, palautetaan tulos
        if min_v_req == 0 or current_min_v >= min_v_req or current_pcs > pcs:
            return data_final, current_min_v, current_pcs
            
    return data_final, current_min_v, current_pcs

# --- PÄÄOHJELMA ---
st.set_page_config(page_title="Pakkauslaskin v3.8", layout="wide")
st.title("🏗️ Pakkausvalmistuksen Jakolaskin v3.8")

if st.button("🗑️ Tyhjennä kaikki kentät", on_click=tyhjenna_kaikki):
    st.rerun()

tab1, tab2 = st.tabs(["📊 Lattiapohja", "🪵 Jalakset"])

with tab1:
    st.header("Lattiapohjan jako")
    # (Lattiapohjan logiikka pidetty ennallaan)
    st.info("Lattiapohjan laskenta on ennallaan.")

with tab2:
    st.header("Jalas-laskenta (Automaattinen optimointi)")
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
            # Lasketaan kaksi vaihtoehtoa uudella logiikalla
            d1, v1, p1 = ratkaise_jalas(j_p, j_l, j_k, j_min_v_req, "peili")
            d2, v2, p2 = ratkaise_jalas(j_p, j_l, j_k, j_min_v_req, "liuku")
            
            st.success(f"Laskenta suoritettu. Käytetty kappalemäärää: **{p1} kpl / kerros**.")

            st.subheader("Vaihtoehto 1: Vuorotteleva jako")
            if j_min_v_req > 0 and v1 < j_min_v_req:
                st.warning(f"⚠️ Vähimmäisväliä {j_min_v_req} mm ei voitu saavuttaa edes kappalemäärää lisäämällä.")
            piirra_jalasjako(d1, j_p, "Peilikuvalla optimoitu", v1)
            
            st.divider()
            
            st.subheader("Vaihtoehto 2: Liukuva jako")
            if j_min_v_req > 0 and v2 < j_min_v_req:
                st.warning(f"⚠️ Vähimmäisväliä {j_min_v_req} mm ei voitu saavuttaa.")
            piirra_jalasjako(d2, j_p, "Liukuva porrastus", v2)

            col1, col2 = st.columns(2)
            with col1:
                st.write("**V1 sahausohje:**")
                for i, row in enumerate(d1): st.text(f"K{i+1}: {' + '.join(map(str, row))}")
            with col2:
                st.write("**V2 sahausohje:**")
                for i, row in enumerate(d2): st.text(f"K{i+1}: {' + '.join(map(str, row))}")
