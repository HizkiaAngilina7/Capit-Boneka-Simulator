# Capit Boneka Simulator

Simulasi gacha dan capit boneka dengan uang virtual (tanpa uang asli) untuk belajar peluang dan mengatur budget.
Proyek Besar Praktikum Algoritma & Struktur Data, Kelompok 5, FTI UKDW.

## Cara menjalankan
```
pip install -r requirements.txt
streamlit run app.py
```

## Akun untuk login
| Username | PIN  |
|----------|------|
| pemain1  | 1234 |
| pemain2  | 5678 |
| demo     | 2026 |

Saldo dan riwayat tiap akun tersimpan otomatis di `data_pengguna.json`.

## Fitur
- Login akun, data (saldo, riwayat) tersimpan dan ada lagi saat login berikutnya
- Katalog dari web scraping (books.toscrape.com), diurutkan dengan merge sort buatan sendiri
- Kurs JPY ke IDR dari Frankfurter API
- Peluang dinamis (pity, cooldown Legendary, mesin Premium) dan panel "Peluang kamu sekarang"
- 4 grafik, ekspor JSON dan Excel, penjelasan AI (Gemini, cadangan Groq)

## Struktur data dan algoritma
Queue (deque), stack (list, undo), dictionary (cache), Counter (koleksi), weighted random, merge sort, searching.

## Catatan
API key diisi lewat sidebar, jangan pernah di-commit.
