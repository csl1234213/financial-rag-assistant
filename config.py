DEBUG_MODE = False
DOCUMENT_HINTS = {

    "Tesla": [
        "tesla",
        "robotaxi",
        "cybercab",
        "optimus",
        "fsd",
        "supercharger",
        "megapack"

    ],

    "NVIDIA": [
        "nvidia",
        "blackwell",
        "cuda",
        "dgx",
        "nvlink",
        "ai factory",
        "grace",
        "hopper"

    ],

    "Apple": [
        "apple",
        "apple intelligence",
        "vision pro",
        "iphone",
        "ipad",
        "mac",
        "services",
        "app store"

    ]

}
CACHE_DIR = "cache"

PDF_DIR = "pdfs"

TOP_K = 4

EMBEDDING_MODEL = "all-MiniLM-L6-v2"

CACHE_VERSION = "1.8"

CHUNK_SIZE = 1000

CHUNK_OVERLAP = 200

LLM_TEMPERATURE = 0.2

LLM_MAX_TOKENS = 1000

MAX_HISTORY = 3

PROMPT_RULES = """
Rules:

1. Use ONLY the provided context.
2. If evidence is insufficient, say so clearly.
3. Do NOT invent facts.
4. Cite supporting evidence whenever possible.
5. Keep answers concise and professional.
6. Focus on financial analysis.
"""