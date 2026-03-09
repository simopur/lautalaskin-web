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
    hex_color = hex_color.lstrip('#')
    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    return "white" if luminance < 0.5 else "black"

def piirra_paneelin_teksti(ax, p, base_fs=6):
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
        # Suodatetaan pois tyhjät tai nolla-arvot
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

# --- KIRJASTO, PDF JA PARSE ---

KIRJASTO_TIEDOSTO = "vakiokoot.json"

def lataa_kirjasto():
    if os.path.exists(KIRJASTO_TIEDOSTO):
        try:
            with open(KIRJASTO_TIEDOSTO, "r") as f:
                data = json.load(f)
                for item in data:
                    if 'Käytä' not in item: item['Käytä'] = True
                return data
        except: pass
    return [{"Käytä": True, "Nimi": "Talla 200", "Pit": 200, "Lev": 200}]

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

def create_pdf_bytes(layouts, s_w, s_h):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=10)
    w_mm, h_mm = 90, 45 
    for i, l in enumerate(layouts):
        if i % 8 == 0:
            pdf.add_page(); pdf.set_font("helvetica", "B", 14); pdf.cell(0,
