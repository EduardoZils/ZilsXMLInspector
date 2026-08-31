"""Coloca src/ no sys.path para que os testes importem os modulos do aplicativo.

O aplicativo e executado como `python src\\main.py`, o que ja poe src/ no
caminho; nos testes o pytest precisa da mesma ajuda.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))


@pytest.fixture(scope="session", autouse=True)
def _config_isolado(tmp_path_factory):
    """Os testes nao podem ler nem escrever as preferencias reais do usuario.

    Sem isso, quem estivesse com o tema escuro salvo veria a janela dos testes
    abrir escura, e rodar a suite sobrescreveria o config.json de verdade.
    """
    import config

    anterior = os.environ.get(config.VARIAVEL_CAMINHO)
    os.environ[config.VARIAVEL_CAMINHO] = str(
        tmp_path_factory.mktemp("config") / "config.json"
    )
    yield
    if anterior is None:
        os.environ.pop(config.VARIAVEL_CAMINHO, None)
    else:
        os.environ[config.VARIAVEL_CAMINHO] = anterior
