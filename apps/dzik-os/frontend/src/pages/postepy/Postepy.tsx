import { FormEvent, useState } from "react";
import { api, getUser } from "../../api";
import { localToday } from "../../dates";
import { ErrorBox, TopBar } from "../../components";
import { KIND_LABELS } from "../../types";
import { PanelPostepow } from "./PanelPostepow";

/* Zakładka „Postępy” klienta (0.66.0, /monitoring): zastępuje „Raport” w
   nawigacji (raport przechodzi do „Więcej”) i wchłania dawne „Postępy”
   (pomiary, zdjęcia) jako sekcje Konsekwencja/Sylwetka. Formularz pomiaru
   zostaje w sekcji Sylwetka — znika razem z nią u klienta z flagą zdrowotną
   (o tym decyduje serwer). */
export default function Postepy() {
  const user = getUser()!;
  return (
    <div className="page">
      <TopBar title="Postępy" />
      <PanelPostepow tryb="klient" clientId={user.id}
        dodatki={(odswiez) => <FormularzPomiaru clientId={user.id} onZapis={odswiez} />} />
    </div>
  );
}

function FormularzPomiaru({ clientId, onZapis }: { clientId: string; onZapis: () => void }) {
  const [kind, setKind] = useState("weight");
  const [value, setValue] = useState("");
  const [unit, setUnit] = useState("kg");
  const [error, setError] = useState<string | null>(null);
  async function zapisz(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await api.post(`/api/clients/${clientId}/measurements`, {
        kind, value: Number(value.replace(",", ".")), unit, measured_at: localToday(),
      });
      setValue("");
      onZapis();
    } catch (err) {
      setError((err as Error).message);
    }
  }
  return (
    <form onSubmit={zapisz} style={{ marginTop: 10 }}>
      <h3>Dodaj pomiar</h3>
      <ErrorBox error={error} />
      <div className="field-row-3">
        <div>
          <label htmlFor="pm-kind">Rodzaj</label>
          <select id="pm-kind" value={kind} onChange={(e) => { setKind(e.target.value); setUnit(e.target.value === "weight" ? "kg" : "cm"); }}>
            {Object.entries(KIND_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        </div>
        <div>
          <label htmlFor="pm-value">Wartość</label>
          <input id="pm-value" inputMode="decimal" required value={value} onChange={(e) => setValue(e.target.value)} />
        </div>
        <div>
          <label htmlFor="pm-unit">Jednostka</label>
          <input id="pm-unit" value={unit} onChange={(e) => setUnit(e.target.value)} />
        </div>
      </div>
      <div style={{ marginTop: 8 }}><button className="btn btn--ghost btn--small">Zapisz pomiar</button></div>
      <small className="dim">Waga w zakładce to zawsze średnia z 7 dni — pojedynczy pomiar nie jest „Twoją wagą”.</small>
    </form>
  );
}
