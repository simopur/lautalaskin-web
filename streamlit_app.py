import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches

# --- SESSION STATE KENTTIEN TYHJENNYSTÄ VARTEN ---
if 'cleared' not in st.session_state:
    st.session_state.cleared = False

def tyhjenna():
    for key in st.session_state.keys():
        if key != 'cleared':
            del st.session_state[key]
    st.session_state.cleared = True

# --- VISUALISOINTI: LATTIAPOHJA ---
def piirra_lautajako(malli_a, malli_b, ulkopituus, nostot):
    fig, ax = plt.subplots(figsize=(12, 3)) 
    jaot = [malli_a, malli_b, malli_a, malli_b, malli_a]
    colors = ['#e67e22', '#d35400']
    lauta_leveys, vali = 100, 10 
    kaikki_saumat = set(malli_a['saumat'])
    if malli_b: kaikki_saumat.update(malli_b['saumat'])
    for n in nostot:
        ax.axvline(x=n, color='gray', linestyle='--', linewidth=0.5, alpha=0.3)
    for i, jako in enumerate(jaot):
        if not jako: continue
        y_pos = i * (lauta_leveys + vali)
        current_x = 0
        for j, pala in enumerate(jako['palat']):
            rect = patches.Rectangle((current_x, y_pos), pala, lauta_leveys, linewidth=0.5, edgecolor='black', facecolor=colors[i % 2], alpha=0.8)
            ax.add_patch(rect)
            if pala > 800:
                ax.text(current_x + pala/2, y_pos + lauta_leveys/2, f"{int(pala)}", ha='center', va='center', color='white', fontsize=7, fontweight='bold')
            current_x += pala
            if j < len(jako['palat']) - 1:
                ax.plot([current_x, current_x], [y_pos, y_pos + lauta_leveys], color='black', linewidth=2.5)
    ax.set_xlim(-200, ulkopituus + 200); ax.set_ylim(-50, 5 * (lauta_leveys + vali) + 50); ax.set_aspect('equal')
    ax.set_xticks(nostot); labels = ax.set_xticklabels([str(int(n)) for n in nostot], fontsize=7, rotation=45)
    for i, n in enumerate(nostot):
        if n in kaikki_saumat: labels[i].set_fontweight('bold')
    ax.set_yticks([(lauta_leveys/2) + i*(lauta_leveys+vali) for i in range(5)]); ax.set_yticklabels(["A", "B", "A", "B", "A"], fontsize=8)
    for spine in ax.spines.values(): spine.set_visible(False)
    st.pyplot(fig)

# --- VISUALISOINTI: JALAKSET ---
def piirra_jalasjako(kerrokset_data, kokonaispituus):
    fig, ax = plt.subplots(figsize=(12, 2 + len(kerrokset_data)*0.5))
    colors = ['#8e44ad', '#2980b9', '#27ae60', '#f1c40f'] # Eri värit kerroksille
    l_h, vali = 100, 15
    for i, kerros in enumerate(kerrokset_data):
        y_pos = i * (l_h + vali)
        curr_x = 0
        for j, p in enumerate(kerros):
            rect = patches.Rectangle((curr_x, y_pos), p, l_h, linewidth=1, edgecolor='black', facecolor=colors[i % len(colors)], alpha=0.8)
            ax.add_patch(rect)
            if p > 400:
                ax.text(curr_x + p/2, y_pos + l_h/2, f"{int(p)}", ha='center', va='center', color='white', fontsize=8, fontweight='bold')
            curr_x += p
            if j < len(kerros) - 1:
                ax.plot([curr_x, curr_x], [y_pos, y_pos + l_h], color='black', linewidth=3)
    ax.set_xlim(-100, kokonaispituus + 100); ax.set_ylim(-50, len(kerrokset_data)*(l_h+vali) + 20); ax.set_aspect('equal')
    ax.set_title("Jalasten kerrosjako (saumojen limitys)", fontsize=10)
    ax.set_yticks([(l_h/2) + i*(l_h+vali) for i in range(len(kerrokset_data))])
    ax.set_yticklabels([f"Kerros {i+1}" for i in range(len(kerrokset_data))])
    for spine in ax.spines.values(): spine.set_visible(False)
    st.pyplot(fig)

# --- LASKENTALOGIIKKA: LATTIAPOHJA ---
def etsi_reitit(n_idx, reitti, max_l, pisteet, sallitut):
    dist = pisteet[-1] - pisteet[n_idx]
    if dist <= max_l:
        if n_idx != len(pisteet) - 2: return [reitti + [len(pisteet)-1]]
    res = []
    for s_idx in sallitut:
        if s_idx <= n_idx: continue
        pala = pisteet[s_idx] - pisteet[n_idx]
        if pala <= max_l and s_idx - n_idx >= 2:
            tulokset = etsi_reitit(s_idx, reitti + [s_idx], max_l, pisteet, sallitut)
            if tulokset: res.extend(tulokset)
    return res

def yrita_laskea_pari(m_l, all_p, sallitut):
    reitit = etsi_reitit(0, [0], m_l, all_p, sallitut)
    if not reitit: return None, None
    valmiit = []
    for r in reitit:
        p = [all_p[r[j+1]] - all_p[r[j]] for j in range(len(r)-1)]
        s = [all_p[idx] for idx in r[1:-1]]
        sc = sum(x**2 for x in p)
        valmiit.append({'palat': p, 'saumat': s, 'idx': r, 'l_score': sc})
    valmiit.sort(key=lambda x: (len(x['palat']), -x['l_score']))
    m_a = valmiit[0]; m_b = None; a_set = set(m_a['idx'][1:-1])
    for ehd in valmiit:
        b_idx = ehd['idx'][1:-1]
        if not b_idx: continue
        safe = True
        for b in b_idx:
            if b in a_set or (b-1) in a_set or (b+1) in a_set: safe = False; break
        if safe: m_b = ehd; break
    return m_a, m_b

# --- PÄÄOHJELMA ---
st.set_page_config(page_title="Lautalaskin v3.0", layout="wide")
st.title("🏗️ Pakkausvalmistuksen Jakolaskin v3.0")

# Tyhjennyspainike sivupalkissa tai ylhäällä
if st.button("🗑️ Tyhjennä kaikki kentät"):
    tyhjenna()
    st.rerun()

tab1, tab2 = st.tabs(["📊 Lattiapohjan jako", "🪵 Jalasten jako"])

with tab1:
    st.header("Floorboard-laskenta")
    c1, c2 = st.columns(2)
    with c1:
        m_l = st.number_input("Laudan pituus mm", value=3900, key="f1")
        ulp_p = st.number_input("ulkopituus mm", value=12110, key="f2")
        tn_e = st.number_input("tn etäisyys mm", value=295, key="f3")
    with c2:
        tn_v = st.number_input("tn väli mm", value=960, key="f4")
        tn_m = st.number_input("tn määrä kpl", value=13, key="f5")

    if st.button("Laske lattiapohja", type="primary"):
        nostot = [int(tn_e + (i * tn_v)) for i in range(int(tn_m)) if (int(tn_e + (i * tn_v))) < ulp_p]
        all_p = [0] + nostot + [int(ulp_p)]
        sallitut = list(range(2, len(all_p) - 2))
        
        if nostot and abs(nostot[0] - (ulp_p - nostot[-1])) > 1: st.warning("⚠️ Jako ei symmetrinen!")
        
        m_a, m_b = yrita_laskea_pari(m_l, all_p, sallitut)
        if m_a and m_b:
            st.success("Laskenta valmis!")
            piirra_lautajako(m_a, m_b, ulp_p, nostot)
            colA, colB = st.columns(2)
            with colA: st.info(f"**MALLI A**\n\n{len(m_a['palat'])} kpl: {' + '.join(map(str, m_a['palat']))} mm")
            with colB: st.info(f"**MALLI B**\n\n{len(m_b['palat'])} kpl: {' + '.join(map(str, m_b['palat']))} mm")
        else:
            st.error("Jako ei mahdollinen. Lisää nosto tai käytä pidempää lautaa.")

with tab2:
    st.header("Jalas-laskenta")
    st.write("Laskee optimaalisen limityksen päällekkäin naulattaville jalaksille.")
    cj1, cj2 = st.columns(2)
    with cj1:
        jalas_pituus = st.number_input("Jalaksen kokonaispituus mm", value=12000, key="j1")
        j_lauta_pituus = st.number_input("Käytettävän laudan pituus mm", value=4500, key="j2")
    with cj2:
        kerrokset = st.number_input("Montako jalasta naulataan yhteen (kpl)", value=3, min_value=1, max_value=6, key="j3")

    if st.button("Laske jalasten jako", type="primary"):
        if j_lauta_pituus >= jalas_pituus:
            st.info("Jalas voidaan tehdä yhdestä puusta. Ei tarvetta jaolle.")
        else:
            kerrokset_data = []
            # Optimaalinen siirtymä (offset) on laudan pituus jaettuna kerrosten määrällä
            offset_step = j_lauta_pituus / kerrokset
            
            for k in range(int(kerrokset)):
                kerros_palat = []
                offset = (k * offset_step) % j_lauta_pituus
                
                curr = 0
                # Ensimmäinen pala (offset)
                if offset > 0:
                    kerros_palat.append(int(offset))
                    curr += offset
                
                # Täydet laudat
                while curr + j_lauta_pituus < jalas_pituus:
                    kerros_palat.append(int(j_lauta_pituus))
                    curr += j_lauta_pituus
                
                # Viimeinen pala
                loppu = jalas_pituus - curr
                if loppu > 0:
                    kerros_palat.append(int(loppu))
                
                kerrokset_data.append(kerros_palat)
            
            st.success("Jalasten limitys laskettu!")
            piirra_jalasjako(kerrokset_data, jalas_pituus)
            
            for i, kd in enumerate(kerrokset_data):
                st.write(f"**Kerros {i+1}:** {' + '.join(map(str, kd))} mm")
