import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import pandas as pd
import hashlib
import io
import json
import os
from fpdf import FPDF

# --- KIRJASTON HALLINTA ---

KIRJASTO_TIEDOSTO = "vakiokoot.json"

def lataa_kirjasto():
    """Lataa vakiokoot tiedostosta tai palauttaa oletukset."""
    if os.path.exists(KIRJASTO_TIEDOSTO):
        with open(KIRJASTO_TIEDOSTO, "r") as f:
            return json.load(f)
    return [
        {"Nimi": "Talla 200", "Pit": 200, "Lev": 200},
        {"Nimi": "Suikale 1200", "Pit": 1200, "Lev": 100}
    ]

# --- AIEMMAT LUOKAT (Panel, MaxRectsOptimizer, group_layouts, get_contrast_color) ---
# (Pidetään samana kuin v4.1, mutta lisätään kontrasti- ja PDF-parannukset)

def get_contrast_color(hex_color):
    hex_color = hex_color.lstrip('#')
    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    return "white" if luminance < 0.5 else "black"

class Panel:
    def __init__(self, w, h, label=""):
        self.w, self.h = w, h
        self.label = label
        self.x, self.y = 0, 0
        self.is_rotated = False
        dims = sorted([w, h])
        tag = f"{dims[0]}x{dims[1]}"
        self.color = "#" + hashlib.md5(tag.encode()).hexdigest()[:6]
        self.text_color = get_contrast_color(self.color)

# ... (MaxRectsOptimizer ja group_layouts pysyvät ennallaan) ...
# (Lisätään ne tähän kopioitavaan versioon varmuuden vuoksi)

class MaxRectsOptimizer:
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
                for rect in sheet['free_rects']:
                    for rot in [False, True]:
                        w, h = (p.h, p.w) if rot else (p.w, p.h)
                        if w <= rect['w'] and h <= rect['h']:
                            score = rect['y'] + h 
                            if best_fit is None or score < best_fit[5]:
                                best_fit = (s_idx, rect, w, h, rot, score)
            if best_fit:
                s_idx, r, w, h, rot, _ = best_fit
                self._place_pala(p, self.sheets[s_idx], r, w, h, rot)
            else:
                new_sheet = {'panels': [], 'free_rects': [{'x': 0, 'y': 0, 'w': self.stock_w, 'h': self.stock_h}]}
                self.sheets.append(new_sheet)
                w, h, rot = (p.w, p.h, False) if p.w <= self.stock_w and p.h <= self.stock_h else (p.h, p.w, True)
                self._place_pala(p, new_sheet, new_sheet['free_rects'][0], w, h, rot)

    def _place_pala(self, p, sheet, used_rect, w, h, rot):
        p.x, p.y, p.w, p.h, p.is_rotated = used_rect['x'], used_rect['y'], w, h, rot
        sheet['panels'].append(p)
        new_free = []
        for r in sheet['free_rects']:
            if not (p.x >= r['x'] + r['w'] or p.x + w + self.kerf <= r['x'] or 
                    p.y >= r['y'] + r['h'] or p.y + h + self.kerf <= r['y']):
                if p.x > r['x']: new_free.append({'x': r['x'], 'y': r['y'], 'w': p.x - r['x'], 'h': r['h']})
                if p.x + w + self.kerf < r['x'] + r['w']: new_free.append({'x': p.x + w + self.kerf, 'y': r['y'], 'w': r['x'] + r['w'] - (p.x + w + self.kerf), 'h': r['h']})
                if p.y > r['y']: new_free.append({'x': r['x'], 'y': r['y'], 'w': r['w'], 'h': p.y - r['y']})
                if p.y + h + self.kerf < r['y'] + r['h']: new_free.append({'x': r['x'], 'y': p.y + h + self.kerf, 'w': r['w'], 'h': r['y'] + r['h'] - (p.y + h + self.kerf)})
            else: new_free.append(r)
        sheet['free_rects'] = self._cleanup_rects(new_free)

    def _cleanup_rects(self, rects):
        unique = []
        for r1 in sorted(rects, key=lambda r: r['w'] * r['h'], reverse=True):
            keep = True
            for r2 in unique:
                if r1['x'] >= r2['x'] and r1['y'] >= r2['y'] and r1['x'] + r1['w'] <= r2['x'] + r2['w'] and r1['y'] + r1['h'] <= r2['y'] + r2['h']:
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
            nimi = str(parts[0]).strip()
            pituus = int(float(str(parts[1]).replace(',', '.')))
            taysi_lkm = int(float(str(parts[3]).replace(',', '.')))
            jatko_w = int(float(str(parts[4]).replace(',', '.')))
            kpl = int(float(str(parts[5]).replace(',', '.')))
            for _ in range(kpl * taysi_lkm): panels.append(Panel(pituus, full_w, f"{nimi} (T)"))
            if jatko_w > 0:
                for _ in range(kpl): panels.append(Panel(pituus, jatko_w, f"{nimi} (J)"))
        except Exception: continue
    return panels

def group_layouts(sheets):
    unique = []
    for s in sheets:
        fp_p = sorted([(p.w, p.h, p.x, p.y) for p in s['panels']])
        fp_w = sorted([(r['w'], r['h'], r['x'], r['y']) for r in s['free_rects'] if r['w']*r['h'] > 100])
        fingerprint = (tuple(fp_p), tuple(fp_w))
        found = False
        for l in unique:
            if l['fp'] == fingerprint:
                l['count'] += 1; found = True; break
        if not found:
            unique.append({'panels': s['panels'], 'waste': s['free_rects'], 'fp': fingerprint, 'count': 1})
    return unique

def create_pdf_bytes(layouts, s_w, s_h):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=10)
    w_mm, h_mm = 90, 45 
    for i, l in enumerate(layouts):
        if i % 8 == 0:
            pdf.add_page()
            pdf.set_font("helvetica", "B", 14)
            pdf.cell(0, 8, f"Sahauslistat - Sivu {int(i/8)+1}", ln=True, align="C")
        fig, ax = plt.subplots(figsize=(7, 3))
        ax.add_patch(patches.Rectangle((0, 0), s_w, s_h, facecolor='none', edgecolor='black', lw=1.2))
        for p in l['panels']:
            ax.add_patch(patches.Rectangle((p.x, p.y), p.w, p.h, facecolor=p.color, edgecolor='black', alpha=0.9, lw=0.4))
            if p.w > 120:
                ax.text(p.x+p.w/2, p.y+p.h/2, f"{p.w}x{p.h}", ha='center', va='center', fontsize=6, fontweight='bold', color=p.text_color)
        for r in l['waste']:
            ax.add_patch(patches.Rectangle((r['x'], r['y']), r['w'], r['h'], facecolor='none', edgecolor='#e74c3c', hatch='///', alpha=0.2, lw=0.3))
        ax.set_xlim(0, s_w); ax.set_ylim(0, s_h); ax.set_aspect('equal'); ax.axis('off')
        img_buf = io.BytesIO()
        plt.savefig(img_buf, format='png', dpi=180, bbox_inches='tight')
        plt.close(fig)
        row, col = (i % 8) // 2, (i % 8) % 2
        x_p, y_p = 10 + (col * 100), 20 + (row * 65)
        pdf.set_xy(x_p, y_p - 6)
        pdf.set_font("helvetica", "B", 10)
        pdf.cell(w_mm, 6, f"Layout {chr(65+i)} - {l['count']} kpl", ln=False)
        pdf.image(img_buf, x=x_p, y=y_p, w=w_mm)
    return bytes(pdf.output())

# --- NÄKYMÄ ---

def nayta_levyoptimoija():
    st.subheader("📐 Levyoptimoija v4.2")

    if 'opt_results' not in st.session_state:
        st.session_state.opt_results = None

    # Ladataan vakiokoot muistiin
    if 'kirjasto' not in st.session_state:
        st.session_state.kirjasto = lataa_kirjasto()

    with st.sidebar:
        st.header("Levyn asetukset")
        s_w = st.number_input("Varastolevyn Pituus (mm)", value=2440)
        s_h = st.number_input("Varastolevyn Leveys (mm)", value=1220)
        kerf = st.number_input("Sahanterä (mm)", value=4)
        input_type = st.radio("Syöttötapa", ["Manuaalinen", "Excel-kopio"])
        
        st.divider()
        with st.expander("📦 Hallitse vakiotuotteita"):
            # Muokattava taulukko vakiotuotteille
            df_v = pd.DataFrame(st.session_state.kirjasto)
            ed_v = st.data_editor(df_v, num_rows="dynamic", use_container_width=True, key="kirjasto_editor")
            if st.button("Päivitä kirjasto väliaikaisesti"):
                st.session_state.kirjasto = ed_v.to_dict('records')
            
            # Mahdollisuus ladata JSON-tiedosto GitHubia varten
            json_str = json.dumps(st.session_state.kirjasto, indent=4)
            st.download_button(
                label="Lataa vakiokoot.json",
                data=json_str,
                file_name="vakiokoot.json",
                mime="application/json",
                help="Lataa tämä tiedosto ja korvaa GitHubissa oleva vakiokoot.json, jos haluat tallentaa koot pysyvästi."
            )

    # Kirjaston käyttö laskennassa
    vakiopalat_laskentaan = []
    with st.expander("➕ Lisää vakiotuotteita täytteeksi"):
        st.write("Valitse kuinka monta kpl lisätään hukkakohdan täytteeksi:")
        for i, item in enumerate(st.session_state.kirjasto):
            c_v1, c_v2 = st.columns([3, 1])
            with c_v1:
                st.write(f"**{item['Nimi']}** ({item['Pit']}x{item['Lev']} mm)")
            with c_v2:
                v_kpl = st.number_input(f"Kpl", min_value=0, value=0, key=f"v_inp_{i}")
                if v_kpl > 0:
                    for _ in range(v_kpl):
                        vakiopalat_laskentaan.append(Panel(item['Pit'], item['Lev'], f"{item['Nimi']} (Vakio)"))

    # Syöttöosio
    palat = []
    if input_type == "Manuaalinen":
        df_init = pd.DataFrame([{"Nimi": "Osa 1", "Pit": 800, "Lev": 600, "Kpl": 5}])
        ed = st.data_editor(df_init, num_rows="dynamic", use_container_width=True)
        if st.button("Laske Optimointi", type="primary"):
            for _, r in ed.iterrows():
                for _ in range(int(r["Kpl"])):
                    palat.append(Panel(int(r["Pit"]), int(r["Lev"]), r["Nimi"]))
            palat.extend(vakiopalat_laskentaan) # Lisätään vakiokoot
            opt = MaxRectsOptimizer(s_w, s_h, kerf)
            opt.optimize(palat)
            st.session_state.opt_results = {'sheets': opt.sheets, 'stock': (s_w, s_h)}
            st.rerun()
    else:
        raw_data = st.text_area("Liitä Excel-data (Nimi, Pit, Lev, Täysiä, Jatko, Kpl):")
        if st.button("Optimoi Excel-data", type="primary"):
            palat = parse_excel_input(raw_data, s_h)
            if palat:
                palat.extend(vakiopalat_laskentaan) # Lisätään vakiokoot
                opt = MaxRectsOptimizer(s_w, s_h, kerf)
                opt.optimize(palat)
                st.session_state.opt_results = {'sheets': opt.sheets, 'stock': (s_w, s_h)}
                st.rerun()

    # Tulosten näyttäminen (sama kuin aiemmin)
    if st.session_state.opt_results:
        res = st.session_state.opt_results
        sw, sh = res['stock']
        layouts = group_layouts(res['sheets'])
        st.divider()
        
        with st.spinner("Valmistellaan PDF-tiedostoa..."):
            pdf_data = create_pdf_bytes(layouts, sw, sh)
            st.download_button(label="📥 Lataa sahauslistat PDF", data=pdf_data, file_name="sahauslistat.pdf", mime="application/pdf")

        kaikki_hukkapalat = []
        for i, l in enumerate(layouts):
            with st.expander(f"Layout {chr(65+i)} — {l['count']} kpl", expanded=True):
                col_info, col_viz = st.columns([1, 2.5])
                with col_info:
                    st.dataframe(pd.DataFrame([{"Osa": p.label, "Koko": f"{p.w}x{p.h}"} for p in l['panels']]), hide_index=True)
                with col_viz:
                    fig, ax = plt.subplots(figsize=(7, 2.8))
                    ax.add_patch(patches.Rectangle((0, 0), sw, sh, facecolor='none', edgecolor='black', lw=1))
                    for p in l['panels']:
                        ax.add_patch(patches.Rectangle((p.x, p.y), p.w, p.h, facecolor=p.color, edgecolor='black', alpha=0.9, lw=0.4))
                        ax.text(p.x+p.w/2, p.y+p.h/2, f"{p.w}x{p.h}", ha='center', va='center', fontsize=6, fontweight='bold', color=p.text_color)
                    for r in l['waste']:
                        kaikki_hukkapalat.append({'L': r['w'], 'K': r['h'], 'lkm': l['count']})
                        ax.add_patch(patches.Rectangle((r['x'], r['y']), r['w'], r['h'], facecolor='none', edgecolor='#e74c3c', hatch='///', alpha=0.2, lw=0.3))
                    ax.set_xlim(0, sw); ax.set_ylim(0, sh); ax.set_aspect('equal'); ax.axis('off')
                    st.pyplot(fig); plt.close()
        
        if kaikki_hukkapalat:
            st.divider()
            st.subheader("📦 Jämäpalat (m²)")
            h_df = pd.DataFrame(kaikki_hukkapalat).groupby(['L', 'K']).sum().reset_index()
            h_df['m²'] = (h_df['L'] * h_df['K'] / 1e6)
            st.dataframe(h_df.sort_values('m²', ascending=False).style.format({'m²': '{:.3f}'}), hide_index=True)
