"""Korelacja katalogu produktów trenera (`food_catalog_data.FOOD_ROWS_ALL`, 2058 pozycji)
z katalogiem diet (`dieta/dane/produkty.csv`, 181 produktów z grupą zamienników,
tagami obróbki, alergenami i wykluczeniami) — wymiany produktów v2, §5a.

Wynik: CSV PROPOZYCJI do przeglądu człowieka (`docs/diet-module/katalog_korelacja_propozycja.csv`).
Nic nie trafia do silnika bez decyzji TAK — zatwierdzone wiersze przenosi się do
`dieta/dane/produkty_z_katalogu.csv` (osobny plik, jawne pochodzenie), a silnik nadal
działa wyłącznie na `DietProduct`. Reguły deterministyczne (test `test_koreluj_katalog.py`):

* DUPLIKAT — znormalizowana nazwa (bez nawiasów, bez diakrytyki) pokrywa się z `name_pl`
  z `produkty.csv` → pominięty (nie dublujemy produktu w innej grupie);
* SŁOWO_KLUCZOWE → grupa z mapy słów kluczowych, pewność ŚREDNIA (WYSOKA, gdy pierwszy
  wyraz nazwy występuje już w nazwie produktu tej grupy w `produkty.csv`);
* KATEGORIA → domyślna grupa kategorii, pewność NISKA;
* kategorie „Dania gotowe i fast food”, „Napoje” (poza mlekami), „Odżywki i suplementy”
  (poza białkiem), „Przekąski i słodycze” → `decision: NIE` z góry;
* `proposed_cooking_tags`/`default_scaling` = najczęstsze w grupie docelowej;
* `proposed_allergens`/`proposed_diet_exclusions` — WYŁĄCZNIE tokeny ze słownika
  `produkty.csv`, heurystyki po nazwie i kategorii; pusty alergen w kategorii, gdzie alergen
  jest typowy (Nabiał, Zboża, Ryby, Orzechy, Jaja, Strączkowe/soja) → pewność NISKA.

Uruchomienie z `apps/dzik-os`: `python tools/koreluj_katalog.py [--out plik.csv]`.
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND))

from dzik_os.food_catalog_data import FOOD_ROWS_ALL, FoodRow
from dzik_os.routers.food_catalog import normalize_name

DANE = BACKEND / "dzik_os" / "dieta" / "dane"
DOMYSLNE_WYJSCIE = Path(__file__).resolve().parents[1] / "docs" / "diet-module" / "katalog_korelacja_propozycja.csv"

KOLUMNY = ["name", "category", "kcal_100", "protein_100", "fat_100", "carbs_100", "fiber_100",
           "proposed_group", "confidence", "method", "proposed_cooking_tags", "proposed_allergens",
           "proposed_diet_exclusions", "default_scaling", "reason", "decision"]

# Kategorie katalogu trenera → domyślna grupa zamienników (pewność NISKA).
KATEGORIA_GRUPA = {
    "Mięso i drób": "białko_chude", "Ryby i owoce morza": "ryba_chuda", "Jaja": "jajka",
    "Nabiał": "nabiał_chudy", "Zboża i pieczywo": "pieczywo", "Kasze, ryż i makarony": "kasza_ryż",
    "Warzywa": "warzywa_gotowane", "Owoce": "owoce", "Rośliny strączkowe": "strączki",
    "Orzechy i nasiona": "orzechy", "Tłuszcze i oleje": "tłuszcz", "Przyprawy i dodatki": "przyprawa",
}
# Kategorie z góry na NIE (nie są zamiennikami składnika szablonu) — chyba że słowo kluczowe
# wskaże mleko (Napoje) albo białko w proszku (Odżywki).
KATEGORIE_NIE = {"Dania gotowe i fast food", "Napoje", "Odżywki i suplementy", "Przekąski i słodycze"}
WYJATKI_NIE = {"Napoje": {"mleko"}, "Odżywki i suplementy": {"białko_proszek"}}
# Kategorie, w których brak alergenu jest podejrzany → pewność NISKA.
KATEGORIE_ALERGEN_TYPOWY = {"Nabiał", "Zboża i pieczywo", "Kasze, ryż i makarony", "Ryby i owoce morza",
                            "Orzechy i nasiona", "Jaja", "Rośliny strączkowe"}

# Słowa kluczowe (regex po znormalizowanej nazwie) → grupa; kolejność ma znaczenie (pierwsze trafienie).
SLOWA_KLUCZOWE: list[tuple[str, str]] = [
    (r"odzywk|wpc|wpi|izolat|bialko serwat|bialko w proszku|proteinow", "białko_proszek"),
    (r"maslo orzechowe|pasta orzechowa|pasta z orzech|tahini|krem orzechowy|pasta migdalowa", "orzechy_pasty"),
    (r"hummus", "pasta_smarowanie"),
    (r"tofu|tempeh|seitan", "białko_roślinne"),
    (r"mielon", "białko_mielone"),
    (r"szynk|wedlin|kielbas|poledwica wedzon|salami|boczek wedzon|parowk|kabanos|pasztet", "wędlina"),
    (r"\budo\b|udk|udziec|skrzyd|karkowk|boczek|kaczk|\bges|golonk|zeberk|podud|ze skor", "białko_tłuste"),
    (r"losos|makrel|sledz|sardynk|pstrag|halibut|tunczyk w oleju|wegorz", "ryba_tłusta"),
    (r"mozzarell|feta|parmezan|gouda|camembert|cheddar|brie|ricott|mascarpone|ser zolt|ser plesniow|halloumi|ser kozi|twarog|serek wiejsk|serek homogen", "ser"),
    (r"^mleko|napoj sojow|napoj owsian|napoj migdalow|napoj ryzow|napoj kokosow|mleko sojow|mleko owsian|mleko migdalow", "mleko"),
    (r"smietan", "dodatek_tłuszczowy"),
    (r"platk|musli|granol|owsiank", "płatki"),
    (r"\bmak[ai]\b|maka ", "mąka"),
    (r"makaron|spaghetti|penne|tagliatelle|lasagn", "makaron"),
    (r"ziemniak|batat", "skrobiowe"),
    (r"kiszon|kwaszon", "kiszonki"),
    (r"salat|szpinak|rukol|jarmuz|roszponk|botwin", "warzywa_liściaste"),
    (r"cebul|\bpor\b|czosnek|szczypior", "warzywa_aromat"),
    (r"pomidor|ogorek|papryk|rzodkiew|seler naciow|kalarep", "warzywa_surowe"),
    (r"borow|malin|truskaw|jagod|porzecz|jezyn|zuraw|agrest", "owoce_jagodowe"),
    (r"suszon|daktyl|rodzynk|miod|dzem|syrop|powidl|konfitur", "słodzik"),
    (r"nasion|pestk|siemi|chia|slonecznik|sezam|dyni", "nasiona"),
    (r"awokado", "tłuszcz_roślinny"),
    (r"ketchup|musztard|\bsos\b|majonez|dressing", "sos"),
    (r"passat|koncentrat|pomidory z puszki|pomidory krojone|pelati", "pomidory_przetwory"),
    (r"oliw|olej|smalec|maslo klarowane|maslo\b", "tłuszcz"),
    (r"soczewic|ciecierzyc|fasol|groch|bob\b|edamame", "strączki"),
    (r"jajk|jaja\b|jajo\b|bialko jaj|zoltk", "jajka"),
    (r"kasz|ryz|komos|quinoa|bulgur|kuskus|amarant|peczak", "kasza_ryż"),
    (r"chleb|bulk|pieczyw|graham|kajzer|tortill|wafle|pita|bagiet|chrupk", "pieczywo"),
    (r"jogurt|kefir|maslank|skyr", "nabiał_chudy"),
    (r"orzech|migdal|nerkow|pistacj|laskow|makadami|pekan|brazyl", "orzechy"),
    (r"czekolad", "słodycze"),
    (r"pierś|piers|filet z kurczak|filet z indyk|poledwic|schab|stek|watrob|krewetk|krewet|dorsz|mintaj|morszczuk|sandacz|tilapi|sola\b", "białko_chude"),
    (r"brokul|kalafior|marchew|cukini|bakłaż|baklaz|dyni|fasolk|szparag|buracz|kapust|pieczark|grzyb|kukurydz|groszek", "warzywa_gotowane"),
    (r"jabłk|jablk|banan|gruszk|pomarancz|mandarynk|kiwi|winogron|brzoskwin|morel|sliwk|nektaryn|ananas|mango|arbuz|melon|grejpfrut|cytryn|limonk|granat", "owoce"),
    (r"bulion|wywar|rosol", "płyn"),
    (r"przypraw|sol\b|pieprz|papryka slodka|papryka ostra|curry|kurkum|oregano|bazyli|tymian|cynamon|imbir|kmin|ziol", "przyprawa"),
]

# Alergeny/wykluczenia — WYŁĄCZNIE tokeny obecne w produkty.csv (słownik czytany z pliku przy starcie).
ALERGEN_KATEGORIA = {"Ryby i owoce morza": "ryby", "Jaja": "jaja", "Nabiał": "mleko", "Orzechy i nasiona": "orzechy"}
WYKLUCZENIE_KATEGORIA = {"Mięso i drób": "meat", "Ryby i owoce morza": "fish", "Jaja": "egg", "Nabiał": "dairy"}
PO_OBROBCE = r"grillowan|pieczon|gotowan|smazon|duszon|wedzon|\bfrytk|panierowan"
GLUTEN = r"pszen|zyt|jeczm|orkisz|owsian|owies|platki owsiane|makaron|spaghetti|penne|chleb|bulk|kajzer|graham|kuskus|bulgur|manna|peczak|tortill|bagiet|pita|musli|granol|seitan|pierog|nalesnik|kluski|pieczyw|wafle ryzowe$"
BEZ_GLUTENU = r"bezglut|ryz|gryczan|jaglan|komos|quinoa|amarant|kukurydz|ziemniacz"


KWALIFIKATORY = r"\b(surow[aey]?|gotowan[aey]?|such[aey]?|odsaczon[aey]?|swiez[aey]?|cal[aey]?|bez kosci|bez skory)\b"


def znormalizuj(nazwa: str) -> str:
    """Klucz porównania nazw: bez nawiasów, przecinków i kwalifikatorów stanu
    („surowa”, „gotowany”, „suchy”, „odsączony”), po `normalize_name` z katalogu —
    „Pierś z kurczaka, surowa” i „Pierś z kurczaka (surowa)” to ten sam produkt."""
    bez = re.sub(r"\([^)]*\)", " ", nazwa).replace(",", " ")
    n = normalize_name(bez)
    n = re.sub(KWALIFIKATORY, " ", n)
    return re.sub(r"\s+", " ", n).strip()


def wczytaj_katalog_diet() -> list[dict]:
    with (DANE / "produkty.csv").open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def slowniki(rows: list[dict]) -> tuple[set[str], set[str], dict[str, str], dict[str, str], set[str], dict[str, set[str]]]:
    """(alergeny, wykluczenia, grupa→najczęstsze tagi, grupa→najczęstsze skalowanie, grupy, grupa→pierwsze wyrazy nazw)."""
    al = {t for r in rows for t in r["allergens"].split(",") if t and not t.endswith("?")}
    ex = {t for r in rows for t in r["diet_exclusions"].split(",") if t}
    tagi: dict[str, Counter] = defaultdict(Counter)
    skal: dict[str, Counter] = defaultdict(Counter)
    wyrazy: dict[str, set[str]] = defaultdict(set)
    for r in rows:
        g = r["substitution_group"]
        if not g:
            continue
        tagi[g][r["cooking_tags"]] += 1
        skal[g][r["default_scaling"] or "LINIOWY"] += 1
        wyrazy[g].add(znormalizuj(r["name_pl"]).split(" ")[0])
    return (al, ex, {g: c.most_common(1)[0][0] for g, c in tagi.items()},
            {g: c.most_common(1)[0][0] for g, c in skal.items()}, set(tagi), wyrazy)


def dopasuj_grupe(nazwa_norm: str, kategoria: str, fat_100: float) -> tuple[str | None, str]:
    """(grupa, metoda) — słowo kluczowe przed kategorią."""
    for wzor, grupa in SLOWA_KLUCZOWE:
        if re.search(wzor, nazwa_norm):
            return grupa, "SŁOWO_KLUCZOWE"
    g = KATEGORIA_GRUPA.get(kategoria)
    if g == "nabiał_chudy" and fat_100 >= 5:
        g = "nabiał_tłusty"
    return g, "KATEGORIA"


def alergeny_i_wykluczenia(nazwa_norm: str, kategoria: str, grupa: str | None, al: set[str], ex: set[str]) -> tuple[list[str], list[str]]:
    a: list[str] = []
    e: list[str] = []

    def dodaj(lista: list[str], token: str, slownik: set[str]) -> None:
        if token in slownik and token not in lista:
            lista.append(token)

    if kategoria in ALERGEN_KATEGORIA:
        dodaj(a, ALERGEN_KATEGORIA[kategoria], al)
    if kategoria in WYKLUCZENIE_KATEGORIA:
        dodaj(e, WYKLUCZENIE_KATEGORIA[kategoria], ex)
    if re.search(r"krewet|krab|malz|kalmar|osmiornic|homar|langust|smazon", nazwa_norm) and kategoria == "Ryby i owoce morza":
        dodaj(a, "skorupiaki", al)
    if grupa in ("ser", "nabiał_chudy", "nabiał_tłusty", "mleko", "dodatek_tłuszczowy") or kategoria == "Nabiał":
        dodaj(a, "mleko", al); dodaj(e, "dairy", ex)
        if not re.search(r"bez laktozy|bezlaktoz|napoj sojow|napoj owsian|napoj migdalow|napoj ryzow|napoj kokosow|mleko sojow|mleko owsian|mleko migdalow|tofu", nazwa_norm):
            dodaj(e, "lactose", ex)
    if re.search(r"maslo\b|maslo klarowane", nazwa_norm) and not re.search(r"orzech|migdal|klarowane", nazwa_norm):
        dodaj(a, "mleko", al); dodaj(e, "dairy", ex); dodaj(e, "lactose", ex)
    if re.search(GLUTEN, nazwa_norm) and not re.search(BEZ_GLUTENU, nazwa_norm):
        dodaj(a, "gluten", al); dodaj(e, "gluten", ex)
    if grupa == "jajka" or re.search(r"jajk|jaja\b|jajo\b|zoltk|bialko jaj|majonez", nazwa_norm):
        dodaj(a, "jaja", al); dodaj(e, "egg", ex)
    if re.search(r"soj|tofu|tempeh|edamame|seitan", nazwa_norm):
        dodaj(a, "soja", al)
    if re.search(r"sezam|tahini", nazwa_norm):
        dodaj(a, "sezam", al)
    if re.search(r"orzech|migdal|nerkow|pistacj|laskow|makadami|pekan|brazyl", nazwa_norm):
        dodaj(a, "orzechy", al)
    if re.search(r"orzech.*ziemn|arachid|fistaszk|maslo orzechowe", nazwa_norm):
        dodaj(a, "orzechy_ziemne", al)
    if re.search(r"musztard|gorczyc", nazwa_norm):
        dodaj(a, "gorczyca", al)
    if re.search(r"ryb|losos|tunczyk|dorsz|makrel|sledz|sardynk|pstrag|halibut|mintaj|morszczuk|sandacz|tilapi", nazwa_norm) or grupa in ("ryba_chuda", "ryba_tłusta"):
        dodaj(a, "ryby", al); dodaj(e, "fish", ex)
    if grupa in ("białko_chude", "białko_tłuste", "białko_mielone", "wędlina") and kategoria == "Mięso i drób":
        dodaj(e, "meat", ex)
    return a, e


def koreluj(rows_katalog: list[FoodRow], rows_diet: list[dict]) -> tuple[list[dict], dict[str, int]]:
    al, ex, tagi, skal, grupy, wyrazy = slowniki(rows_diet)
    istniejace = {znormalizuj(r["name_pl"]) for r in rows_diet}
    out: list[dict] = []
    stat: Counter = Counter()
    for r in rows_katalog:
        nn = znormalizuj(r.name)
        if nn in istniejace:
            stat["DUPLIKAT"] += 1
            continue
        grupa, metoda = dopasuj_grupe(nn, r.category, float(r.fat))
        if grupa is not None and grupa not in grupy:
            stat["GRUPA_SPOZA_CSV"] += 1
            continue
        decyzja = ""
        if r.category in KATEGORIE_NIE and grupa not in WYJATKI_NIE.get(r.category, set()):
            decyzja = "NIE"  # wiersz zostaje w CSV: człowiek może zmienić na TAK i wpisać grupę
        if grupa is None and decyzja != "NIE":
            stat["BEZ_GRUPY"] += 1
            continue
        if grupa is None:
            metoda, pewnosc = "KATEGORIA", "NISKA"
        elif metoda == "SŁOWO_KLUCZOWE":
            pewnosc = "WYSOKA" if nn.split(" ")[0] in wyrazy.get(grupa, set()) else "ŚREDNIA"
        else:
            pewnosc = "NISKA"
        a, e = alergeny_i_wykluczenia(nn, r.category, grupa, al, ex)
        if not a and r.category in KATEGORIE_ALERGEN_TYPOWY:
            pewnosc = "NISKA"
        powod = f"{metoda.lower()}: {grupa or '—'}" + (f"; kategoria {r.category}" if metoda == "SŁOWO_KLUCZOWE" else "")
        # Katalog diet liczy makra na 100 g produktu SUROWEGO (skalowanie porcji); pozycja
        # „po obróbce” (grillowana, pieczona, gotowana, smażona) ma inne wartości — człowiek decyduje.
        if re.search(PO_OBROBCE, nn):
            pewnosc = "NISKA"
            powod += "; wartości po obróbce termicznej (katalog diet liczy na surowo)"
        if r.category in KATEGORIE_NIE and decyzja == "NIE":
            powod += "; kategoria z góry na NIE"
        out.append({
            "name": r.name, "category": r.category, "kcal_100": r.kcal, "protein_100": r.protein, "fat_100": r.fat,
            "carbs_100": r.carbs, "fiber_100": "" if r.fiber is None else r.fiber, "proposed_group": grupa or "",
            "confidence": pewnosc, "method": metoda, "proposed_cooking_tags": tagi.get(grupa, ""),
            "proposed_allergens": ",".join(a), "proposed_diet_exclusions": ",".join(e),
            "default_scaling": skal.get(grupa or "", ""), "reason": powod, "decision": decyzja,
        })
        stat[metoda] += 1
        stat[f"pewność:{pewnosc}"] += 1
        if decyzja == "NIE":
            stat["decision:NIE"] += 1
    return out, dict(stat)


def zapisz(wiersze: list[dict], sciezka: Path) -> None:
    sciezka.parent.mkdir(parents=True, exist_ok=True)
    with sciezka.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=KOLUMNY)
        w.writeheader()
        w.writerows(wiersze)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", type=Path, default=DOMYSLNE_WYJSCIE)
    a = ap.parse_args(argv)
    wiersze, stat = koreluj(FOOD_ROWS_ALL, wczytaj_katalog_diet())
    zapisz(wiersze, a.out)
    print(f"Zapisano {len(wiersze)} propozycji do {a.out}")
    for k, v in sorted(stat.items()):
        print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
