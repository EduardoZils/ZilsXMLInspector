"""Detalhes do item selecionado na arvore do XSD.

Responde a pergunta que se faz o tempo todo lendo um leiaute: o que exatamente
este campo aceita? Tipo, cardinalidade, documentacao, pattern, tamanhos, faixa
numerica e a lista completa de valores permitidos.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

import xsdmodel

FONTE = ("Segoe UI", 9)
FONTE_MONO = ("Consolas", 9)

CORES_ESPECIE = {
    "elemento": "#0b5394",
    "atributo": "#7f0055",
    "grupo": "#0b5394",
    "any": "#a06000",
}


class PainelDetalhes(ttk.LabelFrame):
    def __init__(self, mestre):
        super().__init__(mestre, text="Detalhes do item selecionado", padding=(6, 2, 6, 6))

        self.texto = tk.Text(
            self,
            wrap="word",
            font=FONTE,
            height=13,
            padx=6,
            pady=4,
            relief="flat",
            background="#fbfbfb",
            cursor="arrow",
            # Parada de tabulacao no lugar de espacos: a fonte e proporcional e
            # o alinhamento por espacos nao fecharia.
            tabs=("130p",),
        )
        barra = ttk.Scrollbar(self, orient="vertical", command=self.texto.yview)
        self.texto.configure(yscrollcommand=barra.set)
        self.texto.grid(row=0, column=0, sticky="nsew")
        barra.grid(row=0, column=1, sticky="ns")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        self.texto.tag_configure("titulo", font=("Segoe UI", 11, "bold"))
        self.texto.tag_configure("especie", font=("Segoe UI", 9), foreground="#777777")
        self.texto.tag_configure("secao", font=("Segoe UI", 9, "bold"), spacing1=8)
        self.texto.tag_configure("rotulo", foreground="#555555")
        self.texto.tag_configure("valor", font=FONTE_MONO)
        self.texto.tag_configure("doc", foreground="#333333", spacing3=2)
        self.texto.tag_configure("codigo", font=FONTE_MONO, foreground="#0b5394")
        self.texto.tag_configure("vazio", foreground="#999999")
        for especie, cor in CORES_ESPECIE.items():
            self.texto.tag_configure("titulo_" + especie, font=("Segoe UI", 11, "bold"),
                                     foreground=cor)

        self.limpar()

    # ------------------------------------------------------------------ API

    def limpar(self) -> None:
        self._escrever(
            [("Selecione um elemento ou atributo na arvore para ver os detalhes.", "vazio")]
        )

    def mostrar(self, no) -> None:
        detalhe = xsdmodel.detalhes_do_no(no)
        if not detalhe.titulo:
            self.limpar()
            return
        self._escrever(list(self._montar(detalhe)))

    # -------------------------------------------------------------- internos

    def _montar(self, detalhe):
        yield (detalhe.titulo, "titulo_" + detalhe.especie
               if detalhe.especie in CORES_ESPECIE else "titulo")
        yield ("   " + detalhe.especie + "\n", "especie")

        for rotulo, valor in detalhe.cabecalho:
            if not valor:
                continue
            yield (rotulo + "\t", "rotulo")
            yield (str(valor) + "\n", "valor")

        if detalhe.documentacao:
            yield ("\nDocumentacao\n", "secao")
            yield (detalhe.documentacao + "\n", "doc")

        if detalhe.restricoes:
            yield ("\nRestricoes\n", "secao")
            for rotulo, valor in detalhe.restricoes:
                yield (rotulo + "\t", "rotulo")
                yield (valor + "\n", "valor")

        if detalhe.valores:
            yield ("\nValores permitidos (%d)\n" % len(detalhe.valores), "secao")
            documentados = any(doc for _v, doc in detalhe.valores)
            if documentados:
                for valor, doc in detalhe.valores:
                    yield (valor + "\t", "codigo")
                    yield ((doc or "") + "\n", "doc")
            else:
                # Sem documentacao individual, uma lista corrida cabe melhor.
                yield ("   ".join(v for v, _doc in detalhe.valores) + "\n", "codigo")

        if detalhe.exemplo:
            yield ("\nExemplo gerado\n", "secao")
            yield (detalhe.exemplo + "\n", "valor")

    def _escrever(self, pedacos) -> None:
        self.texto.configure(state="normal")
        self.texto.delete("1.0", "end")
        for conteudo, etiqueta in pedacos:
            self.texto.insert("end", conteudo, etiqueta)
        self.texto.configure(state="disabled")
        self.texto.see("1.0")
