"""Janela de configuracoes gerais do programa.

Hoje so a aparencia, mas nasce dividida em secoes para caber mais depois.

Nao confundir com PainelOpcoes (ui/options_panel.py), que e a aba "Opcoes de
geracao" e trata do XML gerado, nao do programa.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ui import temas

TITULO = "Opcoes gerais"


class JanelaOpcoesGerais(tk.Toplevel):
    """Aplica a escolha na hora; por isso nao tem OK nem Cancelar."""

    def __init__(self, pai, identificador_atual: str, ao_escolher):
        super().__init__(pai)
        self.ao_escolher = ao_escolher
        self.title(TITULO)
        self.resizable(False, False)
        self.transient(pai)

        self.tema = tk.StringVar(value=identificador_atual)

        corpo = ttk.Frame(self, padding=12)
        corpo.pack(fill="both", expand=True)

        self.grupo = ttk.LabelFrame(corpo, text="Aparencia", padding=10)
        self.grupo.pack(fill="x")

        # Uma coluna por familia, cada uma com suas variantes. So entram as que
        # o Tk realmente carregou: um arquivo de tema corrompido nao pode virar
        # uma opcao que nao funciona.
        disponiveis = temas.disponiveis(pai)
        self.rotulos = []
        for coluna, familia in enumerate(temas.familias()):
            variantes = [t for t in disponiveis if t.familia == familia]
            if not variantes:
                continue
            titulo = ttk.Label(self.grupo, text=familia)
            titulo.grid(row=0, column=coluna, sticky="w", padx=(0, 18), pady=(0, 4))
            self.rotulos.append(titulo)
            for linha, tema in enumerate(variantes, start=1):
                ttk.Radiobutton(
                    self.grupo,
                    text=tema.rotulo,
                    value=tema.identificador,
                    variable=self.tema,
                    command=self._escolher,
                ).grid(row=linha, column=coluna, sticky="w", padx=(0, 18), pady=1)

        rodape = ttk.Frame(corpo, padding=(0, 12, 0, 0))
        rodape.pack(fill="x")
        ttk.Button(rodape, text="Fechar", command=self.destroy).pack(side="right")

        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.bind("<Escape>", lambda _e: self.destroy())

        self.aplicar_tema(getattr(pai, "paleta", None))
        self._centralizar(pai)
        self._tornar_modal()

    # ------------------------------------------------------------------ API

    def aplicar_tema(self, paleta) -> None:
        """O Toplevel e um widget Tk classico: o tema nao pinta o fundo dele."""
        if paleta is None:
            return
        self.configure(background=paleta.fundo)
        for rotulo in self.rotulos:
            rotulo.configure(foreground=paleta.texto_suave)
        temas.aplicar_barra_titulo(self, paleta.escuro)

    # -------------------------------------------------------------- internos

    def _escolher(self) -> None:
        self.ao_escolher(self.tema.get(), self)

    def _centralizar(self, pai) -> None:
        self.update_idletasks()
        largura = self.winfo_reqwidth()
        altura = self.winfo_reqheight()
        try:
            esquerda = pai.winfo_rootx() + (pai.winfo_width() - largura) // 2
            topo = pai.winfo_rooty() + (pai.winfo_height() - altura) // 3
        except tk.TclError:
            return
        self.geometry("+%d+%d" % (max(0, esquerda), max(0, topo)))

    def _tornar_modal(self, tentativas: int = 20) -> None:
        """Segura o foco na janela assim que ela puder receber o grab.

        O grab so pega depois de a janela estar visivel. Esperar por isso com
        wait_visibility trava de vez se a janela nunca aparecer -- e o que
        acontece quando a janela-mae esta oculta. Tentar de novo daqui a pouco
        resolve o caso lento sem correr esse risco.
        """
        try:
            self.grab_set()
        except tk.TclError:
            if tentativas > 0:
                self.after(50, lambda: self._tornar_modal(tentativas - 1))


def abrir(pai, identificador_atual: str, ao_escolher) -> JanelaOpcoesGerais:
    """Abre a janela e so retorna quando ela for fechada."""
    dialogo = JanelaOpcoesGerais(pai, identificador_atual, ao_escolher)
    pai.wait_window(dialogo)
    return dialogo
