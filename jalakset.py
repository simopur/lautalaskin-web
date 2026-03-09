import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches

def muodosta_kerros_j(alku, j_p, j_l):
    p_l, curr = [], 0
    p_l.append(int(alku)); curr += alku
    while curr + j_l < j_p:
        p_l.append(int(j_l)); curr += j_l
    if j_p - curr > 0: p_l.append(int(j_p - curr))
    return p_l

def laske_jalas_mestarimalli(j_p, j_l, kerrokset):
    data = []
    rem = j_p % j_l
    data.append(muodosta_kerros_j(j_l, j_p, j_l))
    if kerrokset >= 2:
        data.append(muodosta_kerros_j(j_l/2, j_p, j_l))
    if kerrokset >= 3:
        tasattu = (j_l + rem) / 2 if rem > 0 else j_l/2
        data.append(muodosta_kerros_j(tasattu, j_p, j_l))
    return data

def piirra_jalasjako(kerrokset_data, kokonaispituus):
    fig, ax = plt.subplots(figsize=(12, 1.5 + len(kerrokset_data)*0.5))
    colors = ['#8e44ad', '#2980b9', '#27ae60']
    l_h, v = 100, 15
    for i, kerros in enumerate(kerrokset_data):
        y_pos = i * (l_h + v)
        cx = 0
        for p in kerros:
            ax.add_patch(patches.Rectangle((cx, y_pos), p, l_h, linewidth=1, edgecolor='black', facecolor=colors[i % 3], alpha=0.8))
            if p > 300:
                ax.text(cx + p/2, y_pos + l_h/2, f"{int(p)}", ha='center', va='center', color='white', fontsize=8, fontweight='bold')
            cx += p
    ax.set_xlim(-100, kokonaispituus + 100); ax.set_ylim(-20, len(kerrokset_data)*(l_h+v) + 20); ax.set_aspect('equal')
    for spine in ax.spines.values(): spine.set_visible(False)
    st.pyplot(fig)

def nayta_jalakset():
    st.header("🦶 Jalasten laskenta")
    cj1, cj2 = st.columns(2)
    with cj1:
        j_p = st.number_input("Jalaksen kokonaispituus mm", value=10000, key="j_p")
        j_l = st.number_input("Materiaalin mitta mm", value=4000, key="j_l")
    with cj2:
        j_k = st.number_input("Kerrosmäärä (1-3)", value=3, min_value=1, max_value=3, key="j_k")

    if st.button("Laske jalat", type="primary"):
        if j_l >= j_p: st.info("Jalas voidaan tehdä yhdestä puusta.")
        else:
            d = laske_jalas_mestarimalli(j_p, j_l, j_k)
            piirra_jalasjako(d, j_p)
            for i, kerros in enumerate(d):
                st.info(f"**Kerros {i+1}:** {' + '.join(map(str, kerros))} mm")
