"""
Hybrid Database Storage Layer (MySQL Primary, SQLite Fallback).

Supports MySQL via PyMySQL with connection wrapping, parameter adaptation (? -> %s),
automated database provisioning, and DDL schema management.
Provides automatic offline fallback to SQLite WAL mode for maximum resilience.
"""

from __future__ import annotations
import json
import logging
import os
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

try:
    import pymysql
    import pymysql.cursors
    HAS_PYMYSQL = True
except ImportError:
    HAS_PYMYSQL = False

logger = logging.getLogger("docucraft.database")


class MySQLCursorWrapper:
    """Wraps PyMySQL DictCursor and adapts '?' parameter placeholders to '%s'."""

    def __init__(self, cursor):
        self.cursor = cursor

    def execute(self, query: str, params: Optional[Union[tuple, list, dict]] = None):
        # Translate '?' placeholder syntax to MySQL '%s'
        query_mod = query.replace("?", "%s")
        if params is not None:
            return self.cursor.execute(query_mod, params)
        return self.cursor.execute(query_mod)

    def fetchone(self) -> Optional[Dict[str, Any]]:
        return self.cursor.fetchone()

    def fetchall(self) -> List[Dict[str, Any]]:
        return self.cursor.fetchall()

    @property
    def rowcount(self) -> int:
        return self.cursor.rowcount

    def close(self) -> None:
        self.cursor.close()


class MySQLConnectionWrapper:
    """Manages transactional scope and dict-cursor execution for PyMySQL."""

    def __init__(self, raw_conn):
        self.raw_conn = raw_conn

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if exc_type:
                self.raw_conn.rollback()
            else:
                self.raw_conn.commit()
        finally:
            self.raw_conn.close()

    def execute(self, query: str, params: Optional[Union[tuple, list, dict]] = None) -> MySQLCursorWrapper:
        cursor = self.raw_conn.cursor(pymysql.cursors.DictCursor)
        wrapper = MySQLCursorWrapper(cursor)
        wrapper.execute(query, params)
        return wrapper

    def commit(self) -> None:
        self.raw_conn.commit()

    def rollback(self) -> None:
        self.raw_conn.rollback()

    def close(self) -> None:
        self.raw_conn.close()


class SQLiteConnectionWrapper:
    """Wraps SQLite connection to provide uniform context management and dict access."""

    def __init__(self, raw_conn: sqlite3.Connection):
        self.raw_conn = raw_conn

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if exc_type:
                self.raw_conn.rollback()
            else:
                self.raw_conn.commit()
        finally:
            self.raw_conn.close()

    def execute(self, query: str, params: Optional[Union[tuple, list, dict]] = None):
        if params is not None:
            return self.raw_conn.execute(query, params)
        return self.raw_conn.execute(query)

    def commit(self) -> None:
        self.raw_conn.commit()

    def rollback(self) -> None:
        self.raw_conn.rollback()

    def close(self) -> None:
        self.raw_conn.close()


class Database:
    """
    Database Storage Engine.
    Operates with MySQL as the primary engine, and SQLite with WAL mode as a fallback.
    """

    def __init__(
        self,
        db_path: Optional[str] = None,
        db_type: Optional[str] = None,
        mysql_host: Optional[str] = None,
        mysql_port: Optional[int] = None,
        mysql_user: Optional[str] = None,
        mysql_password: Optional[str] = None,
        mysql_database: Optional[str] = None,
    ):
        self.db_path = db_path or os.path.join(os.getcwd(), "workspaces", "platform_meta.db")
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)

        # Configuration from arguments or environment
        requested_type = (db_type or os.getenv("DB_TYPE", "mysql")).lower()
        self.mysql_host = mysql_host or os.getenv("MYSQL_HOST", "127.0.0.1")
        self.mysql_port = int(mysql_port or os.getenv("MYSQL_PORT", 3306))
        self.mysql_user = mysql_user or os.getenv("MYSQL_USER", "root")
        self.mysql_password = mysql_password or os.getenv("MYSQL_PASSWORD", "0000")
        self.mysql_db = mysql_database or os.getenv("MYSQL_DATABASE", "docucraft_db")

        self.using_mysql = False

        if requested_type == "mysql" and HAS_PYMYSQL:
            if self._init_mysql_database():
                self.using_mysql = True
                logger.info(f"Connected to MySQL at {self.mysql_host}:{self.mysql_port}/{self.mysql_db}")
            else:
                logger.warning("Falling back to local SQLite database.")

        self._init_schema()

    def _init_mysql_database(self) -> bool:
        """Connects to MySQL server and ensures the target database exists."""
        try:
            raw = pymysql.connect(
                host=self.mysql_host,
                port=self.mysql_port,
                user=self.mysql_user,
                password=self.mysql_password,
                charset="utf8mb4",
                connect_timeout=5,
            )
            with raw.cursor() as cur:
                cur.execute(
                    f"CREATE DATABASE IF NOT EXISTS `{self.mysql_db}` "
                    "DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
                )
            raw.commit()
            raw.close()
            return True
        except Exception as e:
            logger.warning(f"MySQL database initialization failed: {e}")
            return False

    def _get_mysql_connection(self) -> MySQLConnectionWrapper:
        """Returns wrapped MySQL connection."""
        raw = pymysql.connect(
            host=self.mysql_host,
            port=self.mysql_port,
            user=self.mysql_user,
            password=self.mysql_password,
            database=self.mysql_db,
            charset="utf8mb4",
            autocommit=False,
            connect_timeout=10,
        )
        return MySQLConnectionWrapper(raw)

    def _get_sqlite_connection(self) -> SQLiteConnectionWrapper:
        """Returns wrapped thread-safe SQLite connection with WAL mode enabled."""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        return SQLiteConnectionWrapper(conn)

    def get_connection(self) -> Union[MySQLConnectionWrapper, SQLiteConnectionWrapper]:
        """Returns connection context manager for the active database engine."""
        if self.using_mysql:
            try:
                return self._get_mysql_connection()
            except Exception as e:
                logger.error(f"MySQL connection error: {e}. Falling back to SQLite.")
        return self._get_sqlite_connection()

    def _init_schema(self) -> None:
        """Initializes tables for either MySQL or SQLite."""
        if self.using_mysql:
            self._init_mysql_schema()
        else:
            self._init_sqlite_schema()

    def _init_mysql_schema(self) -> None:
        """Initializes MySQL DDL schemas with InnoDB and utf8mb4."""
        with self.get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS projects (
                    id VARCHAR(64) PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    description TEXT,
                    source_filename VARCHAR(255) DEFAULT '',
                    source_path VARCHAR(1024) DEFAULT '',
                    output_path VARCHAR(1024) DEFAULT '',
                    template_id VARCHAR(64) DEFAULT 'book',
                    page_count INT DEFAULT 0,
                    word_count INT DEFAULT 0,
                    chapter_count INT DEFAULT 0,
                    status VARCHAR(32) DEFAULT 'DRAFT',
                    created_at VARCHAR(64) NOT NULL,
                    updated_at VARCHAR(64) NOT NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id VARCHAR(64) PRIMARY KEY,
                    project_id VARCHAR(64) NOT NULL,
                    input_file VARCHAR(1024),
                    template_id VARCHAR(64) DEFAULT 'book',
                    status VARCHAR(32) NOT NULL,
                    progress DOUBLE DEFAULT 0.0,
                    current_stage VARCHAR(64) DEFAULT 'QUEUED',
                    current_chunk INT DEFAULT 0,
                    total_chunks INT DEFAULT 0,
                    errors_json LONGTEXT,
                    warnings_json LONGTEXT,
                    output_file VARCHAR(1024),
                    created_at VARCHAR(64) NOT NULL,
                    updated_at VARCHAR(64) NOT NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS job_checkpoints (
                    job_id VARCHAR(64) NOT NULL,
                    chunk_id VARCHAR(64) NOT NULL,
                    stage VARCHAR(64) NOT NULL,
                    status VARCHAR(32) NOT NULL,
                    result_json LONGTEXT,
                    updated_at VARCHAR(64) NOT NULL,
                    PRIMARY KEY (job_id, chunk_id, stage)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS corrections (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    project_id VARCHAR(64) NOT NULL,
                    block_id VARCHAR(64) NOT NULL,
                    original_text TEXT,
                    predicted_type VARCHAR(64) NOT NULL,
                    corrected_type VARCHAR(64) NOT NULL,
                    confidence DOUBLE DEFAULT 0.0,
                    features_json LONGTEXT,
                    created_at VARCHAR(64) NOT NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS templates (
                    id VARCHAR(64) PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    version VARCHAR(32) DEFAULT '1.0',
                    description TEXT,
                    category VARCHAR(64) DEFAULT 'Custom',
                    json_data LONGTEXT NOT NULL,
                    is_builtin TINYINT(1) DEFAULT 0,
                    created_at VARCHAR(64) NOT NULL,
                    updated_at VARCHAR(64) NOT NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS settings (
                    key_name VARCHAR(128) PRIMARY KEY,
                    value_json LONGTEXT NOT NULL,
                    updated_at VARCHAR(64) NOT NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS logo_assets (
                    project_id VARCHAR(64) PRIMARY KEY,
                    filename VARCHAR(255) NOT NULL,
                    file_path VARCHAR(1024) NOT NULL,
                    mime_type VARCHAR(64) NOT NULL,
                    sha256 VARCHAR(64) NOT NULL,
                    width INT NOT NULL,
                    height INT NOT NULL,
                    file_size_bytes BIGINT NOT NULL,
                    is_valid TINYINT(1) DEFAULT 1,
                    validation_message TEXT,
                    uploaded_at VARCHAR(64) NOT NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS validation_reports (
                    job_id VARCHAR(64) PRIMARY KEY,
                    project_id VARCHAR(64) NOT NULL,
                    pre_metrics_json LONGTEXT NOT NULL,
                    post_metrics_json LONGTEXT NOT NULL,
                    is_preserved TINYINT(1) DEFAULT 1,
                    discrepancies_json LONGTEXT,
                    created_at VARCHAR(64) NOT NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    project_id VARCHAR(64),
                    event_type VARCHAR(64) NOT NULL,
                    details_json LONGTEXT NOT NULL,
                    created_at VARCHAR(64) NOT NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                """
            )

    def _init_sqlite_schema(self) -> None:
        """Initializes SQLite DDL schemas."""
        with self.get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    source_filename TEXT DEFAULT '',
                    source_path TEXT DEFAULT '',
                    output_path TEXT DEFAULT '',
                    template_id TEXT DEFAULT 'book',
                    page_count INTEGER DEFAULT 0,
                    word_count INTEGER DEFAULT 0,
                    chapter_count INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'DRAFT',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    input_file TEXT,
                    template_id TEXT DEFAULT 'book',
                    status TEXT NOT NULL,
                    progress REAL DEFAULT 0.0,
                    current_stage TEXT DEFAULT 'QUEUED',
                    current_chunk INTEGER DEFAULT 0,
                    total_chunks INTEGER DEFAULT 0,
                    errors_json TEXT DEFAULT '[]',
                    warnings_json TEXT DEFAULT '[]',
                    output_file TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS job_checkpoints (
                    job_id TEXT NOT NULL,
                    chunk_id TEXT NOT NULL,
                    stage TEXT NOT NULL,
                    status TEXT NOT NULL,
                    result_json TEXT,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (job_id, chunk_id, stage)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS corrections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id TEXT NOT NULL,
                    block_id TEXT NOT NULL,
                    original_text TEXT,
                    predicted_type TEXT NOT NULL,
                    corrected_type TEXT NOT NULL,
                    confidence REAL DEFAULT 0.0,
                    features_json TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS templates (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    version TEXT DEFAULT '1.0',
                    description TEXT DEFAULT '',
                    category TEXT DEFAULT 'Custom',
                    json_data TEXT NOT NULL,
                    is_builtin INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS settings (
                    key_name TEXT PRIMARY KEY,
                    value_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS logo_assets (
                    project_id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    mime_type TEXT NOT NULL,
                    sha256 TEXT NOT NULL,
                    width INTEGER NOT NULL,
                    height INTEGER NOT NULL,
                    file_size_bytes INTEGER NOT NULL,
                    is_valid INTEGER DEFAULT 1,
                    validation_message TEXT DEFAULT '',
                    uploaded_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS validation_reports (
                    job_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    pre_metrics_json TEXT NOT NULL,
                    post_metrics_json TEXT NOT NULL,
                    is_preserved INTEGER DEFAULT 1,
                    discrepancies_json TEXT DEFAULT '[]',
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id TEXT,
                    event_type TEXT NOT NULL,
                    details_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )

    # ------------------ Job Operations ------------------ #

    def create_or_update_job(self, job_data: Dict[str, Any]) -> None:
        now = datetime.utcnow().isoformat()
        with self.get_connection() as conn:
            if self.using_mysql:
                conn.execute(
                    """
                    INSERT INTO jobs (
                        job_id, project_id, input_file, template_id, status, progress,
                        current_stage, current_chunk, total_chunks, errors_json,
                        warnings_json, output_file, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON DUPLICATE KEY UPDATE
                        input_file=VALUES(input_file),
                        template_id=VALUES(template_id),
                        status=VALUES(status),
                        progress=VALUES(progress),
                        current_stage=VALUES(current_stage),
                        current_chunk=VALUES(current_chunk),
                        total_chunks=VALUES(total_chunks),
                        errors_json=VALUES(errors_json),
                        warnings_json=VALUES(warnings_json),
                        output_file=VALUES(output_file),
                        updated_at=VALUES(updated_at)
                    """,
                    (
                        job_data["job_id"],
                        job_data.get("project_id", ""),
                        job_data.get("input_file", ""),
                        job_data.get("template_id", "book"),
                        job_data.get("status", "QUEUED"),
                        job_data.get("progress", 0.0),
                        job_data.get("current_stage", "QUEUED"),
                        job_data.get("current_chunk", 0),
                        job_data.get("total_chunks", 0),
                        json.dumps(job_data.get("errors", [])),
                        json.dumps(job_data.get("warnings", [])),
                        job_data.get("output_file", ""),
                        job_data.get("created_at", now),
                        now,
                    ),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO jobs (
                        job_id, project_id, input_file, template_id, status, progress,
                        current_stage, current_chunk, total_chunks, errors_json,
                        warnings_json, output_file, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(job_id) DO UPDATE SET
                        status=excluded.status,
                        progress=excluded.progress,
                        current_stage=excluded.current_stage,
                        current_chunk=excluded.current_chunk,
                        total_chunks=excluded.total_chunks,
                        errors_json=excluded.errors_json,
                        warnings_json=excluded.warnings_json,
                        output_file=excluded.output_file,
                        updated_at=excluded.updated_at
                    """,
                    (
                        job_data["job_id"],
                        job_data.get("project_id", ""),
                        job_data.get("input_file", ""),
                        job_data.get("template_id", "book"),
                        job_data.get("status", "QUEUED"),
                        job_data.get("progress", 0.0),
                        job_data.get("current_stage", "QUEUED"),
                        job_data.get("current_chunk", 0),
                        job_data.get("total_chunks", 0),
                        json.dumps(job_data.get("errors", [])),
                        json.dumps(job_data.get("warnings", [])),
                        job_data.get("output_file", ""),
                        job_data.get("created_at", now),
                        now,
                    ),
                )

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,))
            row = cursor.fetchone()
            if not row:
                return None
            data = dict(row)
            data["errors"] = json.loads(data["errors_json"]) if data.get("errors_json") else []
            data["warnings"] = json.loads(data["warnings_json"]) if data.get("warnings_json") else []
            return data

    # ------------------ Checkpoints for Crash Recovery ------------------ #

    def save_checkpoint(self, job_id: str, chunk_id: str, stage: str, status: str, result: Any) -> None:
        now = datetime.utcnow().isoformat()
        with self.get_connection() as conn:
            verb = "REPLACE INTO" if self.using_mysql else "INSERT OR REPLACE INTO"
            conn.execute(
                f"""
                {verb} job_checkpoints (
                    job_id, chunk_id, stage, status, result_json, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (job_id, chunk_id, stage, status, json.dumps(result), now),
            )

    def get_checkpoints(self, job_id: str, stage: Optional[str] = None) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            if stage:
                cursor = conn.execute(
                    "SELECT * FROM job_checkpoints WHERE job_id = ? AND stage = ?",
                    (job_id, stage),
                )
            else:
                cursor = conn.execute(
                    "SELECT * FROM job_checkpoints WHERE job_id = ?", (job_id,)
                )
            results = []
            for r in cursor.fetchall():
                item = dict(r)
                if item.get("result_json"):
                    try:
                        item["result"] = json.loads(item["result_json"])
                    except Exception:
                        item["result"] = item["result_json"]
                results.append(item)
            return results

    # ------------------ Human-in-the-Loop Corrections ------------------ #

    def record_correction(
        self,
        project_id: str,
        block_id: str,
        original_text: str,
        predicted_type: str,
        corrected_type: str,
        confidence: float = 0.0,
        features: Optional[Dict[str, Any]] = None,
    ) -> None:
        now = datetime.utcnow().isoformat()
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO corrections (
                    project_id, block_id, original_text, predicted_type,
                    corrected_type, confidence, features_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project_id,
                    block_id,
                    original_text[:500] if original_text else "",
                    predicted_type,
                    corrected_type,
                    confidence,
                    json.dumps(features or {}),
                    now,
                ),
            )

    def get_corrections(self, project_id: Optional[str] = None) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            if project_id:
                cursor = conn.execute(
                    "SELECT * FROM corrections WHERE project_id = ? ORDER BY id DESC",
                    (project_id,),
                )
            else:
                cursor = conn.execute("SELECT * FROM corrections ORDER BY id DESC")
            return [dict(r) for r in cursor.fetchall()]

    # ------------------ Mandatory Publisher Logo Operations ------------------ #

    def save_logo_asset(self, project_id: str, logo_data: Dict[str, Any]) -> None:
        now = datetime.utcnow().isoformat()
        with self.get_connection() as conn:
            if self.using_mysql:
                conn.execute(
                    """
                    INSERT INTO logo_assets (
                        project_id, filename, file_path, mime_type, sha256,
                        width, height, file_size_bytes, is_valid, validation_message, uploaded_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON DUPLICATE KEY UPDATE
                        filename=VALUES(filename),
                        file_path=VALUES(file_path),
                        mime_type=VALUES(mime_type),
                        sha256=VALUES(sha256),
                        width=VALUES(width),
                        height=VALUES(height),
                        file_size_bytes=VALUES(file_size_bytes),
                        is_valid=VALUES(is_valid),
                        validation_message=VALUES(validation_message),
                        uploaded_at=VALUES(uploaded_at)
                    """,
                    (
                        project_id,
                        logo_data.get("filename", "publisher_logo.png"),
                        logo_data.get("file_path", ""),
                        logo_data.get("mime_type", "image/png"),
                        logo_data.get("sha256", logo_data.get("sha256_hash", "")),
                        logo_data.get("width", 0),
                        logo_data.get("height", 0),
                        logo_data.get("file_size_bytes", logo_data.get("file_size", 0)),
                        1 if logo_data.get("is_valid", True) else 0,
                        logo_data.get("validation_message", "Valid logo"),
                        now,
                    ),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO logo_assets (
                        project_id, filename, file_path, mime_type, sha256,
                        width, height, file_size_bytes, is_valid, validation_message, uploaded_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(project_id) DO UPDATE SET
                        filename=excluded.filename,
                        file_path=excluded.file_path,
                        mime_type=excluded.mime_type,
                        sha256=excluded.sha256,
                        width=excluded.width,
                        height=excluded.height,
                        file_size_bytes=excluded.file_size_bytes,
                        is_valid=excluded.is_valid,
                        validation_message=excluded.validation_message,
                        uploaded_at=excluded.uploaded_at
                    """,
                    (
                        project_id,
                        logo_data.get("filename", "publisher_logo.png"),
                        logo_data.get("file_path", ""),
                        logo_data.get("mime_type", "image/png"),
                        logo_data.get("sha256", logo_data.get("sha256_hash", "")),
                        logo_data.get("width", 0),
                        logo_data.get("height", 0),
                        logo_data.get("file_size_bytes", logo_data.get("file_size", 0)),
                        1 if logo_data.get("is_valid", True) else 0,
                        logo_data.get("validation_message", "Valid logo"),
                        now,
                    ),
                )

    def get_logo_asset(self, project_id: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM logo_assets WHERE project_id = ?", (project_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def delete_logo_asset(self, project_id: str) -> None:
        with self.get_connection() as conn:
            conn.execute("DELETE FROM logo_assets WHERE project_id = ?", (project_id,))

    # ------------------ Content Preservation Reports ------------------ #

    def save_validation_report(
        self,
        job_id: str,
        project_id: str,
        pre_metrics: Dict[str, Any],
        post_metrics: Dict[str, Any],
        is_preserved: bool = True,
        discrepancies: Optional[List[str]] = None,
    ) -> None:
        now = datetime.utcnow().isoformat()
        with self.get_connection() as conn:
            verb = "REPLACE INTO" if self.using_mysql else "INSERT OR REPLACE INTO"
            conn.execute(
                f"""
                {verb} validation_reports (
                    job_id, project_id, pre_metrics_json, post_metrics_json,
                    is_preserved, discrepancies_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job_id,
                    project_id,
                    json.dumps(pre_metrics),
                    json.dumps(post_metrics),
                    1 if is_preserved else 0,
                    json.dumps(discrepancies or []),
                    now,
                ),
            )

    def get_validation_report(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM validation_reports WHERE job_id = ?", (job_id,))
            row = cursor.fetchone()
            if not row:
                return None
            res = dict(row)
            res["is_preserved"] = bool(res.get("is_preserved"))
            res["pre_metrics"] = json.loads(res["pre_metrics_json"])
            res["post_metrics"] = json.loads(res["post_metrics_json"])
            res["discrepancies"] = json.loads(res["discrepancies_json"])
            return res

    # ------------------ Structured Audit Logs ------------------ #

    def log_audit_event(self, project_id: Optional[str], event_type: str, details: Dict[str, Any]) -> None:
        now = datetime.utcnow().isoformat()
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO audit_logs (project_id, event_type, details_json, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (project_id, event_type, json.dumps(details), now),
            )

    def get_audit_logs(self, project_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            if project_id:
                cursor = conn.execute(
                    "SELECT * FROM audit_logs WHERE project_id = ? ORDER BY id DESC LIMIT ?",
                    (project_id, limit),
                )
            else:
                cursor = conn.execute(
                    "SELECT * FROM audit_logs ORDER BY id DESC LIMIT ?", (limit,)
                )
            logs = []
            for r in cursor.fetchall():
                item = dict(r)
                try:
                    item["details"] = json.loads(item["details_json"])
                except Exception:
                    item["details"] = {}
                logs.append(item)
            return logs

    # ------------------ Diagnostic Information ------------------ #

    def get_engine_info(self) -> Dict[str, Any]:
        """Returns diagnostic metadata about the active storage engine."""
        if self.using_mysql:
            return {
                "engine": "MySQL",
                "connected": True,
                "host": self.mysql_host,
                "port": self.mysql_port,
                "database": self.mysql_db,
            }
        return {
            "engine": "SQLite",
            "wal_mode": True,
            "connected": True,
            "path": self.db_path,
        }
