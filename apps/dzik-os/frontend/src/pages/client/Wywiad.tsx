import { useCallback, useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api, getUser } from "../../api";
import { plDateTime } from "../../dates";
import { ErrorBox, Spinner, TopBar } from "../../components";
import { WywiadPodsumowanie, WywiadPrzeslanie, WywiadStan, WywiadTyp, WywiadyPrzeglad } from "../../types";
import Formularz from "../wywiad/Formularz";
import { opisWersji, PasekPostepu, PodsumowanieWywiadu, StatusBadges, TYP_LABEL } from "../wywiad/wspolne";

/**
 * Zakładka „Wywiad” klienta (0.59.0): dwie karty (wstępny, głęboki) ze
 * statusem wypełnienia, przeglądu i aktualności, postępem i datą; formularz
 * sekcjami z zapisem częściowym; podsumowanie deterministyczne; prośby
 * trenera o uzupełnienie. Rozmowa krok po kroku (/rozmowa, /wywiad/rozmowa)
 * pozostaje alternatywnym kanałem — zatwierdzona trafia tu jako wersja.
 */
export default function Wywiad() {
  const user = getUser()!;
  const [params, setParams] = useSearchParams();
  const typ = params.get("typ") as WywiadTyp | null;
  const [dane, setDane] = useState<WywiadyPrzeglad | null>(null);
  const [pods, setPods] = useState<WywiadPodsumowanie | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);

  const zaladuj = useCallback(() => {
    setError(null);
    api.get<WywiadyPrzeglad>(`/api/clients/${user.id}/wywiady`).then(setDane).catch((e) => setError(e.message));
    api.get<WywiadPodsumowanie>(`/api/clients/${user.id}/wywiady/podsumowanie`).then(setPods).catch(() => setPods(null));
  }, [user.id]);
  useEffect(zaladuj, [zaladuj, typ]);

  if (typ === "wstepny" || typ === "gleboki") {
    const stan = dane?.wywiady.find((w) => w.typ === typ);
    return (
      <div className="page">
        <TopBar title={TYP_LABEL[typ]} right={<Link className="btn btn--ghost btn--small" to="/wywiad">← Wywiad</Link>} />
        {dane === null && !error ? <Spinner /> : (
          <Formularz clientId={user.id} typ={typ} tryb="klient" doprecyzowania={stan?.open_clarifications ?? []}
            maWersje={(stan?.submissions_count ?? 0) > 0}
            onZamknij={() => setParams({})}
            onPrzeslano={(r) => {
              setInfo(`Przesłano wersję ${r.version_no} — trener zobaczy ją w swoim panelu.`
                + (r.review_tasks.length ? " Zmieniły się fakty istotne dla planu; trener dostanie zadanie sprawdzenia planu." : ""));
              setParams({});
            }} />
        )}
      </div>
    );
  }

  return (
    <div className="page">
      <TopBar title="Wywiad" />
      {info && <p className="alert alert--info" role="status">{info} <button type="button" className="btn btn--ghost btn--small" aria-label="Zamknij komunikat" onClick={() => setInfo(null)}>×</button></p>}
      {error && <ErrorBox error={error} onRetry={zaladuj} />}
      {!dane && !error && <Spinner />}
      {dane && !dane.access.has_coach && (
        <p className="alert alert--warn">Nie masz jeszcze przypisanego trenera. Możesz wypełniać wywiad — zobaczy go trener, z którym nawiążesz współpracę.</p>
      )}
      {dane && dane.access.missing_domains.length > 0 && (
        <p className="alert alert--warn">
          Pytania o {dane.access.missing_domains.map((d) => d === "health_data" ? "zdrowie" : "żywienie i alergie").join(" oraz ")} są wyłączone,
          bo nie wyraziłeś(-aś) zgody na tę kategorię danych. Zmienisz to w <Link to="/profil">Profil → Prywatność i zgody</Link>.
        </p>
      )}
      {dane?.wywiady.map((w) => <KartaWywiadu key={w.typ} w={w} clientId={user.id} onOtworz={() => setParams({ typ: w.typ })} />)}
      {pods && (
        <div className="card">
          <h2>Podsumowanie</h2>
          <PodsumowanieWywiadu d={pods} klientId={user.id} linkDoWywiadu={(t) => `/wywiad?typ=${t}`} />
        </div>
      )}
      <div className="card">
        <h3 style={{ marginTop: 0 }}>Wolisz rozmowę krok po kroku?</h3>
        <p className="dim">Te same pytania możesz przejść jako rozmowę: <Link to="/rozmowa">rozmowa startowa</Link> (wstępny)
          lub <Link to="/wywiad/rozmowa">głęboki wywiad</Link>. Zatwierdzona rozmowa pojawia się tutaj jako wersja.</p>
      </div>
    </div>
  );
}

function KartaWywiadu({ w, clientId, onOtworz }: { w: WywiadStan; clientId: string; onOtworz: () => void }) {
  const [hist, setHist] = useState<WywiadPrzeslanie[] | null>(null);
  const przycisk = w.submission_status === "not_started" ? "Rozpocznij"
    : w.submission_status === "draft" ? "Kontynuuj" : "Aktualizuj odpowiedzi";
  const cel = w.typ === "wstepny"
    ? "Pozwala trenerowi zacząć: cel, punkt wyjścia, ramy treningu, ograniczenia, odżywianie."
    : "Pogłębia historię, regenerację, organizację i motywację. Nie jest wymagany od każdego.";
  return (
    <div className="card">
      <div className="row row--between">
        <h2 style={{ margin: 0 }}>{w.title}</h2>
        <StatusBadges s={w} />
      </div>
      <p className="dim" style={{ marginBottom: 4 }}>{cel}</p>
      <small className="dim">{opisWersji(w)}</small>
      <PasekPostepu p={w.progress} />
      {w.open_clarifications.length > 0 && (
        <p className="alert alert--info" role="status">
          <b>Trener prosi o uzupełnienie</b> ({w.open_clarifications.length}): {w.open_clarifications.map((c) => c.message || "wskazane pytania").join("; ")}
        </p>
      )}
      {w.last_submission?.review?.outcome === "REVIEWED" && (
        <small className="dim">Trener przejrzał wersję {w.last_submission.version_no} ({plDateTime(w.last_submission.review.created_at)}) — to potwierdzenie zapoznania się, nie ocena.</small>
      )}
      <div className="row" style={{ marginTop: 10, gap: 8 }}>
        <button type="button" className="btn btn--small" onClick={onOtworz}>{przycisk}</button>
        {w.submissions_count > 0 && (
          <button type="button" className="btn btn--ghost btn--small" onClick={() => hist ? setHist(null)
            : api.get<{ submissions: WywiadPrzeslanie[] }>(`/api/clients/${clientId}/wywiady/${w.typ}/historia`).then((r) => setHist(r.submissions)).catch(() => setHist([]))}>
            {hist ? "Ukryj historię" : `Historia wersji (${w.submissions_count})`}
          </button>
        )}
      </div>
      {hist && (
        <ul style={{ fontSize: "0.85rem", paddingLeft: 18, marginBottom: 0 }}>
          {hist.map((s) => (
            <li key={s.id}>
              wersja {s.version_no} · {plDateTime(s.submitted_at)}{s.migrated ? " · przeniesiona z rozmowy" : ""}{s.collection_mode === "WSPOLNIE" ? " · wspólnie z trenerem" : ""}
              {s.review ? ` · ${s.review.outcome === "REVIEWED" ? "przejrzana" : "prośba o doprecyzowanie"} ${plDateTime(s.review.created_at)}` : " · nieprzejrzana"}
              {" · odpowiedzi: "}{s.answers.filter((a) => !a.skipped && a.value).length}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
