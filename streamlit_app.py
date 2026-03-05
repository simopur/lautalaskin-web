import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches

# --- VISUALISOINTI ---
def piirra_lautajako(malli_a, malli_b, ulkopituus):
    fig, ax = plt.subplots(figsize=(10, 4))
    
    # Piirretään 5 lautaa (vuorotellen A, B, A, B, A)
    jaot = [malli_a, malli_b, malli_a, malli_b, malli_a]
    colors = ['#e67e22', '#d35400'] # Puun sävyjä
    
    for i, jako in enumerate(jaot):
        if not jako: continue
        
        y_pos = i * 1.2
        current_x = 0
        palat = jako['palat']
        
        for j, pala in enumerate(palat):
            # Piirretään lauta-segmentti
            rect = patches.Rectangle((current_x, y_pos), pala, 0.8, 
                                     linewidth=1, edgecolor='black', 
                                     facecolor=colors[i % 2], alpha=0.7)
            ax.add_patch(rect)
            
            # Lisätään pituuslukema segmentin päälle, jos se on tarpeeksi pitkä
            if pala > 500:
                ax.text(current_x + pala/2, y_pos + 0.4, f"{int(pala)}", 
                        ha='center', va='center', color='white', fontsize=8, fontweight='bold')
            
            current_x += pala
            
            # Piirretään saumaviiva (paitsi jos on viimeinen pala)
            if j < len(palat) - 1:
                ax.plot([current_x, current_x], [y_pos, y_pos + 0.8], color='black', linewidth=2)

    ax.set_xlim(-100, ulkopituus + 100)
    ax.set_ylim(-0.5, 6)
    ax.set_aspect('equal')
    ax.set_title("Lautajaon visualisointi (5 lautaa rinnakkain)", pad=20)
    ax.set_xlabel("Pituus (mm)")
    ax.set_yticks([0.4, 1.6, 2.8, 4.0, 5.2])
    ax.set_yticklabels(["Lauta 1 (A)", "Lauta 2 (B)", "Lauta 3 (A)", "Lauta 4 (B)", "Lauta 5 (A)"])
    
    # Poistetaan turhat kehykset
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
        if s_idx <= n_idx:
            continue
        pala = pisteet[s_idx] - pisteet[n_idx]
        if pala <= max_l:
            if s_idx - n_idx >= 2:
                tulokset = etsi_reitit(s_idx, reitti + [s_idx], max_l, pisteet, sallitut)
                if tulokset:
                    loydetyt.extend(tulokset)
    return loydetyt

# --- KÄYTTÖLIITTYMÄ ---
st.set_page_config(page_title="Lautalaskin v2.3", layout="centered")
st.title("📦 Lautalaatikon Jakolaskin v2.3")
st.write("Visualisointi lisätty – näe liitosten porrastus heti.")

col1, col2 = st.columns(2)
with col1:
    max_l = st.number_input("Laudan pituus mm", value=3900)
    ulkopituus = st.number_input("ulkopituus mm", value=12110)
    tn_eka = st.number_input("tn etäisyys mm", value=295)
with col2:
    tn_vali = st.number_input("tn väli mm", value=960)
    tn_maara = st.number_input("tn määrä kpl", value=13, step=1)

if st.button("Laske lautajako", type="primary"):
    nostot = [int(tn_eka + (i * tn_vali)) for i in range(tn_maara) if (int(tn_eka + (i * tn_vali))) < ulkopituus]
    all_p = [0] + nostot + [int(ulkopituus)]
    sallitut = list(range(2, len(all_p) - 2))
    reitti_idat = etsi_reitit(0, [0], max_l, all_p, sallitut)

    if not reitti_idat:
        st.warning("Jakoa ei löytynyt. Laudan pituus on liian lyhyt.")
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
        a_idx_set = set(m_a['idx'][1:-1])
        
        # Peilikuva-logiikka
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
                if s_idx in sallitut:
                    rev_idx_list.append(s_idx)
                else: is_rev_valid = False; break
            else: is_rev_valid = False; break
        
        if is_rev_valid:
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
                for b_idx in b_idx_list:
                    if b_idx in a_idx_set or (b_idx-1) in a_idx_set or (b_idx+1) in a_idx_set:
                        safe = False; break
                if safe:
                    m_b = ehdokas; break

        st.success("Laskenta valmis!")
        
        # Piirretään kuva
        piirra_lautajako(m_a, m_b, ulkopituus)
        
        tulosta_st("MALLI A (Pohja)", m_a['palat'], m_a['saumat'])
        st.divider()
        if m_b:
            tulosta_st("MALLI B (Sivut / Porrastettu)", m_b['palat'], m_b['saumat'])
        else:
            st.warning("Täydellistä porrastusta ei löytynyt.")
