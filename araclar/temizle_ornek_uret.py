"""Paylaşım Temizleyici deneme dosyası (tamamen sentetik veri): testler/ornekler/kvkk_deneme.xlsx
Kullanım: .venv\Scripts\python araclar\temizle_ornek_uret.py"""
import os
import random
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)
sys.path.insert(0, os.path.join(KOK, "testler"))

from sentetik import iban_bicimli, iban_uret, kart_uret, tc_uret, vkn_uret
from tabcel.io import xlsx_io
from tabcel.model.notlar import Not
from tabcel.model.sayfa import CalismaKitabi, Hucre


def main():
    k = CalismaKitabi()
    s = k.sayfalar[0]
    s.ad = "Müşteriler"
    rnd = random.Random(11)
    for c, b in enumerate(["Ad Soyad", "T.C. no", "IBAN", "Telefon", "E-posta", "Bakiye"], 1):
        s.ata(1, c, Hucre(b))
    adlar = ["Ayşe Örnek", "Mehmet Deneme", "Fatma Sentetik", "Ali Kurgu", "Zeynep Uydurma"]
    for i, ad in enumerate(adlar):
        r = i + 2
        s.ata(r, 1, Hucre(ad))
        s.ata(r, 2, Hucre(tc_uret(rnd=rnd)))
        s.ata(r, 3, Hucre(iban_bicimli(iban_uret(rnd=rnd))))
        s.ata(r, 4, Hucre(f"0532 {rnd.randint(100, 999)} {rnd.randint(10, 99)} {rnd.randint(10, 99)}"))
        s.ata(r, 5, Hucre(f"kisi{i + 1}@ornek.com"))
        s.ata(r, 6, Hucre(float(rnd.randint(1000, 9000))))
    s.ata(8, 6, Hucre(formul="=SUM(F2:F6)"))
    s.ata(9, 6, Hucre(formul="=F8/COUNT(F2:F6)"))
    s.notlari_yaz({(2, 2): Not(f"Vergi no {vkn_uret(rnd=rnd)} ile karıştırılmasın", "Ayşe Örnek")})
    s.gizli_sutun.add(7)
    s.ata(2, 7, Hucre(kart_uret("4", 16, rnd)))                 # gizli sütunda kart no
    g = k.sayfa_ekle("Arşiv")
    g.ata(1, 1, Hucre(f"Eski müşteri: {tc_uret(rnd=rnd)}"))
    g.gizli = True                                              # gizli sayfada T.C. no
    yol = os.path.join(KOK, "testler", "ornekler", "kvkk_deneme.xlsx")
    xlsx_io.kaydet(k, yol)
    print("yazıldı:", yol)


if __name__ == "__main__":
    main()
