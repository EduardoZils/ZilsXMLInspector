r"""Gera uma string de exemplo que casa com uma expressao regular.

Usado para satisfazer o facet ``xs:pattern``. A biblioteca ``xmlschema`` ja
entrega os patterns do XSD traduzidos para o dialeto de regex do Python
(inclusive ``\p{L}``, ``\i``, ``\c`` e subtracao de classes), entao aqui basta
percorrer a arvore sintatica produzida pelo parser da stdlib e emitir a menor
string que a satisfaca.
"""
from __future__ import annotations

try:  # Python 3.11+
    from re import _parser as _parser
except ImportError:  # pragma: no cover - Python <= 3.10
    import sre_parse as _parser  # type: ignore

MAXREPEAT = getattr(_parser, "MAXREPEAT", 4294967295)

# Ordem de preferencia ao escolher um caractere dentro de uma classe: digitos e
# letras produzem exemplos legiveis e seguros dentro de um XML.
_PREFERIDOS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"

_CATEGORIAS = {
    "CATEGORY_DIGIT": "0",
    "CATEGORY_NOT_DIGIT": "A",
    "CATEGORY_WORD": "A",
    "CATEGORY_NOT_WORD": "-",
    "CATEGORY_SPACE": " ",
    "CATEGORY_NOT_SPACE": "A",
    "CATEGORY_LINEBREAK": "\n",
    "CATEGORY_NOT_LINEBREAK": "A",
}

# Limite de expansao para evitar que um {1,10000} gere megabytes de texto.
_MAX_REPETICOES = 512


def _nome(op) -> str:
    return getattr(op, "name", str(op))


def _char_no_intervalo(lo: int, hi: int) -> str:
    for c in _PREFERIDOS:
        if lo <= ord(c) <= hi:
            return c
    for o in range(lo, min(hi, lo + 512) + 1):
        c = chr(o)
        if c.isprintable() and c not in "<>&\"'":
            return c
    return chr(lo)


def _expandir_excluidos(itens) -> set[str]:
    excluidos: set[str] = set()
    for op, av in itens:
        nome = _nome(op)
        if nome == "LITERAL":
            excluidos.add(chr(av))
        elif nome == "RANGE":
            lo, hi = av
            for o in range(lo, min(hi, lo + 512) + 1):
                excluidos.add(chr(o))
        elif nome == "CATEGORY":
            cat = _nome(av)
            if cat == "CATEGORY_DIGIT":
                excluidos.update("0123456789")
            elif cat == "CATEGORY_WORD":
                excluidos.update(_PREFERIDOS + "_")
            elif cat == "CATEGORY_SPACE":
                excluidos.update(" \t\n\r\f\v")
    return excluidos


def _char_de_classe(itens) -> str:
    negado = bool(itens) and _nome(itens[0][0]) == "NEGATE"
    if negado:
        excluidos = _expandir_excluidos(itens[1:])
        for c in _PREFERIDOS:
            if c not in excluidos:
                return c
        return "?"
    for op, av in itens:
        nome = _nome(op)
        if nome == "LITERAL":
            return chr(av)
        if nome == "RANGE":
            return _char_no_intervalo(*av)
        if nome == "CATEGORY":
            return _CATEGORIAS.get(_nome(av), "A")
        if nome == "IN":  # classe aninhada (resultado de subtracao de classes)
            return _char_de_classe(av)
    return "A"


def _emitir(sequencia, grupos: dict, profundidade: int = 0, alvo: int = 1) -> str:
    if profundidade > 40:
        return ""
    partes: list[str] = []
    for op, av in sequencia:
        nome = _nome(op)
        if nome == "LITERAL":
            partes.append(chr(av))
        elif nome == "NOT_LITERAL":
            partes.append("A" if chr(av) != "A" else "B")
        elif nome == "ANY":
            partes.append("A")
        elif nome == "IN":
            partes.append(_char_de_classe(av))
        elif nome == "RANGE":
            partes.append(_char_no_intervalo(*av))
        elif nome in ("MAX_REPEAT", "MIN_REPEAT", "POSSESSIVE_REPEAT"):
            minimo, maximo, sub = av
            # 'alvo' so afeta as repeticoes de tamanho variavel; as fixas ({4})
            # continuam intactas porque minimo == maximo.
            n = max(minimo, min(alvo, maximo) if maximo != MAXREPEAT else alvo)
            if maximo != MAXREPEAT:
                n = min(n, maximo)
            n = min(max(n, 0), _MAX_REPETICOES)
            partes.append(_emitir(sub, grupos, profundidade + 1, alvo) * n)
        elif nome in ("SUBPATTERN", "ATOMIC_GROUP"):
            sub = av[-1] if isinstance(av, tuple) else av
            valor = _emitir(sub, grupos, profundidade + 1, alvo)
            if isinstance(av, tuple) and isinstance(av[0], int):
                grupos[av[0]] = valor
            partes.append(valor)
        elif nome == "BRANCH":
            # Prefere a primeira alternativa que produza texto: padroes como
            # "[0-9]{0}|[A-Z0-9]{12}[0-9]{2}" (CNPJ da NFCom) comecam por uma
            # alternativa vazia, e uma amostra vazia nao serve de exemplo.
            escolhido = ""
            for ramo in av[1] or []:
                escolhido = _emitir(ramo, grupos, profundidade + 1, alvo)
                if escolhido:
                    break
            partes.append(escolhido)
        elif nome == "GROUPREF":
            partes.append(grupos.get(av, ""))
        elif nome == "GROUPREF_EXISTS":
            partes.append(_emitir(av[1], grupos, profundidade + 1, alvo))
        # AT (^ $ \b), ASSERT, ASSERT_NOT e NEGATE nao produzem texto.
    return "".join(partes)


def amostra_para(pattern: str, alvo: int = 1) -> str | None:
    """Devolve uma string que casa com ``pattern`` ou ``None`` se nao souber.

    ``alvo`` e o numero de repeticoes desejado onde a quantidade e livre, o que
    permite atender facets de comprimento: ``[0-9]{1,6}`` com ``minLength=6``
    precisa de seis digitos, nao de um.
    """
    try:
        arvore = _parser.parse(pattern)
        return _emitir(arvore, {}, alvo=max(1, alvo))
    except Exception:
        return None
