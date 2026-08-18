/**
 * Polska odmiana rzeczownika przez liczbę.
 *
 * Polski ma trzy formy, nie dwie: 1 jednostka, 2–4 jednostki, 5+ jednostek.
 * Zasada dotyczy też liczb dwucyfrowych, ale z wyjątkiem nastek — 12 to
 * „jednostek", nie „jednostki".
 */
export function odmien(
  n: number,
  jedna: string,
  kilka: string,
  wiele: string,
): string {
  const abs = Math.abs(n);
  if (abs === 1) return jedna;
  const dziesiatki = abs % 100;
  const jednosci = abs % 10;
  if (jednosci >= 2 && jednosci <= 4 && !(dziesiatki >= 12 && dziesiatki <= 14)) {
    return kilka;
  }
  return wiele;
}

/** Liczba wraz z odmienionym rzeczownikiem, np. „2 jednostki”. */
export function ile(n: number, jedna: string, kilka: string, wiele: string): string {
  return `${n} ${odmien(n, jedna, kilka, wiele)}`;
}
