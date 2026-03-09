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
        # Korjattu: hashlib.md5 (oli mdis)
        self.color = self._generate_color(w, h)

    def _generate_color(self, w, h):
        # Luodaan vakaa väri mittojen perusteella
        tag = f"{min(w,h)}x{max(w,h)}"
        hex_color = "#" + hashlib.md5(tag.encode()).hexdigest()[:6]
        return hex_color

class BestFitOptimizer:
    def __init__(self, stock_w, stock_h, kerf):
        self.stock_w = stock_w
        self.stock_h = stock_h
        self.kerf = kerf
        self.sheets = []

    def optimize(self, panels):
        # Lajitellaan palat pinta-alan mukaan (suurin ensin)
        sorted_panels = sorted(panels, key=lambda p: p.w * p.h, reverse=True)
        
        for p in sorted_panels:
            best_fit = None # (sheet_idx, rect_idx, leftover_area, w, h, rotated)
            
            # Etsitään optimaalisin paikka kaikilta levyiltä
            for s_idx, sheet in enumerate(self.sheets):
                for r_idx, rect in enumerate(sheet['free_rects']):
                    for rot in [False, True]:
                        w, h = (p.h, p.w) if rot else (p.w, p.h)
                        if w <= rect['w'] and h <= rect['h']:
                            leftover = (rect['w'] * rect['h']) - (w * h)
                            if best_fit is None or leftover < best_fit[2]:
                                best_fit = (s_idx, r_idx, leftover, w, h, rot)
            
            if best_fit:
                s_idx, r_idx, _, w, h, rot = best_fit
                sheet = self.sheets[s_idx]
                rect = sheet['free_rects'].pop(r_idx)
                self._place_and_split(p, sheet, rect, w, h, rot)
            else:
                # Uusi levy
                new_sheet = {
                    'panels': [], 
                    'free_rects': [{'x': 0, 'y': 0, 'w': self.stock_w, 'h': self.stock_h}]
                }
                rect = new_sheet['free_rects'].pop(0)
                w, h, rot = (p.w, p.h, False) if p.w <= self.stock_w and p.h <= self.stock_h else (p.h, p.w, True)
                self._place_and_split(p, new_sheet, rect, w, h, rot)
                self.sheets.append(new_sheet)

    def _place_and_split(self, p, sheet, rect, w, h, rot):
        p.x, p.y, p.w, p.h, p.is_rotated = rect['x'], rect['y'], w, h, rot
        sheet['panels'].append(p)
        
        rem_w = rect['w'] - w - self.kerf
        rem_h = rect['h'] - h - self.kerf
        
        # Guillotine split: jaetaan vapaa tila järkevästi
        if rem_w > rem_h:
            if rem_w > 0: sheet['free_rects'].append({'x': rect['x'] + w + self.kerf, 'y': rect['y'], 'w': rem_w, 'h': rect['h']})
            if rem_h > 0: sheet['free_rects'].append({'x': rect['x'], 'y': rect['y'] + h + self.kerf, 'w': w, 'h': rem_h})
        else:
            if rem_h > 0: sheet['free_rects'].append({'x': rect['x'], 'y': rect['y'] + h + self.kerf, 'w': rect['w'], 'h': rem_h})
            if rem_w > 0: sheet['free_rects'].append({'x': rect['x'] + w + self.kerf, 'y': rect['y'], 'w': rem_w, 'h': h})

def group_layouts(sheets):
    unique_layouts = []
    for sheet in sheets:
        fingerprint = tuple(sorted([(p.w, p.h, p.x, p.y) for p in sheet['panels']]))
        found = False
        for layout in unique_layouts:
            if layout['fingerprint'] == fingerprint:
                layout['count'] += 1
                found = True; break
        if not found:
            unique_layouts.append({'panels': sheet['panels'], 'fingerprint': fingerprint, 'count': 1})
    return unique_layouts

def nayta_levyoptimoija():
    st.subheader("📐 Levyoptimoija v3.1 (Best-Fit)")
    
    with st.sidebar:
        s_w = st.number_input("Varastolevy Pituus (mm)", value=2440)
        s_h = st.number_input("Varastolevy Leveys (mm)", value=1220)
        kerf = st.number_input("Sahanterä (mm)", value=4)
        input_type = st.radio("Syöttötapa", ["Manuaalinen", "Excel-kopio"])

    palat = []
    if input_type == "Manuaalinen":
        df_init = pd.DataFrame([{"Nimi": "Osa 1", "Pituus": 800, "Leveys": 600, "Kpl": 5}])
        ed = st.data_editor(df_init, num_rows="dynamic", use_container_width=True)
        if st.button("Laske Optimointi", type="primary"):
            for _, r in ed.iterrows():
                for _ in range(int(r["Kpl"])):
                    palat.append(Panel(int(r["Pituus"]), int(r["Leveys"]), r["Nimi"]))
    else:
        st.info("Kopioi sarakkeet: Nimi, Pituus, Leveys, Täysiä, Jatko, Kpl")
        raw = st.text_area("Liitä Excel-data:")
        if raw:
            # Tässä voisi olla aiempi parse_excel_input kutsu
            pass

    if palat:
        opt = BestFitOptimizer(s_w, s_h, kerf)
        opt.optimize(palat)
        layouts = group_layouts(opt.sheets)

        # Kokonaistilastot
        total_used = sum(p.w * p.h for p in palat)
        total_stock = len(opt.sheets) * s_w * s_h
        total_yield = (total_used / total_stock * 100) if total_stock > 0 else 0

        st.divider()
        m1, m2 = st.columns(2)
        m1.metric("Levyjä yhteensä", f"{len(opt.sheets)} kpl")
        m2.metric("Hyötykäyttö", f"{total_yield:.1f} %", f"{100-total_yield:.1f} % hukkaa", delta_color="inverse")

        for i, l in enumerate(layouts):
            with st.expander(f"Layout {chr(65+i)} — {l['count']} kpl", expanded=True):
                c1, c2 = st.columns([1, 2])
                with c1:
                    l_used = sum(p.w * p.h for p in l['panels'])
                    st.caption(f"Käyttöaste: {(l_used/(s_w*s_h))*100:.1f} %")
                    p_info = pd.DataFrame([{"Pala": p.label, "Mitat": f"{p.w}x{p.h}"} for p in l['panels']])
                    st.dataframe(p_info, hide_index=True)
                
                with c2:
                    fig, ax = plt.subplots(figsize=(6, 2.5))
                    ax.add_patch(patches.Rectangle((0, 0), s_w, s_h, facecolor='#ffffff', edgecolor='black', lw=1))
                    for p in l['panels']:
                        ax.add_patch(patches.Rectangle((p.x, p.y), p.w, p.h, facecolor=p.color, edgecolor='black', alpha=0.9, lw=0.5))
                        if p.w > 120 and p.h > 120:
                            ax.text(p.x+p.w/2, p.y+p.h/2, f"{p.w}x{p.h}", ha='center', va='center', fontsize=5, fontweight='bold', color='white' if p.color < "#888888" else 'black')
                    ax.set_xlim(0, s_w); ax.set_ylim(0, s_h); ax.set_aspect('equal')
                    ax.axis('off')
                    st.pyplot(fig)
                    plt.close()
