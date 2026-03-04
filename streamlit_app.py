import streamlit as st

# Määritellään tulostusfunktio heti alussa, jotta se on aina käytettävissä
def tulosta_st(nimi, reitti):
    palat = [int(reitti[i+1] - reitti[i]) for i in range(len(reitti)-1)]
    st.subheader(nimi)
    st.write(f"**Kappaleita:** {len(palat)} kpl")
    st.info(f"**Laudat:** {' + '.join(map(str, palat))} mm")
    st.write(f"**Saumat (mm):** {reitti[1:-1]}")

def etsi_kaikki_reitit(alkupiste, reitti, pituus, max_l, sallitut, nostot):
    if pituus - alkupiste <= max_l:
        return [reitti + [pituus]]
    
    loydetyt = []
    for sauma in sallitut:
        pala = sauma - alkupiste
        if 0 < pala <= max_l:
            # Sääntö: lauta ei saa olla vain yhden välin mittainen (väh. 2 väliä)
            if len(reitti) > 1:
                edellinen_sauma = reitti[-1]
                if abs(nostot.index(edellinen_sauma) - nostot.index(sauma)) <= 1:
                    continue
            
            tulokset = etsi_kaikki_reitit(sauma, reitti + [sauma], pituus, max_l, sallitut, nostot)
            loydetyt.extend(tulokset)
    return loydetyt

def laske_laadukkuus(reitti):
    palat = [reitti[i+1] - reitti[i] for i in range(len(reitti)-1)]
    # Painotetaan: 1. Vähiten paloja, 2. Tasaiset/pitkät palat (minimipalan pituus)
    return (-len(reitti), min(palat))

# --- KÄYTTÖLIITTYMÄ ---
st.set_page_config(page_title="Lautalaatikon Jakolaskin v1.8", layout="centered")
st.title("📦 Lautalaatikon Jakolaskin v1.8")
st.write("Kestävä ja optimaalinen lautajako selaimessa.")

col1, col2 = st.columns(2)
with col1:
    max_l = st.number_input("Laudan pituus mm", value=4500)
    kokonais = st.number_input("ulkopituus mm", value=9110)
    eka = st.number_input("tn etäisyys mm", value=280)
with col2:
    vali = st.number_input("tn väli mm", value=950)
    maara = st.number_input("tn määrä kpl", value=10, step=1)

if st.button("Laske lautajako", type="primary"):
    nostot = [int(eka + (i * vali)) for i in range(maara) if (int(eka + (i * vali))) < kokonais]
    
    if len(nostot) < 3:
        st.error("Trukkinostojen määrä on liian pieni.")
    else:
        sallitut = nostot[1:-1]
        reitit = etsi_kaikki_reitit(0, [0], kokonais, max_l, sallitut, nostot)

        if not reitit:
            st.warning("Jakoa ei löytynyt näillä asetuksilla.")
        else:
            # Järjestetään reitit parhaasta huonoimpaan
            reitit.sort(key=laske_laadukkuus, reverse=True)
            
            malli_a = reitit[0]
            malli_b = None
            
            a_saumat_idx = [nostot.index(s) for s in malli_a[1:-1]]
            
            # Etsitään paras pari Malli A:lle
            for ehdokas in reitit:
                b_saumat_idx = [nostot.index(s) for s in ehdokas[1:-1]]
                
                safe = True
                if set(b_saumat_idx) == set(a_saumat_idx):
                    safe = False # Ei saa olla täysin sama
                else:
                    for sa in a_saumat_idx:
                        for sb in b_saumat_idx:
                            if abs(sa - sb) <= 1: # Ei saa olla viereinen
                                safe = False
                                break
                        if not safe: break
                
                if safe:
                    malli_b = ehdokas
