# XenonOS

## İndir

**[xenonos-amd64.hybrid.iso (v1.0, Debian tabanlı, 1,7 GB)](https://github.com/Camamaka/XenonOS/releases/download/v1.0/xenonos-amd64.hybrid.iso)** · [Release sayfası](https://github.com/Camamaka/XenonOS/releases/tag/v1.0)

SHA256: `3C117B0AF647DC9D34FA0D21BBDF21423043C90BC0217CAE4471455D6B8A517E`

USB'ye [Ventoy](https://www.ventoy.net) ile kopyalayarak veya `dd` ile yazarak kullanabilirsiniz.

## Hakkında

XenonOS, Debian 13 (trixie) ve KDE Plasma üzerine kurulu, kendi uygulamalarıyla gelen bir Linux dağıtımıdır.
ISO, Debian'ın `live-build` aracıyla üretilir ve kurulum için Calamares kullanır. İçindekiler:

| Klasör | Ne var |
|---|---|
| `debian` | Debian tabanlı ISO'yu üreten betikler, `live-build` yapılandırması ve `.deb` paketleri (ana sürüm) |
| `apps/xenonium` | Xenonium web tarayıcısı (GTK3 + WebKitGTK) ve eklentiler |
| `apps/xenonium/extensions/xenontranslate` | XenonTranslate eklentisi |
| `apps/xenonpad` | XenonPad metin düzenleyici (GTK4 + libadwaita) |
| `apps/xenonwriter` | XenonWriter kelime işlemci (GTK3 + WebKit, HTML/PDF) |
| `xenonchat` | XenonChat sohbet uygulaması (Electron + Vite) |
| `iso` | Eski, Ubuntu 26.04 tabanlı ISO betikleri (`build-desktop.sh`) |
| `harness` | Uygulamaları WSL'de chroot ile Windows masaüstünde görsel olarak test eden yardımcı betikler |

## ISO üretmek (Windows + WSL)
Ayrıntılar: [`debian/README.md`](debian/README.md). Özet, WSL'de (Debian/Ubuntu) root olarak:

```bash
cd debian
sudo bash build-debs.sh   # Xenonium, XenonPad, XenonWriter ve xenonos-defaults .deb paketlerini üretir
sudo bash build-iso.sh    # araçları kurar, Debian paketlerini indirir, ISO'yu üretir
```

- `build-iso.sh` internetten yaklaşık 1,5–3 GB paket indirir ve 20–60 dakika sürer.
- Çıktı: `debian/out/xenonos-*.iso` ve `debian/out/SHA256SUMS`.
- Uygulama kaynakları `apps/` klasöründen alınır.

### Eski Ubuntu tabanlı sürüm
`iso/build-desktop.sh`, Ubuntu 26.04 masaüstü ISO'sunun üstüne XenonOS'u kurar (kaynak ISO'yu WSL'de `mount -t drvfs E: /mnt/e` ile bağlayıp
betiği root olarak çalıştırın; çıktı `XenonOS-Desktop.iso`). Bu yol artık ana sürüm değildir.

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
