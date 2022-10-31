"""
Project linter to help refactoring
"""
import glob

try:
    import pylint
except ModuleNotFoundError:
    import os

    os.system("pip install pylint > pylint-installation-output.txt")
    os.remove("pylint-installation-output.txt")
    import pylint

all_modules = glob.glob('../*.py')
all_modules += glob.glob('../[!venv]*/*.py')
all_modules += glob.glob('../[!venv]*/*/[!db]*.py')
all_modules += glob.glob('../endpoints/*.py')

pylint.run_pylint(all_modules)
