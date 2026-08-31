"""Temas visuais do aplicativo.

Os controles ttk sao pintados por temas prontos, de terceiros, que ficam em
`temas_prontos/` (veja o CREDITOS.md de la). Cada um traz suas proprias imagens
para cada estado de cada controle, entao trocar de tema troca a arte, nao a
construcao dos widgets.

E o que o tema nativo do Windows nao permitia: la os controles sao desenhados
pelo sistema e ignoram qualquer cor configurada, e a unica saida para escurecer
era trocar por um tema que o proprio Tk desenha -- o que mudava forma e medidas
junto com a cor.

Sobra para este modulo o que os temas prontos nao alcancam: os widgets Tk
classicos (o editor de XML e o painel de detalhes, que sao tk.Text; a barra de
menus e os menus suspensos) e as cores proprias do aplicativo (realce de
sintaxe XML, mensagens de status, especies de no na arvore).
"""
from __future__ import annotations

import dataclasses
import os
import sys
import tkinter as tk
from tkinter import ttk


@dataclasses.dataclass(frozen=True)
class Realces:
    """Cores que sao do aplicativo, nao do tema.

    Valem iguais para todos os temas claros, e outras iguais para todos os
    escuros: o que muda entre Forest, Azure e Sun Valley e a pintura dos
    controles, nao o significado de "erro", "tag XML" ou "atributo".
    """

    texto_suave: str
    texto_apagado: str

    status_normal: str
    status_erro: str
    status_aviso: str
    status_ok: str

    sintaxe_comentario: str
    sintaxe_tag: str
    sintaxe_atributo: str
    sintaxe_valor: str
    linha_erro_fundo: str

    especie_elemento: str
    especie_atributo: str
    especie_grupo: str
    especie_any: str
    detalhe_especie: str
    detalhe_doc: str


# Os hexes historicos do aplicativo, de quando so existia a aparencia clara.
REALCES_CLAROS = Realces(
    texto_suave="#555555",
    texto_apagado="#999999",
    status_normal="#333333",
    status_erro="#B00020",
    status_aviso="#A06000",
    status_ok="#1A7F37",
    sintaxe_comentario="#7A7A7A",
    sintaxe_tag="#0B5394",
    sintaxe_atributo="#7F0055",
    sintaxe_valor="#067D17",
    linha_erro_fundo="#FFE0E0",
    especie_elemento="#0B5394",
    especie_atributo="#7F0055",
    especie_grupo="#0B5394",
    especie_any="#A06000",
    detalhe_especie="#777777",
    detalhe_doc="#333333",
)

REALCES_ESCUROS = Realces(
    texto_suave="#C5C5C5",
    texto_apagado="#8A8A8A",
    status_normal="#C5C5C5",
    status_erro="#FF99A4",
    status_aviso="#FFC46B",
    status_ok="#6CD394",
    sintaxe_comentario="#A0A0A0",
    sintaxe_tag="#4CC2FF",
    sintaxe_atributo="#E39FF6",
    sintaxe_valor="#7FD98A",
    linha_erro_fundo="#5A2530",
    especie_elemento="#4CC2FF",
    especie_atributo="#E39FF6",
    especie_grupo="#4CC2FF",
    especie_any="#FFC46B",
    detalhe_especie="#9A9A9A",
    detalhe_doc="#DADADA",
)


@dataclasses.dataclass(frozen=True)
class Tema:
    """Um tema pronto, mais as cores que o aplicativo precisa ao lado dele."""

    identificador: str  # o nome do tema no ttk, e o que vai para o config.json
    rotulo: str  # o que o usuario le na janela de Opcoes
    familia: str  # como o usuario a chama
    pasta: str  # onde os arquivos dela moram, em temas_prontos/
    escuro: bool

    # Tiradas dos proprios arquivos do tema, para os widgets classicos
    # combinarem com os controles ttk ao lado deles.
    fundo: str
    fundo_campo: str
    fundo_alternativo: str
    fundo_menu: str
    fundo_menu_ativo: str
    texto: str
    texto_desabilitado: str
    selecao_fundo: str
    selecao_texto: str

    realces: Realces

    def __getattr__(self, nome: str):
        """Faz o tema responder tambem pelos campos de realce.

        Os paineis falam com um objeto so -- paleta.texto, paleta.sintaxe_tag,
        paleta.status_erro -- sem precisar saber de onde cada cor veio.
        """
        realces = object.__getattribute__(self, "realces")
        try:
            return getattr(realces, nome)
        except AttributeError:
            raise AttributeError(nome) from None

    @property
    def cursor(self) -> str:
        return self.texto


def _tema(identificador, rotulo, familia, escuro, **cores) -> Tema:
    return Tema(
        identificador=identificador,
        rotulo=rotulo,
        familia=familia,
        # A pasta e o identificador sem a variante: "forest-dark" -> "forest".
        pasta=identificador.rsplit("-", 1)[0],
        escuro=escuro,
        realces=REALCES_ESCUROS if escuro else REALCES_CLAROS,
        **cores
    )


# A ordem aqui e a ordem em que aparecem na janela de Opcoes.
TEMAS = (
    _tema(
        "forest-light", "Claro", "Forest", False,
        fundo="#FFFFFF", fundo_campo="#FFFFFF", fundo_alternativo="#FBFBFB",
        fundo_menu="#FFFFFF", fundo_menu_ativo="#E6F0E9",
        texto="#313131", texto_desabilitado="#8A8A8A",
        selecao_fundo="#217346", selecao_texto="#FFFFFF",
    ),
    _tema(
        "forest-dark", "Escuro", "Forest", True,
        fundo="#313131", fundo_campo="#2A2A2A", fundo_alternativo="#2E2E2E",
        fundo_menu="#313131", fundo_menu_ativo="#3F3F3F",
        texto="#EEEEEE", texto_desabilitado="#8A8A8A",
        selecao_fundo="#217346", selecao_texto="#FFFFFF",
    ),
    _tema(
        "azure-light", "Claro", "Azure", False,
        fundo="#FFFFFF", fundo_campo="#FFFFFF", fundo_alternativo="#FBFBFB",
        fundo_menu="#FFFFFF", fundo_menu_ativo="#E5F1FB",
        texto="#000000", texto_desabilitado="#737373",
        selecao_fundo="#007FFF", selecao_texto="#FFFFFF",
    ),
    _tema(
        "azure-dark", "Escuro", "Azure", True,
        fundo="#333333", fundo_campo="#2B2B2B", fundo_alternativo="#2F2F2F",
        fundo_menu="#333333", fundo_menu_ativo="#414141",
        texto="#FFFFFF", texto_desabilitado="#AAAAAA",
        selecao_fundo="#007FFF", selecao_texto="#FFFFFF",
    ),
    _tema(
        "sun-valley-light", "Claro", "Sun Valley", False,
        fundo="#FAFAFA", fundo_campo="#FFFFFF", fundo_alternativo="#F7F7F7",
        fundo_menu="#FAFAFA", fundo_menu_ativo="#E9E9E9",
        texto="#1C1C1C", texto_desabilitado="#A0A0A0",
        selecao_fundo="#2F60D8", selecao_texto="#FFFFFF",
    ),
    _tema(
        "sun-valley-dark", "Escuro", "Sun Valley", True,
        fundo="#1C1C1C", fundo_campo="#272727", fundo_alternativo="#232323",
        fundo_menu="#1C1C1C", fundo_menu_ativo="#2F2F2F",
        texto="#FAFAFA", texto_desabilitado="#595959",
        selecao_fundo="#2F60D8", selecao_texto="#FFFFFF",
    ),
)

TEMA_PADRAO = "forest-light"

# Onde mora o codigo de cada familia. O Forest traz uma variante por arquivo;
# o Azure e o Sun Valley definem as duas de uma vez.
_ARQUIVOS = (
    ("azure", "azure.tcl"),
    ("forest", "forest-light.tcl"),
    ("forest", "forest-dark.tcl"),
    ("sun-valley", "sv.tcl"),
)


def familias() -> tuple:
    """Os nomes das familias, na ordem em que aparecem em TEMAS."""
    vistas = []
    for tema in TEMAS:
        if tema.familia not in vistas:
            vistas.append(tema.familia)
    return tuple(vistas)


def da_familia(familia: str) -> tuple:
    return tuple(t for t in TEMAS if t.familia == familia)


def padrao() -> Tema:
    """O tema usado quando nao ha preferencia gravada."""
    return por_identificador(TEMA_PADRAO)


def por_identificador(identificador) -> Tema:
    """Devolve o tema pedido; qualquer valor desconhecido cai no padrao."""
    for tema in TEMAS:
        if tema.identificador == identificador:
            return tema
    for tema in TEMAS:
        if tema.identificador == TEMA_PADRAO:
            return tema
    return TEMAS[0]


# -------------------------------------------------------------------- carga


def pasta_dos_temas() -> str:
    """Onde estao os arquivos dos temas prontos.

    Empacotado pelo PyInstaller, o conteudo vai para a pasta temporaria que ele
    monta; fora dele, fica ao lado deste modulo.
    """
    empacotado = getattr(sys, "_MEIPASS", None)
    if empacotado:
        return os.path.join(empacotado, "ui", "temas_prontos")
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "temas_prontos")


def carregar_familia(raiz, familia: str) -> None:
    """Ensina uma familia de temas ao interpretador Tk desta janela.

    Cada familia custa algumas centenas de milissegundos, porque sao dezenas de
    imagens: por isso a carga e sob demanda, e nao toda na abertura. Um arquivo
    que nao carregue nao pode derrubar o aplicativo -- no pior caso aquele tema
    fica indisponivel e o Tk segue com o que ja tinha.
    """
    carregadas = getattr(raiz, "_familias_carregadas", None)
    if carregadas is None:
        carregadas = set()
        raiz._familias_carregadas = carregadas
    if familia in carregadas:
        return
    carregadas.add(familia)

    base = pasta_dos_temas()
    for pasta, arquivo in _ARQUIVOS:
        if pasta != familia:
            continue
        # O Tcl quer barras normais mesmo no Windows.
        caminho = os.path.join(base, pasta, arquivo).replace(os.sep, "/")
        try:
            raiz.tk.call("source", caminho)
        except tk.TclError:
            pass


def carregar(raiz) -> None:
    """Carrega todas as familias. Usado por quem precisa da lista completa."""
    for pasta, _arquivo in _ARQUIVOS:
        carregar_familia(raiz, pasta)


def disponiveis(raiz) -> tuple:
    """Os temas que o Tk realmente conseguiu carregar."""
    carregar(raiz)
    nomes = set(ttk.Style(raiz).theme_names())
    return tuple(t for t in TEMAS if t.identificador in nomes)


def aplicar(raiz, tema: Tema) -> ttk.Style:
    """Poe o tema em uso e prepara o que ele nao alcanca.

    So carrega a familia do tema pedido: na abertura, as outras duas ainda nao
    interessam.
    """
    carregar_familia(raiz, tema.pasta)
    estilo = ttk.Style(raiz)
    if tema.identificador in estilo.theme_names():
        estilo.theme_use(tema.identificador)
    _preparar_popdown(raiz, tema)
    return estilo


# ------------------------------------------------------- widgets classicos


def _preparar_popdown(raiz, tema: Tema) -> None:
    """A lista que o Combobox abre e um Listbox fora do alcance do tema."""
    try:
        raiz.option_add("*TCombobox*Listbox.background", tema.fundo_campo)
        raiz.option_add("*TCombobox*Listbox.foreground", tema.texto)
        raiz.option_add("*TCombobox*Listbox.selectBackground", tema.selecao_fundo)
        raiz.option_add("*TCombobox*Listbox.selectForeground", tema.selecao_texto)
    except tk.TclError:
        pass


def recolorir_popdown(combo, tema: Tema) -> None:
    """Repinta a lista de um Combobox que ja existe.

    O option_add so vale para widgets criados depois dele, entao na troca de
    tema em tempo de execucao e preciso alcancar o Listbox pelo nome que o Tk
    da a ele. PopdownWindow cria a janela sob demanda, entao isto funciona
    mesmo antes do primeiro clique no combo.
    """
    try:
        caminho = combo.tk.eval("ttk::combobox::PopdownWindow %s" % combo)
        combo.tk.call(
            caminho + ".f.l",
            "configure",
            "-background", tema.fundo_campo,
            "-foreground", tema.texto,
            "-selectbackground", tema.selecao_fundo,
            "-selectforeground", tema.selecao_texto,
        )
    except tk.TclError:
        pass


def aplicar_barra_titulo(janela, escuro: bool) -> bool:
    """Pinta de escuro a barra de titulo no Windows 11. Puro enfeite.

    Falhar aqui nao tem consequencia: a janela so fica com a barra clara.
    """
    if sys.platform != "win32":
        return False
    try:
        import ctypes

        janela.update_idletasks()
        # winfo_id() devolve o frame interno do Tk; o DWM quer o toplevel.
        interno = janela.winfo_id()
        hwnd = ctypes.windll.user32.GetParent(interno) or interno
        valor = ctypes.c_int(1 if escuro else 0)
        # 20 = DWMWA_USE_IMMERSIVE_DARK_MODE; 19 nas builds do Win10 antes do 20H1.
        for atributo in (20, 19):
            resultado = ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, atributo, ctypes.byref(valor), ctypes.sizeof(valor)
            )
            if resultado == 0:
                return True
    except Exception:
        pass
    return False
