# """
# Capit Boneka Simulator (Streamlit)
# Simulasi gacha dan capit boneka dengan uang virtual untuk belajar peluang
# dan mengatur budget.

# Jalankan: streamlit run app.py
# Install : pip install streamlit pandas requests beautifulsoup4 openpyxl altair

# Pemetaan ke proposal:
#   2.2 Data input     : login akun, sidebar (budget, jumlah putaran, mesin, upload CSV)
#       Data eksternal : ambil_kurs() -> Frankfurter API (JPY ke IDR)
#                        scrape_katalog() -> web scraping (BeautifulSoup) katalog item
#   2.3 AI             : tanya_ai() -> Gemini API
#   2.4 Struktur data  : antrean (queue/deque), riwayat (stack/list),
#                        cache (dictionary), koleksi (Counter), katalog (list of dict)
#       Algoritma      : putar() weighted random + pity, sorting & searching di tab Koleksi
#   2.6 Visualisasi    : tab Grafik (pie, bar x2, line); Ekspor: tab AI & Ekspor (JSON, Excel)
# """
# import io
# import json
# import random
# import re
# import time
# from collections import Counter, deque
# from pathlib import Path

# import altair as alt
# import pandas as pd
# import requests
# import streamlit as st
# from bs4 import BeautifulSoup

# st.set_page_config(page_title="Capit Boneka Simulator", page_icon="🧸", layout="wide")

# # ---------------------------------------------------------------
# # 0. GAYA TAMPILAN (warna lebih hidup + ilustrasi SVG)
# # ---------------------------------------------------------------
# SVG_CLAW = (
#     '<svg width="54" height="54" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">'
#     '<rect x="4" y="4" width="56" height="56" rx="16" fill="white" fill-opacity="0.22"/>'
#     '<path d="M32 10V22M22 22H42L46 31H18L22 22Z" stroke="white" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>'
#     '<path d="M21 31L16 44C15 47 18 50 21 49M43 31L48 44C49 47 46 50 43 49" stroke="#FDE68A" stroke-width="3" stroke-linecap="round"/>'
#     '<circle cx="32" cy="40" r="6" fill="#FDE68A"/>'
#     "</svg>"
# )

# SVG_TOY_BADGE = {
#     "Common": '<span style="font-size:1.35rem;">🧸</span>',
#     "Rare": '<span style="font-size:1.35rem;">🐼</span>',
#     "Epic": '<span style="font-size:1.35rem;">🦄</span>',
#     "Legendary": '<span style="font-size:1.35rem;">🐉</span>',
# }

# st.markdown(
#     """<style>
# .stApp {
#     background: radial-gradient(circle at top left, #fdf2f8 0%, #f5f3ff 45%, #eff6ff 100%);
# }
# .main .block-container {
#     padding-top: 1.75rem;
#     padding-bottom: 2.5rem;
# }
# .hero-banner {
#     background: linear-gradient(120deg, #7c3aed 0%, #db2777 55%, #2563eb 100%);
#     color: #ffffff;
#     border-radius: 20px;
#     padding: 1.35rem 1.6rem;
#     margin-bottom: 1.25rem;
#     display: flex;
#     align-items: center;
#     gap: 1rem;
#     box-shadow: 0 10px 25px rgba(124, 58, 237, 0.22);
# }
# .hero-title {
#     font-size: 1.8rem;
#     font-weight: 800;
#     margin: 0;
#     line-height: 1.2;
# }
# .hero-sub {
#     margin: 0.25rem 0 0 0;
#     font-size: 0.95rem;
#     color: rgba(255, 255, 255, 0.92);
# }
# .drop-card {
#     display: flex;
#     align-items: center;
#     justify-content: space-between;
#     border-radius: 14px;
#     padding: 0.8rem 1.1rem;
#     margin-bottom: 0.65rem;
#     border: 1px solid rgba(0, 0, 0, 0.06);
# }
# .drop-Common {
#     background: linear-gradient(90deg, #f3f4f6 0%, #ffffff 100%);
#     border-left: 6px solid #6b7280;
# }
# .drop-Rare {
#     background: linear-gradient(90deg, #dbeafe 0%, #ffffff 100%);
#     border-left: 6px solid #2563eb;
# }
# .drop-Epic {
#     background: linear-gradient(90deg, #ede9fe 0%, #ffffff 100%);
#     border-left: 6px solid #7c3aed;
# }
# .drop-Legendary {
#     background: linear-gradient(90deg, #fef3c7 0%, #fffbeb 100%);
#     border-left: 6px solid #d97706;
# }
# .rarity-pill {
#     padding: 0.2rem 0.7rem;
#     border-radius: 999px;
#     font-size: 0.78rem;
#     font-weight: 700;
# }
# .pill-Common { background: #e5e7eb; color: #374151; }
# .pill-Rare { background: #bfdbfe; color: #1e40af; }
# .pill-Epic { background: #ddd6fe; color: #5b21b6; }
# .pill-Legendary { background: #fde68a; color: #92400e; }
# div[data-testid="stMetric"] {
#     background: #ffffff;
#     border: 1px solid #e2e8f0;
#     border-top: 4px solid #7c3aed;
#     border-radius: 14px;
#     padding: 0.8rem 1rem;
#     box-shadow: 0 4px 12px rgba(15, 23, 42, 0.05);
# }
# .stTabs [data-baseweb="tab-list"] {
#     gap: 0.5rem;
# }
# .stTabs [data-baseweb="tab"] {
#     background-color: rgba(255, 255, 255, 0.75);
#     border-radius: 10px 10px 0 0;
#     padding: 0.5rem 1rem;
#     font-weight: 600;
# }
# .stTabs [aria-selected="true"] {
#     background-color: #ffffff !important;
#     color: #7c3aed !important;
# }
# </style>""",
#     unsafe_allow_html=True,
# )

# # ---------------------------------------------------------------
# # 1. KONFIGURASI SCRAPING & AKUN
# # ---------------------------------------------------------------
# SCRAPE_URL = "https://books.toscrape.com/"
# KATALOG_CADANGAN = [
#     {"nama": "Item Kejutan 1", "rarity": "Common", "peluang": 15, "harga_yen": 500},
#     {"nama": "Item Kejutan 2", "rarity": "Rare", "peluang": 7, "harga_yen": 1400},
#     {"nama": "Item Kejutan 3", "rarity": "Epic", "peluang": 4, "harga_yen": 2600},
#     {"nama": "Item Kejutan 4", "rarity": "Legendary", "peluang": 1.5, "harga_yen": 6000},
# ]
# FILE_KATALOG = Path(__file__).parent / "katalog_boneka.csv"
# URUTAN_RARITY = {"Common": 1, "Rare": 2, "Epic": 3, "Legendary": 4}
# KURS_CADANGAN = 105.0

# AKUN_TERDAFTAR = {
#     "pemain1": {"pin": "1234", "nama": "Pemain 1"},
#     "pemain2": {"pin": "5678", "nama": "Pemain 2"},
#     "demo": {"pin": "2026", "nama": "Akun Demo"},
# }

# # ---------------------------------------------------------------
# # 2. STATE (struktur data utama disimpan di session_state)
# # ---------------------------------------------------------------
# if "init" not in st.session_state:
#     st.session_state.init = True
#     st.session_state.logged_in = False
#     st.session_state.user = None
#     st.session_state.antrean = deque()      # QUEUE: antrean putaran
#     st.session_state.riwayat = []           # STACK: riwayat hasil (pop = undo)
#     st.session_state.koleksi = Counter()    # COUNTER: jumlah tiap item
#     st.session_state.cache = {}             # DICTIONARY: cache hasil scrape & API
#     st.session_state.pity = 0
#     st.session_state.saldo = 0
#     st.session_state.saldo_awal = 0
#     st.session_state.grafik_saldo = []
#     st.session_state.penjelasan_ai = ""


# def reset_semua(budget):
#     st.session_state.antrean.clear()
#     st.session_state.riwayat.clear()
#     st.session_state.koleksi.clear()
#     st.session_state.grafik_saldo = []
#     st.session_state.pity = 0
#     st.session_state.saldo = budget
#     st.session_state.saldo_awal = budget
#     st.session_state.penjelasan_ai = ""


# def render_login():
#     _, col_tengah, _ = st.columns([1, 1.35, 1])
#     with col_tengah:
#         st.markdown(
#             f'<div class="hero-banner">{SVG_CLAW}<div>'
#             '<p class="hero-title">Capit Boneka Simulator</p>'
#             '<p class="hero-sub">Masuk untuk mulai simulasi gacha &amp; belajar peluang.</p>'
#             "</div></div>",
#             unsafe_allow_html=True,
#         )
#         with st.container(border=True):
#             with st.form("form_login"):
#                 username = st.text_input("Username", placeholder="contoh: pemain1")
#                 pin = st.text_input("PIN", type="password", placeholder="Masukkan PIN")
#                 masuk = st.form_submit_button("Masuk ke Simulator", type="primary", width="stretch")

#             if masuk:
#                 uname = username.strip().lower()
#                 akun = AKUN_TERDAFTAR.get(uname)
#                 if akun and akun["pin"] == pin:
#                     st.session_state.logged_in = True
#                     st.session_state.user = {"username": uname, "nama": akun["nama"]}
#                     reset_semua(200000)
#                     st.rerun()
#                 else:
#                     st.error("Username atau PIN salah. Coba `pemain1` dengan PIN `1234`.")

#             st.divider()
#             if st.button("⚡ Masuk Cepat (Akun Demo)", width="stretch"):
#                 st.session_state.logged_in = True
#                 st.session_state.user = {
#                     "username": "demo",
#                     "nama": AKUN_TERDAFTAR["demo"]["nama"],
#                 }
#                 reset_semua(200000)
#                 st.rerun()
#             st.caption("Akun tersedia: `pemain1` (PIN `1234`), `pemain2` (PIN `5678`), atau `demo` (PIN `2026`).")


# if not st.session_state.logged_in:
#     render_login()
#     st.stop()


# # ---------------------------------------------------------------
# # 3. DATA EKSTERNAL: Web Scraping Katalog + Frankfurter API Kurs
# # ---------------------------------------------------------------
# def _klasifikasi_rarity(idx, total):
#     rasio = idx / max(total, 1)
#     if rasio < 0.45:
#         return "Common", 12.0
#     if rasio < 0.75:
#         return "Rare", 6.5
#     if rasio < 0.92:
#         return "Epic", 4.0
#     return "Legendary", 1.5


# def scrape_katalog():
#     """Scrape halaman web katalog (BeautifulSoup) -> kembalikan LIST of DICTIONARY."""
#     kunci = "katalog_scraped"
#     if kunci in st.session_state.cache and st.session_state.cache[kunci]:
#         return st.session_state.cache[kunci], f"cache scrape ({SCRAPE_URL})"

#     try:
#         resp = requests.get(
#             SCRAPE_URL,
#             headers={"User-Agent": "Mozilla/5.0"},
#             timeout=12,
#         )
#         resp.raise_for_status()
#         soup = BeautifulSoup(resp.text, "html.parser")
#         kartu = soup.select("article.product_pod")

#         hasil = []
#         total = len(kartu)
#         for idx, el in enumerate(kartu):
#             link = el.select_one("h3 a")
#             harga_el = el.select_one("p.price_color")
#             judul = (link.get("title") or link.get_text(strip=True)) if link else ""
#             judul = re.sub(r"\s+", " ", judul).strip()
#             if not judul:
#                 continue

#             angka_harga = re.search(r"([\d.]+)", harga_el.get_text() if harga_el else "")
#             nilai_gbp = float(angka_harga.group(1)) if angka_harga else 10.0
#             harga_yen = max(400, int(round(nilai_gbp * 120)))

#             rarity, peluang = _klasifikasi_rarity(idx, total)
#             hasil.append({
#                 "nama": judul[:45],
#                 "rarity": rarity,
#                 "peluang": peluang,
#                 "harga_yen": harga_yen,
#             })

#         if not hasil:
#             raise ValueError("Elemen produk kosong saat scraping")

#         st.session_state.cache[kunci] = hasil
#         try:
#             pd.DataFrame(hasil).to_csv(FILE_KATALOG, index=False)
#         except OSError:
#             pass
#         return hasil, f"scraping ({SCRAPE_URL})"
#     except Exception as e:
#         if FILE_KATALOG.exists():
#             try:
#                 df_lokal = pd.read_csv(FILE_KATALOG)
#                 if not df_lokal.empty:
#                     return df_lokal.to_dict("records"), f"CSV cache scrape ({e})"
#             except Exception:
#                 pass
#         return KATALOG_CADANGAN, f"cadangan lokal (scrape gagal: {e})"


# def ambil_kurs():
#     kunci = "kurs_JPY_IDR"
#     if kunci in st.session_state.cache:
#         return st.session_state.cache[kunci], "cache"
#     try:
#         url = "https://api.frankfurter.app/latest?from=JPY&to=IDR"
#         data = requests.get(url, timeout=5).json()
#         kurs = float(data["rates"]["IDR"])
#         st.session_state.cache[kunci] = kurs
#         return kurs, "API Frankfurter"
#     except Exception:
#         return KURS_CADANGAN, "nilai cadangan (API gagal)"


# # ---------------------------------------------------------------
# # 4. ALGORITMA GACHA (weighted random + pity)
# # ---------------------------------------------------------------
# def putar(katalog, pity_count, mesin):
#     pool = katalog
#     if pity_count >= 10:  # pity: dijamin Rare ke atas
#         pool_rare = [b for b in katalog if b["rarity"] != "Common"]
#         if pool_rare:
#             pool = pool_rare
#     bobot = []
#     for b in pool:
#         w = float(b["peluang"])
#         if mesin == "Premium" and b["rarity"] == "Common":
#             w = w * 0.5   # mesin premium: Common lebih jarang
#         bobot.append(w)
#     return random.choices(pool, weights=bobot)[0]


# def proses_antrean(katalog, biaya, mesin):
#     """Ambil putaran dari QUEUE satu per satu sampai habis / saldo habis."""
#     dimainkan = 0
#     habis = False
#     while st.session_state.antrean:
#         if st.session_state.saldo < biaya:
#             st.session_state.antrean.clear()
#             habis = True
#             break
#         st.session_state.antrean.popleft()                 # QUEUE: ambil depan
#         hasil = putar(katalog, st.session_state.pity, mesin)
#         st.session_state.saldo -= biaya
#         st.session_state.riwayat.append({**hasil, "biaya": biaya})  # STACK: push
#         st.session_state.koleksi[hasil["nama"]] += 1
#         st.session_state.grafik_saldo.append(st.session_state.saldo)
#         st.session_state.pity = 0 if hasil["rarity"] != "Common" else st.session_state.pity + 1
#         dimainkan += 1
#     return dimainkan, habis


# def hitung_pity(riwayat):
#     """Pity = jumlah hasil Common berturut-turut di ujung riwayat."""
#     pity = 0
#     for h in reversed(riwayat):
#         if h["rarity"] != "Common":
#             break
#         pity += 1
#     return pity


# def undo_terakhir():
#     if not st.session_state.riwayat:
#         return
#     terakhir = st.session_state.riwayat.pop()              # STACK: pop
#     st.session_state.saldo += terakhir["biaya"]
#     st.session_state.koleksi[terakhir["nama"]] -= 1
#     if st.session_state.koleksi[terakhir["nama"]] <= 0:
#         del st.session_state.koleksi[terakhir["nama"]]
#     if st.session_state.grafik_saldo:
#         st.session_state.grafik_saldo.pop()
#     st.session_state.pity = hitung_pity(st.session_state.riwayat)   # pity ikut kembali


# # ---------------------------------------------------------------
# # 5. AI (Gemini lewat REST, tinggal isi API key di sidebar)
# # ---------------------------------------------------------------
# def tanya_ai(prompt, api_key, model, percobaan=3):
#     """Panggil Gemini. Mengembalikan (teks, berhasil). Diulang jika server sedang sibuk."""
#     if not api_key:
#         return "API key belum diisi.", False
#     url = (
#         f"https://generativelanguage.googleapis.com/v1beta/models/{model}"
#         f":generateContent?key={api_key}"
#     )
#     body = {"contents": [{"parts": [{"text": prompt}]}]}
#     pesan = ""
#     for ke in range(1, percobaan + 1):
#         try:
#             r = requests.post(url, json=body, timeout=30)
#             data = r.json()
#             if "error" in data:
#                 pesan = data["error"].get("message", "tidak diketahui")
#                 sibuk = r.status_code in (429, 500, 503) or "high demand" in pesan
#                 if sibuk and ke < percobaan:
#                     time.sleep(2 * ke)
#                     continue
#                 return f"AI menolak permintaan: {pesan}", False
#             return data["candidates"][0]["content"]["parts"][0]["text"], True
#         except Exception as e:
#             pesan = str(e)
#             if ke < percobaan:
#                 time.sleep(2 * ke)
#     return f"AI gagal dipanggil ({pesan}). Cek API key, nama model, atau kuota.", False


# def tanya_ai_openai(prompt, api_key, base_url, model, percobaan=2):
#     """AI cadangan lewat API berformat OpenAI (Groq, OpenRouter, dll). Mengembalikan (teks, berhasil)."""
#     url = base_url.rstrip("/") + "/chat/completions"
#     headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
#     body = {"model": model, "messages": [{"role": "user", "content": prompt}]}
#     pesan = ""
#     for ke in range(1, percobaan + 1):
#         try:
#             r = requests.post(url, headers=headers, json=body, timeout=30)
#             data = r.json()
#             if "error" in data:
#                 err = data["error"]
#                 pesan = err.get("message", str(err)) if isinstance(err, dict) else str(err)
#                 if r.status_code in (429, 500, 503) and ke < percobaan:
#                     time.sleep(2 * ke)
#                     continue
#                 return f"AI cadangan menolak permintaan: {pesan}", False
#             return data["choices"][0]["message"]["content"], True
#         except Exception as e:
#             pesan = str(e)
#             if ke < percobaan:
#                 time.sleep(2 * ke)
#     return f"AI cadangan gagal dipanggil ({pesan})", False


# def penjelasan_cadangan(riwayat, katalog, saldo_awal, saldo):
#     """Penjelasan otomatis (BUKAN AI) dari data hasil gacha, dipakai kalau AI tidak tersedia."""
#     total = len(riwayat)
#     total_bobot = sum(float(b["peluang"]) for b in katalog) or 1
#     teori = Counter()
#     for b in katalog:
#         teori[b["rarity"]] += float(b["peluang"]) / total_bobot * 100
#     nyata = Counter(h["rarity"] for h in riwayat)
#     baris = []
#     for r in ["Common", "Rare", "Epic", "Legendary"]:
#         persen = nyata[r] / total * 100
#         baris.append(f"- {r}: {nyata[r]} dari {total} putaran ({persen:.0f}%), peluang teoritis {teori[r]:.0f}%")
#     langka = nyata["Epic"] + nyata["Legendary"]
#     harapan = (teori["Epic"] + teori["Legendary"]) / 100 * total
#     if langka > harapan + 0.5:
#         nilai = "Kamu cukup beruntung: item Epic dan Legendary yang didapat lebih banyak dari perkiraan."
#     elif langka < harapan - 0.5:
#         nilai = "Kamu kurang beruntung: item Epic dan Legendary yang didapat lebih sedikit dari perkiraan."
#     else:
#         nilai = "Hasilmu cukup sesuai dengan peluang teoritis."
#     terpakai = saldo_awal - saldo
#     return (
#         f"{nilai}\n\n" + "\n".join(baris) +
#         f"\n\nSaldo terpakai Rp {terpakai:,} dari Rp {saldo_awal:,}. "
#         "Saran: tentukan batas budget sebelum bermain, karena hasil tiap putaran bersifat acak."
#     )


# # ---------------------------------------------------------------
# # 6. SIDEBAR: AKUN & DATA INPUT
# # ---------------------------------------------------------------
# st.sidebar.header("Pengaturan")
# if st.session_state.user:
#     st.sidebar.info(f"👤 **{st.session_state.user['nama']}** (`{st.session_state.user['username']}`)")
#     if st.sidebar.button("🚪 Logout", width="stretch"):
#         st.session_state.logged_in = False
#         st.session_state.user = None
#         reset_semua(0)
#         st.rerun()

# if st.sidebar.button("🕸️ Scrape ulang katalog", width="stretch"):
#     st.session_state.cache.pop("katalog_scraped", None)
#     st.rerun()

# katalog, sumber_katalog = scrape_katalog()
# st.sidebar.caption(f"Sumber katalog: {sumber_katalog} ({len(katalog)} item)")

# file_csv = st.sidebar.file_uploader("Upload katalog CSV (opsional)", type="csv")
# def baca_katalog(sumber):
#     """Baca CSV katalog, cek kolom, kembalikan LIST of DICTIONARY."""
#     df_kat = pd.read_csv(sumber)
#     kolom_wajib = {"nama", "rarity", "peluang", "harga_yen"}
#     if not kolom_wajib.issubset(df_kat.columns):
#         raise ValueError(f"Kolom CSV harus: {', '.join(sorted(kolom_wajib))}")
#     df_kat["peluang"] = pd.to_numeric(df_kat["peluang"])
#     df_kat["harga_yen"] = pd.to_numeric(df_kat["harga_yen"])
#     return df_kat.to_dict("records")


# if file_csv is not None:
#     try:
#         katalog, sumber_katalog = baca_katalog(file_csv), file_csv.name
#     except Exception as e:
#         st.sidebar.error(f"CSV tidak valid ({e}). Katalog tidak diganti.")
# st.sidebar.caption(f"Katalog aktif: {sumber_katalog}")

# mesin = st.sidebar.selectbox("Jenis mesin", ["Standar", "Premium"])
# biaya = 20000 if mesin == "Standar" else 35000
# st.sidebar.caption(f"Biaya per putaran: Rp {biaya:,} (uang simulasi)")
# budget = st.sidebar.number_input("Budget simulasi (Rp)", 20000, 5_000_000, 200000, 10000)
# jumlah = st.sidebar.slider("Jumlah putaran", 1, 50, 10)

# api_key = st.sidebar.text_input("Gemini API key", type="password")
# model_ai = st.sidebar.text_input("Nama model AI", "gemini-4-hydrogen")
# with st.sidebar.expander("AI cadangan (opsional)"):
#     api_key2 = st.text_input("API key AI cadangan", type="password")
#     base_url2 = st.text_input("Base URL (format OpenAI)", "https://api.groq.com/openai/v1")
#     model2 = st.text_input("Model AI cadangan", "openai/gpt-oss-120b")

# if st.sidebar.button("🔄 Mulai / Reset sesi", width="stretch"):
#     reset_semua(budget)

# if st.session_state.saldo_awal == 0:
#     reset_semua(budget)

# kurs, sumber_kurs = ambil_kurs()
# df_katalog = pd.DataFrame(katalog)
# if not df_katalog.empty:
#     df_katalog["harga_rupiah"] = (df_katalog["harga_yen"] * kurs).round(0).astype(int)

# # ---------------------------------------------------------------
# # 7. HALAMAN UTAMA
# # ---------------------------------------------------------------
# nama_akun = st.session_state.user["nama"] if st.session_state.user else "Pemain"
# st.markdown(
#     f'<div class="hero-banner">{SVG_CLAW}<div>'
#     '<p class="hero-title">Capit Boneka Simulator</p>'
#     f'<p class="hero-sub">Halo <b>{nama_akun}</b>! Simulasi edukasi tanpa uang asli untuk memahami peluang gacha &amp; mengatur budget.</p>'
#     "</div></div>",
#     unsafe_allow_html=True,
# )

# c1, c2, c3, c4 = st.columns(4)
# c1.metric("Saldo", f"Rp {st.session_state.saldo:,}")
# c2.metric("Total putaran", len(st.session_state.riwayat))
# c3.metric("Pity (tanpa Rare+)", f"{st.session_state.pity}/10")
# c4.metric("Kurs JPY→IDR", f"{kurs:,.1f}", help=f"Sumber: {sumber_kurs}")

# st.write("")
# tab1, tab2, tab3, tab4 = st.tabs(["🎰 Main", "📦 Koleksi", "📊 Grafik", "🤖 AI & Ekspor"])

# # ---- TAB MAIN ----
# with tab1:
#     colA, colB = st.columns([2, 1])
#     if colA.button(f"🎰 Putar {jumlah}x", type="primary", width="stretch"):
#         for _ in range(jumlah):
#             st.session_state.antrean.append("putar")       # QUEUE: masuk antrean
#         n, habis = proses_antrean(katalog, biaya, mesin)
#         pesan = f"{n} putaran selesai."
#         if habis:
#             pesan += " Saldo habis, sisa antrean dibatalkan."
#         st.session_state.pesan = pesan
#         st.rerun()
#     if colB.button("↩️ Undo putaran terakhir", width="stretch"):
#         undo_terakhir()
#         st.rerun()
#     if "pesan" in st.session_state:
#         st.success(st.session_state.pop("pesan"))

#     st.subheader("Riwayat terbaru")
#     if st.session_state.riwayat:
#         terbaru = list(reversed(st.session_state.riwayat[-10:]))
#         for h in terbaru:
#             rarity = h["rarity"] if h["rarity"] in SVG_TOY_BADGE else "Common"
#             ikon = SVG_TOY_BADGE[rarity]
#             st.markdown(
#                 f'<div class="drop-card drop-{rarity}">'
#                 f"<div>{ikon} <b>{h['nama']}</b></div>"
#                 f'<span class="rarity-pill pill-{rarity}">{h["rarity"]}</span>'
#                 "</div>",
#                 unsafe_allow_html=True,
#             )
#     else:
#         st.info("Belum ada putaran. Klik tombol Putar untuk mulai.")

#     with st.expander("Katalog & peluang"):
#         st.dataframe(df_katalog, width="stretch")

# # ---- TAB KOLEKSI (searching + sorting) ----
# with tab2:
#     st.subheader("Koleksi kamu")
#     if st.session_state.koleksi:
#         info = {b["nama"]: b for b in katalog}               # DICTIONARY untuk lookup cepat
#         baris = []
#         for nama, jml in st.session_state.koleksi.items():
#             b = info.get(nama)
#             if b is None:
#                 continue
#             baris.append({
#                 "nama": nama, "rarity": b["rarity"], "jumlah": jml,
#                 "harga_rupiah": int(float(b["harga_yen"]) * kurs),
#             })
#         cari = st.text_input("Cari item (searching)")
#         urut = st.selectbox("Urutkan berdasarkan", ["rarity", "jumlah", "harga_rupiah", "nama"])
#         if cari:
#             baris = [r for r in baris if cari.lower() in r["nama"].lower()]
#         if urut == "rarity":
#             baris.sort(key=lambda r: URUTAN_RARITY.get(r["rarity"], 0), reverse=True)
#         elif urut == "nama":
#             baris.sort(key=lambda r: r["nama"])
#         else:
#             baris.sort(key=lambda r: r[urut], reverse=True)   # SORTING
#         st.dataframe(pd.DataFrame(baris), width="stretch")
#     else:
#         st.info("Koleksi masih kosong.")

# # ---- TAB GRAFIK (4 visualisasi: pie, bar rarity, bar item, line saldo) ----
# with tab3:
#     if st.session_state.riwayat:
#         rarity_count = Counter(h["rarity"] for h in st.session_state.riwayat)
#         st.subheader("Distribusi rarity (pie chart)")
#         df_pie = pd.DataFrame(
#             {"rarity": list(rarity_count.keys()), "jumlah": list(rarity_count.values())}
#         )
#         pie = alt.Chart(df_pie).mark_arc().encode(
#             theta="jumlah:Q", color="rarity:N", tooltip=["rarity", "jumlah"]
#         )
#         st.altair_chart(pie, width="stretch")

#         st.subheader("Jumlah per rarity")
#         st.bar_chart(pd.Series(rarity_count, name="jumlah"))

#         st.subheader("Jumlah per item")
#         st.bar_chart(pd.Series(st.session_state.koleksi, name="jumlah"))

#         st.subheader("Sisa saldo tiap putaran")
#         st.line_chart(pd.Series(st.session_state.grafik_saldo, name="saldo"))
#     else:
#         st.info("Grafik muncul setelah ada putaran.")

# # ---- TAB AI & EKSPOR ----
# with tab4:
#     st.subheader("Penjelasan AI")
#     if st.button("Minta AI menjelaskan hasil"):
#         total = len(st.session_state.riwayat)
#         if total == 0:
#             st.warning("Putar dulu minimal sekali.")
#         else:
#             rarity_count = dict(Counter(h["rarity"] for h in st.session_state.riwayat))
#             prompt = (
#                 "Kamu asisten simulasi gacha (tanpa uang asli). "
#                 f"Total putaran: {total}. Hasil per rarity: {rarity_count}. "
#                 f"Peluang teoritis katalog: {[(b['nama'], b['rarity'], b['peluang']) for b in katalog]}. "
#                 f"Budget awal Rp {st.session_state.saldo_awal:,}, sisa Rp {st.session_state.saldo:,}. "
#                 "Jelaskan dengan bahasa Indonesia sederhana apakah pengguna beruntung atau sial "
#                 "dibanding peluang teoritis, beri saran batas budget bermain, dan buat deskripsi "
#                 "lucu 1 kalimat untuk item paling langka yang didapat."
#             )
#             with st.spinner("AI sedang berpikir..."):
#                 teks, berhasil = tanya_ai(prompt, api_key, model_ai)
#                 sumber = f"Gemini ({model_ai})"
#                 if not berhasil and api_key2:
#                     teks2, berhasil = tanya_ai_openai(prompt, api_key2, base_url2, model2)
#                     if berhasil:
#                         teks, sumber = teks2, f"AI cadangan ({model2})"
#                     else:
#                         teks = f"{teks} | {teks2}"
#             if berhasil:
#                 teks = f"{teks}\n\n*Dijawab oleh: {sumber}*"
#             else:
#                 teks = (
#                     f"AI sedang tidak tersedia ({teks}).\n\n"
#                     "**Penjelasan otomatis (bukan AI):**\n\n"
#                     + penjelasan_cadangan(
#                         st.session_state.riwayat, katalog,
#                         st.session_state.saldo_awal, st.session_state.saldo,
#                     )
#                 )
#             st.session_state.penjelasan_ai = teks
#     if st.session_state.penjelasan_ai:
#         st.write(st.session_state.penjelasan_ai)

#     st.subheader("Ekspor data")
#     if st.session_state.riwayat:
#         df_riwayat = pd.DataFrame(st.session_state.riwayat)
#         st.download_button(
#             "Download JSON",
#             json.dumps(st.session_state.riwayat, indent=2, ensure_ascii=False),
#             "riwayat_gacha.json", "application/json",
#         )
#         buf = io.BytesIO()
#         with pd.ExcelWriter(buf, engine="openpyxl") as w:
#             df_riwayat.to_excel(w, sheet_name="Riwayat", index=False)
#             pd.DataFrame(
#                 [{"nama": n, "jumlah": j} for n, j in st.session_state.koleksi.items()]
#             ).to_excel(w, sheet_name="Koleksi", index=False)
#         st.download_button(
#             "Download Excel", buf.getvalue(), "gacha_boneka.xlsx",
#             "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
#         )
#     else:
#         st.info("Ekspor tersedia setelah ada putaran.")

"""
Capit Boneka Simulator (Streamlit)
Simulasi gacha dan capit boneka dengan uang virtual untuk belajar peluang
dan mengatur budget.

Jalankan: streamlit run app.py
Install : pip install streamlit pandas requests beautifulsoup4 openpyxl altair

Pemetaan ke proposal:
  2.2 Data input     : login akun, sidebar (budget, jumlah putaran, mesin, upload CSV)
      Data eksternal : ambil_kurs() -> Frankfurter API (JPY ke IDR)
                       scrape_katalog() -> web scraping (BeautifulSoup) katalog item
  2.3 AI             : tanya_ai() -> Gemini API
  2.4 Struktur data  : antrean (queue/deque), riwayat (stack/list),
                       cache (dictionary), koleksi (Counter), katalog (list of dict)
      Algoritma      : putar() weighted random + pity, sorting & searching di tab Koleksi
  2.6 Visualisasi    : tab Grafik (pie, bar x2, line); Ekspor: tab AI & Ekspor (JSON, Excel)
"""
import io
import json
import random
import re
import time
from collections import Counter, deque
from pathlib import Path

import altair as alt
import pandas as pd
import requests
import streamlit as st
from bs4 import BeautifulSoup

st.set_page_config(page_title="Capit Boneka Simulator", page_icon="🧸", layout="wide")

# ---------------------------------------------------------------
# 0. GAYA TAMPILAN (warna lebih hidup + ilustrasi SVG)
# ---------------------------------------------------------------
SVG_CLAW = (
    '<svg width="54" height="54" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">'
    '<rect x="4" y="4" width="56" height="56" rx="16" fill="white" fill-opacity="0.22"/>'
    '<path d="M32 10V22M22 22H42L46 31H18L22 22Z" stroke="white" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>'
    '<path d="M21 31L16 44C15 47 18 50 21 49M43 31L48 44C49 47 46 50 43 49" stroke="#FDE68A" stroke-width="3" stroke-linecap="round"/>'
    '<circle cx="32" cy="40" r="6" fill="#FDE68A"/>'
    "</svg>"
)

SVG_TOY_BADGE = {
    "Common": '<span style="font-size:1.35rem;">🧸</span>',
    "Rare": '<span style="font-size:1.35rem;">🐼</span>',
    "Epic": '<span style="font-size:1.35rem;">🦄</span>',
    "Legendary": '<span style="font-size:1.35rem;">🐉</span>',
}

st.markdown(
    """<style>
.stApp {
    background: radial-gradient(circle at top left, #fdf2f8 0%, #f5f3ff 45%, #eff6ff 100%);
}
.main .block-container {
    padding-top: 1.75rem;
    padding-bottom: 2.5rem;
}
.hero-banner {
    background: linear-gradient(120deg, #7c3aed 0%, #db2777 55%, #2563eb 100%);
    color: #ffffff;
    border-radius: 20px;
    padding: 1.35rem 1.6rem;
    margin-bottom: 1.25rem;
    display: flex;
    align-items: center;
    gap: 1rem;
    box-shadow: 0 10px 25px rgba(124, 58, 237, 0.22);
}
.hero-title {
    font-size: 1.8rem;
    font-weight: 800;
    margin: 0;
    line-height: 1.2;
}
.hero-sub {
    margin: 0.25rem 0 0 0;
    font-size: 0.95rem;
    color: rgba(255, 255, 255, 0.92);
}
.drop-card {
    display: flex;
    align-items: center;
    justify-content: space-between;
    border-radius: 14px;
    padding: 0.8rem 1.1rem;
    margin-bottom: 0.65rem;
    border: 1px solid rgba(0, 0, 0, 0.06);
}
.drop-Common {
    background: linear-gradient(90deg, #f3f4f6 0%, #ffffff 100%);
    border-left: 6px solid #6b7280;
}
.drop-Rare {
    background: linear-gradient(90deg, #dbeafe 0%, #ffffff 100%);
    border-left: 6px solid #2563eb;
}
.drop-Epic {
    background: linear-gradient(90deg, #ede9fe 0%, #ffffff 100%);
    border-left: 6px solid #7c3aed;
}
.drop-Legendary {
    background: linear-gradient(90deg, #fef3c7 0%, #fffbeb 100%);
    border-left: 6px solid #d97706;
}
.rarity-pill {
    padding: 0.2rem 0.7rem;
    border-radius: 999px;
    font-size: 0.78rem;
    font-weight: 700;
}
.pill-Common { background: #e5e7eb; color: #374151; }
.pill-Rare { background: #bfdbfe; color: #1e40af; }
.pill-Epic { background: #ddd6fe; color: #5b21b6; }
.pill-Legendary { background: #fde68a; color: #92400e; }
div[data-testid="stMetric"] {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-top: 4px solid #7c3aed;
    border-radius: 14px;
    padding: 0.8rem 1rem;
    box-shadow: 0 4px 12px rgba(15, 23, 42, 0.05);
}
.stTabs [data-baseweb="tab-list"] {
    gap: 0.5rem;
}
.stTabs [data-baseweb="tab"] {
    background-color: rgba(255, 255, 255, 0.75);
    border-radius: 10px 10px 0 0;
    padding: 0.5rem 1rem;
    font-weight: 600;
}
.stTabs [aria-selected="true"] {
    background-color: #ffffff !important;
    color: #7c3aed !important;
}
</style>""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------
# 1. KONFIGURASI SCRAPING & AKUN
# ---------------------------------------------------------------
SCRAPE_URL = "https://books.toscrape.com/"
KATALOG_CADANGAN = [
    {"nama": "Item Kejutan 1", "rarity": "Common", "peluang": 15, "harga_yen": 500},
    {"nama": "Item Kejutan 2", "rarity": "Rare", "peluang": 7, "harga_yen": 1400},
    {"nama": "Item Kejutan 3", "rarity": "Epic", "peluang": 4, "harga_yen": 2600},
    {"nama": "Item Kejutan 4", "rarity": "Legendary", "peluang": 1.5, "harga_yen": 6000},
]
FILE_KATALOG = Path(__file__).parent / "katalog_boneka.csv"
URUTAN_RARITY = {"Common": 1, "Rare": 2, "Epic": 3, "Legendary": 4}
KURS_CADANGAN = 105.0

AKUN_TERDAFTAR = {
    "pemain1": {"pin": "1234", "nama": "Pemain 1"},
    "pemain2": {"pin": "5678", "nama": "Pemain 2"},
    "demo": {"pin": "2026", "nama": "Akun Demo"},
}

# ---------------------------------------------------------------
# 2. STATE (struktur data utama disimpan di session_state)
# ---------------------------------------------------------------
if "init" not in st.session_state:
    st.session_state.init = True
    st.session_state.logged_in = False
    st.session_state.user = None
    st.session_state.antrean = deque()      # QUEUE: antrean putaran
    st.session_state.riwayat = []           # STACK: riwayat hasil (pop = undo)
    st.session_state.koleksi = Counter()    # COUNTER: jumlah tiap item
    st.session_state.cache = {}             # DICTIONARY: cache hasil scrape & API
    st.session_state.pity = 0
    st.session_state.saldo = 0
    st.session_state.saldo_awal = 0
    st.session_state.grafik_saldo = []
    st.session_state.penjelasan_ai = ""


def reset_semua(budget):
    st.session_state.antrean.clear()
    st.session_state.riwayat.clear()
    st.session_state.koleksi.clear()
    st.session_state.grafik_saldo = []
    st.session_state.pity = 0
    st.session_state.saldo = budget
    st.session_state.saldo_awal = budget
    st.session_state.penjelasan_ai = ""


def render_login():
    _, col_tengah, _ = st.columns([1, 1.35, 1])
    with col_tengah:
        st.markdown(
            f'<div class="hero-banner">{SVG_CLAW}<div>'
            '<p class="hero-title">Capit Boneka Simulator</p>'
            '<p class="hero-sub">Masuk untuk mulai simulasi gacha &amp; belajar peluang.</p>'
            "</div></div>",
            unsafe_allow_html=True,
        )
        with st.container(border=True):
            with st.form("form_login"):
                username = st.text_input("Username", placeholder="contoh: pemain1")
                pin = st.text_input("PIN", type="password", placeholder="Masukkan PIN")
                masuk = st.form_submit_button("Masuk ke Simulator", type="primary", width="stretch")

            if masuk:
                uname = username.strip().lower()
                akun = AKUN_TERDAFTAR.get(uname)
                if akun and akun["pin"] == pin:
                    st.session_state.logged_in = True
                    st.session_state.user = {"username": uname, "nama": akun["nama"]}
                    reset_semua(200000)
                    st.rerun()
                else:
                    st.error("Username atau PIN salah.")


if not st.session_state.logged_in:
    render_login()
    st.stop()


# ---------------------------------------------------------------
# 3. DATA EKSTERNAL: Web Scraping Katalog + Frankfurter API Kurs
# ---------------------------------------------------------------
def _klasifikasi_rarity(idx, total):
    rasio = idx / max(total, 1)
    if rasio < 0.45:
        return "Common", 12.0
    if rasio < 0.75:
        return "Rare", 6.5
    if rasio < 0.92:
        return "Epic", 4.0
    return "Legendary", 1.5


def scrape_katalog():
    """Scrape halaman web katalog (BeautifulSoup) -> kembalikan LIST of DICTIONARY."""
    kunci = "katalog_scraped"
    if kunci in st.session_state.cache and st.session_state.cache[kunci]:
        return st.session_state.cache[kunci], f"cache scrape ({SCRAPE_URL})"

    try:
        resp = requests.get(
            SCRAPE_URL,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=12,
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        kartu = soup.select("article.product_pod")

        hasil = []
        total = len(kartu)
        for idx, el in enumerate(kartu):
            link = el.select_one("h3 a")
            harga_el = el.select_one("p.price_color")
            judul = (link.get("title") or link.get_text(strip=True)) if link else ""
            judul = re.sub(r"\s+", " ", judul).strip()
            if not judul:
                continue

            angka_harga = re.search(r"([\d.]+)", harga_el.get_text() if harga_el else "")
            nilai_gbp = float(angka_harga.group(1)) if angka_harga else 10.0
            harga_yen = max(400, int(round(nilai_gbp * 120)))

            rarity, peluang = _klasifikasi_rarity(idx, total)
            hasil.append({
                "nama": judul[:45],
                "rarity": rarity,
                "peluang": peluang,
                "harga_yen": harga_yen,
            })

        if not hasil:
            raise ValueError("Elemen produk kosong saat scraping")

        st.session_state.cache[kunci] = hasil
        try:
            pd.DataFrame(hasil).to_csv(FILE_KATALOG, index=False)
        except OSError:
            pass
        return hasil, f"scraping ({SCRAPE_URL})"
    except Exception as e:
        if FILE_KATALOG.exists():
            try:
                df_lokal = pd.read_csv(FILE_KATALOG)
                if not df_lokal.empty:
                    return df_lokal.to_dict("records"), f"CSV cache scrape ({e})"
            except Exception:
                pass
        return KATALOG_CADANGAN, f"cadangan lokal (scrape gagal: {e})"


def ambil_kurs():
    kunci = "kurs_JPY_IDR"
    if kunci in st.session_state.cache:
        return st.session_state.cache[kunci], "cache"
    try:
        url = "https://api.frankfurter.app/latest?from=JPY&to=IDR"
        data = requests.get(url, timeout=5).json()
        kurs = float(data["rates"]["IDR"])
        st.session_state.cache[kunci] = kurs
        return kurs, "API Frankfurter"
    except Exception:
        return KURS_CADANGAN, "nilai cadangan (API gagal)"


# ---------------------------------------------------------------
# 4. ALGORITMA GACHA (weighted random + pity)
# ---------------------------------------------------------------
def putar(katalog, pity_count, mesin):
    pool = katalog
    if pity_count >= 10:  # pity: dijamin Rare ke atas
        pool_rare = [b for b in katalog if b["rarity"] != "Common"]
        if pool_rare:
            pool = pool_rare
    bobot = []
    for b in pool:
        w = float(b["peluang"])
        if mesin == "Premium" and b["rarity"] == "Common":
            w = w * 0.5   # mesin premium: Common lebih jarang
        bobot.append(w)
    return random.choices(pool, weights=bobot)[0]


def proses_antrean(katalog, biaya, mesin):
    """Ambil putaran dari QUEUE satu per satu sampai habis / saldo habis."""
    dimainkan = 0
    habis = False
    while st.session_state.antrean:
        if st.session_state.saldo < biaya:
            st.session_state.antrean.clear()
            habis = True
            break
        st.session_state.antrean.popleft()                 # QUEUE: ambil depan
        hasil = putar(katalog, st.session_state.pity, mesin)
        st.session_state.saldo -= biaya
        st.session_state.riwayat.append({**hasil, "biaya": biaya})  # STACK: push
        st.session_state.koleksi[hasil["nama"]] += 1
        st.session_state.grafik_saldo.append(st.session_state.saldo)
        st.session_state.pity = 0 if hasil["rarity"] != "Common" else st.session_state.pity + 1
        dimainkan += 1
    return dimainkan, habis


def hitung_pity(riwayat):
    """Pity = jumlah hasil Common berturut-turut di ujung riwayat."""
    pity = 0
    for h in reversed(riwayat):
        if h["rarity"] != "Common":
            break
        pity += 1
    return pity


def undo_terakhir():
    if not st.session_state.riwayat:
        return
    terakhir = st.session_state.riwayat.pop()              # STACK: pop
    st.session_state.saldo += terakhir["biaya"]
    st.session_state.koleksi[terakhir["nama"]] -= 1
    if st.session_state.koleksi[terakhir["nama"]] <= 0:
        del st.session_state.koleksi[terakhir["nama"]]
    if st.session_state.grafik_saldo:
        st.session_state.grafik_saldo.pop()
    st.session_state.pity = hitung_pity(st.session_state.riwayat)   # pity ikut kembali


# ---------------------------------------------------------------
# 5. AI (Gemini lewat REST, tinggal isi API key di sidebar)
# ---------------------------------------------------------------
def tanya_ai(prompt, api_key, model, percobaan=3):
    """Panggil Gemini. Mengembalikan (teks, berhasil). Diulang jika server sedang sibuk."""
    if not api_key:
        return "API key belum diisi.", False
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}"
        f":generateContent?key={api_key}"
    )
    body = {"contents": [{"parts": [{"text": prompt}]}]}
    pesan = ""
    for ke in range(1, percobaan + 1):
        try:
            r = requests.post(url, json=body, timeout=30)
            data = r.json()
            if "error" in data:
                pesan = data["error"].get("message", "tidak diketahui")
                sibuk = r.status_code in (429, 500, 503) or "high demand" in pesan
                if sibuk and ke < percobaan:
                    time.sleep(2 * ke)
                    continue
                return f"AI menolak permintaan: {pesan}", False
            return data["candidates"][0]["content"]["parts"][0]["text"], True
        except Exception as e:
            pesan = str(e)
            if ke < percobaan:
                time.sleep(2 * ke)
    return f"AI gagal dipanggil ({pesan}). Cek API key, nama model, atau kuota.", False


def tanya_ai_openai(prompt, api_key, base_url, model, percobaan=2):
    """AI cadangan lewat API berformat OpenAI (Groq, OpenRouter, dll). Mengembalikan (teks, berhasil)."""
    url = base_url.rstrip("/") + "/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    body = {"model": model, "messages": [{"role": "user", "content": prompt}]}
    pesan = ""
    for ke in range(1, percobaan + 1):
        try:
            r = requests.post(url, headers=headers, json=body, timeout=30)
            data = r.json()
            if "error" in data:
                err = data["error"]
                pesan = err.get("message", str(err)) if isinstance(err, dict) else str(err)
                if r.status_code in (429, 500, 503) and ke < percobaan:
                    time.sleep(2 * ke)
                    continue
                return f"AI cadangan menolak permintaan: {pesan}", False
            return data["choices"][0]["message"]["content"], True
        except Exception as e:
            pesan = str(e)
            if ke < percobaan:
                time.sleep(2 * ke)
    return f"AI cadangan gagal dipanggil ({pesan})", False


def penjelasan_cadangan(riwayat, katalog, saldo_awal, saldo):
    """Penjelasan otomatis (BUKAN AI) dari data hasil gacha, dipakai kalau AI tidak tersedia."""
    total = len(riwayat)
    total_bobot = sum(float(b["peluang"]) for b in katalog) or 1
    teori = Counter()
    for b in katalog:
        teori[b["rarity"]] += float(b["peluang"]) / total_bobot * 100
    nyata = Counter(h["rarity"] for h in riwayat)
    baris = []
    for r in ["Common", "Rare", "Epic", "Legendary"]:
        persen = nyata[r] / total * 100
        baris.append(f"- {r}: {nyata[r]} dari {total} putaran ({persen:.0f}%), peluang teoritis {teori[r]:.0f}%")
    langka = nyata["Epic"] + nyata["Legendary"]
    harapan = (teori["Epic"] + teori["Legendary"]) / 100 * total
    if langka > harapan + 0.5:
        nilai = "Kamu cukup beruntung: item Epic dan Legendary yang didapat lebih banyak dari perkiraan."
    elif langka < harapan - 0.5:
        nilai = "Kamu kurang beruntung: item Epic dan Legendary yang didapat lebih sedikit dari perkiraan."
    else:
        nilai = "Hasilmu cukup sesuai dengan peluang teoritis."
    terpakai = saldo_awal - saldo
    return (
        f"{nilai}\n\n" + "\n".join(baris) +
        f"\n\nSaldo terpakai Rp {terpakai:,} dari Rp {saldo_awal:,}. "
        "Saran: tentukan batas budget sebelum bermain, karena hasil tiap putaran bersifat acak."
    )


# ---------------------------------------------------------------
# 6. SIDEBAR: AKUN & DATA INPUT
# ---------------------------------------------------------------
st.sidebar.header("Pengaturan")
if st.session_state.user:
    st.sidebar.info(f"👤 **{st.session_state.user['nama']}** (`{st.session_state.user['username']}`)")
    if st.sidebar.button("🚪 Logout", width="stretch"):
        st.session_state.logged_in = False
        st.session_state.user = None
        reset_semua(0)
        st.rerun()

if st.sidebar.button("🕸️ Scrape ulang katalog", width="stretch"):
    st.session_state.cache.pop("katalog_scraped", None)
    st.rerun()

katalog, sumber_katalog = scrape_katalog()
st.sidebar.caption(f"Sumber katalog: {sumber_katalog} ({len(katalog)} item)")

file_csv = st.sidebar.file_uploader("Upload katalog CSV (opsional)", type="csv")
def baca_katalog(sumber):
    """Baca CSV katalog, cek kolom, kembalikan LIST of DICTIONARY."""
    df_kat = pd.read_csv(sumber)
    kolom_wajib = {"nama", "rarity", "peluang", "harga_yen"}
    if not kolom_wajib.issubset(df_kat.columns):
        raise ValueError(f"Kolom CSV harus: {', '.join(sorted(kolom_wajib))}")
    df_kat["peluang"] = pd.to_numeric(df_kat["peluang"])
    df_kat["harga_yen"] = pd.to_numeric(df_kat["harga_yen"])
    return df_kat.to_dict("records")


if file_csv is not None:
    try:
        katalog, sumber_katalog = baca_katalog(file_csv), file_csv.name
    except Exception as e:
        st.sidebar.error(f"CSV tidak valid ({e}). Katalog tidak diganti.")
st.sidebar.caption(f"Katalog aktif: {sumber_katalog}")

mesin = st.sidebar.selectbox("Jenis mesin", ["Standar", "Premium"])
biaya = 20000 if mesin == "Standar" else 35000
st.sidebar.caption(f"Biaya per putaran: Rp {biaya:,} (uang simulasi)")
budget = st.sidebar.number_input("Budget simulasi (Rp)", 20000, 5_000_000, 200000, 10000)
jumlah = st.sidebar.slider("Jumlah putaran", 1, 50, 10)

api_key = st.sidebar.text_input("Gemini API key", type="password")
model_ai = st.sidebar.text_input("Nama model AI", "gemini-4-hydrogen")
with st.sidebar.expander("AI cadangan (opsional)"):
    api_key2 = st.text_input("API key AI cadangan", type="password")
    base_url2 = st.text_input("Base URL (format OpenAI)", "https://api.groq.com/openai/v1")
    model2 = st.text_input("Model AI cadangan", "openai/gpt-oss-120b")

if st.sidebar.button("🔄 Mulai / Reset sesi", width="stretch"):
    reset_semua(budget)

if st.session_state.saldo_awal == 0:
    reset_semua(budget)

kurs, sumber_kurs = ambil_kurs()
df_katalog = pd.DataFrame(katalog)
if not df_katalog.empty:
    df_katalog["harga_rupiah"] = (df_katalog["harga_yen"] * kurs).round(0).astype(int)

# ---------------------------------------------------------------
# 7. HALAMAN UTAMA
# ---------------------------------------------------------------
nama_akun = st.session_state.user["nama"] if st.session_state.user else "Pemain"
st.markdown(
    f'<div class="hero-banner">{SVG_CLAW}<div>'
    '<p class="hero-title">Capit Boneka Simulator</p>'
    f'<p class="hero-sub">Halo <b>{nama_akun}</b>! Simulasi edukasi tanpa uang asli untuk memahami peluang gacha &amp; mengatur budget.</p>'
    "</div></div>",
    unsafe_allow_html=True,
)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Saldo", f"Rp {st.session_state.saldo:,}")
c2.metric("Total putaran", len(st.session_state.riwayat))
c3.metric("Pity (tanpa Rare+)", f"{st.session_state.pity}/10")
c4.metric("Kurs JPY→IDR", f"{kurs:,.1f}", help=f"Sumber: {sumber_kurs}")

st.write("")
tab1, tab2, tab3, tab4 = st.tabs(["🎰 Main", "📦 Koleksi", "📊 Grafik", "🤖 AI & Ekspor"])

# ---- TAB MAIN ----
with tab1:
    colA, colB = st.columns([2, 1])
    if colA.button(f"🎰 Putar {jumlah}x", type="primary", width="stretch"):
        for _ in range(jumlah):
            st.session_state.antrean.append("putar")       # QUEUE: masuk antrean
        n, habis = proses_antrean(katalog, biaya, mesin)
        pesan = f"{n} putaran selesai."
        if habis:
            pesan += " Saldo habis, sisa antrean dibatalkan."
        st.session_state.pesan = pesan
        st.rerun()
    if colB.button("↩️ Undo putaran terakhir", width="stretch"):
        undo_terakhir()
        st.rerun()
    if "pesan" in st.session_state:
        st.success(st.session_state.pop("pesan"))

    st.subheader("Riwayat terbaru")
    if st.session_state.riwayat:
        terbaru = list(reversed(st.session_state.riwayat[-10:]))
        for h in terbaru:
            rarity = h["rarity"] if h["rarity"] in SVG_TOY_BADGE else "Common"
            ikon = SVG_TOY_BADGE[rarity]
            st.markdown(
                f'<div class="drop-card drop-{rarity}">'
                f"<div>{ikon} <b>{h['nama']}</b></div>"
                f'<span class="rarity-pill pill-{rarity}">{h["rarity"]}</span>'
                "</div>",
                unsafe_allow_html=True,
            )
    else:
        st.info("Belum ada putaran. Klik tombol Putar untuk mulai.")

    with st.expander("Katalog & peluang"):
        st.dataframe(df_katalog, width="stretch")

# ---- TAB KOLEKSI (searching + sorting) ----
with tab2:
    st.subheader("Koleksi kamu")
    if st.session_state.koleksi:
        info = {b["nama"]: b for b in katalog}               # DICTIONARY untuk lookup cepat
        baris = []
        for nama, jml in st.session_state.koleksi.items():
            b = info.get(nama)
            if b is None:
                continue
            baris.append({
                "nama": nama, "rarity": b["rarity"], "jumlah": jml,
                "harga_rupiah": int(float(b["harga_yen"]) * kurs),
            })
        cari = st.text_input("Cari item (searching)")
        urut = st.selectbox("Urutkan berdasarkan", ["rarity", "jumlah", "harga_rupiah", "nama"])
        if cari:
            baris = [r for r in baris if cari.lower() in r["nama"].lower()]
        if urut == "rarity":
            baris.sort(key=lambda r: URUTAN_RARITY.get(r["rarity"], 0), reverse=True)
        elif urut == "nama":
            baris.sort(key=lambda r: r["nama"])
        else:
            baris.sort(key=lambda r: r[urut], reverse=True)   # SORTING
        st.dataframe(pd.DataFrame(baris), width="stretch")
    else:
        st.info("Koleksi masih kosong.")

# ---- TAB GRAFIK (4 visualisasi: pie, bar rarity, bar item, line saldo) ----
with tab3:
    if st.session_state.riwayat:
        rarity_count = Counter(h["rarity"] for h in st.session_state.riwayat)
        st.subheader("Distribusi rarity (pie chart)")
        df_pie = pd.DataFrame(
            {"rarity": list(rarity_count.keys()), "jumlah": list(rarity_count.values())}
        )
        pie = alt.Chart(df_pie).mark_arc().encode(
            theta="jumlah:Q", color="rarity:N", tooltip=["rarity", "jumlah"]
        )
        st.altair_chart(pie, width="stretch")

        st.subheader("Jumlah per rarity")
        st.bar_chart(pd.Series(rarity_count, name="jumlah"))

        st.subheader("Jumlah per item")
        st.bar_chart(pd.Series(st.session_state.koleksi, name="jumlah"))

        st.subheader("Sisa saldo tiap putaran")
        st.line_chart(pd.Series(st.session_state.grafik_saldo, name="saldo"))
    else:
        st.info("Grafik muncul setelah ada putaran.")

# ---- TAB AI & EKSPOR ----
with tab4:
    st.subheader("Penjelasan AI")
    if st.button("Minta AI menjelaskan hasil"):
        total = len(st.session_state.riwayat)
        if total == 0:
            st.warning("Putar dulu minimal sekali.")
        else:
            rarity_count = dict(Counter(h["rarity"] for h in st.session_state.riwayat))
            prompt = (
                "Kamu asisten simulasi gacha (tanpa uang asli). "
                f"Total putaran: {total}. Hasil per rarity: {rarity_count}. "
                f"Peluang teoritis katalog: {[(b['nama'], b['rarity'], b['peluang']) for b in katalog]}. "
                f"Budget awal Rp {st.session_state.saldo_awal:,}, sisa Rp {st.session_state.saldo:,}. "
                "Jelaskan dengan bahasa Indonesia sederhana apakah pengguna beruntung atau sial "
                "dibanding peluang teoritis, beri saran batas budget bermain, dan buat deskripsi "
                "lucu 1 kalimat untuk item paling langka yang didapat."
            )
            with st.spinner("AI sedang berpikir..."):
                teks, berhasil = tanya_ai(prompt, api_key, model_ai)
                sumber = f"Gemini ({model_ai})"
                if not berhasil and api_key2:
                    teks2, berhasil = tanya_ai_openai(prompt, api_key2, base_url2, model2)
                    if berhasil:
                        teks, sumber = teks2, f"AI cadangan ({model2})"
                    else:
                        teks = f"{teks} | {teks2}"
            if berhasil:
                teks = f"{teks}\n\n*Dijawab oleh: {sumber}*"
            else:
                teks = (
                    f"AI sedang tidak tersedia ({teks}).\n\n"
                    "**Penjelasan otomatis (bukan AI):**\n\n"
                    + penjelasan_cadangan(
                        st.session_state.riwayat, katalog,
                        st.session_state.saldo_awal, st.session_state.saldo,
                    )
                )
            st.session_state.penjelasan_ai = teks
    if st.session_state.penjelasan_ai:
        st.write(st.session_state.penjelasan_ai)

    st.subheader("Ekspor data")
    if st.session_state.riwayat:
        df_riwayat = pd.DataFrame(st.session_state.riwayat)
        st.download_button(
            "Download JSON",
            json.dumps(st.session_state.riwayat, indent=2, ensure_ascii=False),
            "riwayat_gacha.json", "application/json",
        )
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as w:
            df_riwayat.to_excel(w, sheet_name="Riwayat", index=False)
            pd.DataFrame(
                [{"nama": n, "jumlah": j} for n, j in st.session_state.koleksi.items()]
            ).to_excel(w, sheet_name="Koleksi", index=False)
        st.download_button(
            "Download Excel", buf.getvalue(), "gacha_boneka.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    else:
        st.info("Ekspor tersedia setelah ada putaran.")