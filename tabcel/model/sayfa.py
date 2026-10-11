"""Hücre, Sayfa, Çalışma Kitabı: seyrek (yalnızca dolu hücreler saklanır). Qt yok.

Formül başvurularının satır/sütun ekle-sil sonrası düzeltilmesi Faz 2'dedir;
burada yalnızca hücreler ve boyutlar kaydırılır.
"""
from dataclasses import dataclass, replace
from typing import Any, Callable, Dict, Iterator, List, Optional, Set, Tuple, Union

from .ad import TanimliAd, ad_anahtari
from .adres import MAX_COL, MAX_ROW, AdresHatasi, Aralik, aralik_kaydir
from .deger import Deger
from .olay import Olay
from .sayfa_yapisi import SayfaYapisi
from .stil import Stil, StilHavuzu

Anahtar = Tuple[int, int]


@dataclass(frozen=True, eq=False)
class Hucre:
    """Değişmez hücre = kullanıcının GİRDİSİ: ya sabit bir `deger` ya da bir `formul` (kanonik
    İngilizce, '=' ile başlar) — ikisi birlikte olamaz. Formülün hesaplanmış sonucu burada değil,
    `Sayfa.sonuc_ata` ile ayrı depoda tutulur: böylece geri al yalnızca girdiyi geri yükler, yeniden
    hesaplama hücre nesnelerini yeniden yazmaz.

    Eşitlik değerin TÜRÜNÜ de karşılaştırır: Python'da `True == 1.0` doğrudur, ama Excel'de
    DOĞRU ile 1 farklı değerlerdir (aksi halde 1 olan hücreye DOĞRU yazmak 'değişmedi' sayılırdı).
    """
    deger: Deger = None
    formul: Optional[str] = None

    def __post_init__(self):
        if self.formul is not None and self.deger is not None:
            raise ValueError("Hucre ya sabit değer ya da formül taşır; sonuç Sayfa'da tutulur")

    def _anahtar(self):
        return (self.deger.__class__, self.deger, self.formul)

    def __eq__(self, diger):
        if self is diger:
            return True
        if not isinstance(diger, Hucre):
            return NotImplemented
        a, b = self.deger, diger.deger
        # `_anahtar()` ile aynı anlam, demet kurmadan (sıralama/toplu yazımda yüz binlerce çağrı)
        return (self.formul == diger.formul and a.__class__ is b.__class__
                and (a is b or a == b))

    def __hash__(self):
        return hash(self._anahtar())

    def bos_mu(self) -> bool:
        return self.deger is None and self.formul is None


class Sayfa:
    VARSAYILAN_SUTUN_GENISLIGI = 64   # px, 100% yakınlaştırmada
    VARSAYILAN_SATIR_YUKSEKLIGI = 20

    def __init__(self, ad: str, havuz: Optional[StilHavuzu] = None):
        self.ad = ad
        self.havuz: StilHavuzu = havuz if havuz is not None else StilHavuzu()
        self._stil: Dict[Anahtar, int] = {}          # hücre → stil kimliği (açık kayıt; 0 yalnız satır/sütun stilini ezmek için)
        self.satir_stil: Dict[int, int] = {}         # tam satır biçimi
        self.sutun_stil: Dict[int, int] = {}         # tam sütun biçimi
        self.kitap: Optional["CalismaKitabi"] = None   # bağlı olduğu kitap (olaylar buradan yayılır)
        self.kimlik: int = 0                         # kitapta benzersiz, yeniden adlandırma/taşımayla değişmez
        self._hucreler: Dict[Anahtar, Hucre] = {}
        self.sutun_genislik: Dict[int, int] = {}
        self.satir_yukseklik: Dict[int, int] = {}
        self.gizli_sutun: Set[int] = set()
        self.gizli_satir: Set[int] = set()
        self.sekme_rengi: Optional[str] = None     # '#rrggbb' ya da None
        self._kul: Optional[Tuple[int, int, int, int]] = None   # kullanılan aralık önbelleği
        self._sonuc: Dict[Anahtar, Deger] = {}     # formüllerin hesaplanmış sonuçları (girdi değil)
        self.dondur: Optional[Tuple[int, int]] = None   # kaydırılabilir bölgenin sol üst hücresi; None = dondurma yok
        self.kilavuz: bool = True                  # kılavuz çizgileri görünür mü
        self.sayfa_sonlari: bool = False           # ekranda sayfa sınırı çizgileri (T9; dosyaya yazılmaz)
        self.sayfa_yapisi = SayfaYapisi()           # yazdırma ayarları (Faz 4 / 4d)
        self.birlesimler: List[Aralik] = []        # birleştirilmiş hücre aralıkları (çakışmaz, ≥ 2 hücre)
        self._birlesim_idx: Dict[Anahtar, Aralik] = {}   # birleşimin kapsadığı her hücre → aralığı
        # Faz 5 ek verileri (faz5_tasarim.md §1.3): değişmez nesneler; tür modülleri 5e–5h'de gelir.
        # Dogrulama/KosulluKural `araliklar` (Aralik demeti), Filtre `aralik` + `kosullar` {sütun: koşul} taşır
        self.notlar: Dict[Anahtar, Any] = {}
        self.dogrulamalar: List[Any] = []
        self.kosullu: List[Any] = []                # liste sırası = öncelik (0 en yüksek)
        self.filtre: Optional[Any] = None           # sayfa başına en çok bir otomatik filtre
        self.silinen_notlar: Dict[Anahtar, Any] = {}   # son satır/sütun silmede düşen notlar (bilgi)
        # Faz 6 (faz6_tasarim.md §1): yüzen nesneler (Grafik | Resim); liste sırası = z sırası (son en üstte)
        self.nesneler: List[Any] = []
        self._sonraki_nesne = 1                    # kimlik sayacı: asla yeniden kullanılmaz

    # --- okuma / yazma ---
    def hucre(self, satir: int, sutun: int) -> Optional[Hucre]:
        return self._hucreler.get((satir, sutun))

    def deger(self, satir: int, sutun: int) -> Deger:
        """Hücrenin GÖRÜNEN değeri: sabit girdi ya da formülün hesaplanmış sonucu (yoksa None)."""
        h = self._hucreler.get((satir, sutun))
        if h is None:
            return None
        return h.deger if h.formul is None else self._sonuc.get((satir, sutun))

    def sonuc_ata(self, satir: int, sutun: int, deger: Deger) -> None:
        """Formül hücresinin hesaplanmış sonucunu yazar (None = sonuç yok). Geri al yığınına girmez:
        sonuç girdiden türetilir. Formülü olmayan hücreye sonuç yazılamaz."""
        h = self._hucreler.get((satir, sutun))
        if h is None or h.formul is None:
            raise ValueError("Sonuç yalnızca formül hücresine yazılabilir")
        if deger is None:
            self._sonuc.pop((satir, sutun), None)
        else:
            self._sonuc[(satir, sutun)] = deger
        self._bildir("sonuc", anahtar=(satir, sutun), deger=deger,
                     degisiklikler={(satir, sutun): deger})

    def sonuclari_yaz(self, sonuclar: Dict[Anahtar, Deger]) -> None:
        """Formül motorunun toplu sonuç yazımı: TEK `sonuc` olayı (`degisiklikler`). Formülü
        olmayan hücrelerin sonucu yazılmaz (motor bayat bir anahtar verirse sessizce atlanır)."""
        hucreler, depo = self._hucreler, self._sonuc
        yazilan = {}
        for anahtar, deger in sonuclar.items():
            h = hucreler.get(anahtar)
            if h is None or h.formul is None:
                continue
            if deger is None:
                depo.pop(anahtar, None)
            else:
                depo[anahtar] = deger
            yazilan[anahtar] = deger
        if yazilan:
            self._bildir("sonuc", degisiklikler=yazilan)

    def sonuc(self, satir: int, sutun: int) -> Deger:
        return self._sonuc.get((satir, sutun))

    def _yaz(self, satir: int, sutun: int, hucre: Optional[Hucre]):
        """Olay yaymadan yazar. Döner: (eski, yeni_normallestirilmis, degisti)."""
        if not (1 <= satir <= MAX_ROW and 1 <= sutun <= MAX_COL):
            raise AdresHatasi(f"Hücre aralık dışı: ({satir}, {sutun})")
        eski = self._hucreler.get((satir, sutun))
        yeni_h = None if hucre is None or hucre.bos_mu() else hucre
        degisti = eski is not yeni_h and eski != yeni_h
        if degisti:
            self._sonuc.pop((satir, sutun), None)     # girdi değişti: eski sonuç geçersiz
        if yeni_h is None:
            if eski is not None:
                del self._hucreler[(satir, sutun)]
                kul = self._kul
                if kul and (satir in (kul[0], kul[2]) or sutun in (kul[1], kul[3])):
                    self._kul = None             # sınırdaki hücre silindi: yeniden hesaplanır
        else:
            self._hucreler[(satir, sutun)] = yeni_h
            kul = self._kul
            if kul:
                self._kul = (min(kul[0], satir), min(kul[1], sutun),
                             max(kul[2], satir), max(kul[3], sutun))
        return eski, yeni_h, degisti

    def ata(self, satir: int, sutun: int, hucre: Optional[Hucre]) -> Optional[Hucre]:
        """Hücreyi yazar (None/boş = siler); eski hücreyi döndürür. Değiştiyse bir `hucre` olayı yayar."""
        eski, yeni_h, degisti = self._yaz(satir, sutun, hucre)
        if degisti:
            self._bildir("hucre", degisiklikler={(satir, sutun): (eski, yeni_h)})
        return eski

    def toplu_yaz(self, yeni: Dict[Anahtar, Optional[Hucre]]) -> Dict[Anahtar, Optional[Hucre]]:
        """Birçok hücreyi yazar ve TEK `hucre` olayı yayar (100.000 hücrede olay maliyeti sabit kalır).
        Döner: {anahtar: eski hücre} (verilen her anahtar için)."""
        hucreler, sonuclar = self._hucreler, self._sonuc
        eskiler: Dict[Anahtar, Optional[Hucre]] = {}
        degisenler = {}
        for anahtar, hucre in yeni.items():
            satir, sutun = anahtar
            if not (1 <= satir <= MAX_ROW and 1 <= sutun <= MAX_COL):
                raise AdresHatasi(f"Hücre aralık dışı: ({satir}, {sutun})")
            eski = hucreler.get(anahtar)
            eskiler[anahtar] = eski
            yeni_h = None if hucre is None or (hucre.deger is None and hucre.formul is None) else hucre
            if eski is yeni_h or (eski is not None and yeni_h is not None and eski == yeni_h):
                continue
            degisenler[anahtar] = (eski, yeni_h)
            if sonuclar:
                sonuclar.pop(anahtar, None)           # girdi değişti: eski sonuç geçersiz
            if yeni_h is None:
                del hucreler[anahtar]
            else:
                hucreler[anahtar] = yeni_h
        if degisenler:
            kul = self._kul
            if kul is not None:
                if len(degisenler) > 256:
                    self._kul = None                  # çok hücre: bir kez geçersiz kıl, ilk kullanımda hesaplansın
                else:
                    for (satir, sutun), (_, yeni_h) in degisenler.items():
                        kul = self._kul
                        if kul is None:
                            break
                        if yeni_h is None:
                            if satir in (kul[0], kul[2]) or sutun in (kul[1], kul[3]):
                                self._kul = None
                        else:
                            self._kul = (min(kul[0], satir), min(kul[1], sutun),
                                         max(kul[2], satir), max(kul[3], sutun))
            self._bildir("hucre", degisiklikler=degisenler)
        return eskiler

    def _bildir(self, tur: str, **ayrinti) -> None:
        """Kitaba bağlıysa değişiklik olayı yayar (kitapsız sayfada sessizce geçer)."""
        if self.kitap is not None:
            self.kitap._olay_yay(Olay(tur, self, ayrinti))

    def dolu_hucreler(self, sirali: bool = True) -> Iterator[Tuple[int, int, Hucre]]:
        """Dolu hücreler. Sıra gerekmiyorsa `sirali=False` (100.000 hücrede sıralama pahalıdır)."""
        ogeler = sorted(self._hucreler.items()) if sirali else self._hucreler.items()
        for (s, c), h in ogeler:
            yield s, c, h

    def aralikta(self, ar: Aralik) -> Iterator[Tuple[int, int, Hucre]]:
        """Aralıktaki dolu hücreler (sırasız). Küçük aralıkta aralığı, büyükte sözlüğü gezer."""
        alan = (ar.son_satir - ar.ilk_satir + 1) * (ar.son_sutun - ar.ilk_sutun + 1)
        hucreler = self._hucreler
        if alan <= len(hucreler):
            for r in range(ar.ilk_satir, ar.son_satir + 1):
                for c in range(ar.ilk_sutun, ar.son_sutun + 1):
                    h = hucreler.get((r, c))
                    if h is not None:
                        yield r, c, h
        else:
            r1, c1, r2, c2 = ar.ilk_satir, ar.ilk_sutun, ar.son_satir, ar.son_sutun
            for (r, c), h in hucreler.items():
                if r1 <= r <= r2 and c1 <= c <= c2:
                    yield r, c, h

    # --- stil (biçim) ---
    def ham_stil_kimligi(self, satir: int, sutun: int) -> Optional[int]:
        """Hücrenin KENDİ stil kaydı (satır/sütun stiline düşmeden); kayıt yoksa None."""
        return self._stil.get((satir, sutun))

    def stil_kimligi(self, satir: int, sutun: int) -> int:
        """Etkin stil kimliği: hücre → satır → sütun → 0 (varsayılan)."""
        k = self._stil.get((satir, sutun))
        if k is not None:
            return k
        k = self.satir_stil.get(satir)
        if k is not None:
            return k
        return self.sutun_stil.get(sutun, 0)

    def stil(self, satir: int, sutun: int) -> Stil:
        return self.havuz.stil(self.stil_kimligi(satir, sutun))

    def bicim_yaz(self, hucreler: Optional[Dict[Anahtar, Optional[int]]] = None,
                  satirlar: Optional[Dict[int, Optional[int]]] = None,
                  sutunlar: Optional[Dict[int, Optional[int]]] = None):
        """Ham stil kayıtlarını yazar ve değişen varsa TEK `bicim` olayı yayar. Değer None = kaydı sil.
        Satır/sütun değeri 0 ya da None kaydı siler; hücre değeri 0 yalnız bir satır/sütun stili varsa
        açıkça saklanır (varsayılana dönmek için), yoksa kayıt silinir. Döner: (eski_hucreler,
        eski_satirlar, eski_sutunlar) — verilen her anahtar için eski ham kayıt (None = yoktu); aynen
        `bicim_yaz(*eskiler)` ile geri yüklenir."""
        eski_s: Dict[int, Optional[int]] = {}
        eski_su: Dict[int, Optional[int]] = {}
        eski_h: Dict[Anahtar, Optional[int]] = {}
        olay_s, olay_su, olay_h = {}, {}, {}
        for depo, yeni, eski, olay, sinir in ((self.satir_stil, satirlar, eski_s, olay_s, MAX_ROW),
                                              (self.sutun_stil, sutunlar, eski_su, olay_su, MAX_COL)):
            for k, v in (yeni or {}).items():
                if not 1 <= k <= sinir:
                    raise AdresHatasi(f"Satır/sütun aralık dışı: {k}")
                eski[k] = depo.get(k)
                v = v or None
                if v is None:
                    depo.pop(k, None)
                else:
                    depo[k] = v
                if eski[k] != v:
                    olay[k] = (eski[k], v)
        for anahtar, v in (hucreler or {}).items():
            r, c = anahtar
            if not (1 <= r <= MAX_ROW and 1 <= c <= MAX_COL):
                raise AdresHatasi(f"Hücre aralık dışı: ({r}, {c})")
            eski_h[anahtar] = e = self._stil.get(anahtar)
            if v == 0 and r not in self.satir_stil and c not in self.sutun_stil:
                v = None
            if v is None:
                self._stil.pop(anahtar, None)
            else:
                self._stil[anahtar] = v
            if e != v:
                olay_h[anahtar] = (e, v)
        if olay_h or olay_s or olay_su:
            self._bildir("bicim", degisiklikler=olay_h, satir=olay_s, sutun=olay_su)
        return eski_h, eski_s, eski_su

    def stilleri_yaz(self, yeni: Dict[Anahtar, Optional[int]]) -> Dict[Anahtar, Optional[int]]:
        return self.bicim_yaz(hucreler=yeni)[0]

    def satir_stili_yaz(self, yeni: Dict[int, Optional[int]]) -> Dict[int, Optional[int]]:
        return self.bicim_yaz(satirlar=yeni)[1]

    def sutun_stili_yaz(self, yeni: Dict[int, Optional[int]]) -> Dict[int, Optional[int]]:
        return self.bicim_yaz(sutunlar=yeni)[2]

    def havuza_gec(self, havuz: StilHavuzu) -> None:
        """Sayfa başka bir kitaba bağlanırken stil kimliklerini yeni havuza çevirir."""
        if havuz is self.havuz:
            return
        eski = self.havuz
        self._stil = {k: havuz.aktar(eski, v) for k, v in self._stil.items()}
        self.satir_stil = {k: havuz.aktar(eski, v) for k, v in self.satir_stil.items()}
        self.sutun_stil = {k: havuz.aktar(eski, v) for k, v in self.sutun_stil.items()}
        self.havuz = havuz

    def bicim_silinecek(self, eksen: int, nerede: int, adet: int):
        """Silinecek bantta (`nerede`…`nerede+adet-1`) kalan ham stil kayıtları (silmeyi geri almak için):
        ({anahtar: kimlik}, {satır: kimlik}, {sütun: kimlik}). Önce çağrılır, sonra silinir."""
        son = nerede + adet - 1
        hucre = {k: v for k, v in self._stil.items() if nerede <= k[eksen] <= son}
        satir = {k: v for k, v in self.satir_stil.items() if eksen == 0 and nerede <= k <= son}
        sutun = {k: v for k, v in self.sutun_stil.items() if eksen == 1 and nerede <= k <= son}
        return hucre, satir, sutun

    def bicim_geri_koy(self, eksen: int, nerede: int, adet: int, durum) -> None:
        """Silmeyi geri alırken: boş açılan bandın (ekleme sırasında üstten devralınan) stillerini temizler,
        silinen stilleri aynen geri yazar. TEK `bicim` olayı."""
        son = nerede + adet - 1
        hucre, satir, sutun = durum
        yeni_h = {k: None for k in self._stil if nerede <= k[eksen] <= son}
        yeni_h.update(hucre)
        yeni_s = {k: None for k in self.satir_stil if eksen == 0 and nerede <= k <= son}
        yeni_s.update(satir)
        yeni_su = {k: None for k in self.sutun_stil if eksen == 1 and nerede <= k <= son}
        yeni_su.update(sutun)
        self.bicim_yaz(yeni_h, yeni_s, yeni_su)

    def kullanilan_aralik(self, bicim_dahil: bool = False) -> Optional[Tuple[int, int, int, int]]:
        """(ilk_satir, ilk_sutun, son_satir, son_sutun) ya da sayfa boşsa None. `bicim_dahil=True`:
        biçimli boş hücreler de sayılır (Ctrl+End, yazdırma, .xlsx boyutu); tam satır/sütun stilleri
        sayılmaz (sayfayı sonsuza uzatırdı). Varsayılan (içerik tabanlı) önbelleklidir."""
        if bicim_dahil and self._stil:
            icerik = self.kullanilan_aralik()
            satirlar = [k[0] for k in self._stil]
            sutunlar = [k[1] for k in self._stil]
            kutu = (min(satirlar), min(sutunlar), max(satirlar), max(sutunlar))
            if icerik is None:
                return kutu
            return (min(icerik[0], kutu[0]), min(icerik[1], kutu[1]),
                    max(icerik[2], kutu[2]), max(icerik[3], kutu[3]))
        if not self._hucreler:
            return None
        if self._kul is None:
            satirlar = [k[0] for k in self._hucreler]
            sutunlar = [k[1] for k in self._hucreler]
            self._kul = (min(satirlar), min(sutunlar), max(satirlar), max(sutunlar))
        return self._kul

    # --- boyutlar ---
    def genislik(self, sutun: int) -> int:
        """Görünen genişlik; gizli sütun için 0 (özgün genişlik saklı kalır)."""
        if sutun in self.gizli_sutun:
            return 0
        return self.sutun_genislik.get(sutun, self.VARSAYILAN_SUTUN_GENISLIGI)

    def yukseklik(self, satir: int) -> int:
        if satir in self.gizli_satir:
            return 0
        return self.satir_yukseklik.get(satir, self.VARSAYILAN_SATIR_YUKSEKLIGI)

    def boyut_durumu(self):
        """Boyut + gizleme durumunun kopyası (geri al için)."""
        return (dict(self.sutun_genislik), dict(self.satir_yukseklik),
                set(self.gizli_sutun), set(self.gizli_satir))

    def boyut_durumu_yukle(self, durum) -> None:
        g, y, gs, gr = durum
        self.sutun_genislik, self.satir_yukseklik = dict(g), dict(y)
        self.gizli_sutun, self.gizli_satir = set(gs), set(gr)
        self._bildir("boyut")

    # --- görünüm: dondurulmuş bölmeler, kılavuz çizgileri (faz3_tasarim.md §4) ---
    def gorunum_yaz(self, dondur="AYNI", kilavuz="AYNI", sayfa_sonlari="AYNI") -> bool:
        """Dondurma konumu `(satır, sütun)` (kaydırılabilir bölgenin sol üstü; `(1, 1)`/None = dondurma yok)
        ve kılavuz çizgisi durumunu yazar. Geri al yığınına GİRMEZ (Excel'de de geri alınamaz); değişirse
        `bicim` olayı `gorunum` ile yayılır. Döner: değişti mi."""
        degisti = {}
        if not isinstance(dondur, str):
            if dondur is not None:
                r, c = dondur
                if not (1 <= r <= MAX_ROW and 1 <= c <= MAX_COL):
                    raise AdresHatasi(f"Dondurma konumu aralık dışı: {dondur}")
                dondur = None if (r, c) == (1, 1) else (int(r), int(c))
            if dondur != self.dondur:
                self.dondur = dondur
                degisti["dondur"] = dondur
        if not isinstance(kilavuz, str) and bool(kilavuz) != self.kilavuz:
            self.kilavuz = bool(kilavuz)
            degisti["kilavuz"] = self.kilavuz
        sb_degisti = False
        if not isinstance(sayfa_sonlari, str) and bool(sayfa_sonlari) != self.sayfa_sonlari:
            self.sayfa_sonlari = bool(sayfa_sonlari)       # dosyaya yazılmaz: belgeyi "değişti" yapmaz (bicim olayı yok)
            sb_degisti = True
            self._bildir("yazdirma", gorunum=True)
        if degisti:
            self._bildir("bicim", degisiklikler={}, satir={}, sutun={}, gorunum=degisti)
        return bool(degisti) or sb_degisti

    def yazdirma_yaz(self, yapi) -> None:
        """Yazdırma ayarlarını yazar ve `yazdirma` olayı yayar (ızgara sayfa sınırı çizgileri yenilensin)."""
        if yapi != self.sayfa_yapisi:
            self.sayfa_yapisi = yapi
            self._bildir("yazdirma")

    # --- birleştirilmiş hücreler (faz3_tasarim.md §3) ---
    def birlesim(self, satir: int, sutun: int) -> Optional[Aralik]:
        """Hücreyi kapsayan birleşim (sol üst hücre dahil); yoksa None."""
        return self._birlesim_idx.get((satir, sutun)) if self._birlesim_idx else None

    def birlesim_kesisen(self, ar: Aralik) -> List[Aralik]:
        """`ar` ile kesişen birleşimler."""
        return [b for b in self.birlesimler
                if b.ilk_satir <= ar.son_satir and b.son_satir >= ar.ilk_satir
                and b.ilk_sutun <= ar.son_sutun and b.son_sutun >= ar.ilk_sutun]

    def _birlesim_kur(self, liste: List[Aralik]) -> None:
        self.birlesimler = list(liste)
        idx: Dict[Anahtar, Aralik] = {}
        for b in self.birlesimler:
            for r in range(b.ilk_satir, b.son_satir + 1):
                for c in range(b.ilk_sutun, b.son_sutun + 1):
                    idx[(r, c)] = b
        self._birlesim_idx = idx

    def birlesimleri_yaz(self, ekle: List[Aralik], kaldir: List[Aralik]) -> None:
        """Birleşimleri kaldırır ve ekler (TEK `bicim` olayı, `birlesim=(ekle, kaldir)`). Eklenen birleşim
        en az 2 hücre olmalı, sayfa sınırları içinde kalmalı, kalan birleşimlerle ya da birbiriyle
        çakışmamalı; kaldırılan birleşim var olmalı. Hatada ValueError, sayfa değişmez."""
        mevcut = list(self.birlesimler)
        for k in kaldir:
            if k not in mevcut:
                raise ValueError(f"Böyle bir birleşim yok: {k}")
            mevcut.remove(k)
        for e in ekle:
            if not (1 <= e.ilk_satir <= e.son_satir <= MAX_ROW and 1 <= e.ilk_sutun <= e.son_sutun <= MAX_COL):
                raise AdresHatasi(f"Birleşim sayfa dışında: {e}")
            if e.ilk_satir == e.son_satir and e.ilk_sutun == e.son_sutun:
                raise ValueError("Birleşim en az iki hücre olmalı")
            for m in mevcut:
                if (m.ilk_satir <= e.son_satir and m.son_satir >= e.ilk_satir
                        and m.ilk_sutun <= e.son_sutun and m.son_sutun >= e.ilk_sutun):
                    raise ValueError("Birleşim başka bir birleşimle çakışıyor")
            mevcut.append(e)
        if not ekle and not kaldir:
            return
        self._birlesim_kur(mevcut)
        self._bildir("bicim", degisiklikler={}, satir={}, sutun={},
                     birlesim=(list(ekle), list(kaldir)))

    def birlesim_durumu(self) -> List[Aralik]:
        return list(self.birlesimler)

    def birlesim_yukle(self, liste: List[Aralik]) -> None:
        """Birleşim listesini aynen yükler (satır/sütun ekle-sil geri alınırken)."""
        eski = list(self.birlesimler)
        if eski == list(liste):
            return
        self._birlesim_kur(liste)
        self._bildir("bicim", degisiklikler={}, satir={}, sutun={},
                     birlesim=([b for b in liste if b not in eski], [b for b in eski if b not in liste]))

    def _birlesimleri_kaydir(self, eksen: int, nerede: int, fark: int, sinir: int) -> None:
        """Ekle-sil sonrası birleşimler: birleşimin içine ekleme büyütür, silme küçültür, tamamen silinen
        (ya da tek hücreye inen) kalkar (Excel gibi)."""
        if not self.birlesimler:
            return
        yeni = []
        for b in self.birlesimler:
            ar = aralik_kaydir(b, eksen, nerede, fark, sinir)
            if ar is None or (ar.ilk_satir == ar.son_satir and ar.ilk_sutun == ar.son_sutun):
                continue
            yeni.append(ar)
        self._birlesim_kur(yeni)

    # --- Faz 5 ek verileri: notlar, doğrulama, koşullu biçim, filtre ---
    def ek_durumu(self):
        """Ek verilerin anlık görüntüsü (geri al için): `(notlar, dogrulamalar, kosullu, filtre)`.
        Öğeler değişmez nesnelerdir; sığ kopya yeter."""
        return (dict(self.notlar), list(self.dogrulamalar), list(self.kosullu), self.filtre)

    def ek_durumu_yukle(self, durum) -> None:
        """`ek_durumu` görüntüsünü aynen yükler; değişen varsa TEK `ek` olayı (`alan="hepsi"`)."""
        notlar, dogrulamalar, kosullu, filtre = durum
        degisti = (self.notlar != notlar or self.dogrulamalar != dogrulamalar
                   or self.kosullu != kosullu or self.filtre != filtre)
        eski_notlar = self.notlar
        self.notlar = dict(notlar)
        self.dogrulamalar = list(dogrulamalar)
        self.kosullu = list(kosullu)
        self.filtre = filtre
        if degisti:
            self._bildir("ek", alan="hepsi", anahtarlar=set(eski_notlar) | set(notlar))

    # --- Faz 6: yüzen nesneler (grafik, resim) ---
    def nesne(self, kimlik: int):
        """Kimliğe göre nesne (yoksa None)."""
        for n in self.nesneler:
            if n.kimlik == kimlik:
                return n
        return None

    def nesne_ekle(self, nesne, indeks: Optional[int] = None):
        """Nesneyi ekler (`indeks` None = en üste). `kimlik == 0` ise yeni kimlik atanır; dolu kimlik (geri alma,
        yükleme) korunur ve çakışırsa ValueError. Döner: sayfada saklanan nesne. TEK `nesne` olayı."""
        if nesne.kimlik == 0:
            nesne = nesne.degistir(kimlik=self._sonraki_nesne)
        elif self.nesne(nesne.kimlik) is not None:
            raise ValueError(f"nesne kimliği zaten var: {nesne.kimlik}")
        self._sonraki_nesne = max(self._sonraki_nesne, nesne.kimlik + 1)
        if indeks is None or indeks > len(self.nesneler):
            indeks = len(self.nesneler)
        self.nesneler.insert(max(0, indeks), nesne)
        self._bildir("nesne", islem="ekle", kimlik=nesne.kimlik)
        return nesne

    def nesne_sil(self, kimlik: int):
        """Nesneyi siler. Döner: `(nesne, indeks)` (geri alırken `nesne_ekle(nesne, indeks)`)."""
        for i, n in enumerate(self.nesneler):
            if n.kimlik == kimlik:
                del self.nesneler[i]
                self._bildir("nesne", islem="sil", kimlik=kimlik)
                return n, i
        raise KeyError(f"nesne yok: {kimlik}")

    def nesne_degistir(self, yeni):
        """Aynı kimlikli nesneyi yenisiyle değiştirir (tür aynı kalmalı). Döner: eski nesne; değişen yoksa
        olay yayılmaz."""
        for i, n in enumerate(self.nesneler):
            if n.kimlik == yeni.kimlik:
                if type(n) is not type(yeni):
                    raise ValueError("nesne türü değiştirilemez")
                if n == yeni:
                    return n
                self.nesneler[i] = yeni
                self._bildir("nesne", islem="degis", kimlik=yeni.kimlik)
                return n
        raise KeyError(f"nesne yok: {yeni.kimlik}")

    def nesne_sirala(self, kimlik: int, indeks: int) -> int:
        """Nesneyi z sırasında `indeks` konumuna taşır (0 = en altta). Döner: eski indeks."""
        for i, n in enumerate(self.nesneler):
            if n.kimlik == kimlik:
                indeks = max(0, min(indeks, len(self.nesneler) - 1))
                if indeks != i:
                    del self.nesneler[i]
                    self.nesneler.insert(indeks, n)
                    self._bildir("nesne", islem="sira", kimlik=kimlik)
                return i
        raise KeyError(f"nesne yok: {kimlik}")

    def nesne_durumu(self):
        """Nesnelerin anlık görüntüsü (geri al için; öğeler değişmez → sığ kopya). `ek_durumu`ndan ayrıdır:
        o demet 4'lü kalır."""
        return list(self.nesneler)

    def nesne_durumu_yukle(self, liste) -> None:
        """`nesne_durumu` görüntüsünü aynen yükler; değişen varsa TEK `nesne` olayı (`islem="hepsi"`)."""
        if list(liste) == self.nesneler:
            return
        self.nesneler = list(liste)
        for n in self.nesneler:
            self._sonraki_nesne = max(self._sonraki_nesne, n.kimlik + 1)
        self._bildir("nesne", islem="hepsi", kimlik=None)

    def nesne_baglari_yaz(self, liste) -> bool:
        """Başvuruları kitap düzeyinde düzeltilmiş nesne listesini yazar (`komutlar` ekle-sil); değişen varsa
        TEK `nesne` olayı (`islem="hepsi"`). Döner: değişti mi."""
        if list(liste) == self.nesneler:
            return False
        self.nesneler = list(liste)
        self._bildir("nesne", islem="hepsi", kimlik=None)
        return True

    def _nesneleri_kaydir(self, eksen: int, nerede: int, fark: int, sinir: int) -> None:
        """Ekle-sil sonrası nesnelerin ÇAPA hücreleri kayar (olay yok: aynı işlemin `yapi` olayı gelir).
        Başvurular (seriler) kitap düzeyinde `komutlar._SatirSutun`da düzelir."""
        if not self.nesneler:
            return
        from .grafik import konum_kaydir
        self.nesneler = [n.degistir(konum=konum_kaydir(n.konum, eksen, nerede, fark, sinir))
                         for n in self.nesneler]

    def kosullulari_yaz(self, liste) -> None:
        """Koşullu biçim kural listesini aynen yazar (sıra = öncelik); değişirse `ek` olayı (`alan="kosullu"`)."""
        if list(liste) == self.kosullu:
            return
        self.kosullu = list(liste)
        self._bildir("ek", alan="kosullu")

    def dogrulama(self, satir: int, sutun: int):
        """Hücrenin veri doğrulama kuralı (yoksa None). Kural sayısı küçüktür: doğrusal tarama."""
        if not self.dogrulamalar:
            return None
        from .dogrulama import kural_ara
        return kural_ara(self.dogrulamalar, satir, sutun)

    def dogrulamalari_yaz(self, liste) -> None:
        """Kural listesini aynen yazar; değişirse `ek` olayı (`alan="dogrulama"`)."""
        if list(liste) == self.dogrulamalar:
            return
        self.dogrulamalar = list(liste)
        self._bildir("ek", alan="dogrulama")

    def filtre_yaz(self, filtre) -> None:
        """Otomatik filtreyi değiştirir (None = kaldır); değişirse `ek` olayı (`alan="filtre"`).
        Satır gizliliği ayrıca `gizli_satir` + `boyut_degisti` ile yazılır (`komutlar.FiltreDegis`)."""
        if self.filtre == filtre:
            return
        self.filtre = filtre
        self._bildir("ek", alan="filtre")

    def notlari_yaz(self, yeni: Dict[Anahtar, Any]) -> Dict[Anahtar, Any]:
        """Notları toplu değiştirir (`None` ya da boş `Not` = sil); değişen varsa TEK `ek` olayı
        (`alan="not"`, `anahtarlar`). Döner: değişen hücrelerin ESKİ notları (None = yoktu) — geri al
        için `notlari_yaz(eskiler)`."""
        eski: Dict[Anahtar, Any] = {}
        for anahtar, n in yeni.items():
            if n is not None and n.bos_mu():
                n = None
            simdiki = self.notlar.get(anahtar)
            if simdiki == n:
                continue
            eski[anahtar] = simdiki
            if n is None:
                del self.notlar[anahtar]
            else:
                self.notlar[anahtar] = n
        if eski:
            self._bildir("ek", alan="not", anahtarlar=set(eski))
        return eski

    def _ekleri_kaydir(self, eksen: int, nerede: int, fark: int, sinir: int) -> None:
        """Ekle-sil sonrası ek veriler: notlar anahtar kaydırır (silinen bant `silinen_notlar`a düşer),
        doğrulama/koşullu biçim aralıkları `aralik_kaydir` ile (aralıksız kalan kural düşer), filtre
        aralığı kayar (başlık satırı silinirse filtre kalkar — Excel). Formül içerikleri (doğrulama,
        koşullu biçim, adlar) burada değil `formul.kaydir.ek_duzeltmeleri`nde düzelir."""
        self.silinen_notlar = {}
        if self.notlar:
            yeni = {}
            for anahtar, n in self.notlar.items():
                k = self._kaydir_indeks(anahtar[eksen], nerede, fark, sinir)
                if k is None:
                    self.silinen_notlar[anahtar] = n
                else:
                    yeni[(k, anahtar[1]) if eksen == 0 else (anahtar[0], k)] = n
            self.notlar = yeni
        for depo in ("dogrulamalar", "kosullu"):
            liste = getattr(self, depo)
            if not liste:
                continue
            yeni_liste = []
            for kural in liste:
                araliklar = tuple(a for a in (aralik_kaydir(x, eksen, nerede, fark, sinir)
                                              for x in kural.araliklar) if a is not None)
                if araliklar:
                    yeni_liste.append(kural if araliklar == tuple(kural.araliklar)
                                      else replace(kural, araliklar=araliklar))
            setattr(self, depo, yeni_liste)
        f = self.filtre
        if f is not None:
            ar = aralik_kaydir(f.aralik, eksen, nerede, fark, sinir)
            bas = f.aralik.ilk_satir
            baslik_silindi = eksen == 0 and fark < 0 and nerede <= bas < nerede - fark
            if ar is None or baslik_silindi:
                self.filtre = None
            else:
                kosullar = getattr(f, "kosullar", {})
                if eksen == 1:
                    kosullar = {k2: v for k, v in kosullar.items()
                                if (k2 := self._kaydir_indeks(k, nerede, fark, sinir)) is not None}
                self.filtre = replace(f, aralik=ar, kosullar=kosullar)

    def boyut_degisti(self) -> None:
        """Boyut sözlükleri doğrudan değiştirildiyse (örn. `OlcuDegis`) olay yayar."""
        self._bildir("boyut")

    # --- satır / sütun ekle-sil ---
    def satir_ekle(self, nerede: int, adet: int = 1) -> None:
        """`nerede` satırından itibaren `adet` boş satır açar (aşağıdakiler kayar)."""
        self._kaydir(0, nerede, adet)

    def satir_sil(self, nerede: int, adet: int = 1) -> Dict[Anahtar, Hucre]:
        """Satırları siler, yukarı kaydırır; silinen hücreleri döndürür."""
        return self._kaydir(0, nerede, -adet)

    def sutun_ekle(self, nerede: int, adet: int = 1) -> None:
        self._kaydir(1, nerede, adet)

    def sutun_sil(self, nerede: int, adet: int = 1) -> Dict[Anahtar, Hucre]:
        return self._kaydir(1, nerede, -adet)

    def _kaydir(self, eksen: int, nerede: int, fark: int) -> Dict[Anahtar, Hucre]:
        sinir = MAX_COL if eksen else MAX_ROW
        if not 1 <= nerede <= sinir or fark == 0:
            raise AdresHatasi(f"Geçersiz konum/adet: {nerede}, {fark}")
        kul = self.kullanilan_aralik()
        if fark > 0 and kul and kul[2 + eksen] >= nerede and kul[2 + eksen] + fark > sinir:
            # Excel gibi: dolu hücre sayfanın dışına itilecekse işlem reddedilir (sessiz veri kaybı yok)
            raise AdresHatasi("Sayfanın sonundaki dolu hücreler dışarı itileceği için eklenemiyor")
        silinen: Dict[Anahtar, Hucre] = {}
        yeni: Dict[Anahtar, Hucre] = {}
        for anahtar, h in self._hucreler.items():
            k = anahtar[eksen]
            if k >= nerede:
                if fark < 0 and k < nerede - fark:
                    silinen[anahtar] = h
                    continue
                k += fark
                if k > sinir:          # ekleme sınırın dışına iter: hücre kaybolur
                    continue
                anahtar = (k, anahtar[1]) if eksen == 0 else (anahtar[0], k)
            yeni[anahtar] = h
        self._hucreler = yeni
        self._kul = None
        yeni_sonuc = {}
        for (s, c), v in self._sonuc.items():
            k = self._kaydir_indeks((s, c)[eksen], nerede, fark, sinir)
            if k is not None:
                yeni_sonuc[(k, c) if eksen == 0 else (s, k)] = v
        self._sonuc = yeni_sonuc
        self._stilleri_kaydir(eksen, nerede, fark, sinir)
        self._birlesimleri_kaydir(eksen, nerede, fark, sinir)
        self._ekleri_kaydir(eksen, nerede, fark, sinir)
        self._nesneleri_kaydir(eksen, nerede, fark, sinir)
        self._yapiyi_kaydir(eksen, nerede, fark, sinir)
        olcu = self.sutun_genislik if eksen else self.satir_yukseklik
        yeni_olcu = {}
        for k, v in olcu.items():
            k = self._kaydir_indeks(k, nerede, fark, sinir)
            if k is not None:
                yeni_olcu[k] = v
        olcu.clear()
        olcu.update(yeni_olcu)
        gizli = self.gizli_sutun if eksen else self.gizli_satir
        yeni_gizli = {k2 for k in gizli
                      if (k2 := self._kaydir_indeks(k, nerede, fark, sinir)) is not None}
        gizli.clear()
        gizli.update(yeni_gizli)
        self._bildir("yapi", eksen="sutun" if eksen else "satir", nerede=nerede, fark=fark,
                     silinen=silinen)
        return silinen

    def _yapiyi_kaydir(self, eksen: int, nerede: int, fark: int, sinir: int) -> None:
        """Ekle-sil sonrası yazdırma ayarları (T9): el ile sayfa sonları, yazdırma alanı ve yinelenen başlık
        satırları kayar (Excel gibi); silinen bandın içindeki sayfa sonu düşer, alan tamamen silinirse kalkar."""
        y = self.sayfa_yapisi
        kw = {}
        ad = "sutun_kesmeleri" if eksen else "satir_kesmeleri"
        kesmeler = getattr(y, ad)
        if kesmeler:
            yeni = tuple(k2 for k in kesmeler
                         if (k2 := self._kaydir_indeks(k, nerede, fark, sinir)) is not None and k2 >= 2)
            if yeni != kesmeler:
                kw[ad] = yeni
        if y.alan is not None:
            ar = aralik_kaydir(y.alan, eksen, nerede, fark, sinir)
            if ar != y.alan:
                kw["alan"] = ar
        if eksen == 0 and y.baslik_satirlari is not None:
            a, b = y.baslik_satirlari
            a2 = self._kaydir_indeks(a, nerede, fark, sinir)
            b2 = self._kaydir_indeks(b, nerede, fark, sinir)
            if a2 is None:                              # başlığın ilk satırı silindi: kalan kısım silinen bandın yerinde başlar
                a2 = nerede
            if b2 is None:                              # son satırı silindi: silinen bandın hemen üstünde biter
                b2 = nerede - 1
            yeni_b = (a2, b2) if 1 <= a2 <= b2 else None
            if yeni_b != y.baslik_satirlari:
                kw["baslik_satirlari"] = yeni_b
        if kw:
            self.sayfa_yapisi = y.degistir(**kw)

    def _stilleri_kaydir(self, eksen: int, nerede: int, fark: int, sinir: int) -> None:
        """Ekle-sil sonrası stil kayıtlarını kaydırır. Ekleme: yeni satır/sütun hemen üstündeki
        (solundaki) satırın/sütunun biçimini alır (Excel varsayılanı)."""
        yeni = {}
        for (s, c), v in self._stil.items():
            k = self._kaydir_indeks((s, c)[eksen], nerede, fark, sinir)
            if k is not None:
                yeni[(k, c) if eksen == 0 else (s, k)] = v
        self._stil = yeni
        eksen_depo = self.sutun_stil if eksen else self.satir_stil
        yeni_e = {}
        for k, v in eksen_depo.items():
            k2 = self._kaydir_indeks(k, nerede, fark, sinir)
            if k2 is not None:
                yeni_e[k2] = v
        eksen_depo.clear()
        eksen_depo.update(yeni_e)
        kaynak = nerede - 1
        if fark > 0 and kaynak >= 1:
            yeni_satirlar = [k for k in range(nerede, nerede + fark) if k <= sinir]
            if kaynak in eksen_depo:
                for k in yeni_satirlar:
                    eksen_depo[k] = eksen_depo[kaynak]
            for anahtar, v in [(a, v) for a, v in self._stil.items() if a[eksen] == kaynak]:
                for k in yeni_satirlar:
                    self._stil[(k, anahtar[1]) if eksen == 0 else (anahtar[0], k)] = v

    @staticmethod
    def _kaydir_indeks(k: int, nerede: int, fark: int, sinir: int) -> Optional[int]:
        """Satır/sütun indeksinin ekle-sil sonrası yeni değeri; silinmişse/sınır dışıysa None."""
        if k < nerede:
            return k
        if fark < 0 and k < nerede - fark:
            return None
        k += fark
        return k if k <= sinir else None


SAYFA_ADI_YASAK = set("\\/?*[]:")


def sayfa_adi_dogrula(ad: str) -> None:
    """Excel kuralları: boş olamaz, en çok 31 karakter, ters/düz bölü, ? * [ ] : içeremez,
    başta/sonda kesme işareti olamaz. Geçersizse Türkçe iletiyle ValueError."""
    if not ad.strip():
        raise ValueError("Sayfa adı boş olamaz")
    if len(ad) > 31:
        raise ValueError("Sayfa adı en çok 31 karakter olabilir")
    kotu = sorted(set(ad) & SAYFA_ADI_YASAK)
    if kotu:
        raise ValueError("Sayfa adı şu karakterleri içeremez: " + " ".join(kotu))
    if ad.startswith("'") or ad.endswith("'"):
        raise ValueError("Sayfa adı kesme işaretiyle başlayıp bitemez")


class CalismaKitabi:
    """Sayfaların kabı ve değişiklik olaylarının dağıtıcısı.

    Sayfalar kitaba bağlıdır (`sayfa.kitap`); her sayfaya kitapta benzersiz, kalıcı bir `kimlik`
    verilir (yeniden adlandırma, taşıma ve silme+geri alma boyunca aynı kalır). Formüllerdeki
    sayfa başvuruları bu kimliğe bağlanacak, metinde ad görünecek.
    """

    def __init__(self):
        self.sayfalar: List[Sayfa] = []
        self.stil_havuzu = StilHavuzu()
        self._dinleyiciler: List[Callable[[Olay], None]] = []
        self._sonraki_kimlik = 1
        self.adlar: Dict[Tuple[Optional[int], str], TanimliAd] = {}   # tanımlı adlar (faz5_tasarim.md §4)
        self._baglan(Sayfa("Sayfa1"))

    # --- olaylar ---
    def dinle(self, dinleyici: Callable[[Olay], None]) -> Callable[[], None]:
        """Dinleyici ekler; dinlemeyi bırakmak için dönen işlevi çağırın."""
        self._dinleyiciler.append(dinleyici)

        def birak():
            if dinleyici in self._dinleyiciler:
                self._dinleyiciler.remove(dinleyici)
        return birak

    def _olay_yay(self, olay: Olay) -> None:
        for d in list(self._dinleyiciler):
            d(olay)

    # --- tanımlı adlar (doğrulama/komutlar/arayüz 5d'de; burada depo, arama ve olay) ---
    def ad_bul(self, ad: str, sayfa_kimligi: Optional[int] = None) -> Optional[TanimliAd]:
        """Önce `sayfa_kimligi` kapsamındaki, sonra kitap kapsamındaki ad. Kapsamı kitapta olmayan
        (silinmiş) sayfa olan ad hiçbir sayfa kimliğiyle bulunamaz ama silinmez: sayfa geri gelince döner."""
        if sayfa_kimligi is not None:
            t = self.adlar.get(ad_anahtari(sayfa_kimligi, ad))
            if t is not None:
                return t
        return self.adlar.get(ad_anahtari(None, ad))

    def ad_yaz(self, tanim: Optional[TanimliAd],
               eski_anahtar: Optional[Tuple[Optional[int], str]] = None) -> None:
        """Adı ekler ya da değiştirir (`tanim`); `tanim` None ise `eski_anahtar`daki adı siler.
        Yeniden adlandırma/kapsam değişiminde `eski_anahtar` verilir. Değişen ad için bir `ad` olayı."""
        if tanim is None:
            if eski_anahtar is None:
                return
            eski = self.adlar.pop(eski_anahtar, None)
            if eski is not None:
                self._olay_yay(Olay("ad", None, {"eski": eski, "yeni": None}))
            return
        anahtar = tanim.anahtar()
        eski = self.adlar.get(eski_anahtar if eski_anahtar is not None else anahtar)
        if eski_anahtar is not None and eski_anahtar != anahtar:
            self.adlar.pop(eski_anahtar, None)
        self.adlar[anahtar] = tanim
        if eski != tanim:
            self._olay_yay(Olay("ad", None, {"eski": eski, "yeni": tanim}))

    def ad_durumu(self) -> Dict[Tuple[Optional[int], str], TanimliAd]:
        """Adların anlık görüntüsü (geri al için; `TanimliAd` değişmez → sığ kopya)."""
        return dict(self.adlar)

    def ad_durumu_yukle(self, durum) -> None:
        """Görüntüyü aynen yükler; değişen her ad için (eski, yeni) bir `ad` olayı yayılır."""
        eski_depo, self.adlar = self.adlar, dict(durum)
        for anahtar in list(eski_depo) + [k for k in durum if k not in eski_depo]:
            eski, yeni = eski_depo.get(anahtar), self.adlar.get(anahtar)
            if eski != yeni:
                self._olay_yay(Olay("ad", None, {"eski": eski, "yeni": yeni}))

    # --- sayfalar ---
    def _baglan(self, sayfa: Sayfa, indeks: Optional[int] = None) -> None:
        sayfa.havuza_gec(self.stil_havuzu)
        sayfa.kitap = self
        if not sayfa.kimlik:
            sayfa.kimlik = self._sonraki_kimlik
            self._sonraki_kimlik += 1
        if indeks is None:
            self.sayfalar.append(sayfa)
        else:
            self.sayfalar.insert(indeks, sayfa)

    def sayfa_kimlikle(self, kimlik: int) -> Optional[Sayfa]:
        return next((s for s in self.sayfalar if s.kimlik == kimlik), None)

    def sayfa_ekle(self, ad: Optional[str] = None) -> Sayfa:
        ad = ad or self._yeni_ad()
        sayfa_adi_dogrula(ad)
        if self.ad_var_mi(ad):
            raise ValueError(f"Bu adda bir sayfa zaten var: {ad}")
        s = Sayfa(ad)
        self._baglan(s)
        self._olay_yay(Olay("sayfa", s, {"islem": "ekle", "indeks": len(self.sayfalar) - 1}))
        return s

    def sayfa_geri_koy(self, sayfa: Sayfa, indeks: int) -> None:
        """Daha önce silinmiş sayfayı (kimliğiyle, verisiyle) `indeks` konumuna geri koyar."""
        if sayfa in self.sayfalar:
            raise ValueError("Sayfa zaten kitapta")
        if self.ad_var_mi(sayfa.ad):
            raise ValueError(f"Bu adda bir sayfa zaten var: {sayfa.ad}")
        self._baglan(sayfa, min(max(indeks, 0), len(self.sayfalar)))
        self._olay_yay(Olay("sayfa", sayfa, {"islem": "ekle", "indeks": self.sayfalar.index(sayfa)}))

    def ad_var_mi(self, ad: str) -> bool:
        return any(s.ad.casefold() == ad.casefold() for s in self.sayfalar)

    def _yeni_ad(self) -> str:
        n = len(self.sayfalar) + 1
        while self.ad_var_mi(f"Sayfa{n}"):
            n += 1
        return f"Sayfa{n}"

    def sayfa_sil(self, sayfa: Sayfa) -> int:
        """Sayfayı kitaptan çıkarır (nesne ve verisi korunur: geri alınabilir); eski sırasını döndürür."""
        if len(self.sayfalar) == 1:
            raise ValueError("Son sayfa silinemez")
        indeks = self.sayfalar.index(sayfa)
        self.sayfalar.remove(sayfa)
        sayfa.kitap = None                      # silinmiş sayfa olay yaymaz
        self._olay_yay(Olay("sayfa", sayfa, {"islem": "sil", "indeks": indeks}))
        return indeks

    def yeniden_adlandir(self, sayfa: Sayfa, ad: str) -> None:
        sayfa_adi_dogrula(ad)
        if any(s is not sayfa and s.ad.casefold() == ad.casefold() for s in self.sayfalar):
            raise ValueError(f"Bu adda bir sayfa zaten var: {ad}")
        eski = sayfa.ad
        sayfa.ad = ad
        if eski != ad:
            self._olay_yay(Olay("sayfa", sayfa, {"islem": "ad", "eski_ad": eski,
                                                  "indeks": self.sayfalar.index(sayfa)}))

    def sayfa_tasi(self, sayfa: Sayfa, yeni_indeks: int) -> None:
        """Sayfayı sekme sırasında `yeni_indeks` konumuna taşır."""
        if not 0 <= yeni_indeks < len(self.sayfalar):
            raise ValueError(f"Geçersiz sıra: {yeni_indeks}")
        eski = self.sayfalar.index(sayfa)
        if eski == yeni_indeks:
            return
        self.sayfalar.remove(sayfa)
        self.sayfalar.insert(yeni_indeks, sayfa)
        self._olay_yay(Olay("sayfa", sayfa, {"islem": "tasi", "indeks": yeni_indeks,
                                              "eski_indeks": eski}))
