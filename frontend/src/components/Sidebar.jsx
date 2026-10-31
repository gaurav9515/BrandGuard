import React, { useState } from 'react';
import {
  Shield,
  LayoutDashboard,
  BookOpen,
  FileCheck,
  Users,
  FileText,
  Sliders,
  FolderGit2,
  Sparkles,
  ChevronLeft,
  ChevronRight,
  Palette,
  Layers,
  Database,
  ExternalLink,
  FlaskConical,
  X,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useLanguage } from '../context/LanguageContext';
import ServerHealthPill from './ServerHealthPill';

export default function Sidebar({
  activeTab,
  setActiveTab,
  queueCount = 3,
  collapsed,
  setCollapsed,
  mobileOpen,
  setMobileOpen,
}) {
  const { user, isAdmin, isWriter } = useAuth();
  const { t } = useLanguage();

  // Role-based navigation items
  const adminMenuItems = [
    { id: 'telemetry', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'registry', label: 'Rule Registry', icon: BookOpen },
    { id: 'facts', label: 'Fact Ledger', icon: Database },
    { id: 'visual_test_lab', label: 'Visual Test Lab', icon: FlaskConical },
    { id: 'queue', label: 'Review Queue', icon: FileCheck, badge: queueCount },
    { id: 'team', label: 'Team', icon: Users },
    { id: 'audit_log', label: 'Audit Log', icon: FileText },
    { id: 'settings', label: 'Settings', icon: Sliders },
  ];

  const writerMenuItems = [
    { id: 'workspaces', label: 'My Workspace', icon: FolderGit2 },
    { id: 'inspector', label: 'Pre-Flight Inspector', icon: Sparkles },
    { id: 'submissions', label: 'My Submissions', icon: FileCheck },
    { id: 'guide', label: 'Rule Guide', icon: BookOpen },
  ];

  const menuItems = isAdmin ? adminMenuItems : writerMenuItems;

  const handleNavClick = (tabId) => {
    setActiveTab(tabId);
    if (mobileOpen && setMobileOpen) {
      setMobileOpen(false);
    }
  };

  return (
    <>
      {/* Mobile Backdrop */}
      {mobileOpen && (
        <div
          role="presentation"
          onClick={() => setMobileOpen(false)}
          className="fixed inset-0 z-40 bg-black/40 backdrop-blur-xs lg:hidden transition-opacity"
        />
      )}

      {/* Sidebar Container */}
      <aside
        className={`fixed lg:sticky top-0 left-0 z-50 h-screen bg-[var(--surface)] border-r border-[var(--border)] flex flex-col justify-between transition-all duration-200 select-none ${
          collapsed ? 'w-16' : 'w-60'
        } ${
          mobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        }`}
      >
        {/* Top: Brand Header */}
        <div>
          <div className="h-14 border-b border-[var(--border)] flex items-center justify-between px-3.5">
            <div className="flex items-center gap-2.5 overflow-hidden">
              <div className="w-8 h-8 rounded-lg bg-[var(--primary)] flex items-center justify-center shrink-0 border border-emerald-900/40 shadow-2xs">
                <Shield className="w-4 h-4 text-white" />
              </div>
              {!collapsed && (
                <div className="truncate text-left">
                  <div className="font-bold text-[var(--text)] text-sm tracking-tight font-serif truncate">
                    BrandGuard
                  </div>
                  <div className="text-[10px] text-[var(--text-muted)] truncate font-mono">
                    NovaPay · Compiler
                  </div>
                </div>
              )}
            </div>

            {/* Mobile Close Button */}
            <button
              type="button"
              onClick={() => setMobileOpen(false)}
              className="lg:hidden text-[var(--text-muted)] hover:text-[var(--text)] p-1 rounded-md"
              aria-label="Close sidebar"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Navigation Menu */}
          <nav className="p-2 space-y-1 mt-2 text-left">
            {!collapsed && (
              <div className="px-3 py-1.5 text-[10px] font-mono font-bold uppercase tracking-wider text-[var(--text-muted)]">
                {isAdmin ? 'GOVERNANCE ADMIN' : 'CREATOR WORKSPACE'}
              </div>
            )}

            {menuItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;

              return (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => handleNavClick(item.id)}
                  title={collapsed ? item.label : undefined}
                  className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs font-semibold transition-all relative cursor-pointer ${
                    isActive
                      ? 'bg-[var(--surface-alt)] text-[var(--primary)] font-bold shadow-2xs'
                      : 'text-[var(--text-muted)] hover:text-[var(--text)] hover:bg-[var(--surface-alt)]/50'
                  } ${collapsed ? 'justify-center px-0' : ''}`}
                >
                  <Icon className={`w-4 h-4 shrink-0 ${isActive ? 'text-[var(--primary)]' : ''}`} />
                  {!collapsed && <span className="truncate">{item.label}</span>}

                  {/* Notification / Queue count badge */}
                  {item.badge !== undefined && item.badge > 0 && (
                    <span
                      className={`ml-auto font-mono text-[10px] font-bold px-1.5 py-0.2 rounded-full shrink-0 ${
                        collapsed
                          ? 'absolute top-1 right-1 w-2 h-2 p-0 bg-[var(--blocker)]'
                          : 'bg-[var(--primary)] text-white'
                      }`}
                    >
                      {!collapsed && item.badge}
                    </span>
                  )}
                </button>
              );
            })}
          </nav>
        </div>

        {/* Bottom / Footer: Status Chips & Collapse Button */}
        <div className="p-3 border-t border-[var(--border)] bg-[var(--surface)] space-y-2">
          {!collapsed ? (
            <div className="space-y-1.5">
              {/* Single-line Status Chip 1: Ruleset */}
              {/* <div className="h-7 px-2.5 rounded-full bg-[var(--surface-alt)] border border-[var(--border)] flex items-center justify-between text-[11px] font-mono whitespace-nowrap text-[var(--text)] shadow-2xs">
                <span className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-[var(--cleared)] inline-block"></span>
                  <span>Ruleset v3.2</span>
                </span>
                <span className="text-[10px] text-[var(--cleared)] font-bold">Active</span>
              </div> */}

              {/* Single-line Status Chip 2: API Live */}
              {/* <div className="h-7 px-2.5 rounded-full bg-[var(--surface-alt)] border border-[var(--border)] flex items-center justify-between text-[11px] font-mono whitespace-nowrap text-[var(--text)] shadow-2xs">
                <span className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse inline-block"></span>
                  <span>API Live</span>
                </span>
                <span className="text-[10px] text-[var(--text-muted)] font-mono">974ms</span>
              </div> */}
            </div>
          ) : (
            <div className="flex flex-col items-center gap-2 py-1">
              <span className="w-2.5 h-2.5 rounded-full bg-[var(--cleared)]" title="Ruleset v3.2 Active" />
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" title="API Live · 974ms" />
            </div>
          )}

          {/* Collapse Sidebar Toggle (Desktop Only) */}
          <div className="pt-2 hidden lg:flex justify-end">
            <button
              type="button"
              onClick={() => setCollapsed(!collapsed)}
              title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
              aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
              className="text-[var(--text-muted)] hover:text-[var(--text)] p-1.5 rounded-md hover:bg-[var(--surface-alt)] transition-colors cursor-pointer"
            >
              {collapsed ? (
                <ChevronRight className="w-4 h-4" />
              ) : (
                <ChevronLeft className="w-4 h-4" />
              )}
            </button>
          </div>
        </div>
      </aside>
    </>
  );
}

