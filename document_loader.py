import fitz
import re
import os

def load_documents(pdf_folder):

    all_chunks = []

    pdf_files = [

        file

        for file in os.listdir(pdf_folder)

        if file.lower().endswith(".pdf")

    ]

    print()

    print("=" * 60)
    print("DOCUMENT INFORMATION")
    print("=" * 60)

    print(f"Loaded Documents: {len(pdf_files)}")
    print()

    for pdf_name in pdf_files:

        print(pdf_name)

        pdf_path = os.path.join(
            pdf_folder,
            pdf_name
        )

        doc = fitz.open(pdf_path)

        text = ""

        for page in doc:

            text += page.get_text()

        doc.close()

        text = clean_text(text)

        chunks = chunk_text(text)

        for i, chunk in enumerate(chunks):

            all_chunks.append({

                "source": pdf_name,

                "chunk_id": i,

                "text": chunk

            })

    print()

    print(f"Total Chunks: {len(all_chunks)}")

    return all_chunks

def clean_text(text):

    # 修复单词断行
    text = re.sub(r'(\w)-\n(\w)', r'\1\2', text)

    # 换行转空格
    text = re.sub(r'\n+', ' ', text)

    # 多个空格压缩
    text = re.sub(r'\s+', ' ', text)

    return text.strip()

def chunk_text(text, chunk_size=1000, overlap=200):

    chunks = []

    start = 0

    text_length = len(text)

    while start < text_length:

        end = min(start + chunk_size, text_length)

        chunk = text[start:end]

        chunks.append(chunk.strip())

        start += chunk_size - overlap

    return chunks

def prepare_document(pdf_path):
    doc = fitz.open(pdf_path)

    text = ""

    for page in doc:
        text += page.get_text()

    doc.close()

    text = clean_text(text)

    chunks = chunk_text(text)

    return chunks


def show_chunk_preview(chunks):
    print()

    print("=" * 60)

    print("DOCUMENT INFORMATION")

    print("=" * 60)

    print(f"Total Chunks: {len(chunks)}")

    preview_num = min(3, len(chunks))

    for i in range(preview_num):
        print()

        print("-" * 60)

        print(f"Chunk {i + 1}")

        print("-" * 60)

        print(f"Source: {chunks[i]['source']}")

        print(f"Chunk ID: {chunks[i]['chunk_id']}")

        print()

        print(chunks[i]["text"][:300])

        print("...")
