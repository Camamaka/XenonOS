#!/usr/bin/env python3
"""Kurulum programi (libapp.so) icindeki gorunen 'Ubuntu' metinlerini ayni uzunlukta 'Xenon ' ile degistirir.

Dart snapshot'inda dizgeler birbirine bitisik durdugu icin blok uzunluguna degil, 'Ubuntu' kelimesinin
hemen cevresine bakilir: yani bir cumlenin parcasi (oncesinde 'kelime ' veya sonrasinda ' kelime')
olmali; 'UbuntuPage', 'ubuntu_x', yol/anahtar gibi tanimlayici baglamlarina dokunulmaz.
Uzunluk degismedigi icin snapshot yapisi bozulmaz."""
import sys, re

path = sys.argv[1]
data = bytearray(open(path, 'rb').read())

OLD = b'Ubuntu'
NEW = b'Xenon '
SKIP_AFTER = (b' Pro', b' One', b' Insights', b' Core', b' Desktop', b' Server', b' Touch')
IDCH = re.compile(rb'[A-Za-z0-9_/.\-]')
LETTER = re.compile(rb'[A-Za-z\xc0-\xff]')

count = skipped = 0
i = 0
while True:
    i = data.find(OLD, i)
    if i < 0:
        break
    end = i + len(OLD)
    before = bytes(data[max(0, i - 12):i])
    after = bytes(data[end:end + 12])
    # hemen yaninda tanimlayici karakteri varsa (UbuntuPage, /Ubuntu, ubuntu-x ...) atla
    prev_ch = before[-1:] if before else b''
    next_ch = after[:1]
    glued = (prev_ch and IDCH.match(prev_ch)) or (next_ch and re.match(rb'[A-Za-z0-9_]', next_ch))
    # cumle baglami: 'kelime ' + Ubuntu   veya   Ubuntu + ' ' + kucuk harf / kesme
    sentence_before = len(before) >= 2 and before[-1:] == b' ' and LETTER.match(before[-2:-1]) is not None
    sentence_after = after[:1] == b' ' and re.match(rb'[a-z\xe0-\xff]', after[1:2] or b'') is not None
    apostrophe = after[:1] in (b"'", b'\xb4')
    skip_prod = any(after.startswith(s) for s in SKIP_AFTER)
    if not glued and (sentence_before or sentence_after or apostrophe) and not skip_prod:
        data[i:end] = NEW
        count += 1
    else:
        skipped += 1
    i = end

# tek basina duran 'Ubuntu' dizgesi (surum adi sabiti: 'Welcome to <ad>' basligini besler)
standalone = re.compile(rb'(?<![\x20-\x7e\xa0-\xff])Ubuntu(?![\x20-\x7e\xa0-\xff])')
data = bytearray(standalone.sub(NEW, bytes(data)))
alone = len(standalone.findall(bytes(open(path, 'rb').read())))

open(path, 'wb').write(data)
print(f'degistirilen: {count}, atlanan: {skipped}, tek basina Ubuntu (dosyada): {alone}')
