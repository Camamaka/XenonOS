# XenonOS — Debian 13 (trixie) + KDE Plasma

XenonOS built from Debian packages, independent of Ubuntu.

## Layout
| Path | What |
|---|---|
| `build-debs.sh` | Builds the `xenonium`, `xenonpad`, `xenonwriter` and `xenonos-defaults` `.deb` packages (no internet required) |
| `packages/` | Generated `.deb` files |
| `live-build/` | Debian `live-build` configuration (package list, hooks, branding) |
| `build-iso.sh` | Installs the tools and builds the ISO (**downloads packages**) |

## Steps
1. `sudo bash build-debs.sh`  → packages (no download)
2. `sudo bash build-iso.sh`   → tool setup + Debian package download + ISO (≈ 1.5–3 GB download, 20–60 min)
3. Open `out/xenonos-*.iso` in VirtualBox.

## Publishing your own package repository (next step)
Put `packages/*.deb` into an apt repository with `reprepro` or `aptly`, sign it with GPG, and write the repository address into
`config/archives/xenonos.list.chroot`. Updates then arrive through `apt upgrade`.

## Known gaps (not yet tested)
- Plasma taskbar favorites (pinning Xenonium/XenonPad/XenonWriter) are not configured.
- Calamares branding texts are replaced with `sed`; verify with a screenshot.
- Package names were written for Debian 13; if `apt` cannot find one, `lb build` fails and it needs fixing.
