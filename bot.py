import os
import re
import random
import asyncio
import tempfile
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from playwright.async_api import async_playwright

# ─── TOKEN ───
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

# ─── FİRMALAR ───
FIRMALAR = {
    "ERTEK": {
        "unvan": "ERTEK TAVUKÇULUK SAN. TİC. LTD. ŞTİ",
        "adres": "Gıda Toptancılar sitesi G blok No:10/B Bağlar/Diyarbakır",
        "vd": "Gökalp V.D.",
        "vkn": "3720444794",
        "iban": "TR09 0020 5000 0962 6568 6000 01",
        "banka": "KUVEYT TÜRK",
    },
    "ULTEDA": {
        "unvan": "ALBAYRAKLAR ULTEDA TEM İNŞ YEMEK GIDA SAN VE TİC LTD ŞTİ",
        "adres": "Mezopotamya mah 613/4.sk Pia Comsept sitesi A blok no:4 A iç kapı 1 KAYAPINAR DİYARBAKIR",
        "vd": "Gökalp V.D.",
        "vkn": "0501428567",
        "iban": "TR65 0020 3000 1021 9069 0000 01",
        "banka": "ALBARAKA TÜRK",
    },
    "ÖZERTEK": {
        "unvan": "ÖZ ERTEK GIDA PAZ NAK LTD ŞTİ",
        "adres": "Yukarıazıklı mah OSB bulvarı MGT sitesi no:41 KIZILTEPE/MARDİN",
        "vd": "Gökalp V.D.",
        "vkn": "6620776048",
        "iban": "TR31 0020 5000 0962 6570 1000 01",
        "banka": "KUVEYT TÜRK",
    },
    "KARAKOÇ": {
        "unvan": "SALİH KARAKOÇ TAVUKÇULUK",
        "adres": "ŞEHİDİYE MAH YENİYOL CAD. NO:9/A ARTUKLU/MARDİN",
        "vd": "Mardin V.D.",
        "vkn": "25106373636",
        "iban": "TR29 0020 5000 0089 0466 9000 01",
        "banka": "KUVEYT TÜRK",
    },
    "ALBAYRAK": {
        "unvan": "ALBAYRAKLAR SOS.HİZ.İNŞ.OTO.GIDA TARIM A.Ş.",
        "adres": "Mesihpaşa mah Mesihpaşa cd hotel malkoç no:47 içkapı:104 Fatih/İSTANBUL",
        "vd": "Beyazıt V.D.",
        "vkn": "1630406928",
        "iban": "TR85 0001 0016 2280 7028 9450 02",
        "banka": "T.C. ZİRAAT BANKASI",
    },
}

# Kısa isim eşlemeleri (kullanıcı farklı yazabilir)
FIRMA_ALIAS = {
    "ERTEK": "ERTEK",
    "ULTEDA": "ULTEDA",
    "ÖZERTEK": "ÖZERTEK",
    "OZERTEK": "ÖZERTEK",
    "ÖZERTEK": "ÖZERTEK",
    "KARAKOÇ": "KARAKOÇ",
    "KARAKOC": "KARAKOÇ",
    "ALBAYRAK": "ALBAYRAK",
}

# ─── ÜRÜNLER ───
URUNLER = [
    {"ad": "POŞETLİ BÜTÜN PİLİÇ", "fiyat": 105},
    {"ad": "PİLİÇ SIRTSIZ GÖĞÜS", "fiyat": 150},
    {"ad": "PİLİÇ BAGET", "fiyat": 100},
    {"ad": "PİLİÇ IZGARA KANAT", "fiyat": 190},
    {"ad": "PİLİÇ SIRTSIZ ÜST BUT", "fiyat": 130},
    {"ad": "PİLİÇ KALÇALI BUT", "fiyat": 85},
]


# ─── TUTAR DAĞITIM ───
def dagilim_hesapla(toplam: int) -> list:
    kac = 4 if toplam > 3_000_000 else 3 if toplam > 1_000_000 else 2
    karisik = random.sample(URUNLER, kac)
    weights = [random.uniform(0.4, 1.0) for _ in karisik]
    w_sum = sum(weights)
    kalemler = []
    kalan = toplam
    for i, u in enumerate(karisik):
        if i == len(karisik) - 1:
            tutar = kalan
        else:
            ham = round((toplam * weights[i] / w_sum) / 1000) * 1000
            min_pay = 50_000
            max_pay = kalan - (len(karisik) - i - 1) * min_pay
            tutar = max(min_pay, min(ham, max_pay))
        kalan -= tutar
        kalemler.append({
            "urun": u["ad"],
            "birimFiyat": u["fiyat"],
            "toplamTutar": tutar,
            "miktar": tutar / u["fiyat"],
        })
    return kalemler


# ─── HTML OLUŞTUR ───
def html_olustur(satici_key: str, alici_key: str, toplam: int) -> str:
    S = FIRMALAR[satici_key]
    A = FIRMALAR[alici_key]
    kalemler = dagilim_hesapla(toplam)
    tarih = datetime.now().strftime("%d.%m.%Y")

    def fmt(n):
        return f"{n:,.0f}".replace(",", ".")

    def fmt_kg(n):
        return f"{n:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    rows = ""
    for i, k in enumerate(kalemler):
        rows += f"""
        <tr>
          <td class="idx">{i+1}</td>
          <td class="urun">{k['urun']}</td>
          <td class="num">{fmt_kg(k['miktar'])} kg</td>
          <td class="num">{fmt(k['birimFiyat'])} TL</td>
          <td class="num total">{fmt(k['toplamTutar'])} TL</td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap');
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ background: #f0f0f0; font-family: 'IBM Plex Sans', sans-serif; padding: 20px; }}

.proforma-page {{
  background: #fff; width: 794px; margin: 0 auto;
  font-family: 'IBM Plex Sans', sans-serif; color: #111;
}}
.pf-topbar {{ height: 8px; background: linear-gradient(90deg,#1a1a2e,#16213e 40%,#0f3460 70%,#533483); }}
.pf-body {{ padding: 40px 48px 44px; }}

.pf-header {{ display: grid; grid-template-columns: 1fr auto; gap: 32px;
  margin-bottom: 32px; padding-bottom: 24px; border-bottom: 1px solid #e0e0e0; }}
.pf-satici-unvan {{ font-size: 15px; font-weight: 600; color: #0f3460; margin-bottom: 6px; }}
.pf-satici-det {{ font-size: 11px; color: #666; line-height: 1.8; font-family: 'IBM Plex Mono', monospace; }}
.pf-title-block {{ text-align: right; }}
.pf-title {{ font-family: 'IBM Plex Mono', monospace; font-size: 20px; font-weight: 600;
  letter-spacing: 4px; color: #0f3460; margin-bottom: 8px; }}
.pf-tarih-badge {{ display: inline-block; background: #f5f0e8; border: 1px solid #d4b896;
  padding: 4px 12px; font-family: 'IBM Plex Mono', monospace; font-size: 11px; color: #8a6a3a; }}

.pf-alici-wrap {{ margin-bottom: 32px; }}
.pf-alici-label {{ font-family: 'IBM Plex Mono', monospace; font-size: 8px;
  letter-spacing: 3px; color: #999; margin-bottom: 8px; }}
.pf-alici-card {{ border: 1px solid #e0e0e0; border-left: 4px solid #0f3460;
  padding: 16px 20px; background: #f9f9fb; }}
.pf-alici-name {{ font-size: 13px; font-weight: 600; color: #111; margin-bottom: 4px; }}
.pf-alici-det {{ font-size: 11px; color: #666; line-height: 1.7; }}
.pf-alici-vkn {{ font-family: 'IBM Plex Mono', monospace; font-size: 10px; color: #888; margin-top: 4px; display: block; }}

.pf-table {{ width: 100%; border-collapse: collapse; margin-bottom: 0; }}
.pf-table thead tr {{ background: #0f3460; }}
.pf-table thead th {{ padding: 11px 14px; font-family: 'IBM Plex Mono', monospace;
  font-size: 9px; letter-spacing: 1.5px; font-weight: 500; color: rgba(255,255,255,0.85); text-align: left; }}
.pf-table thead th.r {{ text-align: right; }}
.pf-table tbody tr {{ border-bottom: 1px solid #efefef; }}
.pf-table tbody tr:nth-child(even) {{ background: #f8f8fb; }}
.pf-table tbody tr:last-child {{ border-bottom: 2px solid #e0e0e0; }}
.pf-table tbody td {{ padding: 12px 14px; color: #222; font-size: 12.5px; }}
.idx {{ font-family: 'IBM Plex Mono', monospace; font-size: 10px; color: #bbb; width: 30px; }}
.urun {{ font-weight: 500; color: #111; }}
.num {{ text-align: right; font-family: 'IBM Plex Mono', monospace; font-size: 12px; color: #333; }}
.total {{ color: #0f3460; font-weight: 600; }}

.pf-bottom {{ display: grid; grid-template-columns: 1fr auto; gap: 32px; margin-top: 24px; }}
.pf-conds {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px; align-content: start; }}
.pf-cond {{ font-size: 11px; color: #666; }}
.pf-cond b {{ color: #333; }}

.pf-totals {{ width: 280px; }}
.pf-total-row {{ display: flex; border-bottom: 1px solid #f0f0f0; }}
.pf-total-row .lbl {{ flex: 1; padding: 9px 14px; font-family: 'IBM Plex Mono', monospace;
  font-size: 10px; color: #777; background: #f7f7f7; }}
.pf-total-row .val {{ padding: 9px 14px; min-width: 130px; text-align: right;
  font-family: 'IBM Plex Mono', monospace; font-size: 11px; font-weight: 500; color: #333; }}
.pf-total-row.genel .lbl {{ background: #0f3460; color: rgba(255,255,255,0.8); font-weight: 600; font-size: 11px; }}
.pf-total-row.genel .val {{ background: #0f3460; color: #f0c060; font-weight: 700; font-size: 14px; }}

.pf-banka {{ margin-top: 20px; background: #f5f0e8; border: 1px solid #e0d0b0;
  padding: 14px 20px; display: flex; align-items: center; gap: 20px; flex-wrap: wrap; }}
.pf-banka-title {{ font-family: 'IBM Plex Mono', monospace; font-size: 8px;
  letter-spacing: 2.5px; color: #9a7a4a; white-space: nowrap; }}
.pf-banka-sep {{ width: 1px; height: 28px; background: #d4b896; }}
.pf-banka-item {{ font-size: 12px; display: flex; gap: 7px; align-items: center; }}
.pf-banka-item b {{ color: #5a3a10; font-size: 11px; }}
.pf-banka-item span {{ font-family: 'IBM Plex Mono', monospace; font-size: 11.5px; color: #333; }}

.pf-footer {{ margin-top: 32px; padding-top: 20px; border-top: 1px dashed #ddd;
  display: flex; justify-content: space-between; align-items: flex-end; }}
.pf-imza-box {{ text-align: center; width: 160px; }}
.pf-imza-line {{ border-bottom: 1px solid #ccc; height: 48px; margin-bottom: 8px; }}
.pf-imza-lbl {{ font-size: 9px; color: #aaa; font-family: 'IBM Plex Mono', monospace; letter-spacing: 1.5px; }}
.pf-watermark {{ font-family: 'IBM Plex Mono', monospace; font-size: 9px; color: #ccc; text-align: center; }}
.pf-botbar {{ height: 5px; background: linear-gradient(90deg,#533483,#0f3460 40%,#16213e 70%,#1a1a2e); }}
</style>
</head>
<body>
<div class="proforma-page">
  <div class="pf-topbar"></div>
  <div class="pf-body">

    <div class="pf-header">
      <div>
        <div class="pf-satici-unvan">{S['unvan']}</div>
        <div class="pf-satici-det">{S['adres']}<br>{S['vd']} &nbsp;·&nbsp; VKN: {S['vkn']}</div>
      </div>
      <div class="pf-title-block">
        <div class="pf-title">PROFORMA FATURA</div>
        <div class="pf-tarih-badge">TARİH: {tarih}</div>
      </div>
    </div>

    <div class="pf-alici-wrap">
      <div class="pf-alici-label">SAYIN</div>
      <div class="pf-alici-card">
        <div class="pf-alici-name">{A['unvan']}</div>
        <div class="pf-alici-det">{A['adres']}</div>
        <span class="pf-alici-vkn">{A['vd']} &nbsp;·&nbsp; VKN: {A['vkn']}</span>
      </div>
    </div>

    <table class="pf-table">
      <thead>
        <tr>
          <th>#</th><th>ÜRÜN ADI</th>
          <th class="r">MİKTAR</th><th class="r">BİRİM FİYAT</th><th class="r">TOPLAM FİYAT</th>
        </tr>
      </thead>
      <tbody>{rows}</tbody>
    </table>

    <div class="pf-bottom">
      <div class="pf-conds">
        <div class="pf-cond"><b>TESLİMAT:</b> Nakliye satıcıya aittir.</div>
        <div class="pf-cond"><b>ÖDEME:</b> Banka yolu ile EFT/Havale</div>
        <div class="pf-cond"><b>FİYAT:</b> TL olarak verilmiştir.</div>
        <div class="pf-cond"><b>GEÇERLİLİK:</b> 5 gündür.</div>
      </div>
      <div class="pf-totals">
        <div class="pf-total-row">
          <div class="lbl">TOPLAM</div><div class="val">{fmt(toplam)} TL</div>
        </div>
        <div class="pf-total-row">
          <div class="lbl">KDV %1</div><div class="val">KDV DAHİL</div>
        </div>
        <div class="pf-total-row genel">
          <div class="lbl">GENEL TOPLAM</div><div class="val">{fmt(toplam)} TL</div>
        </div>
      </div>
    </div>

    <div class="pf-banka">
      <div class="pf-banka-title">Banka Hesap Bilgileri</div>
      <div class="pf-banka-sep"></div>
      <div class="pf-banka-item"><b>BANKA:</b><span>{S['banka']}</span></div>
      <div class="pf-banka-item"><b>IBAN:</b><span>{S['iban']}</span></div>
    </div>

    <div class="pf-footer">
      <div class="pf-imza-box">
        <div class="pf-imza-line"></div>
        <div class="pf-imza-lbl">DÜZENLEYEN / İMZA</div>
      </div>
      <div class="pf-watermark">{S['unvan']}<br>{tarih}</div>
      <div class="pf-imza-box">
        <div class="pf-imza-line"></div>
        <div class="pf-imza-lbl">KAŞE / İMZA</div>
      </div>
    </div>

  </div>
  <div class="pf-botbar"></div>
</div>
</body>
</html>"""


# ─── HTML → PDF ───
async def html_to_pdf(html_content: str) -> bytes:
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.set_content(html_content, wait_until="networkidle")
        pdf_bytes = await page.pdf(
            format="A4",
            print_background=True,
            margin={"top": "5mm", "bottom": "5mm", "left": "5mm", "right": "5mm"},
        )
        await browser.close()
    return pdf_bytes


# ─── MESAJ PARSE ───
def parse_mesaj(metin: str):
    """
    Formatlar:
      ertek ulteda 4350000
      ertek → ulteda 4.350.000
      satici: ertek alici: ulteda tutar: 4350000
    """
    metin = metin.upper().strip()

    # Tutarı bul (rakam, nokta, virgül)
    tutar_match = re.search(r"[\d][.\d,]*\d", metin.replace(" ", ""))
    if not tutar_match:
        # Tek haneli rakam da olabilir
        tutar_match = re.search(r"\d+", metin)
    if not tutar_match:
        return None, None, None

    tutar_str = tutar_match.group().replace(".", "").replace(",", "")
    try:
        tutar = int(tutar_str)
    except:
        return None, None, None

    # Firma isimlerini bul
    firma_bul = []
    for alias, key in FIRMA_ALIAS.items():
        if alias in metin:
            firma_bul.append((metin.index(alias), key))

    firma_bul.sort(key=lambda x: x[0])  # Metindeki sıraya göre
    firma_keys = [f[1] for f in firma_bul]

    # Tekrarları kaldır (sıra korunarak)
    seen = []
    for k in firma_keys:
        if k not in seen:
            seen.append(k)
    firma_keys = seen

    if len(firma_keys) < 2:
        return None, None, None

    return firma_keys[0], firma_keys[1], tutar


# ─── BOT HANDLER'LAR ───
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    metin = """👋 *Proforma Fatura Botu*

Kullanım:
`ertek ulteda 4350000`
`özertek karakoç 2500000`

*Firmalar:*
• ERTEK
• ULTEDA  
• ÖZERTEK
• KARAKOÇ
• ALBAYRAK

Tutar TL cinsinden gir. Nokta/virgül olabilir.
"""
    await update.message.reply_text(metin, parse_mode="Markdown")


async def firmalar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    metin = "📋 *Kayıtlı Firmalar:*\n\n"
    for key, f in FIRMALAR.items():
        metin += f"*{key}*\n{f['unvan']}\n`{f['iban']}`\n\n"
    await update.message.reply_text(metin, parse_mode="Markdown")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    metin = update.message.text or ""

    satici_key, alici_key, tutar = parse_mesaj(metin)

    if not satici_key or not alici_key or not tutar:
        await update.message.reply_text(
            "❓ Anlamadım. Şöyle yaz:\n\n`ertek ulteda 4350000`",
            parse_mode="Markdown",
        )
        return

    if satici_key == alici_key:
        await update.message.reply_text("⚠️ Satıcı ve alıcı aynı olamaz.")
        return

    if tutar < 10_000:
        await update.message.reply_text("⚠️ Tutar çok küçük (min. 10.000 TL).")
        return

    S = FIRMALAR[satici_key]
    A = FIRMALAR[alici_key]

    await update.message.reply_text(
        f"⏳ Hazırlanıyor...\n\n"
        f"📤 *Satıcı:* {S['unvan']}\n"
        f"📥 *Alıcı:* {A['unvan']}\n"
        f"💰 *Tutar:* {tutar:,} TL".replace(",", "."),
        parse_mode="Markdown",
    )

    try:
        html = html_olustur(satici_key, alici_key, tutar)
        pdf_bytes = await html_to_pdf(html)

        tarih = datetime.now().strftime("%d%m%Y")
        dosya_adi = f"Proforma_{satici_key}_{alici_key}_{tarih}.pdf"

        await update.message.reply_document(
            document=pdf_bytes,
            filename=dosya_adi,
            caption=f"✅ Proforma hazır\n{S['unvan']} → {A['unvan']}\n{tutar:,} TL".replace(",", "."),
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Hata oluştu: {str(e)}")


# ─── MAIN ───
def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN environment variable ayarlı değil!")

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("firmalar", firmalar))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot başlatıldı...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
