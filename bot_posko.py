import os
import sys
import requests
from playwright.sync_api import sync_playwright

EMAIL = os.environ.get("POSKO_EMAIL", "").strip()
PASSWORD = os.environ.get("POSKO_PASSWORD", "").strip()
TG_TOKEN = os.environ.get("TELEGRAM_TOKEN", "").strip()
TG_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "").strip()

DEFAULT_LINK = "https://drive.google.com/file/d/17KmVFmPU-OZk0dBdbVgF7AZ6ayhGWPyl/view?usp=drivesdk"

def kirim_notif_telegram(pesan, foto_path=None):
    print(f"Mengirim pesan ke Telegram (Chat ID: {TG_CHAT_ID})...")
    if not TG_TOKEN or not TG_CHAT_ID:
        print("❌ ERROR: TELEGRAM_TOKEN atau TELEGRAM_CHAT_ID kosong di GitHub Secrets!")
        return
    try:
        if foto_path and os.path.exists(foto_path):
            url = f"https://api.telegram.org/bot{TG_TOKEN}/sendPhoto"
            with open(foto_path, "rb") as f:
                r = requests.post(url, data={"chat_id": TG_CHAT_ID, "caption": pesan[:1000]}, files={"photo": f}, timeout=20)
        else:
            url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
            r = requests.post(url, data={"chat_id": TG_CHAT_ID, "text": pesan[:4000]}, timeout=20)
        print("Status Respon Telegram:", r.status_code, r.text)
    except Exception as e:
        print("Gagal kirim ke Telegram:", e)

def ambil_link_dari_telegram():
    links = {"siang": DEFAULT_LINK, "dimtaq": DEFAULT_LINK, "malam": DEFAULT_LINK}
    if not TG_TOKEN:
        return links
    try:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/getUpdates"
        res = requests.get(url, timeout=15).json()
        print("Cek pesan masuk Telegram:", res.get("ok"))
        for item in res.get("result", []):
            msg = item.get("message", {})
            text = msg.get("text", "").strip()
            if "drive.google.com" in text:
                parts = text.split()
                perintah = parts[0].lower().replace("/", "")
                link = next((p for p in parts if "drive.google.com" in p), DEFAULT_LINK)
                if perintah == "siang":
                    links["siang"] = link
                    if links["dimtaq"] == DEFAULT_LINK:
                        links["dimtaq"] = link
                elif perintah == "dimtaq":
                    links["dimtaq"] = link
                elif perintah == "malam":
                    links["malam"] = link
                else:
                    links["siang"] = links["dimtaq"] = links["malam"] = link
    except Exception as e:
        print("Gagal baca Telegram:", e)
    print("Link yang akan dipakai:", links)
    return links

def jalankan_robot(mode):
    print(f"=== MEMULAI ROBOT MODE: {mode.upper()} ===")
    kirim_notif_telegram(f"🤖 Robot Posko PBM mulai berjalan (Mode: {mode.upper()})...")
    links = ambil_link_dari_telegram()
    
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
            print("Membuka Posko PBM...")
            page.goto("https://poskopbm.polri.go.id/input", timeout=60000, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
            print("Judul Halaman:", page.title())

            # 1. Login jika diminta
            if page.locator("input[type='password']").count() > 0:
                print("Halaman Login terdeteksi, memasukkan email & password...")
                page.locator("input[type='email'], input[type='text']").first.fill(EMAIL)
                page.locator("input[type='password']").first.fill(PASSWORD)
                page.get_by_role("button", name="Masuk").click()
                page.wait_for_timeout(5000)
                print("Login diklik!")

            # 2. Isi Identitas & Pilih Jabatan Kanit Samapta
            print("Mengisi nama pelapor & memilih jabatan...")
            pelapor = page.locator("xpath=//label[contains(., 'Nama dan pangkat pelapor')]/following::input[1]")
            if pelapor.count() > 0:
                pelapor.fill("BRIPKA ABU ZAKARIYA, SH")

            page.locator("select").first.select_option(label="Kanit Samapta (3 kegiatan)")
            page.wait_for_timeout(2000)

            # 3. EKSEKUSI PATROLI SABHARA (SIANG / MALAM)
            if mode in ["siang", "malam"]:
                print(f"Mengisi form Patroli {mode}...")
                link_patroli = links["siang"] if mode == "siang" else links["malam"]
                
                baris_patroli = page.locator("div, li").filter(has_text="Patroli Sabhara").filter(has_text="QW1.10")
                baris_patroli.get_by_role("button", name="Isi laporan").first.click()
                page.wait_for_timeout(2000)

                page.locator("xpath=//label[contains(., 'Nama dan pangkat pejabat pelaksana')]/following::input[1]").fill("BRIPKA ABU ZAKARIYA,S.H.")
                page.locator("xpath=//label[contains(., 'Rute patroli')]/following::input[1]").fill("MAKO - BRI - PASAR - BPD - BNI - MANDIRI - MAKO")
                page.locator("xpath=//label[contains(., 'Pertimbangan pilihan rute')]/following::textarea[1]").fill("Antisipasi Gangguan keamanan")
                page.locator("input[placeholder*='drive.google.com']").fill(link_patroli)

                page.wait_for_timeout(1000)
                page.get_by_role("button", name="Kirim laporan").click()
                page.wait_for_timeout(4000)
                
                ss_patroli = f"bukti_patroli_{mode}.png"
                page.screenshot(path=ss_patroli)
                kirim_notif_telegram(f"✅ Laporan PATROLI {mode.upper()} berhasil dikirim!\n🔗 Link: {link_patroli}", ss_patroli)

            # 4. EKSEKUSI DIMTAQ EKSTERNAL
            if mode in ["siang", "dimtaq"]:
                print("Mengisi form DIMTAQ...")
                link_dimtaq = links["dimtaq"]
                page.goto("https://poskopbm.polri.go.id/input", timeout=60000, wait_until="domcontentloaded")
                page.wait_for_timeout(3000)
                page.locator("select").first.select_option(label="Kanit Samapta (3 kegiatan)")
                page.wait_for_timeout(2000)

                baris_dimtaq = page.locator("div, li").filter(has_text="DIMTAQ").filter(has_text="QW1.14")
                baris_dimtaq.get_by_role("button", name="Isi laporan").first.click()
                page.wait_for_timeout(2000)

                page.locator("xpath=//label[contains(., 'Nama dan pangkat pejabat pelaksana')]/following::input[1]").fill("BRIPKA ABU ZAKARIYA, S.H.")
                page.locator("xpath=//label[contains(., 'Nama lokasi DIMTAQ')]/following::input[1]").fill("PASAR JATISRONO")
                page.locator("xpath=//label[contains(., 'Nama lokasi DIMTAQ')]/following::input[2]").fill("(-7.8273937, 111.1285440)")
                page.locator("xpath=//label[contains(., 'Pertimbangan pilihan lokasi')]/following::textarea[1]").fill("Antisipasi gangguan keamanan")

                jml_inputs = page.locator("xpath=//label[contains(., 'Jumlah')]/following::input[@type='number' or @type='text']")
                if jml_inputs.count() >= 2:
                    jml_inputs.nth(0).fill("1")
                    jml_inputs.nth(1).fill("1")

                page.locator("xpath=//label[contains(., 'Uraian pelaksanaan kegiatan')]/following::textarea[1]").fill("Melaksanakan patroli rutin")
                page.locator("input[placeholder*='drive.google.com']").fill(link_dimtaq)

                page.wait_for_timeout(1000)
                page.get_by_role("button", name="Kirim laporan").click()
                page.wait_for_timeout(4000)

                ss_dimtaq = "bukti_dimtaq.png"
                page.screenshot(path=ss_dimtaq)
                kirim_notif_telegram(f"✅ Laporan DIMTAQ EKSTERNAL berhasil dikirim!\n🔗 Link: {link_dimtaq}", ss_dimtaq)

        except Exception as e:
            print("❌ TERJADI ERROR:", str(e))
            err_ss = "error.png"
            try:
                page.screenshot(path=err_ss)
                kirim_notif_telegram(f"⚠️ Gagal mengirim laporan ({mode}):\n{str(e)}", err_ss)
            except Exception as e2:
                print("Gagal screenshot error:", e2)
                kirim_notif_telegram(f"⚠️ Gagal membuka web ({mode}):\n{str(e)}")
        finally:
            browser.close()

if __name__ == "__main__":
    mode_pilihan = sys.argv[1] if len(sys.argv) > 1 else "siang"
    jalankan_robot(mode_pilihan)
