import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import math

# --- SYÖTTÖKENTTIEN HALLINTA ---
DEFAULTS = {
    "f_max_l": 5100, "f_ulp": 12110, "f_tne": 295, "f_tnv": 960, "f_tnm": 13,
    "j_jalas_p": 10000, "j_lauta_p": 4000, "j_kerrokset": 3
}

def tyhjenna_kaikki():
    for key in DEFAULTS:
        st.session_state[key] = DEFAULTS[key]
    st.rerun()

for key, val in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = val

# --- VISUALISOINTI ---
def piirra_lautajako(malli_a, malli_b, ulkopituus, nostot):
    fig, ax = plt.subplots(figsize=(12, 3)) 
    jaot = [malli_a, malli_b, malli_a, malli_b, malli_a]
    l_w, v = 100, 10 
    kaikki_s = set(malli_a['saumat'])
    if malli_b: kaikki_s.update(malli_b['saumat'])
    for n in nostot:
        ax.axvline(x=n, color='gray', linestyle='--', linewidth=0.5, alpha=0.3)
    for i, jako in enumerate(jaot):
        if not jako: continue
        y_pos = i * (l_w + v)
        cx = 0
        for j, pala in enumerate(jako['palat']):
            rect = patches.Rectangle((cx, y_pos), pala, l_w, linewidth=0.5, edgecolor='black', 
                                     facecolor='#e67e22' if i%2==0 else '#d35400', alpha=0.8)
            ax.add_patch(rect)
            if pala > 800:
                ax.text(cx + pala/2, y_pos + l_w/2, f"{int(pala)}", ha='center', va='center', color='white', fontsize=7, fontweight='bold')
            cx += pala
            if j < len(jako['palat']) - 1:
                ax.plot([cx, cx], [y_pos, y_pos + l_w], color='black', linewidth=2.5)
    ax.set_xlim(-200, ulkopituus + 200); ax.set_ylim(-50, 5 * (l_w + v) + 50); ax.set_aspect('equal')
    ax.set_xticks(nostot); labels = ax.set_xticklabels([str(int(n)) for n in nostot], fontsize=7, rotation=45)
    for i, n in enumerate(nostot):
        if n in kaikki_s: labels[i].set_fontweight('bold')
    ax.set_yticks([(l_w/2) + k*(l_w+v) for k in range(5)])
    ax.set_yticklabels(["A", "B", "A", "B", "A"], fontsize=8)
    for spine in ax.spines.values(): spine.set_visible(False)
    st.pyplot(fig)

def piirra_jalasjako(kerrokset_data, kokonaispituus, min_v):
    fig, ax = plt.subplots(figsize=(12, 1.5 + len(kerrokset_data)*0.5))
    colors = ['#8e44ad', '#2980b9', '#27ae60']
    l_h, v = 100, 15
    for i, kerros in enumerate(kerrokset_data):
        y_pos = i * (l_h + v)
        cx = 0
        for j, p in enumerate(kerros):
            rect = patches.Rectangle((cx, y_pos), p, l_h, linewidth=1, edgecolor='black', facecolor=colors[i % 3], alpha=0.8)
            ax.add_patch(rect)
            if p > 300:
                ax.text(cx + p/2, y_pos + l_h/2, f"{int(p)}", ha='center', va='center', color='white', fontsize=8, fontweight='bold')
            cx += p
            if j < len(kerros) - 1:
                ax.plot([cx, cx], [y_pos, y_pos + l_h], color='black', linewidth=3)
    ax.set_xlim(-100, kokonaispituus + 100); ax.set_ylim(-20, len(kerrokset_data)*(l_h+v) + 20); ax.set_aspect('equal')
    ax.set_title(f"Jalasrakenne (Pienin vierekkäinen saumaväli: {min_v} mm)", fontsize=10, fontweight='bold')
    ax.set_yticks([(l_h/2) + k*(l_h+v) for k in range(len(kerrokset_data))])
    ax.set_yticklabels([f"K{k+1}" for k in range(len(kerrokset_data))], fontsize=8)
    for spine in ax.spines.values(): spine.set_visible(False)
    st.pyplot(fig)

# --- LASKENTALOGIIKKA: LATTIAPOHJA ---
def etsi_reitit_f(n_idx, reitti, max_l, pisteet, sallitut):
    if pisteet[-1] - pisteet[n_idx] <= max_l:
        if n_idx != len(pisteet) - 2: return [reitti + [len(pisteet)-1]]
    res = []
    for s_idx in sallitut:
        if s_idx > n_idx:
            pala = pisteet[s_idx] - pisteet[n_idx]
            if pala <= max_l and s_idx - n_idx >= 2:
                t = etsi_reitit_f(s_idx, reitti + [s_idx], max_l, pisteet, sallitut)
                if t: res.extend(t)
    return res

def yrita_laskea_pari_f(m_l, all_p, sallitut):
    reitit = etsi_reitit_f(0, [0], m_l, all_p, sallitut)
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
        if b_idx and all(b not in a_set and b-1 not in a_set and b+1 not in a_set for b in b_idx):
            m_b = ehd; break
    return m_a, m_b

# --- LASKENTALOGIIKKA: JALAKSET ---
def muodosta_kerros_j(alku, j_p, j_l):
    p_l, s_l, curr = [], [], 0
    p_l.append(int(alku)); curr += alku
    if curr < j_p: s_l.append(curr)
    while curr + j_l < j_p:
        p_l.append(int(j_l)); curr += j_l; s_l.append(curr)
    if j_p - curr > 0: p_l.append(int(j_p - curr))
    return p_l, s_l

def laske_jalas_ohjeistettu(j_p, j_l, kerrokset):
    data, saumat = [], []
    rem = j_p % j_l
    
    # K1: Täydet kanget ensin
    k1_p, k1_s = muodosta_kerros_j(j_l, j_p, j_l)
    data.append(k1_p); saumat.append(k1_s)
    
    # K2: Aloitus puolikkaalla kankella
    if kerrokset >= 2:
        k2_p, k2_s = muodosta_kerros_j(j_l/2, j_p, j_l)
        data.append(k2_p); saumat.append(k2_s)
        
    # K3: Tasattu jako (L+Rem)/2
    if kerrokset >= 3:
        tasattu = (j_l + rem) / 2 if rem > 0 else j_l/2
        k3_p, k3_s = muodosta_kerros_j(tasattu, j_p, j_l)
        data.append(k3_p); saumat.append(k3_s)
        
    min_v = float('inf')
    for i in range(len(saumat)-1):
        for s1 in saumat[i]:
            for s2 in saumat[i+1]:
                min_v = min(min_v, abs(s1 - s2))
    return data, int(min_v) if min_v != float('inf') else 0

# --- KÄYTTÖLIITTYMÄ ---
st.set_page_config(page_title="Pakkauslaskin v4.4", layout="wide")
st.title("🏗️ Pakkausvalmistuksen Jakolaskin v4.4")

if st.button("🗑️ Tyhjennä kaikki kentät", on_click=tyhjenna_kaikki):
    st.rerun()

t1, t2 = st.tabs(["📊 Lattiapohja", "🪵 Jalakset"])

with t1:
    st.header("Lattiapohjan jako")
    c1, c2 = st.columns(2)
    with c1:
        f_max = st.number_input("Laudan pituus mm", key="f_max_l")
        f_ulp = st.number_input("ulkopituus mm", key="f_ulp")
        f_tne = st.number_input("tn etäisyys mm", key="f_tne")
    with c2:
        f_tnv = st.number_input("tn väli mm", key="f_tnv")
        f_tnm = st.number_input("tn määrä kpl", key="f_tnm")

    if st.button("Laske lattiapohja", type="primary"):
        nostot = [int(f_tne + (i * f_tnv)) for i in range(int(f_tnm)) if (int(f_tne + (i * f_tnv))) < f_ulp]
        all_p = [0] + nostot + [int(f_ulp)]
        sallitut = list(range(2, len(all_p) - 2))
        m_a, m_b = yrita_laskea_pari_f(f_max, all_p, sallitut)
        
        if m_a and m_b:
            st.success("Laskenta valmis!")
            piirra_lautajako(m_a, m_b, f_ulp, nostot)
            colA, colB = st.columns(2)
            with colA:
                st.info(f"**MALLI A (Pohja)**\n\nKappaleita: {len(m_a['palat'])} kpl\n\nLaudat: {' + '.join(map(str, m_a['palat']))} mm")
            with colB:
                st.info(f"**MALLI B (Porrastettu)**\n\nKappaleita: {len(m_b['palat'])} kpl\n\nLaudat: {' + '.join(map(str, m_b['palat']))} mm")
        else:
            test_l, loytyi = f_max, False
            while test_l < f_ulp:
                test_l += 10
                ta, tb = yrita_laskea_pari_f(test_l, all_p, sallitut)
                if ta and tb: loytyi = True; break
            
            msg = "Lisää yksi trukkinosto tai käytä pidempää lautaa, jako ei mahdollinen."
            if loytyi: st.error(f"❌ {msg}\n\n**Laudan vaadittu vähimmäispituus on {int(test_l)} mm.**")
            else: st.error(f"❌ {msg}")

with t2:
    st.header("Jalas-laskenta (Mestarin logiikka)")
    cj1, cj2 = st.columns(2)
    with cj1:
        j_p = st.number_input("Jalaksen kokonaispituus mm", key="j_jalas_p")
        j_l = st.number_input("Käytettävän materiaalin mitta mm", key="j_lauta_p")
    with cj2:
        j_k = st.number_input("Jalasmäärä (1-3 kerrosta)", value=3, min_value=1, max_value=3, key="j_kerrokset")

    if st.button("Laske jalasten jako", type="primary"):
        if j_l >= j_p: st.info("Jalas voidaan tehdä yhdestä puusta.")
        else:
            d, v = laske_jalas_ohjeistettu(j_p, j_l, j_k)
            st.success("Jalas laskettu lujuus ja helppous edellä.")
            piirra_jalasjako(d, j_p, v)
            for i, kerros in enumerate(d):
                st.info(f"**Kerros {i+1}:** {' + '.join(map(str, kerros))} mm")
