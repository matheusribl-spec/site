from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import database
from config import Config

Row = Dict[str, Any]


def initialize_database() -> None:
    database.ensure_database()
    _create_tables()


def _create_tables() -> None:
    if Config.DB_USE_SQLITE:
        database.execute(
            """
            CREATE TABLE IF NOT EXISTS tb_usuario (
                id_usuario INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT,
                nome TEXT,
                senha TEXT,
                profile_image TEXT
            )
            """,
            commit=True,
        )

        database.execute(
            """
            CREATE TABLE IF NOT EXISTS noticias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tema TEXT,
                manchete TEXT,
                link TEXT UNIQUE,
                fonte TEXT,
                image TEXT,
                data TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            commit=True,
        )
        return

    database.execute(
        """
        CREATE TABLE IF NOT EXISTS tb_usuario (
            id_usuario INT AUTO_INCREMENT PRIMARY KEY,
            email VARCHAR(255),
            nome VARCHAR(255),
            senha VARCHAR(255),
            profile_image VARCHAR(255)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """,
        commit=True,
    )

    database.execute(
        """
        CREATE TABLE IF NOT EXISTS noticias (
            id INT AUTO_INCREMENT PRIMARY KEY,
            tema VARCHAR(100),
            manchete VARCHAR(500),
            link VARCHAR(500) UNIQUE,
            fonte VARCHAR(50),
            image VARCHAR(500),
            data TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """,
        commit=True,
    )


def get_user_by_email(email: str) -> Optional[Row]:
    if not email:
        return None

    return database.query_one(
        "SELECT id_usuario, email, nome, senha, profile_image FROM tb_usuario WHERE email = ? LIMIT 1",
        (email,),
    )


def get_user_by_id(user_id: int) -> Optional[Row]:
    return database.query_one(
        "SELECT id_usuario, email, nome, senha, profile_image FROM tb_usuario WHERE id_usuario = ? LIMIT 1",
        (user_id,),
    )


def create_user(email: Optional[str], name: Optional[str], password_hash: Optional[str], profile_image: Optional[str]) -> int:
    return database.insert(
        "INSERT INTO tb_usuario (email, nome, senha, profile_image) VALUES (?, ?, ?, ?)",
        (email or None, name or None, password_hash or None, profile_image or None),
    )


def update_user_profile(user_id: int, name: Optional[str], password_hash: Optional[str], profile_image: Optional[str]) -> int:
    updates: List[str] = []
    params: List[Any] = []

    if name:
        updates.append("nome = ?")
        params.append(name)

    if password_hash:
        updates.append("senha = ?")
        params.append(password_hash)

    if profile_image:
        updates.append("profile_image = ?")
        params.append(profile_image)

    if not updates:
        return 0

    params.append(user_id)
    return database.update(
        f"UPDATE tb_usuario SET {', '.join(updates)} WHERE id_usuario = ?",
        tuple(params),
    )


def get_news_by_link(link: str) -> Optional[Row]:
    if not link:
        return None

    return database.query_one("SELECT id FROM noticias WHERE link = ? LIMIT 1", (link,))


def save_news_items(news_items: List[Dict[str, Optional[str]]]) -> int:
    created = 0

    for item in news_items:
        link = (item.get("link") or "").strip()
        if not link or get_news_by_link(link):
            continue

        try:
            database.insert(
                "INSERT INTO noticias (tema, manchete, link, fonte, image) VALUES (?, ?, ?, ?, ?)",
                (
                    (item.get("tema") or "Política").strip(),
                    (item.get("manchete") or "").strip()[:500],
                    link[:500],
                    (item.get("fonte") or "").strip()[:100],
                    (item.get("image") or None),
                ),
            )
            created += 1
        except Exception:
            continue

    return created


def get_news_list(
    fonte: str = "",
    tema: str = "",
    pesquisa: str = "",
    data_inicio: str = "",
    data_fim: str = "",
) -> List[Row]:
    query = "SELECT id, tema, manchete, link, fonte, image, data FROM noticias WHERE 1 = 1"
    params: List[Any] = []

    if fonte:
        query += " AND fonte = ?"
        params.append(fonte)

    if tema:
        query += " AND tema = ?"
        params.append(tema)

    if pesquisa:
        query += " AND (manchete LIKE ? OR link LIKE ?)"
        params.append(f"%{pesquisa}%")
        params.append(f"%{pesquisa}%")

    if data_inicio:
        query += " AND DATE(data) >= ?"
        params.append(data_inicio)

    if data_fim:
        query += " AND DATE(data) <= ?"
        params.append(data_fim)

    query += " ORDER BY data DESC LIMIT 100"
    return database.query(query, tuple(params))


def get_sources_stats() -> List[Row]:
    return database.query(
        "SELECT fonte, COUNT(*) AS total FROM noticias GROUP BY fonte ORDER BY total DESC"
    )


def get_topic_stats() -> List[Row]:
    return database.query(
        "SELECT tema, COUNT(*) AS total FROM noticias GROUP BY tema ORDER BY total DESC"
    )


def get_available_sources() -> List[str]:
    return [item["fonte"] for item in get_sources_stats()]


def get_available_themes() -> List[str]:
    return [item["tema"] for item in get_topic_stats()]


def get_timeline_data() -> List[Row]:
    start_date = datetime.utcnow().date() - timedelta(days=14)
    return database.query(
        "SELECT DATE(data) AS dia, COUNT(*) AS total "
        "FROM noticias "
        "WHERE data >= ? "
        "GROUP BY DATE(data) "
        "ORDER BY dia",
        (start_date.isoformat(),),
    )


def get_total_news() -> int:
    row = database.query_one("SELECT COUNT(*) AS total FROM noticias")
    if not row:
        return 0

    return int(row.get("total", 0))
