import streamlit as st

def etsi_kaikki_reitit(alkupiste, reitti, pituus, max_l, sallitut, nostot):
    if pituus - alkupiste <= max_l:
        return [reitti + [pituus]]
    
    loydetyt = []
    for sauma in sallitut:
        pala = sauma - alkupiste
        if 0 < pala <= max_l:
            # Tarkistetaan, ettei sauma ole viereisessä nostossa kuin edellinen sauma
            if len(reitti) > 1:
                edellinen_sauma = reitti[-1]
                idx1 = nostot.index(edellinen_sauma)
                idx2 = nostot.index(sauma)
                if abs(idx1 - idx2) <= 1:
                    continue
            
            tulokset = etsi_kaikki_reitit(sauma, reitti + [sauma], pituus, max_l, sallitut, nostot)
            loydetyt.extend(tulokset)
    return loydetyt

def laske_laadukkuus(reitti):
    # Laskee reitin laadun: suosii pitkiä paloja ja vähäistä kappalemäärää
    palat = [reitti[i+1] - reitti[i] for i in range(len(reitti)-1)]
    min_pala = min(palat)
    # Pisteet: mitä vähemmän paloja ja mitä suurempi minimipala, sen parempi
    return (-len(reitti), min_pala)

# --- KÄYTTÖLIITTYMÄ ---
st.set_page_config(page_title="Lautalaatikon Jakolaskin v1.7", layout="centered")
st.title("📦 Lautalaatikon Jakolaskin v1.7")
st.write("Optimoitu pitkille laudoille ja parhaalle mahdolliselle porrastukselle.")

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
            st.warning("Jakoa ei löytynyt. Kokeile lyhyempää jakoa tai pidempää lautaa.")
        else:
            # Etsitään paras PARI (A ja B)
            reitit.sort(key=laske_laadukkuus, reverse=True)
            
            paras_pari = None
            max_stagger_score = -1
            
            # Käydään läpi reittejä ja etsitään optimaalinen pari
            # Rajoitetaan hakua suorituskyvyn vuoksi parhaisiin ehdokkaisiin
            top_ehdokkaat = reitit[:50] 
            
            for i, r_a in enumerate(top_ehdokkaat):
                a_saumat_idx = [nostot.index(s) for s in r_a[1:-1]]
                
                for r_b in top_ehdokkaat[i:]:
                    b_saumat_idx = [nostot.index(s) for s in r_b[1:-1]]
                    
                    # Tarkistetaan porrastus A:n ja B:n välillä
                    safe = True
                    total_diff = 0
                    for sa in a_saumat_idx:
                        for sb in b_saumat_idx:
                            diff = abs(sa - sb)
                            if diff <= 1: # Ei saa olla sama tai viereinen
                                safe = False
                                break
                            total_diff += diff
                        if not safe: break
                    
                    if safe:
                        # Pisteytys: suositaan vähäistä kappalemäärää ja hyvää porrastusta
                        score = (-(len(r_a) + len(r_b)) * 1000) + total_diff
                        if score > max_stagger_score:
                            max_stagger_score = score
                            paras_pari = (r_a, r_b)

            if paras_pari:
                malli_a, malli_b = paras_pari
                st.success(f"Laskenta valmis! Löydetty optimaalinen limitys.")
                
                def tulosta_st(nimi, reitti):
                    palat = [int(reitti[i+1] - reitti[i]) for i in range(len(reitti)-1)]
                    st.subheader(nimi)
                    st.write(f"**Kappaleita:** {len(palat)} kpl")
                    st.info(f"**Laudat:** {' + '.join(map(str, palat))} mm")
                    st.write(f"**Saumat (mm):** {reitti[1:-1]}")

                tulosta_st("MALLI A (Pohja)", malli_a)
                st.divider()
                tulosta_st("MALLI B (Sivut / Vuorottelu)", malli_b)
            else:
                st.warning("Täydellistä porrastusta ei löytynyt vähällä kappalemäärällä. Näytetään paras yksittäinen jako.")
                tulosta_st("MALLI A", reitit[0])
