# Proforma Fatura Telegram Botu

## Kullanım
Bota şu formatta yaz:
```
ertek ulteda 4350000
özertek karakoç 2500000
albayrak ertek 1750000
```

Bot PDF olarak proforma faturayı gönderir.

## Komutlar
- `/start` — Yardım mesajı
- `/firmalar` — Kayıtlı firma listesi

## Railway'e Deploy

### 1. GitHub'a yükle
```bash
git init
git add .
git commit -m "init"
git remote add origin https://github.com/KULLANICI/proforma-bot.git
git push -u origin main
```

### 2. Railway.app
1. https://railway.app → GitHub ile giriş
2. "New Project" → "Deploy from GitHub repo"
3. Bu repo'yu seç
4. "Variables" sekmesine git:
   - `BOT_TOKEN` = BotFather'dan aldığın token
5. Deploy!

## Firmalar
- ERTEK — Ertek Tavukçuluk
- ULTEDA — Albayraklar Ulteda
- ÖZERTEK — Öz Ertek Gıda
- KARAKOÇ — Salih Karakoç Tavukçuluk
- ALBAYRAK — Albayraklar Sos. Hiz.
