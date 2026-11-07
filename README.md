# Sistem Pakar Penyakit Kucing Domestik
Forward Chaining + Certainty Factor (Streamlit, Python). 7 penyakit, 27 gejala, 33 relasi (Widayani et al., 2022).

## Menjalankan
1. Pasang Python 3.10+ (centang "Add Python to PATH").
2. Di folder ini:
   ```
   python -m venv venv
   venv\Scripts\activate          # Windows  (Linux/Mac: source venv/bin/activate)
   pip install -r requirements.txt
   streamlit run app.py
   ```
3. Browser terbuka otomatis di http://localhost:8501.

## Menjalankan uji perhitungan
```
python -m pytest -q
```

## Struktur
- `app.py` antarmuka (halaman input gejala & hasil identifikasi)
- `engine.py` working memory, forward chaining, perhitungan CF
- `knowledge_base.json` gejala, penyakit, aturan, CF pakar, saran
- `style.css` tampilan; `tests/test_engine.py` uji
