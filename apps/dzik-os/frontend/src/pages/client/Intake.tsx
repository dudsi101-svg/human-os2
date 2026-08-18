import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, getUser } from "../../api";
import { WEEKDAYS } from "../../dates";
import { ErrorBox, SectionLabel, TopBar } from "../../components";

/** Ankieta startowa (wywiad) — klient sam wypełnia strukturalny wywiad,
 * który zasila profil z proweniencją CLIENT_DECLARED (append-only).
 * Pola zdrowotne (kontuzje, alergie) zapisywane jako wrażliwe.
 * Obowiązkowy jest wyłącznie cel — reszta dobrowolna. */
export default function Intake() {
  const user = getUser()!;
  const navigate = useNavigate();
  const [goal, setGoal] = useState("");
  const [experience, setExperience] = useState("");
  const [days, setDays] = useState<number[]>([]);
  const [equipment, setEquipment] = useState("");
  const [dietPrefs, setDietPrefs] = useState("");
  const [allergies, setAllergies] = useState("");
  const [injuries, setInjuries] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const fields = [
        { field_key: "cel_glowny", value: goal, sensitive: false },
        experience && { field_key: "doswiadczenie", value: experience, sensitive: false },
        days.length > 0 && {
          field_key: "dni_treningowe",
          value: days.map((d) => WEEKDAYS[d - 1]).join(", "),
          sensitive: false,
        },
        equipment && { field_key: "sprzet", value: equipment, sensitive: false },
        dietPrefs && { field_key: "preferencje_zywieniowe", value: dietPrefs, sensitive: true },
        allergies && { field_key: "alergie", value: allergies, sensitive: true },
        injuries && { field_key: "urazy", value: injuries, sensitive: true },
      ].filter(Boolean);
      await api.put(`/api/clients/${user.id}/profile`, fields);
      await api.post(`/api/clients/${user.id}/goals`, { title: goal, kind: "MAIN" });
      navigate("/", { replace: true });
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="page">
      <TopBar title="Wywiad startowy" />
      <p className="dim" style={{ marginTop: -6 }}>
        Kilka pytań, dzięki którym trener od razu dopasuje plan do Ciebie.
        Obowiązkowy jest tylko cel — resztę możesz uzupełnić później w
        Profilu. Wszystko, co wpiszesz, należy do Ciebie i widzi to tylko
        Twój trener (za Twoją zgodą).
      </p>
      <p className="dim">
        Wolisz przejść to jak rozmowę — jedno pytanie na raz, z wyjaśnieniem,
        po co jest potrzebne? <Link to="/rozmowa">Przejdź do rozmowy startowej</Link>.
        Ten formularz zostaje jako pełnoprawna alternatywa; obie drogi
        zapisują dokładnie te same pola profilu.
      </p>
      <form className="card" onSubmit={submit}>
        <h2 className="sr-only">Pytania wywiadu</h2>
        <SectionLabel n={1} title="Cel" />
        <label htmlFor="in-goal">Twój główny cel *</label>
        <input id="in-goal" required value={goal} placeholder="np. redukcja 6 kg do wakacji"
          onChange={(e) => setGoal(e.target.value)} />

        <SectionLabel n={2} title="Trening" />
        <label htmlFor="in-exp">Doświadczenie</label>
        <select id="in-exp" value={experience} onChange={(e) => setExperience(e.target.value)}>
          <option value="">— wybierz —</option>
          <option>Zaczynam od zera</option>
          <option>Trenowałem(-am) kiedyś, wracam po przerwie</option>
          <option>Trenuję regularnie do 2 lat</option>
          <option>Trenuję regularnie ponad 2 lata</option>
        </select>
        <span style={{ display: "block", fontSize: "0.85rem", color: "var(--text-dim)", margin: "10px 0 4px" }} id="in-days-label">
          Dni, w które możesz trenować
        </span>
        <div className="row" style={{ flexWrap: "wrap", gap: 4 }} role="group" aria-labelledby="in-days-label">
          {WEEKDAYS.map((w, i) => (
            <button type="button" key={i}
              className="btn btn--ghost btn--small"
              aria-pressed={days.includes(i + 1)}
              style={days.includes(i + 1)
                ? { background: "var(--accent)", color: "var(--accent-ink)" } : {}}
              onClick={() => setDays(days.includes(i + 1)
                ? days.filter((d) => d !== i + 1) : [...days, i + 1])}>
              {w}
            </button>
          ))}
        </div>
        <label htmlFor="in-equipment">Dostępny sprzęt / miejsce treningu</label>
        <input id="in-equipment" value={equipment} placeholder="np. siłownia komercyjna / hantle w domu"
          onChange={(e) => setEquipment(e.target.value)} />

        <SectionLabel n={3} title="Żywienie i zdrowie" />
        <label htmlFor="in-dietprefs">Preferencje żywieniowe</label>
        <input id="in-dietprefs" value={dietPrefs} placeholder="np. nie jem ryb; lubię proste posiłki"
          onChange={(e) => setDietPrefs(e.target.value)} />
        <label htmlFor="in-allergies">Alergie i nietolerancje</label>
        <input id="in-allergies" value={allergies} placeholder="np. orzechy, laktoza"
          onChange={(e) => setAllergies(e.target.value)} />
        <label htmlFor="in-injuries">Kontuzje i ograniczenia zdrowotne</label>
        <textarea id="in-injuries" value={injuries}
          placeholder="np. przebyty uraz barku — unikam wyciskania za głowę"
          onChange={(e) => setInjuries(e.target.value)} />
        <small className="dim">
          Pola zdrowotne są oznaczone jako wrażliwe — w razie wątpliwości
          zdrowotnych skonsultuj się z lekarzem; aplikacja nie zastępuje
          porady medycznej.
        </small>

        <ErrorBox error={error} />
        <div className="row" style={{ marginTop: 12 }}>
          <button className="btn" disabled={busy}>
            {busy ? "Zapisywanie…" : "Zapisz wywiad"}
          </button>
          <button type="button" className="btn btn--ghost" onClick={() => navigate("/")}>
            Później
          </button>
        </div>
      </form>
    </div>
  );
}
