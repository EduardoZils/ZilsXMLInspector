"""Opcoes de geracao do XML de exemplo."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

import generator
from ui import temas


class PainelOpcoes(ttk.Frame):
    def __init__(self, mestre):
        super().__init__(mestre, padding=10)

        self.incluir_opcionais = tk.BooleanVar(value=True)
        self.incluir_atributos = tk.BooleanVar(value=True)
        self.repeticoes = tk.IntVar(value=1)
        self.profundidade = tk.IntVar(value=15)
        self.modo_choice = tk.StringVar(value="primeira")
        self.schema_location = tk.BooleanVar(value=False)
        self.documentacao = tk.BooleanVar(value=False)

        linha = 0
        conteudo = ttk.LabelFrame(self, text="Conteudo", padding=8)
        conteudo.grid(row=linha, column=0, sticky="ew")
        conteudo.columnconfigure(1, weight=1)
        ttk.Checkbutton(
            conteudo,
            text="Incluir elementos opcionais (minOccurs=0)",
            variable=self.incluir_opcionais,
        ).grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Checkbutton(
            conteudo,
            text='Incluir atributos opcionais (use="optional")',
            variable=self.incluir_atributos,
        ).grid(row=1, column=0, columnspan=2, sticky="w")
        ttk.Label(conteudo, text="Repeticoes quando maxOccurs > 1:").grid(
            row=2, column=0, sticky="w", pady=(6, 0)
        )
        ttk.Spinbox(
            conteudo, from_=1, to=50, width=6, textvariable=self.repeticoes
        ).grid(row=2, column=1, sticky="w", pady=(6, 0))
        ttk.Label(conteudo, text="Profundidade maxima:").grid(row=3, column=0, sticky="w")
        ttk.Spinbox(
            conteudo, from_=1, to=100, width=6, textvariable=self.profundidade
        ).grid(row=3, column=1, sticky="w")

        linha += 1
        escolha = ttk.LabelFrame(self, text="xs:choice", padding=8)
        escolha.grid(row=linha, column=0, sticky="ew", pady=(10, 0))
        ttk.Radiobutton(
            escolha,
            text="Gerar somente a primeira opcao",
            value="primeira",
            variable=self.modo_choice,
        ).grid(row=0, column=0, sticky="w")
        ttk.Radiobutton(
            escolha,
            text="Primeira opcao + demais como comentario",
            value="comentar",
            variable=self.modo_choice,
        ).grid(row=1, column=0, sticky="w")

        linha += 1
        saida = ttk.LabelFrame(self, text="Saida", padding=8)
        saida.grid(row=linha, column=0, sticky="ew", pady=(10, 0))
        ttk.Checkbutton(
            saida, text="Incluir xsi:schemaLocation", variable=self.schema_location
        ).grid(row=0, column=0, sticky="w")
        ttk.Checkbutton(
            saida,
            text="Incluir a documentacao (xs:annotation) como comentario",
            variable=self.documentacao,
        ).grid(row=1, column=0, sticky="w")

        linha += 1
        presets = ttk.Frame(self)
        presets.grid(row=linha, column=0, sticky="ew", pady=(12, 0))
        ttk.Button(presets, text="XML minimo", command=self.preset_minimo).grid(
            row=0, column=0, padx=(0, 6)
        )
        ttk.Button(presets, text="Esqueleto completo", command=self.preset_completo).grid(
            row=0, column=1
        )

        linha += 1
        self.rotulo_dica = ttk.Label(
            self,
            wraplength=320,
            text=(
                "O XML minimo traz so o que o schema exige. O esqueleto completo "
                "inclui todos os elementos e atributos opcionais, servindo como "
                "referencia da estrutura."
            ),
        )
        self.rotulo_dica.grid(row=linha, column=0, sticky="w", pady=(10, 0))

        self.columnconfigure(0, weight=1)
        self.aplicar_tema(temas.padrao())

    # ------------------------------------------------------------------ API

    def aplicar_tema(self, paleta) -> None:
        """Todo o resto do painel e ttk puro e segue o ttk.Style."""
        self.rotulo_dica.configure(foreground=paleta.texto_suave)

    def opcoes(self) -> generator.OpcoesGeracao:
        return generator.OpcoesGeracao(
            incluir_opcionais=self.incluir_opcionais.get(),
            incluir_atributos_opcionais=self.incluir_atributos.get(),
            repeticoes=max(1, self._inteiro(self.repeticoes, 1)),
            comentar_alternativas_choice=self.modo_choice.get() == "comentar",
            profundidade_max=max(1, self._inteiro(self.profundidade, 15)),
            incluir_schema_location=self.schema_location.get(),
            incluir_documentacao=self.documentacao.get(),
        )

    def preset_minimo(self) -> None:
        self.incluir_opcionais.set(False)
        self.incluir_atributos.set(False)
        self.repeticoes.set(1)
        self.modo_choice.set("primeira")
        self.documentacao.set(False)

    def preset_completo(self) -> None:
        self.incluir_opcionais.set(True)
        self.incluir_atributos.set(True)
        self.repeticoes.set(1)

    @staticmethod
    def _inteiro(variavel, padrao: int) -> int:
        # O Spinbox aceita texto digitado; um valor invalido nao pode derrubar
        # a geracao.
        try:
            return int(variavel.get())
        except (tk.TclError, ValueError):
            return padrao
