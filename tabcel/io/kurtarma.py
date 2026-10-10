"""Otomatik kurtarma kopyaları (Faz 4 / 4e). Qt yok.

Excel'in AutoRecover'ı gibi: değişmiş belgenin kopyası kullanıcının dosyasına DOKUNMADAN
`veri_klasoru()/recovery/<kimlik>.xlsx` (+ `<kimlik>.json` üst verisi) olarak yazılır. Belge kaydedilince ya
da bilerek kapatılınca silinir; uygulama çökerse (sahibi süreç artık yoksa) bir sonraki açılışta önerilir.
"""
import json
import os
import time
import uuid
from dataclasses import dataclass
from typing import List, Optional

from .. import veri_klasoru
from . import xlsx_io


@dataclass(frozen=True)
class Kurtarilabilir:
    kimlik: str
    ad: str                      # belge adı (başlıkta görünen)
    yol: Optional[str]           # özgün dosya yolu (varsa)
    zaman: float                 # son kopya zamanı (epoch)
    dosya: str                   # kopyanın .xlsx yolu
    veri_kaybi: bool = False     # özgün dosyada korunamayan öğe vardı (kurtarılınca uyarı geri gelsin)
    uyarilar: tuple = ()


def klasor() -> str:
    return str(veri_klasoru() / "recovery")


def yeni_kimlik() -> str:
    return uuid.uuid4().hex


def _dosya(kimlik: str, uzanti: str) -> str:
    return os.path.join(klasor(), kimlik + uzanti)


def surec_canli_mi(pid: int) -> bool:
    """`pid` numaralı süreç çalışıyor mu (kendi sürecimiz dahil)."""
    if pid == os.getpid():
        return True
    try:
        if os.name == "nt":
            import ctypes
            k = ctypes.windll.kernel32
            h = k.OpenProcess(0x1000, False, pid)            # PROCESS_QUERY_LIMITED_INFORMATION
            if not h:
                return False
            kod = ctypes.c_ulong()
            ok = k.GetExitCodeProcess(h, ctypes.byref(kod))
            k.CloseHandle(h)
            return bool(ok) and kod.value == 259             # STILL_ACTIVE
        os.kill(pid, 0)
        return True
    except (OSError, AttributeError, ValueError):
        return False


def surec_baslangic(pid: int) -> Optional[int]:
    """Sürecin başlangıç zamanı (Windows FILETIME); pid yeniden kullanımını ayırt etmek için. Bilinmezse None."""
    if os.name != "nt":
        return None
    try:
        import ctypes
        from ctypes import wintypes
        k = ctypes.windll.kernel32
        h = k.OpenProcess(0x1000, False, pid)
        if not h:
            return None
        try:
            olus, bitis, ker, kul = (wintypes.FILETIME() for _ in range(4))
            if not k.GetProcessTimes(h, ctypes.byref(olus), ctypes.byref(bitis), ctypes.byref(ker),
                                     ctypes.byref(kul)):
                return None
            return (olus.dwHighDateTime << 32) | olus.dwLowDateTime
        finally:
            k.CloseHandle(h)
    except Exception:
        return None


def _sahibi_canli_mi(m: dict) -> bool:
    """Üst verideki pid hâlâ aynı süreç mi (pid başka bir süreç tarafından yeniden kullanıldıysa değil)."""
    pid = int(m["pid"])
    if not surec_canli_mi(pid):
        return False
    kayitli = m.get("baslangic")
    if kayitli is None or pid == os.getpid():
        return True
    simdi = surec_baslangic(pid)
    return simdi is None or simdi == kayitli


def kopya_yaz(kitap, kimlik: str, ad: str, yol: Optional[str], rapor=None) -> None:
    """Kitabın kurtarma kopyasını yazar (xlsx önce, üst veri sonra: üst verisi olan kopya her zaman tamdır).
    Yazılamazsa OSError/XlsxHatasi; çağıran sessizce geçer (otomatik işlem kullanıcıyı bölmez)."""
    os.makedirs(klasor(), exist_ok=True)
    xlsx_io.kaydet(kitap, _dosya(kimlik, ".xlsx"))
    gecici = _dosya(kimlik, ".json.tmp")
    with open(gecici, "w", encoding="utf-8") as f:
        json.dump({"ad": ad, "yol": yol, "zaman": time.time(), "pid": os.getpid(),
                   "baslangic": surec_baslangic(os.getpid()),
                   "veri_kaybi": bool(rapor and rapor.veri_kaybi),
                   "uyarilar": list(rapor.uyarilar) if rapor else []}, f, ensure_ascii=False)
    os.replace(gecici, _dosya(kimlik, ".json"))


def sil(kimlik: str) -> None:
    for u in (".json", ".xlsx", ".json.tmp"):
        try:
            os.remove(_dosya(kimlik, u))
        except OSError:
            pass


def bekleyenler() -> List[Kurtarilabilir]:
    """Sahibi çalışmayan (çökmüş/öldürülmüş) süreçlerden kalan kopyalar, en yeni önce. Bozuk üst veri atlanır
    (dosyaya dokunulmaz)."""
    sonuc: List[Kurtarilabilir] = []
    try:
        adlar = os.listdir(klasor())
    except OSError:
        return sonuc
    for a in adlar:
        if not a.endswith(".json"):
            continue
        kimlik = a[:-5]
        try:
            with open(_dosya(kimlik, ".json"), encoding="utf-8") as f:
                m = json.load(f)
            xlsx = _dosya(kimlik, ".xlsx")
            if not os.path.exists(xlsx) or _sahibi_canli_mi(m):
                continue
            sonuc.append(Kurtarilabilir(kimlik, str(m.get("ad") or "Adsız"), m.get("yol"),
                                        float(m.get("zaman") or 0), xlsx, bool(m.get("veri_kaybi")),
                                        tuple(str(u) for u in m.get("uyarilar") or ())))
        except (OSError, ValueError, KeyError, TypeError):
            continue
    return sorted(sonuc, key=lambda k: -k.zaman)


def ac(k: Kurtarilabilir):
    """(kitap, rapor); okunamazsa `xlsx_io.XlsxHatasi`."""
    return xlsx_io.ac(k.dosya)


def sahiplen(kimlik: str) -> None:
    """Kurtarılan kopyayı bu sürece bağlar (üst verideki pid güncellenir): belge kaydedilene dek korunur."""
    try:
        with open(_dosya(kimlik, ".json"), encoding="utf-8") as f:
            m = json.load(f)
        m["pid"] = os.getpid()
        m["baslangic"] = surec_baslangic(os.getpid())
        gecici = _dosya(kimlik, ".json.tmp")
        with open(gecici, "w", encoding="utf-8") as f:
            json.dump(m, f, ensure_ascii=False)
        os.replace(gecici, _dosya(kimlik, ".json"))
    except (OSError, ValueError):
        pass
