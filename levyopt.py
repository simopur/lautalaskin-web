import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import pandas as pd
import hashlib
import io
from fpdf import FPDF

# --- AIEMMAT LUOKAT (Panel, MaxRectsOptimizer, group_layouts) SÄILYVÄT ---

def create_pdf(layouts, s_w, s_h):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # Lasketaan sijoittelu (4 layoutia per A4, eli 2x2 ruudukko)
    # A4 on 210x297mm. Jätetään marginaalit.
    w_px, h_px = 90, 60  # Yhden kaavion koko PDF-sivulla (mm)
    
    for i, l in enumerate(layouts):
        if i % 4 == 0:
            pdf.add_page()
            pdf.set_font("Arial", "B", 16)
            pdf.cell(0, 10, "Sahauslistat", ln=True, align="C")
        
        # Tallennetaan layout kuvaksi muistiin
        fig, ax = plt.subplots(figsize=(7, 3))
        ax.add_patch(patches.Rectangle((0, 0), s_w, s_h, facecolor='none', edgecolor='black', lw=1))
        for p in l['panels']:
            ax.add_patch(patches.Rectangle((p.x, p.y), p.w, p.h, facecolor=p.color, edgecolor='black', alpha=0.9, lw=0.4))
            if p.w > 120:
                ax.text(p.x+p.w/2, p.y+p.h/2, f"{p.w}x{p.h}", ha='center', va='center', fontsize=5, fontweight='bold', color='white')
        
        ax.set_xlim(0, s_w); ax.set_ylim(0, s_h); ax.set_aspect('equal'); ax.axis('off')
        
        img_buf = io.BytesIO()
        plt.savefig(img_buf, format='png', dpi=300, bbox_inches='tight')
        plt.close(fig)
        
        # Määritetään paikka ruudukossa (2x2)
        row = (i % 4) // 2
        col = (i % 4) % 2
        x_pos = 10 + (col * 100)
        y_pos = 30 + (row * 120)
        
        # Lisätään teksti ja kuva
        pdf.set_xy(x_pos, y_pos - 10)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(w_px, 10, f"Layout {chr(65+i)} - {l['count']} kpl", ln=False)
        pdf.image(img_buf, x=x_pos, y=y_pos, w=w_px)
        
        # Lisätään osalistaus kaavion alle
        pdf.set_xy(x_pos, y_pos + h_px + 2)
        pdf.set_font("Arial", "", 8)
        osat_txt = ", ".join([f"{p.label} ({p.w}x{p.h})" for p in l['panels'][:5]]) # Max 5 ekaa mahtuu
        pdf.multi_cell(w_px, 4, f"Osat: {osat_txt}...")

    return pdf.output()

def nayta_levyoptimoija():
    # ... (Aiempi käyttöliittymäkoodi alkaa tästä) ...
    
    # Alhaalla, kun layoutit on laskettu:
    if 'opt' in locals() and palat:
        layouts = group_layouts(opt.sheets)
        
        st.divider()
        st.subheader("Tulostus")
        
        # PDF-painike
        if st.button("Generoi tulostettava PDF"):
            pdf_data = create_pdf(layouts, s_w, s_h)
            st.download_button(
                label="📥 Lataa PDF (A4 - 2x2 layoutia)",
                data=pdf_data,
                file_name="sahauslistat.pdf",
                mime="application/pdf"
            )
            
        # ... (Layouttien visualisointi näytölle jatkuu tästä) ...
