import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches

# --- VISUALISOINTI ---
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
            rect = patches.Rectangle((current_x, y_pos), pala, lauta_leveys, 
                                     linewidth=0.5, edgecolor='black', 
                                     facecolor=colors[i % 2], alpha=0.8)
            ax.add_patch(rect)
            if pala > 800:
                ax.text(current_x + pala/2, y_pos + lauta_leveys/2, f"{int(pala)}", 
                        ha='center', va='center', color='white', fontsize=7, fontweight='bold')
            current_x += pala
            if j < len(jako['palat']) - 1:
                ax.plot([current_x, current_x], [y_pos, y_pos + lauta_leveys], color='black', linewidth=2.5)

    ax.set_xlim(-200, ulkopituus + 200)
    ax.set_ylim(-50, 5 * (lauta_leveys + vali) + 50)
    ax.set_aspect('equal')
    ax.set_xticks(nostot)
    labels = ax.set_xticklabels([str(int(n)) for n in nostot], fontsize=7, rotation=45)
    for i, n in enumerate(nostot):
        if n in kaikki_saumat:
            labels[i].set_fontweight('bold')
    ax.set_yticks([(lauta_leveys/2) + i*(lauta_leveys+vali) for i in range(5)])
    ax.set_yticklabels(["A", "B", "A", "B", "A"], fontsize=8)
    for spine in ax.spines.values(): spine.set_visible(False)
    st.pyplot(fig)

# --- APUFUNKTIOT JA LOGIIKKA ---
def etsi_reitit(n_idx, reitti, max_l, pisteet, sallitut):
    etaisyys_loppuun = pisteet[-1] - pisteet[n_idx]
    if etaisyys_loppuun <= max_l:
        if n_idx != len(pisteet) - 2: return [reitti + [len(pisteet)-1]]
    loydetyt = []
    for s_idx in sallitut:
        if s_idx <= n_idx: continue
        pala = pisteet[s_idx] - pisteet[n_idx]
        if pala <= max_l and s_idx - n_idx >= 2:
            tulokset = etsi_reitit(s_idx, reitti + [s_idx], max_l, pisteet, sallitut)
            if tulokset: loydetyt.extend(tulokset)
    return loydetyt

def yrita_laskea_pari(m_l, all_p, sallitut, nostot):
    reitit = etsi_reitit(0, [0], m_l, all_p, sallitut)
    if not reitit: return None, None
    
    valmiit = []
    for r in reitit:
        palat = [all_p[r[j+1]] - all_p[r[j]] for j in range(len(r)-1)]
        saumat = [all_p[idx] for idx in r[1:-1]]
        l_score = sum(p**2 for p in palat)
        valmiit.append({'palat': palat, 'saumat': saumat, 'idx': r, 'l_score': l_score})

    valmiit.sort(key=lambda x: (len(x['palat']), -x['l_score']))
    m_a = valmiit[0]
    m_b = None
    
    # Kokeillaan peilikuvaa ja muita yhdistelmiä (kuten v2.8)
    a_idx_set = set(m_a['idx'][1:-1])
    for ehdokas in valmiit:
        b_idx_list = ehdokas['idx'][1:-1]
        if not b_idx_list: continue
        safe = True
        for b_idx in b_idx_list:
            if b_idx in a_idx_set or (b_idx-1) in a_idx_set or (b_idx+1) in a_idx_set:
                safe = False; break
        if safe:
            m_b = ehdokas; break
    return m_a, m_b

# --- KÄYTTÖLIITTYMÄ ---
st.set_page_config(page_title="Lautalaskin v2.9", layout="wide")
st.title("📦 Lautalaatikon Jakolaskin v2.9")

col1, col2 = st.columns(2)
with col1:
    m_l = st.number_input("Laudan pituus mm", value=3900)
    ulp_p = st.number_input("ulkopituus mm", value=12110)
    tn_e = st.number_input("tn etäisyys mm", value=295)
with col2:
    tn_v = st.number_input("tn väli mm", value=960)
    tn_m = st.number_input("tn määrä kpl", value=13, step=1)

if st.button("Laske lautajako", type="primary"):
    nostot = [int(tn_e + (i * tn_v)) for i in range(tn_m) if (int(tn_e + (i * tn_v))) < ulp_p]
    all_p = [0] + nostot + [int(ulp_p)]
    sallitut = list(range(2, len(all_p) - 2))
    
    # Tarkistetaan symmetria
    if nostot:
        if abs(nostot[0] - (ulp_p - nostot[-1])) > 1: st.warning("⚠️ Jako ei symmetrinen!")

    # Yritetään laskea jako
    m_a, m_b = yrita_laskea_pari(m_l, all_p, sallitut, nostot)

    if m_a and m_b:
        st.success("Laskenta valmis!")
        piirra_lautajako(m_a, m_b, ulp_p, nostot)
        c1, c2 = st.columns(2)
        with c1: st.info(f"**MALLI A (Pohja)**\n\n{len(m_a['palat'])} kpl: {' + '.join(map(str, m_a['palat']))} mm")
        with c2: st.info(f"**MALLI B (Sivut)**\n\n{len(m_b['palat'])} kpl: {' + '.join(map(str, m_b['palat']))} mm")
    else:
        # Lasketaan vaadittu minimipituus (iteraatio)
        min_v_p = m_l
        loydetty = False
        while min_v_p < ulp_p:
            min_v_p += 10 # Testataan 10mm välein
            test_a, test_b = yrita_laskea_pari(min_v_p, all_p, sallitut, nostot)
            if test_a and test_b:
                loydetty = True
                break
        
        error_msg = "Jako ei mahdollinen näillä asetuksilla."
        if loydetty:
            st.error(f"❌ {error_msg}\n\n**Laudan vaadittu vähimmäispituus on {int(min_v_p)} mm.** (Tai lisää yksi trukkinosto).")
        else:
            st.error(f"❌ {error_msg} Lisää yksi trukkinosto, jotta jako onnistuisi.")
