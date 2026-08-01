from __future__ import annotations

import fitz
import pytest

import document_loader
from document_loader import (
    DocumentProcessingError,
    ParsedBlock,
    ParsedDocument,
    ParsedPage,
    chunk_document,
    load_pdf_chunks,
    parse_pdf,
)


def _write_text_pdf(path) -> None:
    with fitz.open() as pdf:
        first = pdf.new_page()
        first.insert_text((72, 72), "Revenue Overview", fontsize=16)
        first.insert_text(
            (72, 160),
            "Tesla automotive revenue increased during the quarter.",
        )
        second = pdf.new_page()
        second.insert_text((72, 72), "Risk Factors", fontsize=16)
        second.insert_text(
            (72, 160),
            "Supply chain constraints remain a material risk.",
        )
        pdf.save(path)


@pytest.mark.unit
def test_parse_pdf_preserves_sorted_page_and_section_provenance(tmp_path):
    pdf_path = tmp_path / "Tesla_Q2_2025.pdf"
    _write_text_pdf(pdf_path)

    parsed = parse_pdf(pdf_path, ocr_enabled=False)

    assert parsed.parser_version == "pymupdf-blocks-ocr-v3"
    assert [page.number for page in parsed.pages] == [1, 2]
    assert [block.text for block in parsed.pages[0].blocks] == [
        "Revenue Overview",
        "Tesla automotive revenue increased during the quarter.",
    ]
    assert parsed.pages[0].blocks[1].section == "Revenue Overview"
    assert parsed.pages[1].blocks[1].section == "Risk Factors"
    assert not any(page.ocr_used for page in parsed.pages)


@pytest.mark.unit
@pytest.mark.parametrize(
    "table_cell",
    [
        "2Q-2025",
        "March 28,",
        "Revenue",
        "$12.4",
        "2025",
    ],
)
def test_table_cells_are_not_misclassified_as_headings(table_cell):
    assert not document_loader._looks_like_heading(
        table_cell,
        table_cell,
    )


@pytest.mark.unit
def test_real_multiword_title_remains_a_heading():
    assert document_loader._looks_like_heading(
        "Revenue Overview",
        "Revenue Overview",
    )


@pytest.mark.unit
def test_chunk_document_keeps_page_and_section_boundaries():
    document = ParsedDocument(
        filename="report.pdf",
        pages=(
            ParsedPage(
                number=1,
                ocr_used=False,
                blocks=(
                    ParsedBlock(
                        text="Revenue Overview",
                        page=1,
                        section="Revenue Overview",
                        ocr_used=False,
                        is_heading=True,
                    ),
                    ParsedBlock(
                        text="Revenue increased by ten percent.",
                        page=1,
                        section="Revenue Overview",
                        ocr_used=False,
                    ),
                ),
            ),
            ParsedPage(
                number=2,
                ocr_used=True,
                blocks=(
                    ParsedBlock(
                        text="Risk Factors",
                        page=2,
                        section="Risk Factors",
                        ocr_used=True,
                        is_heading=True,
                    ),
                    ParsedBlock(
                        text="Supply chain constraints remain material.",
                        page=2,
                        section="Risk Factors",
                        ocr_used=True,
                    ),
                ),
            ),
        ),
    )

    chunks = chunk_document(document, chunk_size=100, overlap=10)

    assert [chunk.page for chunk in chunks] == [1, 2]
    assert [chunk.section for chunk in chunks] == [
        "Revenue Overview",
        "Risk Factors",
    ]
    assert [chunk.ocr_used for chunk in chunks] == [False, True]
    assert "Risk Factors" not in chunks[0].text
    assert "Revenue Overview" not in chunks[1].text


@pytest.mark.unit
def test_chunk_document_merges_heading_only_and_tiny_same_page_chunks():
    document = ParsedDocument(
        filename="table-report.pdf",
        pages=(
            ParsedPage(
                number=1,
                ocr_used=False,
                blocks=(
                    ParsedBlock(
                        text="Revenue Overview",
                        page=1,
                        section="Revenue Overview",
                        ocr_used=False,
                        is_heading=True,
                    ),
                    ParsedBlock(
                        text="Risk Factors",
                        page=1,
                        section="Risk Factors",
                        ocr_used=False,
                        is_heading=True,
                    ),
                    ParsedBlock(
                        text="Supply constraints remain material.",
                        page=1,
                        section="Risk Factors",
                        ocr_used=False,
                    ),
                ),
            ),
        ),
    )

    chunks = chunk_document(document, chunk_size=200, overlap=20)

    assert len(chunks) == 1
    assert "Revenue Overview" in chunks[0].text
    assert "Risk Factors" in chunks[0].text
    assert "Supply constraints remain material." in chunks[0].text
    assert chunks[0].section == "Risk Factors"


@pytest.mark.unit
def test_chunk_document_removes_duplicate_normalized_content():
    repeated_text = "Tesla automotive revenue increased year over year."
    document = ParsedDocument(
        filename="duplicate-report.pdf",
        pages=(
            ParsedPage(
                number=1,
                ocr_used=False,
                blocks=(
                    ParsedBlock(
                        text=repeated_text,
                        page=1,
                        section="Page 1",
                        ocr_used=False,
                    ),
                ),
            ),
            ParsedPage(
                number=2,
                ocr_used=False,
                blocks=(
                    ParsedBlock(
                        text="  TESLA   AUTOMOTIVE REVENUE increased year over year. ",
                        page=2,
                        section="Page 2",
                        ocr_used=False,
                    ),
                ),
            ),
        ),
    )

    chunks = chunk_document(document, chunk_size=200, overlap=20)

    assert len(chunks) == 1
    assert chunks[0].page == 1


@pytest.mark.unit
def test_low_text_page_uses_ocr_and_marks_chunk_provenance(
    monkeypatch,
    tmp_path,
):
    pdf_path = tmp_path / "scan.pdf"
    with fitz.open() as pdf:
        pdf.new_page()
        pdf.save(pdf_path)

    ocr_calls: list[tuple[int, str, int]] = []

    def fake_ocr(_page, *, page_number, languages, dpi):
        ocr_calls.append((page_number, languages, dpi))
        return [
            "Revenue Overview",
            "OCR recovered multilingual revenue evidence.",
        ]

    monkeypatch.setattr(document_loader, "_extract_ocr_blocks", fake_ocr)

    chunks = load_pdf_chunks(
        pdf_path,
        ocr_enabled=True,
        ocr_languages="eng+chi_sim",
        ocr_dpi=300,
        ocr_min_text_chars=20,
    )

    assert ocr_calls == [(1, "eng+chi_sim", 300)]
    assert chunks[0].page == 1
    assert chunks[0].section == "Revenue Overview"
    assert chunks[0].ocr_used is True


@pytest.mark.unit
@pytest.mark.parametrize(
    "ocr_text",
    [
        (
            "Tesla automotive revenue increased during the quarter, "
            "while operating margin remained stable."
        ),
        "财 务 报 告 显 示 公 司 营 收 和 利 润 持 续 稳 定 增 长",
        (
            "2025 年 Tesla 营 收 增 长 remained strong, with revenue "
            "reaching USD 25.5 billion."
        ),
        "2Q-2025",
        "$12.4",
        "(18.6%)",
        (
            "TESLA SEMI - MEGACHARGER NETWORK PLANNED SITES FOR 2026 "
            "VANCOUVER SEATTLE TACOMA PORTLAND RENO MODESTO "
            "LOS ANGELES PHOENIX"
        ),
    ],
)
def test_ocr_quality_gate_preserves_useful_english_chinese_and_financial_text(
    ocr_text,
):
    assert document_loader._is_usable_ocr_block(ocr_text)


@pytest.mark.unit
@pytest.mark.parametrize(
    "ocr_text",
    [
        "|||| |||| ---- ____ <<<< >>>>",
        "\ufffd\ufffd\ufffd broken OCR text",
        "llllllllllllllllllllllllllllllllllllllll",
        "l I l I l I l I l I l I l I l I l I l I",
        (
            "TESLA SEMI 一 本 有 7 ‘ =. —_— << = son 1 一一 ad — = , "
            "| er| |) me ty | ras | | 外 — | \\"
        ),
        (
            "GIGAFACTORY SHANGHAI - 9 MILLIONTH VEHICLE PRODUCED "
            "(GLOBALLY) - "
            + " | i SS oes ee aye ee — ) | 二) 二 o> Lars | a| 1 em)! "
            * 8
        ),
        (
            "NEXT GENERATION VEHICLE PLATFORM "
            + "= ns! zor2 J 多 3 — es » * 第 一 a | n | 2 | x | "
            * 8
        ),
    ],
)
def test_ocr_quality_gate_rejects_image_derived_character_noise(ocr_text):
    assert not document_loader._is_usable_ocr_block(ocr_text)


@pytest.mark.unit
def test_ocr_quality_gate_filters_only_unusable_blocks():
    useful = (
        "Revenue increased year over year based on the scanned report. "
        "Operating income and free cash flow also improved during the quarter."
    )
    noise = "l | I | l | I | l | I | l | I | l | I | l | I |"

    assert document_loader._filter_ocr_blocks([noise, useful]) == [useful]


@pytest.mark.unit
def test_ocr_quality_gate_rejects_noise_split_across_small_blocks():
    blocks = [
        "TESLA SEMI -—-",
        "_ P Ee 4",
        '= ‘| > =" = ‘ae NG ~ 人',
        '| ”有 | n ,',
        "| fy ‘ iq lf ) on oie . | ) me. oO} ip",
        "| at —",
        "\\",
    ]

    assert document_loader._filter_ocr_blocks(blocks) == []


@pytest.mark.unit
def test_ocr_quality_gate_rechecks_filtered_blocks_as_one_page():
    heading = "GIGAFACTORY SHANGHAI - 9 MILLIONTH VEHICLE PRODUCED"
    fragment = "NA Fx a ie oe ae i vere al x noise"
    blocks = [heading, *([fragment] * 12)]

    assert document_loader._is_usable_ocr_block(fragment)
    assert document_loader._filter_ocr_blocks(blocks) == []


@pytest.mark.unit
def test_ocr_quality_gate_preserves_long_coherent_english_page():
    paragraph = (
        "Revenue increased year over year, supported by automotive sales, "
        "energy generation, storage deployments, and services. "
    )
    page_text = paragraph * 3

    assert len(page_text) >= 200
    assert document_loader._is_usable_ocr_block(page_text)
    assert document_loader._filter_ocr_blocks([page_text]) == [page_text]


@pytest.mark.unit
def test_rejected_ocr_falls_back_to_native_page_text(monkeypatch, tmp_path):
    pdf_path = tmp_path / "native-fallback.pdf"
    with fitz.open() as pdf:
        pdf.new_page()
        pdf.save(pdf_path)

    monkeypatch.setattr(
        document_loader,
        "_extract_text_blocks",
        lambda _page: ["Short native financial note retained."],
    )
    monkeypatch.setattr(
        document_loader,
        "_extract_ocr_blocks",
        lambda _page, **_kwargs: [
            "l | I | l | I | l | I | l | I | l | I | l | I |"
        ],
    )

    parsed = parse_pdf(
        pdf_path,
        ocr_enabled=True,
        ocr_min_text_chars=80,
    )

    assert [block.text for block in parsed.pages[0].blocks] == [
        "Short native financial note retained."
    ]
    assert parsed.pages[0].ocr_used is False
    assert parsed.pages[0].blocks[0].ocr_used is False


@pytest.mark.unit
def test_rejected_ocr_on_image_only_pdf_produces_no_content(
    monkeypatch,
    tmp_path,
):
    pdf_path = tmp_path / "image-only.pdf"
    with fitz.open() as pdf:
        pdf.new_page()
        pdf.save(pdf_path)

    monkeypatch.setattr(
        document_loader,
        "_extract_ocr_blocks",
        lambda _page, **_kwargs: ["|||| ---- ____ <<<< >>>>"],
    )

    with pytest.raises(
        DocumentProcessingError,
        match="PDF contains no extractable text",
    ):
        parse_pdf(
            pdf_path,
            ocr_enabled=True,
            ocr_min_text_chars=80,
        )


@pytest.mark.unit
def test_ocr_runtime_failure_has_page_and_language_context():
    class BrokenPage:
        def get_textpage_ocr(self, **_kwargs):
            raise RuntimeError("tesseract data unavailable")

    with pytest.raises(
        DocumentProcessingError,
        match=r"OCR failed on page 3.*eng\+chi_sim.*tesseract data unavailable",
    ):
        document_loader._extract_ocr_blocks(
            BrokenPage(),
            page_number=3,
            languages="eng+chi_sim",
            dpi=300,
        )
