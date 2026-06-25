import os
import json
from pathlib import Path

from config import PDF_DIR

PDF_DIR = Path("pdfs")

PDF_FOLDER = "pdfs"
REGISTRY_FILE = "knowledge_registry.json"

def get_documents():
    """
    返回知识库所有 PDF 文件
    """
    if not PDF_DIR.exists():
        return []

    return sorted(
        [
            pdf.name
            for pdf in PDF_DIR.glob("*.pdf")
        ]
    )


def get_document_count():
    """
    返回 PDF 数量
    """
    return len(get_documents())


def refresh_registry():
    """
    当前版本直接刷新文件列表
    后续可扩展 JSON Registry
    """
    return get_documents()