import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import engine as e  # noqa: E402

KB = e.load_kb()


def test_jumlah_basis_pengetahuan():
    assert len(KB["gejala"]) == 27
    assert len(KB["penyakit"]) == 7
    assert sum(len(a["premis"]) for a in KB["aturan"]) == 33


def test_contoh_flutd_proposal():
    """Contoh proposal bagian 5.4: G15 Yakin, G17 Sangat yakin, G18 Cukup yakin."""
    r = e.identifikasi({"G15": 0.8, "G17": 1.0, "G18": 0.6}, KB)
    top = r.hasil[0]
    assert top.kode == "K04" and top.aturan == "R02"
    assert [round(g.cf_gejala, 2) for g in top.cocok] == [0.48, 0.80, 0.48]
    assert top.langkah[0][2] == pytest.approx(0.8960)
    assert top.cf == pytest.approx(0.9459, abs=1e-4)
    assert top.persen == 95 and top.istilah == "Keyakinan tinggi"
    assert [k for k, _ in r.gejala_bahaya] == ["G17"]
    assert len(r.hasil) == 1


def test_contoh_scabies_widayani():
    """Widayani et al. (2022): G25 0,4 ; G26 0,8 ; G27 0,8 -> 79%."""
    r = e.identifikasi({"G25": 0.4, "G26": 0.8, "G27": 0.8}, KB)
    assert r.hasil[0].kode == "K07"
    assert r.hasil[0].cf == pytest.approx(0.7945, abs=1e-4)
    assert r.hasil[0].persen == 79


def test_gejala_tumpang_tindih_menghasilkan_beberapa_dugaan():
    r = e.identifikasi({"G08": 0.8}, KB)  # lesu: R03, R04, R05
    assert {h.kode for h in r.hasil} == {"K02", "K03", "K05"}
    assert r.hasil[0].kode == "K03"  # CF pakar 1,0
    assert [h.cf for h in r.hasil] == sorted([h.cf for h in r.hasil], reverse=True)


def test_semua_cf_pengguna_satu():
    r = e.identifikasi({"G01": 1.0, "G02": 1.0}, KB)
    assert r.hasil[0].cf == pytest.approx(0.6 + 0.4 * 0.4)


def test_gejala_bahaya():
    r = e.identifikasi({"G22": 0.6, "G23": 0.8}, KB)
    assert [k for k, _ in r.gejala_bahaya] == ["G22", "G23"]


def test_validasi():
    with pytest.raises(e.InputError):
        e.validasi({}, KB)
    with pytest.raises(e.InputError):
        e.validasi({"G01": None}, KB)
    with pytest.raises(e.InputError):
        e.validasi({"G99": 0.8}, KB)
    assert e.validasi({"G01": 0.8}, KB) == {"G01": 0.8}


def test_format_dan_istilah():
    assert e.fmt(0.48) == "0,48" and e.fmt_cf(1.0) == "1,0"
    assert e.istilah_keyakinan(39) == "Keyakinan rendah"
    assert e.istilah_keyakinan(40) == "Keyakinan sedang"
    assert e.istilah_keyakinan(60) == "Keyakinan cukup tinggi"
    assert e.istilah_keyakinan(80) == "Keyakinan tinggi"


def test_urutan_seri_memakai_proporsi_gejala_cocok():
    """Widayani (2022) sampel 10: K03 dan K05 sama-sama 100%; K05 cocok 2 dari 5 premis, K03 hanya 1 dari 7."""
    r = e.identifikasi({"G19": 1.0, "G12": 1.0, "G21": 1.0}, KB)
    assert [h.kode for h in r.hasil[:2]] == ["K05", "K03"]
    assert r.hasil[0].persen == r.hasil[1].persen == 100


def test_evaluasi_kasus_uji_widayani():
    """Replikasi Tabel 9 Widayani et al. (2022): persentase sistem sama dengan jurnal, 9 dari 10 sesuai."""
    import csv
    sesuai = 0
    with open(Path(__file__).with_name("kasus_uji.csv"), encoding="utf-8") as f:
        for r in csv.DictReader(f):
            fakta = {p.split(":")[0]: float(p.split(":")[1]) for p in r["gejala"].split(";")}
            hasil = e.identifikasi(fakta, KB).hasil
            sesuai += hasil[0].kode in set(r["diagnosis_pembanding"].split("|"))
            if hasil[0].kode in set(r["diagnosis_pembanding"].split("|")):
                assert abs(hasil[0].persen - int(r["persen_jurnal"])) <= 1
    assert sesuai == 9