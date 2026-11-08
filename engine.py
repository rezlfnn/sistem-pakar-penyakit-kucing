"""Mesin inferensi Sistem Pakar Penyakit Kucing Domestik.

Metode: Forward Chaining + Certainty Factor (CF).
  (1) CF gejala    = CF pakar x CF pengguna
  (2) CF gabungan  = CF1 + CF2 x (1 - CF1)
  (3) Persentase   = CF gabungan x 100%
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

KB_PATH = Path(__file__).with_name("knowledge_base.json")


# ----------------------------------------------------------------------------
# Basis pengetahuan (hanya dibaca)
# ----------------------------------------------------------------------------
def load_kb(path: Path | str = KB_PATH) -> dict:
    with open(path, encoding="utf-8") as f:
        kb = json.load(f)
    kb["gejala_by_kode"] = {g["kode"]: g for g in kb["gejala"]}
    kb["penyakit_by_kode"] = {p["kode"]: p for p in kb["penyakit"]}
    return kb


# ----------------------------------------------------------------------------
# Format angka gaya Indonesia (koma desimal)
# ----------------------------------------------------------------------------
def fmt(x: float, nd: int = 2) -> str:
    return f"{x:.{nd}f}".replace(".", ",")


def fmt_cf(x: float) -> str:
    """CF pakar / pengguna: 0,6 ; 1,0 (satu desimal)."""
    return fmt(x, 1)


def to_percent(cf: float) -> int:
    """Pembulatan setengah ke atas (0,9459 -> 95)."""
    return int(cf * 100 + 0.5 + 1e-9)


def istilah_keyakinan(persen: int) -> str:
    if persen < 40:
        return "Keyakinan rendah"
    if persen < 60:
        return "Keyakinan sedang"
    if persen < 80:
        return "Keyakinan cukup tinggi"
    return "Keyakinan tinggi"


# ----------------------------------------------------------------------------
# Struktur hasil
# ----------------------------------------------------------------------------
@dataclass
class GejalaCocok:
    kode: str
    nama: str
    cf_pakar: float
    cf_user: float
    cf_gejala: float


@dataclass
class HasilPenyakit:
    kode: str
    nama: str
    deskripsi: str
    aturan: str
    jumlah_premis: int
    cocok: list[GejalaCocok]
    langkah: list[tuple[float, float, float]]  # (CF sebelumnya, CF gejala, hasil)
    cf: float
    persen: int
    istilah: str
    saran: list[str] = field(default_factory=list)


@dataclass
class HasilKonsultasi:
    hasil: list[HasilPenyakit]            # urut dari persentase tertinggi
    gejala_bahaya: list[tuple[str, str]]  # (kode, nama)


# ----------------------------------------------------------------------------
# Validasi input
# ----------------------------------------------------------------------------
class InputError(ValueError):
    pass


def validasi(fakta: dict[str, float | None], kb: dict) -> dict[str, float]:
    """fakta: {kode gejala: CF pengguna atau None}. Kembalikan fakta bersih."""
    if not fakta:
        raise InputError("Pilih minimal satu gejala.")
    kosong = [k for k, v in fakta.items() if v is None]
    if kosong:
        raise InputError(
            "Tentukan tingkat keyakinan untuk gejala: " + ", ".join(sorted(kosong)) + "."
        )
    for k, v in fakta.items():
        if k not in kb["gejala_by_kode"]:
            raise InputError(f"Kode gejala tidak dikenal: {k}.")
        if not 0.2 <= v <= 1.0:
            raise InputError(f"CF pengguna {k} di luar rentang 0,2 sampai 1,0.")
    return dict(fakta)


# ----------------------------------------------------------------------------
# Forward chaining + CF
# ----------------------------------------------------------------------------
def gabung_cf(cf_list: list[float]) -> tuple[float, list[tuple[float, float, float]]]:
    """Gabungkan CF berurutan; kembalikan CF akhir dan jejak tiap langkah."""
    langkah: list[tuple[float, float, float]] = []
    total = cf_list[0]
    for nxt in cf_list[1:]:
        hasil = total + nxt * (1 - total)
        langkah.append((total, nxt, hasil))
        total = hasil
    return total, langkah


def identifikasi(fakta: dict[str, float], kb: dict) -> HasilKonsultasi:
    """Working memory = `fakta`. Setiap aturan diperiksa; aturan aktif bila
    minimal satu gejala premisnya ada di working memory."""
    hasil: list[HasilPenyakit] = []
    for aturan in kb["aturan"]:
        cocok: list[GejalaCocok] = []
        for kode, cf_pakar in aturan["premis"]:
            if kode in fakta:
                cf_user = fakta[kode]
                cocok.append(
                    GejalaCocok(
                        kode=kode,
                        nama=kb["gejala_by_kode"][kode]["nama_pendek"],
                        cf_pakar=cf_pakar,
                        cf_user=cf_user,
                        cf_gejala=cf_pakar * cf_user,
                    )
                )
        if not cocok:
            continue  # aturan tidak aktif
        cocok.sort(key=lambda g: g.kode)
        cf, langkah = gabung_cf([g.cf_gejala for g in cocok])
        penyakit = kb["penyakit_by_kode"][aturan["penyakit"]]
        persen = to_percent(cf)
        hasil.append(
            HasilPenyakit(
                kode=penyakit["kode"],
                nama=penyakit["nama"],
                deskripsi=penyakit["deskripsi"],
                aturan=aturan["kode"],
                jumlah_premis=len(aturan["premis"]),
                cocok=cocok,
                langkah=langkah,
                cf=cf,
                persen=persen,
                istilah=istilah_keyakinan(persen),
                saran=penyakit["saran"],
            )
        )
    # Urut: CF tertinggi; bila sama, penyakit dengan proporsi gejala premis cocok lebih besar didahulukan.
    hasil.sort(key=lambda h: (round(h.cf, 6), len(h.cocok) / h.jumlah_premis), reverse=True)
    bahaya = [
        (k, kb["gejala_by_kode"][k]["nama"][0].lower() + kb["gejala_by_kode"][k]["nama"][1:])
        for k in sorted(fakta)
        if k in kb["gejala_bahaya"]
    ]
    return HasilKonsultasi(hasil=hasil, gejala_bahaya=bahaya)
