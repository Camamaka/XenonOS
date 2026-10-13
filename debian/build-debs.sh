#!/bin/bash
# XenonOS .deb packages (Debian 13 + GNOME). Needs NO internet: only dpkg-deb + python3.
# Output: ./packages/*.deb  (also copied to live-build/config/packages.chroot/)
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
APPS="$(cd "$HERE/../apps" && pwd)"
OUT="$HERE/packages"
BUILD="$(mktemp -d /tmp/xenonos-debbuild.XXXXXX)"   # ext4: file modes on the Windows drive (777) break dpkg-deb
trap 'rm -rf "$BUILD"' EXIT
VERSION="${VERSION:-1.0}"
MAINT="XenonOS <noreply@xenonos.local>"

rm -rf "$OUT"; mkdir -p "$OUT"

# ---- brand assets: everything is built around the element Xenon (Xe, 54) ----
python3 "$HERE/brand.py" "$BUILD/brand" >/dev/null
EXT_SRC="$HERE/extension/xenonnews@xenonos"

mkdeb() {   # mkdeb <package-dir> <name>
    local dir="$1" name="$2"
    find "$dir" -name '__pycache__' -prune -exec rm -rf {} + 2>/dev/null || true
    find "$dir" -type d -exec chmod 755 {} +
    find "$dir" -type f -exec chmod 644 {} +
    [ -d "$dir/usr/bin" ] && chmod 755 "$dir"/usr/bin/* || true
    for s in postinst prerm postrm; do [ -f "$dir/DEBIAN/$s" ] && chmod 755 "$dir/DEBIAN/$s" || true; done
    local size; size=$(du -sk --exclude=DEBIAN "$dir" | cut -f1)
    echo "Installed-Size: $size" >> "$dir/DEBIAN/control"
    dpkg-deb --root-owner-group --build "$dir" "$OUT/${name}_${VERSION}_all.deb" >/dev/null
    echo "  + ${name}_${VERSION}_all.deb"
}

control() {  # control <dir> <name> <depends> <short> <long>
    mkdir -p "$1/DEBIAN"
    cat > "$1/DEBIAN/control" <<EOF
Package: $2
Version: $VERSION
Architecture: all
Maintainer: $MAINT
Section: ${SECTION:-utils}
Priority: optional
Depends: $3
Description: $4
 $5
EOF
}

app_icon() { mkdir -p "$1/usr/share/icons/hicolor/scalable/apps"; cp "$BUILD/brand/$2.svg" "$1/usr/share/icons/hicolor/scalable/apps/$2.svg"; }
wrapper()  { mkdir -p "$1/usr/bin"; printf '#!/bin/sh\nexec python3 /usr/lib/xenonos/%s/%s "$@"\n' "$2" "$3" > "$1/usr/bin/$2"; }

echo ">> Building packages ($VERSION)..."

# ------------------------------------------------------------------ xenonium
P="$BUILD/xenonium"; mkdir -p "$P/usr/lib/xenonos"
cp -r "$APPS/xenonium" "$P/usr/lib/xenonos/xenonium"
wrapper "$P" xenonium browser.py; app_icon "$P" xenonium
mkdir -p "$P/usr/share/applications"
cat > "$P/usr/share/applications/org.xenonos.Xenonium.desktop" <<'EOF'
[Desktop Entry]
Type=Application
Name=Xenonium
GenericName=Web Browser
Comment=The XenonOS web browser (XenonTranslate included)
Exec=xenonium %U
Icon=xenonium
Terminal=false
Categories=Network;WebBrowser;
MimeType=text/html;application/xhtml+xml;x-scheme-handler/http;x-scheme-handler/https;
StartupWMClass=xenonium
StartupNotify=true
Keywords=web;internet;browser;
Actions=new-window;private-window;

[Desktop Action new-window]
Name=New Window
Exec=xenonium

[Desktop Action private-window]
Name=New Private Window
Exec=xenonium --private
EOF
SECTION=web control "$P" xenonium \
    "python3, python3-gi, gir1.2-gtk-3.0, gir1.2-webkit2-4.1, gir1.2-gdkpixbuf-2.0, libwebkit2gtk-4.1-0, shared-mime-info" \
    "XenonOS web browser" \
    "WebKitGTK based browser: tabs, bookmarks, history, downloads, private windows and extension support. Includes the XenonTranslate extension."
cat > "$P/DEBIAN/postinst" <<'EOF'
#!/bin/sh
set -e
if [ "$1" = "configure" ]; then
    update-alternatives --install /usr/bin/x-www-browser x-www-browser /usr/bin/xenonium 200
    update-alternatives --install /usr/bin/gnome-www-browser gnome-www-browser /usr/bin/xenonium 200
    update-alternatives --install /usr/bin/www-browser www-browser /usr/bin/xenonium 100
fi
exit 0
EOF
cat > "$P/DEBIAN/prerm" <<'EOF'
#!/bin/sh
set -e
if [ "$1" = "remove" ] || [ "$1" = "deconfigure" ]; then
    update-alternatives --remove x-www-browser /usr/bin/xenonium
    update-alternatives --remove gnome-www-browser /usr/bin/xenonium
    update-alternatives --remove www-browser /usr/bin/xenonium
fi
exit 0
EOF
mkdeb "$P" xenonium

# ------------------------------------------------------------------ xenonpad
P="$BUILD/xenonpad"; mkdir -p "$P/usr/lib/xenonos"
cp -r "$APPS/xenonpad" "$P/usr/lib/xenonos/xenonpad"
wrapper "$P" xenonpad xenonpad.py; app_icon "$P" xenonpad
mkdir -p "$P/usr/share/applications"
cat > "$P/usr/share/applications/org.xenonos.XenonPad.desktop" <<'EOF'
[Desktop Entry]
Type=Application
Name=XenonPad
GenericName=Text Editor
Comment=The XenonOS text editor
Exec=xenonpad %F
Icon=xenonpad
Terminal=false
Categories=Utility;TextEditor;GTK;
MimeType=text/plain;text/markdown;text/x-python;text/x-csrc;application/x-shellscript;application/json;application/xml;
StartupNotify=true
Keywords=text;notes;editor;
EOF
SECTION=editors control "$P" xenonpad "python3, python3-gi, gir1.2-gtk-4.0, gir1.2-adw-1" \
    "XenonOS text editor" \
    "GTK4 and libadwaita text editor: tabs, find/replace, go to line, auto-indent and recovery copies."
mkdeb "$P" xenonpad

# ------------------------------------------------------------------ xenonwriter
P="$BUILD/xenonwriter"; mkdir -p "$P/usr/lib/xenonos"
cp -r "$APPS/xenonwriter" "$P/usr/lib/xenonos/xenonwriter"
wrapper "$P" xenonwriter xenonwriter.py; app_icon "$P" xenonwriter
mkdir -p "$P/usr/share/applications"
cat > "$P/usr/share/applications/org.xenonos.XenonWriter.desktop" <<'EOF'
[Desktop Entry]
Type=Application
Name=XenonWriter
GenericName=Word Processor
Comment=The XenonOS word processor
Exec=xenonwriter %F
Icon=xenonwriter
Terminal=false
Categories=Office;WordProcessor;GTK;
MimeType=text/html;
StartupWMClass=xenonwriter
StartupNotify=true
Keywords=document;writer;word;
EOF
SECTION=editors control "$P" xenonwriter \
    "python3, python3-gi, gir1.2-gtk-3.0, gir1.2-webkit2-4.1, libwebkit2gtk-4.1-0" \
    "XenonOS word processor" \
    "Rich text editing with an A4 page view, tables, images and links; save as HTML/text and export to PDF."
mkdeb "$P" xenonwriter

# ------------------------------------------------------------------ xenonos-defaults (brand, GNOME defaults, news widget)
P="$BUILD/xenonos-defaults"
mkdir -p "$P/usr/share/xenonos" "$P/usr/share/backgrounds/xenonos" "$P/etc/xdg" "$P/etc/skel" \
         "$P/etc/dconf/profile" "$P/etc/dconf/db/xenon.d" "$P/etc/dconf/db/gdm.d" \
         "$P/usr/share/gnome-shell/extensions"
cp "$BUILD/brand/xenonos-logo.svg" "$BUILD/brand/xenonos-icon.svg" "$P/usr/share/xenonos/"
cp "$BUILD/brand/xenonos-wallpaper.svg" "$P/usr/share/backgrounds/xenonos/xenonos.svg"
cp -r "$EXT_SRC" "$P/usr/share/gnome-shell/extensions/xenonnews@xenonos"
cat > "$P/usr/share/xenonos/CREDITS" <<'EOF'
XenonOS
=======
Element: Xenon (Xe) - atomic number 54, atomic mass 131.293, noble gas, [Kr] 4d10 5s2 5p6
Founders: DTA & CMK
Designer: EHA
EOF
cat > "$P/etc/xenonos-release" <<EOF
NAME="XenonOS"
VERSION="$VERSION"
ID=xenonos
ID_LIKE=debian
PRETTY_NAME="XenonOS $VERSION (Xe 54)"
XENONOS_ELEMENT="Xenon (Xe, 54)"
XENONOS_FOUNDERS="DTA & CMK"
XENONOS_DESIGNER="EHA"
EOF
cat > "$P/etc/xdg/mimeapps.list" <<'EOF'
[Default Applications]
x-scheme-handler/http=org.xenonos.Xenonium.desktop;
x-scheme-handler/https=org.xenonos.Xenonium.desktop;
text/html=org.xenonos.Xenonium.desktop;
application/xhtml+xml=org.xenonos.Xenonium.desktop;
text/plain=org.xenonos.XenonPad.desktop;
text/markdown=org.xenonos.XenonPad.desktop;
EOF
cat > "$P/etc/skel/Welcome-to-XenonOS.txt" <<'EOF'
Welcome to XenonOS!

XenonOS is named after the element Xenon (Xe, atomic number 54).
It is built on Debian 13, so packages and updates come from Debian:

    sudo apt update && sudo apt upgrade

Tip: triple-click the Xe tile in the news widget (bottom-left of the desktop)
to see who made XenonOS.
EOF
printf 'user-db:user\nsystem-db:xenon\nsystem-db:local\n' > "$P/etc/dconf/profile/user"
cat > "$P/etc/dconf/db/xenon.d/00-xenonos" <<'EOF'
[org/gnome/desktop/background]
picture-uri='file:///usr/share/backgrounds/xenonos/xenonos.png'
picture-uri-dark='file:///usr/share/backgrounds/xenonos/xenonos.png'
picture-options='zoom'
primary-color='#0b0720'

[org/gnome/desktop/screensaver]
picture-uri='file:///usr/share/backgrounds/xenonos/xenonos.png'
primary-color='#0b0720'

[org/gnome/desktop/interface]
color-scheme='prefer-dark'
accent-color='purple'
enable-hot-corners=false

[org/gnome/desktop/input-sources]
sources=[('xkb', 'tr'), ('xkb', 'us')]

[org/gnome/desktop/wm/preferences]
button-layout='appmenu:minimize,maximize,close'

[org/gnome/settings-daemon/plugins/media-keys]
custom-keybindings=['/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/xenon-terminal/']

[org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/xenon-terminal]
name='Terminal'
command='kgx'
binding='<Primary><Alt>t'

[org/gnome/shell]
favorite-apps=['org.xenonos.Xenonium.desktop', 'org.gnome.Nautilus.desktop', 'org.xenonos.XenonPad.desktop', 'org.xenonos.XenonWriter.desktop', 'org.gnome.Console.desktop', 'org.gnome.Settings.desktop']
enabled-extensions=['xenonnews@xenonos']
welcome-dialog-last-shown-version='999'
EOF
cat > "$P/etc/dconf/db/gdm.d/00-xenonos" <<'EOF'
[org/gnome/login-screen]
logo='/usr/share/xenonos/xenonos-logo.svg'
banner-message-enable=true
banner-message-text='XenonOS  ·  Xe 54'

[org/gnome/desktop/interface]
color-scheme='prefer-dark'
EOF
SECTION=misc control "$P" xenonos-defaults \
    "xenonium, xenonpad, xenonwriter, librsvg2-bin, fonts-dejavu-core, dconf-cli, gnome-shell" \
    "XenonOS defaults and branding" \
    "Xenon element (Xe, 54) branding, wallpaper, GNOME defaults, default apps and the Xenon News desktop widget."
cat > "$P/DEBIAN/postinst" <<'EOF'
#!/bin/sh
set -e
if [ "$1" = "configure" ]; then
    # wallpaper PNG from the SVG
    if command -v rsvg-convert >/dev/null 2>&1; then
        rsvg-convert -w 1920 -h 1080 /usr/share/backgrounds/xenonos/xenonos.svg -o /usr/share/backgrounds/xenonos/xenonos.png || true
    fi
    # os-release: divert Debian's file (derivative: ID_LIKE=debian)
    if ! dpkg-divert --list /usr/lib/os-release | grep -q xenonos-defaults; then
        dpkg-divert --package xenonos-defaults --add --rename --divert /usr/lib/os-release.debian /usr/lib/os-release
    fi
    . /etc/xenonos-release
    cat > /usr/lib/os-release <<OSR
PRETTY_NAME="$PRETTY_NAME"
NAME="XenonOS"
VERSION_ID="$VERSION"
VERSION="$VERSION (Debian 13 trixie)"
VERSION_CODENAME=trixie
ID=xenonos
ID_LIKE=debian
HOME_URL="https://www.debian.org/"
SUPPORT_URL="https://www.debian.org/support"
BUG_REPORT_URL="https://bugs.debian.org/"
LOGO=xenonos
XENONOS_ELEMENT="$XENONOS_ELEMENT"
XENONOS_FOUNDERS="$XENONOS_FOUNDERS"
XENONOS_DESIGNER="$XENONOS_DESIGNER"
OSR
    ln -sf ../usr/lib/os-release /etc/os-release
    printf 'XenonOS %s (Xe 54) \\n \\l\n\n' "$VERSION" > /etc/issue
    printf 'XenonOS %s\n' "$VERSION" > /etc/issue.net
    command -v dconf >/dev/null 2>&1 && dconf update || true
fi
exit 0
EOF
cat > "$P/DEBIAN/postrm" <<'EOF'
#!/bin/sh
set -e
if [ "$1" = "remove" ] || [ "$1" = "purge" ]; then
    dpkg-divert --package xenonos-defaults --remove --rename /usr/lib/os-release || true
    command -v dconf >/dev/null 2>&1 && dconf update || true
fi
exit 0
EOF
mkdeb "$P" xenonos-defaults

# copy into live-build's local package folder
LB="$HERE/live-build/config/packages.chroot"
mkdir -p "$LB"; rm -f "$LB"/*.deb; cp "$OUT"/*.deb "$LB/"
echo ">> Done: $OUT"
ls -la "$OUT"
