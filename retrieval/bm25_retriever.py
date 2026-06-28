from rank_bm25 import BM25Okapi


def build_bm25(chunks):

    corpus = [
        chunk["text"].split()
        for chunk in chunks
    ]

    return BM25Okapi(corpus)


def bm25_search(
        bm25,
        query,
        chunks,
        top_k=5
):

    scores = bm25.get_scores(
        query.split()
    )

    ranked = [

        (chunk, score)

        for chunk, score

        in zip(chunks, scores)

        if score > 0

    ]
    ranked.sort(
        key=lambda x: x[1],
        reverse=True
    )

    return [
        item[0]
        for item in ranked[:top_k]
    ]
