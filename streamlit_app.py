import streamlit as st

def tulosta_st(nimi, palat, saumat):
    st.subheader(nimi)
    st.write(f"**Kappaleita:** {len(palat)} kpl")
    st.info(f"**Laudat:** {' + '.join(map(str, palat))} mm")
    st.write(f"**Saumat (mm):** {saumat}")

def etsi_reitit(n_idx, reitti, max_l, pisteet, sallitut):
    # Jos päästään loppuun asti yhdellä laudalla
    etaisyys_loppuun = pisteet[-1] - pisteet[n_idx]
    if etaisyys_loppuun <= max_l:
        # Varmistetaan, ettei olla viimeisessä kielletyssä nostossa
        if n_idx != len(pisteet) - 2:
            return [reitti + [len(pisteet)-1]]
    
    loydetyt = []
    for s_idx in sallitut:
        if s_idx <= n_idx:
            continue
        pala = pisteet[s_idx] - pisteet[n_idx]
        if pala <= max_l:
            # Sääntö: saumojen välissä oltava vähintään kaksi väliä
            if s_idx - n_idx >= 2:
                tulokset = etsi_reitit(s_idx, reitti + [s_idx], max_l, pisteet, sallitut)
                if tulokset:
                    loydetyt.extend(tulokset)
    return loydetyt

# --- KÄYTTÖLIITTYMÄ ---
st.set_page_config(page_title="Lautalaskin v2.2", layout="centered")
st.title("📦 Lautalaatikon Jakolaskin v2.2")
st.write("Priorisoitu: 1. Pitkät laudat, 2. Saumojen porrastus peilikuvalla.")

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
            # Pistemäärä: sum(p**2) suosii pitkiä lautoja (vähemmän tasapainoa)
            l_score = sum(p**2 for p in palat)
            valmiit.append({'palat': palat, 'saumat': saumat, 'idx': r, 'l_score': l_score})

        # Järjestys: 1. vähiten paloja, 2. pituuspisteet (pitkät laudat ensin)
        valmiit.sort(key=lambda x: (len(x['palat']), -x['l_score']))

        m_a = valmiit[0]
        m_b = None
        a_idx_set = set(m_a['idx'][1:-1])
        
        # 1. Yritetään Malli B:ksi kääntää Malli A toisin päin
        rev_palat = m_a['palat'][::-1]
        rev_saumat = []
        cur = 0
        for p in rev_palat[:-1]:
            cur += p
            rev_saumat.append(cur)
        
        # Tarkistetaan onko käännetty versio validi (osuvatko saumat nostoihin)
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
                m_b = {'palat': rev_palat, 'saumat': rev_saumat}

        # 2. Jos käännetty ei käynyt, etsitään muista vaihtoehdoista
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

        st.success("Laskenta valmis! Optimoitu pituus ja porrastus.")
        tulosta_st("MALLI A (Pohja)", m_a['palat'], m_a['saumat'])
        st.divider()
        if m_b:
            tulosta_st("MALLI B (Sivut / Porrastettu)", m_b['palat'], m_b['saumat'])
        else:
            st.warning("Täydellistä porrastusta ei löytynyt. Näytetään vara-ehdotus.")
            if len(valmiit) > 1:
                tulosta_st("MALLI B (Varaehdotus)", valmiit[1]['palat'], valmiit[1]['saumat'])
