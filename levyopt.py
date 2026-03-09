import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import pandas as pd

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
                sheets.append({'panels': [], 'shelves': []})
                sheet = sheets[-1]
                bw, bh, br = min(opts, key=lambda x: x[1])
                p.w, p.h, p.is_rotated, p.x, p.y = bw, bh, br, 0, 0
                sheet['shelves'].append({'y': 0, 'h': bh, 'rem_w': s_w - (bw + kerf)})
                sheet['panels'].append(p)
    return sheets

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
    st.header("📐 Levyjen sahausoptimointi")
    
    with st.sidebar:
        st.subheader("Varastolevyn asetukset")
        s_w = st.number_input("Varastolevyn pituus (mm)", value=2700)
        s_h = st.number_input("Varastolevyn leveys (mm)", value=1200)
        kerf = st.slider("Terän hukka (mm)", 0, 10, 4)
    
    input_method = st.radio("Valitse syöttötapa:", ["Excel-kopiointi", "Manuaalinen syöttö"], horizontal=True)
    
    palat = []
    if input_method == "Excel-kopiointi":
        full_w = st.number_input("Täyden suikaleen leveys (mm)", value=1220)
        excel_input = st.text_area("Liitä Excel-tiedot tähän:", height=150)
        if excel_input:
            palat = parse_excel_input(excel_input, full_w)
    else:
        st.write("Lisää sahattavat palat taulukkoon:")
        df_init = pd.DataFrame([{"Nimi": "Pala 1", "Leveys": 1132, "Korkeus": 1000, "Kpl": 2}])
        edited_df = st.data_editor(df_init, num_rows="dynamic", use_container_width=True)
        if st.button("Laske manuaalisilla tiedoilla"):
            for _, row in edited_df.iterrows():
                for _ in range(int(row["Kpl"])):
                    palat.append(Panel(int(row["Leveys"]), int(row["Korkeus"]), row["Nimi"]))

    if palat:
        kaikki_levyt = optimize_sheets(palat, s_w, s_h, kerf)
        layouts = group_layouts(kaikki_levyt)
        
        # Yhteenveto
        total_area = s_w * s_h * len(kaikki_levyt)
        used_area = sum(p.w * p.h for p in palat)
        yield_pct = (used_area / total_area * 100) if total_area > 0 else 0
        
        st.divider()
        c1, c2, c3 = st.columns(3)
        c1.metric("Levyjä yhteensä", f"{len(kaikki_levyt)} kpl")
        c2.metric("Erilaisia layoutteja", f"{len(layouts)} kpl")
        c3.metric("Hyötykäyttö", f"{yield_pct:.1f} %")

        # Visualisointi sarakkeissa koon pienentämiseksi
        for i, layout in enumerate(layouts):
            layout_id = chr(65 + i)
            st.markdown(f"#### Layout {layout_id} (Toistetaan {layout['count']} kertaa)")
            
            # Luodaan sarakkeet, joilla kuva saadaan pienemmäksi (keskelle)
            _, viz_col, _ = st.columns([0.1, 0.8, 0.1])
            
            with viz_col:
                fig, ax = plt.subplots(figsize=(7, 2.5)) # Pienempi figuuri
                ax.add_patch(patches.Rectangle((0, 0), s_w, s_h, facecolor='#f8f9fa', edgecolor='black', lw=1.5))
                
                for p in layout['panels']:
                    ax.add_patch(patches.Rectangle((p.x, p.y), p.w, p.h, edgecolor='navy', facecolor=p.color, alpha=0.5))
                    ax.text(p.x + p.w/2, p.y + p.h/2, f"{p.label}\n{p.w}x{p.h}", ha='center', va='center', fontsize=6)
                
                ax.set_xlim(-50, s_w + 50)
                ax.set_ylim(-50, s_h + 50)
                ax.set_aspect('equal')
                ax.axis('off') # Poistetaan akselit turhan tilan viemiseksi
                st.pyplot(fig)
                plt.close(fig)
