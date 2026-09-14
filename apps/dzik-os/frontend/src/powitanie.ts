/** Powitanie wg lokalnej pory dnia urządzenia (0.63.0). Bez imienia, gdy go nie ma. */
export function powitanie(hour: number, imie?: string | null): string {
  const h = ((Math.floor(hour) % 24) + 24) % 24;
  const slowo = h >= 5 && h < 12 ? "Dzień dobry" : h >= 12 && h < 18 ? "Cześć" : "Dobry wieczór";
  const i = (imie ?? "").trim();
  return i ? `${slowo}, ${i}` : slowo;
}
