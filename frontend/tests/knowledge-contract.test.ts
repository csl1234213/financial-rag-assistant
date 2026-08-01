import assert from 'node:assert/strict';
import test from 'node:test';

import {
  formatByteSize,
  MAX_PDF_UPLOAD_BYTES,
  mapKnowledgeDocument,
  validatePdfUpload,
} from '../src/api/knowledgeContract.ts';

test('maps stable knowledge item fields from the backend contract', () => {
  const document = mapKnowledgeDocument({
    id: 42,
    filename: 'Tesla_Q2_2025.pdf',
    company: 'Tesla',
    period: 'Q2_2025',
    status: 'indexed',
    chunk_count: 63,
    byte_size: 2_621_440,
    content_sha256: 'a'.repeat(64),
    uploaded_at: '2026-07-29T12:00:00Z',
    can_delete: true,
  });

  assert.deepEqual(document, {
    id: '42',
    filename: 'Tesla_Q2_2025.pdf',
    company: 'Tesla',
    period: 'Q2_2025',
    status: 'indexed',
    pages: 0,
    chunkCount: 63,
    byteSize: 2_621_440,
    size: '2.5 MB',
    contentSha256: 'a'.repeat(64),
    uploadedAt: '2026-07-29T12:00:00Z',
    canDelete: true,
  });
});

test('legacy filename responses remain readable but are never deletable', () => {
  assert.deepEqual(mapKnowledgeDocument('NVIDIA.pdf'), {
    id: 'NVIDIA.pdf',
    filename: 'NVIDIA.pdf',
    company: 'NVIDIA',
    status: 'indexed',
    pages: 0,
    uploadedAt: '',
    canDelete: false,
  });
});

test('formats document byte sizes without losing small-file visibility', () => {
  assert.equal(formatByteSize(124), '124 B');
  assert.equal(formatByteSize(1536), '1.5 KB');
  assert.equal(formatByteSize(2_621_440), '2.5 MB');
});

test('accepts PDF filenames at the 50 MB upload boundary', () => {
  assert.equal(
    validatePdfUpload({
      name: 'Quarterly Report.PDF',
      size: MAX_PDF_UPLOAD_BYTES,
    }),
    null,
  );
});

test('rejects non-PDF files before upload', () => {
  assert.equal(
    validatePdfUpload({ name: 'financials.xlsx', size: 1024 }),
    'invalid-type',
  );
});

test('rejects PDFs larger than the backend upload limit', () => {
  assert.equal(
    validatePdfUpload({
      name: 'annual-report.pdf',
      size: MAX_PDF_UPLOAD_BYTES + 1,
    }),
    'too-large',
  );
});
