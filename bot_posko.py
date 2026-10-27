import os
import sys
import requests
from playwright.sync_api import sync_playwright

# Konfigurasi dari GitHub Secrets
EMAIL = os.environ.get("POSKO_EMAIL")
PASSWORD = os.environ.get("POSKO_PASSWORD")
TG_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TG_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# Link cadangan jika hari itu kamu lupa kirim link ke Telegram
DEFAULT_LINK = "https://drive.google.com/file/d/1_LINK_CADANGAN_DEFAULT/view?usp=drivesdk"

def kirim_notif_telegram(pesan, foto_path=None):
    if not TG_TOKEN or not TG_CHAT_ID:
        return
    if foto_path and os.path.exists(foto_path):
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendPhoto"
        with open(foto_path, "rb") as f:
            requests.post(url, data={"chat_id": TG_CHAT_ID, "caption": pesan}, files={"photo": f})
    else:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": TG_CHAT_ID, "text": pesan})

def ambil_link_dari_telegram():
    """Membaca pesan terakhir yang kamu kirim ke Bot Telegram"""
    links = {"siang": DEFAULT_LINK, "dimtaq": DEFAULT_LINK, "malam": DEFAULT_LINK}
    if not TG_TOKEN:
        return links
    try:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/getUpdates"
        res = requests.get(url, timeout=10).json()
        for item in res.get("result", []):
            msg = item.get("message", {})
            text = msg.get("text", "").strip()
            # Pastikan pesan berasal dari kamu sendiri
            if str(msg.get("chat", {}).get("id")) == str(TG_CHAT_ID) and "drive.google.com" in text:
                parts = text.split()
                perintah = parts[0].lower().replace("/", "")
                link = next((p for p in parts if "drive.google.com" in p), DEFAULT_LINK)
                
                if perintah == "siang":
                    links["siang"] = link
                    # Jika dimtaq belum diset khusus, pakai link siang juga
                    if links["dimtaq"] == DEFAULT_LINK:
                        links["dimtaq"] = link
                elif perintah == "dimtaq":
                    links["dimtaq"] = link
                elif perintah == "malam":
                    links["malam"] = link
                else:
                    # Jika cuma kirim link tanpa kata kunci, masukkan ke semua
                    links["siang"] = links["dimtaq"] = links["malam"] = link
    except Exception as e:
        print("Gagal baca Telegram:", e)
    return links

def jalankan_robot(mode):
    links = ambil_link_dari_telegram()
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 412, "height": 915})
        page = context.new_page()

        try:
            print("Membuka Posko PBM...")
            page.goto("https://poskopbm.polri.go.id/input", wait_until="networkidle")

            # 1. Login jika diminta
            if page.locator("input[type='email'], input[placeholder*='Email' i]").count() > 0:
                page.get_by_label("Email").fill(EMAIL)
                page.get_by_label("Password").fill(PASSWORD)
                page.get_by_role("button", name="Masuk").click()
                page.wait_for_load_state("networkidle")
                page.wait_for_timeout(2000)

            # 2. Isi Identitas & Pilih Jabatan Kanit Samapta
            pelapor = page.locator("xpath=//label[contains(., 'Nama dan pangkat pelapor')]/following::input[1]")
            if pelapor.count() > 0:
                pelapor.fill("BRIPKA ABU ZAKARIYA, SH")

            page.locator("select").select_option(label="Kanit Samapta (3 kegiatan)")
            page.wait_for_timeout(2000)

            # 3. EKSEKUSI SESUAI JADWAL (SIANG / MALAM)
            if mode in ["siang", "malam"]:
                link_patroli = links["siang"] if mode == "siang" else links["malam"]
                
                # Klik Isi Laporan pada Patroli Sabhara QW1.10
                baris_patroli = page.locator("div, li").filter(has_text="Patroli Sabhara").filter(has_text="QW1.10")
                baris_patroli.get_by_role("button", name="Isi laporan").first.click()
                page.wait_for_timeout(1500)

                page.locator("xpath=//label[contains(., 'Nama dan pangkat pejabat pelaksana')]/following::input[1]").fill("BRIPKA ABU ZAKARIYA,S.H.")
                page.locator("xpath=//label[contains(., 'Rute patroli')]/following::input[1]").fill("MAKO - BRI - PASAR - BPD - BNI - MANDIRI - MAKO")
                page.locator("xpath=//label[contains(., 'Pertimbangan pilihan rute')]/following::textarea[1]").fill("Antisipasi Gangguan keamanan")
                page.locator("input[placeholder*='drive.google.com']").fill(link_patroli)

                page.wait_for_timeout(1000)
                page.get_by_role("button", name="Kirim laporan").click()
                page.wait_for_timeout(3000)
                
                ss_patroli = f"bukti_patroli_{mode}.png"
                page.screenshot(path=ss_patroli, full_page=False)
                kirim_notif_telegram(f"✅ Laporan PATROLI {mode.upper()} berhasil dikirim!\n🔗 Link: {link_patroli}", ss_patroli)

            # 4. JIKA SIANG, LANJUT ISI DIMTAQ EKSTERNAL (QW1.14)
            if mode == "siang" or mode == "dimtaq":
                link_dimtaq = links["dimtaq"]
                page.goto("https://poskopbm.polri.go.id/input", wait_until="networkidle")
                page.wait_for_timeout(1500)
                page.locator("select").select_option(label="Kanit Samapta (3 kegiatan)")
                page.wait_for_timeout(1500)

                baris_dimtaq = page.locator("div, li").filter(has_text="DIMTAQ").filter(has_text="QW1.14")
                baris_dimtaq.get_by_role("button", name="Isi laporan").first.click()
                page.wait_for_timeout(1500)

                page.locator("xpath=//label[contains(., 'Nama dan pangkat pejabat pelaksana')]/following::input[1]").fill("BRIPKA ABU ZAKARIYA, S.H.")
                page.locator("xpath=//label[contains(., 'Nama lokasi DIMTAQ')]/following::input[1]").fill("PASAR JATISRONO")
                page.locator("xpath=//label[contains(., 'Nama lokasi DIMTAQ')]/following::input[2]").fill("(-7.8273937, 111.1285440)")
                page.locator("xpath=//label[contains(., 'Pertimbangan pilihan lokasi')]/following::textarea[1]").fill("Antisipasi gangguan keamanan")

                # Isi jumlah pelanggar & pemuda dibina = 1
                jml_inputs = page.locator("xpath=//label[contains(., 'Jumlah')]/following::input[@type='number' or @type='text']")
                if jml_inputs.count() >= 2:
                    jml_inputs.nth(0).fill("1")
                    jml_inputs.nth(1).fill("1")

                page.locator("xpath=//label[contains(., 'Uraian pelaksanaan kegiatan')]/following::textarea[1]").fill("Melaksanakan patroli rutin")
                page.locator("input[placeholder*='drive.google.com']").fill(link_dimtaq)

                page.wait_for_timeout(1000)
                page.get_by_role("button", name="Kirim laporan").click()
                page.wait_for_timeout(3000)

                ss_dimtaq = "bukti_dimtaq.png"
                page.screenshot(path=ss_dimtaq, full_page=False)
                kirim_notif_telegram(f"✅ Laporan DIMTAQ EKSTERNAL berhasil dikirim!\n🔗 Link: {link_dimtaq}", ss_dimtaq)

        except Exception as e:
            err_ss = "error.png"
            page.screenshot(path=err_ss)
            kirim_notif_telegram(f"⚠️ Gagal mengirim laporan ({mode}):\n{str(e)}", err_ss)
        finally:
            browser.close()

if __name__ == "__main__":
    mode_pilihan = sys.argv[1] if len(sys.argv) > 1 else "siang"
    jalankan_robot(mode_pilihan)
