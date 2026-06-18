from sentence_transformers import SentenceTransformer
import os
import torch

def get_cache_path(

        pdf_folder

):

    cache_name = pdf_folder.replace(

        "/",

        "_"

    )

    return f"cache/{cache_name}.pt"

def save_embeddings(

        embeddings,

        cache_path

):

    torch.save(

        embeddings,

        cache_path

    )

    print()

    print(

        "Embeddings cached."

    )

    print(

        cache_path

    )

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

        embeddings,

        cache_path

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
