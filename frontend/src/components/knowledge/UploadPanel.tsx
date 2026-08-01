import { useState, useRef, type DragEvent } from 'react';
import { useLanguage } from '../../i18n/LanguageContext';
import { validatePdfUpload } from '../../api/knowledgeContract';

type UploadStatus = 'idle' | 'uploading' | 'success' | 'error';

interface UploadPanelProps {
  onUploadSuccess?: (file: File) => Promise<void>;
}

export function UploadPanel({ onUploadSuccess }: UploadPanelProps) {
  const { t } = useLanguage();
  const [dragOver, setDragOver] = useState(false);
  const [uploadStatus, setUploadStatus] = useState<UploadStatus>('idle');
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const doUpload = async (file: File) => {
    setSelectedFile(file.name);
    setUploadError(null);

    const validationIssue = validatePdfUpload(file);
    if (validationIssue) {
      setUploadStatus('error');
      setUploadError(
        validationIssue === 'too-large'
          ? t.upload.fileTooLarge
          : t.upload.invalidFileType,
      );
      return;
    }

    setUploadStatus('uploading');

    if (onUploadSuccess) {
      try {
        await onUploadSuccess(file);
        setUploadStatus('success');
      } catch (err: unknown) {
        setUploadStatus('error');
        const message = err instanceof Error ? err.message : t.upload.fallbackError;
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
        {t.upload.title}
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
        aria-label={t.upload.ariaLabel}
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
          {selectedFile && uploadStatus !== 'idle'
            ? selectedFile
            : {
                idle: t.upload.idle,
                uploading: t.upload.uploading,
                success: t.upload.success,
                error: t.upload.error,
              }[uploadStatus]}
        </p>

        {uploadStatus === 'idle' && (
          <span className="upload-panel__dropzone-hint">{t.upload.hint}</span>
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
            {t.upload.chooseFile}
          </button>
        )}

        {uploadStatus === 'uploading' && (
          <button type="button" className="upload-panel__button upload-panel__button--disabled" disabled>
            {t.upload.uploading}
          </button>
        )}

        {uploadStatus === 'success' && (
          <button type="button" className="upload-panel__button" onClick={handleReset}>
            {t.upload.uploadAnother}
          </button>
        )}

        {uploadStatus === 'error' && (
          <button type="button" className="upload-panel__button" onClick={handleReset}>
            {t.upload.retry}
          </button>
        )}
      </div>
    </section>
  );
}
