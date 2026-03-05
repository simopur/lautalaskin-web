import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches

# --- VISUALISOINTI ---
def piirra_lautajako(malli_a, malli_b, ulkopituus):
    # Säädetään figsize niin, että korkeus pysyy maltillisena (n. 15cm näytöllä)
    # 12 metriä vs 500mm on suhde 24:1. Leveä ja matala kuva on paras.
    fig, ax = plt.subplots(figsize=(12, 3)) 
    
    # 5 lautaa rinnakkain (vuorotellen A, B, A, B, A)
    jaot = [malli_a, malli_b, malli_a, malli_b, malli_a]
    colors = ['#e67e22', '#d35400'] # Puun sävyjä
    
    lauta_leveys = 100 # mm
    vali = 10 # mm rako visualisoinnin selkeyttämiseksi
    
    for i, jako in enumerate(jaot):
        if not jako: continue
        
        y_pos = i * (lauta_leveys + vali)
        current_x = 0
        palat = jako['palat']
        
        for j, pala in enumerate(palat):
            # Piirretään lauta mittakaavassa (korkeus 100mm)
            rect = patches.Rectangle((current_x, y_pos), pala, lauta_leveys, 
                                     linewidth=0.5, edgecolor='black', 
                                     facecolor=colors[i % 2], alpha=0.8)
            ax.add_patch(rect)
            
            # Lisätään pituuslukema vain, jos se mahtuu (esim. > 800mm)
            if pala > 800:
                ax.text(current_x + pala/2, y_pos + lauta_leveys/2, f"{int(pala)}", 
                        ha='center', va='center', color='white', fontsize=7, fontweight='bold')
            
            current_x += pala
            
            # Saumaviiva
            if j < len(palat) - 1:
                ax.plot([current_x, current_x], [y_pos, y_pos + lauta_leveys], 
                        color='black', linewidth=1.5)

    # Asetetaan akselit mittakaavaan
    ax.set_xlim(-200, ulkopituus + 200)
    ax.set_ylim(-50, 5 * (lauta_leveys + vali) + 50)
    
    # TÄRKEÄ: Pitää mittasuhteet oikeina (1mm x = 1mm y)
    ax.set_aspect('equal')
    
    ax.set_title(f"Visualisointi: 100mm laudat rinnakkain (Pituus {int(ulp_p)} mm)", fontsize=10)
    ax.set_xlabel("Pituus (mm)", fontsize=8)
    
    # Siistitään ulkoasua
    ax.set_yticks([(lauta_leveys/2) + i*(lauta_leveys+vali) for i in range(5)])
    ax.set_yticklabels(["A", "B", "A", "B", "A"], fontsize=8)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)
    
    st.pyplot(fig)

# --- LASKENTALAGIIKKA (Ennallaan v2.2) ---
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
st.set_page_config(page_title="Lautalaskin v2.4", layout="wide") # Leveä tila parempi kuvalle
st.title("📦 Lautalaatikon Jakolaskin v2.4")

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
    reitti_idat = etsi_reitit(0, [0], m_l, all_p, sallitut)

    if not reitti_idat:
        st.warning("Jakoa ei löytynyt.")
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
        
        # Peilikuva-tarkistus (kuten v2.2)
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

        st.success("Laskenta valmis!")
        
        # Piirretään kuva mittakaavassa
        piirra_lautajako(m_a, m_b, ulp_p)
        
        c1, c2 = st.columns(2)
        with c1: tulosta_st("MALLI A (Pohja)", m_a['palat'], m_a['saumat'])
        with c2: 
            if m_b: tulosta_st("MALLI B (Sivut / Porrastettu)", m_b['palat'], m_b['saumat'])
