import { type FormEvent, useState } from 'react';

interface InputBoxProps {
  onSubmit: (message: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

export function InputBox({
  onSubmit,
  disabled = false,
  placeholder = 'Ask a financial question...',
}: InputBoxProps) {
  const [message, setMessage] = useState('');

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = message.trim();

    if (!trimmed || disabled) {
      return;
    }

    onSubmit(trimmed);
    setMessage('');
  }

  return (
    <form className="chat-input" onSubmit={handleSubmit}>
      <label className="sr-only" htmlFor="chat-message-input">
        Financial question input
      </label>
      <input
        id="chat-message-input"
        type="text"
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        placeholder={placeholder}
        disabled={disabled}
        autoComplete="off"
      />
      <button type="submit" disabled={disabled || message.trim().length === 0}>
        Send
      </button>
    </form>
  );
}