import streamlit as st

def etsi_kaikki_reitit(alkupiste, reitti, pituus, max_l, sallitut):
    if pituus - alkupiste <= max_l:
        return [reitti + [pituus]]
    
    loydetyt = []
    for sauma in sallitut:
        pala = sauma - alkupiste
        if 0 < pala <= max_l:
            tulokset = etsi_kaikki_reitit(sauma, reitti + [sauma], pituus, max_l, sallitut)
            loydetyt.extend(tulokset)
    return loydetyt

def laske_pituuspisteet(reitti):
    # Lasketaan lautojen pituuksien neliösumma. 
    # Tämä suosii matemaattisesti pitkiä lautoja ja rankaisee pirstaleisuutta.
    pisteet = 0
    for i in range(len(reitti)-1):
        pala = reitti[i+1] - reitti[i]
        pisteet += pala**2
    return pisteet

# --- KÄYTTÖLIITTYMÄ ---
st.set_page_config(page_title="Lautalaatikon Jakolaskin", layout="centered")
st.title("📦 Lautalaatikon Jakolaskin v1.6")
st.write("Prioriteetti: 1. Liitosten porrastus (ei vierekkäin), 2. Maksimaalinen laudan pituus.")

col1, col2 = st.columns(2)
with col1:
    max_l = st.number_input("Laudan pituus mm", value=4200)
    kokonais = st.number_input("ulkopituus mm", value=12110)
    eka = st.number_input("tn etäisyys mm", value=295)
with col2:
    vali = st.number_input("tn väli mm", value=960)
    maara = st.number_input("tn määrä kpl", value=13, step=1)

if st.button("Laske lautajako", type="primary"):
    nostot = [int(eka + (i * vali)) for i in range(maara) if (int(eka + (i * vali))) < kokonais]
    
    if len(nostot) < 3:
        st.error("Trukkinostojen määrä on liian pieni.")
    else:
        sallitut = nostot[1:-1]
        kaikki_reitit = etsi_kaikki_reitit(0, [0], kokonais, max_l, sallitut)

        if not kaikki_reitit:
            st.warning("Jakoa ei löytynyt. Laudan pituus on liian lyhyt.")
        else:
            # Järjestetään reitit: 1. Vähiten paloja, 2. Pituuspisteet (parhaat laudat)
            # Käytetään negatiivista pistemäärää, jotta saadaan laskeva järjestys pituuden suhteen
            kaikki_reitit.sort(key=lambda r: (len(r), -laske_pituuspisteet(r)))
            
            malli_a = kaikki_reitit[0]
            malli_b = None
            
            # Etsitään Malli B, joka täyttää "ei vierekkäisiä saumoja" -ehdon
            a_saumat_indeksit = [nostot.index(s) for s in malli_a[1:-1]]
            
            for ehdokas in kaikki_reitit:
                ehdokas_saumat_indeksit = [nostot.index(s) for s in ehdokas[1:-1]]
                
                on_turvallinen = True
                for s_a in a_saumat_indeksit:
                    for s_b in ehdokas_saumat_indeksit:
                        # Kielletään sama sauma tai viereinen trukkinosto
                        if abs(s_a - s_b) <= 1:
                            on_turvallinen = False
                            break
                    if not on_turvallinen: break
                
                if on_turvallinen:
                    malli_b = ehdokas
                    break

            # Tulosten näyttäminen
            st.success(f"Laskenta valmis! Optimoitu kestävyys ja pituus.")
            
            def tulosta_st(nimi, reitti):
                palat = [int(reitti[i+1] - reitti[i]) for i in range(len(reitti)-1)]
                st.subheader(nimi)
                st.write(f"**Kappaleita:** {len(palat)} kpl")
                st.info(f"**Laudat:** {' + '.join(map(str, palat))} mm")
                st.write(f"**Saumat (nostojen kohdat):** {reitti[1:-1]} mm")

            tulosta_st("MALLI A (Tehokkain)", malli_a)
            st.divider()
            if malli_b:
                tulosta_st("MALLI B (Turvallisin limitys)", malli_b)
            else:
                # Jos täydellistä limitystä ei löydy, otetaan se mikä on vähiten huono
                st.warning("Täydellistä porrastusta (yli 1 tn väli) ei löytynyt. Näytetään paras mahdollinen.")
                tulosta_st("MALLI B (Paras saatavilla oleva)", kaikki_reitit[-1])
