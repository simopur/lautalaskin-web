import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches

# --- SYÖTTÖKENTTIEN HALLINTA ---
# Määritellään oletusarvot
DEFAULTS = {
    "f_max_l": 3900, "f_ulp": 12110, "f_tne": 295, "f_tnv": 960, "f_tnm": 13,
    "j_jalas_p": 12000, "j_lauta_p": 4500, "j_kerrokset": 3
}

def tyhjenna_kentat():
    for key in DEFAULTS:
        st.session_state[key] = DEFAULTS[key]

# Alustetaan session_state, jos sitä ei ole
for key, val in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = val

# --- VISUALISOINTI: LATTIAPOHJA ---
def piirra_lautajako(malli_a, malli_b, ulkopituus, nostot):
    fig, ax = plt.subplots(figsize=(12, 3)) 
    jaot = [malli_a, malli_b, malli_a, malli_b, malli_a]
    colors = ['#e67e22', '#d35400']
    l_w, v = 100, 10 
    kaikki_s = set(malli_a['saumat'])
    if malli_b: kaikki_s.update(malli_b['saumat'])
    for n in nostot:
        ax.axvline(x=n, color='gray', linestyle='--', linewidth=0.5, alpha=0.3)
    for i, jako in enumerate(jaot):
        if not jako: continue
        y_pos = i * (l_w + v)
        curr_x = 0
        for j, pala in enumerate(jako['palat']):
            rect = patches.Rectangle((curr_x, y_pos), pala, l_w, linewidth=0.5, edgecolor='black', facecolor=colors[i % 2], alpha=0.8)
            ax.add_patch(rect)
            if pala > 800:
                ax.text(curr_x + pala/2, y_pos + l_w/2, f"{int(pala)}", ha='center', va='center', color='white', fontsize=7, fontweight='bold')
            curr_x += pala
            if j < len(jako['palat']) - 1:
                ax.plot([curr_x, current_x := curr_x], [y_pos, y_pos + l_w], color='black', linewidth=2.5)
    ax.set_xlim(-200, ulkopituus + 200); ax.set_ylim(-50, 5 * (l_w + v) + 50); ax.set_aspect('equal')
    ax.set_xticks(nostot); labels = ax.set_xticklabels([str(int(n)) for n in nostot], fontsize=7, rotation=45)
    for i, n in enumerate(nostot):
        if n in kaikki_s: labels[i].set_fontweight('bold')
    ax.set_yticks([(l_w/2) + i*(l_w+v) for i in range(5)]); ax.set_yticklabels(["A", "B", "A", "B", "A"], fontsize=8)
    for spine in ax.spines.values(): spine.set_visible(False)
    st.pyplot(fig)

# --- VISUALISOINTI: JALAKSET ---
def piirra_jalasjako(kerrokset_data, kokonaispituus):
    fig, ax = plt.subplots(figsize=(12, 2 + len(kerrokset_data)*0.5))
    colors = ['#8e44ad', '#2980b9', '#27ae60', '#f1c40f']
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
    ax.set_xlim(-100, kokonaispituus + 100); ax.set_ylim(-50, len(kerrokset_data)*(l_h+v) + 20); ax.set_aspect('equal')
    ax.set_yticks([(l_h/2) + i*(l_h+v) for i in range(len(kerrokset_data))])
    ax.set_yticklabels([f"Kerros {i+1}" for i in range(len(kerrokset_data))])
    for spine in ax.spines.values(): spine.set_visible(False)
    st.pyplot(fig)

# --- LASKENTALAGIIKKA ---
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
st.set_page_config(page_title="Pakkauslaskin v3.1", layout="wide")
st.title("🏗️ Pakkausvalmistuksen Jakolaskin v3.1")

if st.button("🗑️ Tyhjennä kaikki kentät", on_click=tyhjenna_kentat):
    st.rerun()

tab1, tab2 = st.tabs(["📊 Lattiapohja", "🪵 Jalakset"])

with tab1:
    st.header("Floorboard-laskenta")
    c1, c2 = st.columns(2)
    with c1:
        f_max_l = st.number_input("Laudan pituus mm", key="f_max_l")
        f_ulp = st.number_input("ulkopituus mm", key="f_ulp")
        f_tne = st.number_input("tn etäisyys mm", key="f_tne")
    with c2:
        f_tnv = st.number_input("tn väli mm", key="f_tnv")
        f_tnm = st.number_input("tn määrä kpl", key="f_tnm")

    if st.button("Laske lattiapohja", type="primary"):
        nostot = [int(f_tne + (i * f_tnv)) for i in range(int(f_tnm)) if (int(f_tne + (i * f_tnv))) < f_ulp]
        all_p = [0] + nostot + [int(f_ulp)]
        sallitut = list(range(2, len(all_p) - 2))
        
        if nostot and abs(nostot[0] - (f_ulp - nostot[-1])) > 1: st.warning("⚠️ Jako ei symmetrinen!")
        
        m_a, m_b = yrita_laskea_pari(f_max_l, all_p, sallitut)
        if m_a and m_b:
            st.success("Laskenta valmis!")
            piirra_lautajako(m_a, m_b, f_ulp, nostot)
            colA, colB = st.columns(2)
            with colA: st.info(f"**MALLI A**\n\n{len(m_a['palat'])} kpl: {' + '.join(map(str, m_a['palat']))} mm")
            with colB: st.info(f"**MALLI B**\n\n{len(m_b['palat'])} kpl: {' + '.join(map(str, m_b['palat']))} mm")
        else:
            st.error("Jako ei mahdollinen. Käytä pidempää lautaa.")

with tab2:
    st.header("Jalas-laskenta")
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
            kerrokset_data = []
            kaikki_saumapaikat = []
            offset_step = j_l / j_k
            
            for k in range(int(j_k)):
                k_palat = []
                k_saumat = []
                offset = (k * offset_step) % j_l
                curr = 0
                if offset > 0:
                    k_palat.append(int(offset)); curr += offset; k_saumat.append(curr)
                while curr + j_l < j_p:
                    k_palat.append(int(j_l)); curr += j_l; k_saumat.append(curr)
                loppu = j_p - curr
                if loppu > 0: k_palat.append(int(loppu))
                
                kerrokset_data.append(k_palat)
                kaikki_saumapaikat.append(k_saumat)
            
            # Lasketaan pienin väli saumojen välillä
            min_vali = float('inf')
            for i in range(len(kaikki_saumapaikat)):
                for j in range(i + 1, len(kaikki_saumapaikat)):
                    for s1 in kaikki_saumapaikat[i]:
                        for s2 in kaikki_saumapaikat[j]:
                            vali = abs(s1 - s2)
                            if vali < min_vali: min_vali = vali
            
            st.success(f"Jalasten jako valmis. Pienin saumojen väli kerrosten välillä: **{int(min_vali)} mm**")
            piirra_jalasjako(kerrokset_data, j_p)
            for i, kd in enumerate(kerrokset_data):
                st.write(f"**Kerros {i+1}:** {' + '.join(map(str, kd))} mm")
