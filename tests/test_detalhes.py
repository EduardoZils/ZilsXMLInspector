"""O painel de detalhes precisa dizer exatamente o que o campo aceita."""
from __future__ import annotations

import os

import pytest

import xsdmodel

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


@pytest.fixture(scope="module")
def schema():
    return xsdmodel.carregar(os.path.join(FIXTURES, "detalhes.xsd"))


@pytest.fixture(scope="module")
def nos(schema):
    raiz = xsdmodel.no_de_elemento(schema.elements["nota"])
    return {no.rotulo: no for no in xsdmodel.filhos(raiz)}


def test_enumeracao_traz_valor_e_documentacao(nos):
    d = xsdmodel.detalhes_do_no(nos["uf"])
    assert d.valores == [("RO", "Rondonia"), ("AC", "Acre"), ("SP", "Sao Paulo")]
    assert d.exemplo == "RO"


def test_enumeracao_sem_documentacao_individual(nos):
    d = xsdmodel.detalhes_do_no(nos["modelo"])
    assert d.valores == [("55", ""), ("65", "")]


def test_pattern_vem_como_escrito_no_xsd(nos):
    """Nao a traducao para regex do Python, que teria ancoras e (?:...)."""
    d = xsdmodel.detalhes_do_no(nos["chave"])
    assert ("Pattern", "[0-9]{44}") in d.restricoes
    assert ("Tamanho exato", "44") in d.restricoes
    assert len(d.exemplo) == 44


def test_faixa_numerica_e_casas_decimais(nos):
    d = xsdmodel.detalhes_do_no(nos["valor"])
    rotulos = dict(d.restricoes)
    assert rotulos["Digitos no total"] == "15"
    assert rotulos["Casas decimais"] == "2"
    assert rotulos["Valor minimo"] == "0"
    assert rotulos["Menor que"] == "1000000"


def test_cabecalho_do_elemento(nos):
    d = xsdmodel.detalhes_do_no(nos["uf"])
    cabecalho = dict(d.cabecalho)
    assert cabecalho["Tipo"] == "TUF (restricao de string)"
    assert cabecalho["Cardinalidade"] == "1..1"
    assert d.documentacao  # a documentacao do tipo serve quando o campo nao tem


def test_default_aparece_no_cabecalho(nos):
    d = xsdmodel.detalhes_do_no(nos["obs"])
    assert ("Default", "sem observacao") in d.cabecalho
    assert ("Cardinalidade", "0..1") in d.cabecalho


def test_atributo_mostra_uso_e_valor_fixo(nos):
    d = xsdmodel.detalhes_do_no(nos["@versao"])
    cabecalho = dict(d.cabecalho)
    assert d.especie == "atributo"
    assert cabecalho["Uso"] == "required"
    assert cabecalho["Fixo"] == "1.00"
    assert d.exemplo == "1.00"


def test_grupo_choice_se_explica(nos, schema):
    raiz = xsdmodel.no_de_elemento(schema.elements["nota"])
    grupos = [n for n in xsdmodel.filhos(raiz) if n.especie == "grupo"]
    assert grupos, "o xs:choice deveria aparecer como no de grupo"
    d = xsdmodel.detalhes_do_no(grupos[0])
    assert d.titulo == "<choice>"
    assert "Escolha" in d.documentacao
    assert ("Particulas", "2") in d.cabecalho


def test_no_nulo_nao_quebra():
    assert xsdmodel.detalhes_do_no(None).titulo == ""


def test_painel_renderiza_tudo():
    """O painel real precisa escrever as secoes no widget."""
    tkinter = pytest.importorskip("tkinter")
    from ui.details_panel import PainelDetalhes

    try:
        raiz = tkinter.Tk()
    except tkinter.TclError as erro:
        pytest.skip("tkinter indisponivel: %s" % erro)
    raiz.withdraw()
    try:
        painel = PainelDetalhes(raiz)
        schema = xsdmodel.carregar(os.path.join(FIXTURES, "detalhes.xsd"))
        no_raiz = xsdmodel.no_de_elemento(schema.elements["nota"])
        uf = [n for n in xsdmodel.filhos(no_raiz) if n.rotulo == "uf"][0]
        painel.mostrar(uf)
        conteudo = painel.texto.get("1.0", "end")
        assert "uf" in conteudo
        assert "Valores permitidos (3)" in conteudo
        assert "Rondonia" in conteudo
        assert "Exemplo gerado" in conteudo
        assert painel.texto.cget("state") == "disabled"  # somente leitura

        painel.limpar()
        assert "Selecione um elemento" in painel.texto.get("1.0", "end")
    finally:
        raiz.destroy()
