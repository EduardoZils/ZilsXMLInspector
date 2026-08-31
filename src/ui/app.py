"""Janela principal do Zils XML Inspector."""
from __future__ import annotations

import os
import queue
import threading
import tkinter as tk
import traceback
from tkinter import filedialog, messagebox, ttk

from lxml import etree

import config
import generator
import validator
import xsdmodel
from ui import settings_dialog, temas
from ui.details_panel import PainelDetalhes
from ui.editor_panel import PainelEditor, PainelErros
from ui.options_panel import PainelOpcoes
from ui.tree_panel import PainelEstrutura

TITULO = "Zils XML Inspector"

TIPOS_XSD = [("Esquema XML", "*.xsd"), ("Todos os arquivos", "*.*")]
TIPOS_XML = [("Documento XML", "*.xml"), ("Todos os arquivos", "*.*")]

# Especies de mensagem da barra de status; cada uma tem uma cor por tema.
ESPECIES_STATUS = ("normal", "erro", "aviso", "ok")

FONTE_MENU = ("Segoe UI", 9)


class Aplicativo(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(TITULO)

        # O tema entra antes de qualquer widget existir: assim todo controle ttk
        # ja nasce pintado e nada chega a ser desenhado com a cor errada.
        self.preferencias = config.carregar()
        self.paleta = temas.por_identificador(self.preferencias.get("tema"))
        temas.aplicar(self, self.paleta)
        self.configure(background=self.paleta.fundo)
        self._status_especie = "normal"
        self._repintura_agendada = False
        # "all" e a ultima etiqueta de binding, entao isto roda depois do que o
        # proprio tema faz ao ser ativado.
        self.bind_all("<<ThemeChanged>>", self._ao_trocar_tema_do_ttk, add="+")

        self.minsize(820, 520)
        self._dimensionar()

        self.schema = None
        self.caminho_xsd = None
        self.caminho_xml = None
        self.modo_tolerante = False
        self._fila = queue.Queue()
        self._ocupado = False

        self._montar_menu()
        self._montar_barra_superior()
        # O rodape vem antes do corpo de proposito: o pack distribui a area na
        # ordem em que os widgets sao empacotados e o corpo tem expand=True, ou
        # seja, engole toda a cavidade que sobrar. Empacotado depois dele, o
        # rodape ficaria sem espaco e os botoes sumiriam da janela.
        self._montar_rodape()
        self._montar_corpo()
        # Segunda passada, agora nos widgets que o ttk.Style nao alcanca: os
        # tk.Text, as etiquetas das arvores, os menus e a barra de titulo.
        self.aplicar_tema()
        self._atualizar_acoes()
        self.status("Abra um arquivo .xsd para comecar.")

    def _dimensionar(self) -> None:
        """Abre maximizada, com um tamanho razoavel ao restaurar a janela."""
        largura = min(1180, max(820, self.winfo_screenwidth() - 120))
        altura = min(740, max(520, self.winfo_screenheight() - 160))
        esquerda = max(0, (self.winfo_screenwidth() - largura) // 2)
        topo = max(0, (self.winfo_screenheight() - altura) // 3)
        self.geometry("%dx%d+%d+%d" % (largura, altura, esquerda, topo))
        self.maximizar()

    def maximizar(self) -> None:
        try:
            self.state("zoomed")  # Windows
        except tk.TclError:
            try:
                self.attributes("-zoomed", True)  # X11
            except tk.TclError:
                pass

    # ------------------------------------------------------------- montagem

    def _montar_menu(self) -> None:
        """Barra de menus propria, montada com widgets Tk classicos.

        A barra nativa (a que se obtem com self.config(menu=...)) e desenhada
        pelo Windows e ignora qualquer cor que o Tk mande: no tema escuro ela
        ficaria como uma faixa branca entre a barra de titulo e o resto da
        janela. Menubutton e Button classicos aceitam cor, entao a barra
        acompanha o tema.
        """
        barra = tk.Frame(self)
        barra.pack(side="top", fill="x")
        self.barra_menu = barra
        self._itens_menu = []
        self._menus = []

        arquivo = self._menu_da_barra("Arquivo")
        arquivo.add_command(label="Abrir XSD...", accelerator="Ctrl+O", command=self.abrir_xsd)
        arquivo.add_command(label="Abrir XML...", command=self.abrir_xml)
        arquivo.add_separator()
        arquivo.add_command(
            label="Salvar XML como...", accelerator="Ctrl+S", command=self.salvar_como
        )
        arquivo.add_separator()
        arquivo.add_command(label="Sair", command=self.destroy)

        ferramentas = self._menu_da_barra("Ferramentas")
        ferramentas.add_command(label="Gerar XML", accelerator="F5", command=self.gerar)
        ferramentas.add_command(label="Validar XML", accelerator="F8", command=self.validar)
        ferramentas.add_command(label="Formatar (indentar)", command=self.formatar)

        # Item clicavel, sem submenu: um clique ja abre a janela.
        self._acao_da_barra("Opcoes", self.abrir_opcoes_gerais)

        ajuda = self._menu_da_barra("Ajuda")
        ajuda.add_command(label="Sobre", command=self.sobre)

        self.bind("<Control-o>", lambda _e: self.abrir_xsd())
        self.bind("<Control-s>", lambda _e: self.salvar_como())
        self.bind("<F5>", lambda _e: self.gerar())
        self.bind("<F8>", lambda _e: self.validar())

    def _aparencia_de_item(self, rotulo: str) -> dict:
        return dict(
            text=rotulo,
            font=FONTE_MENU,
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            padx=8,
            pady=3,
            takefocus=False,
        )

    def _menu_da_barra(self, rotulo: str) -> tk.Menu:
        """Cria um item da barra que abre um menu suspenso.

        O menu e criado como filho do proprio Menubutton: o Tk exige essa
        parentalidade para conseguir posicionar e postar o menu.
        """
        item = tk.Menubutton(
            self.barra_menu, direction="below", **self._aparencia_de_item(rotulo)
        )
        menu = tk.Menu(item, tearoff=False)
        item.configure(menu=menu)
        item.pack(side="left")
        self._itens_menu.append(item)
        self._menus.append(menu)
        return menu

    def _acao_da_barra(self, rotulo: str, comando) -> None:
        """Cria um item da barra que executa um comando, sem menu suspenso."""
        item = tk.Button(
            self.barra_menu,
            command=comando,
            overrelief="flat",
            **self._aparencia_de_item(rotulo),
        )
        item.pack(side="left")
        self._itens_menu.append(item)

    def _montar_barra_superior(self) -> None:
        barra = ttk.Frame(self, padding=(10, 8))
        barra.pack(fill="x")
        self.botao_abrir = ttk.Button(barra, text="Abrir XSD...", command=self.abrir_xsd)
        self.botao_abrir.pack(side="left")

        self.rotulo_xsd = ttk.Label(barra, text="(nenhum schema carregado)")
        self.rotulo_xsd.pack(side="left", padx=10)

        self.combo_raiz = ttk.Combobox(barra, state="disabled", width=32)
        self.combo_raiz.pack(side="right")
        ttk.Label(barra, text="Elemento raiz:").pack(side="right", padx=(0, 6))

    def _montar_corpo(self) -> None:
        painel = ttk.PanedWindow(self, orient="horizontal")
        painel.pack(fill="both", expand=True, padx=10)

        # A esquerda e dividida na vertical: a arvore em cima e os detalhes do
        # item selecionado embaixo, com divisor arrastavel entre os dois.
        esquerda = ttk.PanedWindow(painel, orient="vertical")

        abas_esquerda = ttk.Notebook(esquerda)
        self.painel_estrutura = PainelEstrutura(
            abas_esquerda,
            ao_escolher_raiz=self._escolher_raiz,
            ao_selecionar=self._mostrar_detalhes,
        )
        self.painel_opcoes = PainelOpcoes(abas_esquerda)
        abas_esquerda.add(self.painel_estrutura, text="Estrutura do XSD")
        abas_esquerda.add(self.painel_opcoes, text="Opcoes de geracao")
        esquerda.add(abas_esquerda, weight=3)

        self.painel_detalhes = PainelDetalhes(esquerda)
        esquerda.add(self.painel_detalhes, weight=1)
        painel.add(esquerda, weight=2)

        direita = ttk.Notebook(painel)
        self.painel_editor = PainelEditor(direita)
        self.painel_erros = PainelErros(direita, ao_escolher=self._ir_para_erro)
        direita.add(self.painel_editor, text="XML")
        direita.add(self.painel_erros, text="Validacao")
        painel.add(direita, weight=3)
        self.abas_direita = direita

        # O ttk posiciona o divisor pela largura pedida pelos filhos, e a arvore
        # pede bem mais do que precisa. Fixamos a posicao depois que a janela
        # aparece; o usuario continua livre para arrastar.
        painel.after(80, lambda: self._posicionar_divisor(painel))
        esquerda.after(80, lambda: self._posicionar_divisor(esquerda, 0.60, vertical=True))

    def _mostrar_detalhes(self, no) -> None:
        if no is None:
            self.painel_detalhes.limpar()
        else:
            self.painel_detalhes.mostrar(no)

    def _posicionar_divisor(self, painel, fracao: float = 0.40, vertical: bool = False) -> None:
        try:
            medida = painel.winfo_height() if vertical else painel.winfo_width()
            if medida > 300:
                painel.sashpos(0, int(medida * fracao))
        except tk.TclError:
            pass

    def _montar_rodape(self) -> None:
        rodape = ttk.Frame(self, padding=(10, 8))
        rodape.pack(side="bottom", fill="x")

        self.botao_gerar = ttk.Button(rodape, text="Gerar XML  (F5)", command=self.gerar)
        self.botao_gerar.pack(side="left")
        self.botao_salvar = ttk.Button(rodape, text="Salvar como...", command=self.salvar_como)
        self.botao_salvar.pack(side="left", padx=6)
        self.botao_abrir_xml = ttk.Button(rodape, text="Abrir XML...", command=self.abrir_xml)
        self.botao_abrir_xml.pack(side="left")
        self.botao_validar = ttk.Button(rodape, text="Validar  (F8)", command=self.validar)
        self.botao_validar.pack(side="left", padx=6)

        self.rotulo_status = ttk.Label(rodape, text="", anchor="e")
        self.rotulo_status.pack(side="right", fill="x", expand=True)

    # --------------------------------------------------------------- estado

    def status(self, mensagem: str, especie: str = "normal") -> None:
        """Escreve na barra de status. A cor sai da paleta, pela *especie*.

        Guardar a especie permite recolorir a mensagem que ja esta na tela
        quando o usuario troca de tema.
        """
        self._status_especie = especie if especie in ESPECIES_STATUS else "normal"
        self.rotulo_status.configure(text=mensagem, foreground=self._cor_status())
        self.update_idletasks()

    def _cor_status(self) -> str:
        return getattr(self.paleta, "status_" + self._status_especie)

    # ----------------------------------------------------------------- tema

    def abrir_opcoes_gerais(self) -> None:
        settings_dialog.abrir(self, self.paleta.identificador, self._trocar_tema)

    def _trocar_tema(self, identificador: str, dialogo=None) -> None:
        """Aplica e grava na hora: a janela de Opcoes nao tem OK nem Cancelar."""
        self.aplicar_tema(identificador)
        if dialogo is not None:
            dialogo.aplicar_tema(self.paleta)
        self.preferencias["tema"] = self.paleta.identificador
        if not config.salvar(self.preferencias):
            self.status(
                "Tema aplicado, mas nao foi possivel gravar as preferencias.", "aviso"
            )

    def aplicar_tema(self, identificador=None) -> None:
        if identificador is not None:
            self.paleta = temas.por_identificador(identificador)
        temas.aplicar(self, self.paleta)
        self._pintar_classicos()
        temas.aplicar_barra_titulo(self, self.paleta.escuro)

    def _pintar_classicos(self) -> None:
        """Aplica a paleta no que o tema ttk nao alcanca.

        Separado de aplicar_tema porque precisa rodar mais de uma vez: veja
        _ao_trocar_tema_do_ttk.
        """
        self.configure(background=self.paleta.fundo)
        self.rotulo_xsd.configure(foreground=self.paleta.texto_suave)
        self.rotulo_status.configure(foreground=self._cor_status())
        temas.recolorir_popdown(self.combo_raiz, self.paleta)
        self._recolorir_menu()
        for painel in (
            self.painel_estrutura,
            self.painel_opcoes,
            self.painel_detalhes,
            self.painel_editor,
            self.painel_erros,
        ):
            painel.aplicar_tema(self.paleta)

    def _ao_trocar_tema_do_ttk(self, _evento=None) -> None:
        """Repinta os widgets classicos depois que o tema termina de se aplicar.

        Alguns temas prontos (o Sun Valley e um) chamam tk_setPalette ao serem
        ativados, e isso repinta a forca todo widget Tk classico da janela --
        inclusive o editor de XML e o painel de detalhes, desfazendo o que a
        paleta tinha acabado de definir. O tk_setPalette roda no tratamento de
        <<ThemeChanged>>, que o Tk entrega depois; entao a ultima palavra so e
        nossa se repintarmos aqui.

        O evento chega uma vez por widget da janela: o agendamento junta todas
        essas chamadas numa repintura so.
        """
        if self._repintura_agendada or not hasattr(self, "painel_editor"):
            return
        self._repintura_agendada = True
        self.after_idle(self._repintura_pendente)

    def _repintura_pendente(self) -> None:
        self._repintura_agendada = False
        try:
            self._pintar_classicos()
        except tk.TclError:
            pass  # a janela pode ter sido fechada nesse meio tempo

    def _recolorir_menu(self) -> None:
        """Pinta a barra de menus, seus itens e os menus que descem deles."""
        p = self.paleta
        self.barra_menu.configure(background=p.fundo_menu)
        for item in self._itens_menu:
            item.configure(
                background=p.fundo_menu,
                foreground=p.texto,
                activebackground=p.fundo_menu_ativo,
                activeforeground=p.texto,
            )
        for menu in self._menus:
            menu.configure(
                background=p.fundo_menu,
                foreground=p.texto,
                activebackground=p.selecao_fundo,
                activeforeground=p.selecao_texto,
                disabledforeground=p.texto_desabilitado,
                borderwidth=1,
            )

    def _atualizar_acoes(self) -> None:
        tem_schema = self.schema is not None
        estado_schema = "normal" if tem_schema and not self._ocupado else "disabled"
        self.botao_gerar.configure(state=estado_schema)
        self.botao_validar.configure(state=estado_schema)
        self.botao_abrir_xml.configure(state=estado_schema)
        self.combo_raiz.configure(state="readonly" if tem_schema else "disabled")
        self.botao_salvar.configure(
            state="normal" if self.painel_editor.obter_texto().strip() else "disabled"
        )
        self.botao_abrir.configure(state="disabled" if self._ocupado else "normal")

    # ------------------------------------------------------------- threads

    def _em_segundo_plano(self, tarefa, ao_concluir, mensagem: str, ao_falhar=None) -> None:
        """Executa *tarefa* fora da thread da interface.

        Carregar um XSD com dezenas de includes leva segundos; sem isso a janela
        congelaria e o Windows a marcaria como "nao respondendo".
        """
        self._ocupado = True
        self._atualizar_acoes()
        self.status(mensagem)
        self.configure(cursor="watch")

        def executar():
            try:
                self._fila.put((True, tarefa()))
            except Exception as erro:  # o traceback vai para o dialogo de erro
                self._fila.put((False, (erro, traceback.format_exc())))

        threading.Thread(target=executar, daemon=True).start()
        self.after(50, lambda: self._verificar_fila(ao_concluir, ao_falhar))

    def _verificar_fila(self, ao_concluir, ao_falhar=None) -> None:
        try:
            ok, resultado = self._fila.get_nowait()
        except queue.Empty:
            self.after(50, lambda: self._verificar_fila(ao_concluir, ao_falhar))
            return

        self._ocupado = False
        self.configure(cursor="")
        self._atualizar_acoes()
        if ok:
            ao_concluir(resultado)
            return

        erro, detalhe = resultado
        self.status("Falhou: %s" % erro, "erro")
        # Quem sabe tratar a falha tem a chance de propor uma alternativa antes
        # de o usuario ver um dialogo de erro.
        if ao_falhar is not None and ao_falhar(erro):
            return
        messagebox.showerror(TITULO, str(erro)[:600], detail=detalhe[-1500:], parent=self)

    # ---------------------------------------------------------------- acoes

    def abrir_xsd(self) -> None:
        if self._ocupado:
            return
        caminho = filedialog.askopenfilename(
            title="Selecione o arquivo .xsd", filetypes=TIPOS_XSD, parent=self
        )
        if not caminho:
            return
        self.abrir_arquivo_xsd(caminho)

    def abrir_arquivo_xsd(self, caminho: str) -> None:
        """Carrega um XSD ja escolhido (usado tambem pelo argumento da linha de comando)."""
        if not os.path.isfile(caminho):
            messagebox.showerror(TITULO, "Arquivo nao encontrado: %s" % caminho, parent=self)
            return
        self._carregar_xsd(os.path.abspath(caminho), tolerante=False)

    def _carregar_xsd(self, caminho: str, tolerante: bool) -> None:
        self._em_segundo_plano(
            lambda: xsdmodel.carregar(caminho, tolerante),
            lambda schema: self._schema_carregado(caminho, schema, tolerante),
            "Carregando %s..." % os.path.basename(caminho),
            ao_falhar=lambda erro: self._falha_ao_carregar(caminho, tolerante, erro),
        )

    def _falha_ao_carregar(self, caminho: str, tolerante: bool, erro) -> bool:
        """Oferece o modo tolerante quando o XSD tem defeitos de publicacao."""
        if tolerante:
            return False
        aceitou = messagebox.askyesno(
            TITULO,
            "O schema tem inconsistencias e nao pode ser carregado no modo normal.",
            detail=(
                "%s\n\nAbrir mesmo assim, ignorando as inconsistencias?\n"
                "A geracao do XML funciona, mas a validacao ficara indisponivel."
                % str(erro)[:600]
            ),
            parent=self,
        )
        if not aceitou:
            return False
        self._carregar_xsd(caminho, tolerante=True)
        return True

    def _schema_carregado(self, caminho: str, schema, tolerante: bool = False) -> None:
        self.schema = schema
        self.modo_tolerante = tolerante
        self.caminho_xsd = caminho
        self.rotulo_xsd.configure(text=caminho)
        self.title("%s - %s" % (TITULO, os.path.basename(caminho)))

        raizes = [xsdmodel.nome_local(e.name) for e in xsdmodel.elementos_globais(schema)]
        self.combo_raiz.configure(values=raizes)
        if raizes:
            self.combo_raiz.current(0)
        self.painel_estrutura.carregar(schema)
        self.painel_detalhes.limpar()
        self._atualizar_acoes()

        if not raizes:
            self.status(
                "O schema nao declara elementos globais, entao nao ha raiz para gerar.",
                "erro",
            )
        elif tolerante:
            self.status(
                "Schema carregado em modo tolerante: %d raiz(es). A validacao esta "
                "indisponivel para este arquivo." % len(raizes),
                "aviso",
            )
        else:
            self.status(
                "Schema carregado: %d elemento(s) global(is). Escolha a raiz e gere o XML."
                % len(raizes)
            )

    def _escolher_raiz(self, nome: str) -> None:
        if nome in self.combo_raiz.cget("values"):
            self.combo_raiz.set(nome)
            self.status("Elemento raiz: %s" % nome)

    def _raiz_selecionada(self):
        nome = self.combo_raiz.get()
        for elemento in xsdmodel.elementos_globais(self.schema):
            if xsdmodel.nome_local(elemento.name) == nome:
                return elemento
        return None

    def gerar(self) -> None:
        if self.schema is None or self._ocupado:
            return
        raiz = self._raiz_selecionada()
        if raiz is None:
            messagebox.showwarning(TITULO, "Escolha o elemento raiz.", parent=self)
            return
        if getattr(raiz, "abstract", False):
            messagebox.showwarning(
                TITULO,
                "O elemento %s e abstrato e nao pode ser a raiz do documento."
                % self.combo_raiz.get(),
                parent=self,
            )
            return

        opcoes = self.painel_opcoes.opcoes()
        caminho = self.caminho_xsd

        def tarefa():
            return generator.gerar_xml(self.schema, raiz, opcoes, caminho)

        self._em_segundo_plano(tarefa, self._xml_gerado, "Gerando XML...")

    def _xml_gerado(self, resultado) -> None:
        texto, avisos = resultado
        self.caminho_xml = None
        self.painel_editor.definir_texto(texto)
        self.abas_direita.select(0)
        self._atualizar_acoes()
        self._validar_conteudo(prefixo="XML gerado", avisos=avisos)

    def abrir_xml(self) -> None:
        caminho = filedialog.askopenfilename(
            title="Selecione o arquivo .xml", filetypes=TIPOS_XML, parent=self
        )
        if not caminho:
            return
        try:
            with open(caminho, "rb") as arquivo:
                bruto = arquivo.read()
            texto = bruto.decode("utf-8", errors="replace")
        except OSError as erro:
            messagebox.showerror(TITULO, str(erro), parent=self)
            return
        self.caminho_xml = caminho
        self.painel_editor.definir_texto(texto)
        self.abas_direita.select(0)
        self._atualizar_acoes()
        self.status("Aberto: %s" % caminho)
        if self.schema is not None:
            self._validar_conteudo(prefixo="XML aberto")

    def validar(self) -> None:
        if self.schema is None:
            messagebox.showinfo(
                TITULO, "Carregue um XSD antes de validar.", parent=self
            )
            return
        if self.modo_tolerante:
            messagebox.showinfo(
                TITULO,
                "Validacao indisponivel para este schema.",
                detail=("O arquivo foi aberto em modo tolerante porque tem "
                        "inconsistencias, e o validador nao consegue compila-lo."),
                parent=self,
            )
            return
        self._validar_conteudo(prefixo="XML")

    def _validar_conteudo(self, prefixo: str = "XML", avisos=None) -> None:
        if self.modo_tolerante:
            self.painel_erros.limpar()
            recado = "  |  " + "; ".join(avisos) if avisos else ""
            self.status(
                "%s: validacao indisponivel em modo tolerante.%s" % (prefixo, recado),
                "aviso",
            )
            return
        texto = self.painel_editor.obter_texto()
        if not texto.strip():
            self.painel_erros.limpar()
            self.status("Nada para validar.")
            return
        try:
            erros = validator.validar_texto(self.caminho_xsd, texto)
        except validator.ErroDeSchema as erro:
            self.status("Nao foi possivel compilar o XSD: %s" % erro, "erro")
            messagebox.showerror(TITULO, "Nao foi possivel compilar o XSD.",
                                 detail=str(erro), parent=self)
            return

        self.painel_erros.mostrar(erros)
        sufixo = ""
        if avisos:
            sufixo = "  |  " + "; ".join(avisos)
        if erros:
            self.abas_direita.select(1)
            self.status(
                "%s invalido: %d erro(s) - veja a aba Validacao.%s"
                % (prefixo, len(erros), sufixo),
                "erro",
            )
        else:
            self.status("%s valido contra o schema.%s" % (prefixo, sufixo), "ok")

    def _ir_para_erro(self, erro) -> None:
        self.abas_direita.select(0)
        self.painel_editor.ir_para_linha(erro.linha)

    def formatar(self) -> None:
        texto = self.painel_editor.obter_texto()
        if not texto.strip():
            return
        try:
            analisador = etree.XMLParser(remove_blank_text=True)
            arvore = etree.fromstring(texto.encode("utf-8"), analisador)
        except etree.XMLSyntaxError as erro:
            self.status("XML mal formado: %s" % erro.msg, "erro")
            return
        self.painel_editor.definir_texto(generator.serializar(arvore))
        self.status("XML reindentado.")

    def salvar_como(self) -> None:
        texto = self.painel_editor.obter_texto()
        if not texto.strip():
            return
        sugestao = "exemplo.xml"
        if self.caminho_xml:
            sugestao = os.path.basename(self.caminho_xml)
        elif self.caminho_xsd:
            sugestao = os.path.splitext(os.path.basename(self.caminho_xsd))[0] + ".xml"

        caminho = filedialog.asksaveasfilename(
            title="Salvar XML",
            defaultextension=".xml",
            initialfile=sugestao,
            filetypes=TIPOS_XML,
            parent=self,
        )
        if not caminho:
            return
        try:
            with open(caminho, "w", encoding="utf-8", newline="\n") as arquivo:
                arquivo.write(texto)
        except OSError as erro:
            messagebox.showerror(TITULO, str(erro), parent=self)
            return
        self.caminho_xml = caminho
        self.status("Salvo em %s" % caminho, "ok")

    def sobre(self) -> None:
        messagebox.showinfo(
            TITULO,
            "Zils XML Inspector",
            detail=(
                "Gera XML de exemplo a partir de um XSD e valida documentos "
                "contra o schema.\n\n"
                "Feito com Python, tkinter, xmlschema e lxml."
            ),
            parent=self,
        )


def executar(caminho_xsd=None) -> None:
    aplicativo = Aplicativo()
    try:
        aplicativo.call("tk", "scaling", 1.25)
    except tk.TclError:
        pass
    if caminho_xsd:
        # Depois de a janela aparecer, para o usuario ver o "Carregando...".
        aplicativo.after(100, lambda: aplicativo.abrir_arquivo_xsd(caminho_xsd))
    aplicativo.mainloop()
