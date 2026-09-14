"""Hasła dnia — treść systemowa, deterministyczna, bez AI.

Rotacja: index = date.toordinal() % len(DAILY_MESSAGES) — jedno hasło na dzień,
identyczne dla wszystkich urządzeń danego użytkownika. Proweniencja (autor) jest
zawsze pokazywana. Znaczniki w polu `note`: "parafraza" / "przypisywane" oznaczają
mniej pewne autorstwo — reszta jest dobrze udokumentowana.

Wstaw jako: apps/dzik-os/backend/dzik_os/daily_messages.py
Wystaw message_for(local_today(user)) jako pole `daily_message` w GET /api/me/today.
"""
from __future__ import annotations

from datetime import date

# (text, author, note)  — note może być "" (puste)
DAILY_MESSAGES: list[dict[str, str]] = [
    {"text": "Jakość Twojego życia zależy od jakości Twoich myśli.", "author": "Marek Aureliusz", "note": ""},
    {"text": "Nie trać już czasu na spory o to, jakim człowiekiem należy być. Bądź nim.", "author": "Marek Aureliusz", "note": ""},
    {"text": "Nie dlatego nie próbujemy, że rzeczy są trudne — są trudne, bo nie próbujemy.", "author": "Seneka", "note": ""},
    {"text": "Najpierw powiedz sobie, kim chcesz być — potem rób to, co musisz.", "author": "Epiktet", "note": ""},
    {"text": "Jesteśmy tym, co nieustannie robimy. Doskonałość nie jest więc czynem, lecz nawykiem.", "author": "Will Durant", "note": "parafraza Arystotelesa"},
    {"text": "Niezbadane życie nie jest warte życia.", "author": "Sokrates", "note": ""},
    {"text": "Podróż tysiąca mil zaczyna się od jednego kroku.", "author": "Lao Tsy", "note": ""},
    {"text": "Kto zwycięża innych, jest silny. Kto zwycięża siebie, jest potężny.", "author": "Lao Tsy", "note": ""},
    {"text": "Kropla po kropli napełnia się dzban.", "author": "Budda", "note": "Dhammapada"},
    {"text": "Charakter człowieka jest jego przeznaczeniem.", "author": "Heraklit", "note": ""},
    {"text": "Najwspanialszą rzeczą na świecie jest umieć należeć do siebie.", "author": "Michel de Montaigne", "note": ""},
    {"text": "Wiedzieć nie wystarczy — trzeba stosować. Chcieć nie wystarczy — trzeba działać.", "author": "Johann Wolfgang Goethe", "note": ""},
    {"text": "Kto ma po co żyć, zniesie niemal każde jak.", "author": "Friedrich Nietzsche", "note": ""},
    {"text": "Stań się tym, kim jesteś.", "author": "Friedrich Nietzsche", "note": ""},
    {"text": "Nie dość być pracowitym — pracowite są i mrówki. Pytanie brzmi: nad czym pracujesz?", "author": "Henry David Thoreau", "note": ""},
    {"text": "Idź śmiało w stronę swoich marzeń. Żyj życiem, które sobie wyobraziłeś.", "author": "Henry David Thoreau", "note": ""},
    {"text": "Wszyscy myślą o zmianie świata, nikt nie myśli o zmianie samego siebie.", "author": "Lew Tołstoj", "note": ""},
    {"text": "Nawet najciemniejsza noc się skończy i wzejdzie słońce.", "author": "Victor Hugo", "note": "Nędznicy"},
    {"text": "Doskonałość bywa wrogiem dobra.", "author": "Voltaire", "note": ""},
    {"text": "Dyscyplina jest mostem między celami a ich osiągnięciem.", "author": "Jim Rohn", "note": ""},
    {"text": "Nie życzę sobie, by było łatwiej — życzę sobie, bym był lepszy.", "author": "Jim Rohn", "note": ""},
    {"text": "Zasiej czyn — zbierzesz nawyk. Zasiej nawyk — zbierzesz charakter. Zasiej charakter — zbierzesz los.", "author": "przysłowie", "note": "przypisywane wielu"},
    {"text": "Niczego w życiu nie należy się bać — należy to tylko zrozumieć.", "author": "Maria Skłodowska-Curie", "note": ""},
    {"text": "Trzeba mieć wytrwałość i wiarę w siebie — wierzyć, że jest się do czegoś zdolnym.", "author": "Maria Skłodowska-Curie", "note": ""},
    {"text": "Życie jest jak jazda na rowerze — by zachować równowagę, musisz się poruszać.", "author": "Albert Einstein", "note": "list, 1930"},
    {"text": "Nie jestem szczególnie zdolny — jestem tylko namiętnie ciekawy.", "author": "Albert Einstein", "note": ""},
    {"text": "Pierwsza zasada: nie wolno oszukiwać samego siebie — a siebie najłatwiej oszukać.", "author": "Richard Feynman", "note": ""},
    {"text": "Jeśli widziałem dalej, to dlatego, że stałem na ramionach olbrzymów.", "author": "Isaac Newton", "note": ""},
    {"text": "Los sprzyja przygotowanym umysłom.", "author": "Louis Pasteur", "note": ""},
    {"text": "Geniusz to jeden procent natchnienia i dziewięćdziesiąt dziewięć procent potu.", "author": "Thomas Edison", "note": ""},
    {"text": "Wyobraźnia jest ważniejsza od wiedzy.", "author": "Albert Einstein", "note": ""},
    {"text": "Przyszłość zależy od tego, co robisz dziś.", "author": "Mahatma Gandhi", "note": ""},
    {"text": "Zawsze wydaje się to niemożliwe — dopóki nie zostanie zrobione.", "author": "Nelson Mandela", "note": ""},
    {"text": "Chwała nie polega na tym, że nigdy nie upadamy, lecz że po każdym upadku wstajemy.", "author": "Nelson Mandela", "note": "parafraza"},
    {"text": "Nie musisz widzieć całych schodów — wystarczy, że zrobisz pierwszy krok.", "author": "Martin Luther King Jr.", "note": ""},
    {"text": "Przyszłość należy do tych, którzy wierzą w piękno swoich marzeń.", "author": "Eleanor Roosevelt", "note": ""},
    {"text": "Nikt nie odbierze Ci poczucia niższości bez Twojej zgody.", "author": "Eleanor Roosevelt", "note": ""},
    {"text": "Łatwiej zbudować silne dzieci, niż naprawiać złamanych dorosłych.", "author": "Frederick Douglass", "note": ""},
    {"text": "Najlepszym sposobem przewidzenia przyszłości jest jej stworzenie.", "author": "Peter Drucker", "note": "przypisywane też innym"},
    {"text": "Zarządzanie to robienie rzeczy właściwie; przywództwo to robienie właściwych rzeczy.", "author": "Peter Drucker", "note": ""},
    {"text": "Wymagajcie od siebie, choćby inni od was nie wymagali.", "author": "Jan Paweł II", "note": ""},
    {"text": "Człowiek jest wielki nie przez to, co posiada, lecz przez to, kim jest.", "author": "Jan Paweł II", "note": ""},
    {"text": "Mierz siły na zamiary, nie zamiar podług sił.", "author": "Adam Mickiewicz", "note": "Oda do młodości"},
    {"text": "Tyle wiemy o sobie, ile nas sprawdzono.", "author": "Wisława Szymborska", "note": ""},
    {"text": "Bądź wierny. Idź.", "author": "Zbigniew Herbert", "note": "Przesłanie Pana Cogito"},
    {"text": "Czułość jest najskromniejszą odmianą miłości.", "author": "Olga Tokarczuk", "note": "mowa noblowska"},
    {"text": "Nie ma dzieci — są ludzie.", "author": "Janusz Korczak", "note": ""},
    {"text": "Wątpić trzeba umieć.", "author": "Stanisław Lem", "note": ""},
    {"text": "Nie trzeba kłaniać się okolicznościom, a prawdom kazać, by za drzwiami stały.", "author": "Cyprian Kamil Norwid", "note": ""},
    {"text": "Trzeba z żywymi naprzód iść, po życie sięgać nowe.", "author": "Adam Asnyk", "note": ""},
    {"text": "Nie wznosisz się do poziomu swoich celów — spadasz do poziomu swoich systemów.", "author": "James Clear", "note": "Atomowe nawyki"},
    {"text": "Każde działanie to głos oddany na człowieka, którym chcesz się stać.", "author": "James Clear", "note": ""},
    {"text": "Nawyki to procent składany samodoskonalenia.", "author": "James Clear", "note": ""},
    {"text": "Chcesz stworzyć nawyk? Zacznij od tak małego kroku, że nie sposób odmówić.", "author": "BJ Fogg", "note": "parafraza — Tiny Habits"},
    {"text": "Entuzjazm jest powszechny. Wytrwałość — rzadka.", "author": "Angela Duckworth", "note": "Upór"},
    {"text": "Szczęście nie jest gotowe — rodzi się z Twoich własnych czynów.", "author": "Dalajlama XIV", "note": ""},
    {"text": "Możesz wybrać odwagę albo wygodę — nie jedno i drugie naraz.", "author": "Brené Brown", "note": "parafraza"},
    {"text": "To, co robisz, ma znaczenie — sam decydujesz, jakie znaczenie chcesz wywrzeć.", "author": "Jane Goodall", "note": ""},
    {"text": "W świecie zalewu informacji jasność myślenia staje się potęgą.", "author": "Yuval Noah Harari", "note": "parafraza"},
    {"text": "Skupienie uwagi to jedna z najrzadszych i najcenniejszych umiejętności naszych czasów.", "author": "Cal Newport", "note": "parafraza"},
]


def message_for(day: date) -> dict[str, str]:
    """Deterministyczne hasło dnia dla podanej daty lokalnej."""
    return DAILY_MESSAGES[day.toordinal() % len(DAILY_MESSAGES)]
