from config import DOCUMENT_HINTS
def detect_documents(question):

    question_lower = question.lower()

    matched_sources = []

    for company, keywords in DOCUMENT_HINTS.items():

        matched = False

        for keyword in keywords:

            if keyword in question_lower:

                matched = True

                break

        if matched:

            matched_sources.append(company)

    return matched_sources

def show_document_detection(question):

    sources = detect_documents(question)

    print()

    print("=" * 60)

    print("DOCUMENT DETECTION")

    print("=" * 60)

    if sources:

        print()

        print("Matched Documents:")

        print()

        for i, source in enumerate(sources):
            print(

                f"{i + 1}. {source}"

            )

        print()

        print(

            f"Total Matched: {len(sources)}"

        )

    else:

        print()

        print("No document hint detected.")

        print("Using global retrieval.")

    print()

    return sources

def filter_chunks_by_source(
        chunks,
        matched_sources
):

    # 没匹配到文档

    if not matched_sources:

        print()

        print("Using all documents.")

        return chunks

    filtered_chunks = []

    for chunk in chunks:

        source_name = chunk["source"].lower()

        for company in matched_sources:

            if company.lower() in source_name:

                filtered_chunks.append(chunk)

                break

    print()

    print("=" * 60)

    print("DOCUMENT FILTER")

    print("=" * 60)

    print()

    print("Selected Documents:")

    for company in matched_sources:

        print(company)

    print()

    print(

        f"Filtered Chunks: {len(filtered_chunks)}"

    )
    company_count = {}

    for chunk in filtered_chunks:
        source = chunk["source"]

        company_count[source] = (

                company_count.get(source, 0)

                + 1

        )

    print()

    print("Chunk Distribution:")

    for company, count in company_count.items():
        print(

            f"{company}: {count}"

        )

    print()

    return filtered_chunks
def detect_research_mode(question):
    q = question.lower()
    RESEARCH_MODES = {

        "compare": [
            "compare",
            "comparison",
            "vs",
            "versus",
            "difference"
        ],

        "leader": [
            "stronger",
            "leader",
            "leading",
            "best",
            "largest",
            "dominant",
            "moat"
        ],

        "risk": [
            "risk",
            "challenge",
            "threat",
            "weakness"
        ],

        "growth": [
            "growth",
            "future",
            "opportunity",
            "expand"
        ],

        "investment": [
            "investment",
            "invest",
            "buy",
            "position",
            "outlook"
        ]

    }
    for mode, keywords in RESEARCH_MODES.items():
        for keyword in keywords:
            if keyword in q:
                return mode
    return "default"

def expand_research_sources(
        matched_sources,
        research_mode
):
    if research_mode == "default":

        return matched_sources
    if matched_sources:

        return matched_sources
    return list(
        DOCUMENT_HINTS.keys()
    )

def detect_compare_question(question):

    q = question.lower()

    compare_keywords = [
        "compare",
        "comparison",
        "vs",
        "versus",
        "difference",
        "better",
        "stronger",
        "weaker",
        "larger",
        "smaller",
        "advantage",
        "leading",
        "leader"

    ]

    for word in compare_keywords:

        if word in q:

            return True

    return False
