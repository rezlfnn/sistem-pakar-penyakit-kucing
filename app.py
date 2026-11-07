"""Sistem Pakar Penyakit Kucing Domestik (Forward Chaining + Certainty Factor).

Jalankan:  streamlit run app.py
"""
from __future__ import annotations

from html import escape
from pathlib import Path

import streamlit as st

import engine as E

st.set_page_config(page_title="Sistem Pakar Penyakit Kucing Domestik", page_icon="🐱", layout="wide")


@st.cache_resource
def get_kb() -> dict:
    return E.load_kb()


KB = get_kb()
SKALA = KB["skala_keyakinan"]
LABEL_KE_CF = {f"{s['label']} ({E.fmt_cf(s['cf'])})": s["cf"] for s in SKALA}
OPSI = list(LABEL_KE_CF)
KATEGORI = KB["kategori"]
GEJALA = KB["gejala"]
KODE_URUT = sorted(g["kode"] for g in GEJALA)

st.markdown(f"<style>{Path(__file__).with_name('style.css').read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)

ss = st.session_state
ss.setdefault("page", "input")
ss.setdefault("result", None)
ss.setdefault("error", None)


# --------------------------------------------------------------------------- callbacks
def on_check(code: str) -> None:
    if not ss.get(f"cb_{code}"):
        ss[f"cf_{code}"] = None


def on_cf(code: str) -> None:
    if ss.get(f"cf_{code}") is not None:
        ss[f"cb_{code}"] = True


def do_identify() -> None:
    fakta = {}
    for code in KODE_URUT:
        if ss.get(f"cb_{code}"):
            label = ss.get(f"cf_{code}")
            fakta[code] = LABEL_KE_CF.get(label) if label else None
    try:
        bersih = E.validasi(fakta, KB)
    except E.InputError as exc:
        ss.error = str(exc)
        return
    ss.error = None
    ss.result = E.identifikasi(bersih, KB)
    ss.page = "hasil"


def do_reset() -> None:
    for code in KODE_URUT:
        ss[f"cb_{code}"] = False
        ss[f"cf_{code}"] = None
    ss.error = None


def do_new() -> None:
    for code in KODE_URUT:
        ss.pop(f"cb_{code}", None)
        ss.pop(f"cf_{code}", None)
    ss.result = None
    ss.error = None
    ss.page = "input"


# --------------------------------------------------------------------------- komponen HTML
def header(step: int) -> str:
    d1 = '<span class="dot filled">✓</span>' if step == 2 else '<span class="dot filled">1</span>'
    d2 = f'<span class="dot{" filled" if step == 2 else ""}">2</span>'
    return (
        '<div class="hdr"><div class="brand"><span class="b1">Sistem Pakar</span>'
        '<span class="b2">Penyakit Kucing Domestik</span></div>'
        f'<div class="stepper">{d1}<span>Input Gejala</span><span class="line"></span>{d2}<span>Hasil Identifikasi</span></div></div>'
    )


def breakdown(h: E.HasilPenyakit) -> str:
    rows = "".join(
        f"<tr><td>{escape(g.nama)} ({g.kode})</td><td>{E.fmt_cf(g.cf_pakar)}</td>"
        f"<td>{E.fmt_cf(g.cf_user)}</td><td>{E.fmt(g.cf_gejala)}</td></tr>"
        for g in h.cocok
    )
    if not h.langkah:
        proses = (
            f'<div class="ln">Hanya satu gejala cocok, sehingga CF gabungan = CF gejala = {E.fmt(h.cocok[0].cf_gejala)} '
            f"→ <b>{h.persen}%</b></div>"
        )
    else:
        baris = []
        for i, (a, b, hasil) in enumerate(h.langkah):
            last = i == len(h.langkah) - 1
            if i == 0:
                teks = f"CF1 + CF2 = {E.fmt(a)} + {E.fmt(b)} × (1 − {E.fmt(a)}) = {E.fmt(hasil, 4)}"
            else:
                teks = f"{E.fmt(a, 4)} + {E.fmt(b)} × (1 − {E.fmt(a, 4)}) = {E.fmt(hasil, 4)}"
            if last:
                teks += f" → <b>{h.persen}%</b>"
            baris.append(f'<div class="ln">{teks}</div>')
        proses = "".join(baris)
    premis = ", ".join(k for k, _ in next(a for a in KB["aturan"] if a["kode"] == h.aturan)["premis"])
    return (
        '<div class="cf-card"><div class="cf-title">Rincian Perhitungan Certainty Factor</div>'
        '<table class="cf"><thead><tr><th>Gejala</th><th>CF Pakar</th><th>CF Pengguna</th><th>CF Gejala</th></tr></thead>'
        f"<tbody>{rows}</tbody></table>"
        '<div class="cf-boxes">'
        f'<div class="cf-box"><div class="bt">Proses Penggabungan CF</div>{proses}</div>'
        '<div class="cf-box"><div class="bt">Aturan yang Digunakan</div>'
        f'<div class="ln"><span class="rbadge">{h.aturan}</span> JIKA {premis} MAKA {h.kode} ({escape(h.nama)})</div>'
        f'<div class="ft">Aktif karena {len(h.cocok)} dari {h.jumlah_premis} gejala premis dipilih.</div></div>'
        "</div></div>"
    )


def daftar_dan(items: list[str]) -> str:
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " dan " + items[-1]


# =========================================================================== HALAMAN INPUT
def page_input() -> None:
    st.markdown(header(1), unsafe_allow_html=True)
    st.markdown(
        '<div class="page-title">Identifikasi Penyakit Kucing</div>'
        '<div class="page-sub">Pilih gejala yang tampak pada kucing, lalu tentukan keyakinan Anda. '
        "Hasil hanya berupa dugaan awal, bukan pengganti pemeriksaan dokter hewan.</div>",
        unsafe_allow_html=True,
    )
    dipilih = [c for c in KODE_URUT if ss.get(f"cb_{c}")]

    kat_aktif = ss.get("kategori_val") or "Semua"
    if kat_aktif != "Semua":
        sembunyi = [f".st-key-row_{g['kode']}" for g in GEJALA if g["kategori"] != kat_aktif]
        sembunyi += [f".st-key-cat_{i}" for i, k in enumerate(KATEGORI) if k != kat_aktif]
        st.markdown(f"<style>{','.join(sembunyi)}{{display:none !important;}}</style>", unsafe_allow_html=True)

    kiri, kanan = st.columns([3, 2], gap="large")

    with kiri:
        with st.container(key="left_card"):
            st.markdown(
                f'<div class="lc-head"><span class="t">Pilih Gejala yang Dialami Kucing</span>'
                f'<span class="c">{len(dipilih)} dari {len(GEJALA)} gejala dipilih</span></div>',
                unsafe_allow_html=True,
            )
            with st.container(key="kategori"):
                st.pills("Kategori", ["Semua"] + KATEGORI, default="Semua", selection_mode="single",
                         key="kategori_val", label_visibility="collapsed")
            with st.container(key="tbl"):
                st.markdown('<div class="tbl-head"><span>Gejala</span><span>Tingkat Keyakinan</span></div>',
                            unsafe_allow_html=True)
                for i, kat in enumerate(KATEGORI):
                    with st.container(key=f"cat_{i}"):
                        st.markdown(kat, unsafe_allow_html=False)
                    for g in sorted((x for x in GEJALA if x["kategori"] == kat), key=lambda x: x["kode"]):
                        code = g["kode"]
                        with st.container(key=f"row_{code}"):
                            c1, c2 = st.columns([1.15, 1])
                            with c1:
                                st.checkbox(f"**{code}** {g['nama']}", key=f"cb_{code}",
                                            on_change=on_check, args=(code,))
                            with c2:
                                st.selectbox("Keyakinan", OPSI, index=None, placeholder="Pilih tingkat keyakinan",
                                             key=f"cf_{code}", label_visibility="collapsed",
                                             on_change=on_cf, args=(code,))

    with kanan:
        legend = "".join(
            f"<b>{s['label']} ({E.fmt_cf(s['cf'])})</b><span>{s['ket']}</span>" for s in SKALA
        )
        st.markdown(
            '<div class="card-light"><div class="card-title">Tingkat Keyakinan</div>'
            '<div style="font-size:.92rem">Seberapa yakin Anda gejala ini benar-benar terlihat pada kucing?</div>'
            f'<div class="legend">{legend}</div></div>',
            unsafe_allow_html=True,
        )
        with st.container(key="sel_card"):
            st.markdown('<div class="sel-title">Gejala terpilih</div>', unsafe_allow_html=True)
            if dipilih:
                items = ""
                for c in dipilih:
                    nama = KB["gejala_by_kode"][c]["nama_pendek"]
                    lab = ss.get(f"cf_{c}")
                    ket = lab if lab else "belum dipilih"
                    items += f'<div class="sel-item"><b>{c}</b> {escape(nama)}<br><b>Keyakinan: {escape(ket)}</b></div>'
                st.markdown(items, unsafe_allow_html=True)
            else:
                st.markdown('<div class="sel-empty">Belum ada gejala dipilih.</div>', unsafe_allow_html=True)
            if ss.error:
                st.markdown(f'<div class="err-box">{escape(ss.error)}</div>', unsafe_allow_html=True)
            with st.container(key="btn_identify"):
                st.button("Identifikasi →", on_click=do_identify, use_container_width=True)
            with st.container(key="btn_reset"):
                st.button("Kosongkan pilihan", on_click=do_reset, type="tertiary")
        st.markdown(
            f'<div class="warn-card">Gejala bahaya ({", ".join(KB["gejala_bahaya"])}) akan memunculkan '
            "peringatan agar kucing segera diperiksakan ke dokter hewan.</div>",
            unsafe_allow_html=True,
        )


# =========================================================================== HALAMAN HASIL
def page_hasil() -> None:
    res: E.HasilKonsultasi = ss.result
    st.markdown(header(2), unsafe_allow_html=True)
    st.markdown('<div class="page-title" style="margin-bottom:1.1rem">Identifikasi Penyakit Kucing</div>',
                unsafe_allow_html=True)

    if not res.hasil:
        st.markdown('<div class="alert-danger">Dugaan penyakit belum dapat ditentukan dari gejala yang dipilih. '
                    "Periksakan kucing ke dokter hewan.</div>", unsafe_allow_html=True)
        with st.container(key="btn_new"):
            st.button("Konsultasi baru", on_click=do_new)
        return

    top = res.hasil[0]
    lain = res.hasil[1:]
    lain_txt = (
        "Dugaan lain: " + ", ".join(f"{escape(h.nama)} ({h.persen}%)" for h in lain) + "."
        if lain else "Dugaan lain: tidak ada aturan lain yang aktif."
    )
    long_cls = " long" if len(top.nama) > 12 else ""
    cocok_rows = "".join(
        f'<div class="match-row"><span>{escape(g.nama)} ({g.kode})</span><b>{E.to_percent(g.cf_gejala)}%</b></div>'
        for g in top.cocok
    )
    st.markdown(
        '<div class="res-grid"><div class="res-col">'
        '<div class="done-card">Identifikasi Selesai!</div>'
        '<div class="main-card"><div>'
        f'<span class="badge">{top.kode}</span><div class="dis-name{long_cls}">{escape(top.nama)}</div>'
        f'<div class="dis-desc">{escape(top.deskripsi)}</div><div class="dis-other">{lain_txt}</div></div>'
        f'<div class="pct"><div class="n">{top.persen}%</div><div class="t">{top.istilah}</div>'
        '<div class="s">Tingkat keyakinan</div></div></div></div>'
        '<div class="match-card"><div class="match-head"><span class="t">Gejala cocok</span>'
        f'<span class="c">{len(top.cocok)} dari {top.jumlah_premis}</span></div>{cocok_rows}</div></div>',
        unsafe_allow_html=True,
    )

    if res.gejala_bahaya:
        daftar = daftar_dan([f"{k} ({escape(n)})" for k, n in res.gejala_bahaya])
        st.markdown(
            f'<div class="alert-danger">Segera periksakan kucing ke dokter hewan. Gejala {daftar} '
            "termasuk gejala bahaya, berapa pun persentase hasilnya.</div>",
            unsafe_allow_html=True,
        )

    st.markdown(breakdown(top), unsafe_allow_html=True)

    saran = "".join(f"<li>{escape(s)}</li>" for s in top.saran)
    st.markdown(
        '<div class="bot-grid"><div class="saran-card"><div class="card-title" style="font-size:1.15rem">'
        f'Saran Perawatan Awal</div><ul>{saran}</ul>'
        '<div class="ft">Saran disusun dari jurnal rujukan (perlu divalidasi dokter hewan).</div></div>'
        '<div class="warn-big">Hasil ini adalah dugaan awal, bukan pengganti pemeriksaan dan diagnosis oleh dokter hewan.</div></div>',
        unsafe_allow_html=True,
    )

    for h in lain:
        with st.expander(f"Rincian dugaan lain: {h.nama} ({h.persen}%, {h.istilah.lower()})"):
            st.markdown(breakdown(h), unsafe_allow_html=True)
            st.markdown(
                '<div class="saran-card"><ul>' + "".join(f"<li>{escape(s)}</li>" for s in h.saran) + "</ul></div>",
                unsafe_allow_html=True,
            )

    with st.container(key="btn_new"):
        st.button("Konsultasi baru", on_click=do_new)


if ss.page == "hasil" and ss.result is not None:
    page_hasil()
else:
    page_input()
