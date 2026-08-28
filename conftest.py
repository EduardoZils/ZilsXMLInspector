"""Coloca src/ no sys.path para que os testes importem os modulos do aplicativo.

O aplicativo e executado como `python src\\main.py`, o que ja poe src/ no
caminho; nos testes o pytest precisa da mesma ajuda.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
