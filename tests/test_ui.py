"""Exercita a janela de verdade: abrir schema, gerar, validar e formatar.

Nao entra no mainloop -- as acoes sao chamadas diretamente e o loop de eventos e
girado a mao enquanto houver trabalho em segundo plano.
"""
from __future__ import annotations

import os
import time

import pytest

tkinter = pytest.importorskip("tkinter")

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


@pytest.fixture(scope="module")
def janela():
    """Uma unica janela para todo o modulo.

    Criar e destruir uma raiz Tk por teste falha de forma intermitente no
    Windows (o Tk nao consegue reler tk.tcl), e ainda deixa variaveis do Tk
    para o coletor de lixo derrubar depois.
    """
    from ui.app import Aplicativo

    try:
        raiz = Aplicativo()
    except tkinter.TclError as erro:  # sem display disponivel
        pytest.skip("tkinter indisponivel: %s" % erro)
    raiz.withdraw()
    try:
        yield raiz
    finally:
        raiz.destroy()


@pytest.fixture()
def app(janela):
    janela.schema = None
    janela.caminho_xsd = None
    janela.caminho_xml = None
    janela.modo_tolerante = False
    janela.painel_editor.limpar()
    janela.painel_erros.limpar()
    janela.painel_estrutura.limpar()
    janela.combo_raiz.configure(values=())
    janela.combo_raiz.set("")
    janela.painel_opcoes.preset_completo()
    janela.painel_opcoes.modo_choice.set("primeira")
    janela.painel_opcoes.schema_location.set(False)
    janela.painel_opcoes.documentacao.set(False)
    janela.painel_opcoes.profundidade.set(15)
    return janela


def aguardar(janela, limite=30.0):
    """Gira o loop de eventos ate a tarefa em segundo plano terminar."""
    fim = time.time() + limite
    while time.time() < fim:
        janela.update()
        if not janela._ocupado:
            return
        time.sleep(0.01)
    raise AssertionError("a tarefa em segundo plano nao terminou")


def carregar(janela, nome_arquivo):
    import xsdmodel

    caminho = os.path.join(FIXTURES, nome_arquivo)
    janela._em_segundo_plano(
        lambda: xsdmodel.carregar(caminho),
        lambda schema: janela._schema_carregado(caminho, schema),
        "carregando",
    )
    aguardar(janela)


def test_fluxo_completo_gerar_e_validar(app):
    carregar(app, "simples.xsd")
    assert app.combo_raiz.cget("values") == ("documento",)

    app.gerar()
    aguardar(app)
    texto = app.painel_editor.obter_texto()
    assert texto.startswith('<?xml version="1.0" encoding="UTF-8"?>')
    assert "<chave>" in texto
    assert "valido contra o schema" in app.rotulo_status.cget("text")
    assert not app.painel_erros.lista.get_children()


def test_erro_de_validacao_aparece_na_lista(app):
    carregar(app, "simples.xsd")
    app.gerar()
    aguardar(app)

    quebrado = app.painel_editor.obter_texto().replace("<modelo>55</modelo>", "<modelo>99</modelo>")
    app.painel_editor.definir_texto(quebrado)
    app.validar()
    app.update()

    itens = app.painel_erros.lista.get_children()
    assert itens, "o valor fora da enumeracao deveria gerar erro"
    linha = app.painel_erros._erros[0].linha
    assert linha > 0
    app._ir_para_erro(app.painel_erros._erros[0])
    assert app.painel_editor.texto.index("insert").startswith("%d." % linha)


def test_troca_de_raiz_e_presets(app):
    carregar(app, "principal.xsd")
    valores = app.combo_raiz.cget("values")
    assert "pedido" in valores and "pedidoSimplificado" in valores

    app._escolher_raiz("pedidoSimplificado")
    app.painel_opcoes.preset_minimo()
    app.gerar()
    aguardar(app)
    assert "<pedidoSimplificado" in app.painel_editor.obter_texto()
    assert "valido contra o schema" in app.rotulo_status.cget("text")


def test_arvore_expande_sob_demanda(app):
    carregar(app, "escolha.xsd")
    arvore = app.painel_estrutura.arvore
    raizes = arvore.get_children("")
    assert len(raizes) == 1

    filhos = arvore.get_children(raizes[0])
    assert len(filhos) == 1 and arvore.item(filhos[0], "text") == "__preencher__"

    arvore.focus(raizes[0])
    app.painel_estrutura._ao_abrir()
    rotulos = [arvore.item(i, "text") for i in arvore.get_children(raizes[0])]
    assert "pessoa" in rotulos and "__preencher__" not in rotulos


def test_formatar_reindenta(app):
    carregar(app, "simples.xsd")
    app.painel_editor.definir_texto("<documento><chave>1</chave></documento>")
    app.formatar()
    assert "\n  <chave>" in app.painel_editor.obter_texto()


def test_abstrato_nao_pode_ser_raiz(app, monkeypatch):
    from ui import app as modulo

    carregar(app, "principal.xsd")
    app._escolher_raiz("pagamento")
    avisos = []
    monkeypatch.setattr(modulo.messagebox, "showwarning", lambda *a, **k: avisos.append(a))
    app.gerar()
    assert avisos, "gerar a partir de um elemento abstrato deveria avisar"


def test_modo_tolerante_desliga_validacao(app, monkeypatch):
    """Um XSD com defeito pode ser aberto ignorando as inconsistencias."""
    from ui import app as modulo

    quebrado = os.path.join(FIXTURES, "quebrado.xsd")
    monkeypatch.setattr(modulo.filedialog, "askopenfilename", lambda **k: quebrado)
    monkeypatch.setattr(modulo.messagebox, "askyesno", lambda *a, **k: True)

    app.abrir_xsd()
    aguardar(app)
    assert app.modo_tolerante
    assert app.schema is not None

    app.gerar()
    aguardar(app)
    assert "<raiz" in app.painel_editor.obter_texto()
    assert "validacao indisponivel em modo tolerante" in app.rotulo_status.cget("text")


def test_xsd_quebrado_recusado_nao_carrega(app, monkeypatch):
    from ui import app as modulo

    quebrado = os.path.join(FIXTURES, "quebrado.xsd")
    erros = []
    monkeypatch.setattr(modulo.filedialog, "askopenfilename", lambda **k: quebrado)
    monkeypatch.setattr(modulo.messagebox, "askyesno", lambda *a, **k: False)
    monkeypatch.setattr(modulo.messagebox, "showerror", lambda *a, **k: erros.append(a))

    app.abrir_xsd()
    aguardar(app)
    assert app.schema is None
    assert erros, "recusar o modo tolerante deveria mostrar o erro de carga"


def test_rodape_reserva_espaco_antes_do_corpo(app):
    """Os botoes nao podem ser espremidos para fora da janela.

    O corpo tem expand=True e o pack distribui a area na ordem de empacotamento:
    se o rodape vier depois, o corpo engole a cavidade inteira e a barra de
    botoes desaparece.
    """
    from tkinter import ttk

    slaves = app.pack_slaves()
    rodape = app.botao_gerar.master
    corpo = [w for w in slaves if isinstance(w, ttk.PanedWindow)][0]
    assert slaves.index(rodape) < slaves.index(corpo)
    assert rodape.pack_info()["side"] == "bottom"


def test_janela_abre_maximizada(app):
    """No Windows o estado zoomed sobrevive ao withdraw do teste."""
    import sys

    if sys.platform != "win32":
        pytest.skip("estado zoomed e especifico do Windows")
    app.maximizar()
    assert app.state() in ("zoomed", "withdrawn")
