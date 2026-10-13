# XenonOS — Debian 13 (trixie) + KDE Plasma

Ubuntu tabanından bağımsız, Debian paketleriyle kurulan XenonOS.

## Yapı
| Yol | Ne |
|---|---|
| `build-debs.sh` | `xenonium`, `xenonpad`, `xenonwriter`, `xenonos-defaults` `.deb` paketlerini üretir (internet gerektirmez) |
| `packages/` | Üretilen `.deb` dosyaları |
| `live-build/` | Debian `live-build` yapılandırması (paket listesi, kancalar, marka) |
| `build-iso.sh` | Araçları kurar, ISO'yu üretir (**indirme yapar**) |

## Sıra
1. `sudo bash build-debs.sh`  → paketler (indirme yok)
2. `sudo bash build-iso.sh`   → araç kurulumu + Debian paketleri indirme + ISO (≈ 1.5–3 GB indirme, 20–60 dk)
3. `out/xenonos-*.iso` dosyasını VirtualBox'ta aç.

## Kendi paket deposunu yayınlamak (sonraki adım)
`packages/*.deb` dosyalarını `reprepro` veya `aptly` ile bir apt deposuna koy, GPG ile imzala,
`config/archives/xenonos.list.chroot` içine depo adresini yaz. Böylece güncellemeler `apt upgrade` ile gelir.

## Bilinen eksikler (henüz test edilmedi)
- Plasma görev çubuğu favorileri (Xenonium/XenonPad/XenonWriter sabitleme) ayarlanmadı.
- Calamares marka metinleri `sed` ile değiştiriliyor; ekran görüntüsüyle doğrulanmalı.
- Paket adları Debian 13'e göre yazıldı; `apt` bulamazsa `lb build` hata verir, düzeltilir.
