"""Visualizador do XML e lista de erros de validacao."""
from __future__ import annotations

import re
import tkinter as tk
from tkinter import ttk

from ui import temas

FONTE = ("Consolas", 10)

# Acima disso o realce colorido custa mais do que ajuda.
LIMITE_REALCE = 400_000

_REGRAS = re.compile(
    r"(?P<comentario><!--.*?-->)"
    r"|(?P<pi><\?.*?\?>)"
    r"|(?P<tag></?[A-Za-z_][\w:.\-]*)"
    r"|(?P<atributo>[A-Za-z_][\w:.\-]*(?=\s*=\s*\"))"
    r"|(?P<valor>\"[^\"]*\")"
    r"|(?P<fecha>/?>)",
    re.DOTALL,
)

# Etiqueta de realce -> token da paleta. As chaves tem de continuar iguais aos
# nomes dos grupos de _REGRAS: e por elas que realcar() casa o que o regex achou.
TAGS = {
    "comentario": "sintaxe_comentario",
    "pi": "sintaxe_comentario",
    "tag": "sintaxe_tag",
    "fecha": "sintaxe_tag",
    "atributo": "sintaxe_atributo",
    "valor": "sintaxe_valor",
}


class PainelEditor(ttk.Frame):
    """Area de texto com realce simples de sintaxe XML."""

    def __init__(self, mestre):
        super().__init__(mestre)
        self.texto = tk.Text(self, wrap="none", font=FONTE, undo=True, padx=6, pady=4)
        barra_v = ttk.Scrollbar(self, orient="vertical", command=self.texto.yview)
        barra_h = ttk.Scrollbar(self, orient="horizontal", command=self.texto.xview)
        self.texto.configure(yscrollcommand=barra_v.set, xscrollcommand=barra_h.set)

        self.texto.grid(row=0, column=0, sticky="nsew")
        barra_v.grid(row=0, column=1, sticky="ns")
        barra_h.grid(row=1, column=0, sticky="ew")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        self.aplicar_tema(temas.padrao())

    # ------------------------------------------------------------------ API

    def aplicar_tema(self, paleta) -> None:
        self.texto.configure(
            background=paleta.fundo_campo,
            foreground=paleta.texto,
            insertbackground=paleta.cursor,
            selectbackground=paleta.selecao_fundo,
            selectforeground=paleta.selecao_texto,
            # Sem isto a selecao some quando o foco vai para a arvore.
            inactiveselectbackground=paleta.selecao_fundo,
            # O anel de foco que o Tk desenha em volta do Text fica gritante no escuro.
            highlightthickness=0,
        )
        for nome, token in TAGS.items():
            self.texto.tag_configure(nome, foreground=getattr(paleta, token))
        self.texto.tag_configure("linha_erro", background=paleta.linha_erro_fundo)

    def definir_texto(self, conteudo: str) -> None:
        self.texto.delete("1.0", "end")
        self.texto.insert("1.0", conteudo)
        self.texto.edit_reset()
        self.realcar()
        self.texto.mark_set("insert", "1.0")
        self.texto.see("1.0")

    def obter_texto(self) -> str:
        # O Text sempre acrescenta um \n final que nao faz parte do documento.
        return self.texto.get("1.0", "end-1c")

    def limpar(self) -> None:
        self.texto.delete("1.0", "end")

    def ir_para_linha(self, linha: int) -> None:
        self.texto.tag_remove("linha_erro", "1.0", "end")
        if linha <= 0:
            return
        indice = "%d.0" % linha
        self.texto.tag_add("linha_erro", indice, "%d.end" % linha)
        self.texto.mark_set("insert", indice)
        self.texto.see(indice)
        self.texto.focus_set()

    def realcar(self) -> None:
        conteudo = self.obter_texto()
        for nome in TAGS:
            self.texto.tag_remove(nome, "1.0", "end")
        if len(conteudo) > LIMITE_REALCE:
            return
        # Converter deslocamentos em indices "linha.coluna" no Python evita uma
        # chamada ao Tk por ocorrencia, que e o que tornaria isso lento.
        inicios = [0]
        for linha in conteudo.split("\n")[:-1]:
            inicios.append(inicios[-1] + len(linha) + 1)

        def posicao(deslocamento: int) -> str:
            baixo, alto = 0, len(inicios) - 1
            while baixo < alto:
                meio = (baixo + alto + 1) // 2
                if inicios[meio] <= deslocamento:
                    baixo = meio
                else:
                    alto = meio - 1
            return "%d.%d" % (baixo + 1, deslocamento - inicios[baixo])

        for ocorrencia in _REGRAS.finditer(conteudo):
            nome = ocorrencia.lastgroup
            if nome in TAGS:
                self.texto.tag_add(
                    nome, posicao(ocorrencia.start()), posicao(ocorrencia.end())
                )


class PainelErros(ttk.Frame):
    """Lista os erros de validacao; o duplo clique salta para a linha."""

    def __init__(self, mestre, ao_escolher=None):
        super().__init__(mestre)
        self.ao_escolher = ao_escolher
        colunas = ("linha", "coluna", "mensagem")
        self.lista = ttk.Treeview(self, columns=colunas, show="headings", selectmode="browse")
        self.lista.heading("linha", text="Linha")
        self.lista.heading("coluna", text="Coluna")
        self.lista.heading("mensagem", text="Mensagem")
        self.lista.column("linha", width=60, anchor="e", stretch=False)
        self.lista.column("coluna", width=60, anchor="e", stretch=False)
        self.lista.column("mensagem", width=700)

        barra = ttk.Scrollbar(self, orient="vertical", command=self.lista.yview)
        self.lista.configure(yscrollcommand=barra.set)
        self.lista.grid(row=0, column=0, sticky="nsew")
        barra.grid(row=0, column=1, sticky="ns")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        self.lista.bind("<Double-1>", self._clique)
        self.lista.bind("<Return>", self._clique)
        self._erros: list = []

    def aplicar_tema(self, paleta) -> None:
        """Nada a fazer: a Treeview e inteiramente pintada pelo ttk.Style.

        O metodo existe para o painel entrar na mesma cadeia dos outros.
        """

    def mostrar(self, erros: list) -> None:
        self._erros = list(erros)
        self.lista.delete(*self.lista.get_children())
        for indice, erro in enumerate(self._erros):
            self.lista.insert(
                "", "end", iid=str(indice), values=(erro.linha, erro.coluna, erro.mensagem)
            )

    def limpar(self) -> None:
        self.mostrar([])

    def _clique(self, _evento=None):
        selecao = self.lista.selection()
        if not selecao or not self.ao_escolher:
            return
        erro = self._erros[int(selecao[0])]
        self.ao_escolher(erro)
