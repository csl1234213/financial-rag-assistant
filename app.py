from dotenv import load_dotenv
from document_loader import (
    load_documents, show_chunk_preview
)
from embedding import (
    load_embedding_model,
    get_embeddings,
    embed_chunks
)
from retriever import (
    retrieve_evidence,
    retrieve_multi_document,
    extract_local_context,
)
from research_mode import (
    detect_research_mode,
    show_document_detection,
    expand_research_sources,
    filter_chunks_by_source,
)
from prompt_builder import (
    build_prompt,
    build_compare_prompt,
)
from llm_client import generate_answer
from config import DEBUG_MODE, DOCUMENT_HINTS

load_dotenv()

def build_context(
    chunks,
    top_k,
    scores,
    question
):

    context = ""

    citations = []

    for rank, idx in enumerate(top_k):

        score = scores[idx].item()

        local_context = extract_local_context(
            chunks[idx]["text"],
            question
        )

        citations.append({

            "rank": rank + 1,

            "source": chunks[idx]["source"],

            "chunk_id": chunks[idx]["chunk_id"],

            "similarity": round(score, 4),

            "preview": local_context[:150]

        })

        context += "=" * 60 + "\n"
        context += f"Evidence {rank + 1}\n"
        context += f"Source: {chunks[idx]['source']}\n"
        context += f"Chunk ID: {chunks[idx]['chunk_id']}\n"
        context += f"Similarity Score: {score:.4f}\n"
        context += "=" * 60 + "\n"

        context += local_context
        context += "\n\n"

    return context, citations



def display_citations(citations):

    print()

    print("=" * 60)

    print("EVIDENCE CITATIONS")

    print("=" * 60)

    print()

    for item in citations:

        print(

            f"Evidence {item['rank']}"

        )

        print(

            f"Source: {item['source']}"

        )

        print(

            f"Chunk ID: {item['chunk_id']}"

        )

        print(

            f"Similarity: {item['similarity']}"

        )

        print(

            "Preview:"
        )

        print(

            item["preview"]

        )

        print()

        print("-" * 60)


def get_user_question():

    print()

    question = input(

        "Ask a question (type 'exit' to quit):\n> "

    )

    return question


def display_result(answer):

    print()

    print("=" * 60)

    print("FINANCIAL ANALYSIS")

    print("=" * 60)

    print()

    print(answer)

    print()

    print("=" * 60)


if __name__ == "__main__":

    pdf_folder="pdfs/"

    chunks = load_documents(
        pdf_folder
    )

    show_chunk_preview(
        chunks
    )

    model = load_embedding_model()

    embeddings = get_embeddings(

        model,

        chunks,

        pdf_folder

    )

    while True:

        question = get_user_question()

        if question.lower() in [

            "exit",

            "quit",

            "q"

        ]:
            print()

            print("Exiting Financial RAG...")

            break

        research_mode = detect_research_mode(
            question
        )

        matched_sources = show_document_detection(
            question
        )

        matched_sources = expand_research_sources(

            matched_sources,

            research_mode

        )

        print()

        print(

            f"Research Mode: {research_mode}"

        )

        print(

            f"Research Sources: {matched_sources}"

        )

        filtered_chunks = filter_chunks_by_source(

            chunks,

            matched_sources

        )

        filtered_embeddings = embed_chunks(model, filtered_chunks)

        if len(matched_sources) > 1:
            multi_results = retrieve_multi_document(
                matched_sources,
                filtered_chunks,
                model,
                question
            )
            top_k = []
            score_values = []
            selected_chunks = []
            for item in multi_results:
                selected_chunks.append(item["chunk"])
                score_values.append(item["score"])
                top_k.append(len(selected_chunks)-1)
            import torch
            scores = torch.tensor(score_values)
            context, citations = build_context(
                selected_chunks,
                top_k,
                scores,
                question
            )
        else:
            top_k, scores = retrieve_evidence(
                model,
                filtered_embeddings,
                question
            )
            context, citations = build_context(
                filtered_chunks,
                top_k,
                scores,
                question
            )

        display_citations(
            citations
        )

        if research_mode == "compare":

            prompt = build_compare_prompt(
                question,
                context
            )

        elif research_mode == "leader":

            prompt = build_compare_prompt(
                question,
                context
            )

        else:

            prompt = build_prompt(
                question,
                context
            )

        if DEBUG_MODE:

            print()

            print("=" * 60)

            print("DEBUG MODE")

            print("=" * 60)

            print(prompt)

        else:

            answer = generate_answer(
                prompt
            )

            display_result(
                answer
            )