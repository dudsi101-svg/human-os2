import { FormEvent, ReactNode, useState } from "react";

/* Publiczna strona marketingowa (0.49.0) — widoczna na "/" dla
   niezalogowanych. Treść jest neutralna („trener personalny"); miejsca
   do personalizacji przez właściciela oznaczono komentarzami
   PERSONALIZACJA. Zero ciasteczek i śledzenia — jedyna interakcja
   z backendem to formularz zapytania (POST /api/public/lead). */

const ATUTY = [
  {
    tytul: "Plan treningowy pod Ciebie",
    opis:
      "Trening układany indywidualnie i modyfikowany na bieżąco — z opisem techniki, wideo i rysunkiem pracujących mięśni przy każdym ćwiczeniu.",
  },
  {
    tytul: "Dieta, którą da się odmierzyć",
    opis:
      "Plany żywieniowe z bazy ponad 2000 produktów, komponowane wg uznanych wzorców (śródziemnomorski, DASH), z gramaturami mierzalnymi w kuchni.",
  },
  {
    tytul: "Cotygodniowy raport",
    opis:
      "Raz w tygodniu krótki raport: samopoczucie, pomiary, zdjęcia sylwetki. Trener odpowiada na każdy — nic nie ginie w wiadomościach.",
  },
  {
    tytul: "Postępy czarno na białym",
    opis:
      "Wykresy siły i objętości, rekordy własne, porównywarka zdjęć — widzisz, co dają tygodnie pracy, zamiast zgadywać.",
  },
  {
    tytul: "Stały kontakt",
    opis:
      "Wiadomości (także głosowe), terminarz konsultacji i powiadomienia w aplikacji — pytania nie czekają do następnego treningu.",
  },
  {
    tytul: "Twoje dane pod kontrolą",
    opis:
      "Zgody RODO, eksport danych i pełna historia zmian. Aplikacja działa jak PWA — instalujesz ją z przeglądarki, bez sklepu.",
  },
];

/* Warstwa wizualna 0.65.0 → 0.72.0 (wariant czerwono-biały): kafel gradientowy,
   ikona SVG (siatka 24, bez emoji) i chipy przy każdym atucie — treść
   ATUTY bez zmian. */
type Kafel = "tile-red" | "tile-graphite" | "tile-coral";
const ATUTY_WIZ: { kafel: Kafel; ikona: keyof typeof IKONY; chipy: string[]; grafit?: boolean }[] = [
  { kafel: "tile-red", ikona: "hantel", chipy: ["Technika", "Wideo", "Mapa mięśni"] },
  { kafel: "tile-graphite", ikona: "miska", chipy: ["2000+ produktów", "Śródziemnomorska", "DASH"], grafit: true },
  { kafel: "tile-coral", ikona: "kartka", chipy: ["Samopoczucie", "Pomiary", "Zdjęcia"] },
  { kafel: "tile-red", ikona: "wykres", chipy: ["Siła", "Objętość", "Rekordy"] },
  { kafel: "tile-graphite", ikona: "dymek", chipy: ["Wiadomości głosowe", "Terminarz", "Powiadomienia"], grafit: true },
  { kafel: "tile-coral", ikona: "tarcza", chipy: ["RODO", "Eksport", "PWA"] },
];
const KAFLE_KROKOW: Kafel[] = ["tile-red", "tile-graphite", "tile-coral"];

/* Ikony liniowe (stroke currentColor/biały ustawia CSS kafla). */
const IKONY = {
  hantel: <><path d="M3 10v4M6 8v8M18 8v8M21 10v4M6 12h12" /></>,
  miska: <><path d="M3 12h18a9 9 0 0 1-18 0Z" /><path d="M8 12 15 4M12 21v-3" /></>,
  kartka: <><path d="M7 3h7l5 5v13H7Z" /><path d="M14 3v5h5M10 12h5M10 16h5" /></>,
  wykres: <><path d="M4 4v16h16" /><path d="M8 15l4-5 3 3 5-6" /></>,
  dymek: <><path d="M20 12a8 8 0 0 1-11.5 7.2L4 20l1-4.2A8 8 0 1 1 20 12Z" /></>,
  tarcza: <><path d="M12 3 5 6v6c0 4.5 3 7.5 7 9 4-1.5 7-4.5 7-9V6Z" /><path d="m9 12 2 2 4-4" /></>,
  telefon: <><path d="M5 4h4l2 5-2.5 1.5a11 11 0 0 0 5 5L15 13l5 2v4a2 2 0 0 1-2 2A16 16 0 0 1 3 6a2 2 0 0 1 2-2Z" /></>,
  koperta: <><path d="M3 6h18v12H3Z" /><path d="m3 7 9 6 9-6" /></>,
  gwiazda: <><path d="m12 3 2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1L3.2 9.5l6.1-.9Z" /></>,
  ptaszek: <><path d="m5 12 5 5 9-10" /></>,
  slupki: <><path d="M4 20h16M7 16v-5M12 16V8M17 16v-8" /></>,
};

function Ikona({ nazwa }: { nazwa: keyof typeof IKONY }) {
  return <svg viewBox="0 0 24 24" aria-hidden="true">{IKONY[nazwa]}</svg>;
}

function Strzalka() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth={2.4} strokeLinecap="round" strokeLinejoin="round">
      <path d="M5 12h14M13 6l6 6-6 6" />
    </svg>
  );
}

function Naglowek({ etykieta, tytul, opis }: { etykieta: string; tytul: ReactNode; opis?: ReactNode }) {
  return (
    <div className="sec-head">
      <div>
        <div className="eyebrow">{etykieta}</div>
        <h2 className="h2">{tytul}</h2>
      </div>
      {opis && <p className="sec-head__desc">{opis}</p>}
    </div>
  );
}

const KROKI = [
  {
    tytul: "Napisz do mnie",
    opis: "Wypełnij formularz poniżej — opisz cel i dotychczasowe doświadczenie. Odpowiadam na każde zgłoszenie.",
  },
  {
    tytul: "Ankieta i plan startowy",
    opis: "Po rozmowie dostajesz zaproszenie do aplikacji, wypełniasz ankietę startową, a ja układam pierwszy plan.",
  },
  {
    tytul: "Trenujemy i korygujemy",
    opis: "Trenujesz według planu, raportujesz raz w tygodniu, a plan i dieta ewoluują razem z Twoimi wynikami.",
  },
];

const FAQ = [
  {
    p: "Czy współpraca jest zdalna?",
    o: "Tak — plan, dieta, raporty i kontakt działają w aplikacji, więc trenujesz gdzie chcesz. Możliwe są też konsultacje na żywo, jeśli jesteś w okolicy.",
  },
  {
    p: "Nie mam doświadczenia na siłowni. Czy to dla mnie?",
    o: "Tak. Każde ćwiczenie w planie ma opis techniki, najczęstsze błędy i warianty łatwiejsze/trudniejsze — plan zaczyna się od Twojego poziomu, nie od cudzego.",
  },
  {
    p: "Jak wygląda dieta?",
    o: "Dostajesz plan posiłków z konkretnymi produktami i gramaturami, dopasowany do Twoich kalorii i preferencji. Produkty można wymieniać — dieta ma być do utrzymania, nie do przetrwania.",
  },
  {
    p: "Co z moimi danymi?",
    o: "Dane zbierane są wyłącznie za Twoją zgodą, masz do nich wgląd i możesz je wyeksportować albo usunąć. Aplikacja nie używa ciasteczek marketingowych ani zewnętrznych trackerów.",
  },
];

export default function Landing() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [message, setMessage] = useState("");
  const [website, setWebsite] = useState(""); // honeypot — ukryte pole
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const r = await fetch("/api/public/lead", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, email, phone, message, website }),
      });
      if (r.status === 429) {
        setError("Zbyt wiele zgłoszeń z tego urządzenia. Spróbuj ponownie za godzinę.");
        return;
      }
      if (!r.ok) {
        setError("Sprawdź, czy pola są wypełnione poprawnie (wiadomość: co najmniej 10 znaków).");
        return;
      }
      setSent(true);
    } catch {
      setError("Brak połączenia z serwerem. Spróbuj ponownie.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="landing landing--czerwony">
      <header className="landing-top">
        <div className="landing-top__inner">
          <img src="/icons/boar-mark-red.png" alt="" className="landing-top__logo" />
          <span className="landing-top__name">Dzik OS</span>
          <nav className="landing-top__nav" aria-label="Sekcje strony">
            <a href="#oferta">Oferta</a>
            <a href="#jak-to-dziala">Jak zaczynamy</a>
            <a href="#aplikacja">Aplikacja</a>
            <a href="#o-trenerze">Trener</a>
            <a href="#faq">FAQ</a>
          </nav>
          <span className="landing-top__spacer" />
          <a className="btn btn--ghost btn--sm" href="/login">
            Zaloguj się
          </a>
        </div>
      </header>

      <section className="landing-hero">
        <div className="wrap landing-hero__grid">
          <div className="landing-hero__copy">
            <div className="eyebrow">Trening personalny · Lublin i online</div>
            {/* PERSONALIZACJA: nagłówek i podtytuł — wstaw własne hasło. */}
            <h1>Trening prowadzony, nie <span className="mark">zgadywany</span></h1>
            <p className="landing-hero__sub">
              Indywidualny plan treningowy i dieta, cotygodniowe raporty
              i stały kontakt z trenerem — wszystko w jednej aplikacji,
              którą masz w telefonie.
            </p>
            <div className="landing-hero__cta">
              <a className="btn btn--primary" href="#kontakt">Umów bezpłatną konsultację <Strzalka /></a>
              <a className="btn btn--ghost" href="/login">Mam już konto</a>
            </div>
            <ul className="landing-proof" role="list">
              <li className="landing-proof__item"><b>IFBB PRO</b><small>trener i zawodnik</small></li>
              <li className="landing-proof__sep" aria-hidden="true" />
              <li className="landing-proof__item"><b>30 000+</b><small>społeczność na Instagramie</small></li>
              <li className="landing-proof__sep" aria-hidden="true" />
              <li className="landing-proof__item"><b>nawet <span className="nowrap">−12 kg</span></b><small>w 20 tygodni, bez utraty mięśni</small></li>
            </ul>
          </div>
          <div className="landing-panel dark" aria-hidden="true">
            {/* Scena: dekoracje przycięte do panelu (0.72.0, P1-a — pierścień 520 px
                i plama 440 px wystawały poza panel i przewijały stronę w pasie 900–1150 px).
                Karty-powiadomienia zostają poza sceną: mają wystawać poza krawędź. */}
            <div className="landing-panel__scene">
              <span className="landing-panel__tag">LUBELSKI DZIK</span>
              <span className="landing-panel__raster" />
              <span className="landing-panel__blob" />
              <span className="landing-panel__ring" />
              {/* Obraz LCP na telefonie/tablecie: wymiary i priorytet pobierania (0.72.0).
                  `fetchpriority` małymi literami przez spread — React 18 przepuszcza nieznane
                  atrybuty pisane małymi literami bez ostrzeżenia, a camelCase zna dopiero React 19. */}
              <img
                src="/icons/boar-hero-red.png"
                alt=""
                className="landing-panel__boar"
                width={560}
                height={721}
                decoding="async"
                {...{ fetchpriority: "high" }}
              />
            </div>
            {/* PERSONALIZACJA: dane na kartach są przykładowe — treść NIEPOTWIERDZONA przez
                właściciela (zlecenie 3, pytanie 14), dlatego każda karta nosi etykietę „przykład”. */}
            <div className="card landing-panel__card landing-panel__card--a">
              <small className="landing-panel__demo">przykład</small>
              <span className="icon icon--s tile-graphite"><Ikona nazwa="slupki" /></span>
              <span><b>Przysiad 110 kg</b><small>nowy rekord własny</small></span>
              <span className="landing-bars">
                <i style={{ height: 12, background: "#F5A3AB" }} /><i style={{ height: 18, background: "#F27F8A" }} />
                <i style={{ height: 22, background: "#EE6B77" }} /><i style={{ height: 26, background: "#E11D2E" }} />
                <i style={{ height: 34, background: "linear-gradient(180deg,#FF6B5A,#E11D2E)" }} />
              </span>
            </div>
            <div className="card landing-panel__card landing-panel__card--b">
              <small className="landing-panel__demo">przykład</small>
              <span className="icon icon--s tile-red"><Ikona nazwa="ptaszek" /></span>
              <span><b>Raport z tygodnia 8</b><small>Odpowiedź trenera: dziś 09:40</small></span>
            </div>
            <div className="card landing-panel__card landing-panel__card--c">
              <small className="landing-panel__demo">przykład</small>
              <span className="landing-dot" />
              <span>Dieta: 2300 kcal · 180 g białka</span>
            </div>
          </div>
        </div>
      </section>

      <section className="section" id="oferta">
        <div className="wrap">
          <Naglowek etykieta="Oferta" tytul="Co dostajesz we współpracy"
            opis="Sześć elementów, które w innych układach żyją w czatach, arkuszach i notatkach. Tu są w jednym miejscu — i wszystkie widzi trener." />
          <div className="landing-grid">
            {ATUTY.map((a, i) => (
              <div className="card landing-atut" key={a.tytul}>
                <span className={`icon leaf ${ATUTY_WIZ[i].kafel}`}><Ikona nazwa={ATUTY_WIZ[i].ikona} /></span>
                <div className="landing-atut__body">
                  <h3>{a.tytul}</h3>
                  <p>{a.opis}</p>
                  <div className="chips">
                    {ATUTY_WIZ[i].chipy.map((c) => (
                      <span className={ATUTY_WIZ[i].grafit ? "chip chip--graphite" : "chip"} key={c}>{c}</span>
                    ))}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="dark landing-steps-sec" id="jak-to-dziala">
        <span className="wm" aria-hidden="true">DZIK OS</span>
        <div className="wrap">
          <Naglowek etykieta="Jak zaczynamy" tytul="Trzy kroki do pierwszego planu"
            opis={<span className="landing-dark-desc">Bez sklepu z aplikacjami i bez arkuszy w wiadomościach. Zaczynasz od rozmowy, kończysz z planem w telefonie.</span>} />
          <ol className="landing-steps" role="list">
            {KROKI.map((k, i) => (
              <li className="card--dark" key={k.tytul}>
                <span className={`num leaf ${KAFLE_KROKOW[i]}`}>0{i + 1}</span>
                <h3>{k.tytul}</h3>
                <p>{k.opis}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section className="landing-app" id="aplikacja">
        <div className="wrap">
          <Naglowek etykieta="Aplikacja" tytul="Zobacz aplikację"
            opis={<span className="landing-dark-desc">Prawdziwe ekrany z danymi demonstracyjnymi — tak wygląda codzienna współpraca. Motyw wybierasz sam: ciemny na siłownię albo jasny czerwono-biały.</span>} />
          {/* Region z nazwą: na telefonie galeria przewija się poziomo i jest przystankiem fokusu. */}
          <div className="landing-gallery" role="region" aria-label="Ekrany aplikacji">
            {[
              { src: "/screens/dzisiaj.jpg", podpis: "Dzisiaj — Twój dzień w pigułce" },
              { src: "/screens/plan.jpg", podpis: "Plan treningowy z techniką" },
              { src: "/screens/dieta.jpg", podpis: "Dieta z gramaturami" },
              { src: "/screens/postepy.jpg", podpis: "Postępy i rekordy" },
            ].map((e) => (
              <figure key={e.src}>
                <img src={e.src} alt={e.podpis} width={780} height={1560} loading="lazy" />
                <figcaption>{e.podpis}</figcaption>
              </figure>
            ))}
          </div>
        </div>
      </section>

      <section className="section landing-about" id="o-trenerze">
        <div className="wrap landing-about__grid">
          <div className="landing-about__foto-wrap">
            <span className="landing-about__foto-bg tile-red" aria-hidden="true" />
            <img
              src="/icons/trener.jpg"
              alt="Łukasz Drygiel na treningu"
              className="landing-about__foto"
              width={1200}
              height={795}
              loading="lazy"
            />
            <div className="card landing-about__badge">
              <span className="icon icon--s tile-coral"><Ikona nazwa="gwiazda" /></span>
              <span><b>IFBB PRO</b><small>RAPTOR GYM, Lublin</small></span>
            </div>
          </div>
          <div className="landing-about__text">
            <div className="eyebrow">O trenerze</div>
            <h2 className="h2 landing-about__imie">
              Łukasz Drygiel — <span className="landing-about__ksywa">Lubelski Dzik</span>
            </h2>
            <p>
              Trener personalny i zawodnik scen sylwetkowych (IFBB PRO).
              Prowadzę podopiecznych na siłowni w Lublinie (RAPTOR GYM)
              i online — w całej Polsce. Na Instagramie towarzyszy mi
              społeczność ponad 30 tysięcy osób, ale każdą współpracę
              prowadzę osobiście: układam plan, czytam każdy raport
              i odpowiadam na każdą wiadomość.
            </p>
            <p>
              Mój konik to redukcja bez utraty mięśni — pomagam schudnąć
              nawet 12 kg w 20 tygodni, budując przy tym siłę i sylwetkę.
              Aplikacja Dzik OS to moje własne narzędzie pracy: powstała po
              to, żeby nic z naszej współpracy nie ginęło w czatach
              i arkuszach.
            </p>
            <div className="landing-stats">
              <div className="landing-stat landing-stat--red"><b>IFBB PRO</b><small>zawodnik scen sylwetkowych</small></div>
              <div className="landing-stat landing-stat--graphite"><b>30 000+</b><small>społeczność na Instagramie</small></div>
              <div className="landing-stat landing-stat--coral"><b>nawet <span className="nowrap">−12 kg</span></b><small>w 20 tygodni, bez utraty mięśni</small></div>
            </div>
            <p className="landing-about__social">
              <a className="btn btn--ghost btn--pill" href="https://www.instagram.com/lubelski_dzik_ifbbpro/" target="_blank" rel="noopener nofollow">Instagram</a>
              <a className="btn btn--ghost btn--pill" href="https://www.tiktok.com/@lubelski_dzik" target="_blank" rel="noopener nofollow">TikTok</a>
              <a className="btn btn--ghost btn--pill" href="https://www.youtube.com/@Lubelski_dzik_ifbbpro" target="_blank" rel="noopener nofollow">YouTube</a>
              <a className="btn btn--ghost btn--pill" href="https://www.facebook.com/lubelskidzikk/" target="_blank" rel="noopener nofollow">Facebook</a>
            </p>
          </div>
        </div>
      </section>

      <section className="landing-faq-sec" id="faq">
        <div className="wrap">
          <Naglowek etykieta="FAQ" tytul="Częste pytania" />
          <div className="landing-faq">
            {FAQ.map((f) => (
              <details className="card" key={f.p}>
                <summary>{f.p}</summary>
                <p>{f.o}</p>
              </details>
            ))}
          </div>
        </div>
      </section>

      <section className="dark landing-contact" id="kontakt">
        <span className="wm wm--kontakt" aria-hidden="true">KONTAKT</span>
        <div className="wrap landing-contact__grid">
          <div>
            <div className="eyebrow">Kontakt</div>
            <h2 className="h2">Napisz do mnie</h2>
            {/* PERSONALIZACJA: projekt proponował dopisek „— zwykle tego samego dnia”;
                niepotwierdzony przez właściciela, więc zostaje dotychczasowe zdanie. */}
            <p className="landing-contact__desc">
              Opisz cel i dotychczasowe doświadczenie. Odpowiadam na każde zgłoszenie.
            </p>
            <div className="landing-contact__row">
              <span className="icon icon--m leaf tile-red"><Ikona nazwa="telefon" /></span>
              <a href="tel:+48570477540">+48 570 477 540</a>
            </div>
            <div className="landing-contact__row">
              <span className="icon icon--m leaf tile-graphite"><Ikona nazwa="koperta" /></span>
              <a href="mailto:lubelskidzikk@gmail.com">lubelskidzikk@gmail.com</a>
            </div>
            <p className="landing-contact__health">
              <b>Nie wpisuj w formularzu informacji o zdrowiu, diagnoz ani
              dokumentacji medycznej</b> — takie ustalenia prowadzimy
              bezpiecznie w aplikacji, po założeniu konta i za Twoją
              wyraźną zgodą.
            </p>
          </div>
          {sent ? (
            <div className="alert alert--info landing-sent" role="status">
              Dziękuję za wiadomość! Odezwę się na podany adres tak szybko,
              jak to możliwe.
            </div>
          ) : (
            <form className="card landing-form" onSubmit={submit}>
              <div className="landing-form__row">
                <label>
                  Imię
                  <input
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    required
                    minLength={2}
                    maxLength={120}
                    autoComplete="name"
                  />
                </label>
                <label>
                  E-mail
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    maxLength={254}
                    autoComplete="email"
                  />
                </label>
              </div>
              <label>
                Telefon (opcjonalnie)
                <input
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  maxLength={40}
                  autoComplete="tel"
                />
              </label>
              <label>
                Wiadomość — cel, doświadczenie, pytania
                <textarea
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  required
                  minLength={10}
                  maxLength={2000}
                  rows={5}
                />
              </label>
              {/* Honeypot: niewidoczne dla ludzi, boty je wypełniają. */}
              <label className="landing-form__hp" aria-hidden="true">
                Strona WWW
                <input
                  value={website}
                  onChange={(e) => setWebsite(e.target.value)}
                  tabIndex={-1}
                  autoComplete="off"
                />
              </label>
              {error && <div className="alert" role="alert">{error}</div>}
              <button className="btn btn--primary" disabled={busy}>
                {busy ? "Wysyłanie…" : "Wyślij zapytanie"}
              </button>
              {/* Warstwowa informacja art. 13 RODO (audyt P0-1). */}
              <p className="landing-form__note">
                Administratorem danych z formularza jest LUBELSKI DZIK
                sp. z o.o. (Lublin). Podane dane posłużą wyłącznie do
                odpowiedzi na Twoje zapytanie — nie trafiają na żadną
                listę mailingową. Przysługuje Ci prawo dostępu, sprostowania
                i usunięcia danych. Szczegóły:{" "}
                <a href="/prywatnosc">informacja o przetwarzaniu danych</a>.
              </p>
            </form>
          )}
        </div>
      </section>

      <footer className="landing-footer">
        <div className="wrap">
          {/* Dane firmy / NIP — do uzupełnienia przez właściciela. */}
          <p><img src="/icons/boar-mark-red.png" alt="" /> © {new Date().getFullYear()} Dzik OS · Łukasz Drygiel — Lubelski Dzik · trening personalny Lublin i online</p>
          <p>
            Strona nie używa ciasteczek marketingowych ani narzędzi
            śledzących. <a href="/prywatnosc">Informacja o przetwarzaniu
            danych osobowych</a>.
          </p>
        </div>
      </footer>
    </div>
  );
}
