import os
import json

PDF_FOLDER = "pdfs"
REGISTRY_FILE = "knowledge_registry.json"


def build_registry():
    """
    扫描知识库并生成注册表
    """

    registry = []

    if not os.path.exists(PDF_FOLDER):
        return registry

    pdf_files = [
        f for f in os.listdir(PDF_FOLDER)
        if f.endswith(".pdf")
    ]

    pdf_files.sort()

    for pdf in pdf_files:

        registry.append({
            "name": pdf,
            "status": "active"
        })

    with open(
        REGISTRY_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            registry,
            f,
            ensure_ascii=False,
            indent=2
        )

    return registry


def load_registry():
    """
    读取注册表
    """

    if not os.path.exists(REGISTRY_FILE):
        return build_registry()

    with open(
        REGISTRY_FILE,
        "r",
        encoding="utf-8"
    ) as f:

        return json.load(f)


def refresh_registry():
    """
    上传文件后刷新注册表
    """

    return build_registry()