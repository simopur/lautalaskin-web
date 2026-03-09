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
        dims = sorted([w, h])
        tag = f"{dims[0]}x{dims[1]}"
        return "#" + hashlib.md5(tag.encode()).hexdigest()[:6]

class MaxRectsOptimizer:
    def __init__(self, stock_w, stock_h, kerf):
        self.stock_w = stock_w
        self.stock_h = stock_h
        self.kerf = kerf
        self.sheets = []

    def optimize(self, panels):
        # Best-Fit Decreasing: lajitellaan pinta-alan mukaan
        sorted_panels = sorted(panels, key=lambda p: p.w * p.h, reverse=True)
        
        for p in sorted_panels:
            best_fit = None 
            for s_idx, sheet in enumerate(self.sheets):
                for rect in sheet['free_rects']:
                    for rot in [False, True]:
                        w, h = (p.h, p.w) if rot else (p.w, p.h)
                        if w <= rect['w'] and h <= rect['h']:
                            # Valitaan sijoitus, joka on mahdollisimman lähellä "pohjaa"
                            score = rect['y'] + h 
                            if best_fit is None or score < best_fit[5]:
                                best_fit = (s_idx, rect, w, h, rot, score)
            
            if best_fit:
                s_idx, rect, w, h, rot, _ = best_fit
                self._place_pala(p, self.sheets[s_idx], rect, w, h, rot)
            else:
                new_sheet = {
                    'panels': [], 
                    'free_rects': [{'x': 0, 'y': 0, 'w': self.stock_w, 'h': self.stock_h}]
                }
                self.sheets.append(new_sheet)
                w, h, rot = (p.w, p.h, False) if p.w <= self.stock_w and p.h <= self.stock_h else (p.h, p.w, True)
                self._place_pala(p, new_sheet, new_sheet['free_rects'][0], w, h, rot)

    def _place_pala(self, p, sheet, used_rect, w, h, rot):
        p.x, p.y, p.w, p.h, p.is_rotated = used_rect['x'], used_rect['y'], w, h, rot
        sheet['panels'].append(p)
        
        new_free = []
        for r in sheet['free_rects']:
            # Tarkistetaan leikkaako uusi pala vapaan suorakaiteen kanssa
            if not (p.x >= r['x'] + r['w'] or p.x + w + self.kerf <= r['x'] or 
                    p.y >= r['y'] + r['h'] or p.y + h + self.kerf <= r['y']):
                if p.x > r['x']:
                    new_free.append({'x': r['x'], 'y': r['y'], 'w': p.x - r['x'], 'h': r['h']})
                if p.x + w + self.kerf < r['x'] + r['w']:
                    new_free.append({'x': p.x + w + self.kerf, 'y': r['y'], 'w': r['x'] + r['w'] - (p.x + w + self.kerf), 'h': r['h']})
                if p.y > r['y']:
                    new_free.append({'x': r['x'], 'y': r['y'], 'w': r['w'], 'h': p.y - r['y']})
                if p.y + h + self.kerf < r['y'] + r['h']:
                    new_free.append({'x': r['x'], 'y': p.y + h + self.kerf, 'w': r['w'], 'h': r['y'] + r['h'] - (p.y + h + self.kerf)})
            else:
                new_free.append(r)
        sheet['free_rects'] = self._cleanup_rects(new_free)

    def _cleanup_rects(self, rects):
        unique = []
        for r1 in sorted(rects, key=lambda r: r['w'] * r['h'], reverse=True):
            keep = True
            for r2 in unique:
                if r1['x'] >= r2['x'] and r1['y'] >= r2['y'] and \
                   r1['x'] + r1['w'] <= r2['x'] + r2['w'] and r1['y'] + r1['h'] <= r2['y'] + r2['h']:
                    keep = False; break
            if keep: unique.append(r1)
        return unique

def parse_excel_input(text, full_w):
    panels = []
    lines = text.strip().split('\n')
    for line in lines:
        parts = line.split('\t')
        if len(parts) < 6: continue
        try:
            nimi = parts[0]
            pituus = int(float(parts[1].replace(',', '.')))
            taysi_lkm = int(parts[3])
            jatko_w = int(parts[4])
            kpl = int(parts[5])
            
            # Lisätään täydet levyt
            for _ in range(kpl * taysi_lkm):
                panels.append(Panel(pituus, full_w, f"{nimi} (T)"))
            # Lisätään jatkopala
            if jatko_w > 0:
                for _ in range(kpl):
                    panels.append(Panel(pituus, jatko_w, f"{nimi} (J)"))
        except: continue
    return panels

def group_layouts(sheets):
    unique = []
    for s in sheets:
        fp = (tuple(sorted([(p.w, p.h, p.x, p.y) for p in s['panels']])), 
              tuple(sorted([(r['w'], r['h'], r['x'], r['y']) for r in s['free_rects'] if r['w']*r['h'] > 1000])))
        found = False
        for l in unique:
            if l['fp'] == fp:
                l['count'] += 1; found = True; break
        if not found:
            unique.append({'panels': s['panels'], 'waste': s['free_rects'], 'fp': fp, 'count': 1})
    return unique

def nayta_levyoptimoija():
    st.subheader("📐 Levyoptimoija v3.5 (MaxRects & Excel)")
    
    with st.sidebar:
        s_w = st.number_input("Levyn Pituus (mm)", value=2440)
        s_h = st.number_input("Levyn Leveys (mm)", value=1220)
        kerf = st.number_input("Terä (mm)", value=4)
        input_type = st.radio("Syöttö", ["Manuaalinen", "Excel-kopio"])

    palat = []
    if input_type == "Manuaalinen":
        df_init = pd.DataFrame([{"Nimi": "Osa 1", "Pit": 800, "Lev": 600, "Kpl": 5}])
        ed = st.data_editor(df_init, num_rows="dynamic", use_container_width=True)
        if st.button("Optimoi", type="primary"):
            for _, r in ed.iterrows():
                for _ in range(int(r["Kpl"])):
                    palat.append(Panel(int(r["Pit"]), int(r["Lev"]), r["Nimi"]))
    else:
        full_w = st.number_input("Täyden levyn leveys (mm)", value=1220)
        st.info("Kopioi solut: Nimi, Pituus, Kokonaislev., Täysiä levyjä, Jatkopala, Kpl")
        raw = st.text_area("Liitä Excel-data tähän:")
        if raw and st.button("Optimoi Excel-data"):
            palat = parse_excel_input(raw, full_w)

    if palat:
        opt = MaxRectsOptimizer(s_w, s_h, kerf)
        opt.optimize(palat)
        layouts = group_layouts(opt.sheets)

        # Kokonaistilastot m²
        total_u = sum(p.w * p.h for p in palat) / 1000000
        total_s = (len(opt.sheets) * s_w * s_h) / 1000000
        yield_pct = (total_u / total_s * 100) if total_s > 0 else 0
        
        st.divider()
        m1, m2 = st.columns(2)
        m1.metric("Levyjä", f"{len(opt.sheets)} kpl")
        m2.metric("Hyötykäyttö", f"{yield_pct:.1f} %", f"{(total_s-total_u):.3f} m² hukkaa", delta_color="inverse")

        hukka_lista = []
        for i, l in enumerate(layouts):
            with st.expander(f"Layout {chr(65+i)} — {l['count']} kpl", expanded=True):
                c1, c2 = st.columns([1, 2.5])
                with c1:
                    st.dataframe(pd.DataFrame([{"Osa": p.label, "Koko": f"{p.w}x{p.h}"} for p in l['panels']]), hide_index=True)
                with c2:
                    fig, ax = plt.subplots(figsize=(7, 2.8))
                    ax.add_patch(patches.Rectangle((0, 0), s_w, s_h, facecolor='none', edgecolor='black', lw=1))
                    for p in l['panels']:
                        ax.add_patch(patches.Rectangle((p.x, p.y), p.w, p.h, facecolor=p.color, edgecolor='black', alpha=0.9, lw=0.4))
                        if p.w > 120: ax.text(p.x+p.w/2, p.y+p.h/2, f"{p.w}x{p.h}", ha='center', va='center', fontsize=5, fontweight='bold', color='white')
                    for r in l['waste']:
                        hukka_lista.append({'L': r['w'], 'K': r['h'], 'lkm': l['count']})
                        ax.add_patch(patches.Rectangle((r['x'], r['y']), r['w'], r['h'], facecolor='none', edgecolor='#e74c3c', hatch='///', alpha=0.3, lw=0.3))
                        if r['w'] > 120 and r['h'] > 120:
                            ax.text(r['x']+r['w']/2, r['y']+r['h']/2, f"{int(r['w'])}x{int(r['h'])}", ha='center', va='center', fontsize=4, color='#c0392b', alpha=0.8)
                    ax.set_xlim(0, s_w); ax.set_ylim(0, s_h); ax.set_aspect('equal'); ax.axis('off')
                    st.pyplot(fig); plt.close()

        if hukka_lista:
            st.subheader("📦 Jämäpalojen koontitaulukko (m²)")
            h_df = pd.DataFrame(hukka_lista)
            koonti = h_df.groupby(['L', 'K']).sum().reset_index()
            koonti['m²'] = (koonti['L'] * koonti['K'] / 1000000)
            koonti = koonti.sort_values('m²', ascending=False)
            koonti.columns = ['Pituus', 'Leveys', 'Kpl', 'm²']
            st.dataframe(koonti.style.format({'m²': '{:.3f}'}), hide_index=True)
