#!/bin/bash
# GNOME icin aday paket adlarini, onceki derlemeden kalan chroot'un apt dizinine karsi dogrular (indirme yok)
CH=/root/xenonos-lb/chroot
[ -d "$CH/var/lib/apt/lists" ] || { echo "chroot yok"; exit 1; }
for p in gnome-shell gdm3 gnome-session nautilus gnome-control-center gnome-console gnome-terminal gnome-calculator \
         gnome-system-monitor gnome-disk-utility loupe papers evince gnome-tweaks gnome-shell-extension-manager \
         gnome-keyring xdg-desktop-portal-gnome gvfs-backends network-manager network-manager-gnome \
         pipewire-audio wireplumber file-roller gnome-clocks gnome-text-editor gnome-menus gnome-shell-extensions \
         gnome-backgrounds adwaita-icon-theme yaru-theme-gtk fonts-cantarell fonts-noto-core fonts-dejavu \
         dconf-cli librsvg2-bin calamares calamares-settings-debian firefox-esr plymouth plymouth-themes \
         gir1.2-adw-1 gir1.2-gtk-4.0 gir1.2-gtk-3.0 gir1.2-webkit2-4.1 python3-gi hunspell-en-us \
         gnome-initial-setup gnome-online-accounts gnome-user-docs yelp malcontent gnome-software gnome-shell-extension-prefs \
         gnome-remote-desktop ibus ibus-gtk4 ibus-gtk3 chrome-gnome-shell gjs libsoup-3.0-0 gir1.2-soup-3.0 \
         desktop-base task-gnome-desktop gnome-core; do
  if chroot "$CH" apt-cache show "$p" >/dev/null 2>&1; then echo "var : $p"; else echo "YOK : $p"; fi
done
echo "== GNOME Shell surumu"
chroot "$CH" apt-cache policy gnome-shell | head -3
