"""Carrega o XSD e expoe sua estrutura em nos simples para a arvore da interface.

A arvore e montada sob demanda: cada no sabe se tem filhos, mas so os calcula
quando e expandido. Sem isso, um schema recursivo (ou simplesmente grande, como
os leiautes fiscais) faria a interface travar na abertura.
"""
from __future__ import annotations

import warnings
from dataclasses import dataclass, field

import xmlschema
from xmlschema.validators import XsdAnyElement, XsdAtomicRestriction, XsdGroup


XS = "{http://www.w3.org/2001/XMLSchema}"


class ErroDeCarga(Exception):
    """O XSD nao pode ser carregado."""


def carregar(caminho: str, tolerante: bool = False) -> xmlschema.XMLSchema:
    """Carrega o XSD.

    No modo tolerante as inconsistencias do schema viram avisos em vez de erro.
    Serve para arquivos publicados com defeito (tipo global declarado duas
    vezes, include faltando): da para gerar o exemplo, mas a validacao fica
    indisponivel, porque o libxml2 tambem se recusa a compila-los.
    """
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            if tolerante:
                return xmlschema.XMLSchema(caminho, validation="lax")
            return xmlschema.XMLSchema(caminho)
    except Exception as erro:  # XMLSchemaParseError, OSError, ParseError...
        raise ErroDeCarga(str(erro)) from erro


def nome_local(nome: str) -> str:
    if nome and nome.startswith("{"):
        return nome.split("}", 1)[1]
    return nome or ""


def elementos_globais(schema) -> list:
    """Elementos declarados no nivel do schema, candidatos a raiz do XML."""
    itens = [e for e in schema.elements.values()]
    itens.sort(key=lambda e: nome_local(e.name).lower())
    return itens


def cardinalidade(minimo, maximo) -> str:
    fim = "*" if maximo is None else str(maximo)
    return "%s..%s" % (minimo if minimo is not None else 0, fim)


def _nome_do_tipo(tipo) -> str:
    if tipo is None:
        return ""
    if getattr(tipo, "name", None):
        return nome_local(tipo.name)
    base = getattr(tipo, "base_type", None)
    if base is not None and getattr(base, "name", None):
        return "(anonimo: %s)" % nome_local(base.name)
    return "(anonimo)"


def documentacao(objeto) -> str:
    anotacao = getattr(objeto, "annotation", None)
    if not anotacao:
        return ""
    return " ".join(str(anotacao).split())


def _facet_objeto(tipo, nome_local_facet):
    """Objeto do facet, subindo a cadeia de derivacao.

    Aliases (``<xs:restriction base="X"/>``) tem o dicionario de facets vazio e
    guardam tudo no tipo base.
    """
    alvo = XS + nome_local_facet
    atual = tipo
    vistos = set()
    while atual is not None and id(atual) not in vistos:
        vistos.add(id(atual))
        objeto = (getattr(atual, "facets", None) or {}).get(alvo)
        if objeto is not None:
            return objeto
        atual = getattr(atual, "base_type", None)
    return None


def _documentacao_do_elemento(elemento) -> str:
    """Junta os xs:documentation de dentro de um elemento cru do XSD."""
    partes = []
    for doc in elemento.iter(XS + "documentation"):
        if doc.text:
            partes.append(" ".join(doc.text.split()))
    return " ".join(partes)


def padroes_do_tipo(tipo) -> list:
    """Os patterns como escritos no XSD, nao a traducao para regex do Python."""
    facet = _facet_objeto(tipo, "pattern")
    if facet is None:
        return []
    crus = []
    try:
        for elemento in facet:
            valor = elemento.get("value")
            if valor:
                crus.append(valor)
    except TypeError:
        pass
    if crus:
        return crus
    elemento = getattr(facet, "elem", None)
    return [elemento.get("value")] if elemento is not None and elemento.get("value") else []


def valores_do_tipo(tipo) -> list:
    """Pares (valor, documentacao) de cada xs:enumeration.

    A documentacao individual e o que transforma uma lista de codigos em algo
    util: "11" sozinho nao diz nada, "11 - Rondonia" diz.
    """
    enumeracao = getattr(tipo, "enumeration", None) or []
    if not enumeracao:
        return []
    docs = {}
    facet = _facet_objeto(tipo, "enumeration")
    if facet is not None:
        try:
            for elemento in facet:
                valor = elemento.get("value")
                if valor is not None:
                    docs[valor] = _documentacao_do_elemento(elemento)
        except TypeError:
            pass
    resultado = []
    for valor in enumeracao:
        texto = valor if isinstance(valor, str) else str(valor)
        resultado.append((texto, docs.get(texto, "")))
    return resultado


# Facets numericos e de tamanho, na ordem em que fazem sentido para ler.
_FACETS_LEGIVEIS = (
    ("length", "Tamanho exato"),
    ("minLength", "Tamanho minimo"),
    ("maxLength", "Tamanho maximo"),
    ("totalDigits", "Digitos no total"),
    ("fractionDigits", "Casas decimais"),
    ("minInclusive", "Valor minimo"),
    ("minExclusive", "Maior que"),
    ("maxInclusive", "Valor maximo"),
    ("maxExclusive", "Menor que"),
    ("whiteSpace", "Espacos em branco"),
)


def restricoes_do_tipo(tipo) -> list:
    """Pares (rotulo, valor) dos facets do tipo, prontos para exibir."""
    if tipo is None:
        return []
    resultado = []
    for pattern in padroes_do_tipo(tipo):
        resultado.append(("Pattern", pattern))
    for chave, rotulo in _FACETS_LEGIVEIS:
        objeto = _facet_objeto(tipo, chave)
        if objeto is None:
            continue
        valor = str(getattr(objeto, "value", objeto))
        if chave == "whiteSpace" and _whitespace_padrao(tipo, valor):
            continue
        resultado.append((rotulo, valor))
    return resultado


def _whitespace_padrao(tipo, valor: str) -> bool:
    """O whiteSpace herdado do primitivo nao informa nada e polui a tela.

    Todo tipo tem esse facet: "preserve" em qualquer xs:string e "collapse" em
    todos os demais. Vale mostrar so quando o schema realmente aperta a regra.
    """
    primitivo = getattr(getattr(tipo, "primitive_type", None), "local_name", None)
    if primitivo == "string":
        return valor == "preserve"
    return valor == "collapse"


def resumo_de_facets(tipo) -> str:
    """Descreve as restricoes de um tipo simples em uma linha (coluna da arvore)."""
    if tipo is None or not isinstance(tipo, XsdAtomicRestriction):
        return ""
    partes = []
    valores = valores_do_tipo(tipo)
    if valores:
        amostra = ", ".join(v for v, _doc in valores[:6])
        if len(valores) > 6:
            amostra += ", ... (%d valores)" % len(valores)
        partes.append("valores: " + amostra)
    padroes = padroes_do_tipo(tipo)
    if padroes:
        partes.append("pattern: " + " | ".join(padroes)[:120])
    for rotulo, chave in (
        ("min", "minLength"),
        ("max", "maxLength"),
        ("tam", "length"),
        ("digitos", "totalDigits"),
        ("decimais", "fractionDigits"),
    ):
        objeto = _facet_objeto(tipo, chave)
        if objeto is not None:
            partes.append("%s=%s" % (rotulo, getattr(objeto, "value", objeto)))
    return "; ".join(partes)


@dataclass
class Detalhe:
    """Tudo o que se sabe sobre o item selecionado, pronto para exibir."""

    titulo: str = ""
    especie: str = ""
    cabecalho: list = field(default_factory=list)  # [(rotulo, valor)]
    documentacao: str = ""
    restricoes: list = field(default_factory=list)  # [(rotulo, valor)]
    valores: list = field(default_factory=list)  # [(valor, documentacao)]
    exemplo: str = ""


def _descricao_do_tipo(tipo) -> str:
    if tipo is None:
        return ""
    nome = _nome_do_tipo(tipo)
    base = getattr(tipo, "base_type", None)
    if base is not None and getattr(base, "name", None) and getattr(tipo, "name", None):
        return "%s (restricao de %s)" % (nome, nome_local(base.name))
    if getattr(tipo, "member_types", None):
        membros = ", ".join(_nome_do_tipo(m) for m in tipo.member_types)
        return "%s (uniao de %s)" % (nome, membros)
    item = getattr(tipo, "item_type", None)
    if item is not None and getattr(tipo, "variety", None) == "list":
        return "%s (lista de %s)" % (nome, _nome_do_tipo(item))
    return nome


def _exemplo(tipo, nome: str, declarado=None) -> str:
    """O valor que o gerador colocaria neste campo.

    Precisa receber o par (default, fixed) da declaracao: um campo com valor
    fixo so aceita aquele valor, e mostrar outro seria mentir sobre a saida.
    """
    if tipo is None or not tipo.is_simple():
        return ""
    try:
        import samplevalues

        return samplevalues.GeradorDeValores().valor_para(tipo, nome, declarado)
    except Exception:
        return ""


def detalhes_do_no(no) -> Detalhe:
    """Descreve o item selecionado na arvore."""
    if no is None:
        return Detalhe()
    objeto = no.objeto

    if no.especie == "grupo":
        return Detalhe(
            titulo="<%s>" % no.rotulo,
            especie="grupo",
            cabecalho=[
                ("Modelo", no.rotulo),
                ("Cardinalidade", no.cardinalidade),
                ("Particulas", str(len(objeto)) if objeto is not None else "0"),
            ],
            documentacao=(
                "Escolha uma das opcoes abaixo." if no.rotulo == "choice"
                else "Os itens abaixo aparecem nesta ordem." if no.rotulo == "sequence"
                else ""
            ),
        )

    if no.especie == "any":
        namespaces = ", ".join(sorted(getattr(objeto, "namespace", None) or [])) or "##any"
        return Detalhe(
            titulo="xs:any",
            especie="any",
            cabecalho=[
                ("Namespace", namespaces),
                ("Validacao", str(getattr(objeto, "process_contents", ""))),
                ("Cardinalidade", no.cardinalidade),
            ],
            documentacao=documentacao(objeto),
        )

    tipo = getattr(objeto, "type", None)
    declarado = (getattr(objeto, "default", None), getattr(objeto, "fixed", None))
    cabecalho = [("Tipo", _descricao_do_tipo(tipo))]
    if no.especie == "atributo":
        cabecalho.append(("Uso", getattr(objeto, "use", "optional")))
    else:
        cabecalho.append(("Cardinalidade", no.cardinalidade))
        if getattr(objeto, "abstract", False):
            cabecalho.append(("Abstrato", "sim (exige um substituto)"))
        if getattr(objeto, "nillable", False):
            cabecalho.append(("Nillable", "sim (aceita xsi:nil)"))
    if getattr(objeto, "default", None) is not None:
        cabecalho.append(("Default", str(objeto.default)))
    if getattr(objeto, "fixed", None) is not None:
        cabecalho.append(("Fixo", str(objeto.fixed)))
    if getattr(objeto, "name", "") and str(objeto.name).startswith("{"):
        cabecalho.append(("Namespace", objeto.name.split("}", 1)[0][1:]))

    return Detalhe(
        titulo=no.rotulo,
        especie=no.especie,
        cabecalho=cabecalho,
        documentacao=documentacao(objeto) or documentacao(tipo),
        restricoes=restricoes_do_tipo(tipo),
        valores=valores_do_tipo(tipo),
        exemplo=_exemplo(tipo, no.rotulo.lstrip("@"), declarado),
    )


@dataclass
class No:
    rotulo: str
    cardinalidade: str = ""
    tipo: str = ""
    detalhe: str = ""
    especie: str = "elemento"  # elemento | atributo | grupo | any
    objeto: object = None
    tem_filhos: bool = False


def no_de_elemento(xsd_element, minimo=None, maximo=None) -> No:
    tipo = xsd_element.type
    detalhe = documentacao(xsd_element) or resumo_de_facets(tipo)
    return No(
        rotulo=nome_local(xsd_element.name),
        cardinalidade=cardinalidade(
            xsd_element.min_occurs if minimo is None else minimo,
            xsd_element.max_occurs if maximo is None else maximo,
        ),
        tipo=_nome_do_tipo(tipo),
        detalhe=detalhe,
        especie="elemento",
        objeto=xsd_element,
        tem_filhos=_tem_filhos(xsd_element),
    )


def _tem_filhos(xsd_element) -> bool:
    tipo = getattr(xsd_element, "type", None)
    if tipo is None or tipo.is_simple():
        return False
    if getattr(tipo, "attributes", None):
        return True
    conteudo = getattr(tipo, "content", None)
    return isinstance(conteudo, XsdGroup) and len(conteudo) > 0


def filhos(no: No) -> list:
    """Filhos de um no, calculados no momento da expansao."""
    if no.especie == "elemento":
        return _filhos_de_elemento(no.objeto)
    if no.especie == "grupo":
        return _particulas(no.objeto)
    return []


def _filhos_de_elemento(xsd_element) -> list:
    tipo = getattr(xsd_element, "type", None)
    if tipo is None or tipo.is_simple():
        return []
    resultado = []
    for chave, atributo in (getattr(tipo, "attributes", None) or {}).items():
        if chave is None:
            continue
        resultado.append(
            No(
                rotulo="@" + (atributo.local_name or nome_local(str(chave))),
                cardinalidade="1..1" if atributo.use == "required" else "0..1",
                tipo=_nome_do_tipo(atributo.type),
                detalhe=documentacao(atributo) or resumo_de_facets(atributo.type),
                especie="atributo",
                objeto=atributo,
            )
        )
    conteudo = getattr(tipo, "content", None)
    if isinstance(conteudo, XsdGroup):
        resultado.extend(_particulas(conteudo))
    return resultado


def _particulas(grupo) -> list:
    resultado = []
    for particula in grupo:
        if isinstance(particula, XsdGroup):
            resultado.append(
                No(
                    rotulo=particula.model or "grupo",
                    cardinalidade=cardinalidade(particula.min_occurs, particula.max_occurs),
                    tipo="",
                    detalhe="",
                    especie="grupo",
                    objeto=particula,
                    tem_filhos=len(particula) > 0,
                )
            )
        elif isinstance(particula, XsdAnyElement):
            resultado.append(
                No(
                    rotulo="xs:any",
                    cardinalidade=cardinalidade(particula.min_occurs, particula.max_occurs),
                    tipo=str(particula.process_contents),
                    especie="any",
                    objeto=particula,
                )
            )
        else:
            resultado.append(no_de_elemento(particula))
    return resultado
