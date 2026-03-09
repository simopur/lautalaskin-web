import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import pandas as pd
import hashlib

class Panel:
    def __init__(self, w, h, label=""):
        self.w, self.h = w, h
        self.label = label
        self.x, self.y = 0, 0
        self.is_rotated = False
        self.color = self._generate_color(w, h)

    def _generate_color(self, w, h):
        # Käytetään lajiteltuja mittoja, jotta sama pala eri päin saa saman värin
        dims = sorted([w, h])
        tag = f"{dims[0]}x{dims[1]}"
        return "#" + hashlib.md5(tag.encode()).hexdigest()[:6]

class BestFitOptimizer:
    def __init__(self, stock_w, stock_h, kerf):
        self.stock_w = stock_w
        self.stock_h = stock_h
        self.kerf = kerf
        self.sheets = []

    def optimize(self, panels):
        # Lajitellaan palat pinta-alan mukaan (Best-Fit Decreasing)
        sorted_panels = sorted(panels, key=lambda p: p.w * p.h, reverse=True)
        
        for p in sorted_panels:
            best_fit = None 
            
            # Etsitään optimaalisin paikka (pienin jäännösala)
            for s_idx, sheet in enumerate(self.sheets):
                for r_idx, rect in enumerate(sheet['free_rects']):
                    # Kokeillaan molemmat asennot: pysty (w, h) ja vaaka (h, w)
                    for rot in [False, True]:
                        w, h = (p.h, p.w) if rot else (p.w, p.h)
                        if w <= rect['w'] and h <= rect['h']:
                            # Lasketaan hukka tässä kolossa
                            score = (rect['w'] * rect['h']) - (w * h)
                            if best_fit is None or score < best_fit[2]:
                                best_fit = (s_idx, r_idx, score, w, h, rot)
            
            if best_fit:
                s_idx, r_idx, _, w, h, rot = best_fit
                sheet = self.sheets[s_idx]
                rect = sheet['free_rects'].pop(r_idx)
                self._place_and_split(p, sheet, rect, w, h, rot)
            else:
                # Aloitetaan uusi levy ja kokeillaan siinäkin kumpaakin suuntaa
                new_sheet = {'panels': [], 'free_rects': [{'x': 0, 'y': 0, 'w': self.stock_w, 'h': self.stock_h}]}
                rect = new_sheet['free_rects'].pop(0)
                # Valitaan asento, joka jättää enemmän tilaa pituussuunnassa (yleensä viisaampaa)
                if p.h <= self.stock_w and p.w <= self.stock_h and p.h > p.w:
                    w, h, rot = p.h, p.w, True
                else:
                    w, h, rot = p.w, p.h, False
                self._place_and_split(p, new_sheet, rect, w, h, rot)
                self.sheets.append(new_sheet)

    def _place_and_split(self, p, sheet, rect, w, h, rot):
        p.x, p.y, p.w, p.h, p.is_rotated = rect['x'], rect['y'], w, h, rot
        sheet['panels'].append(p)
        
        rem_w = rect['w'] - w - self.kerf
        rem_h = rect['h'] - h - self.kerf
        
        # Dynaaminen jako: jaetaan tila aina niin, että syntyy mahdollisimman suuria yhtenäisiä pintoja
        if rem_w > rem_h:
            if rem_w > 0: sheet['free_rects'].append({'x': rect['x'] + w + self.kerf, 'y': rect['y'], 'w': rem_w, 'h': rect['h']})
            if rem_h > 0: sheet['free_rects'].append({'x': rect['x'], 'y': rect['y'] + h + self.kerf, 'w': w, 'h': rem_h})
        else:
            if rem_h > 0: sheet['free_rects'].append({'x': rect['x'], 'y': rect['y'] + h + self.kerf, 'w': rect['w'], 'h': rem_h})
            if rem_w > 0: sheet['free_rects'].append({'x': rect['x'] + w + self.kerf, 'y': rect['y'], 'w': rem_w, 'h': h})

def nayta_levyoptimoija():
    st.subheader("📐 Levyoptimoija v3.4 (Parannettu kääntö)")
    
    with st.sidebar:
        s_w = st.number_input("Varastolevy Pituus (mm)", value=2440)
        s_h = st.number_input("Varastolevy Leveys (mm)", value=1220)
        kerf = st.number_input("Terä (mm)", value=4)
        input_type = st.radio("Syöttö", ["Manuaalinen", "Excel-kopio"])

    palat = []
    if input_type == "Manuaalinen":
        df_init = pd.DataFrame([{"Nimi": "Osa 1", "Pituus": 800, "Leveys": 600, "Kpl": 5}])
        ed = st.data_editor(df_init, num_rows="dynamic", use_container_width=True)
        if st.button("Laske Optimointi", type="primary"):
            for _, r in ed.iterrows():
                for _ in range(int(r["Kpl"])):
                    palat.append(Panel(int(r["Pituus"]), int(r["Leveys"]), r["Nimi"]))
    else:
        # Excel-parsiminen (oletetaan olevan app.py:ssa tai lisättynä tähän)
        pass

    if palat:
        opt = BestFitOptimizer(s_w, s_h, kerf)
        opt.optimize(palat)
        
        from levyopt import group_layouts
        layouts = group_layouts(opt.sheets)

        # Lasketaan globaali hyötykäyttö
        total_used = sum(p.w * p.h for p in palat)
        total_stock = len(opt.sheets) * s_w * s_h
        yield_pct = (total_used / total_stock * 100) if total_stock > 0 else 0
        
        st.divider()
        m1, m2 = st.columns(2)
        m1.metric("Levyjä yhteensä", f"{len(opt.sheets)} kpl")
        m2.metric("Hyötykäyttö", f"{yield_pct:.1f} %", f"{100-yield_pct:.1f} % hukkaa", delta_color="inverse")

        kaikki_hukkapalat = []

        for i, l in enumerate(layouts):
            with st.expander(f"Layout {chr(65+i)} — {l['count']} kpl", expanded=True):
                c1, c2 = st.columns([1, 2.5])
                with c1:
                    st.write("**Osat:**")
                    st.dataframe(pd.DataFrame([{"Osa": p.label, "Koko": f"{p.w}x{p.h}"} for p in l['panels']]), hide_index=True)
                
                with c2:
                    fig, ax = plt.subplots(figsize=(7, 3))
                    ax.add_patch(patches.Rectangle((0, 0), s_w, s_h, facecolor='none', edgecolor='black', lw=1))
                    
                    for p in l['panels']:
                        ax.add_patch(patches.Rectangle((p.x, p.y), p.w, p.h, facecolor=p.color, edgecolor='black', alpha=0.9, lw=0.4))
                        if p.w > 120 and p.h > 120:
                            ax.text(p.x+p.w/2, p.y+p.h/2, f"{p.w}x{p.h}", ha='center', va='center', fontsize=5, fontweight='bold', color='white')
                    
                    for r in l['waste']:
                        kaikki_hukkapalat.append({'L': r['w'], 'K': r['h'], 'lkm': l['count']})
                        ax.add_patch(patches.Rectangle((r['x'], r['y']), r['w'], r['h'], facecolor='none', edgecolor='#e74c3c', hatch='///', alpha=0.4, lw=0.4))
                        if r['w'] > 100 and r['h'] > 100:
                            ax.text(r['x']+r['w']/2, r['y']+r['h']/2, f"{int(r['w'])}x{int(r['h'])}", ha='center', va='center', fontsize=4, color='#c0392b', fontweight='bold')

                    ax.set_xlim(0, s_w); ax.set_ylim(0, s_h); ax.set_aspect('equal'); ax.axis('off')
                    st.pyplot(fig)
                    plt.close()

        # --- JÄMÄPALOJEN TAULUKKO (Nyt m²) ---
        if kaikki_hukkapalat:
            st.divider()
            st.subheader("📦 Jämäpalojen koontitaulukko")
            h_df = pd.DataFrame(kaikki_hukkapalat)
            koonti = h_df.groupby(['L', 'K']).sum().reset_index()
            
            # Lasketaan pinta-ala m² (mm * mm / 1 000 000)
            koonti['Pinta-ala (m²)'] = (koonti['L'] * koonti['K']) / 1000000
            koonti = koonti.sort_values(by='Pinta-ala (m²)', ascending=False)
            
            # Muotoillaan luvut selkeämmiksi
            koonti.columns = ['Pituus (mm)', 'Leveys (mm)', 'Kpl yhteensä', 'Pinta-ala (m²)']
            koonti['Pinta-ala (m²)'] = koonti['Pinta-ala (m²)'].map('{:,.3f}'.format)
            
            st.write("Järjestetty pinta-alan mukaan (suurimmat ensin).")
            st.dataframe(koonti, hide_index=True, use_container_width=True)
