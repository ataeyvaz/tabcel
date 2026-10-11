"""Tablo Sağlığı deneme dosyası (tamamen sentetik veri): testler/ornekler/saglik_deneme.xlsx
Kullanım: .venv\\Scripts\\python araclar\\saglik_ornek_uret.py"""
import os
import random
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)
sys.path.insert(0, os.path.join(KOK, "testler"))

from sentetik import iban_uret, tc_bozuk, tc_uret
from tabcel.io import xlsx_io
from tabcel.model.sayfa import CalismaKitabi, Hucre


def main():
    k = CalismaKitabi()
    s = k.sayfalar[0]
    s.ad = "Satışlar"
    rnd = random.Random(7)
    for c, b in enumerate(["Ürün", "Adet", "Birim fiyat", "Tutar", "Müşteri T.C. no", "IBAN"], 1):
        s.ata(1, c, Hucre(b))
    for r in range(2, 12):
        s.ata(r, 1, Hucre(f"Ürün {r - 1}"))
        s.ata(r, 2, Hucre(float(rnd.randint(1, 20))))
        s.ata(r, 3, Hucre(float(rnd.randint(10, 90))))
        s.ata(r, 4, Hucre(formul=f"=B{r}*C{r}"))
        s.ata(r, 5, Hucre(tc_uret(rnd=rnd)))
        s.ata(r, 6, Hucre(iban_uret(rnd=rnd)))
    s.ata(7, 4, Hucre(formul="=B7+C7"))                         # tutarsız formül
    s.ata(5, 5, Hucre(tc_bozuk(tc_uret(rnd=rnd))))              # geçersiz T.C. no
    s.ata(13, 4, Hucre(formul="=SUM(D2:D10)"))                  # D11 toplamaya katılmıyor (eksik aralık)
    s.ata(14, 4, Hucre(formul="=D13*1.18"))                     # formülde sabit sayı
    s.ata(15, 4, Hucre(formul="=D13/0"))                        # hata değeri
    for r in range(2, 8):
        s.ata(r, 8, Hucre(str(r * 10)))                         # H sütunu: metin olarak saklanan sayılar
    s.ata(1, 8, Hucre("Kontenjan"))
    yol = os.path.join(KOK, "testler", "ornekler", "saglik_deneme.xlsx")
    xlsx_io.kaydet(k, yol)
    print("yazıldı:", yol)


if __name__ == "__main__":
    main()
