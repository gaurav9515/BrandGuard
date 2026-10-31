import React, { useState } from 'react';
import { Bell, LogOut, Shield, ChevronDown, User, Sun, Moon, Globe } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useLanguage } from '../context/LanguageContext';
import { useTheme } from '../context/ThemeContext';
import ServerHealthPill from './ServerHealthPill';

export default function Navbar({ activeTab, setActiveTab, queueCount = 3 }) {
  const { user, isAdmin, isWriter, login, logout, unreadNotifications } = useAuth();
  const { language, setLanguage, languages, t } = useLanguage();
  const { isDark, toggleTheme } = useTheme();

  const [userDropdownOpen, setUserDropdownOpen] = useState(false);
  const [langDropdownOpen, setLangDropdownOpen] = useState(false);

  // Filter tabs according to role
  const adminTabs = [
    { id: 'inspector', label: t('nav_inspector', 'Pre-Flight Inspector') },
    { id: 'registry', label: t('nav_registry', 'Rule Registry') },
    { id: 'queue', label: t('nav_queue', 'Review Queue'), badge: queueCount },
    { id: 'telemetry', label: t('nav_telemetry', 'Telemetry & Facts') },
    { id: 'team', label: t('nav_team', 'Team Management') },
    { id: 'workspaces', label: t('nav_workspaces', 'Workspace Directory') },
  ];

  const writerTabs = [
    { id: 'inspector', label: t('nav_inspector', 'Pre-Flight Inspector') },
    { id: 'workspaces', label: t('nav_workspaces', 'My Workspace') },
    { id: 'telemetry', label: 'My Top Rules' },
  ];

  const visibleTabs = isAdmin ? adminTabs : writerTabs;
  const currentLangObj = languages.find((l) => l.code === language) || languages[0];

  return (
    <>
      {/* Skip to Main Content Link for WCAG Accessibility */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-50 focus:px-4 focus:py-2 focus:bg-emerald-600 focus:text-white focus:rounded-md focus:shadow-lg focus:font-semibold text-xs"
      >
        Skip to main content
      </a>

      <header
        role="banner"
        className="sticky top-0 z-40 w-full bg-[var(--surface)] border-b border-[var(--border)] px-6 h-14 flex items-center justify-between transition-colors shadow-2xs"
      >
        {/* Left: Clean Brand Identity (Crowded subtitle, ruleset pill, and role badge removed) */}
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-[var(--primary)] flex items-center justify-center border border-emerald-900/40 shadow-2xs">
            <Shield className="w-4 h-4 text-white" />
          </div>
          <span className="font-bold text-[var(--text)] text-base font-serif tracking-tight">
            BrandGuard
          </span>
        </div>

        {/* Center: Role-Based Navigation Tabs */}
        <nav
          role="navigation"
          aria-label="Main Navigation"
          className="flex items-center gap-6 h-full text-xs"
        >
          {visibleTabs.map((tab) => {
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                type="button"
                onClick={() => setActiveTab(tab.id)}
                aria-current={isActive ? 'page' : undefined}
                className={`h-full flex items-center gap-1.5 px-0.5 border-b-2 font-medium transition-colors relative cursor-pointer ${
                  isActive
                    ? 'border-[#0A3423] dark:border-emerald-400 text-zinc-950 dark:text-white font-semibold'
                    : 'border-transparent text-zinc-500 dark:text-zinc-400 hover:text-zinc-800 dark:hover:text-zinc-200'
                }`}
              >
                <span>{tab.label}</span>
                {tab.badge !== undefined && tab.badge > 0 && (
                  <span className="bg-rose-100 dark:bg-rose-950 text-rose-700 dark:text-rose-300 border border-rose-200 dark:border-rose-900 font-mono text-[11px] px-1.5 py-0.2 rounded-full font-semibold">
                    {tab.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>

        {/* Right: Language Switcher, Theme Toggle, Notifications & User Dropdown */}
        <div className="flex items-center gap-2.5">
          {/* Multi-Language Selector Dropdown (Displays "EN" only) */}
          <div className="relative">
            <button
              type="button"
              onClick={() => setLangDropdownOpen(!langDropdownOpen)}
              title="Change Language"
              aria-label={`Language switcher, current: ${currentLangObj.name}`}
              aria-expanded={langDropdownOpen}
              className="flex items-center gap-1 px-2 py-1 text-xs font-mono font-bold rounded-lg border border-[var(--border)] bg-[var(--surface)] text-[var(--text)] hover:bg-[var(--surface-alt)] transition cursor-pointer"
            >
              <span>{currentLangObj.code.toUpperCase()}</span>
              <ChevronDown className="w-3 h-3 text-[var(--text-muted)]" />
            </button>

            {langDropdownOpen && (
              <div
                className="absolute right-0 mt-2 w-40 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl shadow-lg py-1 z-50 text-xs"
                onMouseLeave={() => setLangDropdownOpen(false)}
              >
                <div className="px-3 py-1.5 text-[10px] font-mono text-zinc-400 border-b border-zinc-100 dark:border-zinc-800">
                  Select Language
                </div>
                {languages.map((l) => (
                  <button
                    key={l.code}
                    type="button"
                    onClick={() => {
                      setLanguage(l.code);
                      setLangDropdownOpen(false);
                    }}
                    className={`w-full flex items-center justify-between px-3 py-2 text-left hover:bg-zinc-100 dark:hover:bg-zinc-800 transition cursor-pointer ${
                      language === l.code ? 'font-bold text-emerald-600 dark:text-emerald-400 bg-emerald-50/50 dark:bg-emerald-950/50' : 'text-zinc-700 dark:text-zinc-300'
                    }`}
                  >
                    <span className="flex items-center gap-2">
                      <span>{l.flag}</span>
                      <span>{l.name}</span>
                    </span>
                    {language === l.code && <span className="text-emerald-600 text-xs">✓</span>}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Light / Dark Mode Toggle */}
          <button
            type="button"
            onClick={toggleTheme}
            title={isDark ? "Switch to light mode" : "Switch to dark mode"}
            aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
            className="text-zinc-500 dark:text-zinc-400 hover:text-zinc-800 dark:hover:text-zinc-200 p-1.5 rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors cursor-pointer"
          >
            {isDark ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4" strokeWidth={1.75} />}
          </button>

          {/* Notification Bell */}
          <div className="relative">
            <button
              type="button"
              aria-label={`Notifications ${unreadNotifications > 0 ? `(${unreadNotifications} unread)` : ''}`}
              className="text-zinc-500 dark:text-zinc-400 hover:text-zinc-800 dark:hover:text-zinc-200 p-1.5 rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors relative cursor-pointer"
            >
              <Bell className="w-4 h-4" strokeWidth={1.75} />
              {unreadNotifications > 0 && (
                <span className="absolute top-1 right-1 w-2 h-2 rounded-full bg-rose-600 ring-2 ring-white dark:ring-zinc-900"></span>
              )}
            </button>
          </div>

          {/* User Profile & Role Indicator */}
          <div className="relative">
            <button
              type="button"
              onClick={() => setUserDropdownOpen(!userDropdownOpen)}
              aria-label="User profile menu"
              aria-expanded={userDropdownOpen}
              className="flex items-center gap-2 p-1 rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors cursor-pointer text-left"
            >
              <div
                className="w-7 h-7 rounded-full flex items-center justify-center font-bold text-[11px] text-white shadow-xs shrink-0"
                style={{ backgroundColor: user?.avatar_color || '#0A3423' }}
              >
                {(user?.first_name?.[0] || user?.username?.[0] || 'U').toUpperCase()}
              </div>
              <div className="hidden lg:block">
                <div className="text-xs font-semibold text-zinc-900 dark:text-white leading-none">
                  {user?.name || user?.username || 'User'}
                </div>
                <div className="text-[10px] text-zinc-500 font-mono mt-0.5">
                  {user?.role}
                </div>
              </div>
              <ChevronDown className="w-3.5 h-3.5 text-zinc-400" />
            </button>

            {/* User Dropdown Menu */}
            {userDropdownOpen && (
              <div
                className="absolute right-0 mt-2 w-56 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl shadow-lg py-1 z-50 text-xs"
                onMouseLeave={() => setUserDropdownOpen(false)}
              >
                <div className="px-3 py-2 border-b border-zinc-100 dark:border-zinc-800">
                  <p className="font-semibold text-zinc-900 dark:text-white">{user?.name}</p>
                  <p className="text-[11px] text-zinc-500">{user?.email}</p>
                  <p className="text-[10px] font-mono text-zinc-400 mt-0.5">{user?.department}</p>
                </div>

                <div className="px-3 py-1.5 text-[11px] font-mono text-zinc-500 dark:text-zinc-400 bg-zinc-50 dark:bg-zinc-800/50 flex items-center justify-between">
                  <span>Active Role:</span>
                  <span className="font-bold text-zinc-800 dark:text-zinc-200">{user?.role}</span>
                </div>

                {/* Quick Persona Switcher */}
                <div className="px-2 py-1.5 border-t border-zinc-100 dark:border-zinc-800">
                  <p className="px-1 text-[10px] font-mono text-zinc-400 uppercase tracking-wider mb-1">
                    Switch Demo Persona
                  </p>
                  <button
                    type="button"
                    onClick={async () => {
                      setUserDropdownOpen(false);
                      await login('admin', 'admin123');
                    }}
                    className={`w-full text-left px-2 py-1 rounded text-[11px] flex items-center justify-between transition cursor-pointer ${
                      isAdmin ? 'bg-emerald-50 dark:bg-emerald-950/50 text-emerald-800 dark:text-emerald-300 font-semibold' : 'text-zinc-700 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800'
                    }`}
                  >
                    <span>Jordan Lee (Admin)</span>
                    {isAdmin && <span className="text-[10px] text-emerald-600">Active</span>}
                  </button>
                  <button
                    type="button"
                    onClick={async () => {
                      setUserDropdownOpen(false);
                      await login('writer1', 'writer123');
                    }}
                    className={`w-full text-left px-2 py-1 rounded text-[11px] flex items-center justify-between transition cursor-pointer ${
                      user?.username === 'writer1' ? 'bg-sky-50 dark:bg-sky-950/50 text-sky-800 dark:text-sky-300 font-semibold' : 'text-zinc-700 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800'
                    }`}
                  >
                    <span>Alex Morgan (Writer)</span>
                    {user?.username === 'writer1' && <span className="text-[10px] text-sky-600">Active</span>}
                  </button>
                  <button
                    type="button"
                    onClick={async () => {
                      setUserDropdownOpen(false);
                      await login('writer2', 'writer123');
                    }}
                    className={`w-full text-left px-2 py-1 rounded text-[11px] flex items-center justify-between transition cursor-pointer ${
                      user?.username === 'writer2' ? 'bg-zinc-100 dark:bg-zinc-800 text-zinc-900 dark:text-white font-semibold' : 'text-zinc-700 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800'
                    }`}
                  >
                    <span>Taylor Reed (Writer)</span>
                    {user?.username === 'writer2' && <span className="text-[10px] text-zinc-600">Active</span>}
                  </button>
                </div>

                <div className="border-t border-zinc-100 dark:border-zinc-800 mt-1">
                  <button
                    type="button"
                    onClick={() => {
                      setUserDropdownOpen(false);
                      logout();
                    }}
                    className="w-full text-left px-3 py-2 text-rose-600 dark:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-950/40 flex items-center gap-2 cursor-pointer transition-colors"
                  >
                    <LogOut className="w-3.5 h-3.5" />
                    Sign out
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </header>
    </>
  );
}
