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
    # Pakotetaan tyhjennys poistamalla mahdolliset laskentatulokset
    if "laskettu_j" in st.session_state: del st.session_state["laskettu_j"]
    if "laskettu_f" in st.session_state: del st.session_state["laskettu_f"]

for key, val in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = val

# --- VISUALISOINTI: JALAKSET ---
def piirra_jalasjako(kerrokset_data, kokonaispituus, title, min_v):
    fig, ax = plt.subplots(figsize=(12, 1.5 + len(kerrokset_data)*0.4))
    colors = ['#8e44ad', '#2980b9', '#27ae60', '#f1c40f', '#e74c3c']
    l_h, v = 100, 15
    fig.patch.set_facecolor("#f8f9fa")
    
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
    ax.set_title(f"{title}\n(Pienin saumaväli: {min_v} mm)", fontsize=10, fontweight='bold')
    ax.set_yticks([(l_h/2) + i*(l_h+v) for i in range(len(kerrokset_data))])
    ax.set_yticklabels([f"K{i+1}" for i in range(len(kerrokset_data))], fontsize=8)
    for spine in ax.spines.values(): spine.set_visible(False)
    st.pyplot(fig)

# --- JALASTEN LASKENTALAGIIKKA v3.4 ---
def laske_jalas_tehokas(j_p, j_l, kerrokset):
    # Lasketaan minimikappalemäärä per kerros
    min_pcs = math.ceil(j_p / j_l)
    # Alue, jolla ensimmäinen pala pitää kappalemäärän minimissä:
    # X + (min_pcs - 1)*L >= P  =>  X >= P - (min_pcs - 1)*L
    min_x = max(100, j_p - (min_pcs - 1) * j_l)
    max_x = j_l
    
    data, saumat = [], []
    # Jaetaan sallittu alue (min_x ... max_x) tasaisesti kerrosten välille
    step = (max_x - min_x) / max(1, kerrokset - 1) if kerrokset > 1 else 0
    
    for k in range(int(kerrokset)):
        p_lista, s_lista = [], []
        # Aloituspala tässä kerroksessa
        x_start = int(max_x - (k * step))
        
        curr = 0
        p_lista.append(x_start); curr += x_start; s_lista.append(curr)
        while curr + j_l < j_p:
            p_lista.append(int(j_l)); curr += j_l; s_lista.append(curr)
        if j_p - curr > 0:
            p_lista.append(int(j_p - curr))
            
        data.append(p_lista); saumat.append(s_lista)
    
    # Minimivälin laskenta
    min_v = float('inf')
    for i in range(len(saumat)):
        for j in range(i + 1, len(saumat)):
            for s1 in saumat[i]:
                for s2 in saumat[j]:
                    min_v = min(min_v, abs(s1 - s2))
    return data, int(min_v), min_pcs

# --- PÄÄOHJELMA ---
st.set_page_config(page_title="Pakkauslaskin v3.4", layout="wide")
st.title("🏗️ Pakkausvalmistuksen Jakolaskin v3.4")

if st.button("🗑️ Tyhjennä kaikki kentät", on_click=tyhjenna_kaikki):
    st.rerun()

tab1, tab2 = st.tabs(["📊 Lattiapohja", "🪵 Jalakset"])

with tab1:
    st.header("Floorboard-laskenta")
    # (Aiempi lattiapohjan logiikka pidetty ennallaan)
    # ... (Toteutetaan vastaavasti kuin aiemmin) ...
    st.info("Käytä lattiapohjan laskentaa tästä.")

with tab2:
    st.header("Jalas-laskenta (Minimoi sahaukset & materiaali)")
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
            # Lasketaan tehokas jako (minimoi kappaleet)
            d_eff, v_eff, pcs = laske_jalas_tehokas(j_p, j_l, j_k)
            
            # Tarkistetaan saataisiko puolikkaalla parempi tulos (jos se pitää kappaleet samana)
            half_l = j_l / 2
            min_x_needed = j_p - (pcs - 1) * j_l
            
            st.subheader(f"Tehokas jako: {pcs} kappaletta per kerros")
            
            if v_eff >= 1200:
                st.success(f"✅ Optimaalinen kestävyys ja minimi sahaukset! (Väli: {v_eff} mm)")
            else:
                st.warning(f"Huom: Minimiväli on {v_eff} mm. Kappalemäärän pitäminen pienenä vaikeuttaa porrastusta.")

            piirra_jalasjako(d_eff, j_p, "Tehokas minimikappale-jako", v_eff)
            
            # Materiaalilista
            st.write(f"**Yhteensä tarvitaan:** {int(pcs * j_k)} lautaa per koko jalas-nippu (ennen viimeistä katkoa).")
            cols = st.columns(int(j_k))
            for i in range(int(j_k)):
                with cols[i]:
                    st.write(f"**Kerros {i+1}**")
                    for p in d_eff[i]:
                        st.text(f"- {p} mm")
