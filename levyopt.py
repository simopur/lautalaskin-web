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
        tag = f"{min(w,h)}x{max(w,h)}"
        return "#" + hashlib.md5(tag.encode()).hexdigest()[:6]

class BestFitOptimizer:
    def __init__(self, stock_w, stock_h, kerf):
        self.stock_w = stock_w
        self.stock_h = stock_h
        self.kerf = kerf
        self.sheets = []

    def optimize(self, panels):
        sorted_panels = sorted(panels, key=lambda p: p.w * p.h, reverse=True)
        
        for p in sorted_panels:
            best_fit = None
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
        if rem_w > rem_h:
            if rem_w > 0: sheet['free_rects'].append({'x': rect['x'] + w + self.kerf, 'y': rect['y'], 'w': rem_w, 'h': rect['h']})
            if rem_h > 0: sheet['free_rects'].append({'x': rect['x'], 'y': rect['y'] + h + self.kerf, 'w': w, 'h': rem_h})
        else:
            if rem_h > 0: sheet['free_rects'].append({'x': rect['x'], 'y': rect['y'] + h + self.kerf, 'w': rect['w'], 'h': rem_h})
            if rem_w > 0: sheet['free_rects'].append({'x': rect['x'] + w + self.kerf, 'y': rect['y'], 'w': rem_w, 'h': h})

def group_layouts(sheets):
    unique_layouts = []
    for sheet in sheets:
        # Sormenjälkeen mukaan paneelit JA vapaat alueet (hukkapalat)
        fp_panels = sorted([(p.w, p.h, p.x, p.y) for p in sheet['panels']])
        fp_waste = sorted([(r['w'], r['h'], r['x'], r['y']) for r in sheet['free_rects']])
        fingerprint = (tuple(fp_panels), tuple(fp_waste))
        
        found = False
        for layout in unique_layouts:
            if layout['fingerprint'] == fingerprint:
                layout['count'] += 1
                found = True; break
        if not found:
            unique_layouts.append({
                'panels': sheet['panels'], 
                'waste': sheet['free_rects'],
                'fingerprint': fingerprint, 
                'count': 1
            })
    return unique_layouts

def nayta_levyoptimoija():
    st.subheader("📐 Levyoptimoija v3.2 (Hukkapala-analyysi)")
    
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
        raw = st.text_area("Liitä Excel-data (Nimi, Pituus, Leveys...):")
        # Lisää parse_excel_input kutsu tähän jos käytössä

    if palat:
        opt = BestFitOptimizer(s_w, s_h, kerf)
        opt.optimize(palat)
        layouts = group_layouts(opt.sheets)

        # Kokonaistilastot
        st.divider()
        m1, m2 = st.columns(2)
        total_used = sum(p.w * p.h for p in palat)
        total_stock = len(opt.sheets) * s_w * s_h
        yield_pct = (total_used / total_stock * 100) if total_stock > 0 else 0
        m1.metric("Levyjä yhteensä", f"{len(opt.sheets)} kpl")
        m2.metric("Hyötykäyttö", f"{yield_pct:.1f} %", f"{100-yield_pct:.1f} % hukkaa", delta_color="inverse")

        kaikki_hukkapalat = []

        for i, l in enumerate(layouts):
            with st.expander(f"Layout {chr(65+i)} — {l['count']} kpl", expanded=True):
                c1, c2 = st.columns([1, 2.5])
                with c1:
                    st.write("**Osat tässä layoutissa:**")
                    p_info = pd.DataFrame([{"Pala": p.label, "Koko": f"{p.w}x{p.h}"} for p in l['panels']])
                    st.dataframe(p_info, hide_index=True)
                
                with c2:
                    fig, ax = plt.subplots(figsize=(7, 3))
                    # Tausta
                    ax.add_patch(patches.Rectangle((0, 0), s_w, s_h, facecolor='none', edgecolor='black', lw=1))
                    
                    # 1. Piirretään varsinaiset paneelit
                    for p in l['panels']:
                        ax.add_patch(patches.Rectangle((p.x, p.y), p.w, p.h, facecolor=p.color, edgecolor='black', alpha=0.9, lw=0.5))
                        if p.w > 100 and p.h > 100:
                            ax.text(p.x+p.w/2, p.y+p.h/2, f"{p.w}x{p.h}", ha='center', va='center', fontsize=5, fontweight='bold', color='white')
                    
                    # 2. Piirretään hukkapalat (punaiset kenoviivat)
                    for r in l['waste']:
                        # Lisätään koontiin (määrä huomioiden)
                        kaikki_hukkapalat.append({'L': r['w'], 'K': r['h'], 'lkm': l['count']})
                        
                        ax.add_patch(patches.Rectangle(
                            (r['x'], r['y']), r['w'], r['h'], 
                            facecolor='none', edgecolor='red', hatch='\\\\\\', alpha=0.5, lw=0.5
                        ))
                        # Näytetään hukan koko jos se on riittävän suuri
                        if r['w'] > 80 and r['h'] > 80:
                            ax.text(r['x']+r['w']/2, r['y']+r['h']/2, f"{int(r['w'])}x{int(r['h'])}", 
                                    ha='center', va='center', fontsize=4, color='red', backgroundcolor='white', alpha=0.7)

                    ax.set_xlim(0, s_w); ax.set_ylim(0, s_h); ax.set_aspect('equal')
                    ax.axis('off')
                    st.pyplot(fig)
                    plt.close()

        # --- KIRJALLINEN KOONTI HUKKAPALOISTA ---
        if kaikki_hukkapalat:
            st.divider()
            st.subheader("📦 Hukkapalojen ja jämäpalojen koonti")
            hukka_df = pd.DataFrame(kaikki_hukkapalat)
            # Ryhmitellään samanlaiset hukat
            koonti = hukka_df.groupby(['L', 'K']).sum().reset_index()
            koonti = koonti.sort_values(by=['L', 'K'], ascending=False)
            
            st.write("Alla on listaus kaikista sahauksessa syntyvistä hukka- ja jämäpaloista:")
            cols = st.columns(3)
            for idx, row in koonti.iterrows():
                with cols[idx % 3]:
                    st.info(f"**{int(row['L'])} x {int(row['K'])} mm**\n\nMäärä: {int(row['lkm'])} kpl")
