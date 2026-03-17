import streamlit as st
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
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
    pystyyn = p.h > p.w * 1.2
    pituus = p.h if pystyyn else p.w
    leveys = p.w if pystyyn else p.h
    
    fs_leveys_raja = pituus / (len(teksti) * 0.7) / 6.0
    fs_korkeus_raja = leveys / 20
    fs = min(base_fs, fs_leveys_raja, fs_korkeus_raja)
    fs = max(fs, 2.0) 
    
    if p.w > 45 and p.h > 45:
        ax.text(p.x + p.w/2, p.y + p.h/2, teksti,
                ha='center', va='center', fontsize=fs,
                fontweight='bold', color=getattr(p, 'text_color', 'black'),
                rotation=90 if pystyyn else 0)

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
                        score = rect['y'] * 10 + rect['x']
                        if best_fit is None or score < best_fit[4]:
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
        active_lib = [item for item in library if item.get('Käytä', True) and int(item.get('Pit', 0)) > 0 and int(item.get('Lev', 0)) > 0]
        if not active_lib: return
        sorted_lib = sorted(active_lib, key=lambda x: int(x['Pit']) * int(x['Lev']), reverse=True)
        for sheet in self.sheets:
            placed_on_sheet = True
            while placed_on_sheet:
                placed_on_sheet = False
                for item in sorted_lib:
                    best_for_this_item = None
                    w_orig, h_orig = int(item['Pit']), int(item['Lev'])
                    for rect in sheet['free_rects']:
                        for rot in [False, True]:
                            w, h = (h_orig, w_orig) if rot else (w_orig, h_orig)
                            if w <= rect['w'] and h <= rect['h']:
                                score = rect['y'] * 10 + rect['x']
                                if best_for_this_item is None or score < best_for_this_item[4]:
                                    best_for_this_item = (rect, w, h, rot, score)
                    if best_for_this_item:
                        rect, w, h, rot, _ = best_for_this_item
                        p = Panel(w, h, f"{item['Nimi']} (Vakio)", is_standard=True)
                        p.x, p.y, p.is_rotated = rect['x'], rect['y'], rot
                        sheet['panels'].append(p); self._split_rects(sheet, p.x, p.y, w, h)
                        placed_on_sheet = True; break

# --- KIRJASTOJEN HALLINTA ---

KIRJASTO_TIEDOSTO = "vakiokoot.json"
LAATIKKO_TIEDOSTO = "vakiolaatikot.json"

def lataa_json(tiedosto, oletus):
    if os.path.exists(tiedosto):
        try:
            with open(tiedosto, "r") as f: return json.load(f)
        except: pass
    return oletus

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
    for i, l in enumerate(layouts):
        if i % 8 == 0:
            pdf.add_page(); pdf.set_font("helvetica", "B", 14); pdf.cell(0, 8, f"Sahauslistat - Sivu {int(i/8)+1}", ln=True, align="C")
        fig = Figure(figsize=(7, 3))
        ax = fig.add_subplot(111)
        ax.add_patch(patches.Rectangle((0, 0), s_w, s_h, facecolor='none', edgecolor='black', lw=1.2))
        for p in l['panels']:
            ax.add_patch(patches.Rectangle((p.x, p.y), p.w, p.h, facecolor=getattr(p, 'color', '#ffffff'), edgecolor='black', alpha=0.9, lw=0.4))
            piirra_paneelin_teksti(ax, p)
        for r in l['waste']:
            ax.add_patch(patches.Rectangle((r['x'], r['y']), r['w'], r['h'], facecolor='none', edgecolor='#e74c3c', hatch='///', alpha=0.2, lw=0.3))
        ax.set_xlim(0, s_w); ax.set_ylim(0, s_h); ax.set_aspect('equal'); ax.axis('off')
        img_buf = io.BytesIO(); fig.savefig(img_buf, format='png', dpi=180, bbox_inches='tight')
        row, col = (i % 8) // 2, (i % 8) % 2
        x_p, y_p = 10 + (col * 100), 20 + (row * 65)
        pdf.set_xy(x_p, y_p - 6); pdf.set_font("helvetica", "B", 10); pdf.cell(90, 6, f"Layout {chr(65+i)} - {l['count']} kpl", ln=False); pdf.image(img_buf, x=x_p, y=y_p, w=90)
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
    st.subheader("📐 Levyoptimoija v6.3")

    if 'opt_results' not in st.session_state: st.session_state.opt_results = None
    if 'kirjasto' not in st.session_state: st.session_state.kirjasto = lataa_json(KIRJASTO_TIEDOSTO, [{"Käytä": True, "Nimi": "Talla 200", "Pit": 200, "Lev": 200}])
    if 'laatikot' not in st.session_state: st.session_state.laatikot = lataa_json(LAATIKKO_TIEDOSTO, [{"Nimi": "Esimerkki", "Osat": "2kpl 400x400, 2kpl 600x400, 1kpl 600x400"}])

    with st.sidebar:
        st.header("Asetukset")
        s_w = st.number_input("Pituus (mm)", value=2440)
        s_h = st.number_input("Leveys (mm)", value=1220)
        kerf = st.number_input("Terä (mm)", value=4)
        do_fill = st.checkbox("Täytä hukka vakiokooilla", value=True)
        input_type = st.radio("Syöttötapa", ["Yhdistetty syöttö", "Excel-kopio"])
        
        st.divider()
        if st.button("🗑️ Nollaa laskenta"):
            st.session_state.opt_results = None; st.rerun()

        with st.expander("📦 Hallitse vakiotuotteita"):
            df_v = pd.DataFrame(st.session_state.kirjasto)
            if not df_v.empty:
                df_v["Pit"] = pd.to_numeric(df_v["Pit"], errors='coerce').fillna(0).astype(int)
                df_v["Lev"] = pd.to_numeric(df_v["Lev"], errors='coerce').fillna(0).astype(int)
                if 'Käytä' not in df_v.columns: df_v['Käytä'] = True
                df_v = df_v[['Käytä', 'Nimi', 'Pit', 'Lev']]
            edited_v = st.data_editor(df_v, num_rows="dynamic", use_container_width=True, key="kirjasto_editor")
            if st.button("Päivitä vakioluettelo"):
                st.session_state.kirjasto = edited_v.to_dict('records'); st.rerun()

        with st.expander("📦 Hallitse laatikkokirjastoa"):
            df_box = pd.DataFrame(st.session_state.laatikot)
            edited_box = st.data_editor(df_box, num_rows="dynamic", use_container_width=True, key="box_library_editor")
            if st.button("Päivitä laatikkokirjasto"):
                st.session_state.laatikot = edited_box.to_dict('records'); st.rerun()
            st.download_button(label="📥 Lataa vakiolaatikot.json", data=json.dumps(st.session_state.laatikot, indent=4), file_name="vakiolaatikot.json")

    if input_type == "Yhdistetty syöttö":
        col_box, col_man = st.columns(2)
        with col_box:
            st.write("### 📦 Vakiolaatikot")
            df_l = pd.DataFrame(st.session_state.laatikot)
            df_l["Kpl"] = 0 
            ed_l = st.data_editor(df_l, use_container_width=True, key="box_order_editor", column_config={"Kpl": st.column_config.NumberColumn(min_value=0)})
        with col_man:
            st.write("### ✏️ Yksittäiset osat")
            df_m = pd.DataFrame([{"Nimi": "Osa 1", "Pit": 800, "Lev": 600, "Kpl": 0}])
            ed_m = st.data_editor(df_m, num_rows="dynamic", use_container_width=True, key="man_ed")

        if st.button("Laske Optimointi", type="primary", use_container_width=True):
            palat = []
            for _, laatikko in ed_l.iterrows():
                maara = int(laatikko["Kpl"])
                if maara > 0:
                    for osa in laatikko["Osat"].split(','):
                        try:
                            k_per, mitat = int(osa.split('kpl')[0]), osa.split('kpl')[1].split('x')
                            for _ in range(maara * k_per): palat.append(Panel(int(mitat[0]), int(mitat[1]), laatikko["Nimi"]))
                        except: pass
            for _, r in ed_m.iterrows():
                if int(r.get("Kpl", 0)) > 0:
                    for _ in range(int(r["Kpl"])): palat.append(Panel(int(r["Pit"]), int(r["Lev"]), r["Nimi"]))
            if palat:
                opt = MaxRectsOptimizer(s_w, s_h, kerf); opt.optimize(palat)
                if do_fill: opt.fill_waste_with_standards(st.session_state.kirjasto)
                st.session_state.opt_results = {'sheets': opt.sheets, 'stock': (s_w, s_h)}; st.rerun()
    else:
        raw_data = st.text_area("Liitä Excel-data:")
        if st.button("Optimoi Excel-data", type="primary"):
            palat = parse_excel_input(raw_data, s_h)
            if palat:
                opt = MaxRectsOptimizer(s_w, s_h, kerf); opt.optimize(palat)
                if do_fill: opt.fill_waste_with_standards(st.session_state.kirjasto)
                st.session_state.opt_results = {'sheets': opt.sheets, 'stock': (s_w, s_h)}; st.rerun()

    if st.session_state.opt_results:
        res = st.session_state.opt_results
        sw, sh = res['stock']; layouts = group_layouts(res['sheets'])
        
        # --- METRIIKAT (v5.4 logiikka palautettu) ---
        total_used_area = sum(p.w * p.h for s in res['sheets'] for p in s['panels'] if not getattr(p, 'is_standard', False)) / 1e6
        total_standard_area = sum(p.w * p.h for s in res['sheets'] for p in s['panels'] if getattr(p, 'is_standard', False)) / 1e6
        total_stock_area = (len(res['sheets']) * sw * sh) / 1e6
        
        order_yield_pct = (total_used_area / total_stock_area * 100) if total_stock_area > 0 else 0
        total_yield_pct = ((total_used_area + total_standard_area) / total_stock_area * 100) if total_stock_area > 0 else 0
        waste_pct = 100 - total_yield_pct

        st.divider()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Levyjä yhteensä", f"{len(res['sheets'])} kpl")
        c2.metric("Tilausten hyöty", f"{order_yield_pct:.1f} %")
        if total_standard_area > 0:
            c3.metric("Kokonais hyöty", f"{total_yield_pct:.1f} %", f"+{(total_yield_pct-order_yield_pct):.1f} % vakioista")
        else:
            c3.metric("Kokonais hyöty", f"{total_yield_pct:.1f} %")
        c4.metric("Lopullinen hukka", f"{waste_pct:.1f} %", f"{(total_stock_area - total_used_area - total_standard_area):.3f} m²", delta_color="inverse")
        
        if total_standard_area > 0:
            st.success(f"✅ Vakiokokoilla pelastettiin materiaalia: **{total_standard_area:.3f} m²**")
        st.divider()

        st.download_button(label="📥 Lataa sahauslistat PDF", data=create_pdf_bytes(layouts, sw, sh), file_name="sahauslistat.pdf")

        for i, l in enumerate(layouts):
            with st.expander(f"Layout {chr(65+i)} — {l['count']} kpl", expanded=True):
                col_i, col_v = st.columns([1, 2.5])
                with col_i:
                    st.write("**Osat:**")
                    st.dataframe(pd.DataFrame([{"Osa": p.label, "Koko": f"{int(p.w)}x{int(p.h)}"} for p in l['panels'] if not getattr(p, 'is_standard', False)]), hide_index=True)
                with col_v:
                    fig = Figure(figsize=(7, 2.8))
                    ax = fig.add_subplot(111)
                    ax.add_patch(patches.Rectangle((0, 0), sw, sh, facecolor='none', edgecolor='black', lw=1))
                    for p in l['panels']:
                        ax.add_patch(patches.Rectangle((p.x, p.y), p.w, p.h, facecolor=getattr(p, 'color', '#ffffff'), edgecolor='black', alpha=0.9, lw=0.4))
                        piirra_paneelin_teksti(ax, p)
                    for r in l['waste']:
                        ax.add_patch(patches.Rectangle((r['x'], r['y']), r['w'], r['h'], facecolor='none', edgecolor='#e74c3c', hatch='///', alpha=0.2, lw=0.3))
                    ax.set_xlim(0, sw); ax.set_ylim(0, sh); ax.set_aspect('equal'); ax.axis('off')
                    st.pyplot(fig)
