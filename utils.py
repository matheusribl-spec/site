import time
from pathlib import Path
from typing import Optional

from flask import current_app
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from config import Config


def is_allowed_file(filename: str) -> bool:
    if not filename or "." not in filename:
        return False
    extension = filename.rsplit(".", 1)[1].lower()
    return extension in Config.ALLOWED_EXTENSIONS


def save_profile_image(file_storage: FileStorage) -> str:
    filename = secure_filename(file_storage.filename)
    if not filename:
        raise ValueError("Arquivo inválido para upload.")

    if not is_allowed_file(filename):
        raise ValueError("Tipo de arquivo não permitido.")

    upload_folder = Path(current_app.config["UPLOAD_FOLDER"])
    upload_folder.mkdir(parents=True, exist_ok=True)

    sanitized = f"{int(time.time())}_{filename}"
    destination = upload_folder / sanitized
    file_storage.save(str(destination))
    return sanitized
