import { FormEvent, useState } from "react";

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
    <div className="landing">
      <header className="landing-top">
        <div className="landing-top__inner">
          <img src="/icons/boar-mark.png" alt="" className="landing-top__logo" />
          <span className="landing-top__name">Dzik OS</span>
          <span className="landing-top__spacer" />
          <a className="btn btn--ghost landing-top__login" href="/login">
            Zaloguj się
          </a>
        </div>
      </header>

      <section className="landing-hero">
        <img src="/icons/logo-full.png" alt="Dzik OS" className="landing-hero__logo" />
        {/* PERSONALIZACJA: nagłówek i podtytuł — wstaw własne hasło. */}
        <h1>Trening prowadzony, nie zgadywany</h1>
        <p className="landing-hero__sub">
          Indywidualny plan treningowy i dieta, cotygodniowe raporty
          i stały kontakt z trenerem — wszystko w jednej aplikacji,
          którą masz w telefonie.
        </p>
        <div className="landing-hero__cta">
          <a className="btn" href="#kontakt">Umów bezpłatną konsultację</a>
          <a className="btn btn--ghost" href="/login">Mam już konto</a>
        </div>
      </section>

      <section className="landing-section" id="oferta">
        <h2>Co dostajesz we współpracy</h2>
        <div className="landing-grid">
          {ATUTY.map((a) => (
            <div className="card landing-card" key={a.tytul}>
              <h3>{a.tytul}</h3>
              <p>{a.opis}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="landing-section" id="jak-to-dziala">
        <h2>Jak zaczynamy</h2>
        <ol className="landing-steps">
          {KROKI.map((k, i) => (
            <li className="card landing-card" key={k.tytul}>
              <span className="landing-steps__no">{i + 1}</span>
              <h3>{k.tytul}</h3>
              <p>{k.opis}</p>
            </li>
          ))}
        </ol>
      </section>

      <section className="landing-section" id="o-trenerze">
        <h2>O trenerze</h2>
        <div className="card landing-card landing-about">
          {/* PERSONALIZACJA: wstaw swoje imię, doświadczenie, certyfikaty
              i zdjęcie (np. <img src="/icons/trener.jpg" ... /> po dodaniu
              pliku do frontend/public/icons/). */}
          <p>
            Trenuję ludzi, którzy chcą realnej zmiany — siły, sylwetki albo
            po prostu zdrowia — i wolą plan oparty na pomiarach niż na
            motywacyjnych hasłach. Każdą współpracę prowadzę osobiście:
            układam plan, czytam każdy raport i odpowiadam na każdą
            wiadomość.
          </p>
          <p>
            Aplikacja Dzik OS to moje własne narzędzie pracy — powstała po
            to, żeby nic z naszej współpracy nie ginęło w czatach
            i arkuszach.
          </p>
        </div>
      </section>

      <section className="landing-section" id="faq">
        <h2>Częste pytania</h2>
        <div className="landing-faq">
          {FAQ.map((f) => (
            <details className="card landing-card" key={f.p}>
              <summary>{f.p}</summary>
              <p>{f.o}</p>
            </details>
          ))}
        </div>
      </section>

      <section className="landing-section" id="kontakt">
        <h2>Napisz do mnie</h2>
        {sent ? (
          <div className="alert alert--info landing-sent" role="status">
            Dziękuję za wiadomość! Odezwę się na podany adres tak szybko,
            jak to możliwe.
          </div>
        ) : (
          <form className="card landing-card landing-form" onSubmit={submit}>
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
            <button className="btn" disabled={busy}>
              {busy ? "Wysyłanie…" : "Wyślij zapytanie"}
            </button>
            <p className="landing-form__note">
              Podane dane posłużą wyłącznie do odpowiedzi na Twoje
              zapytanie. Nie trafiają na żadną listę mailingową.
            </p>
          </form>
        )}
      </section>

      <footer className="landing-footer">
        {/* PERSONALIZACJA: dane firmy / NIP / adres, jeśli wymagane. */}
        <p>© {new Date().getFullYear()} Dzik OS — trening personalny.</p>
        <p>
          Strona nie używa ciasteczek marketingowych ani narzędzi
          śledzących.
        </p>
      </footer>
    </div>
  );
}
