import streamlit as st

def etsi_reitit(alkupiste, reitti, pituus, max_l, sallitut):
    if pituus - alkupiste <= max_l:
        return [reitti + [pituus]]
    
    loydetyt = []
    for sauma in sallitut:
        pala = sauma - alkupiste
        if 0 < pala <= max_l:
            tulokset = etsi_reitit(sauma, reitti + [sauma], pituus, max_l, sallitut)
            loydetyt.extend(tulokset)
    return loydetyt

# --- KÄYTTÖLIITTYMÄ ---
st.set_page_config(page_title="Lautalaatikon Jakolaskin", layout="centered")
st.title("📦 Lautalaatikon Jakolaskin v1.5")
st.write("Tämä työkalu laskee optimaalisen ja porrastetun lautajaon.")

# Syöttökentät kahteen sarakkeeseen
col1, col2 = st.columns(2)

with col1:
    max_l = st.number_input("Laudan pituus mm", value=4200)
    kokonais = st.number_input("ulkopituus mm", value=12110)
    eka = st.number_input("tn etäisyys mm", value=295)

with col2:
    vali = st.number_input("tn väli mm", value=960)
    maara = st.number_input("tn määrä kpl", value=13, step=1)

if st.button("Laske lautajako", type="primary"):
    # 1. Nostojen paikat
    nostot = [int(eka + (i * vali)) for i in range(maara) if (int(eka + (i * vali))) < kokonais]
    
    if len(nostot) < 3:
        st.error("Trukkinostojen määrä on liian pieni suhteessa pituuteen.")
    else:
        sallitut = nostot[1:-1] # Ei ensimmäinen, ei viimeinen
        kaikki_reitit = etsi_reitit(0, [0], kokonais, max_l, sallitut)

        if not kaikki_reitit:
            st.warning("Jakoa ei löytynyt. Laudan pituus on liian lyhyt.")
        else:
            # Ryhmitellään ja valitaan parhaat
            reitit_koon_mukaan = {}
            for r in kaikki_reitit:
                koko = len(r)
                if koko not in reitit_koon_mukaan:
                    reitit_koon_mukaan[koko] = []
                reitit_koon_mukaan[koko].append(r)

            koot = sorted(reitit_koon_mukaan.keys())
            malli_a = reitit_koon_mukaan[koot[0]][0]
            malli_b = None
            
            for r in reitit_koon_mukaan[koot[0]]:
                if set(r[1:-1]) != set(malli_a[1:-1]):
                    malli_b = r
                    break
            
            if malli_b is None and len(koot) > 1:
                parhaat_b_ehdokkaat = reitit_koon_mukaan[koot[1]]
                malli_b = parhaat_b_ehdokkaat[len(parhaat_b_ehdokkaat)//2]

            # Tulosten näyttäminen
            st.success(f"Laskenta valmis! Ulkopituus {int(kokonais)} mm.")
            
            def tulosta_st(nimi, reitti):
                palat = [int(reitti[i+1] - reitti[i]) for i in range(len(reitti)-1)]
                st.subheader(nimi)
                st.write(f"**Kappaleita:** {len(palat)} kpl")
                st.info(f"**Laudat:** {' + '.join(map(str, palat))} mm")
                st.write(f"**Saumat (etäisyys alusta):** {reitti[1:-1]} mm")

            tulosta_st("MALLI A (Pohja)", malli_a)
            st.divider()
            if malli_b:
                tulosta_st("MALLI B (Sivut / Porrastettu)", malli_b)
            else:
                st.write("Huom: Vain yksi toimiva jako löytyi.")