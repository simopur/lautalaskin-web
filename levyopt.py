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
        # Luodaan uniikki väri mittojen perusteella
        self.color = self._generate_color(w, h)

    def _generate_color(self, w, h):
        # Generoidaan vakaa väri leveyden ja korkeuden perusteella
        tag = f"{min(w,h)}x{max(w,h)}"
        hex_color = "#" + hashlib.mdis(tag.encode()).hexdigest()[:6]
        return hex_color

class BestFitOptimizer:
    def __init__(self, stock_w, stock_h, kerf):
        self.stock_w = stock_w
        self.stock_h = stock_h
        self.kerf = kerf
        self.sheets = []

    def optimize(self, panels):
        # Lajitellaan palat (Best-Fit Decreasing)
        sorted_panels = sorted(panels, key=lambda p: p.w * p.h, reverse=True)
        
        for p in sorted_panels:
            best_fit = None # (sheet_idx, rect_idx, score, width, height, rotated)
            
            # Etsitään paras paikka kaikilta olemassa olevilta levyiltä
            for s_idx, sheet in enumerate(self.sheets):
                for r_idx, rect in enumerate(sheet['free_rects']):
                    for rot in [False, True]:
                        w, h = (p.h, p.w) if rot else (p.w, p.h)
                        if w <= rect['w'] and h <= rect['h']:
                            # Score: kuinka paljon tilaa jää jäljelle (pienempi on parempi)
                            score = (rect['w'] * rect['h']) - (w * h)
                            if best_fit is None or score < best_fit[2]:
                                best_fit = (s_idx, r_idx, score, w, h, rot)
            
            if best_fit:
                s_idx, r_idx, _, w, h, rot = best_fit
                sheet = self.sheets[s_idx]
                rect = sheet['free_rects'].pop(r_idx)
                self._place_and_split(p, sheet, rect, w, h, rot)
            else:
                # Luodaan uusi levy jos sopivaa koloa ei löytynyt
                new_sheet = {'panels': [], 'free_rects': [{'x': 0, 'y': 0, 'w': self.stock_w, 'h': self.stock_h}]}
                rect = new_sheet['free_rects'].pop(0)
                # Kokeillaan kumpaa asentoa tahansa uuden levyn aloitukseen
                w, h, rot = (p.w, p.h, False) if p.w <= self.stock_w and p.h <= self.stock_h else (p.h, p.w, True)
                self._place_and_split(p, new_sheet, rect, w, h, rot)
                self.sheets.append(new_sheet)

    def _place_and_split(self, p, sheet, rect, w, h, rot):
        p.x, p.y, p.w, p.h, p.is_rotated = rect['x'], rect['y'], w, h, rot
        sheet['panels'].append(p)
        
        # Guillotine split (Best-Fit tyylinen jako)
        rem_w = rect['w'] - w - self.kerf
        rem_h = rect['h'] - h - self.kerf
        
        if rem_w > rem_h: # Jaetaan pidemmän sivun mukaan sirpaleisuuden vähentämiseksi
            if rem_w > 0: sheet['free_rects'].append({'x': rect['x'] + w + self.kerf, 'y': rect['y'], 'w': rem_w, 'h': rect['h']})
            if rem_h > 0: sheet['free_rects'].append({'x': rect['x'], 'y': rect['y'] + h + self.kerf, 'w': w, 'h': rem_h})
        else:
            if rem_h > 0: sheet['free_rects'].append({'x': rect['x'], 'y': rect['y'] + h + self.kerf, 'w': rect['w'], 'h': rem_h})
            if rem_w > 0: sheet['free_rects'].append({'x': rect['x'] + w + self.kerf, 'y': rect['y'], 'w': rem_w, 'h': h})

def nayta_levyoptimoija():
    st.subheader("📐 Levyoptimoija v3.0 (Best-Fit)")
    
    with st.sidebar:
        s_w = st.number_input("Varastolevy Pituus", value=2440)
        s_h = st.number_input("Varastolevy Leveys", value=1220)
        kerf = st.number_input("Terä (mm)", value=4)
        input_type = st.radio("Syöttötapa", ["Manuaalinen", "Excel-kopio"])

    palat = []
    # (Tässä välissä manuaalisen ja excel-syötön koodi, kuten aiemmin)
    if input_type == "Manuaalinen":
        df = pd.DataFrame([{"Nimi": "Osa 1", "Pituus": 800, "Leveys": 600, "Kpl": 5}])
        ed = st.data_editor(df, num_rows="dynamic", use_container_width=True)
        if st.button("Laske Optimointi"):
            for _, r in ed.iterrows():
                for _ in range(int(r["Kpl"])):
                    palat.append(Panel(int(r["Pituus"]), int(r["Leveys"]), r["Nimi"]))

    if palat:
        opt = BestFitOptimizer(s_w, s_h, kerf)
        opt.optimize(palat)
        
        # Ryhmittely (Layout A, B...)
        from levyopt import group_layouts # Käytetään aiempaa ryhmittelyä
        layouts = group_layouts(opt.sheets)

        # Lasketaan globaali hyötykäyttö
        total_stock_area = len(opt.sheets) * s_w * s_h
        total_used_area = sum(p.w * p.h for p in palat)
        total_yield = (total_used_area / total_stock_area * 100) if total_stock_area > 0 else 0

        st.metric("Kokonais-Hyötykäyttö", f"{total_yield:.1f} %", delta=f"{100-total_yield:.1f} % hukkaa", delta_color="inverse")
        
        for i, l in enumerate(layouts):
            with st.container():
                c1, c2 = st.columns([1, 2])
                with c1:
                    st.markdown(f"#### Layout {chr(65+i)} ({l['count']} kpl)")
                    # Layout-kohtainen hyötykäyttö
                    l_used = sum(p.w * p.h for p in l['panels'])
                    l_yield = (l_used / (s_w * s_h)) * 100
                    st.caption(f"Käyttöaste: {l_yield:.1f} %")
                    
                    p_info = pd.DataFrame([{"Pala": p.label, "Mitat": f"{p.w}x{p.h}"} for p in l['panels']])
                    st.dataframe(p_info, hide_index=True, use_container_width=True)
                
                with c2:
                    fig, ax = plt.subplots(figsize=(6, 3))
                    ax.add_patch(patches.Rectangle((0, 0), s_w, s_h, facecolor='#ffffff', edgecolor='#333333', lw=1))
                    for p in l['panels']:
                        ax.add_patch(patches.Rectangle((p.x, p.y), p.w, p.h, facecolor=p.color, edgecolor='black', alpha=0.8, lw=0.5))
                        if p.w > 100 and p.h > 100:
                            ax.text(p.x+p.w/2, p.y+p.h/2, f"{p.w}x{p.h}", ha='center', va='center', fontsize=5, fontweight='bold')
                    ax.set_xlim(0, s_w); ax.set_ylim(0, s_h); ax.set_aspect('equal')
                    ax.axis('off')
                    plt.tight_layout(pad=0)
                    st.pyplot(fig)
                    plt.close()
            st.divider()
