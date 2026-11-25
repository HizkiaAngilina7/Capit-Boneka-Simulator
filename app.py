"""
Capit Boneka Simulator (Streamlit)
Simulasi gacha dan capit boneka dengan uang virtual untuk belajar peluang
dan mengatur budget.

Jalankan: streamlit run app.py
Install : pip install streamlit pandas requests openpyxl altair

Pemetaan ke proposal:
  2.2 Data input     : sidebar (budget, jumlah putaran, mesin, upload CSV)
      Data eksternal : ambil_kurs() -> Frankfurter API (JPY ke IDR)
  2.3 AI             : tanya_ai() -> Gemini API
  2.4 Struktur data  : antrean (queue/deque), riwayat (stack/list),
                       cache (dictionary), koleksi (Counter), katalog (list of dict)
      Algoritma      : putar() weighted random + pity, sorting & searching di tab Koleksi
  2.6 Visualisasi    : tab Grafik (pie, bar x2, line); Ekspor: tab AI & Ekspor (JSON, Excel)
"""
import io
import json
import random
import time
from collections import Counter, deque
from pathlib import Path

import altair as alt
import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="Capit Boneka Simulator", page_icon="🧸", layout="wide")

# ---------------------------------------------------------------
# 1. DATA KATALOG (bisa diganti lewat upload CSV)
#    Kolom CSV: nama, rarity, peluang, harga_yen
# ---------------------------------------------------------------
KATALOG_DEFAULT = [
    {"nama": "Beruang Mini", "rarity": "Common", "peluang": 12, "harga_yen": 500},
    {"nama": "Kelinci Kecil", "rarity": "Common", "peluang": 12, "harga_yen": 500},
    {"nama": "Bebek Kuning", "rarity": "Common", "peluang": 12, "harga_yen": 600},
    {"nama": "Kodok Hijau", "rarity": "Common", "peluang": 12, "harga_yen": 450},
    {"nama": "Domba Putih", "rarity": "Common", "peluang": 12, "harga_yen": 550},
    {"nama": "Kucing Oren", "rarity": "Rare", "peluang": 6, "harga_yen": 1200},
    {"nama": "Panda", "rarity": "Rare", "peluang": 6, "harga_yen": 1500},
    {"nama": "Anjing Corgi", "rarity": "Rare", "peluang": 6, "harga_yen": 1300},
    {"nama": "Pinguin Biru", "rarity": "Rare", "peluang": 7, "harga_yen": 1400},
    {"nama": "Unicorn", "rarity": "Epic", "peluang": 4, "harga_yen": 2500},
    {"nama": "Dino Hijau", "rarity": "Epic", "peluang": 4, "harga_yen": 2800},
    {"nama": "Ubur-ubur Pelangi", "rarity": "Epic", "peluang": 4, "harga_yen": 2600},
    {"nama": "Naga Emas", "rarity": "Legendary", "peluang": 1.5, "harga_yen": 6000},
    {"nama": "Phoenix Api", "rarity": "Legendary", "peluang": 1.5, "harga_yen": 6500},
]
FILE_KATALOG = Path(__file__).parent / "katalog_boneka.csv"   # dibuat otomatis jika belum ada
URUTAN_RARITY = {"Common": 1, "Rare": 2, "Epic": 3, "Legendary": 4}
KURS_CADANGAN = 105.0  # dipakai kalau API gagal (1 JPY ~ 105 IDR, hanya contoh)

# ---------------------------------------------------------------
# 2. STATE (struktur data utama disimpan di session_state)
# ---------------------------------------------------------------
if "init" not in st.session_state:
    st.session_state.init = True
    st.session_state.antrean = deque()      # QUEUE: antrean putaran
    st.session_state.riwayat = []           # STACK: riwayat hasil (pop = undo)
    st.session_state.koleksi = Counter()    # COUNTER: jumlah tiap boneka
    st.session_state.cache = {}             # DICTIONARY: cache hasil API
    st.session_state.pity = 0
    st.session_state.saldo = 0
    st.session_state.saldo_awal = 0
    st.session_state.grafik_saldo = []
    st.session_state.penjelasan_ai = ""


# ---------------------------------------------------------------
# 3. DATA EKSTERNAL: Frankfurter API (kurs JPY -> IDR) + cache
# ---------------------------------------------------------------
def ambil_kurs():
    kunci = "kurs_JPY_IDR"
    if kunci in st.session_state.cache:        # cek cache dulu
        return st.session_state.cache[kunci], "cache"
    try:
        url = "https://api.frankfurter.app/latest?from=JPY&to=IDR"
        data = requests.get(url, timeout=5).json()
        kurs = float(data["rates"]["IDR"])
        st.session_state.cache[kunci] = kurs   # simpan ke cache
        return kurs, "API Frankfurter"
    except Exception:
        return KURS_CADANGAN, "nilai cadangan (API gagal)"


# ---------------------------------------------------------------
# 4. ALGORITMA GACHA (weighted random + pity)
# ---------------------------------------------------------------
def putar(katalog, pity_count, mesin):
    pool = katalog
    if pity_count >= 10:  # pity: dijamin Rare ke atas
        pool = [b for b in katalog if b["rarity"] != "Common"]
    bobot = []
    for b in pool:
        w = b["peluang"]
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


def reset_semua(budget):
    st.session_state.antrean.clear()
    st.session_state.riwayat.clear()
    st.session_state.koleksi.clear()
    st.session_state.grafik_saldo = []
    st.session_state.pity = 0
    st.session_state.saldo = budget
    st.session_state.saldo_awal = budget
    st.session_state.penjelasan_ai = ""


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
                    time.sleep(2 * ke)       # tunggu sebentar lalu coba lagi
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
    total_bobot = sum(b["peluang"] for b in katalog)
    teori = Counter()
    for b in katalog:
        teori[b["rarity"]] += b["peluang"] / total_bobot * 100
    nyata = Counter(h["rarity"] for h in riwayat)
    baris = []
    for r in ["Common", "Rare", "Epic", "Legendary"]:
        persen = nyata[r] / total * 100
        baris.append(f"- {r}: {nyata[r]} dari {total} putaran ({persen:.0f}%), peluang teoritis {teori[r]:.0f}%")
    langka = nyata["Epic"] + nyata["Legendary"]
    harapan = (teori["Epic"] + teori["Legendary"]) / 100 * total
    if langka > harapan + 0.5:
        nilai = "Kamu cukup beruntung: boneka Epic dan Legendary yang didapat lebih banyak dari perkiraan."
    elif langka < harapan - 0.5:
        nilai = "Kamu kurang beruntung: boneka Epic dan Legendary yang didapat lebih sedikit dari perkiraan."
    else:
        nilai = "Hasilmu cukup sesuai dengan peluang teoritis."
    terpakai = saldo_awal - saldo
    return (
        f"{nilai}\n\n" + "\n".join(baris) +
        f"\n\nSaldo terpakai Rp {terpakai:,} dari Rp {saldo_awal:,}. "
        "Saran: tentukan batas budget sebelum bermain, karena hasil tiap putaran bersifat acak."
    )


# ---------------------------------------------------------------
# 6. SIDEBAR: DATA INPUT
# ---------------------------------------------------------------
st.sidebar.header("Pengaturan")
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


# Data input berupa FILE: katalog_boneka.csv dibuat otomatis kalau belum ada
if not FILE_KATALOG.exists():
    try:
        pd.DataFrame(KATALOG_DEFAULT).to_csv(FILE_KATALOG, index=False)
    except OSError:
        pass   # folder tidak bisa ditulis: pakai katalog bawaan di memori

katalog, sumber_katalog = KATALOG_DEFAULT, "katalog bawaan"
try:
    katalog, sumber_katalog = baca_katalog(FILE_KATALOG), FILE_KATALOG.name
except Exception:
    pass

if file_csv is not None:    # CSV yang diunggah menggantikan katalog default
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

if st.sidebar.button("Mulai / Reset sesi"):
    reset_semua(budget)

if st.session_state.saldo_awal == 0:
    reset_semua(budget)

kurs, sumber_kurs = ambil_kurs()
df_katalog = pd.DataFrame(katalog)
df_katalog["harga_rupiah"] = (df_katalog["harga_yen"] * kurs).round(0).astype(int)

# ---------------------------------------------------------------
# 7. HALAMAN UTAMA
# ---------------------------------------------------------------
st.title("🧸 Capit Boneka Simulator")
st.caption("Simulasi edukasi tanpa uang asli, untuk memahami peluang gacha.")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Saldo", f"Rp {st.session_state.saldo:,}")
c2.metric("Total putaran", len(st.session_state.riwayat))
c3.metric("Pity (tanpa Rare+)", f"{st.session_state.pity}/10")
c4.metric("Kurs JPY→IDR", f"{kurs:,.1f}", help=f"Sumber: {sumber_kurs}")

tab1, tab2, tab3, tab4 = st.tabs(["🎰 Main", "📦 Koleksi", "📊 Grafik", "🤖 AI & Ekspor"])

# ---- TAB MAIN ----
with tab1:
    colA, colB = st.columns(2)
    if colA.button(f"Putar {jumlah}x", type="primary"):
        for _ in range(jumlah):
            st.session_state.antrean.append("putar")       # QUEUE: masuk antrean
        n, habis = proses_antrean(katalog, biaya, mesin)
        pesan = f"{n} putaran selesai."
        if habis:
            pesan += " Saldo habis, sisa antrean dibatalkan."
        st.session_state.pesan = pesan
        st.rerun()   # supaya angka di atas (saldo, putaran, pity) ikut ter-update
    if colB.button("↩️ Undo putaran terakhir"):
        undo_terakhir()
        st.rerun()
    if "pesan" in st.session_state:
        st.success(st.session_state.pop("pesan"))

    st.subheader("Riwayat terbaru")
    if st.session_state.riwayat:
        for h in reversed(st.session_state.riwayat[-10:]):
            st.write(f"**{h['nama']}** ({h['rarity']})")
    else:
        st.info("Belum ada putaran. Klik tombol Putar.")

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
            if b is None:          # boneka dari katalog lama (CSV diganti): lewati
                continue
            baris.append({
                "nama": nama, "rarity": b["rarity"], "jumlah": jml,
                "harga_rupiah": int(b["harga_yen"] * kurs),
            })
        cari = st.text_input("Cari boneka (searching)")
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

# ---- TAB GRAFIK (4 visualisasi: pie, bar rarity, bar boneka, line saldo) ----
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

        st.subheader("Jumlah per boneka")
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
                "Kamu asisten simulasi gacha boneka (tanpa uang asli). "
                f"Total putaran: {total}. Hasil per rarity: {rarity_count}. "
                f"Peluang teoritis katalog: {[(b['nama'], b['rarity'], b['peluang']) for b in katalog]}. "
                f"Budget awal Rp {st.session_state.saldo_awal:,}, sisa Rp {st.session_state.saldo:,}. "
                "Jelaskan dengan bahasa Indonesia sederhana apakah pengguna beruntung atau sial "
                "dibanding peluang teoritis, beri saran batas budget bermain, dan buat deskripsi "
                "lucu 1 kalimat untuk boneka paling langka yang didapat."
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