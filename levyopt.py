import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import pandas as pd
import hashlib
import io
import json
import os
from fpdf import FPDF

# --- APUFUNKTIOT ---

def get_contrast_color(hex_color):
    """Laskee kumpiko teksti (musta/valkoinen) erottuu paremmin taustasta."""
    hex_color = hex_color.lstrip('#')
    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    return "white" if luminance < 0.5 else "black"

def piirra_paneelin_teksti(ax, p, base_fs=6):
    """Laskee tekstin koon ja asennon niin, että se mahtuu palan sisään."""
    teksti = f"{int(p.w)}x{int(p.h)}"
    fs = min(base_fs, p.w / 18, p.h / 18)
    fs = max(fs, 2.5) 
    rotation = 90 if (p.h > p.w * 1.3) else 0
    if p.w > 40 and p.h > 40:
        ax.text(p.x + p.w/2, p.y + p.h/2, teksti,
                ha='center', va='center', fontsize=fs,
                fontweight='bold', color=getattr(p, 'text_color', 'black'),
                rotation=rotation)

class Panel:
    def __init__(self, w, h, label="", is_standard=False):
        self.w, self.h = int(w), int(h)
        self.label = label
        self.x, self.y = 0, 0
        self.is_rotated = False
        self.is_standard = is_standard
        if is_standard:
            self.color = "#95a5a6" 
        else:
            dims = sorted([self.w, self.h])
            tag = f"{dims[0]}x{dims[1]}"
            self.color = "#" + hashlib.md5(tag.encode()).hexdigest()[:6]
        self.text_color = get_contrast_color(self.color)

class MaxRectsOptimizer:
    def __init__(self, stock_w, stock_h, kerf):
        self.stock_w = int(stock_w); self.stock_h = int(stock_h); self.kerf = int(kerf)
        self.sheets = []

    def optimize(self, panels):
        sorted_panels = sorted(panels, key=lambda p: p.w * p.h, reverse=True)
        for p in sorted_panels: self._place_pala_best_fit(p)

    def _place_pala_best_fit(self, p):
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
            s_idx, rect, w, h, rot, _ = best_fit
            self._execute_placement(p, self.sheets[s_idx], rect, w, h, rot)
        else:
            new_sheet = {'panels': [], 'free_rects': [{'x': 0, 'y': 0, 'w': self.stock_w, 'h': self.stock_h}]}
            self.sheets.append(new_sheet); w, h, rot = (p.w, p.h, False) if p.w <= self.stock_w and p.h <= self.stock_h else (p.h, p.w, True)
            self._execute_placement(p, new_sheet, new_sheet['free_rects'][0], w, h, rot)

    def _execute_placement(self, p, sheet, used_rect, w, h, rot):
        p.x, p.y, p.w, p.h, p.is_rotated = used_rect['x'], used_rect['y'], w, h, rot
        sheet['panels'].append(p)
        self._split_rects(sheet, p.x, p.y, w, h)

    def _split_rects(self, sheet, x, y, w, h):
        new_free = []
        for r in sheet['free_rects']:
            if not (x >= r['x'] + r['w'] or x + w + self.kerf <= r['x'] or y >= r['y'] + r['h'] or y + h + self.kerf <= r['y']):
                if x > r['x']: new_free.append({'x': r['x'], 'y': r['y'], 'w': x - r['x'], 'h': r['h']})
                if x + w + self.kerf < r['x'] + r['w']: new_free.append({'x': x + w + self.kerf, 'y': r['y'], 'w': r['x'] + r['w'] - (x + w + self.kerf), 'h': r['h']})
                if y > r['y']: new_free.append({'x': r['x'], 'y': r['y'], 'w': r['w'], 'h': y - r['y']})
                if y + h + self.kerf < r['y'] + r['h']: new_free.append({'x': r['x'], 'y': y + h + self.kerf, 'w': r['w'], 'h': r['y'] + r['h'] - (y + h + self.kerf)})
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

    def fill_waste_with_standards(self, library):
        # Suodatetaan vain ne, joissa 'Käytä' on True
        active_lib = [item for item in library if item.get('Käytä', True)]
        sorted_lib = sorted(active_lib, key=lambda x: int(x['Pit']) * int(x['Lev']), reverse=True)
        
        for sheet in self.sheets:
            added_any = True
            while added_any:
                added_any = False
                for r_idx, rect in enumerate(sheet['free_rects']):
                    for item in sorted_lib:
                        for rot in [False, True]:
                            w, h = (int(item['Lev']), int(item['Pit'])) if rot else (int(item['Pit']), int(item['Lev']))
                            if w <= rect['w'] and h <= rect['h']:
                                p = Panel(w, h, f"{item['Nimi']} (Vakio)", is_standard=True)
                                p.x, p.y, p.is_rotated = rect['x'], rect['y'], rot
                                sheet['panels'].append(p); sheet['free_rects'].pop(r_idx); self._split_rects(sheet, p.x, p.y, w, h)
                                added_any = True; break
                        if added_any: break
                    if added_any: break

# --- KIRJASTO JA PDF ---

KIRJASTO_TIEDOSTO = "vakiokoot.json"

def lataa_kirjasto():
    if os.path.exists(KIRJASTO_TIEDOSTO):
        try:
            with open(KIRJASTO_TIEDOSTO, "r") as f:
                data = json.load(f)
                # Varmistetaan että kaikilla on 'Käytä' kenttä
                for item in data:
                    if 'Käytä' not in item: item['Käytä'] = True
                return data
        except: pass
    return [{"Nimi": "Talla 200", "Pit": 200, "Lev": 200, "Käytä": True}]

def group_layouts(sheets):
    unique = []
    for s in sheets:
        fp_p = sorted([(p.w, p.h, p.x, p.y, getattr(p, 'is_standard', False)) for p in s['panels']])
        fp_w = sorted([(r['w'], r['h'], r['x'], r['y']) for r in s['free_rects'] if r['w']*r['h'] > 100])
        fingerprint = (tuple(fp_p), tuple(fp_w))
        found = False
        for l in unique:
            if l['fp'] == fingerprint:
                l['count'] += 1; found = True; break
        if not found: unique.append({'panels': s['panels'], 'waste': s['free_rects'], 'fp': fingerprint, 'count': 1})
    return unique

def create_pdf_bytes(layouts, s_w, s_h):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=10)
    w_mm, h_mm = 90, 45 
    for i, l in enumerate(layouts):
        if i % 8 == 0:
            pdf.add_page(); pdf.set_font("helvetica", "B", 14); pdf.cell(0, 8, f"Sahauslistat - Sivu {int(i/8)+1}", ln=True, align="C")
        fig, ax = plt.subplots(figsize=(7, 3))
        ax.add_patch(patches.Rectangle((0, 0), s_w, s_h, facecolor='none', edgecolor='black', lw=1.2))
        for p in l['panels']:
            ax.add_patch(patches.Rectangle((p.x, p.y), p.w, p.h, facecolor=getattr(p, 'color', '#ffffff'), edgecolor='black', alpha=0.9, lw=0.4))
            piirra_paneelin_teksti(ax, p)
        for r in l['waste']:
            ax.add_patch(patches.Rectangle((r['x'], r['y']), r['w'], r['h'], facecolor='none', edgecolor='#e74c3c', hatch='///', alpha=0.2, lw=0.3))
        ax.set_xlim(0, s_w); ax.set_ylim(0, s_h); ax.set_aspect('equal'); ax.axis('off')
        img_buf = io.BytesIO(); plt.savefig(img_buf, format='png', dpi=180, bbox_inches='tight'); plt.close(fig)
        row, col = (i % 8) // 2, (i % 8) % 2
        x_p, y_p = 10 + (col * 100), 20 + (row * 65)
        pdf.set_xy(x_p, y_p - 6); pdf.set_font("helvetica", "B", 10); pdf.cell(w_mm, 6, f"Layout {chr(65+i)} - {l['count']} kpl", ln=False); pdf.image(img_buf, x=x_p, y=y_p, w=w_mm)
    return bytes(pdf.output())

def parse_excel_input(text, full_w):
    panels = []
    lines = text.strip().split('\n')
    for line in lines:
        parts = line.split('\t')
        if len(parts) < 6: continue
        try:
            nimi, pituus = str(parts[0]).strip(), int(float(str(parts[1]).replace(',', '.')))
            taysi_lkm, jatko_w, kpl = int(float(str(parts[3]))), int(float(str(parts[4]))), int(float(str(parts[5])))
            for _ in range(kpl * taysi_lkm): panels.append(Panel(pituus, full_w, f"{nimi} (T)"))
            if jatko_w > 0:
                for _ in range(kpl): panels.append(Panel(pituus, jatko_w, f"{nimi} (J)"))
        except: continue
    return panels

# --- KÄYTTÖLIITTYMÄ ---

def nayta_levyoptimoija():
    st.subheader("📐 Levyoptimoija v4.9")

    if 'opt_results' not in st.session_state: st.session_state.opt_results = None
    if 'kirjasto' not in st.session_state: st.session_state.kirjasto = lataa_kirjasto()

    with st.sidebar:
        st.header("Asetukset")
        s_w = st.number_input("Pituus (mm)", value=2440)
        s_h = st.number_input("Leveys (mm)", value=1220)
        kerf = st.number_input("Terä (mm)", value=4)
        do_fill = st.checkbox("Täytä hukka vakiokooilla", value=True)
        input_type = st.radio("Syöttö", ["Manuaalinen", "Excel-kopio"])
        
        st.divider()
        if st.button("🗑️ Nollaa laskenta"):
            st.session_state.opt_results = None
            st.rerun()

        with st.expander("📦 Hallitse vakiotuotteita"):
            # Luodaan taulukko, jossa 'Käytä' on mukana
            df_v = pd.DataFrame(st.session_state.kirjasto)
            if not df_v.empty:
                df_v["Pit"] = df_v["Pit"].astype(int)
                df_v["Lev"] = df_v["Lev"].astype(int)
                # Järjestetään sarakkeet loogisesti: Käytä ekaksi
                cols = ['Käytä', 'Nimi', 'Pit', 'Lev']
                df_v = df_v[[c for c in cols if c in df_v.columns] + [c for c in df_v.columns if c not in cols]]
            
            edited_v = st.data_editor(df_v, num_rows="dynamic", use_container_width=True, key="kirjasto_editor")
            
            if not edited_v.equals(df_v):
                st.session_state.kirjasto = edited_v.to_dict('records')
                st.rerun()

            st.divider()
            json_str = json.dumps(st.session_state.kirjasto, indent=4)
            st.download_button(label="📥 Lataa vakiokoot.json", data=json_str, file_name="vakiokoot.json", mime="application/json")

    palat = []
    if input_type == "Manuaalinen":
        df_init = pd.DataFrame([{"Nimi": "Osa 1", "Pit": 800, "Lev": 600, "Kpl": 5}])
        ed = st.data_editor(df_init, num_rows="dynamic", use_container_width=True)
        if st.button("Laske Optimointi", type="primary"):
            for _, r in ed.iterrows():
                for _ in range(int(r["Kpl"])): palat.append(Panel(int(r["Pit"]), int(r["Lev"]), r["Nimi"]))
            opt = MaxRectsOptimizer(s_w, s_h, kerf); opt.optimize(palat)
            if do_fill: opt.fill_waste_with_standards(st.session_state.kirjasto)
            st.session_state.opt_results = {'sheets': opt.sheets, 'stock': (s_w, s_h)}; st.rerun()
    else:
        raw_data = st.text_area("Liitä Excel-data (Nimi, Pit, Lev, Täysiä, Jatko, Kpl):")
        if st.button("Optimoi Excel-data", type="primary"):
            palat = parse_excel_input(raw_data, s_h)
            if palat:
                opt = MaxRectsOptimizer(s_w, s_h, kerf); opt.optimize(palat)
                if do_fill: opt.fill_waste_with_standards(st.session_state.kirjasto)
                st.session_state.opt_results = {'sheets': opt.sheets, 'stock': (s_w, s_h)}; st.rerun()

    if st.session_state.opt_results:
        res = st.session_state.opt_results
        sw, sh = res['stock']; layouts = group_layouts(res['sheets'])
        st.divider()
        
        # --- METRIIKAT ---
        total_used_area = sum(p.w * p.h for s in res['sheets'] for p in s['panels'] if not getattr(p, 'is_standard', False)) / 1e6
        total_standard_area = sum(p.w * p.h for s in res['sheets'] for p in s['panels'] if getattr(p, 'is_standard', False)) / 1e6
        total_stock_area = (len(res['sheets']) * sw * sh) / 1e6
        
        yield_pct = (total_used_area / total_stock_area * 100) if total_stock_area > 0 else 0
        waste_pct = 100 - yield_pct
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Levyjä", f"{len(res['sheets'])} kpl")
        m2.metric("Hyötykäyttö", f"{yield_pct:.1f} %")
        m3.metric("Hukkaprosentti", f"{waste_pct:.1f} %", f"{(total_stock_area-total_used_area):.3f} m²", delta_color="inverse")
        
        if total_standard_area > 0:
            st.info(f"💡 Hukasta pelastettu varastoon: **{total_standard_area:.3f} m²** vakiopaloina.")

        pdf_data = create_pdf_bytes(layouts, sw, sh)
        st.download_button(label="📥 Lataa PDF", data=pdf_data, file_name="sahauslistat.pdf", mime="application/pdf")

        for i, l in enumerate(layouts):
            with st.expander(f"Layout {chr(65+i)} — {l['count']} kpl", expanded=True):
                c_vis1, c_vis2 = st.columns([1, 2.5])
                with c_vis1:
                    osat = [p for p in l['panels'] if not getattr(p, 'is_standard', False)]
                    st.write("**Tilausosat:**")
                    st.dataframe(pd.DataFrame([{"Osa": p.label, "Koko": f"{int(p.w)}x{int(p.h)}"} for p in osat]), hide_index=True)
                    vakiot = [p for p in l['panels'] if getattr(p, 'is_standard', False)]
                    if vakiot:
                        st.write("**Varastoon (Vakio):**")
                        v_df = pd.DataFrame([{"Osa": p.label, "W": int(p.w), "H": int(p.h)} for p in vakiot])
                        st.dataframe(v_df.groupby(["Osa", "W", "H"]).size().reset_index(name="Kpl"), hide_index=True)

                with c_vis2:
                    fig, ax = plt.subplots(figsize=(7, 2.8))
                    ax.add_patch(patches.Rectangle((0, 0), sw, sh, facecolor='none', edgecolor='black', lw=1))
                    for p in l['panels']:
                        ax.add_patch(patches.Rectangle((p.x, p.y), p.w, p.h, facecolor=getattr(p, 'color', '#ffffff'), edgecolor='black', alpha=0.9, lw=0.4))
                        piirra_paneelin_teksti(ax, p)
                    for r in l['waste']:
                        ax.add_patch(patches.Rectangle((r['x'], r['y']), r['w'], r['h'], facecolor='none', edgecolor='#e74c3c', hatch='///', alpha=0.2, lw=0.3))
                    ax.set_xlim(0, sw); ax.set_ylim(0, sh); ax.set_aspect('equal'); ax.axis('off'); st.pyplot(fig); plt.close()
