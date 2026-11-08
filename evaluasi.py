"""Evaluasi sistem terhadap kasus uji (proposal bagian 5.6).

Jalankan:  python evaluasi.py
Format tests/kasus_uji.csv:
  id, sumber, gejala ("G03:1.0;G04:0.8"), diagnosis_pembanding ("K02" atau "K02|K01"), persen_jurnal
Tambahkan kasus dari jurnal lain pada berkas yang sama sampai minimal 20 kasus.
"""
import csv
from pathlib import Path

import engine as E

KB = E.load_kb()
BERKAS = Path(__file__).with_name("tests") / "kasus_uji.csv"


def baca_kasus():
    with open(BERKAS, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            fakta = {p.split(":")[0]: float(p.split(":")[1]) for p in r["gejala"].split(";")}
            yield r, fakta, set(r["diagnosis_pembanding"].split("|"))


def main():
    n = top1 = top3 = 0
    print(f"{'ID':<5}{'Sistem (top 3)':<46}{'Pembanding':<12}{'Jurnal':<8}{'Top1':<6}")
    for r, fakta, pembanding in baca_kasus():
        hasil = E.identifikasi(E.validasi(fakta, KB), KB).hasil
        urut = [(h.kode, h.persen) for h in hasil[:3]]
        n += 1
        ok1 = bool(hasil) and hasil[0].kode in pembanding
        ok3 = any(k in pembanding for k, _ in urut)
        top1 += ok1
        top3 += ok3
        ringkas = ", ".join(f"{k} {p}%" for k, p in urut)
        print(f"{r['id']:<5}{ringkas:<46}{r['diagnosis_pembanding']:<12}{r['persen_jurnal']+'%':<8}{'ya' if ok1 else 'TIDAK'}")
    print(f"\nKasus uji         : {n}")
    print(f"Akurasi top-1     : {top1}/{n} = {top1 / n * 100:.0f}%  (target proposal minimal 80%)")
    print(f"Pembanding di top-3: {top3}/{n} = {top3 / n * 100:.0f}%")


if __name__ == "__main__":
    main()