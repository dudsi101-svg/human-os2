"""Dostawca AI (`dzik_os/ai_provider.py`).

Testy pilnują obietnic adaptera — na atrapie klienta, żadne wywołanie nie
opuszcza testów:

* builder włącza Anthropic wyłącznie przy OBU: DZIK_AI_ENABLED i kluczu;
* błąd dostawcy (limit, 5xx, sieć) zwraca None, nigdy nie wybucha;
* system prompt i dane użytkownika idą osobnymi kanałami;
* obraz jedzie jako base64 z właściwym media_type;
* summarize_checkin parsuje twardy schemat i odrzuca zepsuty JSON;
* płot kodu ```json``` wokół odpowiedzi jest tolerowany;
* liczniki tokenów przechodzą z response.usage.
"""

import anthropic
import httpx2
import pytest

from dzik_os.ai_provider import (
    AnthropicAIProvider,
    NullAIProvider,
    _zbuduj_provider,
    _zdejmij_plot_kodu,
)


class _Blok:
    def __init__(self, text):
        self.type = "text"
        self.text = text


class _Uzycie:
    input_tokens = 123
    output_tokens = 45


class _Odpowiedz:
    def __init__(self, text):
        self.content = [_Blok(text)]
        self.usage = _Uzycie()


class AtrapaKlienta:
    """Minimalna atrapa SDK: with_options + messages.create."""

    def __init__(self, odpowiedz=None, wyjatek=None):
        self._odpowiedz = odpowiedz
        self._wyjatek = wyjatek
        self.zadania: list[dict] = []
        self.messages = self

    def with_options(self, **_):
        return self

    def create(self, **kwargs):
        self.zadania.append(kwargs)
        if self._wyjatek is not None:
            raise self._wyjatek
        return self._odpowiedz


def _provider(odpowiedz=None, wyjatek=None):
    klient = AtrapaKlienta(odpowiedz=odpowiedz, wyjatek=wyjatek)
    return AnthropicAIProvider(
        api_key="test", model="claude-opus-5", max_tokens=1000, client=klient
    ), klient


def _blad_api(status):
    request = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
    response = httpx2.Response(status, request=request)
    if status == 429:
        return anthropic.RateLimitError(
            "limit", response=response, body=None
        )
    return anthropic.APIStatusError("błąd", response=response, body=None)


def test_builder_requires_both_switch_and_key(monkeypatch):
    from dzik_os.config import settings

    monkeypatch.setattr(settings, "ai_enabled", False)
    monkeypatch.setattr(settings, "ai_api_key", "sk-cos")
    assert isinstance(_zbuduj_provider(), NullAIProvider)

    monkeypatch.setattr(settings, "ai_enabled", True)
    monkeypatch.setattr(settings, "ai_api_key", "")
    assert isinstance(_zbuduj_provider(), NullAIProvider)

    monkeypatch.setattr(settings, "ai_api_key", "sk-cos")
    zbudowany = _zbuduj_provider()
    assert isinstance(zbudowany, AnthropicAIProvider)
    assert zbudowany.enabled is True


@pytest.mark.parametrize("wyjatek", [
    _blad_api(429),
    _blad_api(500),
    anthropic.APIConnectionError(
        request=httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
    ),
])
def test_provider_errors_return_none_never_raise(wyjatek):
    provider, _ = _provider(wyjatek=wyjatek)
    assert provider.propose_json(
        system_prompt="s", data_section="d", schema_hint="h", timeout_s=5
    ) is None


def test_system_and_user_data_travel_separate_channels():
    provider, klient = _provider(odpowiedz=_Odpowiedz('{"ok": true}'))
    wynik = provider.propose_json(
        system_prompt="INSTRUKCJE", data_section="DANE KLIENTA",
        schema_hint="SCHEMAT", timeout_s=5,
    )
    zadanie = klient.zadania[0]
    assert "INSTRUKCJE" in zadanie["system"]
    assert "SCHEMAT" in zadanie["system"]          # format = kanał systemowy
    assert zadanie["messages"][0]["content"] == "DANE KLIENTA"
    assert "DANE KLIENTA" not in zadanie["system"]  # dane nigdy w systemie
    assert wynik.text == '{"ok": true}'
    assert (wynik.tokens_in, wynik.tokens_out) == (123, 45)


def test_image_goes_as_base64_with_media_type():
    provider, klient = _provider(odpowiedz=_Odpowiedz("{}"))
    provider.propose_json_from_image(
        system_prompt="s", image=b"\x89PNG dane", media_type="image/png",
        task_hint="etykieta produktu", schema_hint="h", timeout_s=5,
    )
    tresc = klient.zadania[0]["messages"][0]["content"]
    obraz, tekst = tresc[0], tresc[1]
    assert obraz["type"] == "image"
    assert obraz["source"]["type"] == "base64"
    assert obraz["source"]["media_type"] == "image/png"
    import base64

    assert base64.standard_b64decode(obraz["source"]["data"]) == b"\x89PNG dane"
    assert tekst == {"type": "text", "text": "etykieta produktu"}


def test_summarize_checkin_parses_schema_and_rejects_garbage():
    dobry = ('{"summary": "Tydzień OK", "draft_response": "Brawo!", '
             '"flags": ["ból barku"]}')
    provider, _ = _provider(odpowiedz=_Odpowiedz(dobry))
    wynik = provider.summarize_checkin(payload={"tydzien": 1}, history_note=None)
    assert wynik.summary == "Tydzień OK"
    assert wynik.flags == ["ból barku"]

    provider, _ = _provider(odpowiedz=_Odpowiedz("to nie jest JSON"))
    assert provider.summarize_checkin(payload={}, history_note=None) is None

    provider, _ = _provider(odpowiedz=_Odpowiedz('{"bez": "schematu"}'))
    assert provider.summarize_checkin(payload={}, history_note=None) is None


def test_code_fence_around_json_is_tolerated():
    assert _zdejmij_plot_kodu('```json\n{"a": 1}\n```') == '{"a": 1}'
    assert _zdejmij_plot_kodu('{"a": 1}') == '{"a": 1}'
    oplotowany = _Odpowiedz('```json\n{"summary": "S", "draft_response": '
                            '"D", "flags": []}\n```')
    provider, _ = _provider(odpowiedz=oplotowany)
    wynik = provider.summarize_checkin(payload={}, history_note=None)
    assert wynik is not None and wynik.summary == "S"


def test_empty_model_text_returns_none():
    provider, _ = _provider(odpowiedz=_Odpowiedz("   "))
    assert provider.propose_json(
        system_prompt="s", data_section="d", schema_hint="h", timeout_s=5
    ) is None
