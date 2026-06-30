import logging
from typing import Any, Dict, Optional

from flask import flash, redirect, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

import models
from utils import save_profile_image

logger = logging.getLogger(__name__)


def _login_user(user: Dict[str, Any]) -> None:
    session["user_id"] = user["id_usuario"]
    session["user_name"] = user.get("nome") or "Usuário"
    if user.get("profile_image"):
        session["profile_image"] = user["profile_image"]


def process_registration() -> Any:
    nome = request.form.get("nome", "").strip()
    email = request.form.get("email", "").strip().lower()
    senha = request.form.get("senha", "").strip()
    foto = request.files.get("foto")

    if not nome:
        flash("Informe seu nome para continuar.", "warning")
        return redirect(url_for("register"))

    profile_image: Optional[str] = None
    if foto and foto.filename:
        try:
            profile_image = save_profile_image(foto)
        except ValueError as error:
            flash(str(error), "warning")
            return redirect(url_for("register"))

    existing_user = models.get_user_by_email(email) if email else None
    password_hash = generate_password_hash(senha) if senha else None

    try:
        if existing_user:
            models.update_user_profile(
                existing_user["id_usuario"], nome, password_hash, profile_image
            )
            user = models.get_user_by_id(existing_user["id_usuario"])
            flash("Perfil atualizado com sucesso.", "success")
        else:
            user_id = models.create_user(email or None, nome, password_hash, profile_image)
            user = models.get_user_by_id(user_id)
            flash("Cadastro realizado com sucesso.", "success")

        if user:
            _login_user(user)
            return redirect(url_for("index"))

        flash("Não foi possível salvar o cadastro.", "danger")
        return redirect(url_for("register"))
    except Exception:
        logger.exception("Erro ao salvar usuário")
        flash("Erro interno. Tente novamente mais tarde.", "danger")
        return redirect(url_for("register"))


def process_login() -> Any:
    email = request.form.get("email", "").strip().lower()
    senha = request.form.get("senha", "").strip()

    if not email or not senha:
        flash("Preencha email e senha.", "warning")
        return redirect(url_for("login"))

    user = models.get_user_by_email(email)
    if not user or not user.get("senha"):
        flash("Email ou senha inválidos.", "danger")
        return redirect(url_for("login"))

    if not check_password_hash(user["senha"], senha):
        flash("Email ou senha inválidos.", "danger")
        return redirect(url_for("login"))

    _login_user(user)
    flash("Login efetuado com sucesso.", "success")
    return redirect(url_for("index"))
