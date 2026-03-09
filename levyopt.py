import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import pandas as pd

class Panel:
    def __init__(self, w, h, label="", color='#3498db'):
        self.w, self.h = w, h
        self.label = label
        self.color = color
        self.x, self.y = 0, 0
        self.is_rotated = False

class GuillotineOptimizer:
    def __init__(self, stock_w, stock_h, kerf):
        self.stock_w = stock_w
        self.stock_h = stock_h
        self.kerf = kerf
        self.sheets = []

    def optimize(self, panels):
        # Lajittelu pinta-alan mukaan tehostaa pakkaamista
        sorted_panels = sorted(panels, key=lambda p: p.w * p.h, reverse=True)
        
        for p in sorted_panels:
            placed = False
            # 1. Yritetään sijoittaa olemassa oleville levyille
            for sheet in self.sheets:
                if self._fit_in_free_rects(p, sheet):
                    placed = True
                    break
            
            # 2. Jos ei mahdu, luodaan uusi levy
            if not placed:
                new_sheet = {
                    'panels': [],
                    'free_rects': [{'x': 0, 'y': 0, 'w': self.stock_w, 'h': self.stock_h}]
                }
                self._fit_in_free_rects(p, new_sheet)
                self.sheets.append(new_sheet)

    def _fit_in_free_rects(self, p, sheet):
        best_rect_idx = -1
        chosen_w, chosen_h, chosen_rot = 0, 0, False
        
        # Kokeillaan molempia asentoja
        for rot in [False, True]:
            w, h = (p.h, p.w) if rot else (p.w, p.h)
            for i, rect in enumerate(sheet['free_rects']):
                if w <= rect['w'] and h <= rect['h']:
                    best_rect_idx = i
                    chosen_w, chosen_h, chosen_rot = w, h, rot
                    break
            if best_rect_idx != -1: break

        if best_rect_idx != -1:
            rect = sheet['free_rects'].pop(best_rect_idx)
            p.x, p.y, p.w, p.h, p.is_rotated = rect['x'], rect['y'], chosen_w, chosen_h, chosen_rot
            sheet['panels'].append(p)
            
            # Jaetaan jäljelle jäänyt tila kahdeksi uudeksi vapaaksi suorakaiteeksi (Guillotine split)
            rem_w = rect['w'] - chosen_w - self.kerf
            rem_h = rect['h'] - chosen_h - self.kerf
            
            if rem_w > 0:
                sheet['free_rects'].append({'x': rect['x'] + chosen_w + self.kerf, 'y': rect['y'], 'w': rem_w, 'h': rect['h']})
            if rem_h > 0:
                sheet['free_rects'].append({'x': rect['x'], 'y': rect['y'] + chosen_h + self.kerf, 'w': chosen_w, 'h': rem_h})
            return True
        return False

def group_layouts(sheets):
    unique = []
    for s in sheets:
        fp = tuple(sorted([(p.w, p.h, p.x, p.y) for p in s['panels']]))
        found = False
        for l in unique:
            if l['fp'] == fp:
                l['count'] += 1
                found = True; break
        if not found:
            unique.append({'panels': s['panels'], 'fp': fp, 'count': 1})
    return unique

def nayta_levyoptimoija():
    st.subheader("📐 Levyoptimoija v2.0")
    
    with st.sidebar:
        s_w = st.number_input("Levy Pituus", value=2400)
        s_h = st.number_input("Levy Leveys", value=1200)
        kerf = st.number_input("Terä (mm)", value=4)
        input_type = st.radio("Syöttö", ["Manuaalinen", "Excel-kopio"])

    palat = []
    if input_type == "Manuaalinen":
        df = pd.DataFrame([{"Nimi": "Osa 1", "Pituus": 800, "Leveys": 600, "Kpl": 10}])
        ed = st.data_editor(df, num_rows="dynamic", use_container_width=True)
        if st.button("Optimoi Sahaus"):
            for _, r in ed.iterrows():
                for _ in range(int(r["Kpl"])):
                    palat.append(Panel(int(r["Pituus"]), int(r["Leveys"]), r["Nimi"]))
    else:
        full_w = st.number_input("Suikaleen leveys", value=1220)
        raw = st.text_area("Liitä tähän:")
        if raw:
            # (Excel-parsiminen kuten aiemmin)
            pass

    if palat:
        opt = GuillotineOptimizer(s_w, s_h, kerf)
        opt.optimize(palat)
        layouts = group_layouts(opt.sheets)
        
        # Tiivis yhteenveto
        st.write(f"**Yhteensä:** {len(opt.sheets)} levyä | **Erilaisia kaavioita:** {len(layouts)}")
        
        for i, l in enumerate(layouts):
            with st.container():
                c1, c2 = st.columns([1, 2])
                with c1:
                    st.markdown(f"### Layout {chr(65+i)}")
                    st.markdown(f"**Määrä: {l['count']} kpl**")
                    # Listataan palat taulukkoon, kuten esimerkkikuvassasi
                    p_data = [{"Pala": p.label, "Mitat": f"{p.w}x{p.h}"} for p in l['panels']]
                    st.table(pd.DataFrame(p_data))
                
                with c2:
                    fig, ax = plt.subplots(figsize=(6, 3))
                    ax.add_patch(patches.Rectangle((0, 0), s_w, s_h, facecolor='#f0f0f0', edgecolor='black', lw=2))
                    for p in l['panels']:
                        ax.add_patch(patches.Rectangle((p.x, p.y), p.w, p.h, facecolor=p.color, edgecolor='black', alpha=0.7))
                        if p.w > 150 and p.h > 150:
                            ax.text(p.x+p.w/2, p.y+p.h/2, f"{p.w}\nx\n{p.h}", ha='center', va='center', fontsize=6)
                    ax.set_xlim(0, s_w); ax.set_ylim(0, s_h); ax.set_aspect('equal')
                    ax.axis('off')
                    plt.tight_layout(pad=0)
                    st.pyplot(fig)
                    plt.close()
            st.divider()
