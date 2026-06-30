import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import pymysql
from pymysql.cursors import DictCursor
from pymysql.connections import Connection as PyMySQLConnection

from config import Config

DatabaseParams = Optional[Union[Sequence[Any], Tuple[Any, ...]]]
Row = Dict[str, Any]
Connection = Union[sqlite3.Connection, PyMySQLConnection]


def _prepare_query(sql: str) -> str:
    return sql if Config.DB_USE_SQLITE else sql.replace("?", "%s")


def _normalize_row(row: Any) -> Optional[Row]:
    if row is None:
        return None

    if isinstance(row, sqlite3.Row):
        row = dict(row)
    elif isinstance(row, dict):
        row = dict(row)
    else:
        row = dict(row)

    if "data" in row and isinstance(row["data"], str):
        try:
            row["data"] = datetime.fromisoformat(row["data"])
        except ValueError:
            pass

    if "dia" in row and isinstance(row["dia"], str):
        try:
            row["dia"] = datetime.fromisoformat(row["dia"]).date()
        except ValueError:
            pass

    return row


def get_connection() -> Connection:
    if Config.DB_USE_SQLITE:
        Config.SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(str(Config.SQLITE_PATH), check_same_thread=False)
        connection.row_factory = sqlite3.Row
        return connection

    return pymysql.connect(
        host=Config.DB_HOST,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        database=Config.DB_NAME,
        port=Config.DB_PORT,
        charset="utf8mb4",
        cursorclass=DictCursor,
        autocommit=False,
    )


def ensure_database() -> None:
    if Config.DB_USE_SQLITE:
        Config.SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
        return

    raw_connection = pymysql.connect(
        host=Config.DB_HOST,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        port=Config.DB_PORT,
        charset="utf8mb4",
        cursorclass=DictCursor,
        autocommit=True,
    )
    try:
        with raw_connection.cursor() as cursor:
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{Config.DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
    finally:
        raw_connection.close()


def execute(sql: str, params: DatabaseParams = None, commit: bool = False) -> int:
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(_prepare_query(sql), params or ())
        if commit:
            connection.commit()
        return cursor.lastrowid if cursor.lastrowid else cursor.rowcount
    except Exception:
        try:
            connection.rollback()
        except Exception:
            pass
        raise
    finally:
        cursor.close()
        connection.close()


def insert(sql: str, params: DatabaseParams = None) -> int:
    return execute(sql, params, commit=True)


def update(sql: str, params: DatabaseParams = None) -> int:
    return execute(sql, params, commit=True)


def query(sql: str, params: DatabaseParams = None) -> List[Row]:
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(_prepare_query(sql), params or ())
        rows = cursor.fetchall()
        return [_normalize_row(row) for row in rows]
    finally:
        cursor.close()
        connection.close()


def query_one(sql: str, params: DatabaseParams = None) -> Optional[Row]:
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(_prepare_query(sql), params or ())
        return _normalize_row(cursor.fetchone())
    finally:
        cursor.close()
        connection.close()


def commit(connection: Connection) -> None:
    connection.commit()


def close(connection: Connection) -> None:
    connection.close()
