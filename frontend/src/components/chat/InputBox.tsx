import {
  type ChangeEvent,
  type FormEvent,
  type KeyboardEvent,
  useRef,
  useState,
} from 'react';
import { validatePdfUpload } from '../../api/knowledgeContract';
import { useLanguage } from '../../i18n/LanguageContext';
import { Icon } from '../ui/Icon';

interface InputBoxProps {
  onSubmit: (message: string) => void;
  onFileUpload?: (file: File) => Promise<void>;
  disabled?: boolean;
  placeholder?: string;
}

type FileUploadState =
  | { status: 'idle' }
  | { status: 'uploading'; filename: string }
  | { status: 'success'; filename: string }
  | { status: 'error'; filename: string; detail: string };

export function InputBox({
  onSubmit,
  onFileUpload,
  disabled = false,
  placeholder,
}: InputBoxProps) {
  const { t } = useLanguage();
  const [message, setMessage] = useState('');
  const [fileUpload, setFileUpload] = useState<FileUploadState>({
    status: 'idle',
  });
  const fileInputRef = useRef<HTMLInputElement>(null);
  const uploadingFile = fileUpload.status === 'uploading';
  const composerDisabled = disabled || uploadingFile;

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = message.trim();

    if (!trimmed || composerDisabled) {
      return;
    }

    onSubmit(trimmed);
    setMessage('');
  }

  async function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.currentTarget.files?.[0];
    event.currentTarget.value = '';

    if (!file || !onFileUpload) {
      return;
    }

    const validationIssue = validatePdfUpload(file);
    if (validationIssue) {
      setFileUpload({
        status: 'error',
        filename: file.name,
        detail: validationIssue === 'too-large'
          ? t.upload.fileTooLarge
          : t.upload.invalidFileType,
      });
      return;
    }

    setFileUpload({ status: 'uploading', filename: file.name });
    try {
      await onFileUpload(file);
      setFileUpload({ status: 'success', filename: file.name });
    } catch (error: unknown) {
      setFileUpload({
        status: 'error',
        filename: file.name,
        detail: error instanceof Error ? error.message : t.upload.fallbackError,
      });
    }
  }

  function handleMessageKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (
      event.key === 'Enter'
      && !event.shiftKey
      && !event.nativeEvent.isComposing
    ) {
      event.preventDefault();
      event.currentTarget.form?.requestSubmit();
    }
  }

  let uploadMessage: string | null = null;
  if (fileUpload.status === 'uploading') {
    uploadMessage = t.chat.uploadingDocument(fileUpload.filename);
  } else if (fileUpload.status === 'success') {
    uploadMessage = t.chat.documentSaved(fileUpload.filename);
  } else if (fileUpload.status === 'error') {
    uploadMessage = t.chat.documentUploadFailed(
      fileUpload.filename,
      fileUpload.detail,
    );
  }

  return (
    <form className="chat-input" onSubmit={handleSubmit}>
      {uploadMessage && (
        <div
          className={`chat-input__upload-status chat-input__upload-status--${fileUpload.status}`}
          role={fileUpload.status === 'error' ? 'alert' : 'status'}
          aria-live="polite"
        >
          <span className="chat-input__upload-icon" aria-hidden="true">
            {fileUpload.status === 'uploading'
              ? '\u21BB'
              : fileUpload.status === 'success'
                ? '\u2713'
                : '!'}
          </span>
          <span>{uploadMessage}</span>
        </div>
      )}

      <div className="chat-input__composer">
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,application/pdf"
          className="chat-input__file-input"
          onChange={handleFileChange}
          tabIndex={-1}
          aria-hidden="true"
        />
        <button
          type="button"
          className="chat-input__attachment"
          onClick={() => fileInputRef.current?.click()}
          disabled={composerDisabled || !onFileUpload}
          aria-label={t.chat.attachPdf}
          title={t.chat.attachPdf}
        >
          <Icon name="paperclip" />
          <span className="chat-input__attachment-label">PDF</span>
        </button>

        <label className="sr-only" htmlFor="chat-message-input">
          {t.chat.inputLabel}
        </label>
        <textarea
          id="chat-message-input"
          className="chat-input__message"
          rows={1}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={handleMessageKeyDown}
          placeholder={placeholder ?? t.chat.placeholder}
          disabled={composerDisabled}
          autoComplete="off"
        />
        <button
          type="submit"
          className="chat-input__send"
          disabled={composerDisabled || message.trim().length === 0}
        >
          <span className="chat-input__send-label">{t.chat.send}</span>
          <Icon name="arrow-up" />
        </button>
      </div>
    </form>
  );
}
