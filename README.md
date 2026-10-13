# XenonOS

## İndir

**[xenonos-amd64.hybrid.iso (v1.0, Debian tabanlı, 1,7 GB)](https://github.com/Camamaka/XenonOS/releases/download/v1.0/xenonos-amd64.hybrid.iso)** · [Release sayfası](https://github.com/Camamaka/XenonOS/releases/tag/v1.0)

SHA256: `3C117B0AF647DC9D34FA0D21BBDF21423043C90BC0217CAE4471455D6B8A517E`

USB'ye [Ventoy](https://www.ventoy.net) ile kopyalayarak veya `dd` ile yazarak kullanabilirsiniz.

## Hakkında

Ubuntu 26.04 masaüstü ISO'sunun üstüne kurulan XenonOS. İçindekiler:

| Klasör | Ne var |
|---|---|
| `apps/xenonium` | Xenonium web tarayıcısı (GTK3 + WebKitGTK) ve eklentiler |
| `apps/xenonium/extensions/xenontranslate` | XenonTranslate eklentisi |
| `apps/xenonpad` | XenonPad metin düzenleyici (GTK4 + libadwaita) |
| `apps/xenonwriter` | XenonWriter kelime işlemci (GTK3 + WebKit, HTML/PDF) |
| `iso` | ISO üreten betikler (`build-desktop.sh`) |

## ISO üretmek (Windows + WSL)
1. WSL'de Ubuntu kurulu olmalı. Kaynak ISO `E:\ubuntu-26.04-desktop-amd64.iso` (WSL'de `mount -t drvfs E: /mnt/e`).
2. `build-desktop.sh`'i WSL'de root olarak çalıştır. Çıktı: `D:\XenonOS\XenonOS-Desktop.iso`.
   - Sadece değişen katmanı yeniden yapmak için: `SKIP_BASE=1 SKIP_STD=1 bash build-desktop.sh`
3. Uygulama kaynakları `apps/` klasöründen alınır.

## Xenonium kısayolları
Ctrl+T yeni sekme · Ctrl+W kapat · Ctrl+Shift+T kapatılanı aç · Ctrl+L adres · Ctrl+F bul · Ctrl+D yer imi ·
Ctrl+H geçmiş · Ctrl+J indirmeler · Ctrl+N pencere · Ctrl+Shift+N gizli pencere · F12 geliştirici araçları ·
Alt+T (sayfada) XenonTranslate paneli.

## Kendi Xenonium eklentini yazmak
`~/.local/share/xenonium/extensions/<ad>/manifest.json` + betikler. API ve örnek: `extensions.py` başındaki açıklama,
`extensions/xenontranslate/` örnek eklenti. Adres sayfası: `xenon://extensions`.

## XenonTranslate
Seçili metni çevirir (seçince beliren 文 düğmesi), tüm sayfayı çevirir / orijinale döndürür, sayfa dilini algılar.
Çeviri servisi: `translate.googleapis.com` (anahtarsız, resmî olmayan uç nokta) ve yedek olarak MyMemory.
Servis erişimi değişirse `content.js` içindeki `gtx()` fonksiyonu değiştirilir.
