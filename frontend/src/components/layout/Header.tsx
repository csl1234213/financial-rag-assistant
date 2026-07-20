interface HeaderProps {
  title: string;
  subtitle: string;
  connected?: boolean;
}

export function Header({ title, subtitle, connected = true }: HeaderProps) {
  return (
    <header className="app-header">
      <div className="app-header__brand">
        <div className="app-header__logo" aria-hidden="true">
          R
        </div>
        <span className="app-header__title">{title}</span>
        <span className="app-header__subtitle">{subtitle}</span>
      </div>

      <div className="app-header__status" aria-label="System status">
        <span className="app-header__status-dot" aria-hidden="true" />
        {connected ? 'Connected' : 'Offline'}
      </div>
    </header>
  );
}