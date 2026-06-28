import os

import torch
from sentence_transformers import SentenceTransformer

CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)






def get_cache_path(

        pdf_folder

):
    cache_name = os.path.basename(pdf_folder)

    if not cache_name:
        cache_name = "all_documents"

    return os.path.join(
        CACHE_DIR,
        f"{cache_name}.pt"
    )



def save_embeddings(path, data):

    import os

    import torch

    os.makedirs(
        os.path.dirname(path),
        exist_ok=True
    )

    torch.save(
        data,
        path
    )

    print()

    print("Embeddings cached.")

    print(
        f"Saved to: {path}"
    )

    try:

        print(

            f"Size: {len(data)}"

        )

    except Exception:

        pass

def load_cached_embeddings(

        cache_path

):

    if os.path.exists(

        cache_path

    ):

        print()

        print(

            "Loading cached embeddings..."

        )
        print(
            f"Cache: {cache_path}"
        )

        return torch.load(

            cache_path

        )

    return None

def get_embeddings(

        model,

        chunks,

        pdf_folder

):



    cache_path = get_cache_path(

        pdf_folder

    )

    embeddings = load_cached_embeddings(

        cache_path

    )

    if embeddings is not None:

        return embeddings

    embeddings = embed_chunks(

        model,

        chunks

    )

    save_embeddings(
        cache_path,
        embeddings
    )
    return embeddings

def load_embedding_model( ):
    # 修复单词换行

    print()

    print("Loading embedding model...")

    model = SentenceTransformer(

        "all-MiniLM-L6-v2"

    )

    print("Embedding model loaded!")

    return model

def embed_chunks(model, chunks):
    print()

    print("Generating embeddings...")

    texts = [
        chunk["text"]
        for chunk in chunks
    ]

    embeddings = model.encode(
        texts,
        convert_to_tensor=True
    )

    print("Embeddings generated!")

    print(f"Total Embeddings: {len(embeddings)}")

    print(f"Embedding Dimension: {embeddings.shape[1]}")

    return embeddings
