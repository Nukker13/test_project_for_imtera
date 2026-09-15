"""Тест, стерегущий самое хрупкое место проекта — подпись запросов.

Единственные автотесты в проекте (по договорённости их не пишем), и они здесь
именно потому, что алгоритм подписи реверс-инженерен: если Яндекс его поменяет,
прямая стратегия начнёт молча получать отказы. Тест на живой фикстуре превращает
это в явный красный сигнал.

Фикстура fixtures/real_request.json пишется автоматически при первом успешном
прогоне парсера (session.py калибрует подпись по перехваченному запросу). Пока её
нет, соответствующий тест пропускается.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from yandex import signature as sig  # noqa: E402
from yandex.errors import SignatureMismatchError  # noqa: E402


def test_djb2_xor_matches_js_semantics():
    """Эталонные значения djb2-xor, совпадающие с реализацией на JS."""
    assert sig.djb2_xor("") == 5381
    assert sig.djb2_xor("a") == 5381 * 33 ^ ord("a")
    # Результат обязан оставаться в пределах uint32 при любой длине входа.
    assert 0 <= sig.djb2_xor("x" * 500) <= 0xFFFFFFFF


def test_signature_excludes_itself():
    """Параметр `s` не участвует в вычислении собственного значения."""
    params = {"businessId": "1", "page": "2", "pageSize": "50"}
    expected = sig.sign(params)
    assert sig.sign({**params, sig.SIGNATURE_KEY: "whatever"}) == expected


def test_signature_is_order_independent():
    """Подпись зависит от набора параметров, а не от порядка их перечисления."""
    a = {"page": "1", "businessId": "42", "ranking": "by_time"}
    b = {"ranking": "by_time", "businessId": "42", "page": "1"}
    assert sig.sign(a) == sig.sign(b)


def test_calibrate_rejects_unknown_algorithm():
    """Если ни одна схема не воспроизводит подпись — это явная ошибка."""
    with pytest.raises(SignatureMismatchError):
        sig.calibrate({"page": "1", "businessId": "42"}, "0")


def test_calibrate_recovers_scheme_for_each_candidate():
    """Калибровка находит ту схему, которой подпись была фактически посчитана."""
    params = {"businessId": "42", "page": "3", "ranking": "by_time"}
    for name, canon in sig.CANDIDATES.items():
        produced = str(sig.djb2_xor(canon(params)))
        assert sig.calibrate(params, produced) in sig.CANDIDATES


@pytest.mark.skipif(sig.load_fixture() is None, reason="нет снятого живого запроса")
def test_live_fixture_still_reproduces_signature():
    """Главный тест: алгоритм всё ещё воспроизводит реальную подпись Яндекса."""
    fixture = sig.load_fixture()
    scheme = sig.calibrate(fixture["params"], fixture["s"])
    assert sig.sign(fixture["params"], scheme) == str(fixture["s"])
