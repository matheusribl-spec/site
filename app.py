import logging
import os
from typing import Any

from flask import Flask, flash, redirect, render_template, request, session, url_for

import auth
import dashboard
import models
from config import Config

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = Config.SECRET_KEY
app.config["UPLOAD_FOLDER"] = str(Config.UPLOAD_FOLDER)
app.config["MAX_CONTENT_LENGTH"] = Config.MAX_CONTENT_LENGTH

models.initialize_database()


@app.route("/")
def index() -> Any:
    filtro_fonte = request.args.get("fonte", "")
    filtro_tema = request.args.get("tema", "")
    pesquisa = request.args.get("q", "").strip()
    data_inicio = request.args.get("data_inicio", "")
    data_fim = request.args.get("data_fim", "")

    noticias = models.get_news_list(
        fonte=filtro_fonte,
        tema=filtro_tema,
        pesquisa=pesquisa,
        data_inicio=data_inicio,
        data_fim=data_fim,
    )

    dados_fonte = models.get_sources_stats()
    dados_tema = models.get_topic_stats()
    dados_timeline = models.get_timeline_data()
    total_noticias = models.get_total_news()
    context = dashboard.build_dashboard_context(
        dados_fonte=dados_fonte,
        dados_tema=dados_tema,
        dados_timeline=dados_timeline,
        total_noticias=total_noticias,
    )

    return render_template(
        "index.html",
        noticias=noticias,
        mensagem=None,
        filtro_fonte=filtro_fonte,
        filtro_tema=filtro_tema,
        pesquisa=pesquisa,
        data_inicio=data_inicio,
        data_fim=data_fim,
        **context,
    )


@app.route("/atualizar", methods=["POST"])
def refresh_news() -> Any:
    from flask import request
import logging

logging.warning("=" * 60)
logging.warning("ENTROU NA ROTA /atualizar")
logging.warning("Método: %s", request.method)
logging.warning("User-Agent: %s", request.headers.get("User-Agent"))
logging.warning("IP: %s", request.remote_addr)
logging.warning("=" * 60)
    import scraper

    quantidade_novas = scraper.update_news()
    flash(f"{quantidade_novas} nova(s) notícia(s) coletada(s).", "success")
    return redirect(url_for("index"))


@app.route("/login", methods=["GET", "POST"])
def login() -> Any:
    if request.method == "POST":
        return auth.process_login()
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register() -> Any:
    if request.method == "POST":
        return auth.process_registration()
    return render_template("register.html")


@app.route("/logout")
def logout() -> Any:
    session.clear()
    flash("Você saiu da sessão.", "success")
    return redirect(url_for("index"))


@app.errorhandler(403)
def forbidden(error: Any) -> Any:
    return render_template("403.html"), 403


@app.errorhandler(404)
def not_found(error: Any) -> Any:
    return render_template("404.html"), 404


@app.errorhandler(500)
def internal_server_error(error: Any) -> Any:
    logger.exception("Internal server error: %s", error)
    return render_template("500.html"), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
