import json

import pytest

from palpiteiro import historico
from palpiteiro.historico import StatisticsStore


@pytest.fixture
def cache_path(tmp_path, monkeypatch):
    path = tmp_path / "estatisticas.json"
    monkeypatch.setattr(historico, "_cache_file", lambda: path)
    return path


@pytest.mark.parametrize("raw", [b'{"loterias":', b"[]", b'{"loterias": null}', b"\xff"])
def test_cache_invalido_preservado_sem_impedir_inicio(cache_path, raw):
    cache_path.write_bytes(raw)
    store = StatisticsStore()
    assert store.data == {"updated_at": None, "loterias": {}}
    assert store.cache_warning
    assert cache_path.read_bytes() == raw
    assert next(cache_path.parent.glob("estatisticas-recuperacao-*.json")).read_bytes() == raw
    store.save_cache()
    assert json.loads(cache_path.read_bytes()) == store.data


def test_recupera_backup_valido(cache_path):
    data = {"updated_at": "06/10/2026 10:00:00", "loterias": {"mega-sena": {"historico": []}}}
    cache_path.write_bytes(b"{")
    cache_path.with_suffix(".json.bak").write_text(json.dumps(data))
    store = StatisticsStore()
    assert store.data == data
    assert "recuperada" in store.cache_warning


def test_gravacao_atomica_mantem_backup(cache_path):
    original = b'{"updated_at": null, "loterias": {}}'
    cache_path.write_bytes(original)
    store = StatisticsStore()
    store.data["updated_at"] = "06/10/2026 10:00:00"
    store.save_cache()
    assert cache_path.with_suffix(".json.bak").read_bytes() == original
    assert json.loads(cache_path.read_bytes()) == store.data
    assert not list(cache_path.parent.glob(".estatisticas-*"))


def test_falha_na_substituicao_preserva_cache(cache_path, monkeypatch):
    original = b'{"updated_at": null, "loterias": {}}'
    cache_path.write_bytes(original)
    store = StatisticsStore()
    replace = historico.os.replace

    def fail(source, destination):
        if destination == cache_path:
            raise OSError("Falha simulada")
        replace(source, destination)

    monkeypatch.setattr(historico.os, "replace", fail)
    with pytest.raises(OSError):
        store.save_cache()
    assert cache_path.read_bytes() == original
    assert not list(cache_path.parent.glob(".estatisticas-*"))


def test_falha_ao_preservar_corrompido_bloqueia_gravacao(cache_path, monkeypatch):
    cache_path.write_bytes(b"{")

    def fail(**kwargs):
        raise PermissionError("Falha simulada")

    monkeypatch.setattr(historico.tempfile, "NamedTemporaryFile", fail)
    store = StatisticsStore()
    with pytest.raises(OSError, match="preservar"):
        store.save_cache()
    assert cache_path.read_bytes() == b"{"
