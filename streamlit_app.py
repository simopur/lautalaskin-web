import streamlit as st

def tulosta_st(nimi, palat, saumat):
    st.subheader(nimi)
    st.write(f"**Kappaleita:** {len(palat)} kpl")
    st.info(f"**Laudat:** {' + '.join(map(str, palat))} mm")
    st.write(f"**Saumat (mm):** {saumat}")

def etsi_reitit(n_idx, reitti, max_l, pisteet, sallitut):
    # Jos päästään loppuun asti
    if pisteet[-1] - pisteet[n_idx] <= max_l:
        if n_idx != len(pisteet) - 2:
            return [reitti + [len(pisteet)-1]]
    
    loydetyt = []
    for s_idx in sallitut:
        if s_idx <= n_idx:
            continue
            
        pala = pisteet[s_idx] - pisteet[n_idx]
        if pala <= max_l:
            # Sääntö: saumojen välissä oltava vähintään yksi vapaa nosto
            if s_idx - n_idx >= 2:
                tulokset = etsi_reitit(s_idx, reitti + [s_idx], max_l, pisteet, sallitut)
                if tulokset:
                    loydetyt.extend(tulokset)
    return loydetyt

# --- KÄYTTÖLIITTYMÄ ---
st.set_page_config(page_title="Lautalaskin v2.1", layout="centered")
st.title("📦 Lautalaatikon Jakolaskin v2.1")
st.write("Optimoitu kestävyys ja maksimaalinen pituus.")

col1, col2 = st.columns(2)
with col1:
    max_l = st.number_input("Laudan pituus mm", value=4500)
    ulkopituus = st.number_input("ulkopituus mm", value=9110)
    tn_eka = st.number_input("tn etäisyys mm", value=280)
with col2:
    tn_vali = st.number_input("tn väli mm", value=950)
    tn_maara = st.number_input("tn määrä kpl", value=10, step=1)

if st.button("Laske lautajako", type="primary"):
    nostot = [int(tn_eka + (i * tn_vali)) for i in range(tn_maara) if (int(tn_eka + (i * tn_vali))) < ulkopituus]
    all_p = [0] + nostot + [int(ulkopituus)]
    
    # Sallitut saumat (ei eka tn, ei vika tn)
    sallitut = list(range(2, len(all_p) - 2))
    reitti_idat = etsi_reitit(0, [0], max_l, all_p, sallitut)

    if not reitti_idat:
        st.warning("Jakoa ei löytynyt. Kokeile pidempää lautaa.")
    else:
        valmiit = []
        for r in reitti_idat:
            palat = [all_p[r[j+1]] - all_p[r[j]] for j in range(len(r)-1)]
            saumat = [all_p[idx] for idx in r[1:-1]]
            valmiit.append({'palat': palat, 'saumat': saumat, 'idx': r})

        # Järjestys: 1. vähiten paloja, 2. pisin minimipala
        valmiit.sort(key=lambda x: (len(x['palat']), -min(x['palat'])))

        m_a = valmiit[0]
        m_b = None
        a_idx_set = set(m_a['idx'][1:-1])
        
        for ehdokas in valmiit:
            b_idx_list = ehdokas['idx'][1:-1]
            if not b_idx_list: continue
            
            safe = True
            for b_idx in b_idx_list:
                # Kielletään sama ja viereiset nostot suhteessa A-malliin
                if b_idx in a_idx_set or (b_idx-1) in a_idx_set or (b_idx+1) in a_idx_set:
                    safe = False
                    break
            if safe:
                m_b = ehdokas
                break

        st.success("Laskenta valmis!")
        tulosta_st("MALLI A (Pohja)", m_a['palat'], m_a['saumat'])
        st.divider()
        if m_b:
            tulosta_st("MALLI B (Sivut / Porrastettu)", m_b['palat'], m_b['saumat'])
        else:
            st.warning("Täydellistä porrastusta ei löytynyt. Näytetään vara-ehdotus.")
            if len(valmiit) > 1:
                tulosta_st("MALLI B (Varaehdotus)", valmiit[1]['palat'], valmiit[1]['saumat'])
