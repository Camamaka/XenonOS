import re, sys, tokenize, io
WORDS = re.compile(r"\b(ekle|kaydet\w*|acil\w*|sekme\w*|gecmis|yer imi\w*|indir\w*|sayfa\w*|dosya\w*|satir\w*|sutun|secili|sec\b|degis\w*|kapat\w*|yeni|iptal|tamam|belge\w*|metin|bul\w*|ayar\w*|hakkinda|cikis|hata\w*|basar\w*|oneri|izin|konum\w*|bildirim|pencere\w*|eklenti\w*|tarayici|islem\w*|yaz\w*|sil|giris|kullanici|parola|ile|ve|veya|icin|bir|bu|mi\?|gizli|goster|tekrar|dene|bekle|yukle\w*|ac\b|git\b|devam|kimlik|erisim|tum\w*|onceki|sonraki|cevir\w*|kopyala\w*|yapistir|kes\b|boyut\w*|renk|yazi|tipi|kelime|karakter|duzen\w*|resim|baglanti\w*|tablo|cizgi|hizala|girinti\w*|alinti|baslik|liste|madde|numara\w*|oturum|cikti|hosgeldin|kur\b|calis\w*|olustur\w*|bulun\w*)\b", re.I)
DIAC = re.compile(r"[çğıöşüÇĞİÖŞÜ]")
for path in sys.argv[1:]:
    src = open(path, encoding="utf-8").read()
    try:
        toks = list(tokenize.generate_tokens(io.StringIO(src).readline))
    except tokenize.TokenError:
        continue
    for t in toks:
        if t.type == tokenize.STRING or (hasattr(tokenize, "FSTRING_MIDDLE") and t.type == tokenize.FSTRING_MIDDLE):
            s = t.string
            if s.startswith(('"""', "'''")) and len(s) > 200:
                continue
            if WORDS.search(s) or DIAC.search(s):
                print(f"{path.split('/')[-1]}:{t.start[0]}: {s[:110]!r}")
