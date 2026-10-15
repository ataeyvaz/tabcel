"""Şablon bilgisinin kitapta saklanması (Faz 10c). Qt yok. Tasarım: `sablon_tasarim.md` §5.

- Bilgi, kitapta **çok gizli** `_tabcel` sayfasında durur (.xlsx `veryHidden`); kitap modelinde sıradan sayfa değil,
  `kitap.sablon` (`SablonKaydi`) nesnesidir. Sayfa düzeni: satır 1 = başlık (`TABCEL_SABLON`, şema sürümü, üretici,
  parça sayısı, SHA-256 sağlama), satır 2…n = JSON parçaları (her hücre ≤ 30.000 karakter; Excel sınırı 32.767).
- Sütunlara **konumla değil** kimlik + tanımlı ad çapası (`TR_MOD_<modül>`) + başlık adıyla bağlanır; `denetle` açılışta
  uyuşmayı denetler. Uyuşmazlıkta çökmez: `Denetim.aktif=False` (form devre dışı), tablo ve formüller çalışmaya devam eder.
- Sağlama tutmayan / bozuk / daha yeni sürümlü bilgi **silinmez**: ham satırlar `kitap.sablon_ham`da tutulur ve olduğu gibi geri yazılır.
"""
import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .. import APP_NAME
from ..model.adres import harften_sutun, sutun_harfe
from . import sema, yukleyici

SAYFA_ADI = "_tabcel"
ETIKET = "TABCEL_SABLON"
PARCA_BOYU = 30_000
SURUM = 1                                   # saklama biçimi sürümü (şema sürümünden ayrı)
_CAPA_RE = re.compile(r"^=\[(\d+)\]!\$([A-Z]{1,3})\$(\d+):\$([A-Z]{1,3})\$(\d+)$")
HATA, BILGI = "hata", "bilgi"


@dataclass
class ModulBagi:
    """Üretim anındaki yerleşim (bilgi amaçlı; asıl bağ çapa + başlıktır)."""
    sayfa_adi: str
    basliklar: Dict[str, str]                # sütun kimliği → başlık (sütun sırasıyla)
    ilk_satir: int = 2
    kapasite: int = 0
    formul_satiri: int = 0
    hesaplanan_ozet: Dict[str, str] = field(default_factory=dict)       # hesaplanan sütun kimliği → ilk satır formülünün özeti


@dataclass
class SablonKaydi:
    akis_kimligi: str
    akis_surumu: int
    uretici: str
    cevaplar: Dict[str, bool]
    ham_akis: dict
    ham_moduller: Dict[str, dict]
    baglar: Dict[str, ModulBagi]
    ornek_satirlar: Dict[str, List[int]] = field(default_factory=dict)
    ayarlar: Dict[str, str] = field(default_factory=dict)               # ayar kimliği → tanımlı ad (TR_AYAR_…)
    surum: int = SURUM


# ---------------------------------------------------------------- serileştirme
def ozet(metin: str) -> str:
    return hashlib.sha1(metin.encode("utf-8")).hexdigest()[:16]


def json_yaz(k: SablonKaydi) -> str:
    d = {"surum": k.surum, "uretici": k.uretici, "akis_kimligi": k.akis_kimligi, "akis_surumu": k.akis_surumu,
         "cevaplar": k.cevaplar,
         "tanim": {"akis": k.ham_akis, "moduller": k.ham_moduller},
         "baglar": {m: {"sayfa_adi": b.sayfa_adi, "basliklar": b.basliklar, "ilk_satir": b.ilk_satir, "kapasite": b.kapasite,
                        "formul_satiri": b.formul_satiri, "hesaplanan_ozet": b.hesaplanan_ozet} for m, b in k.baglar.items()},
         "ornek_satirlar": k.ornek_satirlar, "ayarlar": k.ayarlar}
    return json.dumps(d, ensure_ascii=False, separators=(",", ":"))


def json_oku(metin: str) -> SablonKaydi:
    d = json.loads(metin)
    t = d["tanim"]
    baglar = {m: ModulBagi(b["sayfa_adi"], dict(b["basliklar"]), int(b.get("ilk_satir", 2)), int(b.get("kapasite", 0)),
                           int(b.get("formul_satiri", 0)), dict(b.get("hesaplanan_ozet", {})))
              for m, b in d["baglar"].items()}
    return SablonKaydi(d["akis_kimligi"], int(d["akis_surumu"]), d.get("uretici", ""), dict(d["cevaplar"]), t["akis"], t["moduller"],
                       baglar, {m: list(v) for m, v in d.get("ornek_satirlar", {}).items()}, dict(d.get("ayarlar", {})),
                       int(d["surum"]))


def satirlar(k: SablonKaydi) -> List[List[Any]]:
    """`_tabcel` sayfasının satırları: [başlık satırı, parça, parça, …]."""
    metin = json_yaz(k)
    parcalar = [metin[i:i + PARCA_BOYU] for i in range(0, len(metin), PARCA_BOYU)] or [""]
    return [[ETIKET, k.surum, k.uretici, len(parcalar), ozet(metin)]] + [[p] for p in parcalar]


def coz(satirlar_: List[List[Any]]) -> Tuple[Optional[SablonKaydi], Optional[str]]:
    """Sayfa satırlarından kayıt. Başarısızsa (None, Türkçe neden); ham satırları saklamak çağıranındır."""
    try:
        bas = satirlar_[0]
        if not bas or bas[0] != ETIKET:
            return None, f"“{SAYFA_ADI}” sayfası tanınmayan bir biçimde"
        n = int(bas[3])
        if len(satirlar_) < n + 1:
            return None, "şablon bilgisinin parçaları eksik"
        metin = "".join("" if satirlar_[i][0] is None else str(satirlar_[i][0]) for i in range(1, n + 1))
    except (IndexError, TypeError, ValueError):
        return None, "şablon bilgisi okunamadı"
    if ozet(metin) != str(bas[4]):
        return None, "şablon bilgisi dosyada değiştirilmiş ya da bozulmuş (sağlama tutmuyor)"
    try:
        d = json.loads(metin)
    except ValueError:
        return None, "şablon bilgisi bozuk (JSON okunamadı)"
    if not isinstance(d, dict) or not isinstance(d.get("surum"), int):
        return None, "şablon bilgisi bozuk"
    if d["surum"] > SURUM:
        return None, (f"şablon bilgisi daha yeni bir {APP_NAME} sürümüyle oluşturulmuş (saklama sürümü {d['surum']}); "
                      "form kapalı, tablo çalışır")
    try:
        return json_oku(metin), None
    except (KeyError, TypeError, ValueError, AttributeError):
        return None, "şablon bilgisi eksik alan içeriyor"


# ---------------------------------------------------------------- kayıt oluşturma (üretimden)
def kayit_olustur(sablon, sonuc) -> Optional[SablonKaydi]:
    """`uretici.uret` sonucundan kitaba konacak kayıt. Ham sözlükler yoksa (elle kurulmuş Sablon) None."""
    if not sablon.akis.ham or any(not m.ham for m in sablon.moduller.values()):
        return None
    from .. import KUNYE
    baglar: Dict[str, ModulBagi] = {}
    for mk, yer in sonuc.yerler.items():
        sayfa = sonuc.kitap.sayfa_kimlikle(yer.sayfa_kimligi)
        bas = {s.kimlik: s.ad for s in yer.modul.sutunlar if s.kimlik in yer.sutunlar}
        ozet_ = {}
        for s in yer.modul.sutunlar:
            if s.tur == "hesaplanan" and s.kimlik in yer.sutunlar:
                h = sayfa.hucre(yer.ilk_satir, yer.sutunlar[s.kimlik])
                if h is not None and h.formul:
                    ozet_[s.kimlik] = ozet(h.formul)
        baglar[mk] = ModulBagi(sayfa.ad, bas, yer.ilk_satir, yer.kapasite, yer.formul_satiri, ozet_)
    return SablonKaydi(sablon.akis.kimlik, sablon.akis.surum, KUNYE, dict(sonuc.bayraklar), sablon.akis.ham,
                       {k: m.ham for k, m in sablon.moduller.items()}, baglar,
                       {m: list(v) for m, v in sonuc.ornek_satirlar.items()},
                       {a: f"TR_AYAR_{a}" for a in sonuc.ayar_yerleri})


def tanimlari_ayristir(k: SablonKaydi):
    """Saklanan ham sözlüklerden (göçle) `Akis` + `{kimlik: Modul}`; (None, None, hatalar) başarısızsa."""
    akis, h = yukleyici.tanim_ayristir(k.ham_akis, "akis")
    hatalar = [str(x) for x in h if not x.uyari]
    moduller = {}
    for mk, ham in k.ham_moduller.items():
        m, h = yukleyici.tanim_ayristir(ham, "modul")
        hatalar += [f"{mk}: {x}" for x in h if not x.uyari]
        if m is not None:
            moduller[mk] = m
    if akis is None or hatalar:
        return None, None, hatalar or ["tanım okunamadı"]
    return akis, moduller, []


# ---------------------------------------------------------------- açılışta uyuşma denetimi
@dataclass
class Bulgu:
    modul: str
    tur: str                      # sayfa_yok | capa_yok | baslik_yok | baslik_yer | yeni_sutun | formul_degisti | tanim_bozuk
    onem: str
    mesaj: str


@dataclass
class Denetim:
    bulgular: List[Bulgu] = field(default_factory=list)
    esleme: Dict[str, Dict[str, int]] = field(default_factory=dict)       # modül → {sütun kimliği: güncel sütun no}
    sayfalar: Dict[str, int] = field(default_factory=dict)                # modül → güncel sayfa kimliği
    neden: str = ""                                                        # kayıt hiç okunamadıysa

    @property
    def aktif(self) -> bool:
        return not self.neden and not any(b.onem == HATA for b in self.bulgular)

    def metin(self) -> str:
        return "\n".join(([self.neden] if self.neden else []) + [f"{b.modul}: {b.mesaj}" for b in self.bulgular])


def capa_coz(kitap, modul: str):
    """`TR_MOD_<modül>` çapasının işaret ettiği (sayfa, ilk sütun, son sütun, satır); çözülemezse None."""
    ad = kitap.ad_bul(f"TR_MOD_{modul}")
    if ad is None:
        return None
    m = _CAPA_RE.match(ad.formul)
    if not m or m.group(3) != m.group(5):
        return None
    sayfa = kitap.sayfa_kimlikle(int(m.group(1)))
    if sayfa is None:
        return None
    return sayfa, harften_sutun(m.group(2)), harften_sutun(m.group(4)), int(m.group(3))


def _baslik_metni(sayfa, satir: int, sutun: int) -> str:
    h = sayfa.hucre(satir, sutun)
    return str(h.deger).strip() if h is not None and isinstance(h.deger, str) else ""


def denetle(kitap, kayit: SablonKaydi) -> Denetim:
    """Kayıt ile kitabın uyumu: çapa/sayfa/başlık. Hiçbir zaman istisna fırlatmaz."""
    d = Denetim()
    akis, moduller, hatalar = tanimlari_ayristir(kayit)
    if akis is None:
        d.bulgular.append(Bulgu("", "tanim_bozuk", HATA, "saklanan şablon tanımı okunamadı: " + "; ".join(hatalar[:3])))
        return d
    for mk, bag in kayit.baglar.items():
        capa = capa_coz(kitap, mk)
        if capa is not None:
            sayfa, ilk, son, satir = capa
        else:
            sayfa = next((s for s in kitap.sayfalar if s.ad == bag.sayfa_adi), None)
            if sayfa is None:
                d.bulgular.append(Bulgu(mk, "sayfa_yok", HATA, f"“{bag.sayfa_adi}” sayfası ve tablo çapası bulunamadı"))
                continue
            ilk, son, satir = 1, 0, bag.ilk_satir - 1
            d.bulgular.append(Bulgu(mk, "capa_yok", BILGI, f"tablo çapası yok; “{sayfa.ad}” sayfası adıyla bulundu"))
        kul = sayfa.kullanilan_aralik()
        son_sutun = max(son, kul[3] if kul else 0, len(bag.basliklar))
        mevcut = {}
        for c in range(1, son_sutun + 1):
            b = _baslik_metni(sayfa, satir, c)
            if b and b not in mevcut:
                mevcut[b] = c
        esle = {sk: mevcut[b] for sk, b in bag.basliklar.items() if b in mevcut}
        eksik = [b for b in bag.basliklar.values() if b not in mevcut]
        yer_farki = any(c != ilk + i for i, c in enumerate(esle.values()))        # beklenen konum: çapanın başlangıcından sırayla
        if eksik:
            d.bulgular.append(Bulgu(mk, "baslik_yok", HATA,
                                    "şu sütun başlıkları bulunamadı: " + ", ".join(f"“{b}”" for b in eksik)
                                    + " (silinmiş ya da yeniden adlandırılmış olabilir)"))
        elif yer_farki:
            d.bulgular.append(Bulgu(mk, "baslik_yer", BILGI, "sütunlar yer değiştirmiş; başlık adlarına göre yeniden eşlendi"))
        yeni = [b for b, c in mevcut.items() if b not in bag.basliklar.values()]
        if yeni:
            d.bulgular.append(Bulgu(mk, "yeni_sutun", BILGI, "şablonda olmayan sütunlar: " + ", ".join(f"“{b}”" for b in yeni)))
        for sk, o in bag.hesaplanan_ozet.items():
            c = esle.get(sk)
            h = sayfa.hucre(bag.ilk_satir, c) if c else None
            if c and (h is None or h.formul is None or ozet(h.formul) != o):
                d.bulgular.append(Bulgu(mk, "formul_degisti", BILGI, f"“{bag.basliklar[sk]}” sütununun formülü değiştirilmiş"))
        if not eksik:
            d.esleme[mk] = esle
            d.sayfalar[mk] = sayfa.kimlik
    return d


# ---------------------------------------------------------------- yeniden eşleme (Faz 10f)
@dataclass
class EslemeDurumu:
    modul: str
    sayfa_adi: str
    eksik: List[Tuple[str, str]]            # (sütun kimliği, kayıtlı başlık) — tabloda bulunamayanlar
    adaylar: List[str]                      # tabloda olup şablonda tanımlı olmayan başlıklar (eşleme seçenekleri)


def esleme_durumlari(kitap, kayit: SablonKaydi) -> List[EslemeDurumu]:
    """Başlığı bulunamayan sütunlar için kullanıcıya sunulacak eşleme önerileri (yalnız eksiği olan modüller)."""
    sonuc = []
    for mk, bag in kayit.baglar.items():
        capa = capa_coz(kitap, mk)
        if capa is not None:
            sayfa, ilk, son, satir = capa
        else:
            sayfa = next((s for s in kitap.sayfalar if s.ad == bag.sayfa_adi), None)
            if sayfa is None:
                continue
            ilk, son, satir = 1, 0, bag.ilk_satir - 1
        kul = sayfa.kullanilan_aralik()
        son_sutun = max(son, kul[3] if kul else 0, len(bag.basliklar))
        mevcut = {}
        for c in range(1, son_sutun + 1):
            b = _baslik_metni(sayfa, satir, c)
            if b and b not in mevcut:
                mevcut[b] = c
        eksik = [(sk, b) for sk, b in bag.basliklar.items() if b not in mevcut]
        if eksik:
            adaylar = [b for b in mevcut if b not in bag.basliklar.values()]
            sonuc.append(EslemeDurumu(mk, sayfa.ad, eksik, adaylar))
    return sonuc


def yeniden_esle(kitap, kayit: SablonKaydi, harita: Dict[str, Dict[str, str]]) -> Denetim:
    """`harita`: {modül: {sütun kimliği: tablodaki yeni başlık}}. Kayıttaki başlık adı güncellenir (tablo ve formüller değişmez);
    sonra uyuşma yeniden denetlenir, sonuç `kitap.sablon_denetim`e yazılır. Çağıran belgeyi değişmiş işaretler."""
    for mk, m in harita.items():
        bag = kayit.baglar.get(mk)
        if bag is None:
            continue
        for sk, yeni in m.items():
            if sk in bag.basliklar and yeni:
                bag.basliklar[sk] = yeni
    kitap.sablon_denetim = denetle(kitap, kayit)
    return kitap.sablon_denetim
