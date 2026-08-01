import type { Language } from '../types/language';
import { useLanguage } from '../i18n/LanguageContext';
import { LanguageSwitcher } from './LanguageSwitcher';

interface SidebarProps {
  language?: Language;
  onLanguageChange?: (language: Language) => void;
  labels?: {
    runtime: string;
    title: string;
    demoCompanies: string;
    language: string;
  };
}

export function Sidebar({ language, onLanguageChange, labels }: SidebarProps) {
  const i18n = useLanguage();
  const currentLanguage = language ?? i18n.language;
  const currentLabels = labels ?? {
    runtime: i18n.t.sidebar.runtime,
    title: i18n.t.sidebar.title,
    demoCompanies: i18n.t.sidebar.demoCompanies,
    language: i18n.t.language.label,
  };

  return (
    <aside className="sidebar">
      <div>
        <p className="eyebrow">{currentLabels.runtime}</p>
        <h1>{currentLabels.title}</h1>
      </div>

      {language && onLanguageChange ? (
        <div className="language-switcher" aria-label={currentLabels.language}>
          <button
            type="button"
            className={currentLanguage === 'en' ? 'language-switcher__button--active' : ''}
            aria-pressed={currentLanguage === 'en'}
            onClick={() => onLanguageChange('en')}
          >
            EN
          </button>
          <button
            type="button"
            className={currentLanguage === 'zh-CN' ? 'language-switcher__button--active' : ''}
            aria-pressed={currentLanguage === 'zh-CN'}
            onClick={() => onLanguageChange('zh-CN')}
          >
            中文
          </button>
        </div>
      ) : (
        <LanguageSwitcher />
      )}

      <nav aria-label={currentLabels.demoCompanies}>
        <p className="sidebar__label">{currentLabels.demoCompanies}</p>
        <ul>
          {i18n.t.sidebar.companies.map((company) => (
            <li key={company}>{company}</li>
          ))}
        </ul>
      </nav>
    </aside>
  );
}
