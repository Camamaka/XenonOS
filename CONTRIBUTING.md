# Contributing to XenonOS

Thanks for your interest! Bug reports, ideas and pull requests are all welcome.

## Reporting a problem
Open an [issue](https://github.com/Camamaka/XenonOS/issues) and include:
- what you did and what you expected to happen,
- what actually happened (screenshots help),
- where you ran XenonOS (VirtualBox, QEMU, real hardware) and the ISO version.

## Trying a change
1. Fork the repository and create a branch.
2. The applications live in `apps/` and are plain Python (GTK). You can run them on any Linux machine with GTK and WebKitGTK:
   `python3 apps/xenonpad/xenonpad.py`.
3. To build the ISO, see [`debian/README.md`](debian/README.md) (WSL or Debian/Ubuntu, root required, ~1.5–3 GB download).
4. Keep code, comments and user-facing text in English.
5. Open a pull request describing what changed and how you tested it.

## Good first areas
- Testing the installer (Calamares) on different hardware and reporting results.
- More Xenonium extensions (see `apps/xenonium/extensions/xenontranslate/`).
- Translations and accessibility improvements.

By contributing you agree that your contribution is released under the [MIT License](LICENSE).
