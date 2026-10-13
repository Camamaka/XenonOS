"""XenonOS builder: hand-assembles 16-bit real-mode machine code and writes a 1.44MB floppy image."""
import struct, math

KBASE = 0x7E00  # kernel load address


class Asm:
    def __init__(self, base):
        self.base = base
        self.b = bytearray()
        self.labels = {}
        self.fix = []  # (offset, label, kind) kind: 'abs' | 'rel'

    def label(self, n):
        self.labels[n] = self.base + len(self.b)

    def raw(self, *bs):
        self.b += bytes(bs)

    def w(self, v):
        self.b += struct.pack('<H', v & 0xFFFF)

    def ref_abs(self, name):
        self.fix.append((len(self.b), name, 'abs'))
        self.w(0)

    def ref_rel(self, name):
        self.fix.append((len(self.b), name, 'rel'))
        self.w(0)

    # ---- komutlar ----
    def mov_r16(self, r, v):  # r: ax0 cx1 dx2 bx3 sp4 bp5 si6 di7
        self.raw(0xB8 + r); self.w(v)

    def mov_r16_label(self, r, name):
        self.raw(0xB8 + r); self.ref_abs(name)

    def mov_r8(self, r, v):  # al0 cl1 dl2 bl3 ah4 ch5 dh6 bh7
        self.raw(0xB0 + r, v)

    def int_(self, n): self.raw(0xCD, n)
    def call(self, name): self.raw(0xE8); self.ref_rel(name)
    def jmp(self, name): self.raw(0xE9); self.ref_rel(name)
    def jcc(self, op, name): self.raw(0x0F, op); self.ref_rel(name)
    def je(self, name): self.jcc(0x84, name)
    def jne(self, name): self.jcc(0x85, name)
    def ret(self): self.raw(0xC3)
    def st_ax(self, name): self.raw(0xA3); self.ref_abs(name)
    def ld_ax(self, name): self.raw(0xA1); self.ref_abs(name)
    def st_al(self, name): self.raw(0xA2); self.ref_abs(name)
    def ld_al(self, name): self.raw(0xA0); self.ref_abs(name)
    def st_dl(self, name): self.raw(0x88, 0x16); self.ref_abs(name)
    def ld_dl(self, name): self.raw(0x8A, 0x16); self.ref_abs(name)
    def ld_bl(self, name): self.raw(0x8A, 0x1E); self.ref_abs(name)
    def cmp_al(self, v): self.raw(0x3C, v)

    def finish(self):
        for off, name, kind in self.fix:
            t = self.labels[name]
            if kind == 'abs':
                v = t
            else:
                v = t - (self.base + off + 2)
            self.b[off:off + 2] = struct.pack('<H', v & 0xFFFF)
        return bytes(self.b)


AX, CX, DX, BX, SP, BP, SI, DI = range(8)
AL, CL, DL, BL, AH, CH, DH, BH = range(8)

# ------------------------------------------------------------------ texts
FIKRALAR = [
    "Temel doktora gider: 'Doktor bey, unutkanlik basladi.'\r\nDoktor: 'Ne zamandan beri?'  Temel: 'Ne zamandan beri ne?'",
    "Ogretmen: 'Cocuklar, bir cumlede hem cunku hem ama kullanin.'\r\nAli: 'Cunku ders cok guzeldi ama zil caldi.'",
    "Nasreddin Hoca'ya sormuslar: 'Ay mi faydali gunes mi?'\r\nHoca: 'Ay tabii! Karanlikta isik veriyor, gunes zaten gunduz var.'",
    "Adam bakkala girer: 'Bir ekmek verir misiniz?' Bakkal: 'Dilimli mi?'\r\nAdam: 'Hayir, butun olsun, ben kendim yutarim.'",
    "Bilgisayar neden soguk almaz?\r\nCunku hep Windows'u aciktir... ama o da bazen donar.",
    "Kedi kopege demis: 'Sen neden hep havliyorsun?'\r\nKopek: 'Cunku sen hep miyavliyorsun, birimiz konusmali.'",
]
SOZLER = [
    "Kucuk adimlar da seni hedefe goturur. Onemli olan durmamak.",
    "Bugun dunden bir adim daha iyi olmak yeterli.",
    "Hata yapmak ogrenmenin bir parcasidir, vazgecmek degil.",
    "En karanlik an, safaktan hemen oncedir.",
    "Baslamak icin mukemmel olmayi bekleme, basla ki mukemmellesesin.",
    "Yapabilecegine inan, yolun yarisini gecmis olursun.",
]
YEMEKLER = [
    "Menemen (sogansiz mi soganli mi tartismasi bonus)",
    "Lahmacun ve ayran", "Manti, bol yogurtlu", "Tavuklu pilav ve cacik",
    "Makarna, ustune bol peynir", "Kuru fasulye ve pilav",
    "Tost ve bir bardak cay", "Mercimek corbasi ve limon", "Pizza gecesi!",
]

NL = "\r\n"
BANNER = (
    NL + "   __  __                            ___  ____ " + NL +
    "   \\ \\/ /___  ____  ____  ____ ___  / _ \\/ __/ " + NL +
    "    \\  / -_)/ _ \\/ _ \\/ _ \\/ _ \\_ \\ \\_, /\\ \\   " + NL +
    "    /_/\\__/ _//_/\\___/_//_/\\___/___/  /_/___/   " + NL + NL +
    "              XenonOS v0.1  -  senin ilk isletim sistemin" + NL + NL +
    "   [1] Gunun fikrasi" + NL +
    "   [2] Motivasyon sozu" + NL +
    "   [3] Bugun ne yesem?" + NL +
    "   [4] Zar at" + NL +
    "   [5] Surpriz!" + NL +
    "   [0] Yeniden baslat" + NL + NL +
    "   Bir tusa bas > "
)
DEVAM = NL + NL + "   (devam icin bir tusa bas)"


def kernel():
    a = Asm(KBASE)

    # ---- entry ----
    a.label('start')
    a.mov_r16(AX, 0x0003); a.int_(0x10)          # 80x25 text mode
    a.label('main')
    a.mov_r8(AL, 0x0B); a.st_al('attr')          # light cyan
    a.call('cls')
    a.mov_r16_label(SI, 'banner'); a.call('print')
    a.call('getkey')
    a.cmp_al(ord('1')); a.je('do_fikra')
    a.cmp_al(ord('2')); a.je('do_soz')
    a.cmp_al(ord('3')); a.je('do_yemek')
    a.cmp_al(ord('4')); a.je('do_zar')
    a.cmp_al(ord('5')); a.je('do_surpriz')
    a.cmp_al(ord('0')); a.je('do_reboot')
    a.jmp('main')

    a.label('do_reboot')
    a.raw(0xEA); a.w(0x0000); a.w(0xFFFF)        # jmp FFFF:0000

    def pick_section(lbl, attr, title, count, table):
        a.label(lbl)
        a.mov_r8(AL, attr); a.st_al('attr')
        a.call('cls')
        a.mov_r16_label(SI, title); a.call('print')
        a.mov_r16(BX, count); a.mov_r16_label(CX, table); a.call('pick')
        a.call('print')
        a.jmp('wait_back')

    pick_section('do_fikra', 0x0E, 't_fikra', len(FIKRALAR), 'tb_fikra')
    pick_section('do_soz', 0x0A, 't_soz', len(SOZLER), 'tb_soz')
    pick_section('do_yemek', 0x0D, 't_yemek', len(YEMEKLER), 'tb_yemek')

    a.label('do_zar')
    a.mov_r8(AL, 0x0C); a.st_al('attr')
    a.call('cls')
    a.mov_r16_label(SI, 't_zar'); a.call('print')
    a.call('rand'); a.raw(0x31, 0xD2)            # xor dx,dx
    a.mov_r16(BX, 6); a.raw(0xF7, 0xF3)          # div bx
    a.raw(0x88, 0xD0); a.raw(0x04, ord('1'))     # mov al,dl ; add al,'1'
    a.call('putc')
    a.jmp('wait_back')

    a.label('do_surpriz')
    a.mov_r8(AL, 0x0F); a.st_al('attr')
    a.call('cls')
    a.mov_r16_label(SI, 't_surpriz'); a.call('print')
    a.mov_r8(AL, 0x0E); a.st_al('attr')
    a.mov_r16(BX, len(FIKRALAR)); a.mov_r16_label(CX, 'tb_fikra'); a.call('pick'); a.call('print')
    a.mov_r16_label(SI, 'nl2'); a.call('print')
    a.mov_r8(AL, 0x0A); a.st_al('attr')
    a.mov_r16(BX, len(SOZLER)); a.mov_r16_label(CX, 'tb_soz'); a.call('pick'); a.call('print')
    a.mov_r16_label(SI, 'nl2'); a.call('print')
    a.mov_r8(AL, 0x0D); a.st_al('attr')
    a.mov_r16(BX, len(YEMEKLER)); a.mov_r16_label(CX, 'tb_yemek'); a.call('pick'); a.call('print')
    a.jmp('wait_back')

    a.label('wait_back')
    a.mov_r8(AL, 0x07); a.st_al('attr')
    a.mov_r16_label(SI, 'devam'); a.call('print')
    a.call('getkey')
    a.jmp('main')

    # ---- cls: clear the screen with the attr color, move the cursor to the top ----
    a.label('cls')
    a.raw(0x31, 0xC0)                             # xor ax,ax
    a.mov_r16(AX, 0x0600)
    a.mov_r8(BH, 0x00)
    a.raw(0x8A, 0x3E); a.ref_abs('attr')          # mov bh,[attr]
    a.raw(0x80, 0xE7, 0x70)                       # and bh,0x70  (background only: stays black)
    a.mov_r16(CX, 0x0000); a.mov_r16(DX, 0x184F)
    a.int_(0x10)
    a.mov_r8(AH, 0x02); a.mov_r8(BH, 0x00); a.mov_r16(DX, 0x0000); a.int_(0x10)
    a.ret()

    # ---- putc: write the character in al using the attr color ----
    a.label('putc')
    a.cmp_al(0x0D); a.je('putc_raw')
    a.cmp_al(0x0A); a.je('putc_raw')
    a.mov_r8(AH, 0x09); a.mov_r8(BH, 0x00); a.ld_bl('attr'); a.mov_r16(CX, 1); a.int_(0x10)
    a.label('putc_raw')
    a.mov_r8(AH, 0x0E); a.mov_r8(BH, 0x00); a.int_(0x10)
    a.ret()

    # ---- print: write the 0-terminated string at si ----
    a.label('print')
    a.raw(0xAC)                                   # lodsb
    a.raw(0x08, 0xC0)                             # or al,al
    a.je('print_end')
    a.call('putc')
    a.jmp('print')
    a.label('print_end')
    a.ret()

    # ---- rand: ax = 0..255 ----
    a.label('rand')
    a.ld_ax('seed')
    a.raw(0x53)                                   # push bx
    a.mov_r16(BX, 25173); a.raw(0xF7, 0xE3)       # mul bx
    a.raw(0x5B)                                   # pop bx
    a.raw(0x05); a.w(13849)                       # add ax,13849
    a.st_ax('seed')
    a.raw(0x88, 0xE0); a.raw(0x30, 0xE4)          # mov al,ah ; xor ah,ah
    a.ret()

    # ---- pick: bx=count, cx=table -> si = random string ----
    a.label('pick')
    a.call('rand')
    a.raw(0x31, 0xD2)                             # xor dx,dx
    a.raw(0xF7, 0xF3)                             # div bx
    a.raw(0xD1, 0xE2)                             # shl dx,1
    a.raw(0x89, 0xCB)                             # mov bx,cx
    a.raw(0x01, 0xD3)                             # add bx,dx
    a.raw(0x8B, 0x37)                             # mov si,[bx]
    a.ret()

    # ---- getkey: wait for a key, mix the timer into the seed ----
    a.label('getkey')
    a.mov_r8(AH, 0x00); a.int_(0x16)              # read key (al = character)
    a.raw(0x50)                                   # push ax
    a.mov_r8(AH, 0x00); a.int_(0x1A)              # BIOS tick -> dx
    a.ld_ax('seed'); a.raw(0x31, 0xD0)            # xor ax,dx
    a.st_ax('seed')
    a.raw(0x58)                                   # pop ax
    a.ret()

    # ---- data ----
    a.label('attr'); a.raw(0x07)
    a.label('seed'); a.w(0x1234)

    def s(lbl, text):
        a.label(lbl); a.raw(*(text.encode('ascii') + b'\0'))

    s('banner', BANNER)
    s('devam', DEVAM)
    s('nl2', NL + NL)
    s('t_fikra', NL + "   === GUNUN FIKRASI ===" + NL + NL + "   ")
    s('t_soz', NL + "   === MOTIVASYON ===" + NL + NL + "   ")
    s('t_yemek', NL + "   === BUGUN NE YESEM? ===" + NL + NL + "   Oneri: ")
    s('t_zar', NL + "   === ZAR ===" + NL + NL + "   Zar: ")
    s('t_surpriz', NL + "   === SURPRIZ! ===" + NL + NL)

    def table(lbl, items, prefix):
        for i, t in enumerate(items):
            s(f'{lbl}_{i}', t)
        a.label(lbl)
        for i in range(len(items)):
            a.ref_abs(f'{lbl}_{i}')

    table('tb_fikra', FIKRALAR, '')
    table('tb_soz', SOZLER, '')
    table('tb_yemek', YEMEKLER, '')
    return a.finish()


def bootsector(nsec):
    a = Asm(0x7C00)
    a.raw(0xFA)                                    # cli
    a.raw(0x31, 0xC0)                              # xor ax,ax
    a.raw(0x8E, 0xD8); a.raw(0x8E, 0xC0); a.raw(0x8E, 0xD0)  # ds,es,ss = 0
    a.mov_r16(SP, 0x7C00)
    a.raw(0xFB)                                    # sti
    a.st_dl('drive')
    a.mov_r8(AH, 0x02); a.mov_r8(AL, nsec)
    a.mov_r8(CH, 0x00); a.mov_r8(CL, 0x02); a.mov_r8(DH, 0x00)
    a.ld_dl('drive')
    a.mov_r16(BX, KBASE)
    a.int_(0x13)
    a.jmp('far')                                   # (no error checking; kept simple)
    a.label('far')
    a.raw(0xEA); a.w(KBASE); a.w(0x0000)           # jmp 0000:7E00
    a.label('drive'); a.raw(0x00)
    code = a.finish()
    assert len(code) < 510
    return code.ljust(510, b'\0') + b'\x55\xAA'


if __name__ == '__main__':
    k = kernel()
    nsec = math.ceil(len(k) / 512)
    assert nsec <= 17
    img = bootsector(nsec) + k.ljust(nsec * 512, b'\0')
    img = img.ljust(1474560, b'\0')                # 1.44MB floppy
    open('XenonOS.img', 'wb').write(img)
    print(f'XenonOS.img ready: kernel {len(k)} bytes, {nsec} sectors')
