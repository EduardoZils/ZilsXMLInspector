"""Arvore navegavel da estrutura do XSD, expandida sob demanda."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

import xsdmodel

MARCADOR = "__preencher__"


class PainelEstrutura(ttk.Frame):
    """Mostra os elementos globais e, ao expandir, seus filhos.

    Os filhos so sao calculados quando o no e aberto: um schema recursivo tem
    profundidade infinita e um schema grande levaria segundos para ser expandido
    de uma vez.
    """

    def __init__(self, mestre, ao_escolher_raiz=None, ao_selecionar=None):
        super().__init__(mestre)
        self.ao_escolher_raiz = ao_escolher_raiz
        self.ao_selecionar = ao_selecionar
        self._nos: dict = {}

        colunas = ("cardinalidade", "tipo", "detalhe")
        self.arvore = ttk.Treeview(self, columns=colunas, selectmode="browse")
        self.arvore.heading("#0", text="Elemento / atributo")
        self.arvore.heading("cardinalidade", text="Card.")
        self.arvore.heading("tipo", text="Tipo")
        self.arvore.heading("detalhe", text="Restricoes / doc.")
        self.arvore.column("#0", width=200, minwidth=120)
        self.arvore.column("cardinalidade", width=55, anchor="center", stretch=False)
        self.arvore.column("tipo", width=110)
        self.arvore.column("detalhe", width=200)

        barra_v = ttk.Scrollbar(self, orient="vertical", command=self.arvore.yview)
        barra_h = ttk.Scrollbar(self, orient="horizontal", command=self.arvore.xview)
        self.arvore.configure(yscrollcommand=barra_v.set, xscrollcommand=barra_h.set)
        self.arvore.grid(row=0, column=0, sticky="nsew")
        barra_v.grid(row=0, column=1, sticky="ns")
        barra_h.grid(row=1, column=0, sticky="ew")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        self.arvore.tag_configure("atributo", foreground="#7f0055")
        self.arvore.tag_configure("grupo", foreground="#0b5394")
        self.arvore.tag_configure("any", foreground="#a06000")
        self.arvore.tag_configure("raiz", font=("Segoe UI", 9, "bold"))

        self.arvore.bind("<<TreeviewOpen>>", self._ao_abrir)
        self.arvore.bind("<<TreeviewSelect>>", self._ao_selecionar)
        self.arvore.bind("<Double-1>", self._ao_duplo_clique)

    # ------------------------------------------------------------------ API

    def carregar(self, schema) -> None:
        self.limpar()
        for elemento in xsdmodel.elementos_globais(schema):
            no = xsdmodel.no_de_elemento(elemento, minimo=1, maximo=1)
            self._inserir("", no, raiz=True)

    def limpar(self) -> None:
        self.arvore.delete(*self.arvore.get_children())
        self._nos.clear()

    def selecionar_raiz(self, nome: str) -> None:
        """Destaca o elemento global correspondente ao nome informado."""
        for item in self.arvore.get_children(""):
            no = self._nos.get(item)
            if no and no.rotulo == nome:
                self.arvore.selection_set(item)
                self.arvore.see(item)
                return

    # -------------------------------------------------------------- internos

    def _inserir(self, pai: str, no, raiz: bool = False) -> str:
        etiquetas = [no.especie]
        if raiz:
            etiquetas.append("raiz")
        rotulo = no.rotulo
        if no.especie == "grupo":
            rotulo = "<%s>" % no.rotulo
        item = self.arvore.insert(
            pai,
            "end",
            text=rotulo,
            values=(no.cardinalidade, no.tipo, no.detalhe),
            tags=tuple(etiquetas),
        )
        self._nos[item] = no
        if no.tem_filhos:
            self.arvore.insert(item, "end", text=MARCADOR)
        return item

    def _ao_abrir(self, _evento=None) -> None:
        item = self.arvore.focus()
        filhos = self.arvore.get_children(item)
        if not filhos or self.arvore.item(filhos[0], "text") != MARCADOR:
            return
        self.arvore.delete(filhos[0])
        no = self._nos.get(item)
        if no is None:
            return
        for filho in xsdmodel.filhos(no):
            self._inserir(item, filho)

    def _ao_selecionar(self, _evento=None) -> None:
        if not self.ao_selecionar:
            return
        selecao = self.arvore.selection()
        self.ao_selecionar(self._nos.get(selecao[0]) if selecao else None)

    def _ao_duplo_clique(self, _evento=None):
        item = self.arvore.focus()
        no = self._nos.get(item)
        if no is None or not self.ao_escolher_raiz:
            return
        # So os elementos globais (nos de primeiro nivel) podem virar raiz.
        if self.arvore.parent(item) == "":
            self.ao_escolher_raiz(no.rotulo)
