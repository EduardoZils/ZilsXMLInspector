"""Valores de exemplo para tipos simples do XSD, respeitando os facets.

A estrategia e montar uma lista de candidatos em ordem de prioridade
(fixed > default > enumeration > pattern > tipo base) e devolver o primeiro que
o proprio XSD considera valido. Assim, quando uma heuristica falha, o valor cai
automaticamente para a proxima alternativa em vez de produzir um XML invalido.
"""
from __future__ import annotations

import base64
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR
from typing import Iterator

import regexsample

XS = "{http://www.w3.org/2001/XMLSchema}"

# Caracteres de controle que o XML 1.0 nao aceita no conteudo. Um pattern pode
# perfeitamente admiti-los (o XSD valida o valor, nao a serializacao), mas o
# documento gerado ficaria impossivel de escrever.
_CONTROLE_PERMITIDO = ("\t", "\n", "\r")


def fora_do_xml(valor: str) -> bool:
    """Diz se o texto tem caracteres que nao cabem em um documento XML 1.0."""
    for caractere in valor:
        if caractere == chr(127):
            return True
        if caractere < " " and caractere not in _CONTROLE_PERMITIDO:
            return True
    return False


# Data/hora fixas para que a saida seja deterministica (util nos testes e ao
# comparar dois XMLs gerados).
DATA = "2026-01-01"
HORA = "12:00:00"

_POR_PRIMITIVO = {
    "date": DATA,
    "dateTime": DATA + "T" + HORA,
    "time": HORA,
    "duration": "P1D",
    "gYear": "2026",
    "gYearMonth": "2026-01",
    "gMonth": "--01",
    "gDay": "---01",
    "gMonthDay": "--01-01",
    "base64Binary": "ZXhlbXBsbw==",
    "hexBinary": "0F0F",
    "anyURI": "http://www.exemplo.com.br/",
    "QName": "exemplo",
    "NOTATION": "exemplo",
    "boolean": "true",
    "float": "1.0",
    "double": "1.0",
}

# Tentados antes do pattern quando o tipo e uma string restrita: cobrem os
# formatos de data/hora usados nos leiautes fiscais brasileiros.
_TEMPORAIS = (
    DATA + "T" + HORA + "-03:00",
    DATA + "T" + HORA,
    DATA,
    HORA,
    "2026-01",
)

_POR_NOME_DERIVADO = {
    "language": "pt-BR",
    "NMTOKENS": "token1 token2",
    "NMTOKEN": "token1",
    "IDREFS": "ID001",
    "ENTITIES": "entidade1",
}


def facet(tipo, nome_local):
    """Le o valor de um facet pelo nome local (maxLength, totalDigits...).

    Sobe a cadeia de derivacao porque o dicionario ``facets`` so traz o que o
    tipo declarou. Um alias como ``<xs:restriction base="TS_nrProcJud"/>``, que
    o eSocial usa aos montes, tem ``facets`` vazio e guarda o length no tipo
    base. O primeiro achado subindo e o mais derivado, que e o que vale.
    """
    alvo = XS + nome_local
    atual = tipo
    vistos = set()
    while atual is not None and id(atual) not in vistos:
        vistos.add(id(atual))
        f = (getattr(atual, "facets", None) or {}).get(alvo)
        if f is not None:
            return getattr(f, "value", f)
        atual = getattr(atual, "base_type", None)
    return None


def cadeia_de_tipos(tipo) -> list:
    """Nomes locais da cadeia de derivacao, do mais derivado ao mais basico."""
    nomes = []
    atual = tipo
    vistos = set()
    while atual is not None and id(atual) not in vistos:
        vistos.add(id(atual))
        local = getattr(atual, "local_name", None)
        if local:
            nomes.append(local)
        atual = getattr(atual, "base_type", None)
    return nomes


def _sanear_ncname(texto: str) -> str:
    limpo = "".join(c if (c.isalnum() or c in "_-.") else "_" for c in texto or "")
    if not limpo or not (limpo[0].isalpha() or limpo[0] == "_"):
        limpo = "n" + limpo
    return limpo


class GeradorDeValores:
    """Produz valores de exemplo, mantendo os IDs unicos dentro do documento."""

    def __init__(self, texto_padrao: str = "texto"):
        self.texto_padrao = texto_padrao
        self._seq_id = 0
        self.primeiro_id = None
        self.nao_resolvidos = []

    # ------------------------------------------------------------------ API

    def valor_para(self, tipo, nome=None, declarado=None, variacao: int = 0) -> str:
        """Valor de exemplo para *tipo*.

        *nome* e o nome do elemento/atributo (deixa o texto mais legivel),
        *declarado* e o par (default, fixed) da declaracao no XSD e *variacao* e
        o indice da repeticao: valores diferentes a cada copia evitam violar as
        restricoes xs:unique e deixam claro o que se repete.
        """
        ultimo = None
        for valor in self._candidatos(tipo, nome, declarado, variacao):
            if valor is None or fora_do_xml(valor):
                continue
            ultimo = valor
            if self._valido(tipo, valor):
                self._registrar_id(tipo, valor)
                return valor

        # Nenhum candidato serviu: o tipo e impossivel de satisfazer. Acontece
        # em schemas publicados com erro -- length=2 junto de um pattern que so
        # aceita um caractere, por exemplo. Fica o ultimo candidato, que vem do
        # tipo base ja moldado pelos facets de tamanho, e nao o primeiro, que
        # poderia ser uma data de 25 caracteres num campo de 2.
        self.nao_resolvidos.append(nome or getattr(tipo, "local_name", "?"))
        return ultimo if ultimo is not None else ""

    # -------------------------------------------------------------- internos

    def _valido(self, tipo, valor: str) -> bool:
        try:
            return bool(tipo.is_valid(valor))
        except Exception:
            return True

    def _registrar_id(self, tipo, valor: str) -> None:
        if self.primeiro_id is None and "ID" in cadeia_de_tipos(tipo):
            self.primeiro_id = valor

    def _candidatos(self, tipo, nome, declarado, variacao: int = 0) -> Iterator:
        default, fixed = declarado if declarado else (None, None)
        if fixed is not None:
            yield str(fixed)
            return
        if default is not None:
            yield str(default)

        # xs:union / xs:list
        membros = getattr(tipo, "member_types", None)
        if membros:
            for membro in membros:
                yield self.valor_para(membro, nome, variacao=variacao)
            return
        item = getattr(tipo, "item_type", None)
        if item is not None and getattr(tipo, "variety", None) == "list":
            unitario = self.valor_para(item, nome, variacao=variacao)
            yield unitario + " " + unitario
            return

        enumeracao = getattr(tipo, "enumeration", None) or []
        if enumeracao:
            # Comeca por um valor diferente a cada repeticao, girando a lista.
            deslocamento = variacao % len(enumeracao)
            ordenada = enumeracao[deslocamento:] + enumeracao[:deslocamento]
            for valor in ordenada:
                yield self._lexico(tipo, valor)

        # Antes do pattern: tipos como xs:ID, xs:NCName e xs:language carregam
        # um pattern herdado do meta-schema que produziria algo valido porem
        # sem sentido ("A-"). O valor idiomatico vem primeiro e, se o usuario
        # tiver restringido o tipo com um pattern proprio, o is_valid derruba
        # este candidato e o pattern assume.
        for valor in self._por_nome_derivado(tipo, nome):
            yield valor

        for valor in self._legiveis_antes_do_pattern(tipo, nome):
            yield valor

        for valor in self._por_pattern(tipo):
            yield valor

        for valor in self._por_tipo_base(tipo, nome, variacao):
            yield valor

    def _lexico(self, tipo, valor) -> str:
        """Converte um valor ja decodificado (enumeration) de volta para texto."""
        if isinstance(valor, str):
            return valor
        if isinstance(valor, bool):
            return "true" if valor else "false"
        try:
            codificado = tipo.encode(valor)
            if isinstance(codificado, str):
                return codificado
        except Exception:
            pass
        return str(valor)

    def _legiveis_antes_do_pattern(self, tipo, nome) -> Iterator:
        """Candidatos mais legiveis do que a sintese a partir do regex.

        Um pattern permissivo como o "[!-ÿ]{1,60}" da NFe aceita qualquer coisa;
        sintetizar do regex daria "000" onde o nome do campo ("xNome") seria bem
        mais util. E quando nem o texto serve, o tipo costuma ser data ou hora
        disfarcada de xs:string -- comum nos leiautes fiscais --, e uma data
        idiomatica evita saidas como "2000-02-29T20:00:00+00:00", que e o que a
        primeira alternativa desses patterns produz.
        """
        if not getattr(tipo, "patterns", None):
            return  # sem pattern, o texto do tipo base ja vem logo adiante
        legivel = self._texto(tipo, nome)
        if self._valido(tipo, legivel):
            yield legivel
            return
        if getattr(tipo, "python_type", None) is not str:
            return
        for valor in _TEMPORAIS:
            yield valor

    def _por_pattern(self, tipo) -> Iterator:
        padroes = getattr(tipo, "patterns", None)
        if not padroes:
            return
        # Quando o tipo tambem exige um comprimento, o pattern precisa ser
        # esticado ate ele: "[0-9]{1,6}" com minLength=6 (TCompet da NF3e)
        # renderia um unico digito se pedissemos so o minimo.
        alvos = [1]
        for chave in ("length", "minLength", "maxLength"):
            valor = facet(tipo, chave)
            if valor is not None:
                alvos.append(min(int(valor), 512))
        vistos = set()
        for alvo in alvos:
            for compilado in getattr(padroes, "patterns", []):
                valor = regexsample.amostra_para(compilado.pattern, alvo)
                if valor and valor not in vistos:
                    vistos.add(valor)
                    yield valor

    def _por_nome_derivado(self, tipo, nome) -> Iterator:
        """Valores idiomaticos para os tipos nomeados derivados de xs:string."""
        cadeia = cadeia_de_tipos(tipo)
        for derivado, valor in _POR_NOME_DERIVADO.items():
            if derivado in cadeia:
                yield valor
                return
        if "ID" in cadeia:
            self._seq_id += 1
            yield "ID%03d" % self._seq_id
        elif "IDREF" in cadeia:
            yield self.primeiro_id or "ID001"
        elif set(cadeia) & {"NCName", "Name", "ENTITY", "QName"}:
            yield _sanear_ncname(nome or "nome1")

    def _por_tipo_base(self, tipo, nome, variacao: int = 0) -> Iterator:
        primitivo = getattr(tipo, "primitive_type", None)
        nome_prim = getattr(primitivo, "local_name", None)
        cadeia = cadeia_de_tipos(tipo)
        py = getattr(tipo, "python_type", None)

        if py is bool or nome_prim == "boolean":
            yield "true"
            return
        if py is int:
            yield self._inteiro(tipo, variacao)
            return
        if py is float:
            yield self._decimal(tipo, casas_padrao=1, variacao=variacao)
            return
        if py is Decimal or nome_prim == "decimal":
            yield self._decimal(
                tipo, casas_padrao=0 if "integer" in cadeia else 2, variacao=variacao
            )
            return

        if nome_prim in ("base64Binary", "hexBinary"):
            yield self._binario(tipo, nome_prim)
            return
        if nome_prim in _POR_PRIMITIVO:
            yield _POR_PRIMITIVO[nome_prim]
            return
        yield self._texto(tipo, nome, variacao)

    # --------------------------------------------------------------- numeros

    def _limites(self, tipo):
        minimo = facet(tipo, "minInclusive")
        maximo = facet(tipo, "maxInclusive")
        if minimo is None:
            minimo = getattr(tipo, "min_value", None)
        if maximo is None:
            maximo = getattr(tipo, "max_value", None)
        minimo = Decimal(str(minimo)) if minimo is not None else None
        maximo = Decimal(str(maximo)) if maximo is not None else None
        min_exc = facet(tipo, "minExclusive")
        max_exc = facet(tipo, "maxExclusive")
        if min_exc is not None:
            candidato = Decimal(str(min_exc))
            if minimo is None or candidato > minimo:
                minimo = candidato
        if max_exc is not None:
            candidato = Decimal(str(max_exc))
            if maximo is None or candidato < maximo:
                maximo = candidato
        return minimo, maximo

    def _inteiro(self, tipo, variacao: int = 0) -> str:
        minimo, maximo = self._limites(tipo)
        valor = Decimal(1 + variacao)
        if minimo is not None and valor < minimo:
            valor = minimo.to_integral_value(rounding=ROUND_CEILING) + variacao
        if maximo is not None and valor > maximo:
            valor = maximo.to_integral_value(rounding=ROUND_FLOOR)
        total = facet(tipo, "totalDigits")
        if total is not None and len(str(abs(int(valor)))) > int(total):
            valor = Decimal("9" * int(total))
        return str(int(valor))

    def _decimal(self, tipo, casas_padrao: int = 2, variacao: int = 0) -> str:
        fracao = facet(tipo, "fractionDigits")
        total = facet(tipo, "totalDigits")
        casas = int(fracao) if fracao is not None else casas_padrao
        if total is not None:
            casas = min(casas, max(int(total) - 1, 0))
        minimo, maximo = self._limites(tipo)
        valor = Decimal(1 + variacao)
        if minimo is not None and valor < minimo:
            valor = minimo + variacao
        if maximo is not None and valor > maximo:
            valor = maximo
        if casas <= 0:
            return str(int(valor))
        return "{0:.{1}f}".format(valor, casas)

    # -------------------------------------------------------------- binarios

    def _binario(self, tipo, nome_prim: str) -> str:
        """Nos tipos binarios os facets de comprimento contam octetos.

        Um length=20 em xs:base64Binary pede 20 bytes -- 28 caracteres depois de
        codificado -- e nao 20 caracteres.
        """
        octetos = facet(tipo, "length")
        if octetos is None:
            octetos = facet(tipo, "minLength")
        if octetos is None:
            octetos = 8
        maximo = facet(tipo, "maxLength")
        if maximo is not None:
            octetos = min(int(octetos), int(maximo))
        octetos = max(0, min(int(octetos), 4096))
        dados = bytes(i % 256 for i in range(octetos))
        if nome_prim == "hexBinary":
            return dados.hex().upper()
        return base64.b64encode(dados).decode("ascii")

    # --------------------------------------------------------------- textos

    def _texto(self, tipo, nome, variacao: int = 0) -> str:
        base = (nome or self.texto_padrao).strip() or self.texto_padrao
        if variacao:
            base = base + str(variacao)
        exato = facet(tipo, "length")
        minimo = facet(tipo, "minLength")
        maximo = facet(tipo, "maxLength")
        if exato is not None:
            minimo = maximo = exato
        texto = base
        if maximo is not None and len(texto) > int(maximo):
            texto = texto[: int(maximo)]
        if minimo is not None and len(texto) < int(minimo):
            alvo = int(minimo)
            recheio = base or "x"
            while len(texto) < alvo:
                texto += recheio
            texto = texto[:alvo]
        return texto
