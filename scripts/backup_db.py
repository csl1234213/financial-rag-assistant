import argparse
import gzip
import logging
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("backup")


def backup_postgresql(
    db_url: str,
    output_dir: str,
    compress: bool = True,
) -> str:
    from urllib.parse import urlparse

    parsed = urlparse(db_url)

    db_name = parsed.path.lstrip("/")
    db_user = parsed.username or "postgres"
    db_host = parsed.hostname or "localhost"
    db_port = parsed.port or 5432
    db_password = parsed.password or ""

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"backup_{db_name}_{timestamp}.sql"
    if compress:
        filename += ".gz"
    filepath = os.path.join(output_dir, filename)

    os.makedirs(output_dir, exist_ok=True)

    env = os.environ.copy()
    env["PGPASSWORD"] = db_password

    cmd = [
        "pg_dump",
        "-h", db_host,
        "-p", str(db_port),
        "-U", db_user,
        "-d", db_name,
        "--no-owner",
        "--no-acl",
    ]

    if compress:
        with gzip.open(filepath, "wb") as f:
            proc = subprocess.run(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if proc.returncode != 0:
                logger.error(f"pg_dump failed: {proc.stderr.decode()}")
                return ""
            f.write(proc.stdout)
    else:
        with open(filepath, "wb") as f:
            proc = subprocess.run(cmd, env=env, stdout=f, stderr=subprocess.PIPE)
            if proc.returncode != 0:
                logger.error(f"pg_dump failed: {proc.stderr.decode()}")
                return ""

    size_mb = round(os.path.getsize(filepath) / (1024 * 1024), 2)
    logger.info(f"Backup created: {filepath} ({size_mb} MB)")
    return filepath


def backup_sqlite(db_path: str, output_dir: str, compress: bool = True) -> str:
    if not os.path.exists(db_path):
        logger.error(f"SQLite database not found: {db_path}")
        return ""

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    db_name = Path(db_path).stem
    filename = f"backup_{db_name}_{timestamp}.db"
    if compress:
        filename += ".gz"
    filepath = os.path.join(output_dir, filename)

    os.makedirs(output_dir, exist_ok=True)

    if compress:
        with open(db_path, "rb") as src, gzip.open(filepath, "wb") as dst:
            shutil.copyfileobj(src, dst)
    else:
        shutil.copy2(db_path, filepath)

    size_mb = round(os.path.getsize(filepath) / (1024 * 1024), 2)
    logger.info(f"Backup created: {filepath} ({size_mb} MB)")
    return filepath


def backup_chromadb(chroma_path: str, output_dir: str) -> str:
    if not os.path.exists(chroma_path):
        logger.error(f"ChromaDB path not found: {chroma_path}")
        return ""

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"backup_chroma_{timestamp}.tar.gz"
    filepath = os.path.join(output_dir, filename)

    os.makedirs(output_dir, exist_ok=True)

    import tarfile

    with tarfile.open(filepath, "w:gz") as tar:
        tar.add(chroma_path, arcname=os.path.basename(chroma_path))

    size_mb = round(os.path.getsize(filepath) / (1024 * 1024), 2)
    logger.info(f"Backup created: {filepath} ({size_mb} MB)")
    return filepath


def cleanup_old_backups(output_dir: str, keep_days: int = 7):
    if not os.path.exists(output_dir):
        return

    cutoff = datetime.now(timezone.utc).timestamp() - keep_days * 86400
    removed = 0
    for fname in os.listdir(output_dir):
        fpath = os.path.join(output_dir, fname)
        if os.path.isfile(fpath) and os.path.getmtime(fpath) < cutoff:
            os.remove(fpath)
            removed += 1
            logger.info(f"Removed old backup: {fname}")

    logger.info(f"Cleanup complete: {removed} old backups removed")


def main():
    parser = argparse.ArgumentParser(description="Financial RAG Database Backup")
    parser.add_argument("--db-url", default=os.getenv("DATABASE_URL", ""), help="Database URL")
    parser.add_argument("--chroma-path", default=os.getenv("CHROMA_PATH", "chroma_db"), help="ChromaDB path")
    parser.add_argument("--output-dir", default=os.getenv("BACKUP_DIR", "backup"), help="Backup output directory")
    parser.add_argument("--no-compress", action="store_true", help="Disable compression")
    parser.add_argument("--keep-days", type=int, default=7, help="Days to keep backups")
    parser.add_argument("--no-cleanup", action="store_true", help="Skip cleanup of old backups")
    args = parser.parse_args()

    compress = not args.no_compress
    result = {"status": "ok", "files": []}

    if args.db_url:
        if args.db_url.startswith("postgresql://"):
            filepath = backup_postgresql(args.db_url, args.output_dir, compress)
        elif args.db_url.startswith("sqlite://"):
            db_path = args.db_url.replace("sqlite:///", "")
            if not os.path.isabs(db_path):
                db_path = os.path.join(os.getcwd(), db_path)
            filepath = backup_sqlite(db_path, args.output_dir, compress)
        else:
            logger.error(f"Unsupported database URL: {args.db_url}")
            sys.exit(1)

        if filepath:
            result["files"].append(filepath)
        else:
            result["status"] = "failed"

    if args.chroma_path and os.path.exists(args.chroma_path):
        filepath = backup_chromadb(args.chroma_path, args.output_dir)
        if filepath:
            result["files"].append(filepath)

    if not args.no_cleanup:
        cleanup_old_backups(args.output_dir, args.keep_days)

    logger.info(f"Backup complete: {result}")
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())