"""Gera um XML de exemplo a partir de um elemento declarado no XSD."""
from __future__ import annotations

import os
from dataclasses import dataclass

from lxml import etree
from xmlschema.validators import XsdAnyElement, XsdGroup

import samplevalues

XSI = "http://www.w3.org/2001/XMLSchema-instance"


class LimiteExcedido(Exception):
    """Disparada quando o XML gerado ultrapassa o limite de elementos."""


@dataclass
class OpcoesGeracao:
    incluir_opcionais: bool = True
    incluir_atributos_opcionais: bool = True
    repeticoes: int = 1
    comentar_alternativas_choice: bool = False
    profundidade_max: int = 15
    incluir_schema_location: bool = False
    incluir_documentacao: bool = False
    limite_elementos: int = 50000


def nome_local(nome_expandido: str) -> str:
    if nome_expandido and nome_expandido.startswith("{"):
        return nome_expandido.split("}", 1)[1]
    return nome_expandido or ""


class GeradorXML:
    """Percorre o modelo de conteudo do XSD montando uma arvore lxml."""

    def __init__(self, schema, opcoes: OpcoesGeracao | None = None, caminho_xsd=None):
        self.schema = schema
        self.opcoes = opcoes or OpcoesGeracao()
        self.caminho_xsd = caminho_xsd
        self.valores = samplevalues.GeradorDeValores()
        self.avisos: list = []
        self._elementos = 0
        self._tem_nao_qualificado = False

    # ------------------------------------------------------------------ API

    def gerar(self, xsd_element) -> etree._Element:
        self.avisos = []
        self._elementos = 0
        self._tem_nao_qualificado = False
        self.valores = samplevalues.GeradorDeValores()

        # Monta com prefixo e so troca para namespace padrao no fim, se nenhum
        # elemento sem namespace tiver aparecido: um xmlns padrao no topo
        # arrastaria os elementos locais nao qualificados para dentro do
        # namespace alvo, e o documento seria rejeitado.
        raiz = etree.Element(self._tag(xsd_element), nsmap=self._nsmap())
        self._preencher(raiz, xsd_element, [self._chave(xsd_element)])
        if self._tns() and not self._tem_nao_qualificado:
            raiz = self._com_namespace_padrao(raiz)
        if self.opcoes.incluir_schema_location and self.caminho_xsd:
            self._marcar_schema_location(raiz)
        if self.valores.nao_resolvidos:
            campos = ", ".join(sorted(set(self.valores.nao_resolvidos))[:10])
            self.avisos.append("Sem valor de exemplo confiavel para: " + campos)
        return raiz

    # ---------------------------------------------------------- namespaces

    def _tns(self):
        return self.schema.target_namespace or None

    def _prefixo_tns(self) -> str:
        for prefixo, uri in (self.schema.namespaces or {}).items():
            if uri == self._tns() and prefixo:
                return prefixo
        return "ns"

    def _nsmap(self, padrao: bool = False) -> dict:
        mapa = {}
        tns = self._tns()
        if tns:
            mapa[None if padrao else self._prefixo_tns()] = tns
        if self.opcoes.incluir_schema_location:
            mapa["xsi"] = XSI
        return mapa

    def _com_namespace_padrao(self, raiz):
        """Refaz a raiz declarando o namespace alvo como padrao.

        O nsmap do lxml e fixado na criacao do elemento e vale para toda a
        subarvore, entao a decisao so pode ser tomada depois de saber se algum
        elemento sem namespace foi gerado. Nao da para decidir pelo
        elementFormDefault do schema principal: um elemento local vindo de um
        schema importado segue o elementFormDefault do arquivo onde foi
        declarado, que pode ser outro.
        """
        nova = etree.Element(raiz.tag, nsmap=self._nsmap(padrao=True))
        for chave, valor in raiz.attrib.items():
            nova.set(chave, valor)
        nova.text = raiz.text
        for filho in list(raiz):
            nova.append(filho)  # o lxml move o no, nao copia
        return nova

    def _marcar_schema_location(self, raiz) -> None:
        arquivo = os.path.basename(self.caminho_xsd)
        tns = self._tns()
        if tns:
            raiz.set("{%s}schemaLocation" % XSI, "%s %s" % (tns, arquivo))
        else:
            raiz.set("{%s}noNamespaceSchemaLocation" % XSI, arquivo)

    def _tag(self, xsd_element) -> str:
        # xmlschema ja devolve "{ns}nome" para elementos qualificados e apenas
        # "nome" para os nao qualificados.
        return xsd_element.name

    def _chave(self, xsd_element):
        """Identidade da declaracao, para detectar recursao de verdade.

        Comparar pelo nome derrubaria elementos legitimos: o CTe tem um "toma"
        dentro de "toma3" e varios leiautes de NFSe tem um "nfse" dentro de
        "nfse" -- declaracoes diferentes, tipos diferentes, sem recursao
        nenhuma. So a mesma declaracao reaparecendo no caminho e recursao.
        """
        return id(xsd_element)

    # ------------------------------------------------------------ conteudo

    def _preencher(self, elem, xsd_element, caminho, variacao: int = 0) -> None:
        tipo = xsd_element.type
        if tipo is None:
            return
        nome = nome_local(elem.tag)
        declarado = (xsd_element.default, xsd_element.fixed)

        if tipo.is_simple():
            elem.text = self.valores.valor_para(tipo, nome, declarado, variacao)
            return

        self._atributos(elem, tipo, variacao)

        if tipo.has_simple_content():
            elem.text = self.valores.valor_para(tipo.content, nome, declarado, variacao)
            return
        if tipo.has_mixed_content():
            elem.text = self.valores.texto_padrao

        conteudo = tipo.content
        if isinstance(conteudo, XsdGroup) and len(conteudo):
            self._grupo_repetido(elem, conteudo, caminho, variacao)

    def _atributos(self, elem, tipo, variacao: int = 0) -> None:
        for chave, atributo in (getattr(tipo, "attributes", None) or {}).items():
            if chave is None:  # xs:anyAttribute
                continue
            uso = getattr(atributo, "use", "optional")
            if uso == "prohibited":
                continue
            if uso != "required" and not self.opcoes.incluir_atributos_opcionais:
                continue
            if atributo.type is None:
                continue
            valor = self.valores.valor_para(
                atributo.type,
                atributo.local_name or nome_local(str(chave)),
                (atributo.default, atributo.fixed),
                variacao,
            )
            elem.set(atributo.name, valor)

    # -------------------------------------------------------------- grupos

    def _quantas(self, particula) -> int:
        minimo = particula.min_occurs or 0
        maximo = particula.max_occurs  # None = unbounded
        if minimo == 0 and not self.opcoes.incluir_opcionais:
            return 0
        n = max(self.opcoes.repeticoes, minimo)
        if maximo is not None:
            n = min(n, maximo)
        return max(n, 0)

    def _grupo_repetido(self, pai, grupo, caminho, variacao: int = 0) -> None:
        for indice in range(self._quantas(grupo)):
            self._grupo(pai, grupo, caminho, variacao + indice)

    def _grupo(self, pai, grupo, caminho, variacao: int = 0) -> None:
        particulas = list(grupo)
        if not particulas:
            return
        if grupo.model == "choice":
            self._particula(pai, particulas[0], caminho, variacao)
            if self.opcoes.comentar_alternativas_choice and len(particulas) > 1:
                self._comentar_alternativas(pai, particulas[1:], caminho, variacao)
            return
        for particula in particulas:  # sequence e all
            self._particula(pai, particula, caminho, variacao)

    def _particula(self, pai, particula, caminho, variacao: int = 0) -> None:
        if isinstance(particula, XsdGroup):
            self._grupo_repetido(pai, particula, caminho, variacao)
        elif isinstance(particula, XsdAnyElement):
            self._qualquer(pai, particula)
        else:
            self._elemento(pai, particula, caminho, variacao)

    def _elemento(self, pai, xsd_element, caminho, variacao: int = 0) -> None:
        quantas = self._quantas(xsd_element)
        if not quantas:
            return
        alvo = self._resolver(xsd_element)
        if alvo is None:
            self._comentario(
                pai, " %s: elemento abstrato sem substituto concreto " % nome_local(xsd_element.name)
            )
            return

        chave = self._chave(alvo)
        rotulo = nome_local(alvo.name)
        if chave in caminho:
            self._comentario(pai, " %s: recursao interrompida " % rotulo)
            return
        if len(caminho) >= self.opcoes.profundidade_max:
            self._comentario(pai, " %s: profundidade maxima atingida " % rotulo)
            return

        if self.opcoes.incluir_documentacao:
            doc = self._documentacao(alvo)
            if doc:
                self._comentario(pai, " " + doc + " ")

        for indice in range(quantas):
            self._elementos += 1
            if self._elementos > self.opcoes.limite_elementos:
                raise LimiteExcedido(
                    "O XML passou de %d elementos. Reduza as repeticoes, a "
                    "profundidade maxima ou desmarque os opcionais."
                    % self.opcoes.limite_elementos
                )
            tag = self._tag(alvo)
            if not tag.startswith("{"):
                self._tem_nao_qualificado = True
            filho = etree.SubElement(pai, tag)
            self._preencher(filho, alvo, caminho + [chave], variacao + indice)

    def _qualquer(self, pai, particula) -> None:
        """Trata um xs:any.

        Quando ele e obrigatorio, so um comentario deixaria o XML invalido -- e
        e o caso do infModal do CTe/MDFe. Se o schema nao exige validar o
        conteudo (processContents "skip" ou "lax"), um elemento de marcacao
        resolve; com "strict" so um comentario e possivel, porque qualquer nome
        inventado seria rejeitado.
        """
        quantas = self._quantas(particula)
        if not quantas:
            return
        # A documentacao do proprio xs:any costuma dizer o que vai ali ("Retornar
        # procEventoCTe da versao correspondente..."), entao ela vale mais do que
        # um aviso generico.
        doc = self._documentacao(particula)
        self._comentario(pai, " xs:any: %s " % (doc or "substitua pelo XML apropriado"))
        if (particula.min_occurs or 0) < 1:
            return
        if str(particula.process_contents) not in ("skip", "lax"):
            # Com processContents="strict" o validador exige uma declaracao
            # global de verdade; qualquer nome inventado seria rejeitado.
            return
        namespace = self._namespace_para_any(particula)
        tag = "{%s}elementoQualquer" % namespace if namespace else "elementoQualquer"
        if not namespace:
            self._tem_nao_qualificado = True
        for _ in range(quantas):
            self._elementos += 1
            etree.SubElement(pai, tag)

    def _namespace_para_any(self, particula):
        namespaces = getattr(particula, "namespace", None) or set()
        if "##local" in namespaces:
            return None
        # ##any admite qualquer namespace, inclusive o alvo -- e usar o alvo evita
        # criar um elemento sem namespace so por causa do marcador.
        if "##any" in namespaces or "##targetNamespace" in namespaces:
            return self._tns()
        for uri in sorted(namespaces):
            if not uri.startswith("##"):
                return uri
        if "##other" in namespaces:
            # Precisa ser um namespace diferente do alvo e nao pode ser ausente.
            return "http://exemplo.com.br/outro"
        return None

    def _resolver(self, xsd_element):
        """Troca um elemento abstrato pelo primeiro membro concreto do grupo."""
        if not getattr(xsd_element, "abstract", False):
            return xsd_element
        membros = self.schema.maps.substitution_groups.get(xsd_element.name) or []
        for membro in sorted(membros, key=lambda e: e.name or ""):
            if not getattr(membro, "abstract", False):
                return membro
        return None

    def _documentacao(self, xsd_element) -> str:
        anotacao = getattr(xsd_element, "annotation", None)
        if not anotacao:
            return ""
        texto = " ".join(str(anotacao).split())
        return texto[:200]

    def _comentar_alternativas(self, pai, ramos, caminho, variacao: int = 0) -> None:
        partes = []
        for ramo in ramos:
            temporario = etree.Element("alternativa", nsmap=self._nsmap())
            try:
                self._particula(temporario, ramo, caminho, variacao)
            except LimiteExcedido:
                raise
            except Exception as erro:  # uma alternativa problematica nao pode
                self.avisos.append("Alternativa de xs:choice ignorada: %s" % erro)
                continue
            for filho in temporario:
                partes.append(etree.tostring(filho, pretty_print=True, encoding="unicode"))
        if partes:
            self._comentario(pai, " outras opcoes do xs:choice:\n" + "".join(partes))

    def _comentario(self, pai, texto: str) -> None:
        pai.append(etree.Comment(self._sanear(texto)))

    @staticmethod
    def _sanear(texto: str) -> str:
        limpo = texto.replace("--", "- -")
        return limpo + " " if limpo.endswith("-") else limpo


def serializar(elemento) -> str:
    # A declaracao e escrita a mao porque o lxml a emite com aspas simples.
    corpo = etree.tostring(elemento, pretty_print=True, encoding="unicode")
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + corpo


def gerar_xml(schema, xsd_element, opcoes=None, caminho_xsd=None):
    """Atalho: devolve (texto_xml, avisos)."""
    gerador = GeradorXML(schema, opcoes, caminho_xsd)
    raiz = gerador.gerar(xsd_element)
    return serializar(raiz), gerador.avisos
