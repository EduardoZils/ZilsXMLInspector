"""Cada valor de exemplo precisa ser aceito pelo tipo que o originou."""
from __future__ import annotations

import re

import pytest
import xmlschema

import regexsample
from samplevalues import GeradorDeValores

XS = "{http://www.w3.org/2001/XMLSchema}"

CABECALHO = '<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">%s</xs:schema>'


def tipo(corpo: str, nome: str = "T"):
    return xmlschema.XMLSchema(CABECALHO % corpo).types[nome]


def restricao(base: str, facets: str, nome: str = "T"):
    return tipo(
        '<xs:simpleType name="%s"><xs:restriction base="%s">%s</xs:restriction></xs:simpleType>'
        % (nome, base, facets),
        nome,
    )


@pytest.fixture()
def gerador():
    return GeradorDeValores()


# --------------------------------------------------------------- regexsample

@pytest.mark.parametrize(
    "padrao",
    [
        r"[0-9]{44}",
        r"[A-Z]{2}[0-9]{3,5}",
        r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}",
        r"(a|bb|ccc)+",
        r"[^0-9]{3}",
        r"-?\d{1,4}(\.\d{1,2})?",
        r"[!-~]{1,60}",
        r"[0-9]{0}|[A-Z0-9]{12}[0-9]{2}",
        r"(1|2|3)[0-9]{6}",
    ],
)
def test_amostra_casa_com_o_padrao(padrao):
    valor = regexsample.amostra_para(padrao)
    assert valor is not None
    assert re.fullmatch(padrao, valor), "%r nao casa com %r" % (valor, padrao)


def test_amostra_prefere_alternativa_nao_vazia():
    # A primeira alternativa casa com string vazia, que nao serve de exemplo.
    assert regexsample.amostra_para(r"[0-9]{0}|[A-Z0-9]{12}[0-9]{2}") != ""


def test_amostra_estica_repeticao_livre_ate_o_alvo():
    assert regexsample.amostra_para(r"[0-9]{1,6}", alvo=6) == "000000"
    # Repeticao de tamanho fixo nao e afetada pelo alvo.
    assert regexsample.amostra_para(r"[0-9]{2}", alvo=6) == "00"


def test_amostra_devolve_none_em_padrao_invalido():
    assert regexsample.amostra_para("[nao fecha") is None


# -------------------------------------------------------------- samplevalues

@pytest.mark.parametrize(
    "base,facets",
    [
        ("xs:string", '<xs:pattern value="[0-9]{44}"/>'),
        ("xs:string", '<xs:enumeration value="55"/><xs:enumeration value="65"/>'),
        ("xs:string", '<xs:minLength value="10"/><xs:maxLength value="12"/>'),
        ("xs:string", '<xs:length value="8"/>'),
        ("xs:decimal", '<xs:totalDigits value="15"/><xs:fractionDigits value="2"/>'),
        ("xs:decimal", '<xs:minExclusive value="0"/><xs:maxInclusive value="100"/>'),
        ("xs:int", '<xs:minInclusive value="10"/><xs:maxInclusive value="20"/>'),
        ("xs:base64Binary", '<xs:length value="20"/>'),
        ("xs:hexBinary", '<xs:length value="4"/>'),
        ("xs:string", '<xs:pattern value="[0-9]{1,6}"/><xs:minLength value="6"/>'),
    ],
)
def test_valor_e_aceito_pelo_tipo(gerador, base, facets):
    t = restricao(base, facets)
    valor = gerador.valor_para(t, "campo")
    assert t.is_valid(valor), "%r rejeitado por %s %s" % (valor, base, facets)
    assert not gerador.nao_resolvidos


@pytest.mark.parametrize(
    "nome",
    [
        "string", "boolean", "decimal", "int", "long", "byte", "unsignedByte",
        "positiveInteger", "negativeInteger", "nonNegativeInteger", "date",
        "dateTime", "time", "duration", "gYear", "gYearMonth", "gMonth", "gDay",
        "gMonthDay", "anyURI", "QName", "base64Binary", "hexBinary", "float",
        "double", "ID", "IDREF", "NCName", "Name", "NMTOKEN", "language",
        "token", "normalizedString",
    ],
)
def test_todo_tipo_embutido_tem_valor_valido(gerador, nome):
    t = xmlschema.XMLSchema(CABECALHO % "").maps.types[XS + nome]
    valor = gerador.valor_para(t, "campo")
    assert t.is_valid(valor), "%s -> %r" % (nome, valor)


def test_enumeracao_gira_entre_repeticoes(gerador):
    t = restricao("xs:string", '<xs:enumeration value="A"/><xs:enumeration value="B"/>')
    assert gerador.valor_para(t, "c", variacao=0) == "A"
    assert gerador.valor_para(t, "c", variacao=1) == "B"
    assert gerador.valor_para(t, "c", variacao=2) == "A"


def test_fixed_tem_prioridade(gerador):
    t = xmlschema.XMLSchema(CABECALHO % "").maps.types[XS + "string"]
    assert gerador.valor_para(t, "c", declarado=("padrao", "travado")) == "travado"
    assert gerador.valor_para(t, "c", declarado=("padrao", None)) == "padrao"


def test_ids_sao_unicos(gerador):
    t = xmlschema.XMLSchema(CABECALHO % "").maps.types[XS + "ID"]
    valores = {gerador.valor_para(t, "id") for _ in range(5)}
    assert len(valores) == 5


def test_idref_aponta_para_o_primeiro_id(gerador):
    mapa = xmlschema.XMLSchema(CABECALHO % "").maps.types
    primeiro = gerador.valor_para(mapa[XS + "ID"], "id")
    assert gerador.valor_para(mapa[XS + "IDREF"], "ref") == primeiro


def test_binario_conta_octetos_e_nao_caracteres(gerador):
    t = restricao("xs:base64Binary", '<xs:length value="20"/>')
    valor = gerador.valor_para(t, "anexo")
    import base64

    assert len(base64.b64decode(valor)) == 20


def test_pattern_permissivo_cede_ao_texto_legivel(gerador):
    """Com um pattern que aceita quase tudo, o nome do campo diz mais."""
    t = restricao("xs:string", '<xs:pattern value="[!-~]{1,60}"/>')
    assert gerador.valor_para(t, "natOp") == "natOp"


def test_pattern_restritivo_manda_no_valor(gerador):
    """Ja um pattern estrito descarta o texto legivel."""
    t = restricao("xs:string", '<xs:pattern value="[0-9]{14}"/>')
    assert gerador.valor_para(t, "CNPJ") == "0" * 14


def test_data_em_string_com_pattern_fica_legivel(gerador):
    """Data disfarcada de xs:string deve sair legivel, nao "2000-02-29"."""
    padrao = (
        r"(((20(([02468][048])|([13579][26]))-02-29))|(20[0-9][0-9])-"
        r"((((0[1-9])|(1[0-2]))-((0[1-9])|(1\d)|(2[0-8])))|"
        r"((((0[13578])|(1[02]))-31)|(((0[1,3-9])|(1[0-2]))-(29|30)))))"
        r"T(20|21|22|23|[0-1]\d):[0-5]\d:[0-5]\d([\-,\+](0[0-9]|10|11):00|([\+](12):00))"
    )
    t = restricao("xs:string", '<xs:pattern value="%s"/>' % padrao.replace("&", "&amp;"))
    valor = gerador.valor_para(t, "dhEmi")
    assert t.is_valid(valor)
    assert valor.startswith("2026-01-01T12:00:00")


def test_uniao_e_lista(gerador):
    esquema = xmlschema.XMLSchema(
        CABECALHO
        % (
            '<xs:simpleType name="U"><xs:union memberTypes="xs:int xs:date"/></xs:simpleType>'
            '<xs:simpleType name="L"><xs:list itemType="xs:int"/></xs:simpleType>'
        )
    )
    for nome in ("U", "L"):
        t = esquema.types[nome]
        assert t.is_valid(gerador.valor_para(t, "campo"))


def test_valor_sem_solucao_e_registrado(gerador):
    """Um tipo impossivel nao pode explodir: devolve algo e anota o problema."""
    t = restricao("xs:string", '<xs:pattern value="[0-9]{5}"/><xs:length value="9"/>')
    valor = gerador.valor_para(t, "impossivel")
    assert isinstance(valor, str)
    assert "impossivel" in gerador.nao_resolvidos
