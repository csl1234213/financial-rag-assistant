import { useState, useRef, type DragEvent } from 'react';

type UploadStatus = 'idle' | 'uploading' | 'success' | 'error';

interface UploadPanelProps {
  onUploadSuccess?: (file: File) => Promise<void>;
}

const uploadLabels: Record<UploadStatus, string> = {
  idle: 'Drag & drop a PDF here, or click to browse',
  uploading: 'Uploading...',
  success: 'Upload complete!',
  error: 'Upload failed. Please try again.',
};

const uploadButtonLabels: Record<UploadStatus, string> = {
  idle: 'Choose File',
  uploading: 'Uploading\u2026',
  success: 'Upload Another',
  error: 'Retry',
};

export function UploadPanel({ onUploadSuccess }: UploadPanelProps) {
  const [dragOver, setDragOver] = useState(false);
  const [uploadStatus, setUploadStatus] = useState<UploadStatus>('idle');
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const doUpload = async (file: File) => {
    setSelectedFile(file.name);
    setUploadStatus('uploading');
    setUploadError(null);

    if (onUploadSuccess) {
      try {
        await onUploadSuccess(file);
        setUploadStatus('success');
      } catch (err: unknown) {
        setUploadStatus('error');
        const message = err instanceof Error ? err.message : 'Upload failed.';
        setUploadError(message);
      }
    } else {
      setTimeout(() => setUploadStatus('success'), 1500);
    }
  };

  const handleDragOver = (e: DragEvent) => {
    e.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = (e: DragEvent) => {
    e.preventDefault();
    setDragOver(false);
  };

  const handleDrop = (e: DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) {
      doUpload(file);
    }
  };

  const handleFileSelect = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      doUpload(file);
    }
  };

  const handleReset = () => {
    setUploadStatus('idle');
    setSelectedFile(null);
    setUploadError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <section className="upload-panel" aria-labelledby="upload-title">
      <h2 id="upload-title" className="upload-panel__title">
        Upload Document
      </h2>

      <div
        className={`upload-panel__dropzone ${dragOver ? 'upload-panel__dropzone--drag-over' : ''} upload-panel__dropzone--${uploadStatus}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={uploadStatus === 'idle' || uploadStatus === 'error' ? handleFileSelect : undefined}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            handleFileSelect();
          }
        }}
        aria-label="Upload PDF document"
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf"
          className="upload-panel__file-input"
          onChange={handleFileChange}
          aria-hidden="true"
        />

        <span className="upload-panel__dropzone-icon" aria-hidden="true">
          {uploadStatus === 'uploading' ? '\u21BB' : uploadStatus === 'success' ? '\u2713' : '\u2913'}
        </span>

        <p className="upload-panel__dropzone-text">
          {selectedFile && uploadStatus !== 'idle' ? selectedFile : uploadLabels[uploadStatus]}
        </p>

        {uploadStatus === 'idle' && (
          <span className="upload-panel__dropzone-hint">PDF files only, up to 50 MB</span>
        )}
      </div>

      {uploadError && (
        <p className="upload-panel__error" role="alert">
          <span className="upload-panel__error-icon" aria-hidden="true">&#x26A0;</span>
          {uploadError}
        </p>
      )}

      <div className="upload-panel__actions">
        {uploadStatus === 'idle' && (
          <button
            type="button"
            className="upload-panel__button"
            onClick={handleFileSelect}
          >
            {uploadButtonLabels.idle}
          </button>
        )}

        {uploadStatus === 'uploading' && (
          <button type="button" className="upload-panel__button upload-panel__button--disabled" disabled>
            {uploadButtonLabels.uploading}
          </button>
        )}

        {uploadStatus === 'success' && (
          <button type="button" className="upload-panel__button" onClick={handleReset}>
            {uploadButtonLabels.success}
          </button>
        )}

        {uploadStatus === 'error' && (
          <button type="button" className="upload-panel__button" onClick={handleReset}>
            {uploadButtonLabels.error}
          </button>
        )}
      </div>
    </section>
  );
}