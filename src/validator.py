"""Valida um XML contra um XSD devolvendo os erros com linha e coluna.

Usa o libxml2 (via lxml) porque, alem de rapido, ele reporta a posicao exata do
erro no documento -- que e o que permite saltar para a linha na interface.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass

from lxml import etree

_DECLARACAO = re.compile(r'^(<\?xml[^>]*?)encoding\s*=\s*(["\'])[^"\']*\2')


class ErroDeSchema(Exception):
    """O proprio XSD nao pode ser compilado."""


@dataclass
class ErroValidacao:
    linha: int
    coluna: int
    mensagem: str
    caminho: str = ""

    def __str__(self) -> str:
        return "linha %d, coluna %d: %s" % (self.linha, self.coluna, self.mensagem)


_cache: dict = {}


def compilar(caminho_xsd: str) -> etree.XMLSchema:
    """Compila o XSD, reaproveitando o resultado enquanto o arquivo nao mudar."""
    try:
        assinatura = (os.path.getmtime(caminho_xsd), os.path.getsize(caminho_xsd))
    except OSError as erro:
        raise ErroDeSchema(str(erro)) from erro

    em_cache = _cache.get(caminho_xsd)
    if em_cache and em_cache[0] == assinatura:
        return em_cache[1]

    try:
        documento = etree.parse(caminho_xsd)
        schema = etree.XMLSchema(documento)
    except (etree.XMLSyntaxError, etree.XMLSchemaParseError) as erro:
        raise ErroDeSchema(str(erro)) from erro

    _cache[caminho_xsd] = (assinatura, schema)
    return schema


def _erros_do_log(log) -> list:
    return [
        ErroValidacao(
            linha=entrada.line or 0,
            coluna=entrada.column or 0,
            mensagem=entrada.message or "",
            caminho=entrada.path or "",
        )
        for entrada in log
    ]


def validar_bytes(caminho_xsd: str, conteudo: bytes) -> list:
    """Valida o XML em memoria. Lista vazia significa documento valido."""
    schema = compilar(caminho_xsd)
    try:
        documento = etree.fromstring(conteudo)
    except etree.XMLSyntaxError as erro:
        linha, coluna = (erro.position or (0, 0))
        return [ErroValidacao(linha, coluna, "XML mal formado: %s" % erro.msg)]

    if schema.validate(documento.getroottree()):
        return []
    return _erros_do_log(schema.error_log)


def validar_texto(caminho_xsd: str, texto: str) -> list:
    # O texto vindo do editor sera codificado em UTF-8; se a declaracao anunciar
    # outra codificacao o parser reclamaria de uma incoerencia que nao existe.
    ajustado = _DECLARACAO.sub(lambda m: m.group(1) + 'encoding="UTF-8"', texto, count=1)
    return validar_bytes(caminho_xsd, ajustado.encode("utf-8"))


def validar_arquivo(caminho_xsd: str, caminho_xml: str) -> list:
    with open(caminho_xml, "rb") as arquivo:
        return validar_bytes(caminho_xsd, arquivo.read())
