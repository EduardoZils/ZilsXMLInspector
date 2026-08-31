"""Persistencia das preferencias: nunca pode levantar excecao para o aplicativo."""
from __future__ import annotations

import json
import os

import config


def apontar(monkeypatch, caminho) -> str:
    monkeypatch.setenv(config.VARIAVEL_CAMINHO, str(caminho))
    return str(caminho)


def test_padrao_quando_o_arquivo_nao_existe(monkeypatch, tmp_path):
    apontar(monkeypatch, tmp_path / "ausente.json")
    assert config.carregar() == {"tema": "forest-light"}


def test_ida_e_volta(monkeypatch, tmp_path):
    caminho = apontar(monkeypatch, tmp_path / "sub" / "config.json")
    assert config.salvar({"tema": "sun-valley-dark"}) is True
    assert os.path.isfile(caminho)  # a pasta intermediaria e criada
    assert config.carregar()["tema"] == "sun-valley-dark"


def test_json_corrompido_nao_derruba(monkeypatch, tmp_path):
    caminho = apontar(monkeypatch, tmp_path / "config.json")
    with open(caminho, "w", encoding="utf-8") as arquivo:
        arquivo.write("{ isto nao e json")
    assert config.carregar() == {"tema": "forest-light"}


def test_json_com_tipo_errado_vira_padrao(monkeypatch, tmp_path):
    """Um JSON valido pode ser uma lista; so um objeto serve como preferencias."""
    caminho = apontar(monkeypatch, tmp_path / "config.json")
    with open(caminho, "w", encoding="utf-8") as arquivo:
        json.dump([1, 2, 3], arquivo)
    assert config.carregar() == {"tema": "forest-light"}


def test_chave_desconhecida_sobrevive_e_o_padrao_e_mesclado(monkeypatch, tmp_path):
    """Um config antigo nao pode perder chaves nem ficar sem as novas."""
    caminho = apontar(monkeypatch, tmp_path / "config.json")
    with open(caminho, "w", encoding="utf-8") as arquivo:
        json.dump({"outra_coisa": 1}, arquivo)
    dados = config.carregar()
    assert dados["outra_coisa"] == 1
    assert dados["tema"] == "forest-light"


def test_destino_invalido_devolve_falso(monkeypatch, tmp_path):
    arquivo = tmp_path / "arquivo.txt"
    arquivo.write_text("nao sou pasta", encoding="utf-8")
    apontar(monkeypatch, arquivo / "config.json")
    assert config.salvar({"tema": "forest-dark"}) is False


def test_variavel_de_ambiente_manda_no_caminho(monkeypatch, tmp_path):
    esperado = apontar(monkeypatch, tmp_path / "escolhido.json")
    assert config.caminho_config() == esperado


def test_caminho_padrao_usa_o_appdata(monkeypatch, tmp_path):
    monkeypatch.delenv(config.VARIAVEL_CAMINHO, raising=False)
    monkeypatch.setenv("APPDATA", str(tmp_path))
    caminho = config.caminho_config()
    assert caminho == os.path.join(str(tmp_path), config.NOME_APP, "config.json")


def test_modo_antigo_vira_tema(monkeypatch, tmp_path):
    """Um config.json de antes do seletor de temas continua valendo."""
    caminho = apontar(monkeypatch, tmp_path / "config.json")
    for antigo, esperado in (
        ("claro", "forest-light"),
        ("escuro", "forest-dark"),
        ("sistema", "forest-light"),
    ):
        with open(caminho, "w", encoding="utf-8") as arquivo:
            json.dump({"tema": antigo}, arquivo)
        assert config.carregar()["tema"] == esperado


def test_tema_novo_passa_intacto(monkeypatch, tmp_path):
    caminho = apontar(monkeypatch, tmp_path / "config.json")
    with open(caminho, "w", encoding="utf-8") as arquivo:
        json.dump({"tema": "azure-dark"}, arquivo)
    assert config.carregar()["tema"] == "azure-dark"
