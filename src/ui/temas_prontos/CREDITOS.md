# Temas de terceiros

Os temas visuais desta pasta nao sao do Zils XML Inspector: sao projetos de
codigo aberto de **rdbende**, incluidos aqui sem modificacao. Todos sao
licenciados sob a **licenca MIT**, cujo texto acompanha cada pasta.

| Pasta | Projeto | Origem |
| --- | --- | --- |
| `azure/` | Azure ttk theme | https://github.com/rdbende/Azure-ttk-theme |
| `forest/` | Forest ttk theme | https://github.com/rdbende/Forest-ttk-theme |
| `sun-valley/` | Sun Valley ttk theme (pacote `sv-ttk` 2.6.1) | https://github.com/rdbende/Sun-Valley-ttk-theme |

Copyright (c) 2021 rdbende. Veja `azure/LICENSE`, `forest/LICENSE` e
`sun-valley/LICENSE`.

## Por que estao versionados aqui

O Azure e o Forest nao sao publicados no PyPI, entao nao ha como declara-los
como dependencia. Manter os tres no repositorio deixa o aplicativo
autocontido: nao ha download em tempo de execucao, e o executavel gerado pelo
PyInstaller so precisa levar esta pasta junto (veja `datas` em
`ZilsXMLInspector.spec`).

## Ao atualizar

Cada `.tcl` referencia suas imagens por caminho relativo, entao a estrutura de
pastas de cada familia precisa ser preservada como esta. Basta substituir a
pasta inteira da familia e conferir se os nomes dos temas continuam os mesmos
(`azure-light`, `azure-dark`, `forest-light`, `forest-dark`, `sun-valley-light`,
`sun-valley-dark`) -- e por esses nomes que `src/ui/temas.py` os referencia.
