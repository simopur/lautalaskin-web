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
            nimi, pituus, taysi_lkm, jatko_w, kpl = parts[0], int(parts[1]), int(parts[3]), int(parts[4]), int(parts[5])
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
                        shelf['rem_w'] -= (w + kerf); placed = True; break
                if placed: break
            if placed: break
        if not placed:
            if not sheets or sum(s['h'] + kerf for s in sheets[-1]['shelves']) + min(p.w, p.h) > s_h:
                sheets.append({'panels': [], 'shelves': []})
            sheet = sheets[-1]
            y = sum(s['h'] + kerf for s in sheet['shelves'])
            opts = [o for o in [(p.w, p.h, False), (p.h, p.w, True)] if o[0] <= s_w and y + o[1] <= s_h]
            if opts:
                bw, bh, br = min(opts, key=lambda x: x[1])
                p.w, p.h, p.is_rotated, p.x, p.y = bw, bh, br, 0, y
                sheet['shelves'].append({'y': y, 'h': bh, 'rem_w': s_w - (bw + kerf)})
                sheet['panels'].append(p)
    return sheets

def nayta_levyoptimoija():
    st.header("Levyjen sahausoptimointi")
    col1, col2 = st.columns([1, 3])
    with col1:
        s_w = st.number_input("Varastolevyn pituus (mm)", value=2700)
        s_h = st.number_input("Varastolevyn leveys (mm)", value=1200)
        full_w = st.number_input("Täyden suikaleen leveys (mm)", value=1220)
        kerf = st.slider("Terän hukka (mm)", 0, 10, 4)
        excel_input = st.text_area("Liitä Excel-tiedot:", height=250)

    with col2:
        if excel_input:
            palat = parse_excel_input(excel_input, full_w)
            tulokset = optimize_sheets(palat, s_w, s_h, kerf)
            st.subheader(f"Tarvittava määrä: {len(tulokset)} levyä")
            for i, sheet in enumerate(tulokset):
                fig, ax = plt.subplots(figsize=(10, 4))
                ax.add_patch(patches.Rectangle((0, 0), s_w, s_h, facecolor='#f0f0f0', edgecolor='black', lw=2))
                for p in sheet['panels']:
                    ax.add_patch(patches.Rectangle((p.x, p.y), p.w, p.h, edgecolor='navy', facecolor=p.color, alpha=0.5))
                    ax.text(p.x + p.w/2, p.y + p.h/2, f"{p.label}\n{p.w}x{p.h}", ha='center', va='center', fontsize=7)
                ax.set_aspect('equal')
                st.pyplot(fig)
