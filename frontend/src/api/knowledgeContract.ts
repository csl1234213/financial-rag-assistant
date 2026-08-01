import type { KnowledgeDocument } from '../types/knowledge';

export const MAX_PDF_UPLOAD_BYTES = 50 * 1024 * 1024;

export type PdfUploadValidationIssue = 'invalid-type' | 'too-large';

interface PdfUploadCandidate {
  name: string;
  size: number;
}

export function validatePdfUpload(
  file: PdfUploadCandidate,
): PdfUploadValidationIssue | null {
  if (!file.name.trim().toLowerCase().endsWith('.pdf')) {
    return 'invalid-type';
  }
  if (file.size > MAX_PDF_UPLOAD_BYTES) {
    return 'too-large';
  }
  return null;
}

export function isKnowledgeRecord(
  value: unknown,
): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

export function formatByteSize(byteSize: number): string {
  if (byteSize < 1024) return `${byteSize} B`;
  if (byteSize < 1024 * 1024) {
    return `${(byteSize / 1024).toFixed(1)} KB`;
  }
  return `${(byteSize / (1024 * 1024)).toFixed(1)} MB`;
}

function mapFilename(filename: string): KnowledgeDocument {
  const normalized = filename.toLowerCase();
  const company = normalized.includes('tesla')
    ? 'Tesla'
    : normalized.includes('nvidia')
      ? 'NVIDIA'
      : normalized.includes('apple')
        ? 'Apple'
        : 'Unknown';

  return {
    id: filename,
    filename,
    company,
    status: 'indexed',
    pages: 0,
    uploadedAt: '',
    canDelete: false,
  };
}

export function mapKnowledgeDocument(
  value: unknown,
): KnowledgeDocument | null {
  if (typeof value === 'string') {
    return mapFilename(value);
  }
  if (
    !isKnowledgeRecord(value)
    || typeof value.filename !== 'string'
  ) {
    return null;
  }

  const status = value.status === 'processing' || value.status === 'failed'
    ? value.status
    : 'indexed';
  const byteSize = typeof value.byte_size === 'number'
    ? value.byte_size
    : typeof value.byteSize === 'number'
      ? value.byteSize
      : undefined;
  const contentSha256 = typeof value.content_sha256 === 'string'
    ? value.content_sha256
    : typeof value.contentSha256 === 'string'
      ? value.contentSha256
      : undefined;

  return {
    id: String(value.id ?? value.filename),
    filename: value.filename,
    company: typeof value.company === 'string' ? value.company : 'Unknown',
    period: typeof value.period === 'string' ? value.period : undefined,
    status,
    pages: typeof value.pages === 'number' ? value.pages : 0,
    byteSize,
    size: byteSize === undefined ? undefined : formatByteSize(byteSize),
    chunkCount: typeof value.chunk_count === 'number'
      ? value.chunk_count
      : typeof value.chunkCount === 'number'
        ? value.chunkCount
        : 0,
    contentSha256,
    canDelete: value.can_delete === true || value.canDelete === true,
    uploadedAt: typeof value.uploaded_at === 'string'
      ? value.uploaded_at
      : typeof value.uploadedAt === 'string'
        ? value.uploadedAt
        : '',
  };
}
