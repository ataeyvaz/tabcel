"""Çalışma kitabının salt okunur anlık görüntüsü (T4b; tasarım `t4_arkaplan_tasarim.md`). Qt yok.

Arka planda kurtarma kopyası yazılırken kullanıcı düzenlemeyi sürdürebilsin diye yazıcı bu kopyayı okur.
Model değerleri değişmezdir (`Hucre`, `Stil`, `SayfaYapisi`, not/doğrulama/koşullu/filtre, `Grafik`/`Resim`,
`TanimliAd` — hepsi frozen); değişen yalnız kaplardır (dict/list/set). Bu yüzden kapların sığ kopyası
tutarlı bir görüntü verir. `StilHavuzu` yalnız büyür (kimlikler kalıcı) → paylaşılır.
"""
import copy

_KAPLAR = (dict, list, set)


def _sayfa_anligi(sayfa, kitap):
    yeni = copy.copy(sayfa)
    for ad, deger in vars(sayfa).items():
        if isinstance(deger, _KAPLAR):
            setattr(yeni, ad, copy.copy(deger))          # sığ kopya (alt sınıflar da)
    yeni.kitap = kitap
    return yeni


def kitap_anligi(kitap):
    """Olay dinleyicisi olmayan, kapları kopyalanmış kitap. Ana iş parçacığında çağrılır (ucuz: kap başına
    bir sığ kopya); dönen nesne başka iş parçacığında okunabilir, asıl kitap değişse de etkilenmez."""
    yeni = copy.copy(kitap)
    for ad, deger in vars(kitap).items():
        if isinstance(deger, _KAPLAR):
            setattr(yeni, ad, copy.copy(deger))          # sığ kopya (alt sınıflar da)
    yeni._dinleyiciler = []
    yeni.sayfalar = [_sayfa_anligi(s, yeni) for s in kitap.sayfalar]
    return yeni
