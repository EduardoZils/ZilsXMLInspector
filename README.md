# Zils XML Inspector

Ferramenta desktop que faz o que mais se usa do Altova XMLSpy no dia a dia:
abrir um `.xsd`, navegar pela estrutura do schema, **gerar um XML de exemplo**
a partir dele e **validar** documentos contra o schema.

## Instalacao

Precisa de Python 3.10 ou superior.

```bat
python -m pip install -r requirements.txt
```

## Uso

```bat
run.bat
```

Ou, sem o atalho: `python src\main.py`. Passando um caminho — `run.bat leiaute.xsd` —
o schema ja abre carregado.

O fluxo tipico:

1. **Abrir XSD...** — carrega o schema (os `include`/`import` sao resolvidos).
2. **Elemento raiz** — o combo lista todos os elementos globais; escolha qual
   sera a raiz do documento. Um duplo clique na aba *Estrutura do XSD* tambem
   define a raiz.
3. **Opcoes de geracao** — veja abaixo.
4. **Gerar XML (F5)** — o resultado aparece na aba *XML* e e validado
   automaticamente contra o proprio schema; a barra de status diz se ficou
   valido.
5. **Salvar como...** grava o arquivo.

### Detalhes do campo selecionado

Abaixo da arvore, o painel **Detalhes do item selecionado** responde "o que este
campo aceita?" para o elemento ou atributo clicado:

- tipo (e de que tipo ele deriva), cardinalidade, namespace, `default`, `fixed`,
  se e abstrato ou `nillable`, e o `use` no caso de atributo;
- a **documentacao** do `xs:annotation` do campo, ou do tipo quando o campo nao
  tem uma propria;
- as **restricoes**: o `pattern` como escrito no XSD, tamanhos, digitos, casas
  decimais e faixa numerica;
- a lista completa de **valores permitidos** quando o tipo tem `xs:enumeration`,
  com a descricao de cada valor se o schema documentou uma a uma;
- o **exemplo gerado**, que e exatamente o valor que o gerador colocaria ali.

Grupos (`xs:sequence`, `xs:choice`) e `xs:any` tambem tem sua explicacao. O
divisor entre a arvore e o painel e arrastavel.

Para conferir um documento que voce ja tem: **Abrir XML...** e **Validar (F8)**.
Os erros aparecem na aba *Validacao* com linha, coluna e mensagem, e um duplo
clique salta para a linha correspondente no editor.

### Opcoes de geracao

| Opcao | Efeito |
| --- | --- |
| Incluir elementos opcionais | Gera tambem o que tem `minOccurs="0"` |
| Incluir atributos opcionais | Gera tambem os `use="optional"` |
| Repeticoes quando `maxOccurs > 1` | Quantas copias de cada elemento repetivel |
| Profundidade maxima | Corta a arvore alem desse nivel |
| `xs:choice` | Só a primeira opcao, ou a primeira mais as demais como comentario |
| `xsi:schemaLocation` | Aponta o documento gerado para o `.xsd` de origem |
| Documentacao | Copia o `xs:annotation` de cada elemento como comentario |

Os botoes **XML minimo** e **Esqueleto completo** ajustam tudo de uma vez: o
primeiro produz o menor documento valido, o segundo um esqueleto com todos os
elementos e atributos, util como referencia da estrutura.

### Valores de exemplo

Os valores respeitam as restricoes declaradas no XSD, nesta ordem: `fixed`,
`default`, `enumeration`, o proprio nome do campo quando ele satisfaz o tipo,
`pattern` (uma string e sintetizada a partir do regex), facets de comprimento e
de faixa numerica, e por fim o tipo base. Cada candidato so e aceito depois de
passar pela validacao do proprio tipo, de modo que uma heuristica que nao sirva
cai automaticamente para a proxima.

Na pratica isso quer dizer que `natOp` sai como `natOp` (o pattern da NFe aceita
qualquer texto), `CNPJ` sai como quatorze digitos (o pattern manda) e `dhEmi`
sai como `2026-01-01T12:00:00-03:00` (data e hora sao declaradas como texto com
pattern nos leiautes fiscais). Quando nenhum candidato satisfaz o tipo -- o que
acontece em schemas publicados com restricoes contraditorias -- o campo aparece
na barra de status como "sem valor de exemplo confiavel".

Repeticoes do mesmo elemento recebem valores diferentes entre si -- alem de
ficar mais legivel, e o que evita violar restricoes `xs:unique`.

Casos que o gerador nao tem como resolver sozinho, e que aparecem no XML como
comentario:

- **Tipos recursivos** — a recursao e interrompida com
  `<!-- recursao interrompida -->`. Se o elemento recursivo for obrigatorio, o
  documento gerado fica proposital e necessariamente incompleto.
- **`xs:any`** — o comentario traz a documentacao do proprio schema ("Insira
  neste local o XML especifico do modal..."). Se for obrigatorio e o schema nao
  exigir validar o conteudo (`processContents="skip"` ou `"lax"`), entra tambem
  um `<elementoQualquer/>` de marcacao — e o caso do `infModal` do CTe/MDFe. Com
  `"strict"` fica so o comentario: o validador exige uma declaracao global de
  verdade e qualquer nome inventado seria rejeitado, entao esse trecho e um dos
  poucos em que o XML gerado nao valida sozinho.
- **`xs:IDREF`** — aponta para o primeiro `xs:ID` gerado no documento.

### Schemas com defeito

Alguns XSDs publicados tem inconsistencias (um tipo global declarado duas vezes,
um `include` apontando para arquivo inexistente). Nesses casos o aplicativo
oferece abrir em **modo tolerante**: a geracao do XML funciona, mas a validacao
fica indisponivel, porque o validador tambem se recusa a compilar o schema.

## Linha de comando

Util para automacao e para gerar exemplos em lote:

```bat
python src\cli.py caminho\do\schema.xsd --listar
python src\cli.py caminho\do\schema.xsd -r NFe --minimo -o exemplo.xml
python src\cli.py caminho\do\schema.xsd --repeticoes 3 > exemplo.xml
```

O codigo de saida e 1 quando o XML gerado nao valida contra o schema.

## Executavel

```bat
build_exe.bat
```

Gera `dist\ZilsXMLInspector.exe`, que roda em maquinas sem Python instalado.

## Testes

```bat
python -m pytest tests\
```

A garantia principal e um teste de ida e volta: para cada schema de exemplo e
cada combinacao de opcoes, o XML gerado precisa validar contra o proprio XSD.
Os testes de interface exercitam a janela de verdade, sem entrar no `mainloop`.

## Estrutura

```
src\
  main.py          ponto de entrada
  cli.py           interface de linha de comando
  xsdmodel.py      carga do XSD e montagem da arvore (sob demanda)
  generator.py     percorre o modelo de conteudo e monta o XML
  samplevalues.py  valor de exemplo por tipo, respeitando os facets
  regexsample.py   string de exemplo a partir de um xs:pattern
  validator.py     validacao com linha e coluna (libxml2)
  ui\              janela, arvore, detalhes, opcoes, editor e lista de erros
tests\             testes e schemas de exemplo
```

Feito com Python, tkinter, [xmlschema](https://pypi.org/project/xmlschema/) e
[lxml](https://pypi.org/project/lxml/).
"# ZilsXMLInspector" 
# ZilsXMLInspector
