"""Integridade do catalogo de temas e dos arquivos que eles carregam."""
from __future__ import annotations

import dataclasses
import os
import re

import pytest

from ui import temas

HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")

# Campos do Tema que nao sao cor.
NAO_SAO_COR = {"identificador", "rotulo", "familia", "pasta", "escuro", "realces"}


def test_catalogo_tem_claro_e_escuro_em_cada_familia():
    for familia in temas.familias():
        variantes = temas.da_familia(familia)
        escuros = [t.escuro for t in variantes]
        assert True in escuros, "%s nao tem variante escura" % familia
        assert False in escuros, "%s nao tem variante clara" % familia


def test_identificadores_sao_unicos():
    ids = [t.identificador for t in temas.TEMAS]
    assert len(ids) == len(set(ids))


def test_todas_as_cores_sao_hex_de_seis_digitos():
    for tema in temas.TEMAS:
        for campo in dataclasses.fields(temas.Tema):
            if campo.name in NAO_SAO_COR:
                continue
            valor = getattr(tema, campo.name)
            assert HEX.match(valor), "%s.%s = %r" % (tema.identificador, campo.name, valor)
        for campo in dataclasses.fields(temas.Realces):
            valor = getattr(tema, campo.name)
            assert HEX.match(valor), "%s.%s = %r" % (tema.identificador, campo.name, valor)


def test_tema_responde_pelos_realces():
    """Os paineis falam com um objeto so; os realces entram por __getattr__."""
    tema = temas.por_identificador("forest-light")
    assert tema.sintaxe_tag == temas.REALCES_CLAROS.sintaxe_tag
    assert tema.status_erro == temas.REALCES_CLAROS.status_erro
    assert tema.cursor == tema.texto
    with pytest.raises(AttributeError):
        tema.cor_que_nao_existe


def test_escuro_usa_realces_escuros():
    for tema in temas.TEMAS:
        esperado = temas.REALCES_ESCUROS if tema.escuro else temas.REALCES_CLAROS
        assert tema.realces is esperado


def test_realces_claros_preservam_as_cores_historicas():
    """O realce de sintaxe e as cores de status vem de antes dos temas prontos."""
    r = temas.REALCES_CLAROS
    assert r.texto_suave == "#555555"
    assert r.status_erro == "#B00020"
    assert r.status_aviso == "#A06000"
    assert r.status_ok == "#1A7F37"
    assert r.sintaxe_tag == "#0B5394"
    assert r.sintaxe_atributo == "#7F0055"
    assert r.sintaxe_valor == "#067D17"
    assert r.linha_erro_fundo == "#FFE0E0"


def test_padrao_existe_no_catalogo():
    assert temas.por_identificador(temas.TEMA_PADRAO).identificador == temas.TEMA_PADRAO


def test_identificador_desconhecido_cai_no_padrao():
    """Um config.json editado a mao nao pode explodir na abertura."""
    assert temas.por_identificador("lixo").identificador == temas.TEMA_PADRAO
    assert temas.por_identificador("").identificador == temas.TEMA_PADRAO
    assert temas.por_identificador(None).identificador == temas.TEMA_PADRAO


def test_arquivos_dos_temas_estao_no_lugar():
    """Sem os .tcl o aplicativo abriria sem nenhum tema."""
    base = temas.pasta_dos_temas()
    assert os.path.isdir(base)
    for familia, arquivo in temas._ARQUIVOS:
        assert os.path.isfile(os.path.join(base, familia, arquivo))


def test_todo_tema_do_catalogo_carrega_de_verdade():
    """O catalogo nao pode prometer um tema que o Tk nao consegue usar."""
    tkinter = pytest.importorskip("tkinter")
    try:
        raiz = tkinter.Tk()
    except tkinter.TclError as erro:
        pytest.skip("tkinter indisponivel: %s" % erro)
    raiz.withdraw()
    try:
        carregados = {t.identificador for t in temas.disponiveis(raiz)}
        faltando = [t.identificador for t in temas.TEMAS if t.identificador not in carregados]
        assert not faltando, "temas declarados mas nao carregados: %s" % faltando
        for tema in temas.TEMAS:
            temas.aplicar(raiz, tema)
    finally:
        raiz.destroy()
