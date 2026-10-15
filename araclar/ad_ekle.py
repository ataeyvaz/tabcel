"""eksik_fonksiyonlar.md'deki (Excel'den ölçülmüş) Türkçe adları adlar.py'ye `EN_TR_EK` olarak yazar.
Kullanım: python araclar/ad_ekle.py AD1 AD2 …   (yalnız verilen İngilizce adlar eklenir)"""
import re, sys, io
sys.stdout.reconfigure(encoding="utf-8")
md = open("eksik_fonksiyonlar.md", encoding="utf-8").read()
tablo = dict(re.findall(r"^\| `([^`]+)` \| `([^`]+)` \|$", md, re.M))
yol = "tabcel/formul/adlar.py"
src = open(yol, encoding="utf-8").read()
for ad in sys.argv[1:]:
    if ad not in tablo:
        print("YOK:", ad); continue
    if f'"{ad}":' in src:
        continue
    src = src.replace("\nEN_TR.update(TABCEL_OZEL)", f'\nEN_TR["{ad}"] = "{tablo[ad]}"\nEN_TR.update(TABCEL_OZEL)', 1) if False else src
    ek = f'EN_TR["{ad}"] = "{tablo[ad]}"\n'
    src = src.replace("# Tabcel'e özel (Microsoft Excel'de YOK", "@@EK@@# Tabcel'e özel (Microsoft Excel'de YOK", 1) if "@@EK@@" not in src else src
    src = src.replace("@@EK@@", "@@EK@@" + ek)
src = src.replace("@@EK@@", "")
open(yol, "w", encoding="utf-8").write(src)
