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

def ambil_link_dari_telegram():
    links = {"siang": DEFAULT_LINK, "dimtaq": DEFAULT_LINK, "malam": DEFAULT_LINK}
    if not TG_TOKEN:
        return links
    try:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/getUpdates"
        res = requests.get(url, timeout=15).json()
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
    return links

def jalankan_robot(mode):
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
                link_patroli = links["siang"] if mode == "siang" else links["malam"]
                
                # Klik tombol Patroli Sabhara QW1.10
                page.get_by_text("QW1.10").first.click()
                page.wait_for_timeout(2000)

                page.get_by_label("Nama dan pangkat pejabat pelaksana").fill("BRIPKA ABU ZAKARIYA,S.H.")
                page.get_by_label("Rute patroli").fill("MAKO - BRI - PASAR - BPD - BNI - MANDIRI - MAKO")
                page.get_by_placeholder("Alasan rute dipilih").fill("Antisipasi Gangguan keamanan")
                page.locator("input[placeholder*='drive.google.com']").fill(link_patroli)

                page.wait_for_timeout(1000)
                page.get_by_role("button", name="Kirim laporan").click()
                page.wait_for_timeout(4000)
                
                ss_patroli = f"bukti_patroli_{mode}.png"
                page.screenshot(path=ss_patroli)
                kirim_notif_telegram(f"✅ Laporan PATROLI {mode.upper()} berhasil dikirim!\n🔗 Link: {link_patroli}", ss_patroli)

            # 4. EKSEKUSI DIMTAQ EKSTERNAL (QW1.14)
            if mode in ["siang", "dimtaq"]:
                link_dimtaq = links["dimtaq"]
                
                # Klik langsung tombol menu QW1.14 DIMTAQ (atau tombol Isi laporan kedua)
                tombol_qw14 = page.locator("button, div").filter(has_text="QW1.14").filter(has_text="DIMTAQ")
                if page.get_by_role("button", name="Isi laporan").count() >= 2:
                    page.get_by_role("button", name="Isi laporan").nth(1).click()
                else:
                    tombol_qw14.last.click()
                page.wait_for_timeout(2500)

                # b. Nama dan pangkat pejabat pelaksana
                page.get_by_label("Nama dan pangkat pejabat pelaksana").fill("BRIPKA ABU ZAKARIYA, S.H.")
                
                # c. Nama lokasi DIMTAQ dan titik koordinat (2 kotak input di bawah bagian c)
                input_lokasi = page.locator("xpath=//*[contains(text(), 'Nama lokasi DIMTAQ')]/following::input")
                input_lokasi.nth(0).fill("PASAR JATISRONO")
                input_lokasi.nth(1).fill("(-7.8273937, 111.1285440)")

                # d. Pertimbangan pilihan lokasi
                page.locator("xpath=//*[contains(text(), 'Pertimbangan pilihan lokasi')]/following::textarea[1]").fill("Antisipasi gangguan keamanan")

                # e & f. Isi angka 1 pada kolom jumlah
                num_inputs = page.locator("input[type='number']")
                if num_inputs.count() >= 2:
                    num_inputs.nth(0).fill("1")
                    num_inputs.nth(1).fill("1")

                # h. Uraian pelaksanaan kegiatan
                page.locator("xpath=//*[contains(text(), 'Uraian pelaksanaan kegiatan')]/following::textarea[1]").fill("Melaksanakan patroli rutin")
                
                # k. Link Google Drive
                page.locator("input[placeholder*='drive.google.com']").fill(link_dimtaq)

                page.wait_for_timeout(1000)
                page.get_by_role("button", name="Kirim laporan").click()
                page.wait_for_timeout(4000)

                ss_dimtaq = "bukti_dimtaq.png"
                page.screenshot(path=ss_dimtaq)
                kirim_notif_telegram(f"✅ Laporan DIMTAQ EKSTERNAL berhasil dikirim!\n🔗 Link: {link_dimtaq}", ss_dimtaq)

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
