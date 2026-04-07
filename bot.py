import os
import re
import random
import io
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from weasyprint import HTML as WeasyHTML

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

FIRMALAR = {
    "ERTEK": {
        "unvan": "ERTEK TAVUKÇULUK SAN. TİC. LTD. ŞTİ",
        "adres": "Gıda Toptancılar sitesi G blok No:10/B Bağlar/Diyarbakır",
        "vd": "Gökalp V.D.", "vkn": "3720444794",
        "iban": "TR09 0020 5000 0962 6568 6000 01", "banka": "KUVEYT TÜRK",
    },
    "ULTEDA": {
        "unvan": "ALBAYRAKLAR ULTEDA TEM İNŞ YEMEK GIDA SAN VE TİC LTD ŞTİ",
        "adres": "Mezopotamya mah 613/4.sk Pia Comsept sitesi A blok no:4 A iç kapı 1 KAYAPINAR DİYARBAKIR",
        "vd": "Gökalp V.D.", "vkn": "0501428567",
        "iban": "TR65 0020 3000 1021 9069 0000 01", "banka": "ALBARAKA TÜRK",
    },
    "ÖZERTEK": {
        "unvan": "ÖZ ERTEK GIDA PAZ NAK LTD ŞTİ",
        "adres": "Yukarıazıklı mah OSB bulvarı MGT sitesi no:41 KIZILTEPE/MARDİN",
        "vd": "Gökalp V.D.", "vkn": "6620776048",
        "iban": "TR31 0020 5000 0962 6570 1000 01", "banka": "KUVEYT TÜRK",
    },
    "KARAKOÇ": {
        "unvan": "SALİH KARAKOÇ TAVUKÇULUK",
        "adres": "ŞEHİDİYE MAH YENİYOL CAD. NO:9/A ARTUKLU/MARDİN",
        "vd": "Mardin V.D.", "vkn": "25106373636",
        "iban": "TR29 0020 5000 0089 0466 9000 01", "banka": "KUVEYT TÜRK",
    },
    "ALBAYRAK": {
        "unvan": "ALBAYRAKLAR SOS.HİZ.İNŞ.OTO.GIDA TARIM A.Ş.",
        "adres": "Mesihpaşa mah Mesihpaşa cd hotel malkoç no:47 içkapı:104 Fatih/İSTANBUL",
        "vd": "Beyazıt V.D.", "vkn": "1630406928",
        "iban": "TR85 0001 0016 2280 7028 9450 02", "banka": "T.C. ZİRAAT BANKASI",
    },
}

FIRMA_ALIAS = {
    "ERTEK": "ERTEK",
    "ULTEDA": "ULTEDA",
    "ÖZERTEK": "ÖZERTEK", "OZERTEK": "ÖZERTEK",
    "KARAKOÇ": "KARAKOÇ", "KARAKOC": "KARAKOÇ",
    "ALBAYRAK": "ALBAYRAK",
}

URUNLER = [
    {"ad": "POŞETLİ BÜTÜN PİLİÇ", "fiyat": 105},
    {"ad": "PİLİÇ SIRTSIZ GÖĞÜS", "fiyat": 150},
    {"ad": "PİLİÇ BAGET", "fiyat": 100},
    {"ad": "PİLİÇ IZGARA KANAT", "fiyat": 190},
    {"ad": "PİLİÇ SIRTSIZ ÜST BUT", "fiyat": 130},
    {"ad": "PİLİÇ KALÇALI BUT", "fiyat": 85},
]

def dagilim_hesapla(toplam):
    kac = 4 if toplam > 3_000_000 else 3 if toplam > 1_000_000 else 2
    karisik = random.sample(URUNLER, kac)
    weights = [random.uniform(0.4, 1.0) for _ in karisik]
    w_sum = sum(weights)
    kalemler, kalan = [], toplam
    for i, u in enumerate(karisik):
        if i == len(karisik) - 1:
            tutar = kalan
        else:
            ham = round((toplam * weights[i] / w_sum) / 1000) * 1000
            tutar = max(50_000, min(ham, kalan - (len(karisik) - i - 1) * 50_000))
        kalan -= tutar
        kalemler.append({"urun": u["ad"], "birimFiyat": u["fiyat"],
                         "toplamTutar": tutar, "miktar": tutar / u["fiyat"]})
    return kalemler

def fmt(n):
    s = f"{int(n):,}".replace(",", ".")
    return s

def fmt_kg(n):
    return f"{n:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def html_olustur(satici_key, alici_key, toplam):
    S = FIRMALAR[satici_key]
    A = FIRMALAR[alici_key]
    kalemler = dagilim_hesapla(toplam)
    tarih = datetime.now().strftime("%d.%m.%Y")

    rows = ""
    for i, k in enumerate(kalemler):
        bg = "#f8f8fb" if i % 2 == 1 else "#ffffff"
        rows += f"""
        <tr style="background:{bg};border-bottom:1px solid #efefef;">
          <td style="padding:11px 14px;font-family:monospace;font-size:10px;color:#bbb;width:28px;">{i+1}</td>
          <td style="padding:11px 14px;font-weight:500;color:#111;font-size:12.5px;">{k['urun']}</td>
          <td style="padding:11px 14px;text-align:right;font-family:monospace;font-size:12px;color:#333;">{fmt_kg(k['miktar'])} kg</td>
          <td style="padding:11px 14px;text-align:right;font-family:monospace;font-size:12px;color:#333;">{fmt(k['birimFiyat'])} TL</td>
          <td style="padding:11px 14px;text-align:right;font-family:monospace;font-size:12px;color:#0f3460;font-weight:600;">{fmt(k['toplamTutar'])} TL</td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html lang="tr">
<head><meta charset="UTF-8">
<style>
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ font-family: Arial, sans-serif; background:#fff; color:#111; }}
  @page {{ size: A4; margin: 10mm; }}
</style>
</head>
<body>
<div style="background:#fff;width:100%;font-family:Arial,sans-serif;">

  <!-- Üst bant -->
  <div style="height:8px;background:linear-gradient(90deg,#1a1a2e,#0f3460 60%,#533483);margin-bottom:0;"></div>

  <div style="padding:32px 40px 36px;">

    <!-- Header -->
    <table style="width:100%;margin-bottom:28px;padding-bottom:20px;border-bottom:1px solid #e0e0e0;">
      <tr>
        <td style="vertical-align:top;">
          <div style="font-size:15px;font-weight:700;color:#0f3460;margin-bottom:6px;">{S['unvan']}</div>
          <div style="font-size:11px;color:#666;line-height:1.8;font-family:monospace;">{S['adres']}<br>{S['vd']} · VKN: {S['vkn']}</div>
        </td>
        <td style="text-align:right;vertical-align:top;white-space:nowrap;padding-left:20px;">
          <div style="font-size:20px;font-weight:700;letter-spacing:4px;color:#0f3460;font-family:monospace;margin-bottom:8px;">PROFORMA FATURA</div>
          <div style="display:inline-block;background:#f5f0e8;border:1px solid #d4b896;padding:4px 12px;font-family:monospace;font-size:11px;color:#8a6a3a;">TARİH: {tarih}</div>
        </td>
      </tr>
    </table>

    <!-- Alıcı -->
    <div style="margin-bottom:28px;">
      <div style="font-size:8px;letter-spacing:3px;color:#999;font-family:monospace;margin-bottom:8px;">SAYIN</div>
      <div style="border:1px solid #e0e0e0;border-left:4px solid #0f3460;padding:16px 20px;background:#f9f9fb;">
        <div style="font-size:13px;font-weight:700;color:#111;margin-bottom:4px;">{A['unvan']}</div>
        <div style="font-size:11px;color:#666;line-height:1.7;">{A['adres']}</div>
        <div style="font-family:monospace;font-size:10px;color:#888;margin-top:4px;">{A['vd']} · VKN: {A['vkn']}</div>
      </div>
    </div>

    <!-- Tablo -->
    <table style="width:100%;border-collapse:collapse;margin-bottom:0;">
      <thead>
        <tr style="background:#0f3460;">
          <th style="padding:11px 14px;text-align:left;font-family:monospace;font-size:9px;letter-spacing:1.5px;font-weight:500;color:rgba(255,255,255,0.85);">#</th>
          <th style="padding:11px 14px;text-align:left;font-family:monospace;font-size:9px;letter-spacing:1.5px;font-weight:500;color:rgba(255,255,255,0.85);">ÜRÜN ADI</th>
          <th style="padding:11px 14px;text-align:right;font-family:monospace;font-size:9px;letter-spacing:1.5px;font-weight:500;color:rgba(255,255,255,0.85);">MİKTAR</th>
          <th style="padding:11px 14px;text-align:right;font-family:monospace;font-size:9px;letter-spacing:1.5px;font-weight:500;color:rgba(255,255,255,0.85);">BİRİM FİYAT</th>
          <th style="padding:11px 14px;text-align:right;font-family:monospace;font-size:9px;letter-spacing:1.5px;font-weight:500;color:rgba(255,255,255,0.85);">TOPLAM</th>
        </tr>
      </thead>
      <tbody style="border-bottom:2px solid #e0e0e0;">
        {rows}
      </tbody>
    </table>

    <!-- Alt bölüm: koşullar + toplamlar -->
    <table style="width:100%;margin-top:20px;">
      <tr>
        <td style="vertical-align:top;padding-right:20px;">
          <table style="width:100%;">
            <tr><td style="padding:5px 0;font-size:11px;color:#666;"><b style="color:#333;">TESLİMAT:</b> Nakliye satıcıya aittir.</td></tr>
            <tr><td style="padding:5px 0;font-size:11px;color:#666;"><b style="color:#333;">ÖDEME:</b> Banka yolu ile EFT/Havale</td></tr>
            <tr><td style="padding:5px 0;font-size:11px;color:#666;"><b style="color:#333;">FİYAT:</b> TL olarak verilmiştir.</td></tr>
            <tr><td style="padding:5px 0;font-size:11px;color:#666;"><b style="color:#333;">GEÇERLİLİK:</b> 5 gündür.</td></tr>
          </table>
        </td>
        <td style="vertical-align:top;width:280px;">
          <table style="width:100%;border-collapse:collapse;">
            <tr style="border-bottom:1px solid #f0f0f0;">
              <td style="padding:9px 14px;background:#f7f7f7;font-family:monospace;font-size:10px;color:#777;">TOPLAM</td>
              <td style="padding:9px 14px;text-align:right;font-family:monospace;font-size:11px;font-weight:500;color:#333;">{fmt(toplam)} TL</td>
            </tr>
            <tr style="border-bottom:1px solid #f0f0f0;">
              <td style="padding:9px 14px;background:#f7f7f7;font-family:monospace;font-size:10px;color:#777;">KDV %1</td>
              <td style="padding:9px 14px;text-align:right;font-family:monospace;font-size:11px;font-weight:500;color:#333;">KDV DAHİL</td>
            </tr>
            <tr>
              <td style="padding:11px 14px;background:#0f3460;font-family:monospace;font-size:11px;color:rgba(255,255,255,0.8);font-weight:600;">GENEL TOPLAM</td>
              <td style="padding:11px 14px;text-align:right;background:#0f3460;font-family:monospace;font-size:14px;font-weight:700;color:#f0c060;">{fmt(toplam)} TL</td>
            </tr>
          </table>
        </td>
      </tr>
    </table>

    <!-- Banka -->
    <div style="margin-top:20px;background:#f5f0e8;border:1px solid #e0d0b0;padding:14px 20px;">
      <span style="font-family:monospace;font-size:8px;letter-spacing:2.5px;color:#9a7a4a;margin-right:16px;">BANKA HESAP BİLGİLERİ</span>
      <span style="font-size:12px;margin-right:16px;"><b style="color:#5a3a10;font-size:11px;">BANKA:</b> <span style="font-family:monospace;font-size:11px;color:#333;">{S['banka']}</span></span>
      <span style="font-size:12px;"><b style="color:#5a3a10;font-size:11px;">IBAN:</b> <span style="font-family:monospace;font-size:11.5px;color:#333;letter-spacing:1px;">{S['iban']}</span></span>
    </div>

    <!-- İmza -->
    <table style="width:100%;margin-top:32px;padding-top:16px;border-top:1px dashed #ddd;">
      <tr>
        <td style="width:160px;text-align:center;">
          <div style="border-bottom:1px solid #ccc;height:44px;margin-bottom:8px;"></div>
          <div style="font-size:9px;color:#aaa;font-family:monospace;letter-spacing:1.5px;">DÜZENLEYEN / İMZA</div>
        </td>
        <td style="text-align:center;font-family:monospace;font-size:9px;color:#ccc;">
          {S['unvan']}<br>{tarih}
        </td>
        <td style="width:160px;text-align:center;">
          <div style="border-bottom:1px solid #ccc;height:44px;margin-bottom:8px;"></div>
          <div style="font-size:9px;color:#aaa;font-family:monospace;letter-spacing:1.5px;">KAŞE / İMZA</div>
        </td>
      </tr>
    </table>

  </div>

  <!-- Alt bant -->
  <div style="height:5px;background:linear-gradient(90deg,#533483,#0f3460 40%,#1a1a2e);"></div>

</div>
</body>
</html>"""

def html_to_pdf(html_content):
    pdf_bytes = WeasyHTML(string=html_content).write_pdf()
    return pdf_bytes

def parse_mesaj(metin):
    metin_upper = metin.upper().strip()
    tutar_match = re.search(r'\d[\d.,]*\d|\d', metin_upper.replace(" ", ""))
    if not tutar_match:
        return None, None, None
    tutar_str = tutar_match.group().replace(".", "").replace(",", "")
    try:
        tutar = int(tutar_str)
    except:
        return None, None, None

    firma_bul = []
    for alias, key in FIRMA_ALIAS.items():
        if alias in metin_upper:
            idx = metin_upper.index(alias)
            firma_bul.append((idx, key))
    firma_bul.sort(key=lambda x: x[0])
    seen, firma_keys = [], []
    for _, k in firma_bul:
        if k not in seen:
            seen.append(k)
            firma_keys.append(k)

    if len(firma_keys) < 2:
        return None, None, None
    return firma_keys[0], firma_keys[1], tutar

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 *Proforma Fatura Botu*\n\n"
        "Kullanım:\n`ertek ulteda 4350000`\n`özertek karakoç 2500000`\n\n"
        "*Firmalar:* ERTEK · ULTEDA · ÖZERTEK · KARAKOÇ · ALBAYRAK",
        parse_mode="Markdown"
    )

async def firmalar_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    metin = "📋 *Kayıtlı Firmalar:*\n\n"
    for key, f in FIRMALAR.items():
        metin += f"*{key}*\n{f['unvan']}\n`{f['iban']}`\n\n"
    await update.message.reply_text(metin, parse_mode="Markdown")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    metin = update.message.text or ""
    satici_key, alici_key, tutar = parse_mesaj(metin)

    if not satici_key or not alici_key or not tutar:
        await update.message.reply_text(
            "❓ Anlamadım. Şöyle yaz:\n\n`ertek ulteda 4350000`", parse_mode="Markdown")
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
        f"💰 *Tutar:* {fmt(tutar)} TL",
        parse_mode="Markdown"
    )

    try:
        html = html_olustur(satici_key, alici_key, tutar)
        pdf_bytes = html_to_pdf(html)
        tarih = datetime.now().strftime("%d%m%Y")
        dosya_adi = f"Proforma_{satici_key}_{alici_key}_{tarih}.pdf"
        await update.message.reply_document(
            document=pdf_bytes,
            filename=dosya_adi,
            caption=f"✅ {S['unvan']} → {A['unvan']}\n{fmt(tutar)} TL"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Hata: {str(e)}")

def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN ayarlı değil!")
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("firmalar", firmalar_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("✅ Bot başlatıldı...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
