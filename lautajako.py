import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches

# --- LOGIIKKA ---
def etsi_reitit_f(n_idx, reitti, max_l, pisteet, sallitut):
    if pisteet[-1] - pisteet[n_idx] <= max_l:
        if n_idx != len(pisteet) - 2: return [reitti + [len(pisteet)-1]]
    res = []
    for s_idx in sallitut:
        if s_idx > n_idx:
            pala = pisteet[s_idx] - pisteet[n_idx]
            if pala <= max_l and s_idx - n_idx >= 2:
                t = etsi_reitit_f(s_idx, reitti + [s_idx], max_l, pisteet, sallitut)
                if t: res.extend(t)
    return res

def yrita_laskea_pari_f(m_l, all_p, sallitut):
    reitit = etsi_reitit_f(0, [0], m_l, all_p, sallitut)
    if not reitit: return []
    valmiit = []
    for r in reitit:
        p = [all_p[r[j+1]] - all_p[r[j]] for j in range(len(r)-1)]
        s = [all_p[idx] for idx in r[1:-1]]
        sc = sum(x**2 for x in p)
        valmiit.append({'palat': p, 'saumat': s, 'idx': r, 'l_score': sc})
    
    valmiit.sort(key=lambda x: (len(x['palat']), -x['l_score']))
    parit = []
    nahtyat_jaot = [] 

    for m_a in valmiit[:100]:
        jako_tunniste = tuple(sorted(m_a['palat']))
        if jako_tunniste in nahtyat_jaot: continue
        m_b, is_mirror = None, False
        rev_palat = m_a['palat'][::-1]
        cur, rev_s = 0, []
        for p_val in rev_palat[:-1]:
            cur += p_val
            rev_s.append(cur)
        
        is_rev_valid = True
        rev_idx_list = []
        for sv in rev_s:
            if sv in all_p and all_p.index(sv) in sallitut: rev_idx_list.append(all_p.index(sv))
            else: is_rev_valid = False; break
        
        if is_rev_valid:
            a_set = set(m_a['idx'][1:-1])
            if all(b not in a_set and b-1 not in a_set and b+1 not in a_set for b in rev_idx_list):
                m_b = {'palat': rev_palat, 'saumat': rev_s, 'idx': [0]+rev_idx_list+[len(all_p)-1]}
                is_mirror = True
        
        if not m_b:
            for ehd in valmiit:
                b_idx = ehd['idx'][1:-1]
                if b_idx:
                    a_set = set(m_a['idx'][1:-1])
                    if all(b not in a_set and b-1 not in a_set and b+1 not in a_set for b in b_idx):
                        m_b = ehd; break
        if m_b:
            parit.append({'a': m_a, 'b': m_b, 'is_mirror': is_mirror})
            nahtyat_jaot.append(jako_tunniste)
            if len(parit) >= 2: break
    return parit

def piirra_lautajako(malli_a, malli_b, ulkopituus, nostot, title):
    fig, ax = plt.subplots(figsize=(12, 3)) 
    jaot = [malli_a, malli_b, malli_a, malli_b, malli_a]
    l_w, v = 100, 10 
    kaikki_s = set(malli_a['saumat'])
    if malli_b: kaikki_s.update(malli_b['saumat'])
    
    for n in nostot:
        ax.axvline(x=n, color='gray', linestyle='--', linewidth=0.5, alpha=0.3)
    
    for i, jako in enumerate(jaot):
        if not jako: continue
        y_pos = i * (l_w + v)
        cx = 0
        for j, pala in enumerate(jako['palat']):
            rect = patches.Rectangle((cx, y_pos), pala, l_w, linewidth=0.5, edgecolor='black', 
                                     facecolor='#e67e22' if i%2==0 else '#d35400', alpha=0.8)
            ax.add_patch(rect)
            if pala > 800:
                ax.text(cx + pala/2, y_pos + l_w/2, f"{int(pala)}", ha='center', va='center', 
                        color='white', fontsize=7, fontweight='bold')
            cx += pala
            if j < len(jako['palat']) - 1:
                ax.plot([cx, cx], [y_pos, y_pos + l_w], color='black', linewidth=2.5)

    ax.set_xlim(-200, ulkopituus + 200); ax.set_ylim(-50, 5 * (l_w + v) + 50); ax.set_aspect('equal')
    ax.set_title(title, fontsize=10, fontweight='bold')
    ax.set_xticks(nostot); labels = ax.set_xticklabels([str(int(n)) for n in nostot], fontsize=7, rotation=45)
    ax.set_yticks([(l_w/2) + k*(l_w+v) for k in range(5)])
    ax.set_yticklabels(["A", "B", "A", "B", "A"], fontsize=8)
    for spine in ax.spines.values(): spine.set_visible(False)
    st.pyplot(fig)

# --- NÄKYMÄ ---
def nayta_lautajako():
    st.header("🪵 Lautajako")
    c1, c2 = st.columns(2)
    with c1:
        f_max = st.number_input("Laudan pituus (mm)", value=5100, key="f_max_l")
        f_ulp = st.number_input("Ulkopituus (mm)", value=12110, key="f_ulp")
        f_tne = st.number_input("TN etäisyys (mm)", value=295, key="f_tne")
    with c2:
        f_tnv = st.number_input("TN väli (mm)", value=960, key="f_tnv")
        f_tnm = st.number_input("TN määrä (kpl)", value=13, key="f_tnm")

    if st.button("Laske lautajako", type="primary"):
        nostot = [int(f_tne + (i * f_tnv)) for i in range(int(f_tnm)) if (int(f_tne + (i * f_tnv))) < f_ulp]
        all_p = [0] + nostot + [int(f_ulp)]
        
        if nostot:
            alku_vali = nostot[0]
            loppu_vali = f_ulp - nostot[-1]
            keskivalit = [nostot[i+1] - nostot[i] for i in range(len(nostot)-1)]
            if abs(alku_vali - loppu_vali) > 1 or keskivalit != keskivalit[::-1]:
                st.warning("⚠️ **Huom! Trukkinostojen jako ei ole symmetrinen.**")
            else:
                st.success("✅ Trukkinostojen jako on symmetrinen.")

        sallitut = list(range(2, len(all_p) - 2))
        parit = yrita_laskea_pari_f(f_max, all_p, sallitut)
        
        if parit:
            for idx, pari in enumerate(parit):
                piirra_lautajako(pari['a'], pari['b'], f_ulp, nostot, f"Vaihtoehto {idx+1}")
                st.info(f"**Malli A:** {' + '.join(map(str, pari['a']['palat']))} mm | **Malli B:** {' + '.join(map(str, pari['b']['palat']))} mm")
        else:
            st.error("❌ Jako ei ole mahdollinen nykyisillä mitoilla.")
