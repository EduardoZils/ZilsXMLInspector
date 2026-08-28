"""O gerador precisa produzir XML que valida contra o proprio XSD de origem."""
from __future__ import annotations

import os

import pytest

import generator
import validator
import xsdmodel

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")

PRESETS = {
    "completo": generator.OpcoesGeracao(),
    "minimo": generator.OpcoesGeracao(
        incluir_opcionais=False, incluir_atributos_opcionais=False
    ),
    "repetido": generator.OpcoesGeracao(repeticoes=3, incluir_documentacao=True),
    "comentado": generator.OpcoesGeracao(
        comentar_alternativas_choice=True, incluir_schema_location=True
    ),
}

# recursivo.xsd nao entra: interromper a recursao deixa de fora um elemento que
# o schema exige, entao o resultado e um esqueleto proposital, nao um XML valido.
ARQUIVOS = [
    "simples.xsd",
    "escolha.xsd",
    "principal.xsd",
    "naoqualificado.xsd",
    "homonimos.xsd",
    "herdado.xsd",
    "comnamespace.xsd",
]


def caminho(nome: str) -> str:
    return os.path.join(FIXTURES, nome)


def gerar(nome_arquivo: str, preset: str):
    arquivo = caminho(nome_arquivo)
    schema = xsdmodel.carregar(arquivo)
    raizes = xsdmodel.elementos_globais(schema)
    return schema, arquivo, raizes, PRESETS[preset]


@pytest.mark.parametrize("nome_arquivo", ARQUIVOS)
@pytest.mark.parametrize("preset", sorted(PRESETS))
def test_xml_gerado_e_valido(nome_arquivo, preset):
    schema, arquivo, raizes, opcoes = gerar(nome_arquivo, preset)
    for raiz in raizes:
        if getattr(raiz, "abstract", False):
            continue
        texto, _avisos = generator.gerar_xml(schema, raiz, opcoes, arquivo)
        erros = validator.validar_texto(arquivo, texto)
        assert not erros, "%s / %s / %s:\n%s\n%s" % (
            nome_arquivo,
            preset,
            raiz.name,
            texto,
            "\n".join(str(e) for e in erros),
        )


def test_recursivo_termina_e_comenta():
    schema, arquivo, raizes, opcoes = gerar("recursivo.xsd", "completo")
    texto, _ = generator.gerar_xml(schema, raizes[0], opcoes, arquivo)
    assert "recursao interrompida" in texto


def test_minimo_omite_opcionais():
    schema, arquivo, _raizes, opcoes = gerar("simples.xsd", "minimo")
    texto, _ = generator.gerar_xml(schema, schema.elements["documento"], opcoes, arquivo)
    assert "<anexo>" not in texto and "origem=" not in texto
    assert "<chave>" in texto and 'id="' in texto


def test_completo_inclui_opcionais():
    schema, arquivo, _raizes, opcoes = gerar("simples.xsd", "completo")
    texto, _ = generator.gerar_xml(schema, schema.elements["documento"], opcoes, arquivo)
    assert "<anexo>" in texto and "origem=" in texto


def test_repeticoes_respeitam_max_occurs():
    schema, arquivo, _raizes, opcoes = gerar("escolha.xsd", "repetido")
    texto, _ = generator.gerar_xml(schema, schema.elements["cadastro"], opcoes, arquivo)
    assert texto.count("<pessoa") == 3  # maxOccurs="unbounded"
    assert texto.count("<obrigatorioRepetido>") == 3  # minOccurs 2, maxOccurs 5


def test_choice_gera_apenas_um_ramo():
    schema, arquivo, _raizes, opcoes = gerar("escolha.xsd", "completo")
    texto, _ = generator.gerar_xml(schema, schema.elements["cadastro"], opcoes, arquivo)
    assert "<cpf>" in texto
    assert "<cnpj>" not in texto and "<idEstrangeiro>" not in texto


def test_alternativas_de_choice_viram_comentario():
    schema, arquivo, _raizes, opcoes = gerar("escolha.xsd", "comentado")
    texto, _ = generator.gerar_xml(schema, schema.elements["cadastro"], opcoes, arquivo)
    assert "outras opcoes do xs:choice" in texto
    assert "<!--" in texto and "cnpj" in texto


def test_substitution_group_resolve_elemento_abstrato():
    schema, arquivo, _raizes, opcoes = gerar("principal.xsd", "completo")
    texto, _ = generator.gerar_xml(schema, schema.elements["pedido"], opcoes, arquivo)
    assert "pagamentoCartao" in texto or "pagamentoDinheiro" in texto
    assert "<pagamento>" not in texto


def test_namespace_padrao_quando_qualificado():
    schema, arquivo, _raizes, opcoes = gerar("principal.xsd", "completo")
    texto, _ = generator.gerar_xml(schema, schema.elements["pedido"], opcoes, arquivo)
    assert 'xmlns="http://exemplo.com.br/verificador"' in texto


def test_prefixo_quando_locais_nao_qualificados():
    schema, arquivo, raizes, opcoes = gerar("naoqualificado.xsd", "completo")
    texto, _ = generator.gerar_xml(schema, raizes[0], opcoes, arquivo)
    assert 'xmlns="http://exemplo.com.br/local"' not in texto
    assert "<titulo>" in texto  # filho local fora do namespace


def test_limite_de_elementos():
    schema, arquivo, _raizes, _ = gerar("escolha.xsd", "completo")
    opcoes = generator.OpcoesGeracao(repeticoes=50, limite_elementos=100)
    with pytest.raises(generator.LimiteExcedido):
        generator.gerar_xml(schema, schema.elements["cadastro"], opcoes, arquivo)


def test_homonimos_nao_sao_confundidos_com_recursao():
    """Nomes repetidos em declaracoes distintas nao podem ser podados."""
    schema, arquivo, _raizes, opcoes = gerar("homonimos.xsd", "completo")
    texto, _ = generator.gerar_xml(schema, schema.elements["nfse"], opcoes, arquivo)
    assert "recursao interrompida" not in texto
    # nfse global > nfse de TNota > nfse de tipo simples; toma de TNota > toma
    # de TTomador. Tudo homonimo, nada recursivo.
    assert texto.count("<nfse>") == 3
    assert texto.count("<toma>") == 2
    assert not validator.validar_texto(arquivo, texto)


def test_facet_herdado_de_alias_de_tipo():
    """<xs:restriction base="X"/> sem facets proprios herda os do tipo base."""
    schema, arquivo, _raizes, opcoes = gerar("herdado.xsd", "completo")
    texto, avisos = generator.gerar_xml(schema, schema.elements["processo"], opcoes, arquivo)
    assert not validator.validar_texto(arquivo, texto)
    assert not avisos


def test_namespace_padrao_so_quando_tudo_e_qualificado():
    """Um tipo importado pode trazer elementos locais fora do namespace."""
    schema, arquivo, _raizes, opcoes = gerar("comnamespace.xsd", "completo")
    texto, _ = generator.gerar_xml(schema, schema.elements["resposta"], opcoes, arquivo)
    assert not validator.validar_texto(arquivo, texto)
    # Com um filho sem namespace na arvore, o topo precisa usar prefixo.
    assert 'xmlns="http://exemplo.com.br/resposta"' not in texto
    assert "<protocolo>" in texto
