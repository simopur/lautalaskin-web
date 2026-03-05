import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches

# --- VISUALISOINTI ---
def piirra_lautajako(malli_a, malli_b, ulkopituus, nostot):
    fig, ax = plt.subplots(figsize=(12, 3)) 
    
    jaot = [malli_a, malli_b, malli_a, malli_b, malli_a]
    colors = ['#e67e22', '#d35400']
    
    lauta_leveys = 100 
    vali = 10 
    
    kaikki_saumat = set(malli_a['saumat'])
    if malli_b:
        kaikki_saumat.update(malli_b['saumat'])
    
    # Piirretään trukkinostojen pystyviivat taustalle
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
                ax.plot([current_x, current_x], [y_pos, y_pos + lauta_leveys], 
                        color='black', linewidth=2.5)

    ax.set_xlim(-200, ulkopituus + 200)
    ax.set_ylim(-50, 5 * (lauta_leveys + vali) + 50)
    ax.set_aspect('equal')
    
    ax.set_xticks(nostot)
    labels = ax.set_xticklabels([str(int(n)) for n in nostot], fontsize=7, rotation=45)
    
    for i, n in enumerate(nostot):
        if n in kaikki_saumat:
            labels[i].set_fontweight('bold')
            labels[i].set_color('black')

    ax.set_yticks([(lauta_leveys/2) + i*(lauta_leveys+vali) for i in range(5)])
    ax.set_yticklabels(["A", "B", "A", "B", "A"], fontsize=8)
    
    for spine in ax.spines.values():
        spine.set_visible(False)
    
    st.pyplot(fig)

# --- APUFUNKTIOT ---
def tulosta_st(nimi, palat, saumat):
    st.subheader(nimi)
    st.write(f"**Kappaleita:** {len(palat)} kpl")
    st.info(f"**Laudat:** {' + '.join(map(str, palat))} mm")
    st.write(f"**Saumat (mm):** {saumat}")

def etsi_reitit(n_idx, reitti, max_l, pisteet, sallitut):
    etaisyys_loppuun = pisteet[-1] - pisteet[n_idx]
    if etaisyys_loppuun <= max_l:
        if n_idx != len(pisteet) - 2:
            return [reitti + [len(pisteet)-1]]
    loydetyt = []
    for s_idx in sallitut:
        if s_idx <= n_idx: continue
        pala = pisteet[s_idx] - pisteet[n_idx]
        if pala <= max_l and s_idx - n_idx >= 2:
            tulokset = etsi_reitit(s_idx, reitti + [s_idx], max_l, pisteet, sallitut)
            if tulokset: loydetyt.extend(tulokset)
    return loydetyt

# --- KÄYTTÖLIITTYMÄ ---
st.set_page_config(page_title="Lautalaskin v2.8", layout="wide")
st.title("📦 Lautalaatikon Jakolaskin v2.8")

col1, col2 = st.columns(2)
with col1:
    m_l = st.number_input("Laudan pituus mm", value=3900)
    ulp_p = st.number_input("ulkopituus mm", value=12110)
    tn_e = st.number_input("tn etäisyys mm", value=295)
with col2:
    tn_v = st.number_input("tn väli mm", value=960)
    tn_m = st.number_input("tn määrä kpl", value=13, step=1)

if st.button("Laske lautajako", type="primary"):
    # 1. Trukkinostojen laskenta ja symmetriatarkistus
    nostot = [int(tn_e + (i * tn_v)) for i in range(tn_m) if (int(tn_e + (i * tn_v))) < ulp_p]
    
    if nostot:
        vali_alussa = nostot[0]
        vali_lopussa = ulp_p - nostot[-1]
        valit_keskella = [nostot[i+1] - nostot[i] for i in range(len(nostot)-1)]
        
        # Tarkistetaan onko alku- ja loppuväli sama ja onko välit keskellä symmetriset
        if abs(vali_alussa - vali_lopussa) > 1 or valit_keskella != valit_keskella[::-1]:
            st.warning("⚠️ Jako ei symmetrinen!")

    # 2. Reittien etsintä
    all_p = [0] + nostot + [int(ulp_p)]
    sallitut = list(range(2, len(all_p) - 2))
    reitti_idat = etsi_reitit(0, [0], m_l, all_p, sallitut)

    if not reitti_idat:
        st.error("Jakoa ei löytynyt näillä asetuksilla.")
    else:
        valmiit = []
        for r in reitti_idat:
            palat = [all_p[r[j+1]] - all_p[r[j]] for j in range(len(r)-1)]
            saumat = [all_p[idx] for idx in r[1:-1]]
            l_score = sum(p**2 for p in palat)
            valmiit.append({'palat': palat, 'saumat': saumat, 'idx': r, 'l_score': l_score})

        valmiit.sort(key=lambda x: (len(x['palat']), -x['l_score']))
        m_a = valmiit[0]
        m_b = None
        
        # Peilikuva-tarkistus
        rev_palat = m_a['palat'][::-1]
        rev_saumat = []
        cur = 0
        for p in rev_palat[:-1]:
            cur += p
            rev_saumat.append(cur)
        
        is_rev_valid = True
        rev_idx_list = []
        for s in rev_saumat:
            if s in all_p:
                s_idx = all_p.index(s)
                if s_idx in sallitut: rev_idx_list.append(s_idx)
                else: is_rev_valid = False; break
            else: is_rev_valid = False; break
        
        if is_rev_valid:
            a_idx_set = set(m_a['idx'][1:-1])
            safe_rev = True
            for b_idx in rev_idx_list:
                if b_idx in a_idx_set or (b_idx-1) in a_idx_set or (b_idx+1) in a_idx_set:
                    safe_rev = False; break
            if safe_rev:
                m_b = {'palat': rev_palat, 'saumat': rev_saumat, 'idx': [0] + rev_idx_list + [len(all_p)-1]}

        if not m_b:
            for ehdokas in valmiit:
                b_idx_list = ehdokas['idx'][1:-1]
                if not b_idx_list: continue
                safe = True
                a_idx_set = set(m_a['idx'][1:-1])
                for b_idx in b_idx_list:
                    if b_idx in a_idx_set or (b_idx-1) in a_idx_set or (b_idx+1) in a_idx_set:
                        safe = False; break
                if safe: m_b = ehdokas; break

        # 3. Lopputuloksen näyttäminen tai virheilmoitus
        if not m_b:
            st.error("Lisää yksi trukkinosto tai käytä pidempää lautaa, jako ei mahdollinen.")
        else:
            st.success("Laskenta valmis!")
            piirra_lautajako(m_a, m_b, ulp_p, nostot)
            c1, c2 = st.columns(2)
            with c1: tulosta_st("MALLI A (Pohja)", m_a['palat'], m_a['saumat'])
            with c2: tulosta_st("MALLI B (Sivut / Porrastettu)", m_b['palat'], m_b['saumat'])
