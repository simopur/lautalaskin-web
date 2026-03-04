import streamlit as st

# Määritellään tulostusfunktio
def tulosta_st(nimi, palat, saumat):
    st.subheader(nimi)
    st.write(f"**Kappaleita:** {len(palat)} kpl")
    st.info(f"**Laudat:** {' + '.join(map(str, palat))} mm")
    st.write(f"**Saumat (mm):** {saumat}")

def etsi_reitit(nykyinen_idx, reitti_indices, max_l, all_points, sallitut_indices):
    # Jos loppuun päästään suoraan yhdellä laudalla
    if all_points[-1] - all_points[nykyinen_idx] <= max_l:
        # Varmistetaan, ettei edellinen sauma ollut viimeinen kielletty nosto
        if nykyinen_idx != len(all_points) - 2:
            return [reitti_indices + [len(all_points)-1]]
    
    loydetyt = []
    for seuraava_idx in sallitut_indices:
        if seuraava_idx <= nykyinen_idx:
            continue
            
        pala = all_points[seuraava_idx] - all_points[nykyinen_idx]
        if pala <= max_l:
            # Sääntö: saumojen välillä on oltava vähintään yksi vapaa nosto (väh. 2 väliä)
            if seuraava_idx - nykyinen_idx >= 2:
                tulokset = etsi_reitit(seuraava_idx, reitti_indices + [seuraava_idx], max_l, all_points, sallitut_indices)
                if tulokset:
                    loydetyt.extend(tulokset)
    return loydetyt

# --- KÄYTTÖLIITTYMÄ ---
st.set_page_config(page_title="Lautalaatikon Jakolaskin v2.0", layout="centered")
st.title("📦 Lautalaatikon Jakolaskin v2.0")
st.write("Optimoitu kestävyys, maksimaalinen pituus ja porrastettu jako.")

col1, col2 = st.columns(2)
with col1:
    max_l = st.number_input("Laudan pituus mm", value=4500)
    kokonais = st.number_input("ulkopituus mm", value=9110)
    eka = st.number_input("tn etäisyys mm", value=280)
with col2:
    vali = st.number_input("tn väli mm", value=950)
    maara = st.number_input("tn määrä kpl", value=10, step=1)

if st.button("Laske lautajako", type="primary"):
    # Lasketaan kaikki tukipisteet: [alku, tn1, tn2..., vika_tn, loppu]
    nostot = [int(eka + (i * vali)) for i in range(maara) if (int(eka + (i * vali))) < kokonais]
    all_points = [0] + nostot + [int(kokonais)]
    
    # Sallitut saumapaikat ovat tn2:sta toiseksi viimeiseen tn:ään
    # Indexit listassa: 0=alku, 1=tn1(kielletty), 2...N-2=tn_vika(kielletty), N-1=loppu
    sallitut_indices = list(range(2, len(all_points) - 2))
    
    reitti_indeksit = etsi_reitit(0, [0], max_l, all_points, sallitut_indices)

    if not reitti_indeksit:
        st.warning("Jakoa ei löytynyt. Kokeile pidempää lautaa tai tarkista mitat.")
    else:
        # Muunnetaan indeksit pituuksiksi ja saumapaikoiksi
        valmiit_reitit = []
        for ri in reitti
