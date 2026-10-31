import React, { useState, useEffect } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import { LanguageProvider, useLanguage } from './context/LanguageContext';
import { ThemeProvider, useTheme } from './context/ThemeContext';
import { ServerHealthProvider } from './context/ServerHealthContext';
import Sidebar from './components/Sidebar';
import TopBar from './components/TopBar';
import LoginView from './components/LoginView';
import ServerHealthBanner from './components/ServerHealthBanner';
import ForbiddenGuard from './components/ForbiddenGuard';
import RuleDetailView from './components/RuleDetailView';
import ExceptionRequestView from './components/ExceptionRequestView';
import ManagerQueueView from './components/ManagerQueueView';
import DecidedView from './components/DecidedView';
import TelemetryView from './components/TelemetryView';
import PreFlightInspectorView from './components/PreFlightInspectorView';
import WorkspacesView from './components/WorkspacesView';
import TeamManagementView from './components/TeamManagementView';
import DesignShowcaseView from './components/DesignShowcaseView';
import CodebaseVerifierView from './components/CodebaseVerifierView';
import VisualTestLabView from './components/VisualTestLabView';
import { RealtimeProvider } from './context/RealtimeContext';
import { CompanyProvider } from './context/CompanyContext';
import { API_BASE } from './config/api';

function MainApp() {
  const { user, isAdmin, isWriter } = useAuth();
  const { t } = useLanguage();

  // Navigation tabs: 'telemetry' | 'registry' | 'facts' | 'queue' | 'team' | 'workspaces' | 'inspector' | 'design'
  const [activeTab, setActiveTab] = useState('telemetry');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  // Sub-view toggle for Pre-Flight Inspector: 'exception_request' | 'scan'
  const [inspectorSubView, setInspectorSubView] = useState('scan');

  // Sub-view toggle for Manager Queue: 'review' | 'decided'
  const [queueSubView, setQueueSubView] = useState('review');

  // Badge count for manager queue
  const [queueCount, setQueueCount] = useState(3);

  // Selected submission ID when navigating from Workspace to Inspector
  const [selectedSubmissionId, setSelectedSubmissionId] = useState(null);

  // Global search rule navigation state
  const [selectedRuleCode, setSelectedRuleCode] = useState(null);
  const [ruleSearchQuery, setRuleSearchQuery] = useState('');

  // Exception draft context when navigating from Inspector to Exception Request
  const [exceptionDraftContext, setExceptionDraftContext] = useState(null);

  // Set initial role-based landing tab on login or role switch
  useEffect(() => {
    if (user) {
      if (user.role === 'ADMIN') {
        setActiveTab('telemetry');
      } else if (user.role === 'CONTENT_WRITER') {
        setActiveTab('inspector');
        setInspectorSubView('scan');
      }
    }
  }, [user?.role]);

  // If user is not logged in, display the Login screen with role redirection
  if (!user) {
    return (
      <>
        <ServerHealthBanner />
        <LoginView
          onLoginSuccess={(loggedInUser) => {
            if (loggedInUser.role === 'ADMIN') {
              setActiveTab('telemetry');
            } else {
              setActiveTab('inspector');
              setInspectorSubView('scan');
            }
          }}
        />
      </>
    );
  }

  // Admin-only tabs list
  const adminOnlyTabs = ['registry', 'queue', 'team', 'facts', 'audit_log', 'settings', 'visual_test_lab'];
  const isForbiddenForWriter = isWriter && adminOnlyTabs.includes(activeTab);

  return (
    <div className="flex h-screen overflow-hidden bg-[var(--bg)] text-[var(--text)] font-sans antialiased transition-colors">
      {/* Collapsible Left Sidebar with Role-Based Navigation */}
      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        queueCount={queueCount}
        collapsed={sidebarCollapsed}
        setCollapsed={setSidebarCollapsed}
        mobileOpen={mobileOpen}
        setMobileOpen={setMobileOpen}
      />

      {/* Main View Area */}
      <div className="flex-1 flex flex-col min-w-0 h-full overflow-hidden">
        {/* Forest Design System TopBar */}
        <TopBar
          activeTab={activeTab}
          onToggleMobileMenu={() => setMobileOpen(!mobileOpen)}
          onNavigate={(tab) => {
            setActiveTab(tab);
            if (tab === 'inspector') setInspectorSubView('scan');
          }}
          onSelectRule={(rule) => {
            setSelectedRuleCode(rule.rule_code);
            setRuleSearchQuery(rule.rule_code);
            setActiveTab(isAdmin ? 'registry' : 'guide');
          }}
          onSelectFact={(fact) => {
            setActiveTab('facts');
          }}
          onSelectSubmission={(subId) => {
            setSelectedSubmissionId(subId);
            setActiveTab('inspector');
            setInspectorSubView('scan');
          }}
        />
        <ServerHealthBanner />

        {/* Scrollable Viewport */}
        <div className="flex-1 overflow-y-auto overflow-x-hidden">
          <main id="main-content" tabIndex="-1" className="p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto w-full focus:outline-hidden">
            {/* Route Guard: Content Writers attempting to access Admin screens get HTTP 403 screen */}
            {isForbiddenForWriter ? (
              <ForbiddenGuard
                attemptedTab={activeTab}
                onNavigateBack={() => setActiveTab('inspector')}
              />
            ) : (
              <>
                {/* VIEW 1: Rule Detail / Source of Truth Editor */}
                {activeTab === 'registry' && (
                  <RuleDetailView
                    apiBase={API_BASE}
                    onNavigate={(tab) => setActiveTab(tab)}
                    initialRuleCode={selectedRuleCode}
                    initialSearch={ruleSearchQuery}
                  />
                )}

                {/* VIEW: Fact Ledger & Codebase Verifier */}
                {activeTab === 'facts' && (
                  <CodebaseVerifierView apiBase={API_BASE} />
                )}

                {/* VIEW: Visual Identity Test Lab & Precision/Recall Harness (Admin only) */}
                {activeTab === 'visual_test_lab' && (
                  <VisualTestLabView
                    apiBase={API_BASE}
                    onNavigate={(tab) => setActiveTab(tab)}
                  />
                )}

                {/* VIEW 2 & Pre-Flight: Creator Pre-Flight Inspector & Exception Request */}
                {activeTab === 'inspector' && (
                  <>
                    {inspectorSubView === 'exception_request' ? (
                      <ExceptionRequestView
                        apiBase={API_BASE}
                        draftContext={exceptionDraftContext}
                        onBackToInspection={() => setInspectorSubView('scan')}
                        onSubmitSuccess={() => {
                          if (isAdmin) {
                            setActiveTab('queue');
                            setQueueSubView('review');
                          } else {
                            setActiveTab('workspaces');
                          }
                        }}
                      />
                    ) : (
                      <PreFlightInspectorView
                        apiBase={API_BASE}
                        initialSubmissionId={selectedSubmissionId}
                        onRequestException={(ctx) => {
                          setExceptionDraftContext(ctx || null);
                          setInspectorSubView('exception_request');
                        }}
                        onNavigateToRule={(ruleCode) => {
                          if (isAdmin) {
                            setActiveTab('registry');
                          }
                        }}
                      />
                    )}
                  </>
                )}

                {/* VIEW 3 & VIEW 4: Manager Review Queue (Sign-Off vs Decided) */}
                {activeTab === 'queue' && (
                  <>
                    {queueSubView === 'review' ? (
                      <ManagerQueueView
                        apiBase={API_BASE}
                        onSelectApprovedHandoff={(exceptionId) => {
                          setQueueSubView('decided');
                        }}
                      />
                    ) : (
                      <DecidedView
                        onBackToQueue={() => setQueueSubView('review')}
                        onViewAuditTrail={() => {}}
                        onOpenPublishHandoff={() => {}}
                      />
                    )}
                  </>
                )}

                {/* VIEW 5: Telemetry & Analytics Dashboard (Telemetry & Audit Log) */}
                {(activeTab === 'telemetry' || activeTab === 'audit_log') && (
                  <TelemetryView
                    apiBase={API_BASE}
                    onSelectRule={(ruleId) => {
                      setActiveTab('registry');
                    }}
                    onViewAllRules={() => {
                      setActiveTab('registry');
                    }}
                  />
                )}

                {/* VIEW 6: Team Management & Settings */}
                {(activeTab === 'team' || activeTab === 'settings') && (
                  <TeamManagementView apiBase={API_BASE} />
                )}

                {/* VIEW: Rule Guide for Writers */}
                {activeTab === 'guide' && (
                  <RuleDetailView
                    apiBase={API_BASE}
                    onNavigate={(tab) => setActiveTab(tab)}
                    initialRuleCode={selectedRuleCode}
                    initialSearch={ruleSearchQuery}
                  />
                )}

                {/* Workspaces & My Submissions View */}
                {(activeTab === 'workspaces' || activeTab === 'submissions') && (
                  <WorkspacesView
                    apiBase={API_BASE}
                    onNavigateToInspector={() => {
                      setSelectedSubmissionId(null);
                      setActiveTab('inspector');
                      setInspectorSubView('scan');
                    }}
                    onSelectSubmission={(subId) => {
                      setSelectedSubmissionId(subId);
                      setActiveTab('inspector');
                      setInspectorSubView('scan');
                    }}
                  />
                )}

                {/* VIEW 7: Forest Design System Showcase */}
                {activeTab === 'design' && (
                  <DesignShowcaseView />
                )}
              </>
            )}
          </main>
        </div>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <ThemeProvider>
      <LanguageProvider>
        <ServerHealthProvider>
          <AuthProvider>
            <CompanyProvider>
              <RealtimeProvider>
                <MainApp />
              </RealtimeProvider>
            </CompanyProvider>
          </AuthProvider>
        </ServerHealthProvider>
      </LanguageProvider>
    </ThemeProvider>
  );
}
