"""Ponto de entrada do Zils XML Inspector."""
import os
import sys

# Permite executar tanto como "python src/main.py" quanto empacotado pelo
# PyInstaller, onde o diretorio dos modulos e resolvido em tempo de execucao.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui.app import executar

if __name__ == "__main__":
    # Aceita o caminho de um .xsd para ja abri-lo ao iniciar.
    executar(sys.argv[1] if len(sys.argv) > 1 else None)
