"""Kurtarma klasörü artıkları (2026-10-15 elle test: gerçek klasörde yüzlerce yetim .json/.tmp birikmişti)."""
import os
import time

from tabcel.io import kurtarma


def _yaz(ad: str, yas_sn: float):
    os.makedirs(kurtarma.klasor(), exist_ok=True)
    yol = os.path.join(kurtarma.klasor(), ad)
    open(yol, "w").write("x")
    t = time.time() - yas_sn
    os.utime(yol, (t, t))
    return yol


def test_eski_tmp_ve_yetim_dosyalar_silinir_tam_cift_ve_yeniler_kalir():
    eski_tmp = _yaz("a.json.tmp", 7200)
    taze_tmp = _yaz("b.json.tmp", 60)
    yetim_json = _yaz("c.json", 2 * 86400)
    taze_yetim_json = _yaz("d.json", 3600)
    yetim_xlsx = _yaz("e.xlsx", 2 * 86400)
    cift_json, cift_xlsx = _yaz("f.json", 2 * 86400), _yaz("f.xlsx", 2 * 86400)
    ilgisiz = _yaz("notlar.txt", 9 * 86400)
    assert kurtarma.artiklari_temizle() == 3
    for yol in (eski_tmp, yetim_json, yetim_xlsx):
        assert not os.path.exists(yol), yol
    for yol in (taze_tmp, taze_yetim_json, cift_json, cift_xlsx, ilgisiz):
        assert os.path.exists(yol), yol


def test_klasor_yoksa_cokmez():
    assert kurtarma.artiklari_temizle() == 0


def test_bekleyenler_artik_temizler_ve_tam_cifti_listeler():
    _yaz("zzz.json.tmp", 7200)
    assert kurtarma.bekleyenler() == []
    assert not os.path.exists(os.path.join(kurtarma.klasor(), "zzz.json.tmp"))
