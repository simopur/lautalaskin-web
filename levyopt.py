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
            # Puhdistetaan mahdolliset välilyönnit ja muutetaan numeroiksi
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
        except Exception as e:
            continue
    return panels

def optimize_sheets(panels, s_w, s_h, kerf):
    sheets = []
    # Lajittelu: yritetään sijoittaa pisimmät/suurimmat ensin
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
                        placed = True
                        break
                if placed: break
            if placed: break
            
        if not placed:
            if not sheets:
                sheets.append({'panels': [], 'shelves': []})
            
            sheet = sheets[-1]
            y = sum(s['h'] + kerf for s in sheet['shelves'])
            
            # Kokeillaan kääntöä uuden hyllyn luonnissa
            opts = [o for o in [(p.w, p.h, False), (p.h, p.w, True)] if o[0] <= s_w]
            valid_opts = [o for o in opts if y + o[1] <= s_h]
            
            if valid_opts:
                bw, bh, br = min(valid_opts, key=lambda x: x[1])
                p.w, p.h, p.is_rotated, p.x, p.y = bw, bh, br, 0, y
                sheet['shelves'].append({'y': y, 'h': bh, 'rem_w': s_w - (bw + kerf)})
                sheet['panels'].append(p)
            else:
                # Jos ei mahdu nykyiselle, luodaan uusi levy
                sheets.append({'panels': [], 'shelves': []})
                sheet = sheets[-1]
                bw, bh, br = min(opts, key=lambda x: x[1])
                p.w, p.h, p.is_rotated, p.x, p.y = bw, bh, br, 0, 0
                sheet['shelves'].append({'y': 0, 'h': bh, 'rem_w': s_w - (bw + kerf)})
                sheet['panels'].append(p)
    return sheets

def nayta_levyoptimoija():
    st.header("📐 Levyjen sahausoptimointi")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        s_w = st.number_input("Varastolevyn pituus (mm)", value=2700, key="stock_w")
        s_h = st.number_input("Varastolevyn leveys (mm)", value=1200, key="stock_h")
        full_w = st.number_input("Täyden suikaleen leveys (mm)", value=1220, key="full_w")
        kerf = st.slider("Terän hukka (mm)", 0, 10, 4, key="kerf_val")
        excel_input = st.text_area("Liitä Excel-tiedot (Kansi, Pituus, Leveys, Täysiä, Jatko, Kpl):", height=200)

    with col2:
        if excel_input:
            palat = parse_excel_input(excel_input, full_w)
            if not palat:
                st.warning("Dataa ei voitu lukea. Varmista, että kopioit Excelistä vähintään 6 saraketta.")
                return
                
            tulokset = optimize_sheets(palat, s_w, s_h, kerf)
            st.success(f"Tarvitaan {len(tulokset)} varastolevyä.")
            
            for i, sheet in enumerate(tulokset):
                fig, ax = plt.subplots(figsize=(10, 4))
                ax.add_patch(patches.Rectangle((0, 0), s_w, s_h, facecolor='#f8f9fa', edgecolor='black', lw=2))
                for p in sheet['panels']:
                    ax.add_patch(patches.Rectangle((p.x, p.y), p.w, p.h, edgecolor='navy', facecolor=p.color, alpha=0.5))
                    rot = " (R)" if p.is_rotated else ""
                    ax.text(p.x + p.w/2, p.y + p.h/2, f"{p.label}{rot}\n{p.w}x{p.h}", ha='center', va='center', fontsize=7)
                ax.set_xlim(-50, s_w + 50)
                ax.set_ylim(-50, s_h + 50)
                ax.set_aspect('equal')
                st.pyplot(fig)
                plt.close(fig) # Vapautetaan muisti
