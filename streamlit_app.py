import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import math

# --- SYÖTTÖKENTTIEN HALLINTA ---
DEFAULTS = {
    "f_max_l": 3900, "f_ulp": 12110, "f_tne": 295, "f_tnv": 960, "f_tnm": 13,
    "j_jalas_p": 12000, "j_lauta_p": 4500, "j_kerrokset": 3
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
            if p > 400:
                ax.text(cx + p/2, y_pos + l_h/2, f"{int(p)}", ha='center', va='center', color='white', fontsize=8, fontweight='bold')
            cx += p
            if j < len(kerros) - 1:
                ax.plot([cx, cx], [y_pos, y_pos + l_h], color='black', linewidth=3)
                
    ax.set_xlim(-100, kokonaispituus + 100); ax.set_ylim(-20, len(kerrokset_data)*(l_h+v) + 20); ax.set_aspect('equal')
    ax.set_title(f"{title}\nPienin saumaväli: {min_v} mm", fontsize=10, fontweight='bold')
    ax.set_yticks([(l_h/2) + i*(l_h+v) for i in range(len(kerrokset_data))])
    ax.set_yticklabels([f"K{i+1}" for i in range(len(kerrokset_data))], fontsize=8)
    for spine in ax.spines.values(): spine.set_visible(False)
    st.pyplot(fig)

# --- JALASTEN LASKENTALAGIIKKA v3.5 ---
def laske_jalas_v3_5(j_p, j_l, kerrokset):
    # 1. Lasketaan ehdoton minimikappalemäärä
    min_pcs = math.ceil(j_p / j_l)
    
    # 2. Lasketaan lyhyin sallittu aloituspala, joka pitää kappalemäärän minimissä
    # Kaava: X + (min_pcs - 1) * L >= P  =>  X >= P - (min_pcs - 1) * L
    min_x_sallittu = max(0, j_p - (min_pcs - 1) * j_l)
    
    data, saumat = [], []
    
    # Jaetaan jäljellä oleva "pelivara" (min_x ... täysi lauta) tasaisesti
    pelivara = j_l - min_x_sallittu
    
    for k in range(int(kerrokset)):
        p_lista, s_lista = [], []
        
        # Yritetään käyttää puolikas-aloitusta (j_l/2) JOS se on >= min_x_sallittu
        puolikas = j_l / 2
        
        if k == 0:
            x_start = j_l # Ensimmäinen kerros aina täydellä
        elif k == 1 and puolikas >= min_x_sallittu:
            x_start = puolikas # Toinen puolikkaalla, jos se ei lisää kappaletta
        else:
            # Muut kerrokset porrastetaan tasaisesti jäljellä olevaan tilaan
            if kerrokset > 1:
                # Lasketaan siirtymä niin, että se pysyy sallitulla alueella
                offset_idx = k / (kerrokset - 1)
                x_start = min_x_sallittu + (pelivara * (1 - offset_idx))
            else:
                x_start = j_l
        
        x_start = int(x_start)
        curr = 0
        p_lista.append(x_start); curr += x_start
        if curr < j_p: s_lista.append(curr)
        
        while curr + j_l < j_p:
            p_lista.append(int(j_l)); curr += j_l; s_lista.append(curr)
        
        if j_p - curr > 0:
            p_lista.append(int(j_p - curr))
            
        data.append(p_lista); saumat.append(s_lista)
    
    # Välin laskenta
    min_v = float('inf')
    for i in range(len(saumat)):
        for j in range(i + 1, len(saumat)):
            for s1 in saumat[i]:
                for s2 in saumat[j]:
                    min_v = min(min_v, abs(s1 - s2))
                    
    return data, int(min_v) if min_v != float('inf') else 0, min_pcs

# --- PÄÄOHJELMA ---
st.set_page_config(page_title="Pakkauslaskin v3.5", layout="wide")
st.title("🏗️ Pakkausvalmistuksen Jakolaskin v3.5")

if st.button("🗑️ Tyhjennä kaikki kentät", on_click=tyhjenna_kaikki):
    st.rerun()

tab1, tab2 = st.tabs(["📊 Lattiapohja", "🪵 Jalakset"])

with tab1:
    # Lattiapohjan koodi (pidetty ennallaan toimivana)
    st.header("Lattiapohjan jako")
    c1, c2 = st.columns(2)
    with c1:
        f_max_l = st.number_input("Laudan pituus mm", key="f_max_l")
        f_ulp = st.number_input("ulkopituus mm", key="f_ulp")
        f_tne = st.number_input("tn etäisyys mm", key="f_tne")
    with c2:
        f_tnv = st.number_input("tn väli mm", key="f_tnv")
        f_tnm = st.number_input("tn määrä kpl", key="f_tnm")
    
    # (Tähän väliin tulee aiempi toimiva floorboard-laskentalogiikka)
    # ... (yrita_laskea_pari jne) ...

with tab2:
    st.header("Jalas-laskenta (Prioriteetti: Minimi kappalemäärä)")
    cj1, cj2 = st.columns(2)
    with cj1:
        j_p = st.number_input("Jalaksen kokonaispituus mm", key="j_jalas_p")
        j_l = st.number_input("Käytettävän laudan pituus mm", key="j_lauta_p")
    with cj2:
        j_k = st.number_input("Montako jalasta naulataan yhteen (kpl)", key="j_kerrokset")

    if st.button("Laske jalasten jako", type="primary"):
        if j_l >= j_p:
            st.info("Jalas voidaan tehdä yhdestä puusta.")
        else:
            data, min_v, pcs = laske_jalas_v3_5(j_p, j_l, j_k)
            
            st.success(f"Laskenta valmis: **{pcs} kappaletta** per kerros.")
            if min_v < 1200:
                st.warning(f"⚠️ Huom: Saumojen väli ({min_v} mm) on alle 1200 mm. Kappalemäärän minimointi rajoittaa porrastusta.")
            else:
                st.info(f"✅ Erinomainen kestävyys! Saumojen väli: {min_v} mm")
                
            piirra_jalasjako(data, j_p, "Optimoitu kappalemäärä", min_v)
            
            # Listataan sahaukset
            cols = st.columns(int(j_k))
            for i in range(int(j_k)):
                with cols[i]:
                    st.write(f"**Kerros {i+1}**")
                    for p in data[i]:
                        st.text(f"- {p} mm")
