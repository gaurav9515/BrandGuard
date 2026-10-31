import React, { useState, useRef, useEffect, useMemo } from 'react';
import {
  Menu,
  Search,
  Bell,
  Sun,
  Moon,
  ChevronDown,
  User,
  LogOut,
  Shield,
  Check,
  Building2,
  Plus,
  Sparkles,
  X,
  Loader2,
  BookOpen,
  Database,
  FileCheck,
  FlaskConical,
  LayoutDashboard,
  Sliders,
  Users,
  FileText,
  FolderGit2,
  Palette,
  ArrowRight,
  CornerDownLeft,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useLanguage } from '../context/LanguageContext';
import { useTheme } from '../context/ThemeContext';
import { useRealtime } from '../context/RealtimeContext';
import { useCompany } from '../context/CompanyContext';
import { API_BASE } from '../config/api';

const NAV_ICONS = {
  inspector: Sparkles,
  registry: BookOpen,
  guide: BookOpen,
  facts: Database,
  visual_test_lab: FlaskConical,
  queue: FileCheck,
  telemetry: LayoutDashboard,
  team: Users,
  audit_log: FileText,
  workspaces: FolderGit2,
  design: Palette,
  settings: Sliders,
};

export default function TopBar({
  activeTab,
  onToggleMobileMenu,
  onNavigate,
  onSelectRule,
  onSelectFact,
  onSelectSubmission,
}) {
  const { user, isAdmin, isWriter, logout, unreadNotifications } = useAuth();
  const { language, setLanguage, languages } = useLanguage();
  const { isDark, toggleTheme } = useTheme();
  const { status: realtimeStatus } = useRealtime();
  const { companies, activeCompany, switchCompany, createCompany } = useCompany();

  const [companyDropdownOpen, setCompanyDropdownOpen] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newCompanyName, setNewCompanyName] = useState('');
  const [creatingCompany, setCreatingCompany] = useState(false);
  const [createError, setCreateError] = useState(null);

  const [langDropdownOpen, setLangDropdownOpen] = useState(false);
  const [userDropdownOpen, setUserDropdownOpen] = useState(false);

  // Global search state
  const [searchQuery, setSearchQuery] = useState('');
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchLoading, setSearchLoading] = useState(false);
  const [searchResults, setSearchResults] = useState({
    query: '',
    total: 0,
    navigation: [],
    rules: [],
    facts: [],
    drafts: [],
  });
  const [searchCategory, setSearchCategory] = useState('all'); // 'all' | 'rules' | 'facts' | 'drafts' | 'navigation'
  const [highlightedIndex, setHighlightedIndex] = useState(0);
  const [mobileSearchOpen, setMobileSearchOpen] = useState(false);

  const searchRef = useRef(null);
  const searchInputRef = useRef(null);
  const mobileInputRef = useRef(null);

  const handleCreateCompanySubmit = async (e) => {
    e.preventDefault();
    if (!newCompanyName.trim()) return;
    setCreatingCompany(true);
    setCreateError(null);
    try {
      await createCompany({
        name: newCompanyName.trim(),
        ruleset_version: 'v3.2'
      });
      setNewCompanyName('');
      setShowCreateModal(false);
    } catch (err) {
      setCreateError(err.message || 'Failed to create brand');
    } finally {
      setCreatingCompany(false);
    }
  };

  // Tab label resolution for breadcrumbs
  const tabTitles = {
    workspaces: 'My Workspace',
    inspector: 'Pre-Flight Inspector',
    submissions: 'My Submissions',
    guide: 'Rule Guide',
    registry: 'Rule Registry',
    facts: 'Fact Ledger & Blast Radius',
    visual_test_lab: 'Visual Identity Test Lab',
    queue: 'Manager Sign-Off Queue',
    telemetry: 'Governance Telemetry & Ambiguity',
    team: 'Team Management',
    audit_log: 'Governance Audit Log',
    settings: 'Organization Settings',
    design: 'Design System Showcase',
  };

  const activeTitle = tabTitles[activeTab] || 'BrandGuard';

  // Flattened list of items filtered by active searchCategory
  const filteredItems = useMemo(() => {
    const list = [];
    if (searchCategory === 'all' || searchCategory === 'navigation') {
      (searchResults.navigation || []).forEach((item) => list.push({ ...item, _type: 'navigation' }));
    }
    if (searchCategory === 'all' || searchCategory === 'rules') {
      (searchResults.rules || []).forEach((item) => list.push({ ...item, _type: 'rule' }));
    }
    if (searchCategory === 'all' || searchCategory === 'facts') {
      (searchResults.facts || []).forEach((item) => list.push({ ...item, _type: 'fact' }));
    }
    if (searchCategory === 'all' || searchCategory === 'drafts') {
      (searchResults.drafts || []).forEach((item) => list.push({ ...item, _type: 'draft' }));
    }
    return list;
  }, [searchResults, searchCategory]);

  const handleSelectItem = (item) => {
    setSearchOpen(false);
    setMobileSearchOpen(false);
    setSearchQuery('');
    setHighlightedIndex(0);

    if (item._type === 'navigation') {
      if (onNavigate) onNavigate(item.id);
    } else if (item._type === 'rule') {
      if (onSelectRule) onSelectRule(item);
      else if (onNavigate) onNavigate(isAdmin ? 'registry' : 'guide');
    } else if (item._type === 'fact') {
      if (onSelectFact) onSelectFact(item);
      else if (onNavigate) onNavigate('facts');
    } else if (item._type === 'draft') {
      if (onSelectSubmission) onSelectSubmission(item.id);
      else if (onNavigate) onNavigate('inspector');
    }
  };

  const handleInputKeyDown = (e) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      if (filteredItems.length > 0) {
        setHighlightedIndex((prev) => (prev + 1) % filteredItems.length);
      }
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      if (filteredItems.length > 0) {
        setHighlightedIndex((prev) => (prev - 1 + filteredItems.length) % filteredItems.length);
      }
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (filteredItems.length > 0 && filteredItems[highlightedIndex]) {
        handleSelectItem(filteredItems[highlightedIndex]);
      }
    } else if (e.key === 'Escape') {
      e.preventDefault();
      setSearchOpen(false);
      setMobileSearchOpen(false);
      searchInputRef.current?.blur();
    }
  };

  // Keyboard shortcut listener (Ctrl+K, Cmd+K, /)
  useEffect(() => {
    const handleGlobalKeyDown = (e) => {
      const activeEl = document.activeElement;
      const isInput =
        activeEl &&
        (activeEl.tagName === 'INPUT' ||
          activeEl.tagName === 'TEXTAREA' ||
          activeEl.tagName === 'SELECT' ||
          activeEl.isContentEditable);

      if ((e.key === '/' || ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k')) && !isInput) {
        e.preventDefault();
        setSearchOpen(true);
        setTimeout(() => searchInputRef.current?.focus(), 50);
      } else if (e.key === 'Escape' && (searchOpen || mobileSearchOpen)) {
        setSearchOpen(false);
        setMobileSearchOpen(false);
      }
    };
    window.addEventListener('keydown', handleGlobalKeyDown);
    return () => window.removeEventListener('keydown', handleGlobalKeyDown);
  }, [searchOpen, mobileSearchOpen]);

  // Click outside listener
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (searchRef.current && !searchRef.current.contains(e.target)) {
        setSearchOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Debounced search query fetch
  useEffect(() => {
    if (!searchOpen && !mobileSearchOpen) return;

    const timer = setTimeout(async () => {
      setSearchLoading(true);
      try {
        const token = localStorage.getItem('brandguard_token') || localStorage.getItem('token');
        const compId = activeCompany?.id || '';
        const res = await fetch(
          `${API_BASE}/api/search/?q=${encodeURIComponent(searchQuery.trim())}&company_id=${compId}`,
          {
            headers: {
              'Content-Type': 'application/json',
              ...(token ? { Authorization: `Bearer ${token}` } : {}),
            },
          }
        );
        if (res.ok) {
          const data = await res.json();
          setSearchResults(data);
          setHighlightedIndex(0);
        }
      } catch (err) {
        console.error('Failed to perform global search:', err);
      } finally {
        setSearchLoading(false);
      }
    }, 180);

    return () => clearTimeout(timer);
  }, [searchQuery, searchOpen, mobileSearchOpen, activeCompany?.id]);

  return (
    <header className="sticky top-0 z-30 h-14 bg-[var(--surface)] border-b border-[var(--border)] px-4 sm:px-6 flex items-center justify-between transition-colors shadow-2xs">
      {/* Left: Mobile Toggle & Breadcrumbs */}
      <div className="flex items-center gap-3 overflow-hidden">
        <button
          type="button"
          onClick={onToggleMobileMenu}
          aria-label="Toggle navigation menu"
          className="lg:hidden text-[var(--text-muted)] hover:text-[var(--text)] p-1.5 rounded-lg hover:bg-[var(--surface-alt)] cursor-pointer"
        >
          <Menu className="w-5 h-5" />
        </button>

        {/* Company Switcher Dropdown */}
        <div className="relative">
          <button
            type="button"
            onClick={() => setCompanyDropdownOpen(!companyDropdownOpen)}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg border border-[var(--border)] bg-[var(--surface-alt)]/60 hover:bg-[var(--surface-alt)] text-xs text-[var(--text)] transition-colors cursor-pointer"
            title="Switch Brand / Company"
          >
            <span
              className="w-2.5 h-2.5 rounded-full shrink-0 ring-1 ring-[var(--border)]"
              style={{
                backgroundColor: activeCompany?.allowed_hex_palette?.[0]?.hex || '#1F5A3A'
              }}
            />
            <span className="font-semibold max-w-[110px] truncate">
              {activeCompany?.name || 'NovaPay'}
            </span>
            <ChevronDown className="w-3.5 h-3.5 text-[var(--text-muted)] shrink-0" />
          </button>

          {companyDropdownOpen && (
            <div className="absolute left-0 mt-1.5 w-60 bg-[var(--surface)] border border-[var(--border)] rounded-xl shadow-lg py-1.5 z-50 text-xs">
              <div className="px-3 py-1.5 text-[10px] font-semibold text-[var(--text-muted)] uppercase tracking-wider border-b border-[var(--border)]/60 flex items-center justify-between">
                <span>Select Brand ({companies.length})</span>
                {activeCompany?.ruleset_version && (
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-[var(--surface-alt)] font-mono font-normal">
                    {activeCompany.ruleset_version}
                  </span>
                )}
              </div>

              <div className="max-h-56 overflow-y-auto py-1">
                {companies.map((comp) => {
                  const isSelected = comp.id === activeCompany?.id;
                  const brandColor = comp.allowed_hex_palette?.[0]?.hex || '#1F5A3A';
                  return (
                    <button
                      key={comp.id}
                      type="button"
                      onClick={() => {
                        switchCompany(comp.id);
                        setCompanyDropdownOpen(false);
                      }}
                      className={`w-full text-left px-3 py-2 flex items-center justify-between hover:bg-[var(--surface-alt)] transition-colors cursor-pointer ${
                        isSelected ? 'bg-[var(--surface-alt)]/80 font-semibold text-[var(--text)]' : 'text-[var(--text-muted)]'
                      }`}
                    >
                      <div className="flex items-center gap-2 min-w-0">
                        <span
                          className="w-2.5 h-2.5 rounded-full shrink-0 ring-1 ring-[var(--border)]"
                          style={{ backgroundColor: brandColor }}
                        />
                        <div className="truncate">
                          <div className="truncate text-xs font-medium text-[var(--text)]">{comp.name}</div>
                          <div className="text-[10px] text-[var(--text-muted)] font-mono truncate">{comp.slug}</div>
                        </div>
                      </div>
                      {isSelected && <Check className="w-3.5 h-3.5 text-[var(--primary)] shrink-0" />}
                    </button>
                  );
                })}
              </div>

              {isAdmin && (
                <div className="border-t border-[var(--border)] pt-1 mt-1 px-1">
                  <button
                    type="button"
                    onClick={() => {
                      setCompanyDropdownOpen(false);
                      setShowCreateModal(true);
                    }}
                    className="w-full text-left px-2.5 py-1.5 text-[11px] font-medium text-[var(--primary)] hover:bg-[var(--surface-alt)] rounded-md flex items-center gap-1.5 cursor-pointer"
                  >
                    <Plus className="w-3 h-3" />
                    <span>Add New Brand</span>
                  </button>
                </div>
              )}
            </div>
          )}
        </div>

        <div className="flex items-center gap-1.5 text-xs text-[var(--text-muted)] truncate">
          <span>›</span>
          <span className="font-semibold text-[var(--text)] font-serif truncate">
            {activeTitle}
          </span>
        </div>
      </div>

      {/* Center: Interactive Global Search Bar */}
      <div ref={searchRef} className="relative hidden md:flex items-center max-w-sm lg:max-w-md w-full mx-4">
        <div className="relative w-full">
          <Search className="w-3.5 h-3.5 text-[var(--text-muted)] absolute left-3 top-2.5 pointer-events-none" />
          <input
            ref={searchInputRef}
            type="text"
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              if (!searchOpen) setSearchOpen(true);
            }}
            onFocus={() => setSearchOpen(true)}
            onKeyDown={handleInputKeyDown}
            placeholder="Search rules, facts, drafts... (/)"
            className="w-full pl-9 pr-14 py-1.5 text-xs bg-[var(--surface-alt)]/60 border border-[var(--border)] rounded-[var(--radius-input)] text-[var(--text)] placeholder:text-[var(--text-muted)] focus:outline-hidden focus:border-[var(--primary)] focus:bg-[var(--surface)] transition-all shadow-2xs"
            aria-label="Search rules, facts, drafts, and pages"
            aria-expanded={searchOpen}
          />
          <div className="absolute right-2.5 top-2 flex items-center gap-1">
            {searchLoading ? (
              <Loader2 className="w-3.5 h-3.5 text-[var(--primary)] animate-spin" />
            ) : searchQuery ? (
              <button
                type="button"
                onClick={() => {
                  setSearchQuery('');
                  searchInputRef.current?.focus();
                }}
                className="text-[var(--text-muted)] hover:text-[var(--text)] p-0.5 rounded cursor-pointer"
                title="Clear search"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            ) : (
              <kbd className="hidden lg:inline-block px-1.5 py-0.2 rounded text-[10px] font-mono text-[var(--text-muted)] bg-[var(--surface)] border border-[var(--border)] shadow-2xs">
                /
              </kbd>
            )}
          </div>
        </div>

        {/* Global Search Popover Dropdown */}
        {searchOpen && (
          <div className="absolute left-0 top-full mt-1.5 w-full min-w-[340px] sm:min-w-[480px] lg:min-w-[540px] bg-[var(--surface)] border border-[var(--border)] rounded-2xl shadow-2xl overflow-hidden z-50 text-xs animate-in fade-in zoom-in-95">
            {/* Category Filter Pills */}
            <div className="flex items-center gap-1.5 p-2 border-b border-[var(--border)] bg-[var(--surface-alt)]/50 overflow-x-auto">
              <button
                type="button"
                onClick={() => setSearchCategory('all')}
                className={`px-2.5 py-1 rounded-lg font-semibold text-[11px] transition-colors cursor-pointer shrink-0 ${
                  searchCategory === 'all'
                    ? 'bg-[var(--primary)] text-white shadow-2xs'
                    : 'text-[var(--text-muted)] hover:text-[var(--text)] hover:bg-[var(--surface-alt)]'
                }`}
              >
                All ({searchResults.total || 0})
              </button>

              {searchResults.rules?.length > 0 && (
                <button
                  type="button"
                  onClick={() => setSearchCategory('rules')}
                  className={`px-2.5 py-1 rounded-lg font-semibold text-[11px] transition-colors cursor-pointer shrink-0 flex items-center gap-1.5 ${
                    searchCategory === 'rules'
                      ? 'bg-[var(--primary)] text-white shadow-2xs'
                      : 'text-[var(--text-muted)] hover:text-[var(--text)] hover:bg-[var(--surface-alt)]'
                  }`}
                >
                  <BookOpen className="w-3 h-3" />
                  Rules ({searchResults.rules.length})
                </button>
              )}

              {searchResults.facts?.length > 0 && (
                <button
                  type="button"
                  onClick={() => setSearchCategory('facts')}
                  className={`px-2.5 py-1 rounded-lg font-semibold text-[11px] transition-colors cursor-pointer shrink-0 flex items-center gap-1.5 ${
                    searchCategory === 'facts'
                      ? 'bg-[var(--primary)] text-white shadow-2xs'
                      : 'text-[var(--text-muted)] hover:text-[var(--text)] hover:bg-[var(--surface-alt)]'
                  }`}
                >
                  <Database className="w-3 h-3" />
                  Facts ({searchResults.facts.length})
                </button>
              )}

              {searchResults.drafts?.length > 0 && (
                <button
                  type="button"
                  onClick={() => setSearchCategory('drafts')}
                  className={`px-2.5 py-1 rounded-lg font-semibold text-[11px] transition-colors cursor-pointer shrink-0 flex items-center gap-1.5 ${
                    searchCategory === 'drafts'
                      ? 'bg-[var(--primary)] text-white shadow-2xs'
                      : 'text-[var(--text-muted)] hover:text-[var(--text)] hover:bg-[var(--surface-alt)]'
                  }`}
                >
                  <FileText className="w-3 h-3" />
                  Drafts ({searchResults.drafts.length})
                </button>
              )}

              {searchResults.navigation?.length > 0 && (
                <button
                  type="button"
                  onClick={() => setSearchCategory('navigation')}
                  className={`px-2.5 py-1 rounded-lg font-semibold text-[11px] transition-colors cursor-pointer shrink-0 flex items-center gap-1.5 ${
                    searchCategory === 'navigation'
                      ? 'bg-[var(--primary)] text-white shadow-2xs'
                      : 'text-[var(--text-muted)] hover:text-[var(--text)] hover:bg-[var(--surface-alt)]'
                  }`}
                >
                  <Sparkles className="w-3 h-3" />
                  Pages ({searchResults.navigation.length})
                </button>
              )}
            </div>

            {/* Scrollable Results List */}
            <div className="max-h-[380px] overflow-y-auto p-2 space-y-1 divide-y divide-[var(--border)]/30">
              {searchLoading && filteredItems.length === 0 ? (
                <div className="py-8 text-center text-[var(--text-muted)] flex flex-col items-center justify-center gap-2">
                  <Loader2 className="w-5 h-5 animate-spin text-[var(--primary)]" />
                  <span className="text-xs">Searching rules, facts, and drafts...</span>
                </div>
              ) : filteredItems.length === 0 ? (
                <div className="py-8 px-4 text-center text-[var(--text-muted)]">
                  <p className="font-semibold text-[var(--text)] mb-1">
                    {searchQuery ? `No matches found for "${searchQuery}"` : 'No results to show'}
                  </p>
                  <p className="text-[11px] max-w-xs mx-auto">
                    Try searching by rule code (e.g. <span className="font-mono font-bold text-[var(--primary)]">FACT_012</span>), severity (<span className="font-mono text-rose-600">BLOCKER</span>), or keywords (<span className="italic">cheap</span>, <span className="italic">settlement</span>).
                  </p>
                </div>
              ) : (
                filteredItems.map((item, index) => {
                  const isSelected = index === highlightedIndex;

                  if (item._type === 'navigation') {
                    const NavIcon = NAV_ICONS[item.id] || Sparkles;
                    return (
                      <button
                        key={`nav-${item.id}`}
                        type="button"
                        onClick={() => handleSelectItem(item)}
                        onMouseEnter={() => setHighlightedIndex(index)}
                        className={`w-full text-left px-3 py-2 rounded-xl transition-colors flex items-center justify-between cursor-pointer ${
                          isSelected ? 'bg-[var(--surface-alt)] text-[var(--text)]' : 'hover:bg-[var(--surface-alt)]/60 text-[var(--text)]'
                        }`}
                      >
                        <div className="flex items-center gap-2.5 min-w-0">
                          <div className="p-1.5 rounded-lg bg-[var(--surface-alt)] text-[var(--primary)] shrink-0">
                            <NavIcon className="w-4 h-4" />
                          </div>
                          <div className="truncate">
                            <div className="font-semibold text-xs text-[var(--text)] flex items-center gap-2">
                              <span>{item.title}</span>
                              <span className="text-[10px] px-1.5 py-0.5 rounded bg-[var(--surface-alt)] text-[var(--text-muted)] font-mono uppercase">
                                {item.category}
                              </span>
                            </div>
                            <div className="text-[11px] text-[var(--text-muted)] truncate">
                              {item.description}
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center gap-1 text-[var(--primary)] text-[11px] font-semibold shrink-0 ml-2">
                          <span>Jump</span>
                          <ArrowRight className="w-3 h-3" />
                        </div>
                      </button>
                    );
                  }

                  if (item._type === 'rule') {
                    const isBlocker = item.severity === 'BLOCKER';
                    return (
                      <button
                        key={`rule-${item.id}`}
                        type="button"
                        onClick={() => handleSelectItem(item)}
                        onMouseEnter={() => setHighlightedIndex(index)}
                        className={`w-full text-left px-3 py-2.5 rounded-xl transition-colors flex items-center justify-between cursor-pointer ${
                          isSelected ? 'bg-[var(--surface-alt)] text-[var(--text)]' : 'hover:bg-[var(--surface-alt)]/60 text-[var(--text)]'
                        }`}
                      >
                        <div className="flex items-start gap-2.5 min-w-0">
                          <span className="font-mono text-[11px] font-bold px-1.5 py-0.5 rounded bg-[var(--surface-alt)] border border-[var(--border)] shrink-0 text-[var(--text)] mt-0.5">
                            {item.rule_code}
                          </span>
                          <div className="truncate">
                            <div className="flex items-center gap-1.5 mb-0.5 flex-wrap">
                              <span
                                className={`text-[10px] font-bold px-1.5 py-0.5 rounded font-mono ${
                                  isBlocker
                                    ? 'bg-rose-100 text-rose-800 dark:bg-rose-950/70 dark:text-rose-300'
                                    : 'bg-amber-100 text-amber-800 dark:bg-amber-950/70 dark:text-amber-300'
                                }`}
                              >
                                {item.severity}
                              </span>
                              <span className="font-semibold text-xs text-[var(--text)] truncate">
                                {item.title}
                              </span>
                            </div>
                            {item.claims_allowed && (
                              <div className="text-[11px] text-[var(--text-muted)] truncate flex items-center gap-1">
                                <span className="text-[var(--cleared)] font-bold">✓ Allowed:</span>
                                <span className="truncate italic">"{item.claims_allowed}"</span>
                              </div>
                            )}
                          </div>
                        </div>
                        <div className="text-right shrink-0 ml-2">
                          <span className="text-[10px] font-mono text-[var(--text-muted)]">
                            v{item.version || 1}
                          </span>
                        </div>
                      </button>
                    );
                  }

                  if (item._type === 'fact') {
                    return (
                      <button
                        key={`fact-${item.id}`}
                        type="button"
                        onClick={() => handleSelectItem(item)}
                        onMouseEnter={() => setHighlightedIndex(index)}
                        className={`w-full text-left px-3 py-2.5 rounded-xl transition-colors flex items-center justify-between cursor-pointer ${
                          isSelected ? 'bg-[var(--surface-alt)] text-[var(--text)]' : 'hover:bg-[var(--surface-alt)]/60 text-[var(--text)]'
                        }`}
                      >
                        <div className="flex items-start gap-2.5 min-w-0">
                          <div className="p-1 rounded-md bg-emerald-50 dark:bg-emerald-950/40 text-[var(--cleared)] shrink-0 mt-0.5">
                            <Database className="w-3.5 h-3.5" />
                          </div>
                          <div className="truncate">
                            <div className="flex items-center gap-1.5 mb-0.5">
                              <span className="font-mono font-bold text-[11px] text-[var(--text)]">
                                {item.fact_code}
                              </span>
                              <span className="text-[10px] text-[var(--text-muted)]">
                                · {item.category}
                              </span>
                            </div>
                            <div className="text-[11px] text-[var(--text-muted)] truncate italic">
                              "{item.claim_truth}"
                            </div>
                          </div>
                        </div>
                        <div className="text-right shrink-0 ml-2">
                          <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-emerald-50 dark:bg-emerald-950/60 text-[var(--cleared)]">
                            Verified
                          </span>
                        </div>
                      </button>
                    );
                  }

                  if (item._type === 'draft') {
                    const scoreColor =
                      item.score >= 80 ? 'text-[var(--cleared)]' : item.score >= 50 ? 'text-[var(--warning-text)]' : 'text-[var(--blocker)]';
                    return (
                      <button
                        key={`draft-${item.id}`}
                        type="button"
                        onClick={() => handleSelectItem(item)}
                        onMouseEnter={() => setHighlightedIndex(index)}
                        className={`w-full text-left px-3 py-2.5 rounded-xl transition-colors flex items-center justify-between cursor-pointer ${
                          isSelected ? 'bg-[var(--surface-alt)] text-[var(--text)]' : 'hover:bg-[var(--surface-alt)]/60 text-[var(--text)]'
                        }`}
                      >
                        <div className="flex items-start gap-2.5 min-w-0">
                          <div className="p-1 rounded-md bg-[var(--surface-alt)] text-[var(--primary)] shrink-0 mt-0.5">
                            <FileText className="w-3.5 h-3.5" />
                          </div>
                          <div className="truncate">
                            <div className="font-semibold text-xs text-[var(--text)] truncate">
                              {item.title}
                            </div>
                            <div className="text-[10px] text-[var(--text-muted)] font-mono flex items-center gap-1.5 mt-0.5">
                              <span className="uppercase">{item.channel?.replace('_', ' ')}</span>
                              <span>·</span>
                              <span>Status: {item.status}</span>
                            </div>
                          </div>
                        </div>
                        <div className="text-right shrink-0 ml-2">
                          <span className={`font-mono font-bold text-xs ${scoreColor}`}>
                            {Math.round(item.score)}%
                          </span>
                        </div>
                      </button>
                    );
                  }

                  return null;
                })
              )}
            </div>

            {/* Footer Navigation Bar */}
            <div className="px-3.5 py-2 bg-[var(--surface-alt)]/70 border-t border-[var(--border)] flex items-center justify-between text-[10px] font-mono text-[var(--text-muted)]">
              <div className="flex items-center gap-3">
                <span><kbd className="px-1 py-0.5 rounded bg-[var(--surface)] border border-[var(--border)]">↑↓</kbd> navigate</span>
                <span><kbd className="px-1 py-0.5 rounded bg-[var(--surface)] border border-[var(--border)]">↵</kbd> select</span>
                <span><kbd className="px-1 py-0.5 rounded bg-[var(--surface)] border border-[var(--border)]">esc</kbd> close</span>
              </div>
              <div className="hidden sm:block text-[var(--text-muted)]">
                BrandGuard Global Search
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Right: Actions, Language, Theme, Bell, Role & User */}
      <div className="flex items-center gap-2 sm:gap-3 shrink-0">
        {/* Mobile Search Button (< md) */}
        <button
          type="button"
          onClick={() => {
            setMobileSearchOpen(true);
            setTimeout(() => mobileInputRef.current?.focus(), 50);
          }}
          className="md:hidden text-[var(--text-muted)] hover:text-[var(--text)] p-1.5 rounded-lg hover:bg-[var(--surface-alt)] transition-colors cursor-pointer"
          title="Search rules, facts, drafts"
          aria-label="Search"
        >
          <Search className="w-4 h-4" />
        </button>
        {/* Real-Time SSE Stream & Fallback Polling Indicator */}
        {/* <div
          title={
            realtimeStatus === 'live'
              ? 'Real-Time Server-Sent Events (SSE) Stream Active'
              : realtimeStatus === 'reconnecting'
              ? 'Reconnecting to SSE Stream (automatic 10s fallback active)'
              : 'Live stream connected'
          }
          className="hidden sm:inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-mono font-semibold border border-[var(--border)] bg-[var(--surface-alt)]"
        >
          <span
            className={`w-1.5 h-1.5 rounded-full ${
              realtimeStatus === 'live'
                ? 'bg-[var(--cleared)] animate-pulse'
                : realtimeStatus === 'reconnecting'
                ? 'bg-[var(--warning-text)] animate-ping'
                : 'bg-[var(--cleared)]'
            }`}
          />
          <span className="text-[var(--text)]">
            {realtimeStatus === 'reconnecting' ? 'Reconnecting' : 'Live'}
          </span>
        </div> */}

        {/* Language Selector: Displays "EN" ONLY (No flag emoji rendering bug) */}
        <div className="relative">
          <button
            type="button"
            onClick={() => setLangDropdownOpen(!langDropdownOpen)}
            title="Switch Language"
            aria-label={`Language switcher, current: ${language.toUpperCase()}`}
            className="flex items-center gap-1 px-2.5 py-1 text-xs font-mono font-bold rounded-lg border border-[var(--border)] bg-[var(--surface)] text-[var(--text)] hover:bg-[var(--surface-alt)] transition cursor-pointer"
          >
            <span>{language.toUpperCase()}</span>
            <ChevronDown className="w-3 h-3 text-[var(--text-muted)]" />
          </button>

          {langDropdownOpen && (
            <div
              className="absolute right-0 mt-2 w-36 bg-[var(--surface)] border border-[var(--border)] rounded-xl shadow-lg py-1 z-50 text-xs"
              onMouseLeave={() => setLangDropdownOpen(false)}
            >
              <div className="px-3 py-1 text-[10px] font-mono text-[var(--text-muted)] border-b border-[var(--border)]">
                SELECT LANGUAGE
              </div>
              {languages.map((l) => (
                <button
                  key={l.code}
                  type="button"
                  onClick={() => {
                    setLanguage(l.code);
                    setLangDropdownOpen(false);
                  }}
                  className={`w-full flex items-center justify-between px-3 py-1.5 text-left hover:bg-[var(--surface-alt)] transition cursor-pointer ${
                    language === l.code ? 'font-bold text-[var(--primary)]' : 'text-[var(--text)]'
                  }`}
                >
                  <span>{l.name}</span>
                  {language === l.code && <Check className="w-3.5 h-3.5 text-[var(--primary)]" />}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Light / Dark Mode Toggle */}
        <button
          type="button"
          onClick={toggleTheme}
          title={isDark ? 'Switch to light mist' : 'Switch to night forest'}
          aria-label={isDark ? 'Switch to light mist' : 'Switch to night forest'}
          className="text-[var(--text-muted)] hover:text-[var(--text)] p-1.5 rounded-lg hover:bg-[var(--surface-alt)] transition-colors cursor-pointer"
        >
          {isDark ? (
            <Sun className="w-4 h-4 text-amber-400" />
          ) : (
            <Moon className="w-4 h-4" />
          )}
        </button>

        {/* Notification Bell */}
        <div className="relative">
          <button
            type="button"
            aria-label={`Notifications ${unreadNotifications > 0 ? `(${unreadNotifications} unread)` : ''}`}
            className="text-[var(--text-muted)] hover:text-[var(--text)] p-1.5 rounded-lg hover:bg-[var(--surface-alt)] transition-colors relative cursor-pointer"
          >
            <Bell className="w-4 h-4" />
            {unreadNotifications > 0 && (
              <span className="absolute top-1 right-1 w-2 h-2 rounded-full bg-[var(--blocker)] ring-2 ring-[var(--surface)]" />
            )}
          </button>
        </div>

        {/* User Profile Avatar Dropdown */}
        <div className="relative">
          <button
            type="button"
            onClick={() => setUserDropdownOpen(!userDropdownOpen)}
            aria-expanded={userDropdownOpen}
            className="flex items-center gap-2 pl-1 py-1 rounded-lg hover:bg-[var(--surface-alt)] transition cursor-pointer"
          >
            <div
              className="w-7 h-7 rounded-full text-white text-xs font-bold font-mono flex items-center justify-center shrink-0 border border-black/10"
              style={{ backgroundColor: user?.avatar_color || 'var(--primary)' }}
            >
              {user?.username ? user.username[0].toUpperCase() : 'U'}
            </div>
            <ChevronDown className="w-3 h-3 text-[var(--text-muted)] hidden sm:block" />
          </button>

          {userDropdownOpen && (
            <div
              className="absolute right-0 mt-2 w-52 bg-[var(--surface)] border border-[var(--border)] rounded-xl shadow-xl py-1.5 z-50 text-xs"
              onMouseLeave={() => setUserDropdownOpen(false)}
            >
              <div className="px-3.5 py-2 border-b border-[var(--border)]">
                <div className="font-bold text-[var(--text)] truncate">
                  {user?.name || user?.username}
                </div>
                <div className="text-[10px] font-mono text-[var(--text-muted)] truncate">
                  {user?.email || 'user@novapay.io'}
                </div>
                <div className="text-[10px] text-[var(--primary)] font-semibold mt-1">
                  Role: {isAdmin ? 'Admin' : 'Writer'} · {user?.department || 'Marketing'}
                </div>
              </div>

              <button
                type="button"
                onClick={() => {
                  setUserDropdownOpen(false);
                  logout();
                }}
                className="w-full flex items-center gap-2 px-3.5 py-2 text-left text-rose-600 dark:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-950/30 transition cursor-pointer font-medium"
              >
                <LogOut className="w-3.5 h-3.5" />
                <span>Sign Out</span>
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Modal: Create New Brand / Company */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-xs">
          <div className="bg-[var(--surface)] border border-[var(--border)] rounded-2xl shadow-2xl max-w-md w-full p-6 relative animate-in fade-in zoom-in-95">
            <button
              onClick={() => setShowCreateModal(false)}
              className="absolute right-4 top-4 text-[var(--text-muted)] hover:text-[var(--text)] p-1 rounded-lg"
            >
              <X className="w-5 h-5" />
            </button>

            <div className="flex items-center gap-2.5 mb-4">
              <div className="p-2 rounded-xl bg-[var(--surface-alt)] text-[var(--primary)]">
                <Building2 className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-serif text-lg font-bold text-[var(--text)]">Create Brand</h3>
                <p className="text-xs text-[var(--text-muted)]">Add a new company or brand under your organization</p>
              </div>
            </div>

            {createError && (
              <div className="mb-4 p-3 rounded-lg bg-[var(--blocker-tint)] text-[var(--blocker)] text-xs border border-[var(--blocker)]/20">
                {createError}
              </div>
            )}

            <form onSubmit={handleCreateCompanySubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-[var(--text)] mb-1">Brand / Company Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. NovaPay Prime, Apex Global"
                  value={newCompanyName}
                  onChange={(e) => setNewCompanyName(e.target.value)}
                  className="w-full px-3 py-2 text-xs bg-[var(--surface-alt)] border border-[var(--border)] rounded-[var(--radius-input)] text-[var(--text)] focus:outline-hidden focus:border-[var(--primary)]"
                />
              </div>

              <div className="pt-2 flex items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-3.5 py-2 text-xs rounded-lg border border-[var(--border)] hover:bg-[var(--surface-alt)] text-[var(--text-muted)]"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creatingCompany || !newCompanyName.trim()}
                  className="px-4 py-2 text-xs font-semibold rounded-lg bg-[var(--primary)] hover:bg-[var(--primary-hover)] text-white shadow-xs disabled:opacity-50 flex items-center gap-1.5"
                >
                  {creatingCompany ? 'Creating...' : 'Create Brand'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Mobile Search Modal Overlay */}
      {mobileSearchOpen && (
        <div className="fixed inset-0 z-50 flex flex-col bg-black/50 backdrop-blur-xs p-3 sm:p-6 md:hidden">
          <div className="bg-[var(--surface)] border border-[var(--border)] rounded-2xl shadow-2xl flex flex-col max-h-[90vh] overflow-hidden animate-in fade-in zoom-in-95">
            {/* Mobile Search Input Header */}
            <div className="p-3 border-b border-[var(--border)] flex items-center gap-2">
              <Search className="w-4 h-4 text-[var(--text-muted)] shrink-0 ml-1" />
              <input
                ref={mobileInputRef}
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search rules, facts, drafts..."
                className="w-full text-xs bg-transparent border-0 text-[var(--text)] placeholder:text-[var(--text-muted)] focus:outline-hidden"
              />
              {searchLoading && <Loader2 className="w-4 h-4 text-[var(--primary)] animate-spin shrink-0" />}
              {searchQuery && (
                <button
                  type="button"
                  onClick={() => setSearchQuery('')}
                  className="p-1 text-[var(--text-muted)] hover:text-[var(--text)]"
                >
                  <X className="w-4 h-4" />
                </button>
              )}
              <button
                type="button"
                onClick={() => setMobileSearchOpen(false)}
                className="px-2.5 py-1 text-xs font-semibold rounded-lg bg-[var(--surface-alt)] text-[var(--text)]"
              >
                Close
              </button>
            </div>

            {/* Mobile Category Filters */}
            <div className="flex items-center gap-1.5 p-2 border-b border-[var(--border)] bg-[var(--surface-alt)]/50 overflow-x-auto">
              <button
                type="button"
                onClick={() => setSearchCategory('all')}
                className={`px-2.5 py-1 rounded-lg font-semibold text-[11px] transition-colors cursor-pointer shrink-0 ${
                  searchCategory === 'all'
                    ? 'bg-[var(--primary)] text-white shadow-2xs'
                    : 'text-[var(--text-muted)] hover:text-[var(--text)] hover:bg-[var(--surface-alt)]'
                }`}
              >
                All ({searchResults.total || 0})
              </button>

              {searchResults.rules?.length > 0 && (
                <button
                  type="button"
                  onClick={() => setSearchCategory('rules')}
                  className={`px-2.5 py-1 rounded-lg font-semibold text-[11px] transition-colors cursor-pointer shrink-0 flex items-center gap-1.5 ${
                    searchCategory === 'rules'
                      ? 'bg-[var(--primary)] text-white shadow-2xs'
                      : 'text-[var(--text-muted)] hover:text-[var(--text)] hover:bg-[var(--surface-alt)]'
                  }`}
                >
                  <BookOpen className="w-3 h-3" />
                  Rules ({searchResults.rules.length})
                </button>
              )}

              {searchResults.facts?.length > 0 && (
                <button
                  type="button"
                  onClick={() => setSearchCategory('facts')}
                  className={`px-2.5 py-1 rounded-lg font-semibold text-[11px] transition-colors cursor-pointer shrink-0 flex items-center gap-1.5 ${
                    searchCategory === 'facts'
                      ? 'bg-[var(--primary)] text-white shadow-2xs'
                      : 'text-[var(--text-muted)] hover:text-[var(--text)] hover:bg-[var(--surface-alt)]'
                  }`}
                >
                  <Database className="w-3 h-3" />
                  Facts ({searchResults.facts.length})
                </button>
              )}

              {searchResults.drafts?.length > 0 && (
                <button
                  type="button"
                  onClick={() => setSearchCategory('drafts')}
                  className={`px-2.5 py-1 rounded-lg font-semibold text-[11px] transition-colors cursor-pointer shrink-0 flex items-center gap-1.5 ${
                    searchCategory === 'drafts'
                      ? 'bg-[var(--primary)] text-white shadow-2xs'
                      : 'text-[var(--text-muted)] hover:text-[var(--text)] hover:bg-[var(--surface-alt)]'
                  }`}
                >
                  <FileText className="w-3 h-3" />
                  Drafts ({searchResults.drafts.length})
                </button>
              )}

              {searchResults.navigation?.length > 0 && (
                <button
                  type="button"
                  onClick={() => setSearchCategory('navigation')}
                  className={`px-2.5 py-1 rounded-lg font-semibold text-[11px] transition-colors cursor-pointer shrink-0 flex items-center gap-1.5 ${
                    searchCategory === 'navigation'
                      ? 'bg-[var(--primary)] text-white shadow-2xs'
                      : 'text-[var(--text-muted)] hover:text-[var(--text)] hover:bg-[var(--surface-alt)]'
                  }`}
                >
                  <Sparkles className="w-3 h-3" />
                  Pages ({searchResults.navigation.length})
                </button>
              )}
            </div>

            {/* Mobile Results */}
            <div className="flex-1 overflow-y-auto p-2 space-y-1">
              {searchLoading && filteredItems.length === 0 ? (
                <div className="py-8 text-center text-[var(--text-muted)] flex flex-col items-center justify-center gap-2">
                  <Loader2 className="w-5 h-5 animate-spin text-[var(--primary)]" />
                  <span className="text-xs">Searching...</span>
                </div>
              ) : filteredItems.length === 0 ? (
                <div className="py-8 px-4 text-center text-[var(--text-muted)] text-xs">
                  No matching results found.
                </div>
              ) : (
                filteredItems.map((item) => {
                  if (item._type === 'navigation') {
                    const NavIcon = NAV_ICONS[item.id] || Sparkles;
                    return (
                      <button
                        key={`m-nav-${item.id}`}
                        type="button"
                        onClick={() => handleSelectItem(item)}
                        className="w-full text-left px-3 py-2.5 rounded-xl hover:bg-[var(--surface-alt)] transition-colors flex items-center justify-between"
                      >
                        <div className="flex items-center gap-2.5 min-w-0">
                          <div className="p-1.5 rounded-lg bg-[var(--surface-alt)] text-[var(--primary)] shrink-0">
                            <NavIcon className="w-4 h-4" />
                          </div>
                          <div className="truncate">
                            <div className="font-semibold text-xs text-[var(--text)]">{item.title}</div>
                            <div className="text-[11px] text-[var(--text-muted)] truncate">{item.description}</div>
                          </div>
                        </div>
                        <ArrowRight className="w-3.5 h-3.5 text-[var(--primary)] shrink-0" />
                      </button>
                    );
                  }

                  if (item._type === 'rule') {
                    return (
                      <button
                        key={`m-rule-${item.id}`}
                        type="button"
                        onClick={() => handleSelectItem(item)}
                        className="w-full text-left px-3 py-2.5 rounded-xl hover:bg-[var(--surface-alt)] transition-colors flex items-center justify-between"
                      >
                        <div className="min-w-0">
                          <div className="flex items-center gap-1.5 mb-0.5">
                            <span className="font-mono text-[10px] font-bold px-1 rounded bg-[var(--surface-alt)]">{item.rule_code}</span>
                            <span className={`text-[10px] font-bold px-1 rounded ${item.severity === 'BLOCKER' ? 'bg-rose-100 text-rose-800' : 'bg-amber-100 text-amber-800'}`}>{item.severity}</span>
                          </div>
                          <div className="text-xs font-semibold text-[var(--text)] truncate">{item.title}</div>
                        </div>
                        <span className="text-[10px] font-mono text-[var(--text-muted)] shrink-0 ml-2">v{item.version || 1}</span>
                      </button>
                    );
                  }

                  if (item._type === 'fact') {
                    return (
                      <button
                        key={`m-fact-${item.id}`}
                        type="button"
                        onClick={() => handleSelectItem(item)}
                        className="w-full text-left px-3 py-2.5 rounded-xl hover:bg-[var(--surface-alt)] transition-colors flex items-center justify-between"
                      >
                        <div className="min-w-0">
                          <div className="font-mono font-bold text-xs text-[var(--text)]">{item.fact_code}</div>
                          <div className="text-[11px] text-[var(--text-muted)] truncate">{item.claim_truth}</div>
                        </div>
                        <span className="text-[10px] px-1 py-0.5 rounded bg-emerald-50 text-[var(--cleared)] shrink-0">Verified</span>
                      </button>
                    );
                  }

                  if (item._type === 'draft') {
                    return (
                      <button
                        key={`m-draft-${item.id}`}
                        type="button"
                        onClick={() => handleSelectItem(item)}
                        className="w-full text-left px-3 py-2.5 rounded-xl hover:bg-[var(--surface-alt)] transition-colors flex items-center justify-between"
                      >
                        <div className="min-w-0">
                          <div className="text-xs font-semibold text-[var(--text)] truncate">{item.title}</div>
                          <div className="text-[10px] text-[var(--text-muted)] font-mono">{item.channel}</div>
                        </div>
                        <span className="font-mono text-xs font-bold text-[var(--primary)]">{Math.round(item.score)}%</span>
                      </button>
                    );
                  }

                  return null;
                })
              )}
            </div>
          </div>
        </div>
      )}
    </header>
  );
}

