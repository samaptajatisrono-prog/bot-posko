import os
import re
import sys
import random
from datetime import datetime, timedelta, timezone
import requests
from playwright.sync_api import sync_playwright

EMAIL = os.environ.get("POSKO_EMAIL", "").strip()
PASSWORD = os.environ.get("POSKO_PASSWORD", "").strip()
TG_TOKEN = os.environ.get("TELEGRAM_TOKEN", "").strip()
TG_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "").strip()

# ==========================================================
# LINK FOLDER GOOGLE DRIVE STOK 7 HARI
# ==========================================================
FOLDER_URLS = {
    "siang": "https://drive.google.com/drive/folders/1JZ3oF9j2quXlarQqcQqz9GhpwMbekQVA",
    "malam": "https://drive.google.com/drive/folders/1PPFrBZ7c8kQThXGi2f-BE4sFAXi5uaRU",
    "dimtaq": "https://drive.google.com/drive/folders/1L1wdZfq6DOKCukFTlE-qxN_m3Z-Z-KNa",
}

# ==========================================================
# 1. VARIASI PATROLI SABHARA (QW1.10) - SIANG & MALAM
# ==========================================================

DAFTAR_RUTE_SIANG = [
    "MAKO - BRI - PASAR - BPD - BNI - MANDIRI - MAKO",
    "MAKO - PASAR - BRI - BNI - MANDIRI - BPD - MAKO",
    "MAKO - MANDIRI - BNI - PASAR - BRI - SPBU - MAKO",
    "MAKO - SPBU - BRI - PASAR - BPD - MANDIRI - MAKO",
    "MAKO - BPD - PASAR - BRI - MANDIRI - BNI - MAKO",
    "MAKO - BNI - BRI - PASAR - MANDIRI - BPD - MAKO",
    "MAKO - TUGU BINTANG - PASAR - BRI - BPD - SPBU - MAKO",
]

DAFTAR_RUTE_MALAM = [
    "MAKO - BRI - BPD - BNI - MANDIRI - SPBU - MAKO",
    "MAKO - SPBU - MANDIRI - BNI - BRI - PASAR - MAKO",
    "MAKO - MANDIRI - BRI - PASAR - BPD - BNI - MAKO",
    "MAKO - PASAR - BPD - BRI - BNI - MANDIRI - MAKO",
    "MAKO - BNI - MANDIRI - SPBU - BRI - BPD - MAKO",
    "MAKO - TUGU BINTANG - BRI - BPD - SPBU - ALAS MBOGO - MAKO",
]

ALASAN_RUTE_SIANG = [
    "Antisipasi gangguan keamanan dan ketertiban masyarakat di sekitar objek vital dan pusat keramaian",
    "Antisipasi gangguan kamtibmas serta tindak kejahatan C3 pada jam aktif operasional perbankan dan pasar",
    "Memberikan rasa aman kepada masyarakat yang beraktivitas di pusat perekonomian dan objek vital perbankan",
    "Mencegah potensi tindak pidana kejahatan jalanan, premanisme, dan gangguan keamanan di wilayah hukum Polsek Jatisrono",
    "Pemantauan situasi kamtibmas di titik rawan keramaian masyarakat dan objek vital perbankan agar tetap aman kondusif",
]

ALASAN_RUTE_MALAM = [
    "Antisipasi gangguan keamanan dan tindak kejahatan C3 (Curat, Curas, Curanmor) pada jam rawan malam hari",
    "Mencegah potensi gangguan kamtibmas, kejahatan jalanan, serta pemantauan keamanan objek vital dan mesin ATM malam hari",
    "Patroli kewilayahan guna mengantisipasi kerawanan malam hari dan menjaga situasi kamtibmas tetap aman kondusif",
    "Antisipasi tindak pidana pencurian, balap liar, dan gangguan keamanan di sekitar objek vital pada malam hari",
    "Menjaga stabilitas keamanan wilayah hukum Polsek Jatisrono pada jam rawan malam hari",
]

# ==========================================================
# 2. VARIASI PAKET LOKASI & KOORDINAT ASLI DIMTAQ (QW1.14)
# ==========================================================

PAKET_DIMTAQ = [
    {
        "lokasi": "PASAR JATISRONO",
        "koordinat": "(-7.8273937, 111.1285440)",
        "pertimbangan": [
            "Pusat keramaian dan aktivitas ekonomi masyarakat yang rawan terjadi gangguan kamtibmas serta pelanggaran norma",
            "Antisipasi gangguan keamanan dan ketertiban umum di area pusat perbelanjaan masyarakat",
            "Lokasi aktivitas warga yang memerlukan pemeliharaan kamtibmas dan pembinaan ketertiban sosial",
        ],
        "uraian": [
            "Melaksanakan patroli dialogis dan memberikan pembinaan serta imbauan kamtibmas kepada warga maupun pemuda di area Pasar Jatisrono",
            "Melaksanakan patroli rutin serta mengajak masyarakat bersama-sama menjaga keamanan dan ketertiban di lingkungan pasar",
            "Melaksanakan kegiatan pembinaan disiplin dan imbauan kamtibmas secara humanis kepada warga di Pasar Jatisrono",
        ]
    },
    {
        "lokasi": "JALAN SEKITAR PASAR JATISRONO",
        "koordinat": "(-7.8274594, 111.1289731)",
        "pertimbangan": [
            "Jalur utama aktivitas masyarakat di sekitar pasar yang rawan potensi pelanggaran norma dan gangguan ketertiban umum",
            "Antisipasi gangguan keamanan, premanisme, serta potensi kerawanan sosial di jalan sekitar Pasar Jatisrono",
            "Titik keramaian lalu lalang warga dan pemuda yang memerlukan pengawasan serta pembinaan kamtibmas",
        ],
        "uraian": [
            "Melaksanakan patroli rutin dan memberikan imbauan kamtibmas kepada warga serta pemuda di jalan sekitar Pasar Jatisrono",
            "Melaksanakan kegiatan patroli sambang dan pembinaan norma kepada masyarakat guna menjaga situasi tetap aman dan tertib",
            "Melaksanakan patroli dialogis guna mengantisipasi gangguan kamtibmas dan pelanggaran ketertiban umum di sekitar pasar",
        ]
    },
    {
        "lokasi": "JALAN SEKITAR SPBU JATISRONO",
        "koordinat": "(-7.8296862, 111.1607271)",
        "pertimbangan": [
            "Titik rawan berkumpulnya pemuda di jalur sekitar SPBU yang memerlukan pengawasan guna mencegah pelanggaran norma dan gangguan kamtibmas",
            "Antisipasi gangguan keamanan, ketertiban umum, serta potensi kerawanan remaja di jalan sekitar SPBU Jatisrono",
            "Lokasi strategis di jalur utama yang kerap menjadi tempat berkumpulnya masyarakat dan remaja sehingga perlu pembinaan kamtibmas",
        ],
        "uraian": [
            "Melaksanakan patroli rutin serta memberikan pembinaan kepada pemuda yang ditemui di sekitar SPBU Jatisrono agar menjauhi pelanggaran norma",
            "Melaksanakan patroli dialogis dan menyampaikan pesan kamtibmas kepada warga serta remaja di jalan sekitar SPBU Jatisrono",
            "Melaksanakan kegiatan pembinaan ketertiban masyarakat guna mencegah gangguan keamanan di area sekitar SPBU Jatisrono",
        ]
    },
    {
        "lokasi": "TUGU BINTANG JATISRONO",
        "koordinat": "(-7.8272791, 111.1287683)",
        "pertimbangan": [
            "Titik kumpul masyarakat dan remaja di kawasan Tugu Bintang Jatisrono yang berpotensi menimbulkan kerawanan kamtibmas dan pelanggaran norma",
            "Antisipasi gangguan keamanan serta pencegahan kenakalan remaja dan pelanggaran ketertiban sosial di area Tugu Bintang Jatisrono",
            "Kawasan ruang publik yang ramai dikunjungi warga dan pemuda sehingga memerlukan kehadiran Polri untuk pembinaan kamtibmas",
        ],
        "uraian": [
            "Melaksanakan patroli pembinaan secara humanis kepada warga dan pemuda di kawasan Tugu Bintang Jatisrono guna menjaga ketertiban umum",
            "Melaksanakan patroli dialogis serta memberikan edukasi dan imbauan kamtibmas kepada remaja yang berkumpul di sekitar Tugu Bintang",
            "Melaksanakan patroli rutin dan pembinaan disiplin masyarakat di area Tugu Bintang Jatisrono agar situasi tetap aman kondusif",
        ]
    },
    {
        "lokasi": "ALAS MBOGO JATISRONO",
        "koordinat": "(-7.8549743, 111.0955813)",
        "pertimbangan": [
            "Kawasan rawan yang memerlukan pengawasan intensif guna mencegah potensi pelanggaran norma sosial, miras, maupun gangguan kamtibmas",
            "Antisipasi gangguan keamanan dan penyakit masyarakat di jalur Alas Mbogo Jatisrono agar situasi wilayah tetap aman terkendali",
            "Lokasi yang berpotensi dimanfaatkan oleh oknum pemuda untuk melakukan aktivitas yang melanggar norma dan ketertiban umum",
        ],
        "uraian": [
            "Melaksanakan patroli rutin dan razia pembinaan di kawasan Alas Mbogo Jatisrono guna mencegah pelanggaran norma serta gangguan kamtibmas",
            "Melaksanakan pemantauan wilayah dan memberikan pembinaan disiplin kepada masyarakat maupun pemuda yang ditemui di sekitar Alas Mbogo",
            "Melaksanakan patroli kewilayahan serta imbauan kamtibmas di area Alas Mbogo Jatisrono guna menciptakan rasa aman bagi masyarakat",
        ]
    }
]

def kirim_notif_telegram(pesan, foto_path=None):
    if not TG_TOKEN or not TG_CHAT_ID:
        return
    try:
        if foto_path and os.path.exists(foto_path):
            url = f"https://api.telegram.org/bot{TG_TOKEN}/sendPhoto"
            with open(foto_path, "rb") as f:
                requests.post(url, data={"chat_id": TG_CHAT_ID, "caption": pesan[:1000]}, files={"photo": f}, timeout=20)
        else:
            url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
            requests.post(url, data={"chat_id": TG_CHAT_ID, "text": pesan[:4000]}, timeout=20)
    except Exception as e:
        print("Gagal kirim ke Telegram:", e)

def ambil_satu_foto_dari_folder(page, kategori):
    """Membuka folder Google Drive, mendeteksi semua file foto di dalamnya,
    dan memilih 1 link foto sesuai urutan hari (Hari 1 s/d 7, lalu kembali ke 1)."""
    folder_url = FOLDER_URLS[kategori]
    folder_id = folder_url.rstrip("/").split("/")[-1].split("?")[0]
    embed_url = f"https://drive.google.com/embeddedfolderview?id={folder_id}#list"

    # Hitung urutan hari berdasarkan Waktu Indonesia Barat (WIB / UTC+7)
    wib_now = datetime.now(timezone(timedelta(hours=7)))
    indeks_hari = wib_now.weekday()  # Senin=0 (Foto 1) ... Minggu=6 (Foto 7)

    file_links = []
    try:
        # Cara 1: Ambil dari tampilan daftar publik Google Drive
        res = requests.get(embed_url, timeout=20)
        ids = re.findall(r"/file/d/([a-zA-Z0-9_-]{25,})/", res.text)
        if not ids:
            ids = re.findall(r'id="entry-([a-zA-Z0-9_-]{25,})"', res.text)
        
        seen = set()
        for fid in ids:
            if fid != folder_id and fid not in seen:
                seen.add(fid)
                file_links.append(f"https://drive.google.com/file/d/{fid}/view?usp=drivesdk")

        # Cara 2 (Cadangan): Jika perlu render lewat browser Playwright
        if not file_links:
            page.goto(folder_url, timeout=60000, wait_until="domcontentloaded")
            page.wait_for_timeout(4000)
            html = page.content()
            ids2 = re.findall(r'data-id="([a-zA-Z0-9_-]{25,})"', html)
            for fid in ids2:
                if fid != folder_id and fid not in seen:
                    seen.add(fid)
                    file_links.append(f"https://drive.google.com/file/d/{fid}/view?usp=drivesdk")
    except Exception as e:
        print(f"Gagal memindai folder {kategori}:", e)

    if file_links:
        idx_terpilih = indeks_hari % len(file_links)
        link_terpilih = file_links[idx_terpilih]
        print(f"[{kategori.upper()}] Ditemukan {len(file_links)} foto. Hari ke-{indeks_hari + 1} -> Pakai Foto #{idx_terpilih + 1}")
        return link_terpilih, idx_terpilih + 1, len(file_links)

    # Jika folder kosong, gunakan link foldernya
    return folder_url, 1, 1

def jalankan_robot(mode):
    kirim_notif_telegram(f"🤖 Robot Posko PBM mulai berjalan otomatis (Mode: {mode.upper()})...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )
        context = browser.new_context(
            viewport={"width": 412, "height": 915},
            ignore_https_errors=True,
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
        )
        page = context.new_page()

        try:
            # Pilih dulu 1 link foto dari dalam masing-masing folder sesuai giliran hari
            link_siang, urut_siang, total_siang = ambil_satu_foto_dari_folder(page, "siang") if mode == "siang" else ("", 0, 0)
            link_malam, urut_malam, total_malam = ambil_satu_foto_dari_folder(page, "malam") if mode == "malam" else ("", 0, 0)
            link_dimtaq, urut_dimtaq, total_dimtaq = ambil_satu_foto_dari_folder(page, "dimtaq") if mode in ["siang", "dimtaq"] else ("", 0, 0)

            page.goto("https://poskopbm.polri.go.id/input", timeout=60000, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)

            # 1. Login jika diminta
            if page.locator("input[type='password']").count() > 0:
                page.locator("input[type='email'], input[type='text']").first.fill(EMAIL)
                page.locator("input[type='password']").first.fill(PASSWORD)
                page.get_by_role("button", name="Masuk").click()
                page.wait_for_timeout(5000)

            # 2. Isi Identitas & Pilih Jabatan Kanit Samapta
            page.get_by_label("Nama dan pangkat pelapor").fill("BRIPKA ABU ZAKARIYA, SH")
            page.locator("select").first.select_option(label="Kanit Samapta (3 kegiatan)")
            page.wait_for_timeout(2000)

            # 3. EKSEKUSI PATROLI SABHARA (SIANG / MALAM)
            if mode in ["siang", "malam"]:
                link_patroli = link_siang if mode == "siang" else link_malam
                no_foto = urut_siang if mode == "siang" else urut_malam
                tot_foto = total_siang if mode == "siang" else total_malam
                rute_pilihan = random.choice(DAFTAR_RUTE_SIANG if mode == "siang" else DAFTAR_RUTE_MALAM)
                alasan_pilihan = random.choice(ALASAN_RUTE_SIANG if mode == "siang" else ALASAN_RUTE_MALAM)
                
                page.get_by_role("button", name="Isi laporan").nth(0).click()
                page.wait_for_timeout(2500)

                page.get_by_label("Nama dan pangkat pejabat pelaksana").fill("BRIPKA ABU ZAKARIYA,S.H.")
                page.get_by_label("Rute patroli").fill(rute_pilihan)
                page.get_by_placeholder("Alasan rute dipilih").fill(alasan_pilihan)
                page.locator("input[placeholder*='drive.google.com']").fill(link_patroli)

                page.wait_for_timeout(1000)
                page.get_by_role("button", name="Kirim laporan").click()
                page.wait_for_timeout(4000)
                
                ss_patroli = f"bukti_patroli_{mode}.png"
                page.screenshot(path=ss_patroli)
                kirim_notif_telegram(
                    f"✅ Laporan PATROLI {mode.upper()} berhasil dikirim!\n\n"
                    f"📸 Foto ke-{no_foto} dari {tot_foto} di Folder\n"
                    f"🛣️ Rute: {rute_pilihan}\n"
                    f"📋 Pertimbangan: {alasan_pilihan}\n"
                    f"🔗 Link Foto: {link_patroli}",
                    ss_patroli
                )

            # 4. EKSEKUSI DIMTAQ EKSTERNAL (QW1.14)
            if mode in ["siang", "dimtaq"]:
                paket = random.choice(PAKET_DIMTAQ)
                pertimbangan_dimtaq = random.choice(paket["pertimbangan"])
                uraian_dimtaq = random.choice(paket["uraian"])
                
                page.get_by_role("button", name="Isi laporan").nth(1).click()
                page.wait_for_timeout(2500)

                page.get_by_label("Nama dan pangkat pejabat pelaksana").fill("BRIPKA ABU ZAKARIYA, S.H.")
                
                input_lokasi = page.locator("xpath=//*[contains(text(), 'Nama lokasi DIMTAQ')]/following::input")
                input_lokasi.nth(0).fill(paket["lokasi"])
                input_lokasi.nth(1).fill(paket["koordinat"])

                page.locator("xpath=//*[contains(text(), 'Pertimbangan pilihan lokasi')]/following::textarea[1]").fill(pertimbangan_dimtaq)

                num_inputs = page.locator("input[type='number']")
                if num_inputs.count() >= 2:
                    num_inputs.nth(0).fill("1")
                    num_inputs.nth(1).fill("1")

                page.locator("xpath=//*[contains(text(), 'Uraian pelaksanaan kegiatan')]/following::textarea[1]").fill(uraian_dimtaq)
                page.locator("input[placeholder*='drive.google.com']").fill(link_dimtaq)

                page.wait_for_timeout(1000)
                page.get_by_role("button", name="Kirim laporan").click()
                page.wait_for_timeout(4000)

                ss_dimtaq = "bukti_dimtaq.png"
                page.screenshot(path=ss_dimtaq)
                kirim_notif_telegram(
                    f"✅ Laporan DIMTAQ EKSTERNAL berhasil dikirim!\n\n"
                    f"📸 Foto ke-{urut_dimtaq} dari {total_dimtaq} di Folder\n"
                    f"📍 Lokasi: {paket['lokasi']} {paket['koordinat']}\n"
                    f"📋 Pertimbangan: {pertimbangan_dimtaq}\n"
                    f"📝 Uraian: {uraian_dimtaq}\n"
                    f"🔗 Link Foto: {link_dimtaq}",
                    ss_dimtaq
                )

        except Exception as e:
            err_ss = "error.png"
            try:
                page.screenshot(path=err_ss)
                kirim_notif_telegram(f"⚠️ Gagal mengirim laporan ({mode}):\n{str(e)}", err_ss)
            except Exception:
                kirim_notif_telegram(f"⚠️ Gagal membuka web ({mode}):\n{str(e)}")
        finally:
            browser.close()

if __name__ == "__main__":
    mode_pilihan = sys.argv[1] if len(sys.argv) > 1 else "siang"
    jalankan_robot(mode_pilihan)
