# Implantação e configuração

Este projeto está preparado para rodar em PythonAnywhere com SQLite e em Railway/Render com MySQL apenas alterando variáveis de ambiente.

## Variáveis de ambiente suportadas

- `SECRET_KEY`: chave secreta do Flask.
- `DB_USE_SQLITE`: defina `1` para usar SQLite.
- `SQLITE_PATH`: caminho do arquivo SQLite.
- `DB_HOST`: host do MySQL.
- `DB_USER`: usuário MySQL.
- `DB_PASSWORD`: senha MySQL.
- `DB_NAME`: nome do banco MySQL.
- `DB_PORT`: porta MySQL.
- `MAX_CONTENT_LENGTH`: limite de upload em bytes.

## Passo 1: instalar dependências

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Passo 2: configurar SQLite para PythonAnywhere

```bash
export DB_USE_SQLITE=1
export SQLITE_PATH="$PWD/data.sqlite"
export SECRET_KEY="uma_senha_segura_aqui"
python setup_db.py
```

## Passo 3: configurar o Web App no PythonAnywhere

1. Em `Source code`, aponte para a pasta do projeto.
2. Em `Working directory`, use o mesmo caminho.
3. No arquivo WSGI, carregue o aplicativo usando:

```python
import sys
import os
from pathlib import Path

project_home = Path(__file__).resolve().parent
if str(project_home) not in sys.path:
    sys.path.insert(0, str(project_home))

os.environ.setdefault('DB_USE_SQLITE', '1')
os.environ.setdefault('SQLITE_PATH', str(project_home / 'data.sqlite'))
os.environ.setdefault('SECRET_KEY', 'uma_senha_segura_aqui')

from wsgi import application
```

4. No `Web`, defina `DB_USE_SQLITE`, `SQLITE_PATH` e `SECRET_KEY` se necessário.

## Passo 4: rodar localmente

```bash
export DB_USE_SQLITE=1
export SQLITE_PATH="$PWD/data.sqlite"
export SECRET_KEY="uma_senha_segura_aqui"
python app.py
```

## Rodar com MySQL

Defina as variáveis `DB_USE_SQLITE=0`, `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` e `DB_PORT`.

## Observações

- O projeto usa upload seguro de imagens e validação de formulário básica.
- O banco é gerenciado via `database.py`, sem acesso direto a `sqlite3` ou `pymysql` fora dele.
- O scraper usa `requests.Session`, retry, timeout e filtro de links irrelevantes.
