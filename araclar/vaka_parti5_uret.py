import json, os
V = []
def f(fm, h=None, **k):
    V.append(dict(id=f"P5_{len(V)+1:03d}", formul=fm, hucreler=h, **k))
PAIRS = """kg g|lbm kg|g lbm|ozm g|stone kg|ton kg|uk_ton kg|sg kg|u g|grain g|cwt kg|m km|km mi|mi m|in cm|ft m|yd m|Nmi m|ang m|ly m|pc m|Pica in|pica in|ell m|survey_mi m|yr day|day hr|hr mn|mn sec|yr sec|d s|min s|Pa atm|atm mmHg|psi Pa|Torr Pa|at Pa|N lbf|dyn N|lbf N|pond N|J cal|J e|c J|cal J|eV J|Wh J|HPh J|BTU J|flb J|W HP|HP W|PS W|T ga|l gal|gal l|qt l|pt l|uk_pt l|tsp ml|tbs ml|cup ml|oz ml|m3 l|ft3 l|in3 ml|yd3 m3|barrel l|bushel l|uk_gal l|regton m3|m2 ha|ar m2|ha uk_acre|us_acre m2|mi2 km2|ft2 m2|in2 cm2|m/s mph|mph kn|m/h m/s|kn m/s|bit byte|byte kbyte|Gibyte Mibyte|kbit byte|C F|F C|C K|K F|Rank K|Reau C|kel C|fah C|cel F|mm cm|km m|nm m|um m|Gm km|kg lbm|mg g|kg mg|ug g|kPa Pa|MPa psi|MW W|kW HP|kWh J|mL L|dl l|cl ml|hl l|Mg g|Tg kg|da g|kN N|ms s|ns s|us s|m yd|g kg|xyz kg|kg m|C kg|m C|kg k|m2 m|m3 m|ft2 ft3|ang3 m3|km3 m3|km2 m2|mm2 m2|cm3 l|dm3 l|mm3 ml|Em m|Pm m|Zm m|ym m|am m|fm m|pm m|zm m|em m|Yg g|zg g|ag g|hm m|dam m|Kib bit|Ki byte|Mi byte""".split("|")
for p in PAIRS:
    a, b = p.split()
    f(f'=CONVERT(1,"{a}","{b}")')
    if len(V) % 7 == 0:
        f(f'=CONVERT(123.456,"{a}","{b}")')
for fm in ['=CONVERT(-40,"C","F")', '=CONVERT(0,"K","C")', '=CONVERT(A1,"kg","g")', '=CONVERT(A2,"kg","g")', '=CONVERT(A3,"kg","g")', '=CONVERT(A4,"kg","g")', '=CONVERT(1,A5,"g")', '=CONVERT(1,"KG","g")', '=CONVERT(1,"kg","G")', '=CONVERT(1,"","g")', '=CONVERT(TRUE,"kg","g")', '=CONVERT("2","kg","g")', '=CONVERT(5,"m","m")', '=CONVERT(0,"kg","lbm")', '=CONVERT(1E+300,"km","m")', '=CONVERT(1,"mph","m/s")']:
    f(fm, {"A1": 2, "A2": None, "A3": "x", "A4": "=1/0", "A5": "kg"})
json.dump(V, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "vaka_parti5.json"), "w", encoding="utf-8"), ensure_ascii=False)
print(len(V))
