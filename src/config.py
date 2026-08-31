"""Preferencias do usuario gravadas em disco.

Hoje guarda so o tema, mas o formato e um dicionario JSON justamente para que
novas chaves possam entrar sem quebrar um arquivo antigo.
"""
from __future__ import annotations

import json
import os

NOME_APP = "ZilsXMLInspector"

# Gancho para os testes (e para quem quiser um perfil portatil): quando esta
# definida, manda no caminho do arquivo.
VARIAVEL_CAMINHO = "ZILS_XML_INSPECTOR_CONFIG"

PADRAO = {"tema": "forest-light"}


def caminho_config() -> str:
    """Onde fica o config.json.

    Nunca deriva do caminho do executavel: empacotado com o PyInstaller em modo
    onefile, o programa roda de uma pasta temporaria que e apagada ao sair.
    """
    forcado = os.environ.get(VARIAVEL_CAMINHO)
    if forcado:
        return forcado
    dados_do_usuario = os.environ.get("APPDATA")
    if dados_do_usuario:
        return os.path.join(dados_do_usuario, NOME_APP, "config.json")
    return os.path.join(os.path.expanduser("~"), ".zilsxmlinspector.json")


# Antes de existir o seletor de temas, a chave "tema" guardava so um modo.
# Um config.json gravado por aquela versao continua valendo.
_MODOS_ANTIGOS = {
    "claro": "forest-light",
    "escuro": "forest-dark",
    "sistema": "forest-light",
}


def carregar() -> dict:
    """Le as preferencias. Um arquivo ausente ou corrompido vira o padrao."""
    try:
        with open(caminho_config(), "r", encoding="utf-8") as arquivo:
            lido = json.load(arquivo)
    except (OSError, ValueError):
        return dict(PADRAO)

    dados = dict(PADRAO)
    # Um JSON valido pode ser uma lista ou um numero; so um objeto serve aqui.
    if isinstance(lido, dict):
        dados.update(lido)
    dados["tema"] = _MODOS_ANTIGOS.get(dados.get("tema"), dados.get("tema"))
    return dados


def salvar(dados: dict) -> bool:
    """Grava as preferencias. Devolve False se nao deu (disco cheio, permissao)."""
    caminho = caminho_config()
    try:
        pasta = os.path.dirname(caminho)
        if pasta:
            os.makedirs(pasta, exist_ok=True)
        with open(caminho, "w", encoding="utf-8") as arquivo:
            json.dump(dados, arquivo, indent=2, ensure_ascii=False)
        return True
    except (OSError, TypeError, ValueError):
        return False
