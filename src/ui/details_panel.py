"""Detalhes do item selecionado na arvore do XSD.

Responde a pergunta que se faz o tempo todo lendo um leiaute: o que exatamente
este campo aceita? Tipo, cardinalidade, documentacao, pattern, tamanhos, faixa
numerica e a lista completa de valores permitidos.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

import xsdmodel
from ui import temas

FONTE = ("Segoe UI", 9)
FONTE_MONO = ("Consolas", 9)

# Especie do no -> token da paleta que da a cor do titulo.
TOKENS_ESPECIE = {
    "elemento": "especie_elemento",
    "atributo": "especie_atributo",
    "grupo": "especie_grupo",
    "any": "especie_any",
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

        # Aqui so o que nao depende de tema; a cor vem toda de aplicar_tema.
        self.texto.tag_configure("titulo", font=("Segoe UI", 11, "bold"))
        self.texto.tag_configure("especie", font=("Segoe UI", 9))
        self.texto.tag_configure("secao", font=("Segoe UI", 9, "bold"), spacing1=8)
        self.texto.tag_configure("valor", font=FONTE_MONO)
        self.texto.tag_configure("doc", spacing3=2)
        self.texto.tag_configure("codigo", font=FONTE_MONO)
        for especie in TOKENS_ESPECIE:
            self.texto.tag_configure("titulo_" + especie, font=("Segoe UI", 11, "bold"))

        self.aplicar_tema(temas.padrao())
        self.limpar()

    # ------------------------------------------------------------------ API

    def aplicar_tema(self, paleta) -> None:
        self.texto.configure(
            background=paleta.fundo_alternativo,
            # O widget vive em state="disabled" (e so leitura). O Text, ao
            # contrario do Entry, nao tem disabledforeground: desabilitado ele
            # continua desenhando com o foreground normal.
            foreground=paleta.texto,
            insertbackground=paleta.cursor,
            selectbackground=paleta.selecao_fundo,
            selectforeground=paleta.selecao_texto,
            inactiveselectbackground=paleta.selecao_fundo,
            highlightthickness=0,
        )
        self.texto.tag_configure("titulo", foreground=paleta.texto)
        self.texto.tag_configure("especie", foreground=paleta.detalhe_especie)
        self.texto.tag_configure("secao", foreground=paleta.texto)
        self.texto.tag_configure("rotulo", foreground=paleta.texto_suave)
        self.texto.tag_configure("doc", foreground=paleta.detalhe_doc)
        self.texto.tag_configure("codigo", foreground=paleta.especie_elemento)
        self.texto.tag_configure("vazio", foreground=paleta.texto_apagado)
        for especie, token in TOKENS_ESPECIE.items():
            self.texto.tag_configure("titulo_" + especie, foreground=getattr(paleta, token))

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
               if detalhe.especie in TOKENS_ESPECIE else "titulo")
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
