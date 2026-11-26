"""
Capit Boneka Simulator (Streamlit)
Simulasi gacha dan capit boneka dengan uang virtual untuk belajar peluang
dan mengatur budget.

Jalankan: streamlit run app.py
Install : pip install streamlit pandas requests beautifulsoup4 openpyxl altair

Pemetaan ke proposal:
  2.2 Data input     : login akun, sidebar (budget, jumlah putaran, mesin)
      Data eksternal : scrape_katalog() -> web scraping (BeautifulSoup) katalog item,
                       diurutkan dan diberi rarity/peluang oleh program sendiri
                       ambil_kurs()     -> Frankfurter API (JPY ke IDR)
  2.3 AI             : tanya_ai() -> Gemini API, cadangan tanya_ai_openai() -> Groq
  2.4 Struktur data  : antrean (queue/deque), riwayat (stack/list),
                       cache (dictionary), koleksi (Counter), katalog (list of dict)
      Algoritma      : putar() weighted random + pity + peluang dinamis,
                       merge_sort() buatan sendiri (rarity katalog & tab Koleksi),
                       searching di tab Koleksi
  2.6 Visualisasi    : tab Grafik (pie, bar x2, line); Ekspor: tab AI & Ekspor (JSON, Excel)
  Data akun (saldo, riwayat) disimpan di data_pengguna.json (jangan di-commit).
"""
import hashlib
import hmac
import html
import io
import json
import os
import random
import re
import secrets
import time
from collections import Counter, deque
from datetime import datetime
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
.chance-row{display:flex;align-items:center;gap:.6rem;margin:.4rem 0}
.chance-row .nm{width:90px;font-weight:700}
.chance-row .bar{flex:1;height:10px;border-radius:6px;background:rgba(128,128,128,.22);overflow:hidden}
.chance-row .bar>span{display:block;height:100%;border-radius:6px}
.chance-row .pct{width:210px;font-size:.85rem;text-align:right}
.catatan{border-left:5px solid #7c3aed;border-radius:10px;padding:.55rem .9rem;
    background:rgba(124,58,237,.08);font-size:.9rem;margin:.5rem 0}
.pity-bar{height:8px;border-radius:6px;background:rgba(128,128,128,.25);overflow:hidden;margin-top:.3rem}
.pity-bar>span{display:block;height:100%;background:linear-gradient(90deg,#7c3aed,#db2777)}
</style>""",
    unsafe_allow_html=True,
)


RARITY_URUT = ["Common", "Rare", "Epic", "Legendary"]
RARITY_WARNA = {"Common": "#6b7280", "Rare": "#2563eb", "Epic": "#7c3aed", "Legendary": "#d97706"}
URUTAN_RARITY = {"Common": 1, "Rare": 2, "Epic": 3, "Legendary": 4}


def e(x):
    """Escape teks supaya aman dipakai di HTML (nama hasil scraping bisa berisi tanda khusus)."""
    return html.escape(str(x))


# ---------------------------------------------------------------
# 1. KONFIGURASI
# ---------------------------------------------------------------
SCRAPE_URL = "https://books.toscrape.com/"
SCRAPE_HALAMAN = [SCRAPE_URL, SCRAPE_URL + "catalogue/page-2.html", SCRAPE_URL + "catalogue/page-3.html"]
KATALOG_CADANGAN = [
    {"nama": "Item Kejutan 1", "rarity": "Common", "peluang": 15, "harga_yen": 500},
    {"nama": "Item Kejutan 2", "rarity": "Rare", "peluang": 7, "harga_yen": 1400},
    {"nama": "Item Kejutan 3", "rarity": "Epic", "peluang": 4, "harga_yen": 2600},
    {"nama": "Item Kejutan 4", "rarity": "Legendary", "peluang": 1.5, "harga_yen": 6000},
]
FILE_CACHE = Path(__file__).parent / "katalog_cache.json"      # dibuat otomatis (cadangan jika internet mati)
FILE_PENGGUNA = Path(__file__).parent / "data_pengguna.json"   # data akun (jangan di-commit)
KURS_CADANGAN = 105.0
SALDO_AWAL = 200_000

# Total bobot per rarity = 100 (jadi bisa dibaca sebagai persen)
BOBOT_RARITY = {"Common": 60, "Rare": 25, "Epic": 12, "Legendary": 3}
BATAS_RARITY = [("Common", 0.45), ("Rare", 0.75), ("Epic", 0.92), ("Legendary", 1.01)]

# Pengaturan peluang dinamis
PITY_MAKS = 10            # hard pity: setelah 10 Common berturut-turut, putaran berikutnya pasti Rare+
BONUS_PITY = 0.15         # soft pity: tiap Common berturut-turut menaikkan bobot Rare+ sebesar 15%
COOLDOWN_LEGENDARY = 10   # setelah dapat Legendary, 10 putaran berikutnya peluang Legendary separuh

AKUN_TERDAFTAR = {
    "pemain1": {"pin": "1234", "nama": "Pemain 1"},
    "pemain2": {"pin": "5678", "nama": "Pemain 2"},
    "demo": {"pin": "2026", "nama": "Akun Demo"},
}

# ---------------------------------------------------------------
# 2. STATE (struktur data utama disimpan di session_state)
# ---------------------------------------------------------------
_awal = {
    "user": None, "info_masuk": None,
    "antrean": deque(),        # QUEUE: antrean putaran
    "riwayat": [],             # STACK: riwayat hasil (pop = undo)
    "koleksi": Counter(),      # COUNTER: jumlah tiap item
    "cache": {},               # DICTIONARY: cache hasil scrape & API
    "pity": 0, "cooldown": 0, "saldo": 0, "total_masuk": 0,
    "grafik_saldo": [], "penjelasan_ai": "", "hasil_terbaru": [],
}
for _k, _v in _awal.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v


# ---------------------------------------------------------------
# 3. ALGORITMA: merge sort buatan sendiri + gacha (weighted random, pity, peluang dinamis)
# ---------------------------------------------------------------
def merge_sort(data, key, reverse=False):
    """Merge sort (stabil, O(n log n)). Mengembalikan list baru yang sudah terurut."""
    if len(data) <= 1:
        return list(data)
    tengah = len(data) // 2
    kiri = merge_sort(data[:tengah], key, reverse)
    kanan = merge_sort(data[tengah:], key, reverse)
    hasil, i, j = [], 0, 0
    while i < len(kiri) and j < len(kanan):
        a, b = key(kiri[i]), key(kanan[j])
        ambil_kiri = (a >= b) if reverse else (a <= b)
        if ambil_kiri:
            hasil.append(kiri[i])
            i += 1
        else:
            hasil.append(kanan[j])
            j += 1
    hasil.extend(kiri[i:])
    hasil.extend(kanan[j:])
    return hasil


def beri_rarity(item_mentah):
    """Olah data hasil scraping: urutkan dari yang termurah (merge sort), lalu bagi
    rarity berdasarkan posisi: termurah = Common, termahal = Legendary.
    Peluang tiap rarity dibagi rata ke item-itemnya (total 100)."""
    urut = merge_sort(item_mentah, key=lambda x: x["harga_yen"])
    total = len(urut)
    for idx, item in enumerate(urut):
        rasio = idx / max(total, 1)
        item["rarity"] = next(r for r, batas in BATAS_RARITY if rasio < batas)
    jumlah = Counter(x["rarity"] for x in urut)
    return [
        {"nama": x["nama"], "rarity": x["rarity"],
         "peluang": round(BOBOT_RARITY[x["rarity"]] / jumlah[x["rarity"]], 3),
         "harga_yen": x["harga_yen"]}
        for x in urut
    ]


def hitung_bobot(pool, pity, mesin, cooldown):
    """Bobot tiap item saat ini. Peluang berubah mengikuti keadaan pemain:
    - mesin Premium : Common separuh
    - soft pity     : tiap Common berturut-turut menaikkan bobot Rare ke atas
    - cooldown      : setelah dapat Legendary, bobot Legendary separuh sementara"""
    bobot = []
    for b in pool:
        w = float(b["peluang"])
        if b["rarity"] == "Common":
            if mesin == "Premium":
                w *= 0.5
        else:
            w *= 1 + BONUS_PITY * pity
        if b["rarity"] == "Legendary" and cooldown > 0:
            w *= 0.5
        bobot.append(w)
    return bobot


def pool_untuk(katalog, pity):
    if pity >= PITY_MAKS:  # hard pity: dijamin Rare ke atas
        pool = [b for b in katalog if b["rarity"] != "Common"]
        if pool:
            return pool
    return katalog


def putar(katalog, pity, mesin, cooldown=0):
    pool = pool_untuk(katalog, pity)
    return random.choices(pool, weights=hitung_bobot(pool, pity, mesin, cooldown))[0]


def peluang_efektif(katalog, pity, mesin, cooldown):
    """Persen peluang tiap rarity pada putaran berikutnya."""
    pool = pool_untuk(katalog, pity)
    bobot = hitung_bobot(pool, pity, mesin, cooldown)
    total = sum(bobot) or 1
    hasil = {r: 0.0 for r in RARITY_URUT}
    for b, w in zip(pool, bobot):
        hasil[b["rarity"]] = hasil.get(b["rarity"], 0.0) + w / total * 100
    return hasil


def perbarui_status(pity, cooldown, rarity):
    pity = pity + 1 if rarity == "Common" else 0
    cooldown = COOLDOWN_LEGENDARY if rarity == "Legendary" else max(0, cooldown - 1)
    return pity, cooldown


def hitung_status(riwayat):
    """Hitung ulang pity dan cooldown dari riwayat (dipakai saat login dan undo)."""
    pity, cooldown = 0, 0
    for h in riwayat:
        pity, cooldown = perbarui_status(pity, cooldown, h["rarity"])
    return pity, cooldown


KUNCI_RIWAYAT = ("nama", "rarity", "peluang", "harga_yen")
EKSPOR_KOLOM = ["nama", "rarity", "peluang", "harga_yen", "biaya"]


def proses_antrean(katalog, biaya, mesin):
    """Ambil putaran dari QUEUE satu per satu sampai habis / saldo habis."""
    s = st.session_state
    hasil_list, habis = [], False
    while s.antrean:
        if s.saldo < biaya:
            s.antrean.clear()
            habis = True
            break
        s.antrean.popleft()                                   # QUEUE: ambil depan
        hasil = putar(katalog, s.pity, mesin, s.cooldown)
        s.saldo -= biaya
        catatan = {k: hasil.get(k) for k in KUNCI_RIWAYAT}
        catatan["biaya"] = biaya
        s.riwayat.append(catatan)                             # STACK: push
        s.koleksi[hasil["nama"]] += 1
        s.grafik_saldo.append(s.saldo)
        s.pity, s.cooldown = perbarui_status(s.pity, s.cooldown, hasil["rarity"])
        hasil_list.append(catatan)
    return hasil_list, habis


def undo_terakhir():
    s = st.session_state
    if not s.riwayat:
        return
    terakhir = s.riwayat.pop()                                # STACK: pop
    s.saldo += terakhir["biaya"]
    s.koleksi[terakhir["nama"]] -= 1
    if s.koleksi[terakhir["nama"]] <= 0:
        del s.koleksi[terakhir["nama"]]
    if s.grafik_saldo:
        s.grafik_saldo.pop()
    s.pity, s.cooldown = hitung_status(s.riwayat)             # pity & cooldown ikut kembali
    s.hasil_terbaru = []


def reset_progres(saldo):
    s = st.session_state
    s.antrean.clear()
    s.riwayat.clear()
    s.koleksi.clear()
    s.grafik_saldo = []
    s.pity, s.cooldown = 0, 0
    s.saldo = saldo
    s.total_masuk = saldo
    s.penjelasan_ai = ""
    s.hasil_terbaru = []


# ---------------------------------------------------------------
# 4. LOGIN & DATA AKUN (disimpan di data_pengguna.json, PIN/password di-hash)
# ---------------------------------------------------------------
def _ke_json(o):
    return o.item() if hasattr(o, "item") else str(o)


def muat_semua():
    try:
        return json.loads(FILE_PENGGUNA.read_text(encoding="utf-8"))
    except Exception:
        return {}


def simpan_semua(data):
    sementara = FILE_PENGGUNA.with_suffix(".tmp")
    sementara.write_text(json.dumps(data, ensure_ascii=False, indent=1, default=_ke_json), encoding="utf-8")
    os.replace(sementara, FILE_PENGGUNA)


def hash_password(password, salt_hex):
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), 120_000).hex()


def sekarang():
    return datetime.now().strftime("%d %b %Y %H:%M")


def buat_akun(data, username, password, nama):
    salt = secrets.token_hex(16)
    data[username] = {
        "nama": nama, "salt": salt, "hash": hash_password(password, salt),
        "dibuat": sekarang(), "jumlah_masuk": 0, "terakhir_masuk": "-",
        "saldo": SALDO_AWAL, "total_masuk": SALDO_AWAL,
        "riwayat": [], "grafik_saldo": [],
    }


def cek_login(username, password):
    """Akun bawaan (pemain1, pemain2, demo) dibuatkan datanya saat pertama kali masuk."""
    username = username.strip().lower()
    data = muat_semua()
    if username not in data and username in AKUN_TERDAFTAR:
        if AKUN_TERDAFTAR[username]["pin"] == password:
            buat_akun(data, username, password, AKUN_TERDAFTAR[username]["nama"])
            try:
                simpan_semua(data)
            except OSError:
                return False, "Data tidak bisa disimpan (folder tidak bisa ditulis)."
    rec = data.get(username)
    if rec is None or not hmac.compare_digest(rec["hash"], hash_password(password, rec["salt"])):
        return False, "Username atau PIN salah."
    return True, username


def masuk_sebagai(username):
    """Catat kunjungan, lalu muat saldo & riwayat akun itu ke sesi."""
    s = st.session_state
    data = muat_semua()
    rec = data[username]
    sebelumnya = rec.get("terakhir_masuk", "-")
    rec["jumlah_masuk"] = rec.get("jumlah_masuk", 0) + 1
    rec["terakhir_masuk"] = sekarang()
    try:
        simpan_semua(data)
    except OSError:
        pass
    s.saldo = rec["saldo"]
    s.total_masuk = rec["total_masuk"]
    s.riwayat = list(rec["riwayat"])
    s.grafik_saldo = list(rec["grafik_saldo"])
    s.koleksi = Counter(h["nama"] for h in s.riwayat)
    s.pity, s.cooldown = hitung_status(s.riwayat)
    s.antrean = deque()
    s.penjelasan_ai = ""
    s.hasil_terbaru = []
    s.user = {"username": username, "nama": rec.get("nama", username)}
    s.info_masuk = (rec["jumlah_masuk"], sebelumnya)


def simpan_sesi():
    """Simpan progres pemain (saldo, riwayat) ke file supaya ada saat login lagi."""
    s = st.session_state
    if not s.user:
        return
    data = muat_semua()
    rec = data.get(s.user["username"])
    if rec is None:
        return
    rec.update(saldo=s.saldo, total_masuk=s.total_masuk,
               riwayat=s.riwayat, grafik_saldo=s.grafik_saldo)
    try:
        simpan_semua(data)
    except OSError:
        pass


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
                username = st.text_input("Username", placeholder="Masukkan username")
                pin = st.text_input("PIN", type="password", placeholder="Masukkan PIN")
                masuk = st.form_submit_button("Masuk ke Simulator", type="primary", width="stretch")
            if masuk:
                ok, hasil = cek_login(username, pin)
                if ok:
                    masuk_sebagai(hasil)
                    st.rerun()
                else:
                    st.error(hasil)

            st.caption("Saldo dan riwayat tersimpan per akun.")


if not st.session_state.user:
    render_login()
    st.stop()


# ---------------------------------------------------------------
# 5. DATA EKSTERNAL: Web Scraping Katalog + Frankfurter API Kurs
# ---------------------------------------------------------------
def _scrape_satu_halaman(url):
    """Ambil satu halaman, kembalikan LIST of DICTIONARY item mentah (nama, harga_yen)."""
    resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=12)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    hasil = []
    for el in soup.select("article.product_pod"):
        link = el.select_one("h3 a")
        harga_el = el.select_one("p.price_color")
        judul = (link.get("title") or link.get_text(strip=True)) if link else ""
        judul = re.sub(r"\s+", " ", judul).strip()
        if not judul:
            continue
        angka = re.search(r"(\d+(?:\.\d+)?)", harga_el.get_text() if harga_el else "")
        nilai_gbp = float(angka.group(1)) if angka else 10.0
        hasil.append({"nama": judul[:45], "harga_yen": max(400, int(round(nilai_gbp * 120)))})
    return hasil


def scrape_katalog():
    """Scrape beberapa halaman (BeautifulSoup), lalu olah: urutkan + beri rarity/peluang."""
    kunci = "katalog_scraped"
    if st.session_state.cache.get(kunci):
        return st.session_state.cache[kunci], f"cache scrape ({SCRAPE_URL})"
    try:
        mentah, sudah = [], set()
        for n, url in enumerate(SCRAPE_HALAMAN):
            try:
                for item in _scrape_satu_halaman(url):
                    if item["nama"] not in sudah:          # hindari nama ganda
                        sudah.add(item["nama"])
                        mentah.append(item)
            except Exception:
                if n == 0:                                   # halaman pertama wajib berhasil
                    raise
        if not mentah:
            raise ValueError("elemen produk kosong")
        katalog = beri_rarity(mentah)
        st.session_state.cache[kunci] = katalog
        try:
            FILE_CACHE.write_text(json.dumps(katalog, ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass
        return katalog, f"scraping ({len(katalog)} item dari {SCRAPE_URL})"
    except Exception as err:
        try:
            katalog = json.loads(FILE_CACHE.read_text(encoding="utf-8"))
            if katalog:
                return katalog, f"cache scraping terakhir (scrape gagal: {type(err).__name__})"
        except Exception:
            pass
        return KATALOG_CADANGAN, f"cadangan lokal (scrape gagal: {type(err).__name__})"


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
# 5b. AI (Gemini lewat REST, tinggal isi API key di sidebar)
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


def penjelasan_cadangan(riwayat, katalog, total_masuk, saldo):
    """Penjelasan otomatis (BUKAN AI) dari data hasil gacha, dipakai kalau AI tidak tersedia."""
    total = len(riwayat)
    total_bobot = sum(float(b["peluang"]) for b in katalog) or 1
    teori = Counter()
    for b in katalog:
        teori[b["rarity"]] += float(b["peluang"]) / total_bobot * 100
    nyata = Counter(h["rarity"] for h in riwayat)
    baris = []
    for r in RARITY_URUT:
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
    terpakai = total_masuk - saldo
    return (
        f"{nilai}\n\n" + "\n".join(baris) +
        f"\n\nSaldo terpakai Rp {terpakai:,} dari Rp {total_masuk:,}. "
        "Saran: tentukan batas budget sebelum bermain, karena hasil tiap putaran bersifat acak."
    )


# ---------------------------------------------------------------
# 6. SIDEBAR: AKUN & DATA INPUT
# ---------------------------------------------------------------
s = st.session_state
sb = st.sidebar
sb.header("Pengaturan")
jml, terakhir = s.info_masuk or (None, None)
info = f"Masuk ke-{jml}, sebelumnya: {terakhir}" if jml else "Akun tersimpan otomatis"
sb.info(f"👤 **{s.user['nama']}** (`{s.user['username']}`)\n\n{info}")
if sb.button("🚪 Logout", width="stretch"):
    simpan_sesi()
    s.user = None
    s.info_masuk = None
    reset_progres(0)
    st.rerun()

if sb.button("🕸️ Scrape ulang katalog", width="stretch"):
    s.cache.pop("katalog_scraped", None)
    st.rerun()

katalog, sumber_katalog = scrape_katalog()
sb.caption(f"Sumber katalog: {sumber_katalog} ({len(katalog)} item)")

mesin = sb.selectbox("Jenis mesin", ["Standar", "Premium"])
biaya = 20000 if mesin == "Standar" else 35000
sb.caption(f"Biaya per putaran: Rp {biaya:,} (uang simulasi)")
budget = sb.number_input("Budget simulasi (Rp)", 20000, 5_000_000, SALDO_AWAL, 10000,
                         help="Dipakai untuk Isi ulang saldo dan Reset progres.")
jumlah = sb.slider("Jumlah putaran", 1, 50, 10)

api_key = sb.text_input("Gemini API key", type="password")
model_ai = sb.text_input("Nama model AI", "gemini-4-hydrogen")
with sb.expander("AI cadangan (opsional)"):
    api_key2 = st.text_input("API key AI cadangan", type="password")
    base_url2 = st.text_input("Base URL (format OpenAI)", "https://api.groq.com/openai/v1")
    model2 = st.text_input("Model AI cadangan", "openai/gpt-oss-120b")

if sb.button("💰 Isi ulang saldo", width="stretch"):
    s.saldo += budget
    s.total_masuk += budget
    simpan_sesi()
    s.pesan = f"Saldo ditambah Rp {budget:,}."
    st.rerun()
yakin = sb.checkbox("Saya yakin ingin reset progres")
if sb.button("🔄 Mulai / Reset sesi", width="stretch", disabled=not yakin):
    reset_progres(budget)
    simpan_sesi()
    st.rerun()

kurs, sumber_kurs = ambil_kurs()
df_katalog = pd.DataFrame(katalog)
df_katalog["harga_rupiah"] = (df_katalog["harga_yen"] * kurs).round(0).astype(int)

# ---------------------------------------------------------------
# 7. HALAMAN UTAMA
# ---------------------------------------------------------------
st.markdown(
    f'<div class="hero-banner">{SVG_CLAW}<div>'
    '<p class="hero-title">Capit Boneka Simulator</p>'
    f'<p class="hero-sub">Halo <b>{e(s.user["nama"])}</b>! Simulasi edukasi tanpa uang asli '
    'untuk memahami peluang gacha &amp; mengatur budget.</p>'
    "</div></div>",
    unsafe_allow_html=True,
)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Saldo", f"Rp {s.saldo:,}", help=f"Total diisi Rp {s.total_masuk:,}")
c2.metric("Total putaran", len(s.riwayat), help=f"Terpakai Rp {sum(h['biaya'] for h in s.riwayat):,}")
c3.metric("Pity (tanpa Rare+)", f"{s.pity}/{PITY_MAKS}",
          help=f"Rare+ dijamin di {PITY_MAKS} Common berturut-turut. Cooldown Legendary: {s.cooldown}")
c4.metric("Kurs JPY→IDR", f"{kurs:,.1f}", help=f"Sumber: {sumber_kurs}")

st.write("")
tab1, tab2, tab3, tab4 = st.tabs(["🎰 Main", "📦 Koleksi", "📊 Grafik", "🤖 AI & Ekspor"])


def kartu_hasil(h):
    rarity = h["rarity"] if h["rarity"] in SVG_TOY_BADGE else "Common"
    return (
        f'<div class="drop-card drop-{rarity}">'
        f"<div>{SVG_TOY_BADGE[rarity]} <b>{e(h['nama'])}</b></div>"
        f'<span class="rarity-pill pill-{rarity}">{e(h["rarity"])}</span>'
        "</div>"
    )


# ---- TAB MAIN ----
with tab1:
    colA, colB = st.columns([2, 1])
    if colA.button(f"🎰 Putar {jumlah}x", type="primary", width="stretch"):
        for _ in range(jumlah):
            s.antrean.append("putar")                           # QUEUE: masuk antrean
        hasil_list, habis = proses_antrean(katalog, biaya, mesin)
        s.hasil_terbaru = hasil_list
        pesan = f"{len(hasil_list)} putaran selesai."
        if habis:
            pesan += " Saldo habis, sisa antrean dibatalkan. Isi ulang saldo di sidebar."
        s.pesan = pesan
        rarity_dapat = {h["rarity"] for h in hasil_list}
        s.perayaan = "Legendary" if "Legendary" in rarity_dapat else ("Epic" if "Epic" in rarity_dapat else None)
        simpan_sesi()
        st.rerun()   # supaya angka di atas (saldo, putaran, pity) ikut ter-update
    if colB.button("↩️ Undo putaran terakhir", width="stretch"):
        undo_terakhir()
        simpan_sesi()
        st.rerun()
    if "pesan" in s:
        st.success(s.pop("pesan"))
    perayaan = s.pop("perayaan", None)
    if perayaan == "Legendary":
        st.balloons()
        st.toast("Wah, kamu dapat item Legendary! 🌟")
    elif perayaan == "Epic":
        st.toast("Keren, dapat item Epic! ✨")

    st.subheader("Hasil putaran terakhir")
    if s.hasil_terbaru:
        st.markdown("".join(kartu_hasil(h) for h in s.hasil_terbaru[-10:]), unsafe_allow_html=True)
    else:
        st.info("Belum ada hasil putaran terakhir. Klik tombol Putar.")

    st.subheader("Peluang kamu sekarang")
    efektif = peluang_efektif(katalog, s.pity, mesin, s.cooldown)
    dasar = peluang_efektif(katalog, 0, mesin, 0)
    baris_html = []
    for r in RARITY_URUT:
        sel = efektif[r] - dasar[r]
        tanda = "▲ naik" if sel > 0.05 else ("▼ turun" if sel < -0.05 else "= normal")
        baris_html.append(
            f'<div class="chance-row"><div class="nm" style="color:{RARITY_WARNA[r]}">{r}</div>'
            f'<div class="bar"><span style="width:{min(efektif[r], 100):.1f}%;background:{RARITY_WARNA[r]}"></span></div>'
            f'<div class="pct"><b>{efektif[r]:.1f}%</b> (dasar {dasar[r]:.1f}%) {tanda}</div></div>'
        )
    st.markdown("".join(baris_html), unsafe_allow_html=True)
    catatan = []
    if s.pity >= PITY_MAKS:
        catatan.append("Pity penuh: putaran berikutnya pasti Rare atau lebih tinggi.")
    elif s.pity > 0:
        catatan.append(f"{s.pity} putaran berturut-turut tanpa Rare: bobot Rare, Epic, dan Legendary naik "
                       f"{BONUS_PITY * s.pity * 100:.0f}%.")
    if s.cooldown > 0:
        catatan.append(f"Baru dapat Legendary: peluang Legendary turun separuh selama {s.cooldown} putaran lagi.")
    if mesin == "Premium":
        catatan.append("Mesin Premium: peluang Common separuh dari biasanya.")
    if not catatan:
        catatan.append("Peluang normal: belum ada penyesuaian dari pity, cooldown, maupun mesin.")
    st.markdown('<div class="catatan">' + "<br>".join(e(c) for c in catatan) + "</div>",
                unsafe_allow_html=True)

    st.subheader("Riwayat terbaru")
    if s.riwayat:
        st.markdown("".join(kartu_hasil(h) for h in reversed(s.riwayat[-10:])), unsafe_allow_html=True)
    else:
        st.info("Belum ada putaran. Klik tombol Putar untuk mulai.")

    with st.expander("Katalog & peluang"):
        st.caption("Katalog hasil scraping, diurutkan dari harga dengan merge sort. "
                   "Makin mahal, makin langka.")
        st.dataframe(df_katalog, width="stretch")

# ---- TAB KOLEKSI (searching + sorting) ----
with tab2:
    st.subheader("Koleksi kamu")
    if s.koleksi:
        info_item = {h["nama"]: h for h in s.riwayat}            # DICTIONARY untuk lookup cepat
        nilai_koleksi = sum(info_item[n]["harga_yen"] * kurs * j
                            for n, j in s.koleksi.items() if n in info_item)
        terpakai = sum(h["biaya"] for h in s.riwayat)
        k1, k2, k3 = st.columns(3)
        k1.metric("Nilai koleksi (kurs terkini)", f"Rp {int(nilai_koleksi):,}")
        k2.metric("Uang virtual terpakai", f"Rp {terpakai:,}")
        k3.metric("Selisih", f"Rp {int(nilai_koleksi - terpakai):,}",
                  help="Nilai koleksi dikurangi uang yang dipakai memutar.")
        baris = []
        for nama, jml in s.koleksi.items():
            b = info_item.get(nama)
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
            baris = merge_sort(baris, key=lambda r: URUTAN_RARITY.get(r["rarity"], 0), reverse=True)
        elif urut == "nama":
            baris = merge_sort(baris, key=lambda r: r["nama"].lower())
        else:
            baris = merge_sort(baris, key=lambda r: r[urut], reverse=True)    # SORTING (merge sort)
        if baris:
            st.dataframe(pd.DataFrame(baris), width="stretch")
        else:
            st.info("Tidak ada item yang cocok dengan pencarian.")
    else:
        st.info("Koleksi masih kosong.")

# ---- TAB GRAFIK (4 visualisasi: pie, bar rarity, bar item, line saldo) ----
with tab3:
    if s.riwayat:
        skala = alt.Scale(domain=RARITY_URUT, range=[RARITY_WARNA[r] for r in RARITY_URUT])
        rarity_count = Counter(h["rarity"] for h in s.riwayat)
        df_r = pd.DataFrame({"rarity": list(rarity_count.keys()), "jumlah": list(rarity_count.values())})
        g1, g2 = st.columns(2)
        with g1:
            st.subheader("Distribusi rarity (pie chart)")
            pie = alt.Chart(df_r).mark_arc(innerRadius=45).encode(
                theta="jumlah:Q",
                color=alt.Color("rarity:N", scale=skala, sort=RARITY_URUT),
                tooltip=["rarity", "jumlah"],
            )
            st.altair_chart(pie, width="stretch")
        with g2:
            st.subheader("Jumlah per rarity")
            bar_r = alt.Chart(df_r).mark_bar().encode(
                x=alt.X("rarity:N", sort=RARITY_URUT),
                y="jumlah:Q",
                color=alt.Color("rarity:N", scale=skala, legend=None),
                tooltip=["rarity", "jumlah"],
            )
            st.altair_chart(bar_r, width="stretch")

        st.subheader("Jumlah per item")
        rar_nama = {h["nama"]: h["rarity"] for h in s.riwayat}
        df_b = pd.DataFrame([
            {"nama": n, "jumlah": j, "rarity": rar_nama.get(n, "Common")} for n, j in s.koleksi.items()
        ])
        bar_b = alt.Chart(df_b).mark_bar().encode(
            x="jumlah:Q",
            y=alt.Y("nama:N", sort="-x"),
            color=alt.Color("rarity:N", scale=skala, sort=RARITY_URUT),
            tooltip=["nama", "rarity", "jumlah"],
        )
        st.altair_chart(bar_b, width="stretch")

        st.subheader("Sisa saldo tiap putaran")
        df_s = pd.DataFrame({"putaran": range(1, len(s.grafik_saldo) + 1), "saldo": s.grafik_saldo})
        garis = alt.Chart(df_s).mark_line(point=True, color="#7c3aed").encode(
            x="putaran:Q", y="saldo:Q", tooltip=["putaran", "saldo"],
        )
        st.altair_chart(garis, width="stretch")
    else:
        st.info("Grafik muncul setelah ada putaran.")

# ---- TAB AI & EKSPOR ----
with tab4:
    st.subheader("Penjelasan AI")
    if st.button("Minta AI menjelaskan hasil"):
        total = len(s.riwayat)
        if total == 0:
            st.warning("Putar dulu minimal sekali.")
        else:
            rarity_count = dict(Counter(h["rarity"] for h in s.riwayat))
            prompt = (
                "Kamu asisten simulasi gacha (tanpa uang asli). "
                f"Total putaran: {total}. Hasil per rarity: {rarity_count}. "
                f"Peluang teoritis katalog: {[(b['nama'], b['rarity'], b['peluang']) for b in katalog]}. "
                f"Total uang virtual yang diisi Rp {s.total_masuk:,}, sisa Rp {s.saldo:,}. "
                "Jelaskan dengan bahasa Indonesia sederhana apakah pengguna beruntung atau sial "
                "dibanding peluang teoritis, beri saran batas budget bermain, dan buat deskripsi "
                "lucu 1 kalimat untuk item paling langka yang didapat."
            )
            with st.spinner("AI sedang berpikir..."):
                teks, berhasil = tanya_ai(prompt, api_key, model_ai)
                sumber = f"Gemini ({model_ai})"
                if not berhasil and api_key2:      # Gemini gagal: coba AI cadangan
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
                    + penjelasan_cadangan(s.riwayat, katalog, s.total_masuk, s.saldo)
                )
            s.penjelasan_ai = teks
    if s.penjelasan_ai:
        with st.container(border=True):
            st.write(s.penjelasan_ai)

    st.subheader("Ekspor data")
    if s.riwayat:
        df_riwayat = pd.DataFrame(s.riwayat)[EKSPOR_KOLOM]
        st.download_button(
            "Download JSON",
            json.dumps(df_riwayat.to_dict("records"), indent=2, ensure_ascii=False, default=_ke_json),
            "riwayat_gacha.json", "application/json",
        )
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as w:
            df_riwayat.to_excel(w, sheet_name="Riwayat", index=False)
            pd.DataFrame(
                [{"nama": n, "jumlah": j} for n, j in s.koleksi.items()]
            ).to_excel(w, sheet_name="Koleksi", index=False)
        st.download_button(
            "Download Excel", buf.getvalue(), "gacha_boneka.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    else:
        st.info("Ekspor tersedia setelah ada putaran.")
