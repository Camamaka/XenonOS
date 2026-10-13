#!/bin/bash
# XenonOS desktop ISO v2 (run as root in WSL)
# Base layer: branding, app names, Firefox, theme.  Live layer: installer.
set -euo pipefail

SRC_ISO="${SRC_ISO:-/mnt/e/ubuntu-26.04-desktop-amd64.iso}"
HERE="$(cd "$(dirname "$0")" && pwd)"
W=/root/work
OUT="${OUT:-/mnt/d/XenonOS/XenonOS-Desktop.iso}"

# source ISO (if it is on the Ventoy USB at E:, it may need to be mounted manually in WSL)
case "$SRC_ISO" in
    /mnt/e/*) mkdir -p /mnt/e; mountpoint -q /mnt/e || mount -t drvfs E: /mnt/e 2>/dev/null || true ;;
esac
if [ ! -f "$SRC_ISO" ]; then
    echo "ERROR: source ISO not found: $SRC_ISO  (is the USB plugged in? In WSL: mount -t drvfs E: /mnt/e)" >&2
    exit 1
fi

apt-get install -y squashfs-tools xorriso librsvg2-bin fonts-dejavu-core dconf-cli python3 >/dev/null
mkdir -p "$W"; cd "$W"

# SAFETY: if folders were bind-mounted into the chroot for testing, unmount them first; otherwise 'rm -rf rootfs'
# also deletes the REAL contents of the mounted folders (app sources, /dev, /mnt/wslg ...).
for m in $(awk -v p="$W/rootfs/" 'index($2, p) == 1 { print $2 }' /proc/mounts | sort -r); do
    umount -l "$m" 2>/dev/null || true
done
if awk -v p="$W/rootfs/" 'index($2, p) == 1 { f = 1 } END { exit !f }' /proc/mounts; then
    echo "ERROR: there are still mounted folders under $W/rootfs, stopping the build" >&2
    exit 1
fi

# ---------------------------------------------------------------- helpers
# In a .desktop file only the top-level Name= is changed (Name[xx]= translation lines are removed,
# [Desktop Action ...] sections are left untouched)
rename_desktop() {   # $1=file  $2=new name  $3=(optional) new description
    local f="$1" n="$2" c="${3:-}"
    [ -f "$f" ] || return 0
    awk -v n="$n" -v c="$c" '
        /^\[Desktop Action/ { act=1 }
        !act && /^Name(\[[^]]*\])?=/ { if ($0 ~ /^Name=/) print "Name=" n; next }
        !act && c != "" && /^Comment(\[[^]]*\])?=/ { if ($0 ~ /^Comment=/) print "Comment=" c; next }
        { print }' "$f" > "$f.tmp" && cat "$f.tmp" > "$f" && rm -f "$f.tmp"
}

# ---------------------------------------------------------------- logos
rm -rf assets && python3 "$HERE/gen_assets.py" assets

# ================================================================ BASE LAYER
if [ "${SKIP_BASE:-0}" = 1 ] && [ -f minimal.xenon.squashfs ]; then
echo ">> Base layer skipped (SKIP_BASE=1, using the existing file)"
else
[ -f minimal.squashfs ] || xorriso -osirrox on -indev "$SRC_ISO" -extract /casper/minimal.squashfs minimal.squashfs
echo ">> Unpacking base layer..."
rm -rf rootfs
unsquashfs -f -d rootfs minimal.squashfs >/dev/null
R=rootfs

echo ">> Wallpaper..."
cat > wall.svg <<'EOF'
<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080" viewBox="0 0 1920 1080">
  <defs>
    <radialGradient id="g" cx="50%" cy="45%" r="75%"><stop offset="0" stop-color="#0d2b3e"/><stop offset="1" stop-color="#05070d"/></radialGradient>
    <linearGradient id="l" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#00e5ff"/><stop offset="1" stop-color="#7c4dff"/></linearGradient>
  </defs>
  <rect width="1920" height="1080" fill="url(#g)"/>
  <g fill="none" stroke="url(#l)" stroke-width="3" opacity="0.9">
    <polygon points="960,250 1100,330 1100,490 960,570 820,490 820,330"/>
    <polygon points="960,290 1065,350 1065,470 960,530 855,470 855,350" opacity="0.5"/>
  </g>
  <g fill="none" stroke="#00e5ff" stroke-width="1.5" opacity="0.12">
    <polygon points="300,200 380,246 380,338 300,384 220,338 220,246"/>
    <polygon points="1620,700 1700,746 1700,838 1620,884 1540,838 1540,746"/>
    <polygon points="1500,150 1560,185 1560,255 1500,290 1440,255 1440,185"/>
    <polygon points="420,760 480,795 480,865 420,900 360,865 360,795"/>
  </g>
  <text x="960" y="700" text-anchor="middle" font-family="DejaVu Sans, sans-serif" font-size="96" font-weight="bold" letter-spacing="14" fill="#e6faff">XENONOS</text>
  <text x="960" y="760" text-anchor="middle" font-family="DejaVu Sans, sans-serif" font-size="28" letter-spacing="6" fill="#00e5ff" opacity="0.8">Ubuntu 26.04 tabanli</text>
</svg>
EOF
rsvg-convert -w 1920 -h 1080 wall.svg -o wall.png
B=$R/usr/share/backgrounds; mkdir -p "$B"
for f in warty-final-ubuntu.png ubuntu-wallpaper-d.png; do rm -f "$B/$f"; cp wall.png "$B/$f"; done
cp wall.png "$B/xenonos.png"

echo ">> Version name / GRUB / logo..."
sed -i 's|^PRETTY_NAME=.*|PRETTY_NAME="XenonOS 1.0 (Ubuntu 26.04 LTS)"|' $R/usr/lib/os-release
sed -i 's|^NAME=.*|NAME="XenonOS"|' $R/usr/lib/os-release   # ID/ID_LIKE stay the same (apt, snap, pro)
echo 'XENONOS_VERSION="1.0"' >> $R/usr/lib/os-release
# Replace Ubuntu logos and icons with XenonOS ones (installer icon, app grid button, about logo)
find $R/usr/share/icons $R/usr/share/pixmaps -type f \( -iname '*ubiquity*' -o -iname 'ubuntu-logo*' -o -iname 'view-app-grid-ubuntu*' -o -iname 'start-here*' \) 2>/dev/null | while read -r f; do
    b=$(basename "$f")
    case "$f" in
        *-symbolic.svg) cp assets/symbolic.svg "$f" ;;
        *.svg) case "$b" in *dark*) cp assets/logo-dark.svg "$f" ;; *text*) cp assets/logo-light.svg "$f" ;; *) cp assets/icon.svg "$f" ;; esac ;;
        *.png) dims=$(python3 -c "import struct,sys; d=open(sys.argv[1],'rb').read(32); print(*struct.unpack('>II', d[16:24]))" "$f")
               set -- $dims
               case "$b" in *dark*) s=assets/logo-dark.svg ;; *text*) s=assets/logo-light.svg ;; *) s=assets/icon.svg ;; esac
               rsvg-convert -w "$1" -h "$2" --keep-aspect-ratio "$s" -o "$f" || true ;;
    esac
done
printf 'XenonOS 1.0 \\n \\l\n\n' > $R/etc/issue
echo 'XenonOS 1.0 (Ubuntu 26.04 LTS)' > $R/etc/issue.net
sed -i 's|^GRUB_DISTRIBUTOR=.*|GRUB_DISTRIBUTOR="XenonOS"|' $R/etc/default/grub
mkdir -p $R/usr/share/xenonos
cp assets/*.svg $R/usr/share/xenonos/
# Plymouth (the installed system's initramfs is generated from these)
for f in $(find $R/usr/share/plymouth -type f \( -iname '*watermark*' -o -iname '*ubuntu-logo*' \) 2>/dev/null); do
    dims=$(python3 -c "import struct,sys; d=open(sys.argv[1],'rb').read(32); print(*struct.unpack('>II', d[16:24]))" "$f")
    set -- $dims
    rsvg-convert -w "$1" -h "$2" --keep-aspect-ratio assets/logo-dark.svg -o "$f" || true
done

echo ">> Installing XenonPad / XenonWriter / Xenonium..."
APPS_SRC="$(cd "$HERE/.." && pwd)/apps"
L=$R/usr/lib/xenonos
mkdir -p $L $R/usr/bin $R/usr/share/applications $R/usr/share/icons/hicolor/scalable/apps
for app in xenonium xenonpad xenonwriter; do
    rm -rf "$L/$app"; cp -r "$APPS_SRC/$app" "$L/$app"
    find "$L/$app" -name '__pycache__' -prune -exec rm -rf {} +
    cp "assets/$app.svg" "$R/usr/share/icons/hicolor/scalable/apps/$app.svg"
done
for app in xenonium:browser.py xenonpad:xenonpad.py xenonwriter:xenonwriter.py; do
    name=${app%%:*}; file=${app##*:}
    printf '#!/bin/sh\nexec python3 /usr/lib/xenonos/%s/%s "$@"\n' "$name" "$file" > "$R/usr/bin/$name"
    chmod 755 "$R/usr/bin/$name"
done
cat > $R/usr/share/applications/org.xenonos.Xenonium.desktop <<'EOF'
[Desktop Entry]
Type=Application
Name=Xenonium
GenericName=Web Tarayicisi
Comment=XenonOS web tarayicisi (XenonTranslate dahil)
Exec=xenonium %U
Icon=xenonium
Terminal=false
Categories=Network;WebBrowser;
MimeType=text/html;application/xhtml+xml;x-scheme-handler/http;x-scheme-handler/https;
StartupWMClass=xenonium
StartupNotify=true
Keywords=web;internet;tarayici;browser;
Actions=new-window;private-window;

[Desktop Action new-window]
Name=Yeni pencere
Exec=xenonium

[Desktop Action private-window]
Name=Yeni gizli pencere
Exec=xenonium --private
EOF
cat > $R/usr/share/applications/org.xenonos.XenonPad.desktop <<'EOF'
[Desktop Entry]
Type=Application
Name=XenonPad
GenericName=Metin Duzenleyici
Comment=XenonOS metin duzenleyicisi
Exec=xenonpad %F
Icon=xenonpad
Terminal=false
Categories=Utility;TextEditor;GTK;
MimeType=text/plain;text/markdown;text/x-python;text/x-csrc;application/x-shellscript;application/json;application/xml;
StartupNotify=true
Keywords=metin;not;editor;text;
EOF
cat > $R/usr/share/applications/org.xenonos.XenonWriter.desktop <<'EOF'
[Desktop Entry]
Type=Application
Name=XenonWriter
GenericName=Kelime Islemci
Comment=XenonOS kelime islemcisi
Exec=xenonwriter %F
Icon=xenonwriter
Terminal=false
Categories=Office;WordProcessor;GTK;
MimeType=text/html;
StartupWMClass=xenonwriter
StartupNotify=true
Keywords=yazi;belge;word;writer;kelime;
EOF
# default browser / text editor
mkdir -p $R/etc/xdg $R/etc/alternatives
for alt in x-www-browser gnome-www-browser www-browser; do
    ln -sfn /usr/bin/xenonium "$R/etc/alternatives/$alt"
    ln -sfn "/etc/alternatives/$alt" "$R/usr/bin/$alt"
done
python3 - "$R" <<'PY'
import sys, os, configparser
root = sys.argv[1]
defaults = {
    "x-scheme-handler/http": "org.xenonos.Xenonium.desktop", "x-scheme-handler/https": "org.xenonos.Xenonium.desktop",
    "text/html": "org.xenonos.Xenonium.desktop", "application/xhtml+xml": "org.xenonos.Xenonium.desktop",
    "text/plain": "org.xenonos.XenonPad.desktop", "text/markdown": "org.xenonos.XenonPad.desktop",
}
for fn in ("mimeapps.list", "ubuntu-mimeapps.list", "gnome-mimeapps.list"):
    p = os.path.join(root, "etc/xdg", fn)
    cp = configparser.RawConfigParser(strict=False, delimiters=("=",))
    cp.optionxform = str
    if os.path.exists(p):
        cp.read(p, encoding="utf-8")
    if not cp.has_section("Default Applications"):
        cp.add_section("Default Applications")
    for k, v in defaults.items():
        cp.set("Default Applications", k, v + ";")
    with open(p, "w", encoding="utf-8") as f:
        cp.write(f, space_around_delimiters=False)
PY

echo ">> Application names..."
A=$R/usr/share/applications
rename_desktop $A/org.gnome.Nautilus.desktop         "Xenon Dosyalar"      "XenonOS dosya yoneticisi"
rename_desktop $A/org.gnome.Ptyxis.desktop           "Xenon Terminal"      "XenonOS terminali"
rename_desktop $A/org.gnome.Settings.desktop         "Xenon Ayarlar"       "XenonOS sistem ayarlari"
rename_desktop $A/org.gnome.Calculator.desktop       "Xenon Hesap"         "XenonOS hesap makinesi"
rename_desktop $A/org.gnome.clocks.desktop           "Xenon Saat"          "XenonOS saat ve alarm"
rename_desktop $A/org.gnome.Loupe.desktop            "Xenon Resim"         "XenonOS resim gorunturleyici"
rename_desktop $A/org.gnome.Papers.desktop           "Xenon Belge"         "XenonOS belge gorunturleyici"
rename_desktop $A/org.gnome.baobab.desktop           "Xenon Disk Analizi"  "XenonOS disk kullanim analizi"
rename_desktop $A/org.gnome.DiskUtility.desktop      "Xenon Diskler"       "XenonOS disk yoneticisi"
rename_desktop $A/org.gnome.Characters.desktop       "Xenon Karakterler"
rename_desktop $A/org.gnome.Logs.desktop             "Xenon Gunluk"
rename_desktop $A/org.gnome.Yelp.desktop             "Xenon Yardim"        "XenonOS yardim"
rename_desktop $A/net.nokyan.Resources.desktop       "Xenon Monitor"       "XenonOS sistem monitoru"
rename_desktop $A/org.gnome.font-viewer.desktop      "Xenon Yazi Tipleri"
rename_desktop $A/org.gnome.Extensions.desktop       "Xenon Eklentiler"
rename_desktop $A/nm-connection-editor.desktop       "Xenon Ag Duzenleyici"
rename_desktop $A/update-manager.desktop             "Xenon Guncelleme"    "XenonOS yazilim guncelleyici"
rename_desktop $A/gnome-language-selector.desktop    "Xenon Dil Destegi"

echo ">> Theme (dconf)..."
mkdir -p $R/etc/dconf/profile $R/etc/dconf/db/xenon.d
if [ -f $R/etc/dconf/profile/user ]; then
    grep -q 'system-db:xenon' $R/etc/dconf/profile/user || sed -i '0,/^user-db:user/s//user-db:user\nsystem-db:xenon/' $R/etc/dconf/profile/user
else
    printf 'user-db:user\nsystem-db:xenon\n' > $R/etc/dconf/profile/user
fi
grep -q 'system-db:xenon' $R/etc/dconf/profile/user || echo 'system-db:xenon' >> $R/etc/dconf/profile/user
cat > $R/etc/dconf/db/xenon.d/00-xenonos <<'EOF'
[org/gnome/desktop/interface]
color-scheme='prefer-dark'
accent-color='teal'

[org/gnome/shell]
favorite-apps=['org.xenonos.Xenonium.desktop', 'org.gnome.Nautilus.desktop', 'org.xenonos.XenonPad.desktop', 'org.xenonos.XenonWriter.desktop', 'org.gnome.Ptyxis.desktop', 'org.gnome.Settings.desktop']
EOF
dconf compile $R/etc/dconf/db/xenon $R/etc/dconf/db/xenon.d

echo ">> Firefox settings..."
cat > home.html <<'EOF'
<!doctype html><html lang="tr"><head><meta charset="utf-8"><title>Xenonium</title>
<style>
body{margin:0;min-height:100vh;display:flex;flex-direction:column;align-items:center;justify-content:center;
background:radial-gradient(ellipse at 50% 40%,#0d2b3e,#05070d);font-family:sans-serif;color:#e6faff}
h1{font-size:64px;letter-spacing:12px;margin:0 0 6px;color:#00e5ff}
p{margin:0 0 36px;opacity:.7;letter-spacing:3px}
form{width:min(560px,86vw)}
input{width:100%;box-sizing:border-box;padding:16px 22px;border-radius:30px;border:2px solid #00e5ff;background:#0a1a26;color:#e6faff;font-size:18px;outline:none}
.l{margin-top:34px;display:flex;gap:14px;flex-wrap:wrap;justify-content:center}
a{color:#00e5ff;text-decoration:none;border:1px solid #1d4b63;border-radius:20px;padding:8px 18px}
a:hover{background:#12354a}
</style></head><body>
<h1>XENONIUM</h1><p>XenonOS web tarayicisi</p>
<form action="https://duckduckgo.com/" method="get"><input name="q" placeholder="Ara veya adres yaz..." autofocus></form>
<div class="l"><a href="https://tr.wikipedia.org">Vikipedi</a><a href="https://help.ubuntu.com">Ubuntu Yardim</a><a href="https://github.com">GitHub</a><a href="https://www.youtube.com">YouTube</a></div>
</body></html>
EOF
python3 - <<'PY'
import base64, json, os
html = open('home.html', 'rb').read()
url = 'data:text/html;base64,' + base64.b64encode(html).decode()
pol = {"policies": {
    "DisableTelemetry": True, "DisablePocket": True, "DisableFirefoxStudies": True,
    "NoDefaultBookmarks": True, "DisplayBookmarksToolbar": "always",
    "OverrideFirstRunPage": "", "OverridePostUpdatePage": "",
    "UserMessaging": {"WhatsNew": False, "ExtensionRecommendations": False,
                      "FeatureRecommendations": False, "SkipOnboarding": True},
    "Homepage": {"URL": url, "Locked": False, "StartPage": "homepage"},
    "SearchEngines": {"Default": "DuckDuckGo"},
    "Bookmarks": [
        {"Title": "Vikipedi", "URL": "https://tr.wikipedia.org", "Placement": "toolbar"},
        {"Title": "Ubuntu Yardim", "URL": "https://help.ubuntu.com", "Placement": "toolbar"},
        {"Title": "GitHub", "URL": "https://github.com", "Placement": "toolbar"},
    ],
    "Preferences": {
        "browser.aboutwelcome.enabled": {"Value": False, "Status": "default"},
        "layout.css.prefers-color-scheme.content-override": {"Value": 0, "Status": "default"},
    },
}}
os.makedirs('rootfs/etc/firefox/policies', exist_ok=True)
json.dump(pol, open('rootfs/etc/firefox/policies/policies.json', 'w'), ensure_ascii=False, indent=2)
PY

echo ">> Service that renames Snap apps to Xenon..."
mkdir -p $R/usr/local/bin
cat > $R/usr/local/bin/xenon-brand <<'EOF'
#!/bin/sh
# Translates the names shown in snapd-generated .desktop files to XenonOS names (idempotent)
D=/var/lib/snapd/desktop/applications
rn() {
    f="$D/$1"; [ -f "$f" ] || return 0
    grep -q "^Name=$2\$" "$f" && return 0
    awk -v n="$2" '/^\[Desktop Action/{act=1} !act && /^Name(\[[^]]*\])?=/ { if ($0 ~ /^Name=/) print "Name=" n; next } {print}' "$f" > "$f.tmp" \
        && cat "$f.tmp" > "$f" && rm -f "$f.tmp"
}
rn snap-store_snap-store.desktop "Xenon Magaza"
rn firmware-updater_firmware-updater.desktop "Xenon Aygit Yazilimi"
rn desktop-security-center_desktop-security-center.desktop "Xenon Guvenlik"
rn ubuntu-desktop-bootstrap_ubuntu-desktop-bootstrap.desktop "XenonOS Kur"
exit 0
EOF
chmod 755 $R/usr/local/bin/xenon-brand
cat > $R/etc/systemd/system/xenon-brand.service <<'EOF'
[Unit]
Description=XenonOS uygulama adlari
After=snapd.seeded.service
[Service]
Type=oneshot
ExecStart=/usr/local/bin/xenon-brand
[Install]
WantedBy=multi-user.target
EOF
cat > $R/etc/systemd/system/xenon-brand.path <<'EOF'
[Unit]
Description=XenonOS uygulama adlarini izle
[Path]
PathChanged=/var/lib/snapd/desktop/applications
[Install]
WantedBy=multi-user.target
EOF
mkdir -p $R/etc/systemd/system/multi-user.target.wants
ln -sf /etc/systemd/system/xenon-brand.service $R/etc/systemd/system/multi-user.target.wants/xenon-brand.service
ln -sf /etc/systemd/system/xenon-brand.path    $R/etc/systemd/system/multi-user.target.wants/xenon-brand.path

mkdir -p $R/etc/skel
cat > $R/etc/skel/XenonOS-Hosgeldin.txt <<'EOF'
XenonOS'a hos geldin!

Bu sistem Ubuntu 26.04 LTS uzerine kuruludur. Tum Ubuntu paketleri
ve guncellemeleri aynen calisir:

    sudo apt update && sudo apt upgrade
EOF

echo ">> Packing base layer (xz)..."
rm -f minimal.xenon.squashfs
mksquashfs $R minimal.xenon.squashfs -comp xz -b 131072 -noappend -no-progress
fi

# ================================================================ STANDARD LAYER (LibreOffice, Calendar, Video ...)
if [ "${SKIP_STD:-0}" = 1 ] && [ -f minimal.standard.xenon.squashfs ]; then
echo ">> Standard layer skipped (SKIP_STD=1)"
else
echo ">> Unpacking standard layer..."
[ -f standard.squashfs ] || xorriso -osirrox on -indev "$SRC_ISO" -extract /casper/minimal.standard.squashfs standard.squashfs
rm -rf stdfs; unsquashfs -f -d stdfs standard.squashfs >/dev/null
SA=stdfs/usr/share/applications
rename_desktop $SA/libreoffice-writer.desktop      "Xenon Ofis Writer"     "LibreOffice tabanli kelime islemci"
rename_desktop $SA/libreoffice-calc.desktop        "Xenon Ofis Calc"       "LibreOffice tabanli hesap tablosu"
rename_desktop $SA/libreoffice-impress.desktop     "Xenon Ofis Impress"    "LibreOffice tabanli sunum"
rename_desktop $SA/libreoffice-draw.desktop        "Xenon Ofis Draw"       "LibreOffice tabanli cizim"
rename_desktop $SA/libreoffice-math.desktop        "Xenon Ofis Math"       "LibreOffice tabanli formul editoru"
rename_desktop $SA/libreoffice-startcenter.desktop "Xenon Ofis"            "LibreOffice ofis paketi"
rename_desktop $SA/org.gnome.Calendar.desktop      "Xenon Takvim"
rename_desktop $SA/org.gnome.DejaDup.desktop       "Xenon Yedek"
rename_desktop $SA/org.gnome.FileRoller.desktop    "Xenon Arsiv"
rename_desktop $SA/org.gnome.Rhythmbox3.desktop    "Xenon Muzik"
rename_desktop $SA/org.gnome.Shotwell.desktop      "Xenon Fotograf"
rename_desktop $SA/org.gnome.Showtime.desktop      "Xenon Video"
rename_desktop $SA/org.gnome.Snapshot.desktop      "Xenon Kamera"
rename_desktop $SA/org.remmina.Remmina.desktop     "Xenon Uzak Masaustu"
rename_desktop $SA/simple-scan.desktop             "Xenon Tarayici"
rename_desktop $SA/transmission-gtk.desktop        "Xenon Indirici"
rename_desktop $SA/usb-creator-gtk.desktop         "Xenon USB Olusturucu"
rename_desktop $SA/thunderbird.desktop             "Xenonmail"             "XenonOS e-posta"
echo ">> Packing standard layer..."
rm -f minimal.standard.xenon.squashfs
mksquashfs stdfs minimal.standard.xenon.squashfs -comp xz -b 131072 -noappend -no-progress
fi

# ================================================================ LIVE LAYER (installer)
echo ">> Unpacking live layer..."
[ -f live.squashfs ] || xorriso -osirrox on -indev "$SRC_ISO" -extract /casper/minimal.standard.live.squashfs live.squashfs
rm -rf livefs; unsquashfs -f -d livefs live.squashfs >/dev/null
SNAP_REL=$(ls livefs/var/lib/snapd/seed/snaps/ | grep '^ubuntu-desktop-bootstrap_.*\.snap$' | head -1)
echo "   installer snap: $SNAP_REL"
rm -rf inst; unsquashfs -d inst "livefs/var/lib/snapd/seed/snaps/$SNAP_REL" >/dev/null
FA=inst/bin/data/flutter_assets
for f in assets/welcome/logo-light.svg assets/welcome/logo-dark.svg \
         packages/ubuntu_provision/assets/images/logo-light.svg packages/ubuntu_provision/assets/images/logo-dark.svg; do
    cp "assets/$(basename $f)" "$FA/$f"
done
cp assets/icon.svg "$FA/assets/storage/ubuntu.svg"
# installer icon (the Ubuntu logo shown in the menu)
ICON=$(grep -m1 '^Icon=' inst/meta/gui/ubuntu-desktop-bootstrap.desktop | cut -d= -f2- | sed "s|\${SNAP}|inst|")
if [ -n "$ICON" ] && [ -f "$ICON" ]; then
    case "$ICON" in
        *.svg) cp assets/icon.svg "$ICON" ;;
        *.png) d=$(python3 -c "import struct,sys; d=open(sys.argv[1],'rb').read(32); print(*struct.unpack('>II', d[16:24]))" "$ICON"); set -- $d
               rsvg-convert -w "$1" -h "$2" assets/icon.svg -o "$ICON" ;;
    esac
    echo "   installer icon replaced: $ICON"
fi
python3 "$HERE/patch_installer.py" inst/bin/lib/libapp.so
rename_desktop livefs/usr/share/applications/gparted.desktop "Xenon Bolumleyici" "XenonOS disk bolumleme"
# the "Install RELEASE" shortcut on the desktop
rename_desktop livefs/var/lib/snapd/desktop/applications/ubuntu-desktop-bootstrap_ubuntu-desktop-bootstrap.desktop "XenonOS Kur"
rename_desktop inst/meta/gui/ubuntu-desktop-bootstrap.desktop "XenonOS Kur"
SQ_COMP=$(unsquashfs -s "livefs/var/lib/snapd/seed/snaps/$SNAP_REL" | awk '/^Compression/{print $2}')
SQ_BS=$(unsquashfs -s "livefs/var/lib/snapd/seed/snaps/$SNAP_REL" | awk '/^Block size/{print $3}')
echo "   snap compression: $SQ_COMP, block: $SQ_BS"
rm -f new.snap
mksquashfs inst new.snap -comp "$SQ_COMP" -b "$SQ_BS" -noappend -no-progress -all-root
for d in livefs/var/lib/snapd/seed/snaps livefs/var/lib/snapd/snaps; do
    if [ -f "$d/$SNAP_REL" ]; then rm -f "$d/$SNAP_REL"; cp new.snap "$d/$SNAP_REL"; chmod 600 "$d/$SNAP_REL"; fi
done
echo ">> Packing live layer..."
rm -f minimal.standard.live.xenon.squashfs
mksquashfs livefs minimal.standard.live.xenon.squashfs -comp xz -b 131072 -noappend -no-progress

# ================================================================ GRUB + ISO
cat > grub.cfg <<'EOF'
set default=0
set timeout=30

loadfont unicode
set menu_color_normal=cyan/black
set menu_color_highlight=black/cyan

menuentry "XenonOS 1.0  -  Dene veya Kur" {
    set gfxpayload=keep
    linux  /casper/vmlinuz  --- quiet splash
    initrd /casper/initrd
}
menuentry "XenonOS 1.0  -  Guvenli grafik (nomodeset)" {
    set gfxpayload=keep
    linux  /casper/vmlinuz nomodeset  --- quiet splash
    initrd /casper/initrd
}
grub_platform
if [ "$grub_platform" = "efi" ]; then
menuentry 'Sonraki diskten ac' {
    exit 1
}
menuentry 'UEFI Firmware Ayarlari' {
    fwsetup
}
fi
EOF

# .disk/info: the installer reads the window-title name from here; the format must stay the same as the original
printf 'XenonOS 26.04 "Resolute Raccoon" - Release amd64 (20260423.1)\n' > diskinfo

echo ">> Writing ISO: $OUT"
rm -f "$OUT"
xorriso -indev "$SRC_ISO" -outdev "$OUT" \
    -map minimal.xenon.squashfs /casper/minimal.squashfs \
    -map minimal.standard.xenon.squashfs /casper/minimal.standard.squashfs \
    -map minimal.standard.live.xenon.squashfs /casper/minimal.standard.live.squashfs \
    -map grub.cfg /boot/grub/grub.cfg \
    -map diskinfo /.disk/info \
    -volid "XENONOS" \
    -boot_image any replay \
    -commit
echo ">> Ready: $OUT"
