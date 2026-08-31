/* Publiczna informacja o przetwarzaniu danych (audyt P0-1, 0.53.5).
   Treść oparta o docs/POLITYKA_PRYWATNOSCI_SZKIC.md, z wypełnionymi
   danymi administratora (jawne dane rejestrowe spółki z KRS) i opisem
   zgodnym z FAKTYCZNYM działaniem aplikacji. Formalne zatwierdzenie
   przez administratora danych/prawnika — odnotowane jako otwarte
   w STAN_PRZEKAZANIA (pozycja W3 planu audytowego). */

const DATA_WERSJI = "26 sierpnia 2026";

export default function Privacy() {
  return (
    <div className="landing privacy">
      <header className="landing-top">
        <div className="landing-top__inner">
          <a href="/" className="landing-top__name" style={{ textDecoration: "none" }}>
            ← Dzik OS
          </a>
          <span className="landing-top__spacer" />
          <a className="btn btn--ghost landing-top__login" href="/login">Zaloguj się</a>
        </div>
      </header>

      <section className="landing-section">
        <h1 className="privacy__tytul">Informacja o przetwarzaniu danych osobowych</h1>
        <p className="landing-gallery__intro">Wersja z dnia {DATA_WERSJI}</p>

        <div className="card landing-card privacy__blok">
          <h2>1. Administrator danych</h2>
          <p>
            Administratorem Twoich danych osobowych jest <b>LUBELSKI DZIK
            sp. z o.o.</b>, ul. Wschodnia 6/6, 20-015 Lublin — trener
            prowadzący usługę treningową w aplikacji Dzik OS.
            Kontakt w sprawach danych osobowych:{" "}
            <a href="mailto:lubelskidzikk@gmail.com">lubelskidzikk@gmail.com</a>,
            tel. +48 570 477 540.
          </p>
        </div>

        <div className="card landing-card privacy__blok">
          <h2>2. Jakie dane przetwarzamy i po co</h2>
          <p><b>Formularz kontaktowy na stronie:</b> imię, adres e-mail,
          opcjonalnie telefon i treść wiadomości — wyłącznie po to, żeby
          odpowiedzieć na Twoje zapytanie (art. 6 ust. 1 lit. b/f RODO —
          działania przed zawarciem umowy). Prosimy: <b>nie wpisuj w
          formularzu informacji o zdrowiu, diagnoz ani dokumentacji
          medycznej</b> — takie ustalenia prowadzimy bezpiecznie w
          aplikacji, po założeniu konta i wyrażeniu wyraźnej zgody.</p>
          <p><b>Konto podopiecznego w aplikacji:</b> dane konta (e-mail,
          imię), a po wyrażeniu odrębnych, dobrowolnych zgód — dane
          o treningu, pomiarach, żywieniu, samopoczuciu i zdjęcia
          sylwetki (art. 9 ust. 2 lit. a RODO — wyraźna zgoda na dane
          szczególnej kategorii). Każdą zgodę wyrażasz samodzielnie
          w aplikacji i możesz ją cofnąć w każdej chwili — cofnięcie
          nie wpływa na zgodność wcześniejszego przetwarzania.</p>
        </div>

        <div className="card landing-card privacy__blok">
          <h2>3. Odbiorcy danych</h2>
          <p>Dane są przechowywane na serwerach <b>Fly.io</b> (hosting
          aplikacji; maszyna i wolumen danych w regionie Frankfurt, UE).
          Po włączeniu powiadomień e-mail dostawcą doręczenia jest
          serwer pocztowy administratora. Powiadomienia push doręcza
          dostawca push Twojej przeglądarki. Nie sprzedajemy danych
          i nie udostępniamy ich w celach marketingowych.</p>
        </div>

        <div className="card landing-card privacy__blok">
          <h2>4. Jak długo przechowujemy dane</h2>
          <p>Dane z formularza kontaktowego — do zakończenia korespondencji
          w sprawie zapytania. Dane konta — przez czas współpracy;
          po jej zakończeniu możesz zażądać usunięcia albo anonimizacji
          konta w aplikacji (Profil → Dokumenty i zgody). Kopie zapasowe
          są rotowane automatycznie (do 14 najnowszych archiwów dziennych
          plus migawki infrastruktury); żądanie usunięcia realizowane jest
          także po ewentualnym odtworzeniu kopii.</p>
        </div>

        <div className="card landing-card privacy__blok">
          <h2>5. Twoje prawa</h2>
          <p>Masz prawo dostępu do danych, ich sprostowania, usunięcia,
          ograniczenia przetwarzania, przenoszenia (eksport danych
          dostępny wprost w aplikacji), sprzeciwu oraz cofnięcia każdej
          zgody. Realizacja: samodzielnie w aplikacji albo e-mailem na
          adres kontaktowy. Masz też prawo wniesienia skargi do Prezesa
          Urzędu Ochrony Danych Osobowych (uodo.gov.pl).</p>
        </div>

        <div className="card landing-card privacy__blok">
          <h2>6. Bezpieczeństwo, cookies, małoletni</h2>
          <p>Połączenie jest szyfrowane (HTTPS), konta mogą włączyć
          weryfikację dwuetapową (na czas pilotażu nieobowiązkową),
          dostęp do danych
          wymaga aktywnej współpracy i zgody, a operacje na danych są
          rejestrowane w niemodyfikowalnym dzienniku audytu. Strona
          i aplikacja <b>nie używają ciasteczek marketingowych ani
          narzędzi śledzących</b> — wyłącznie techniczne cookie sesji po
          zalogowaniu. Usługa jest przeznaczona dla osób pełnoletnich.</p>
        </div>

        <p className="privacy__stopka-notka">
          Dokument opisuje faktyczne działanie aplikacji w wersji z dnia
          {" "}{DATA_WERSJI}. Pytania i wnioski dotyczące danych:{" "}
          <a href="mailto:lubelskidzikk@gmail.com">lubelskidzikk@gmail.com</a>.
        </p>
      </section>

      <footer className="landing-footer">
        <p>© {new Date().getFullYear()} Dzik OS · <a href="/">strona główna</a> · <a href="/prywatnosc">prywatność</a></p>
      </footer>
    </div>
  );
}
