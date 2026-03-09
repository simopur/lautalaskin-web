import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches

class Panel:
    def __init__(self, w, h, label="", color='skyblue'):
        self.w, self.h = w, h
        self.label = label
        self.color = color
        self.x, self.y = 0, 0
        self.is_rotated = False

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
            
            for _ in range(kpl * taysi_lkm):
                panels.append(Panel(pituus, full_w, f"{nimi} (T)"))
            if jatko_w > 0:
                for _ in range(kpl):
                    panels.append(Panel(pituus, jatko_w, f"{nimi} (J)", color='#ffcc99'))
        except: continue
    return panels

def optimize_sheets(panels, s_w, s_h, kerf):
    sheets = []
    sorted_p = sorted(panels, key=lambda p: max(p.w, p.h), reverse=True)
    
    for p in sorted_p:
        placed = False
        for sheet in sheets:
            for shelf in sheet['shelves']:
                for w, h, rot in [(p.w, p.h, False), (p.h, p.w, True)]:
                    if shelf['rem_w'] >= w and shelf['h'] >= h:
                        p.w, p.h, p.is_rotated, p.x, p.y = w, h, rot, s_w - shelf['rem_w'], shelf['y']
                        shelf['rem_w'] -= (w + kerf)
                        sheet['panels'].append(p)
                        placed = True; break
                if placed: break
            if placed: break
            
        if not placed:
            sheets.append({'panels': [], 'shelves': []})
            sheet = sheets[-1]
            y = sum(s['h'] + kerf for s in sheet['shelves'])
            opts = [o for o in [(p.w, p.h, False), (p.h, p.w, True)] if o[0] <= s_w]
            valid_opts = [o for o in opts if y + o[1] <= s_h]
            
            if valid_opts:
                bw, bh, br = min(valid_opts, key=lambda x: x[1])
                p.w, p.h, p.is_rotated, p.x, p.y = bw, bh, br, 0, y
                sheet['shelves'].append({'y': y, 'h': bh, 'rem_w': s_w - (bw + kerf)})
                sheet['panels'].append(p)
            else:
                # Jos ei mahdu nykyiselle, luodaan täysin uusi levy
                sheets.append({'panels': [], 'shelves': []})
                sheet = sheets[-1]
                bw, bh, br = min(opts, key=lambda x: x[1])
                p.w, p.h, p.is_rotated, p.x, p.y = bw, bh, br, 0, 0
                sheet['shelves'].append({'y': 0, 'h': bh, 'rem_w': s_w - (bw + kerf)})
                sheet['panels'].append(p)
    return sheets

def group_layouts(sheets):
    """Ryhmittelee identtiset sahauskuviot ja laskee toistot."""
    unique_layouts = []
    for sheet in sheets:
        # Luodaan uniikki sormenjälki paneelien mitoista ja sijainneista
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
    st.header("📐 Levyjen sahausoptimointi")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        s_w = st.number_input("Varastolevyn pituus (mm)", value=2440, key="stock_w")
        s_h = st.number_input("Varastolevyn leveys (mm)", value=1220, key="stock_h")
        full_w = st.number_input("Täyden suikaleen leveys (mm)", value=1220, key="full_w")
        kerf = st.slider("Terän hukka (mm)", 0, 10, 4, key="kerf_val")
        excel_input = st.text_area("Liitä Excel-tiedot:", height=200)

    with col2:
        if excel_input:
            palat = parse_excel_input(excel_input, full_w)
            kaikki_levyt = optimize_sheets(palat, s_w, s_h, kerf)
            layouts = group_layouts(kaikki_levyt)
            
            # Yhteenveto
            st.subheader("Yhteenveto")
            total_area = s_w * s_h * len(kaikki_levyt)
            used_area = sum(p.w * p.h for p in palat)
            yield_pct = (used_area / total_area * 100) if total_area > 0 else 0
            
            c_res1, c_res2, c_res3 = st.columns(3)
            c_res1.metric("Levyjä yhteensä", f"{len(kaikki_levyt)} kpl")
            c_res2.metric("Erilaisia layoutteja", f"{len(layouts)} kpl")
            c_res3.metric("Hyötykäyttö", f"{yield_pct:.1f} %")

            st.divider()

            # Layouttien visualisointi
            for i, layout in enumerate(layouts):
                layout_id = chr(65 + i) # A, B, C...
                st.subheader(f"Layout {layout_id}")
                st.info(f"**Toista tämä sahaus {layout['count']} kertaa**")
                
                fig, ax = plt.subplots(figsize=(10, 4))
                ax.add_patch(patches.Rectangle((0, 0), s_w, s_h, facecolor='#f8f9fa', edgecolor='black', lw=2))
                
                for p in layout['panels']:
                    ax.add_patch(patches.Rectangle((p.x, p.y), p.w, p.h, edgecolor='navy', facecolor=p.color, alpha=0.5))
                    rot = " (R)" if p.is_rotated else ""
                    ax.text(p.x + p.w/2, p.y + p.h/2, f"{p.label}{rot}\n{p.w}x{p.h}", ha='center', va='center', fontsize=7)
                
                ax.set_xlim(-50, s_w + 50)
                ax.set_ylim(-50, s_h + 50)
                ax.set_aspect('equal')
                st.pyplot(fig)
                plt.close(fig)
