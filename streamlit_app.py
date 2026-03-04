import streamlit as st

def tulosta_st(nimi, palat, saumat):
    st.subheader(nimi)
    st.write(f"**Kappaleita:** {len(palat)} kpl")
    st.info(f"**Laudat:** {' + '.join(map(str, palat))} mm")
    st.write(f"**Saumat (mm):** {saumat}")

def etsi_reitit(nykyinen_idx, reitti_indices, max_l, all_points, sallitut_indices):
    # Jos loppuun päästään yhdellä laudalla
    if all_points[-1] - all_points[nykyinen_idx] <= max_l:
        # Tarkistetaan, ettei edellinen sauma ollut viimeinen nosto
        if nykyinen_idx == len(all_points) - 2:
            return []
        return [reitti_indices + [len(all_points)-1]]
    
    loydetyt = []
    for seuraava_idx in sallitut_indices:
        if seuraava_idx <= nykyinen_idx:
            continue
            
        pala = all_points[seuraava_idx] - all_points[nykyinen_idx]
        if pala <= max_l:
            # Sääntö: saumojen väli vähintään 2 tn-väliä (ei vierekkäin)
            if seuraava_idx - nykyinen_idx < 2:
                continue
                
            tulokset = etsi_reitit(seuraava_idx, reitti_indices + [seuraava_idx], max_l, all_points, sallitut_indices)
            loydetyt.extend(tulokset)
    return loydetyt

# --- KÄYTTÖLIITTYMÄ ---
st.set_page_config(page_title="Lautalaatikon Jakolaskin v1.9", layout="centered")
st.title("📦 Lautalaatikon Jakolaskin v1.9")
st.write("Planattu kestävyys edellä – aivan kuten boulderoinnissa, tässäkin reitti on katsottava loppuun asti.")

col1, col2 = st.columns(2)
with col1:
    max_l = st.number_input("Laudan pituus mm", value=4500)
    kokonais = st.number_input("ulkopituus mm", value=9110)
    eka = st.number_input("tn etäisyys mm", value=280)
with col2:
    vali = st.number_input("tn väli mm", value=950)
    maara = st.number_input("tn määrä kpl", value=10, step=1)

if st.button("Laske lautajako", type="primary"):
    # Luodaan kaikki mahdolliset pisteet: 0, tn:t, loppu
    nostot = [int(eka + (i * vali)) for i in range(maara) if (int(eka + (i * vali))) < kokonais]
    all_points = [0] + nostot + [int(kokonais)]
    
    # Sallitut saumaindeksit (ei eka tn (1), ei vika tn (len-2))
    # all_points listassa: [0 (start), 1 (tn1), 2, 3... N-2 (tn last), N-1 (end)]
    sallitut_indices = range(2, len(all_points) - 2)
    
    reitti_indeksit = etsi_reitit(0, [0], max_l, all_points, sallitut_indices)

    if not reitti_indeksit:
        st.warning("Jakoa ei löytynyt. Kokeile pidempää lautaa tai tarkista nostojen määrä.")
    else:
        # Muutetaan indeksit reiteiksi (pituuksiksi ja saumapaikoiksi)
        valmiit_reitit = []
        for ri in reitti_indeksit:
            palat = [all_points[ri[j+1]] - all_points[ri[j]] for j in range(len(ri)-1)]
            saumat = [all_points[idx] for idx in ri[1:-1]]
            valmiit_reitit.append({'palat': palat, 'saumat': saumat, 'indices': ri})

        # Järjestetään: vähiten kappaleita ja pisin minimipala
        valmiit_reitit.sort(key=lambda x: (len(x['palat']), -min(x['palat'])))

        malli_a = valmiit_reitit[0]
        malli_b = None

        # Etsitään Malli B, jossa saumat ovat eri kohdissa (ei samoja eikä vierekkäisiä tn-indeksejä)
        a_indices = set(malli_a['indices'][1:-1])
        
        for ehdokas in valmiit_reitit:
            b_indices = ehdokas['indices'][1:-1]
            if not b_indices: continue
            
            safe = True
            for b_idx in b_indices:
                # Kielletään sama (b_idx) ja viereiset (b_idx-1, b_idx+1) suhteessa A:n saumoihin
                if b_idx in a_indices or (b_idx-1) in a_indices or (b_idx+1) in a_indices:
                    safe = False
                    break
            
            if
