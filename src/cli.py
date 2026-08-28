"""Uso rapido pela linha de comando (util para testes e automacao)."""
import argparse
import sys

import generator
import validator
import xsdmodel


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Gera um XML de exemplo a partir de um XSD.")
    p.add_argument("xsd")
    p.add_argument("-r", "--raiz", help="nome do elemento raiz")
    p.add_argument("-o", "--saida", help="arquivo de saida (padrao: stdout)")
    p.add_argument("--minimo", action="store_true", help="apenas o obrigatorio")
    p.add_argument("--repeticoes", type=int, default=1)
    p.add_argument("--listar", action="store_true", help="lista os elementos globais")
    args = p.parse_args(argv)

    schema = xsdmodel.carregar(args.xsd)
    raizes = xsdmodel.elementos_globais(schema)
    if args.listar:
        for e in raizes:
            print(xsdmodel.nome_local(e.name))
        return 0
    if not raizes:
        print("O XSD nao declara elementos globais.", file=sys.stderr)
        return 2

    alvo = raizes[0]
    if args.raiz:
        for e in raizes:
            if xsdmodel.nome_local(e.name) == args.raiz:
                alvo = e
                break
        else:
            print("Elemento raiz nao encontrado: " + args.raiz, file=sys.stderr)
            return 2

    opcoes = generator.OpcoesGeracao(
        incluir_opcionais=not args.minimo,
        incluir_atributos_opcionais=not args.minimo,
        repeticoes=args.repeticoes,
    )
    texto, avisos = generator.gerar_xml(schema, alvo, opcoes, args.xsd)
    for aviso in avisos:
        print("aviso: " + aviso, file=sys.stderr)
    erros = validator.validar_texto(args.xsd, texto)
    for erro in erros:
        print("invalido: " + str(erro), file=sys.stderr)
    if args.saida:
        with open(args.saida, "w", encoding="utf-8") as f:
            f.write(texto)
    else:
        sys.stdout.write(texto)
    return 1 if erros else 0


if __name__ == "__main__":
    raise SystemExit(main())
