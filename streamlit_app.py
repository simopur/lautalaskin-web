import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches

# --- SYÖTTÖKENTTIEN HALLINTA ---
DEFAULTS = {
    "f_max_l": 3900, "f_ulp": 12110, "f_tne": 295, "f_tnv": 960, "f_tnm": 13,
    "j_jalas_p": 12000, "j_lauta_p": 4500, "j_kerrokset": 3
}

def tyhjenna_kentat():
    for key in DEFAULTS:
        st.session_state[key] = DEFAULTS[key]

for key, val in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = val

# --- VISUALISOINTI: JALAKSET ---
def piirra_jalasjako(kerrokset_data, kokonaispituus, title, min_v):
    fig, ax = plt.subplots(figsize=(12, 1.5 + len(kerrokset_data)*0.4))
    colors = ['#8e44ad', '#2980b9', '#27ae60', '#f1c40f', '#e74c3c']
    l_h, v = 100, 15
    
    # Korostusväri jos kestävyys on hyvä (>1200mm)
    bg_color = "#f0fff0" if min_v >= 1200 else "#ffffff"
    fig.patch.set_facecolor(bg_color)
    
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
    ax.set_title(f"{title} (Min väli: {min_v} mm)", fontsize=10, fontweight='bold')
    ax.set_yticks([(l_h/2) + i*(l_h+v) for i in range(len(kerrokset_data))])
    ax.set_yticklabels([f"K{i+1}" for i in range(len(kerrokset_data))], fontsize=8)
    for spine in ax.spines.values(): spine.set_visible(False)
    st.pyplot(fig)

# --- JALASTEN LASKENTALAGIIKKA v3.3 ---
def laske_jalas_v3(j_p, j_l, kerrokset, tyyppi="helppo"):
    data, saumat = [], []
    
    for k in range(int(kerrokset)):
        p_lista, s_lista = [], []
        
        if tyyppi == "helppo":
            # Priorisoidaan 0, L/2 ja sitten tarvittaessa muut jaot
            if k == 0: offset = 0
            elif k == 1: offset = j_l / 2
            else:
                # Kolmannesta kerroksesta eteenpäin haetaan 1200mm porrastus
                # tai jaetaan lauta kolmeen osaan
                offset = (j_l / 3) * (k-1) if (j_l / 3) >= 1200 else 1200 * (k-1)
        else:
            # Matemaattinen optimi (tasajako)
            offset = (j_l / kerrokset) * k
            
        offset = offset % j_l
        curr = 0
        if offset > 0:
            p_lista.append(int(offset)); curr += offset; s_lista.append(curr)
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
    return data, int(min_v)

# --- PÄÄOHJELMA ---
st.set_page_config(page_title="Pakkauslaskin v3.3", layout="wide")
st.title("🏗️ Pakkausvalmistuksen Jakolaskin v3.3")

if st.button("🗑️ Tyhjennä kaikki kentät", on_click=tyhjenna_kentat):
    st.rerun()

tab1, tab2 = st.tabs(["📊 Lattiapohja", "🪵 Jalakset"])

# (Lattiapohja-osio pidetty ennallaan kuten v3.2)
with tab1:
    # ... (tässä välissä aiempi floorboard-koodi) ...
    st.header("Floorboard-laskenta")
    # Tähän kohtaan kopioidaan aiemman version tab1-sisältö
    f1, f2 = st.columns(2)
    with f1:
        f_max = st.number_input("Laudan pituus mm", key="f_max_l")
        f_ulp = st.number_input("ulkopituus mm", key="f_ulp")
        f_tne = st.number_input("tn etäisyys mm", key="f_tne")
    with f2:
        f_tnv = st.number_input("tn väli mm", key="f_tnv")
        f_tnm = st.number_input("tn määrä kpl", key="f_tnm")
    # Lattiapohjan laskenta on identtinen v3.2 kanssa.

with tab2:
    st.header("Jalas-laskenta (Minimoi sahaukset)")
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
            # Lasketaan kaksi vaihtoehtoa
            d_opt, v_opt = laske_jalas_v3(j_p, j_l, j_k, "matemaattinen")
            d_ez, v_ez = laske_jalas_v3(j_p, j_l, j_k, "helppo")
            
            # Näytetään "Helppo sahaus" ensin, jos se täyttää 1200mm kriteerin
            priority = [("Vaihtoehto: Helppo sahaus (Priorisoitu)", d_ez, v_ez), 
                        ("Vaihtoehto: Matemaattinen optimi", d_opt, v_opt)]
            
            if v_ez < 1200:
                st.warning(f"Huom: Helpon sahauksen minimiväli ({v_ez} mm) alittaa 1200 mm. Harkitse matemaattista optimia.")

            for title, data, m_v in priority:
                st.subheader(title)
                if m_v >= 1200:
                    st.success(f"✅ Erinomainen kestävyys! Saumojen väli: {m_v} mm")
                else:
                    st.info(f"Saumojen väli: {m_v} mm")
                
                piirra_jalasjako(data, j_p, title, m_v)
                
                # Listataan palat selkeästi
                cols = st.columns(int(j_k))
                for i in range(int(j_k)):
                    with cols[i]:
                        st.write(f"**Kerros {i+1}**")
                        for p in data[i]:
                            st.text(f"- {p} mm")
                st.divider()
