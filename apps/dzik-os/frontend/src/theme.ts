// Motyw aplikacji (0.74.0): dwa kompletne motywy do wyboru użytkownika —
// „Ciemny (czarno-zielony)” (domyślny, marka) i „Jasny (czerwono-biały)”.
//
// Mechanizm jest celowo najprostszy z możliwych: jeden atrybut na <html>
// (`data-theme`), który przełącza blok tokenów w styles.css, plus
// <meta name="theme-color"> dla paska przeglądarki/PWA. Wybór żyje w dwóch
// miejscach: na urządzeniu (localStorage — działa też na /login, zanim
// serwer cokolwiek powie) i na koncie (pole `theme` w ustawieniach
// powiadomień; po zalogowaniu wartość z serwera nadpisuje lokalną).
//
// CSP (`style-src 'self'`) nie dopuszcza stylów inline, a `index.html` nie
// może mieć skryptu inline — dlatego atrybut ustawia `main.tsx` przed
// `createRoot`, gdy arkusz jest już załadowany (mignięcie praktycznie zerowe:
// pierwsza farba React dzieje się już z właściwym motywem).
//
// Bez zależności od DOM w funkcjach czystych — testowane w scripts/test-theme.mjs.

export type Motyw = "ciemny" | "czerwony";

export const MOTYWY: readonly Motyw[] = ["ciemny", "czerwony"] as const;
export const MOTYW_DOMYSLNY: Motyw = "ciemny";
/** Klucz w localStorage — świadomie NIE czyszczony przez clearSession (preferencja
 * urządzenia, nie stan sesji; motyw ma obowiązywać także na ekranie logowania). */
export const KLUCZ_MOTYWU = "dzik_theme";

/** Kolor paska przeglądarki per motyw (= `--bg` z styles.css). */
export const KOLOR_PASKA: Record<Motyw, string> = {
  ciemny: "#0b0d0f",
  czerwony: "#FFFFFF",
};

/** Nazwy w UI (decyzja domyślna z pakietu 14.09, pyt. 5). */
export const NAZWY_MOTYWOW: Record<Motyw, { nazwa: string; opis: string }> = {
  ciemny: { nazwa: "Ciemny (czarno-zielony)", opis: "Domyślny — czytelny na siłowni." },
  czerwony: { nazwa: "Jasny (czerwono-biały)", opis: "Biel, grafit i czerwień marki." },
};

/** Czy wartość (z localStorage, z serwera, z URL…) jest jednym z motywów. */
export function jestMotywem(v: unknown): v is Motyw {
  return typeof v === "string" && (MOTYWY as readonly string[]).includes(v);
}

/** Rozstrzygnięcie: wartość z serwera (jeśli poprawna) wygrywa nad lokalną,
 * lokalna nad domyślną. Czysta funkcja — łatwa do testu bez DOM. */
export function rozstrzygnijMotyw(zSerwera: unknown, lokalny: unknown): Motyw {
  if (jestMotywem(zSerwera)) return zSerwera;
  if (jestMotywem(lokalny)) return lokalny;
  return MOTYW_DOMYSLNY;
}

/** Zastosowanie motywu do dokumentu: atrybut na <html> + meta theme-color.
 * Dla ciemnego atrybut jest usuwany (ciemny = brak atrybutu = dokładnie stan
 * sprzed 0.74.0 — piksel w piksel). */
export function zastosujMotyw(doc: Document, motyw: Motyw): void {
  if (motyw === MOTYW_DOMYSLNY) delete doc.documentElement.dataset.theme;
  else doc.documentElement.dataset.theme = motyw;
  const meta = doc.querySelector<HTMLMetaElement>('meta[name="theme-color"]');
  if (meta) meta.content = KOLOR_PASKA[motyw];
}

function odczytajLokalny(): unknown {
  try {
    return localStorage.getItem(KLUCZ_MOTYWU);
  } catch {
    return null; // tryb prywatny / zablokowany magazyn — motyw domyślny
  }
}

/** Motyw obowiązujący na urządzeniu (localStorage → domyślny). */
export function odczytajMotyw(): Motyw {
  return rozstrzygnijMotyw(null, odczytajLokalny());
}

/** Ustawia motyw: dokument + zapis na urządzeniu. Zapis na koncie robi
 * wywołujący (Wyglad.tsx) — ta funkcja nie zna API ani sesji. */
export function ustawMotyw(motyw: Motyw): void {
  zastosujMotyw(document, motyw);
  try {
    localStorage.setItem(KLUCZ_MOTYWU, motyw);
  } catch {
    /* bez magazynu motyw obowiązuje do przeładowania */
  }
}

/** Po zalogowaniu: wartość z konta (jeśli jest) nadpisuje lokalną i trafia
 * do localStorage, żeby /login po wylogowaniu też był w wybranym motywie. */
export function zsynchronizujMotyw(zSerwera: unknown): Motyw {
  const motyw = rozstrzygnijMotyw(zSerwera, odczytajLokalny());
  if (jestMotywem(zSerwera)) ustawMotyw(motyw);
  else zastosujMotyw(document, motyw);
  return motyw;
}
