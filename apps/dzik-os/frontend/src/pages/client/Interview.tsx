import { RozmowaPage } from "./Onboarding";

/** Głęboki wywiad — drugi przepływ tego samego ekranu rozmowy.
 *
 * Scenariusz (46 pytań w 9 modułach) jest serwerowy
 * (dzik_os/interview_flow.py); różnice względem rozmowy startowej to
 * wyłącznie ścieżka API, tytuł i karta wstępu. Podsumowanie wywiadu jest
 * zawsze deterministyczne — nic nie jest wysyłane do dostawcy modelu. */
export default function Interview() {
  return (
    <RozmowaPage
      apiPath="interview"
      healthModuleStepId="gw_c1"
      title="Głęboki wywiad"
      introTitle="Porozmawiajmy głębiej"
      intro={
        <>
          <p className="dim">
            Rozmowa startowa powiedziała trenerowi, CO budujemy. Ten wywiad
            odpowiada na pytanie, dlaczego wcześniej bywało trudno i co tym
            razem ma być inaczej: motywacja, historia, sen, stres, jedzenie
            i logistyka Twojego tygodnia.
          </p>
          <p className="dim">
            To dłuższa rozmowa — kilkadziesiąt pytań. Każde możesz pominąć,
            każde wyjaśnia, po co jest, a przerwać i wrócić możesz
            w dowolnym momencie, także z innego urządzenia.
          </p>
          <p className="dim">
            To nie jest wywiad medyczny. Pytania o zdrowie służą wyłącznie
            temu, żeby plan Ci nie zaszkodził — w sprawach zdrowia decyduje
            lekarz.
          </p>
        </>
      }
    />
  );
}
