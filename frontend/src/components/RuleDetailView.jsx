import React, { useState, useEffect } from 'react';
import {
  FlaskConical,
  GitBranch,
  Check,
  X,
  ShieldAlert,
  ShieldCheck,
  CheckCircle2,
  ChevronRight,
  Edit3,
  Search,
  Filter,
  UploadCloud,
  Globe,
  RotateCcw,
  Plus,
  Trash2,
  ExternalLink,
  FileText,
  AlertTriangle,
  History,
  Sliders,
  Sparkles,
  Layers,
  ArrowRight,
  Lock,
  RefreshCw,
  Copy,
  Info,
  Clock
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { API_BASE } from '../config/api';

export default function RuleDetailView({
  apiBase = API_BASE,
  onNavigate,
  initialPillar = 'ALL',
  initialSearch = '',
  initialRuleCode = null,
}) {
  const { user, token, isAdmin, isWriter } = useAuth();

  // Primary State
  const [rules, setRules] = useState([]);
  const [drafts, setDrafts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('active_rules'); // 'active_rules' | 'draft_rules'
  const [pillarFilter, setPillarFilter] = useState(initialPillar); // 'ALL' | 'VISUAL' | 'FACTUAL' | 'TONE'
  const [severityFilter, setSeverityFilter] = useState('ALL'); // 'ALL' | 'BLOCKER' | 'WARNING'

  useEffect(() => {
    if (initialPillar) {
      setPillarFilter(initialPillar);
    }
  }, [initialPillar]);
  const [searchQuery, setSearchQuery] = useState(initialSearch || '');
  const [toastMessage, setToastMessage] = useState('');
  const [toastType, setToastType] = useState('success'); // 'success' | 'error' | 'info'

  // Modals & Drawers
  const [selectedRule, setSelectedRule] = useState(null); // For Detail Drawer
  const [isEditDrawerOpen, setIsEditDrawerOpen] = useState(false);
  const [editFormData, setEditFormData] = useState({});

  // Version History Modal
  const [versionModalOpen, setVersionModalOpen] = useState(false);
  const [versionRule, setVersionRule] = useState(null);
  const [versionHistory, setVersionHistory] = useState([]);
  const [loadingVersions, setLoadingVersions] = useState(false);
  const [selectedTargetVersion, setSelectedTargetVersion] = useState(null);

  // Import from URL (SSRF-safe scraper) Modal
  const [scraperModalOpen, setScraperModalOpen] = useState(false);
  const [scrapeUrl, setScrapeUrl] = useState('https://novapay.io');
  const [scraping, setScraping] = useState(false);
  const [scrapePreview, setScrapePreview] = useState(null);
  const [selectedPreviewItems, setSelectedPreviewItems] = useState({});
  const [importingScrape, setImportingScrape] = useState(false);
  const [scraperError, setScraperError] = useState('');

  // Multi-Format Upload Modal
  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  const [uploadTab, setUploadTab] = useState('file'); // 'file' | 'paste'
  const [uploadFile, setUploadFile] = useState(null);
  const [pastedContent, setPastedContent] = useState('');
  const [pastedFilename, setPastedFilename] = useState('brand_guidelines.yaml');
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState('');
  const [uploadSuccessSummary, setUploadSuccessSummary] = useState(null);

  // Rule Playground Modal
  const [playgroundModalOpen, setPlaygroundModalOpen] = useState(false);
  const [playgroundRuleCode, setPlaygroundRuleCode] = useState('');
  const [playgroundDraftId, setPlaygroundDraftId] = useState('');
  const [playgroundText, setPlaygroundText] = useState('Instant, zero-fee international transfers across all countries.');
  const [playgroundTesting, setPlaygroundTesting] = useState(false);
  const [playgroundResult, setPlaygroundResult] = useState(null);

  // New Rule Creation Modal
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [createFormData, setCreateFormData] = useState({
    rule_code: '',
    title: '',
    pillar: 'TONE',
    severity: 'BLOCKER',
    enforcement: 'Block publish',
    claims_allowed: '',
    claims_disallowed: '',
    banned_term: '',
    replacement: '',
    rule_description: '',
    source: 'NovaPay Brand Guidelines 2026'
  });

  const showToast = (msg, type = 'success') => {
    setToastMessage(msg);
    setToastType(type);
    setTimeout(() => setToastMessage(''), 3500);
  };

  // Helper auth headers
  const getAuthHeaders = (isJson = true) => {
    const headers = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;
    if (isJson) headers['Content-Type'] = 'application/json';
    return headers;
  };

  // Fetch all active rules
  const fetchRules = async () => {
    try {
      setLoading(true);
      let url = `${apiBase}/api/rules/?status=all`;
      const res = await fetch(url, { headers: getAuthHeaders(false) });
      if (res.ok) {
        const data = await res.json();
        setRules(data.rules || []);
      }
    } catch (err) {
      console.error('Failed to load rules:', err);
    } finally {
      setLoading(false);
    }
  };

  // Fetch pending drafts
  const fetchDrafts = async () => {
    if (!isAdmin) return;
    try {
      const res = await fetch(`${apiBase}/api/rules/drafts/`, { headers: getAuthHeaders(false) });
      if (res.ok) {
        const data = await res.json();
        setDrafts(data.drafts || []);
      }
    } catch (err) {
      console.error('Failed to load drafts:', err);
    }
  };

  useEffect(() => {
    fetchRules();
    if (isAdmin) fetchDrafts();
  }, [apiBase, isAdmin]);

  // Open detail drawer for a rule
  const handleOpenDetail = async (rule) => {
    try {
      const res = await fetch(`${apiBase}/api/rules/${rule.rule_code}/`, { headers: getAuthHeaders(false) });
      if (res.ok) {
        const fullRule = await res.json();
        setSelectedRule(fullRule);
        setEditFormData({
          title: fullRule.title,
          severity: fullRule.severity,
          claims_allowed: fullRule.claims_allowed || '',
          claims_disallowed: fullRule.claims_disallowed || '',
          rule_description: fullRule.rule_description || '',
          change_note: ''
        });
        setIsEditDrawerOpen(true);
      } else {
        setSelectedRule(rule);
        setEditFormData({
          title: rule.title,
          severity: rule.severity,
          claims_allowed: rule.claims_allowed || '',
          claims_disallowed: rule.claims_disallowed || '',
          rule_description: rule.rule_description || '',
          change_note: ''
        });
        setIsEditDrawerOpen(true);
      }
    } catch (err) {
      setSelectedRule(rule);
      setIsEditDrawerOpen(true);
    }
  };

  // Synchronize when opened via global search (initialRuleCode or initialSearch)
  useEffect(() => {
    if (initialRuleCode) {
      setSearchQuery(initialRuleCode);
      const match = rules.find((r) => r.rule_code === initialRuleCode);
      if (match) {
        handleOpenDetail(match);
      }
    } else if (initialSearch !== undefined && initialSearch !== '') {
      setSearchQuery(initialSearch);
    }
  }, [initialRuleCode, initialSearch, rules]);

  // Save rule updates (PUT/PATCH)
  const handleSaveRuleEdit = async () => {
    if (!isAdmin) {
      showToast('Action forbidden: Admin role required.', 'error');
      return;
    }
    try {
      const res = await fetch(`${apiBase}/api/rules/${selectedRule.rule_code}/`, {
        method: 'PUT',
        headers: getAuthHeaders(true),
        body: JSON.stringify(editFormData)
      });
      if (res.ok) {
        const data = await res.json();
        showToast(`Rule ${selectedRule.rule_code} updated to v${data.rule.version}.`);
        setIsEditDrawerOpen(false);
        fetchRules();
      } else {
        const err = await res.json();
        showToast(err.error || 'Failed to update rule.', 'error');
      }
    } catch (err) {
      showToast('Network error while saving rule.', 'error');
    }
  };

  // Open Version History & Rollback Modal
  const handleOpenVersionModal = async (rule) => {
    setVersionRule(rule);
    setVersionModalOpen(true);
    setLoadingVersions(true);
    setSelectedTargetVersion(null);
    try {
      const res = await fetch(`${apiBase}/api/rules/${rule.rule_code}/versions/`, { headers: getAuthHeaders(false) });
      if (res.ok) {
        const data = await res.json();
        setVersionHistory(data.versions || []);
      } else {
        setVersionHistory([]);
      }
    } catch (err) {
      setVersionHistory([]);
    } finally {
      setLoadingVersions(false);
    }
  };

  // Perform Rollback
  const handlePerformRollback = async () => {
    if (!selectedTargetVersion || !versionRule) return;
    if (!isAdmin) {
      showToast('Action forbidden: Admin role required.', 'error');
      return;
    }
    try {
      const res = await fetch(`${apiBase}/api/rules/${versionRule.rule_code}/rollback/`, {
        method: 'POST',
        headers: getAuthHeaders(true),
        body: JSON.stringify({ target_version: selectedTargetVersion.version_number })
      });
      if (res.ok) {
        const data = await res.json();
        showToast(data.message || `Rolled back to v${selectedTargetVersion.version_number}.`);
        setVersionModalOpen(false);
        fetchRules();
        if (selectedRule && selectedRule.rule_code === versionRule.rule_code) {
          handleOpenDetail(data.rule);
        }
      } else {
        const err = await res.json();
        showToast(err.error || 'Failed to rollback rule.', 'error');
      }
    } catch (err) {
      showToast('Network error while executing rollback.', 'error');
    }
  };

  // Scraper Step 1: Preview scrape
  const handleRunScrapePreview = async () => {
    setScraperError('');
    setScrapePreview(null);
    setScraping(true);
    try {
      const res = await fetch(`${apiBase}/api/rules/scrape/`, {
        method: 'POST',
        headers: getAuthHeaders(true),
        body: JSON.stringify({ url: scrapeUrl, import_selected: false })
      });
      const data = await res.json();
      if (res.ok && data.status === 'success') {
        setScrapePreview(data);
        // Default select all items
        const initialSelected = {};
        (data.preview_items || []).forEach((item) => {
          initialSelected[item.id] = true;
        });
        setSelectedPreviewItems(initialSelected);
      } else {
        setScraperError(data.error || 'SSRF inspection rejected the URL or extraction failed.');
      }
    } catch (err) {
      setScraperError('Failed to communicate with SSRF-safe scraper endpoint.');
    } finally {
      setScraping(false);
    }
  };

  // Scraper Step 2: Import selected items
  const handleImportScrapedItems = async () => {
    if (!scrapePreview) return;
    setImportingScrape(true);
    try {
      const selectedList = (scrapePreview.preview_items || []).filter(
        (item) => selectedPreviewItems[item.id]
      );
      const res = await fetch(`${apiBase}/api/rules/scrape/`, {
        method: 'POST',
        headers: getAuthHeaders(true),
        body: JSON.stringify({
          url: scrapeUrl,
          import_selected: true,
          selected_items: selectedList
        })
      });
      const data = await res.json();
      if (res.ok && data.status === 'success') {
        showToast(data.message || 'Imported as unverified facts and draft rules.');
        setScraperModalOpen(false);
        setScrapePreview(null);
        fetchDrafts();
        fetchRules();
        setActiveTab('draft_rules');
      } else {
        showToast(data.error || 'Failed to import scraped items.', 'error');
      }
    } catch (err) {
      showToast('Network error while importing scraped items.', 'error');
    } finally {
      setImportingScrape(false);
    }
  };

  // Multi-Format Upload Handler
  const handleUploadRules = async (e) => {
    e.preventDefault();
    setUploadError('');
    setUploading(true);
    setUploadSuccessSummary(null);

    try {
      let res;
      if (uploadTab === 'file') {
        if (!uploadFile) {
          setUploadError('Please select a file to upload.');
          setUploading(false);
          return;
        }
        const formData = new FormData();
        formData.append('file', uploadFile);
        formData.append('filename', uploadFile.name);

        res = await fetch(`${apiBase}/api/rules/upload/`, {
          method: 'POST',
          headers: getAuthHeaders(false),
          body: formData
        });
      } else {
        if (!pastedContent.trim()) {
          setUploadError('Please paste policy content or markdown rules.');
          setUploading(false);
          return;
        }
        res = await fetch(`${apiBase}/api/rules/upload/`, {
          method: 'POST',
          headers: getAuthHeaders(true),
          body: JSON.stringify({
            rules_text: pastedContent,
            filename: pastedFilename
          })
        });
      }

      const data = await res.json();
      if (res.ok && data.status === 'success') {
        setUploadSuccessSummary(data);
        showToast(`Staged ${data.count} DRAFT rules for review.`);
        fetchDrafts();
      } else {
        setUploadError(data.error || 'Failed to parse rule file.');
      }
    } catch (err) {
      setUploadError('Network error while uploading rule file.');
    } finally {
      setUploading(false);
    }
  };

  // Approve or Reject Draft Rule
  const handleDecideDraft = async (draftId, action, edits = null) => {
    try {
      const payload = {
        draft_ids: [draftId],
        action: action
      };
      if (edits) {
        payload.edits = { [draftId]: edits };
      }
      const res = await fetch(`${apiBase}/api/rules/drafts/approve/`, {
        method: 'POST',
        headers: getAuthHeaders(true),
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (res.ok && data.status === 'success') {
        showToast(action === 'APPROVE' ? 'Draft rule approved and activated!' : 'Draft rule rejected.');
        fetchDrafts();
        fetchRules();
      } else {
        showToast(data.error || 'Failed to process draft rule.', 'error');
      }
    } catch (err) {
      showToast('Network error while processing draft.', 'error');
    }
  };

  // Rule Playground Runner
  const handleRunPlayground = async () => {
    setPlaygroundTesting(true);
    setPlaygroundResult(null);
    try {
      const body = {
        test_text: playgroundText
      };
      if (playgroundDraftId) {
        body.draft_id = playgroundDraftId;
      } else {
        body.rule_code = playgroundRuleCode || (rules[0]?.rule_code || 'TONE_001');
      }

      const res = await fetch(`${apiBase}/api/rules/playground/`, {
        method: 'POST',
        headers: getAuthHeaders(true),
        body: JSON.stringify(body)
      });
      const data = await res.json();
      if (res.ok) {
        setPlaygroundResult(data);
      } else {
        showToast(data.error || 'Playground test failed.', 'error');
      }
    } catch (err) {
      showToast('Network error while running playground test.', 'error');
    } finally {
      setPlaygroundTesting(false);
    }
  };

  // Create New Rule Handler
  const handleCreateNewRule = async (e) => {
    e.preventDefault();
    if (!isAdmin) {
      showToast('Action forbidden: Admin role required.', 'error');
      return;
    }
    try {
      const res = await fetch(`${apiBase}/api/rules/`, {
        method: 'POST',
        headers: getAuthHeaders(true),
        body: JSON.stringify(createFormData)
      });
      const data = await res.json();
      if (res.ok && data.status === 'success') {
        showToast(`Rule ${data.rule.rule_code} created successfully!`);
        setCreateModalOpen(false);
        fetchRules();
      } else {
        showToast(data.error || 'Failed to create rule.', 'error');
      }
    } catch (err) {
      showToast('Network error creating rule.', 'error');
    }
  };

  // Filtered Rules
  const filteredRules = rules.filter((r) => {
    if (pillarFilter !== 'ALL' && r.pillar !== pillarFilter) return false;
    if (severityFilter !== 'ALL' && r.severity !== severityFilter) return false;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchCode = (r.rule_code || '').toLowerCase().includes(q);
      const matchTitle = (r.title || '').toLowerCase().includes(q);
      const matchDesc = (r.rule_description || '').toLowerCase().includes(q);
      const matchAllowed = (r.claims_allowed || '').toLowerCase().includes(q);
      const matchDisallowed = (r.claims_disallowed || '').toLowerCase().includes(q);
      return matchCode || matchTitle || matchDesc || matchAllowed || matchDisallowed;
    }
    return true;
  });

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 animate-fade-in">
      {/* Toast Notification */}
      {toastMessage && (
        <div
          className={`fixed bottom-6 right-6 z-50 px-5 py-3.5 rounded-xl shadow-2xl flex items-center space-x-3 text-sm font-medium transition-all ${
            toastType === 'error'
              ? 'bg-rose-950 text-rose-100 border border-rose-800'
              : 'bg-emerald-950 text-emerald-100 border border-emerald-800'
          }`}
        >
          {toastType === 'error' ? <AlertTriangle className="w-5 h-5 text-rose-400" /> : <CheckCircle2 className="w-5 h-5 text-emerald-400" />}
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between pb-6 border-b border-zinc-200 gap-4">
        <div>
          <div className="flex items-center space-x-3">
            <h1 className="text-2xl font-bold tracking-tight text-zinc-900">Rule Registry & Governance Engine</h1>
            
          </div>
          <p className="mt-1 text-sm text-zinc-500">
            Deterministic source of truth compiler for NovaPay marketing communications. Changes are immutable and version-stamped.
          </p>
        </div>

        {/* Global Action Buttons */}
        <div className="flex items-center flex-wrap gap-2.5">
          <button
            onClick={() => {
              setPlaygroundRuleCode(rules[0]?.rule_code || '');
              setPlaygroundModalOpen(true);
            }}
            className="inline-flex items-center px-3.5 py-2 border border-zinc-300 shadow-sm text-xs font-semibold rounded-lg text-zinc-700 bg-white hover:bg-zinc-50 transition"
          >
            <FlaskConical className="w-4 h-4 mr-1.5 text-emerald-600" />
            Rule Playground
          </button>

          {isAdmin && (
            <>
              <button
                onClick={() => setScraperModalOpen(true)}
                className="inline-flex items-center px-3.5 py-2 border border-zinc-300 shadow-sm text-xs font-semibold rounded-lg text-zinc-700 bg-white hover:bg-zinc-50 transition"
              >
                <Globe className="w-4 h-4 mr-1.5 text-blue-600" />
                Import from URL
              </button>

              <button
                onClick={() => setUploadModalOpen(true)}
                className="inline-flex items-center px-3.5 py-2 border border-zinc-300 shadow-sm text-xs font-semibold rounded-lg text-zinc-700 bg-white hover:bg-zinc-50 transition"
              >
                <UploadCloud className="w-4 h-4 mr-1.5 text-indigo-600" />
                Upload Rules
              </button>

              <button
                onClick={() => setCreateModalOpen(true)}
                className="inline-flex items-center px-4 py-2 border border-transparent text-xs font-semibold rounded-lg shadow-sm text-white bg-emerald-600 hover:bg-emerald-700 transition"
              >
                <Plus className="w-4 h-4 mr-1" />
                New Rule
              </button>
            </>
          )}
        </div>
      </div>

      {/* Stats Summary Bar */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 my-6">
        <div className="bg-white p-4 rounded-xl border border-zinc-200 shadow-sm">
          <span className="text-xs font-medium text-zinc-500">Active Published Rules</span>
          <div className="mt-1 flex items-baseline justify-between">
            <span className="text-2xl font-bold text-zinc-900">{rules.filter((r) => r.is_active).length}</span>
            <span className="text-xs font-semibold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded">Enforcing</span>
          </div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-zinc-200 shadow-sm">
          <span className="text-xs font-medium text-zinc-500">Publication Blockers</span>
          <div className="mt-1 flex items-baseline justify-between">
            <span className="text-2xl font-bold text-rose-600">
              {rules.filter((r) => r.severity === 'BLOCKER' && r.is_active).length}
            </span>
            <span className="text-xs font-semibold text-rose-700 bg-rose-50 px-2 py-0.5 rounded">Strict Stop</span>
          </div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-zinc-200 shadow-sm">
          <span className="text-xs font-medium text-zinc-500">Advisory Warnings</span>
          <div className="mt-1 flex items-baseline justify-between">
            <span className="text-2xl font-bold text-amber-600">
              {rules.filter((r) => r.severity === 'WARNING' && r.is_active).length}
            </span>
            <span className="text-xs font-semibold text-amber-700 bg-amber-50 px-2 py-0.5 rounded">Soft Linter</span>
          </div>
        </div>

        <div
          onClick={() => isAdmin && drafts.length > 0 && setActiveTab('draft_rules')}
          className={`bg-white p-4 rounded-xl border transition ${
            drafts.length > 0 ? 'border-indigo-300 bg-indigo-50/20 cursor-pointer hover:border-indigo-400' : 'border-zinc-200'
          } shadow-sm`}
        >
          <span className="text-xs font-medium text-zinc-500">Pending Drafts (Unverified)</span>
          <div className="mt-1 flex items-baseline justify-between">
            <span className="text-2xl font-bold text-indigo-600">{drafts.length}</span>
            <span className="text-xs font-semibold text-indigo-700 bg-indigo-100 px-2 py-0.5 rounded">
              {drafts.length > 0 ? 'Needs Admin Sign-Off' : 'Clean'}
            </span>
          </div>
        </div>
      </div>

      {/* View Switcher: Active Rules vs Pending Drafts */}
      <div className="flex items-center space-x-3 border-b border-zinc-200 pb-2 mb-6">
        <button
          onClick={() => setActiveTab('active_rules')}
          className={`pb-2 px-1 text-sm font-semibold transition border-b-2 flex items-center space-x-2 ${
            activeTab === 'active_rules'
              ? 'border-emerald-600 text-emerald-700'
              : 'border-transparent text-zinc-500 hover:text-zinc-700'
          }`}
        >
          <Layers className="w-4 h-4" />
          <span>Active Rules Registry ({rules.length})</span>
        </button>

        {isAdmin && (
          <button
            onClick={() => setActiveTab('draft_rules')}
            className={`pb-2 px-1 text-sm font-semibold transition border-b-2 flex items-center space-x-2 ${
              activeTab === 'draft_rules'
                ? 'border-indigo-600 text-indigo-700'
                : 'border-transparent text-zinc-500 hover:text-zinc-700'
            }`}
          >
            <Clock className="w-4 h-4" />
            <span>Staged Draft Review Queue ({drafts.length})</span>
            {drafts.length > 0 && (
              <span className="ml-1.5 px-2 py-0.5 text-xs font-bold rounded-full bg-indigo-600 text-white">
                {drafts.length}
              </span>
            )}
          </button>
        )}
      </div>

      {/* ============================================================== */}
      {/* TAB 1: ACTIVE RULES REGISTRY                                    */}
      {/* ============================================================== */}
      {activeTab === 'active_rules' && (
        <div className="space-y-4">
          {/* Controls & Search */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 bg-zinc-50 p-3 rounded-xl border border-zinc-200">
            {/* Search Input */}
            <div className="relative flex-1 min-w-[240px]">
              <Search className="w-4 h-4 absolute left-3 top-3 text-zinc-400" />
              <input
                type="text"
                placeholder="Search rule code, title, allowed or disallowed claims..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-9 pr-4 py-2 bg-white border border-zinc-300 rounded-lg text-sm text-zinc-900 focus:outline-none focus:ring-2 focus:ring-emerald-500"
              />
            </div>

            {/* Pillar Filter Pills */}
            <div className="flex items-center space-x-1.5 overflow-x-auto pb-1 sm:pb-0">
              {['ALL', 'VISUAL', 'FACTUAL', 'TONE'].map((pillar) => (
                <button
                  key={pillar}
                  onClick={() => setPillarFilter(pillar)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                    pillarFilter === pillar
                      ? 'bg-zinc-900 text-white shadow-sm'
                      : 'bg-white text-zinc-600 border border-zinc-200 hover:bg-zinc-100'
                  }`}
                >
                  {pillar}
                </button>
              ))}
            </div>

            {/* Severity Filter */}
            <div className="flex items-center space-x-1.5">
              {['ALL', 'BLOCKER', 'WARNING'].map((sev) => (
                <button
                  key={sev}
                  onClick={() => setSeverityFilter(sev)}
                  className={`px-2.5 py-1.5 rounded-lg text-xs font-semibold transition ${
                    severityFilter === sev
                      ? sev === 'BLOCKER'
                        ? 'bg-rose-600 text-white'
                        : sev === 'WARNING'
                        ? 'bg-amber-600 text-white'
                        : 'bg-zinc-900 text-white'
                      : 'bg-white text-zinc-600 border border-zinc-200 hover:bg-zinc-100'
                  }`}
                >
                  {sev}
                </button>
              ))}
            </div>
          </div>

          {/* Rules Table */}
          <div className="bg-white rounded-xl border border-zinc-200 shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-zinc-200">
                <thead className="bg-zinc-50/75">
                  <tr>
                    <th scope="col" className="px-5 py-3 text-left text-xs font-semibold text-zinc-500 uppercase tracking-wider">
                      Rule Code
                    </th>
                    <th scope="col" className="px-5 py-3 text-left text-xs font-semibold text-zinc-500 uppercase tracking-wider">
                      Pillar & Severity
                    </th>
                    <th scope="col" className="px-5 py-3 text-left text-xs font-semibold text-zinc-500 uppercase tracking-wider">
                      Title & Specification
                    </th>
                    <th scope="col" className="px-5 py-3 text-left text-xs font-semibold text-zinc-500 uppercase tracking-wider">
                      Allowed Claim / Fix
                    </th>
                    <th scope="col" className="px-5 py-3 text-left text-xs font-semibold text-zinc-500 uppercase tracking-wider">
                      Version
                    </th>
                    <th scope="col" className="px-5 py-3 text-right text-xs font-semibold text-zinc-500 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-100 bg-white">
                  {loading ? (
                    <tr>
                      <td colSpan="6" className="px-6 py-12 text-center text-sm text-zinc-500">
                        <RefreshCw className="w-6 h-6 animate-spin mx-auto text-emerald-600 mb-2" />
                        Loading rule specifications...
                      </td>
                    </tr>
                  ) : filteredRules.length === 0 ? (
                    <tr>
                      <td colSpan="6" className="px-6 py-12 text-center text-sm text-zinc-500">
                        No rules matching your filter criteria.
                      </td>
                    </tr>
                  ) : (
                    filteredRules.map((r) => (
                      <tr
                        key={r.rule_code}
                        className="hover:bg-zinc-50/80 transition cursor-pointer group"
                        onClick={() => handleOpenDetail(r)}
                      >
                        <td className="px-5 py-4 whitespace-nowrap">
                          <div className="flex items-center space-x-2">
                            <span className="font-mono text-xs font-bold text-zinc-900 bg-zinc-100 px-2 py-1 rounded border border-zinc-200 group-hover:border-emerald-300">
                              {r.rule_code}
                            </span>
                            {!r.is_active && (
                              <span className="px-1.5 py-0.5 text-[10px] font-semibold bg-zinc-200 text-zinc-600 rounded">
                                Inactive
                              </span>
                            )}
                          </div>
                        </td>

                        <td className="px-5 py-4 whitespace-nowrap">
                          <div className="flex items-center space-x-1.5">
                            <span
                              className={`px-2 py-0.5 rounded text-[11px] font-semibold ${
                                r.pillar === 'VISUAL'
                                  ? 'bg-indigo-100 text-indigo-800'
                                  : r.pillar === 'FACTUAL'
                                  ? 'bg-blue-100 text-blue-800'
                                  : 'bg-emerald-100 text-emerald-800'
                              }`}
                            >
                              {r.pillar}
                            </span>
                            <span
                              className={`px-2 py-0.5 rounded text-[11px] font-semibold ${
                                r.severity === 'BLOCKER'
                                  ? 'bg-rose-100 text-rose-800'
                                  : 'bg-amber-100 text-amber-800'
                              }`}
                            >
                              {r.severity}
                            </span>
                          </div>
                        </td>

                        <td className="px-5 py-4 max-w-sm">
                          <div className="text-sm font-semibold text-zinc-900 group-hover:text-emerald-700 transition">
                            {r.title}
                          </div>
                          <div className="text-xs text-zinc-500 line-clamp-1 mt-0.5">
                            {r.rule_description || 'Standard deterministic rule constraint.'}
                          </div>
                        </td>

                        <td className="px-5 py-4 max-w-xs">
                          {r.claims_allowed ? (
                            <span className="inline-block text-xs text-emerald-800 bg-emerald-50 px-2 py-1 rounded border border-emerald-200 line-clamp-1">
                              ✓ {r.claims_allowed}
                            </span>
                          ) : (
                            <span className="text-xs text-zinc-400 italic">None specified</span>
                          )}
                        </td>

                        <td className="px-5 py-4 whitespace-nowrap">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleOpenVersionModal(r);
                            }}
                            className="inline-flex items-center px-2 py-1 text-xs font-mono font-semibold rounded bg-zinc-100 hover:bg-zinc-200 text-zinc-700 transition border border-zinc-200"
                            title="View version history & rollback"
                          >
                            <GitBranch className="w-3.5 h-3.5 mr-1 text-zinc-500" />
                            v{r.version || 1}
                          </button>
                        </td>

                        <td className="px-5 py-4 whitespace-nowrap text-right text-xs font-medium space-x-2">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              setPlaygroundRuleCode(r.rule_code);
                              setPlaygroundModalOpen(true);
                            }}
                            className="text-zinc-600 hover:text-emerald-600 p-1.5 rounded hover:bg-zinc-100 transition inline-flex items-center"
                            title="Test in Playground"
                          >
                            <FlaskConical className="w-4 h-4" />
                          </button>

                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleOpenVersionModal(r);
                            }}
                            className="text-zinc-600 hover:text-blue-600 p-1.5 rounded hover:bg-zinc-100 transition inline-flex items-center"
                            title="Version History & Rollback"
                          >
                            <History className="w-4 h-4" />
                          </button>

                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleOpenDetail(r);
                            }}
                            className="text-zinc-600 hover:text-zinc-900 p-1.5 rounded hover:bg-zinc-100 transition inline-flex items-center"
                            title="Inspect Rule Specification"
                          >
                            <ChevronRight className="w-4 h-4" />
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* ============================================================== */}
      {/* TAB 2: PENDING DRAFTS QUEUE (PARSED & SCRAPED ITEMS)            */}
      {/* ============================================================== */}
      {activeTab === 'draft_rules' && isAdmin && (
        <div className="space-y-4">
          <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 flex items-start space-x-3">
            <Info className="w-5 h-5 text-amber-700 mt-0.5 flex-shrink-0" />
            <div className="text-xs text-amber-900 leading-relaxed">
              <span className="font-semibold">Deterministic Safety Guardrail: </span>
              All parsed rules and scraped website claims remain staged in <code className="font-mono bg-amber-100 px-1 py-0.5 rounded">DRAFT / UNVERIFIED</code> status.
              They do <strong>not</strong> affect pre-flight publication scoring until an administrator explicitly reviews and approves them into active enforcement.
            </div>
          </div>

          {drafts.length === 0 ? (
            <div className="bg-white rounded-xl border border-zinc-200 p-12 text-center">
              <CheckCircle2 className="w-10 h-10 text-emerald-500 mx-auto mb-3" />
              <h3 className="text-base font-bold text-zinc-900">No Pending Draft Rules</h3>
              <p className="text-sm text-zinc-500 mt-1 max-w-md mx-auto">
                All parsed policies and scraped brand items have been approved or rejected. Upload a guideline document or import from a URL to stage new draft rules.
              </p>
              <div className="mt-5 flex items-center justify-center space-x-3">
                <button
                  onClick={() => setUploadModalOpen(true)}
                  className="px-3.5 py-2 text-xs font-semibold rounded-lg bg-indigo-600 text-white hover:bg-indigo-700 transition"
                >
                  Upload Guidelines Document
                </button>
                <button
                  onClick={() => setScraperModalOpen(true)}
                  className="px-3.5 py-2 text-xs font-semibold rounded-lg border border-zinc-300 text-zinc-700 hover:bg-zinc-50 transition"
                >
                  Scrape Brand URL
                </button>
              </div>
            </div>
          ) : (
            <div className="bg-white rounded-xl border border-zinc-200 shadow-sm overflow-hidden">
              <div className="p-4 border-b border-zinc-200 flex items-center justify-between">
                <span className="text-sm font-bold text-zinc-900">
                  {drafts.length} Staged Draft Rules Awaiting Sign-Off
                </span>
                <span className="text-xs text-zinc-500">
                  Review claims carefully before activating into the audit engine
                </span>
              </div>

              <div className="divide-y divide-zinc-200">
                {drafts.map((draft) => (
                  <div key={draft.id} className="p-5 hover:bg-zinc-50/50 transition">
                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                      <div className="flex items-start space-x-3">
                        <span className="font-mono text-xs font-bold text-indigo-700 bg-indigo-50 border border-indigo-200 px-2 py-1 rounded">
                          {draft.rule_code}
                        </span>
                        <div>
                          <div className="flex items-center space-x-2">
                            <h4 className="text-sm font-bold text-zinc-900">{draft.title}</h4>
                            <span className="px-2 py-0.5 text-[10px] font-bold rounded bg-amber-100 text-amber-800">
                              DRAFT
                            </span>
                            <span className="px-2 py-0.5 text-[10px] font-semibold rounded bg-zinc-100 text-zinc-700">
                              Source: {draft.source_type} ({draft.source})
                            </span>
                          </div>
                          <p className="text-xs text-zinc-600 mt-1">
                            {draft.rule_description || 'Staged policy rule drafted from upload/scrape.'}
                          </p>
                        </div>
                      </div>

                      {/* Action buttons for draft */}
                      <div className="flex items-center space-x-2 self-end md:self-center">
                        <button
                          onClick={() => {
                            setPlaygroundDraftId(draft.id);
                            setPlaygroundModalOpen(true);
                          }}
                          className="px-2.5 py-1.5 text-xs font-semibold rounded border border-zinc-300 text-zinc-700 hover:bg-zinc-100 transition flex items-center"
                          title="Test in Playground before approval"
                        >
                          <FlaskConical className="w-3.5 h-3.5 mr-1 text-emerald-600" />
                          Test
                        </button>

                        <button
                          onClick={() => handleDecideDraft(draft.id, 'REJECT')}
                          className="px-3 py-1.5 text-xs font-semibold rounded border border-rose-200 text-rose-700 bg-rose-50 hover:bg-rose-100 transition"
                        >
                          Reject
                        </button>

                        <button
                          onClick={() => handleDecideDraft(draft.id, 'APPROVE')}
                          className="px-3.5 py-1.5 text-xs font-semibold rounded bg-emerald-600 text-white hover:bg-emerald-700 transition flex items-center shadow-sm"
                        >
                          <Check className="w-3.5 h-3.5 mr-1" />
                          Approve & Activate
                        </button>
                      </div>
                    </div>

                    {/* Claims Comparison Cards */}
                    <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-3 text-xs bg-zinc-50 p-3 rounded-lg border border-zinc-200">
                      <div>
                        <span className="font-semibold text-emerald-800">Allowed / Mandated Statement:</span>
                        <div className="text-zinc-700 mt-0.5 font-mono">
                          {draft.claims_allowed || '—'}
                        </div>
                      </div>
                      <div>
                        <span className="font-semibold text-rose-800">Disallowed / Banned Statement:</span>
                        <div className="text-zinc-700 mt-0.5 font-mono">
                          {draft.claims_disallowed || '—'}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ============================================================== */}
      {/* DRAWER: RULE DETAIL / SOURCE OF TRUTH INSPECTOR & EDITOR        */}
      {/* ============================================================== */}
      {isEditDrawerOpen && selectedRule && (
        <div className="fixed inset-0 z-50 overflow-hidden bg-zinc-950/40 backdrop-blur-sm flex justify-end animate-fade-in">
          <div className="w-full max-w-2xl bg-white h-full shadow-2xl flex flex-col justify-between overflow-y-auto">
            {/* Drawer Header */}
            <div className="p-6 border-b border-zinc-200">
              <div className="flex items-center justify-between">
                <span className="text-xs font-mono font-bold tracking-wider text-emerald-700 uppercase bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                  {selectedRule.breadcrumb || `RULE REGISTRY > ${selectedRule.pillar} > ${selectedRule.rule_code}`}
                </span>
                <button
                  onClick={() => setIsEditDrawerOpen(false)}
                  className="p-1 rounded-lg text-zinc-400 hover:text-zinc-700 hover:bg-zinc-100 transition"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              <div className="mt-4 flex items-center space-x-3">
                <h2 className="text-xl font-bold text-zinc-900">{selectedRule.title}</h2>
                <span className="px-2 py-0.5 text-xs font-mono font-bold rounded bg-zinc-100 text-zinc-800 border border-zinc-200">
                  v{selectedRule.version}
                </span>
              </div>
              <p className="text-xs text-zinc-500 mt-1">
                Owner: {selectedRule.owner || 'Brand Governance Lead'} · Enforcement: {selectedRule.enforcement || 'Block publish'}
              </p>
            </div>

            {/* Drawer Body */}
            <div className="p-6 space-y-6 flex-1">
              {/* Allowed vs Disallowed Claims Cards */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="p-4 rounded-xl bg-emerald-50/70 border border-emerald-200">
                  <div className="flex items-center space-x-1.5 text-xs font-bold text-emerald-800 uppercase tracking-wide">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                    <span>Compliant / Mandated Claims</span>
                  </div>
                  <p className="text-xs text-emerald-950 mt-2 font-medium leading-relaxed font-mono">
                    “{selectedRule.claims_allowed || 'Approved standard statement'}”
                  </p>
                </div>

                <div className="p-4 rounded-xl bg-rose-50/70 border border-rose-200">
                  <div className="flex items-center space-x-1.5 text-xs font-bold text-rose-800 uppercase tracking-wide">
                    <ShieldAlert className="w-4 h-4 text-rose-600" />
                    <span>Prohibited / Flagged Claims</span>
                  </div>
                  <p className="text-xs text-rose-950 mt-2 font-medium leading-relaxed font-mono">
                    “{selectedRule.claims_disallowed || 'Non-compliant claim or superlative'}”
                  </p>
                </div>
              </div>

              {/* Source Evidence & Fact Ledger Link */}
              <div className="bg-zinc-50 p-4 rounded-xl border border-zinc-200 space-y-2">
                <span className="text-xs font-bold text-zinc-700 uppercase tracking-wide">
                  Source Evidence & Verifiable Truth Link
                </span>
                <p className="text-xs text-zinc-600 italic">
                  "{selectedRule.source_evidence?.quote || selectedRule.rule_description}"
                </p>
                <div className="pt-2 border-t border-zinc-200 flex items-center justify-between text-xs text-zinc-500">
                  <span>Ledger: <strong className="text-zinc-700">{selectedRule.source_evidence?.ledger_entry || `LEDGER-${selectedRule.rule_code}`}</strong></span>
                  <span>Verified: <strong className="text-emerald-700">{selectedRule.source_evidence?.last_verified || 'Active Ledger'}</strong></span>
                </div>
              </div>

              {/* Admin Inline Edit Specification */}
              {isAdmin ? (
                <div className="border border-zinc-200 rounded-xl p-4 bg-white space-y-4">
                  <div className="flex items-center justify-between border-b border-zinc-200 pb-2">
                    <span className="text-xs font-bold text-zinc-900 flex items-center">
                      <Edit3 className="w-3.5 h-3.5 mr-1 text-emerald-600" />
                      Edit Rule Specification & Create Snapshot
                    </span>
                    <span className="text-[11px] text-zinc-500">
                      Saving increments version to v{(selectedRule.version || 1) + 1}
                    </span>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-zinc-700 mb-1">Rule Title</label>
                    <input
                      type="text"
                      value={editFormData.title || ''}
                      onChange={(e) => setEditFormData({ ...editFormData, title: e.target.value })}
                      className="w-full text-xs p-2.5 border border-zinc-300 rounded-lg focus:ring-2 focus:ring-emerald-500"
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs font-semibold text-zinc-700 mb-1">Severity</label>
                      <select
                        value={editFormData.severity || 'BLOCKER'}
                        onChange={(e) => setEditFormData({ ...editFormData, severity: e.target.value })}
                        className="w-full text-xs p-2.5 border border-zinc-300 rounded-lg bg-white"
                      >
                        <option value="BLOCKER">BLOCKER (Strict Stop)</option>
                        <option value="WARNING">WARNING (Advisory)</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-xs font-semibold text-zinc-700 mb-1">Allowed Claim / Fix</label>
                      <input
                        type="text"
                        value={editFormData.claims_allowed || ''}
                        onChange={(e) => setEditFormData({ ...editFormData, claims_allowed: e.target.value })}
                        className="w-full text-xs p-2.5 border border-zinc-300 rounded-lg"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-zinc-700 mb-1">Disallowed / Banned Claim</label>
                    <input
                      type="text"
                      value={editFormData.claims_disallowed || ''}
                      onChange={(e) => setEditFormData({ ...editFormData, claims_disallowed: e.target.value })}
                      className="w-full text-xs p-2.5 border border-zinc-300 rounded-lg"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-zinc-700 mb-1">Rule Description</label>
                    <textarea
                      rows={2}
                      value={editFormData.rule_description || ''}
                      onChange={(e) => setEditFormData({ ...editFormData, rule_description: e.target.value })}
                      className="w-full text-xs p-2.5 border border-zinc-300 rounded-lg"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-zinc-700 mb-1">Change Note (Required for Audit Trail)</label>
                    <input
                      type="text"
                      placeholder="e.g. Added 0.5% FX fee tolerance based on Q2 compliance update."
                      value={editFormData.change_note || ''}
                      onChange={(e) => setEditFormData({ ...editFormData, change_note: e.target.value })}
                      className="w-full text-xs p-2.5 border border-zinc-300 rounded-lg"
                    />
                  </div>

                  <div className="pt-2 flex items-center justify-end space-x-2">
                    <button
                      onClick={() => handleSaveRuleEdit()}
                      className="px-4 py-2 bg-emerald-600 text-white rounded-lg text-xs font-semibold hover:bg-emerald-700 transition shadow-sm"
                    >
                      Publish Version v{(selectedRule.version || 1) + 1}
                    </button>
                  </div>
                </div>
              ) : (
                <div className="p-3 bg-zinc-50 border border-zinc-200 rounded-lg text-xs text-zinc-500 flex items-center space-x-2">
                  <Lock className="w-4 h-4 text-zinc-400" />
                  <span>Only Administrators may edit or publish new versions of this rule specification.</span>
                </div>
              )}
            </div>

            {/* Drawer Footer */}
            <div className="p-4 border-t border-zinc-200 bg-zinc-50 flex items-center justify-between">
              <button
                onClick={() => {
                  handleOpenVersionModal(selectedRule);
                }}
                className="text-xs font-semibold text-zinc-700 hover:text-blue-600 flex items-center transition"
              >
                <GitBranch className="w-4 h-4 mr-1.5" />
                Version History & 1-Click Rollback
              </button>

              <button
                onClick={() => {
                  setPlaygroundRuleCode(selectedRule.rule_code);
                  setIsEditDrawerOpen(false);
                  setPlaygroundModalOpen(true);
                }}
                className="text-xs font-semibold text-emerald-700 hover:text-emerald-800 flex items-center transition"
              >
                <FlaskConical className="w-4 h-4 mr-1.5" />
                Test in Rule Playground
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ============================================================== */}
      {/* MODAL 1: VERSION HISTORY & 1-CLICK ROLLBACK                    */}
      {/* ============================================================== */}
      {versionModalOpen && versionRule && (
        <div className="fixed inset-0 z-50 bg-zinc-950/50 backdrop-blur-sm flex items-center justify-center p-4 animate-fade-in">
          <div className="bg-white rounded-2xl max-w-2xl w-full shadow-2xl border border-zinc-200 overflow-hidden">
            <div className="p-6 border-b border-zinc-200 flex items-center justify-between">
              <div>
                <h3 className="text-lg font-bold text-zinc-900 flex items-center">
                  <History className="w-5 h-5 mr-2 text-indigo-600" />
                  Version History & Rollback: {versionRule.rule_code}
                </h3>
                <p className="text-xs text-zinc-500 mt-1">
                  Existing audit trails retain the snapshot they ran against. Rollback restores snapshot configuration into a new immutable version.
                </p>
              </div>
              <button
                onClick={() => setVersionModalOpen(false)}
                className="p-1 rounded-lg text-zinc-400 hover:text-zinc-700"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 max-h-[60vh] overflow-y-auto space-y-4">
              {loadingVersions ? (
                <div className="text-center py-10 text-zinc-500 text-xs">
                  <RefreshCw className="w-5 h-5 animate-spin mx-auto text-indigo-600 mb-2" />
                  Fetching version snapshots...
                </div>
              ) : versionHistory.length === 0 ? (
                <div className="text-center py-8 text-zinc-500 text-xs">
                  No historical snapshots recorded yet. Version 1 is active.
                </div>
              ) : (
                <div className="relative pl-6 space-y-6 before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-zinc-200">
                  {versionHistory.map((v) => {
                    const isCurrent = v.version_number === versionRule.version;
                    const isSelected = selectedTargetVersion?.version_number === v.version_number;

                    return (
                      <div
                        key={v.version_number}
                        className={`relative p-4 rounded-xl border transition ${
                          isSelected
                            ? 'border-indigo-600 bg-indigo-50/40 ring-2 ring-indigo-500/20'
                            : isCurrent
                            ? 'border-emerald-300 bg-emerald-50/30'
                            : 'border-zinc-200 bg-white hover:border-zinc-300'
                        }`}
                      >
                        <div
                          className={`absolute -left-[27px] top-4 w-4 h-4 rounded-full border-2 ${
                            isCurrent
                              ? 'bg-emerald-600 border-white ring-2 ring-emerald-500'
                              : 'bg-white border-zinc-400'
                          }`}
                        />

                        <div className="flex items-center justify-between">
                          <div className="flex items-center space-x-2">
                            <span className="font-mono text-sm font-bold text-zinc-900">
                              v{v.version_number}
                            </span>
                            {isCurrent && (
                              <span className="px-2 py-0.5 text-[10px] font-bold rounded bg-emerald-100 text-emerald-800">
                                CURRENT LIVE
                              </span>
                            )}
                            <span className="text-xs text-zinc-500">
                              {v.date || v.created_at || 'Recorded snapshot'}
                            </span>
                          </div>

                          {!isCurrent && isAdmin && (
                            <button
                              onClick={() => setSelectedTargetVersion(v)}
                              className={`px-3 py-1 text-xs font-semibold rounded-lg transition ${
                                isSelected
                                  ? 'bg-indigo-600 text-white'
                                  : 'bg-zinc-100 text-zinc-700 hover:bg-zinc-200'
                              }`}
                            >
                              {isSelected ? 'Target Selected' : 'Select for Rollback'}
                            </button>
                          )}
                        </div>

                        <div className="mt-2 text-xs text-zinc-700">
                          <strong>Note: </strong>
                          {v.change_note || 'Rule update'}
                        </div>

                        <div className="mt-2 grid grid-cols-2 gap-2 text-[11px] font-mono bg-zinc-50 p-2 rounded border border-zinc-200">
                          <div>
                            <span className="text-emerald-700 font-bold">Allowed: </span>
                            {v.claims_allowed || '—'}
                          </div>
                          <div>
                            <span className="text-rose-700 font-bold">Disallowed: </span>
                            {v.claims_disallowed || '—'}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            <div className="p-4 border-t border-zinc-200 bg-zinc-50 flex items-center justify-between">
              <span className="text-xs text-zinc-500">
                {selectedTargetVersion
                  ? `Selected: v${selectedTargetVersion.version_number} (will become v${versionRule.version + 1})`
                  : 'Select a past version above to restore it.'}
              </span>

              <div className="flex space-x-2">
                <button
                  onClick={() => setVersionModalOpen(false)}
                  className="px-4 py-2 border border-zinc-300 text-zinc-700 text-xs font-semibold rounded-lg hover:bg-zinc-100 transition"
                >
                  Cancel
                </button>
                {isAdmin && (
                  <button
                    disabled={!selectedTargetVersion}
                    onClick={() => handlePerformRollback()}
                    className="px-4 py-2 bg-indigo-600 text-white text-xs font-semibold rounded-lg hover:bg-indigo-700 transition disabled:opacity-40 disabled:cursor-not-allowed flex items-center shadow-sm"
                  >
                    <RotateCcw className="w-3.5 h-3.5 mr-1.5" />
                    Confirm Rollback
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ============================================================== */}
      {/* MODAL 2: "IMPORT FROM URL" (SSRF-SAFE SCRAPER & PREVIEW)        */}
      {/* ============================================================== */}
      {scraperModalOpen && (
        <div className="fixed inset-0 z-50 bg-zinc-950/50 backdrop-blur-sm flex items-center justify-center p-4 animate-fade-in">
          <div className="bg-white rounded-2xl max-w-3xl w-full shadow-2xl border border-zinc-200 overflow-hidden">
            <div className="p-6 border-b border-zinc-200 flex items-center justify-between">
              <div>
                <h3 className="text-lg font-bold text-zinc-900 flex items-center">
                  <Globe className="w-5 h-5 mr-2 text-blue-600" />
                  Import from URL (SSRF-Protected Scraper)
                </h3>
                <p className="text-xs text-zinc-500 mt-1">
                  Extracts brand colors, typography, and marketing claims. All extracted items stay staged as{' '}
                  <strong className="text-indigo-700">DRAFT rules / unverified facts</strong> until admin approval.
                </p>
              </div>
              <button
                onClick={() => setScraperModalOpen(false)}
                className="p-1 rounded-lg text-zinc-400 hover:text-zinc-700"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 space-y-5 max-h-[65vh] overflow-y-auto">
              {/* SSRF Security Banner */}
              <div className="bg-blue-50 border border-blue-200 rounded-xl p-3.5 flex items-start space-x-2.5">
                <ShieldCheck className="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" />
                <div className="text-xs text-blue-900">
                  <span className="font-bold">SSRF Firewall Guardrail: </span>
                  Internal networks, loopbacks (<code className="font-mono bg-blue-100 px-1 py-0.5 rounded">127.0.0.1</code>), and cloud instance metadata (<code className="font-mono bg-blue-100 px-1 py-0.5 rounded">169.254.169.254</code>) are strictly blocked with pre-request DNS resolution checks.
                </div>
              </div>

              {/* URL Input Form */}
              <div className="flex gap-2">
                <input
                  type="url"
                  placeholder="https://brand.example.com"
                  value={scrapeUrl}
                  onChange={(e) => setScrapeUrl(e.target.value)}
                  className="flex-1 text-sm p-2.5 border border-zinc-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
                <button
                  disabled={scraping || !scrapeUrl.trim()}
                  onClick={() => handleRunScrapePreview()}
                  className="px-5 py-2.5 bg-blue-600 text-white rounded-lg text-xs font-semibold hover:bg-blue-700 transition disabled:opacity-40 flex items-center shadow-sm"
                >
                  {scraping ? (
                    <>
                      <RefreshCw className="w-4 h-4 mr-1.5 animate-spin" />
                      Inspecting...
                    </>
                  ) : (
                    <>
                      <Globe className="w-4 h-4 mr-1.5" />
                      Scrape Brand
                    </>
                  )}
                </button>
              </div>

              {/* Quick sample chips */}
              <div className="flex items-center space-x-2 text-xs text-zinc-500">
                <span>Quick demo:</span>
                <button
                  type="button"
                  onClick={() => setScrapeUrl('https://novapay.io')}
                  className="px-2 py-0.5 rounded bg-zinc-100 hover:bg-zinc-200 text-zinc-700"
                >
                  https://novapay.io
                </button>
                <button
                  type="button"
                  onClick={() => setScrapeUrl('https://stripe.com')}
                  className="px-2 py-0.5 rounded bg-zinc-100 hover:bg-zinc-200 text-zinc-700"
                >
                  https://stripe.com
                </button>
              </div>

              {/* Error Box */}
              {scraperError && (
                <div className="bg-rose-50 border border-rose-200 rounded-xl p-3.5 text-xs text-rose-800 flex items-start space-x-2">
                  <AlertTriangle className="w-4 h-4 text-rose-600 mt-0.5 flex-shrink-0" />
                  <span>{scraperError}</span>
                </div>
              )}

              {/* Scrape Preview Table */}
              {scrapePreview && (
                <div className="space-y-4 animate-fade-in border-t border-zinc-200 pt-4">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-bold text-zinc-900">
                      Extraction Results ({scrapePreview.preview_items?.length || 0} items)
                    </span>
                    <button
                      onClick={() => {
                        const allSelected = Object.keys(selectedPreviewItems).length === (scrapePreview.preview_items?.length || 0);
                        const newSelected = {};
                        if (!allSelected) {
                          (scrapePreview.preview_items || []).forEach((item) => {
                            newSelected[item.id] = true;
                          });
                        }
                        setSelectedPreviewItems(newSelected);
                      }}
                      className="text-xs text-blue-600 hover:text-blue-800 font-semibold"
                    >
                      Toggle All
                    </button>
                  </div>

                  <div className="border border-zinc-200 rounded-xl overflow-hidden max-h-60 overflow-y-auto divide-y divide-zinc-100">
                    {scrapePreview.preview_items?.map((item) => (
                      <label
                        key={item.id}
                        className="flex items-center justify-between p-3 hover:bg-zinc-50 cursor-pointer text-xs"
                      >
                        <div className="flex items-center space-x-3">
                          <input
                            type="checkbox"
                            checked={!!selectedPreviewItems[item.id]}
                            onChange={(e) => {
                              setSelectedPreviewItems({
                                ...selectedPreviewItems,
                                [item.id]: e.target.checked
                              });
                            }}
                            className="rounded text-blue-600 focus:ring-blue-500 w-4 h-4"
                          />
                          {item.type === 'HEX_PALETTE' && (
                            <span
                              className="w-4 h-4 rounded-full border border-zinc-300 inline-block"
                              style={{ backgroundColor: item.value }}
                            />
                          )}
                          <div>
                            <span className="font-semibold text-zinc-900">{item.label}</span>
                            <span className="text-zinc-500 ml-2 font-mono text-[11px]">{item.detail}</span>
                          </div>
                        </div>

                        <span className="px-2 py-0.5 text-[10px] font-bold rounded bg-amber-100 text-amber-800 uppercase">
                          {item.status || 'UNVERIFIED'}
                        </span>
                      </label>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <div className="p-4 border-t border-zinc-200 bg-zinc-50 flex items-center justify-between">
              <span className="text-xs text-zinc-500">
                {scrapePreview
                  ? `${Object.values(selectedPreviewItems).filter(Boolean).length} items selected for draft staging`
                  : 'Enter a valid public URL and click Scrape'}
              </span>

              <div className="flex space-x-2">
                <button
                  onClick={() => setScraperModalOpen(false)}
                  className="px-4 py-2 border border-zinc-300 text-zinc-700 text-xs font-semibold rounded-lg hover:bg-zinc-100 transition"
                >
                  Cancel
                </button>
                {scrapePreview && (
                  <button
                    disabled={importingScrape || Object.values(selectedPreviewItems).filter(Boolean).length === 0}
                    onClick={() => handleImportScrapedItems()}
                    className="px-4 py-2 bg-blue-600 text-white text-xs font-semibold rounded-lg hover:bg-blue-700 transition disabled:opacity-40 flex items-center shadow-sm"
                  >
                    {importingScrape ? (
                      <>
                        <RefreshCw className="w-3.5 h-3.5 mr-1.5 animate-spin" />
                        Staging...
                      </>
                    ) : (
                      <>
                        <Check className="w-3.5 h-3.5 mr-1.5" />
                        Import Selected as Drafts
                      </>
                    )}
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ============================================================== */}
      {/* MODAL 3: MULTI-FORMAT UPLOAD -> DRAFT RULES REVIEW             */}
      {/* ============================================================== */}
      {uploadModalOpen && (
        <div className="fixed inset-0 z-50 bg-zinc-950/50 backdrop-blur-sm flex items-center justify-center p-4 animate-fade-in">
          <div className="bg-white rounded-2xl max-w-2xl w-full shadow-2xl border border-zinc-200 overflow-hidden">
            <div className="p-6 border-b border-zinc-200 flex items-center justify-between">
              <div>
                <h3 className="text-lg font-bold text-zinc-900 flex items-center">
                  <UploadCloud className="w-5 h-5 mr-2 text-indigo-600" />
                  Multi-Format Rules Upload
                </h3>
                <p className="text-xs text-zinc-500 mt-1">
                  Upload guidelines in PDF, DOCX, XLSX, CSV, JSON, YAML, MD, TXT, or images. Parser outputs{' '}
                  <strong className="text-indigo-700">DRAFT rules only</strong>. Never auto-activates.
                </p>
              </div>
              <button
                onClick={() => {
                  setUploadModalOpen(false);
                  setUploadSuccessSummary(null);
                }}
                className="p-1 rounded-lg text-zinc-400 hover:text-zinc-700"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 space-y-5">
              {/* Tabs: File Upload vs Paste Text */}
              <div className="flex border-b border-zinc-200 space-x-4 text-xs font-semibold">
                <button
                  onClick={() => setUploadTab('file')}
                  className={`pb-2 border-b-2 transition ${
                    uploadTab === 'file'
                      ? 'border-indigo-600 text-indigo-700'
                      : 'border-transparent text-zinc-500 hover:text-zinc-700'
                  }`}
                >
                  Upload File (.pdf, .docx, .xlsx, .csv, .json, .yaml, .md)
                </button>
                <button
                  onClick={() => setUploadTab('paste')}
                  className={`pb-2 border-b-2 transition ${
                    uploadTab === 'paste'
                      ? 'border-indigo-600 text-indigo-700'
                      : 'border-transparent text-zinc-500 hover:text-zinc-700'
                  }`}
                >
                  Paste Text / Markdown Guidelines
                </button>
              </div>

              {uploadTab === 'file' ? (
                <div className="border-2 border-dashed border-zinc-300 rounded-xl p-8 text-center hover:border-indigo-400 transition bg-zinc-50/50">
                  <UploadCloud className="w-10 h-10 text-zinc-400 mx-auto mb-2" />
                  <span className="text-sm font-semibold text-zinc-700 block">
                    {uploadFile ? uploadFile.name : 'Select or drop policy file'}
                  </span>
                  <span className="text-xs text-zinc-500 mt-1 block">
                    Supported: PDF, DOCX, XLSX, CSV, JSON, YAML, MD, TXT (Max 10MB)
                  </span>
                  <input
                    type="file"
                    id="rule-file-upload"
                    className="hidden"
                    accept=".pdf,.docx,.xlsx,.csv,.json,.yaml,.yml,.md,.txt,.png,.jpg,.jpeg"
                    onChange={(e) => setUploadFile(e.target.files[0] || null)}
                  />
                  <label
                    htmlFor="rule-file-upload"
                    className="mt-4 inline-block px-4 py-2 bg-white border border-zinc-300 rounded-lg text-xs font-semibold text-zinc-700 hover:bg-zinc-50 cursor-pointer shadow-sm"
                  >
                    Browse Files
                  </label>
                </div>
              ) : (
                <div className="space-y-3">
                  <div className="flex items-center justify-between text-xs">
                    <label className="font-semibold text-zinc-700">Paste Rules Spec (Markdown / Plain Text):</label>
                    <input
                      type="text"
                      value={pastedFilename}
                      onChange={(e) => setPastedFilename(e.target.value)}
                      placeholder="filename.md"
                      className="text-xs p-1 border border-zinc-300 rounded font-mono"
                    />
                  </div>
                  <textarea
                    rows={8}
                    value={pastedContent}
                    onChange={(e) => setPastedContent(e.target.value)}
                    placeholder={`# NovaPay Tone Guidelines\nRule: Prohibit Hyperbolic Returns\nCode: TONE_014\nSeverity: BLOCKER\nBanned: guaranteed payouts\nReplacement: transparent processing\nDescription: Never promise guaranteed payouts without risk disclosures.`}
                    className="w-full text-xs font-mono p-3 border border-zinc-300 rounded-xl focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
              )}

              {/* Error Banner */}
              {uploadError && (
                <div className="bg-rose-50 border border-rose-200 rounded-xl p-3 text-xs text-rose-800 flex items-start space-x-2">
                  <AlertTriangle className="w-4 h-4 text-rose-600 mt-0.5 flex-shrink-0" />
                  <span>{uploadError}</span>
                </div>
              )}

              {/* Success Staging Banner */}
              {uploadSuccessSummary && (
                <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4 space-y-2">
                  <div className="flex items-center space-x-2 text-emerald-800 font-bold text-sm">
                    <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                    <span>Successfully Staged {uploadSuccessSummary.count} DRAFT Rules!</span>
                  </div>
                  <p className="text-xs text-emerald-900">
                    Draft rules are now queued for review. You can review and approve them into active enforcement.
                  </p>
                  <button
                    onClick={() => {
                      setUploadModalOpen(false);
                      setActiveTab('draft_rules');
                    }}
                    className="mt-2 px-3.5 py-1.5 text-xs font-semibold rounded bg-emerald-700 text-white hover:bg-emerald-800 transition"
                  >
                    Open Draft Review Queue →
                  </button>
                </div>
              )}
            </div>

            <div className="p-4 border-t border-zinc-200 bg-zinc-50 flex items-center justify-end space-x-2">
              <button
                onClick={() => {
                  setUploadModalOpen(false);
                  setUploadSuccessSummary(null);
                }}
                className="px-4 py-2 border border-zinc-300 text-zinc-700 text-xs font-semibold rounded-lg hover:bg-zinc-100 transition"
              >
                Close
              </button>
              {!uploadSuccessSummary && (
                <button
                  disabled={uploading}
                  onClick={(e) => handleUploadRules(e)}
                  className="px-5 py-2 bg-indigo-600 text-white text-xs font-semibold rounded-lg hover:bg-indigo-700 transition disabled:opacity-40 flex items-center shadow-sm"
                >
                  {uploading ? (
                    <>
                      <RefreshCw className="w-3.5 h-3.5 mr-1.5 animate-spin" />
                      Parsing Spec...
                    </>
                  ) : (
                    <>
                      <UploadCloud className="w-3.5 h-3.5 mr-1.5" />
                      Parse & Stage as Drafts
                    </>
                  )}
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ============================================================== */}
      {/* MODAL 4: RULE PLAYGROUND (TEST SAMPLE TEXT AGAINST RULES)       */}
      {/* ============================================================== */}
      {playgroundModalOpen && (
        <div className="fixed inset-0 z-50 bg-zinc-950/50 backdrop-blur-sm flex items-center justify-center p-4 animate-fade-in">
          <div className="bg-white rounded-2xl max-w-2xl w-full shadow-2xl border border-zinc-200 overflow-hidden">
            <div className="p-6 border-b border-zinc-200 flex items-center justify-between">
              <div>
                <h3 className="text-lg font-bold text-zinc-900 flex items-center">
                  <FlaskConical className="w-5 h-5 mr-2 text-emerald-600" />
                  Rule Playground & Linter Simulator
                </h3>
                <p className="text-xs text-zinc-500 mt-1">
                  Test sample copy against an active or staged rule before publishing or approving.
                </p>
              </div>
              <button
                onClick={() => setPlaygroundModalOpen(false)}
                className="p-1 rounded-lg text-zinc-400 hover:text-zinc-700"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 space-y-4">
              {/* Select Target Rule */}
              <div>
                <label className="block text-xs font-semibold text-zinc-700 mb-1">Select Target Rule</label>
                <select
                  value={playgroundRuleCode}
                  onChange={(e) => {
                    setPlaygroundRuleCode(e.target.value);
                    setPlaygroundDraftId('');
                  }}
                  className="w-full text-xs p-2.5 border border-zinc-300 rounded-lg bg-white"
                >
                  {rules.map((r) => (
                    <option key={r.rule_code} value={r.rule_code}>
                      [{r.rule_code}] {r.title} ({r.pillar} · {r.severity})
                    </option>
                  ))}
                </select>
              </div>

              {/* Sample Copy Textarea */}
              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="text-xs font-semibold text-zinc-700">Sample Marketing Copy to Test:</label>
                  <div className="flex space-x-1.5 text-[11px]">
                    <button
                      type="button"
                      onClick={() => setPlaygroundText('NovaPay offers 24-hour transfers with 0.5% FX fee across top corridors.')}
                      className="text-emerald-700 hover:underline"
                    >
                      Compliant Example
                    </button>
                    <span>·</span>
                    <button
                      type="button"
                      onClick={() => setPlaygroundText('Instant, zero-fee international transfers worldwide with NovaPay.')}
                      className="text-rose-700 hover:underline"
                    >
                      Violating Example
                    </button>
                  </div>
                </div>
                <textarea
                  rows={4}
                  value={playgroundText}
                  onChange={(e) => setPlaygroundText(e.target.value)}
                  className="w-full text-xs p-3 border border-zinc-300 rounded-xl focus:ring-2 focus:ring-emerald-500"
                />
              </div>

              {/* Test Action */}
              <div className="flex justify-end">
                <button
                  disabled={playgroundTesting || !playgroundText.trim()}
                  onClick={() => handleRunPlayground()}
                  className="px-5 py-2.5 bg-emerald-600 text-white rounded-lg text-xs font-semibold hover:bg-emerald-700 transition disabled:opacity-40 flex items-center shadow-sm"
                >
                  {playgroundTesting ? (
                    <>
                      <RefreshCw className="w-3.5 h-3.5 mr-1.5 animate-spin" />
                      Evaluating...
                    </>
                  ) : (
                    <>
                      <FlaskConical className="w-3.5 h-3.5 mr-1.5" />
                      Run Pre-Flight Test
                    </>
                  )}
                </button>
              </div>

              {/* Playground Result Card */}
              {playgroundResult && (
                <div
                  className={`p-4 rounded-xl border animate-fade-in ${
                    playgroundResult.status === 'PASS'
                      ? 'bg-emerald-50/70 border-emerald-300'
                      : 'bg-rose-50/70 border-rose-300'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      {playgroundResult.status === 'PASS' ? (
                        <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                      ) : (
                        <ShieldAlert className="w-5 h-5 text-rose-600" />
                      )}
                      <span className="font-bold text-sm text-zinc-900">
                        {playgroundResult.status === 'PASS' ? 'Passed Specification' : 'Rule Violation Flagged'}
                      </span>
                    </div>
                    <span
                      className={`px-2.5 py-0.5 rounded text-xs font-bold ${
                        playgroundResult.status === 'PASS'
                          ? 'bg-emerald-200 text-emerald-900'
                          : 'bg-rose-200 text-rose-900'
                      }`}
                    >
                      {playgroundResult.status}
                    </span>
                  </div>

                  <p className="text-xs text-zinc-800 mt-2 leading-relaxed">
                    {playgroundResult.explanation}
                  </p>

                  {playgroundResult.match_excerpt && (
                    <div className="mt-2 text-xs font-mono bg-white/80 p-2 rounded border border-rose-200 text-rose-900">
                      <strong>Flagged trigger: </strong>"{playgroundResult.match_excerpt}"
                    </div>
                  )}

                  {playgroundResult.suggested_fix && (
                    <div className="mt-2 pt-2 border-t border-rose-200/60 flex items-center justify-between text-xs">
                      <span className="text-emerald-800 font-semibold">
                        Suggested Replacement: “{playgroundResult.suggested_fix}”
                      </span>
                      <button
                        onClick={() => {
                          if (playgroundResult.match_excerpt) {
                            setPlaygroundText(
                              playgroundText.replace(playgroundResult.match_excerpt, playgroundResult.suggested_fix)
                            );
                          }
                        }}
                        className="text-xs text-emerald-700 hover:text-emerald-900 font-bold underline"
                      >
                        Apply Fix
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>

            <div className="p-4 border-t border-zinc-200 bg-zinc-50 flex items-center justify-end">
              <button
                onClick={() => setPlaygroundModalOpen(false)}
                className="px-4 py-2 border border-zinc-300 text-zinc-700 text-xs font-semibold rounded-lg hover:bg-zinc-100 transition"
              >
                Close Playground
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ============================================================== */}
      {/* MODAL 5: CREATE NEW RULE (ADMIN ONLY)                          */}
      {/* ============================================================== */}
      {createModalOpen && isAdmin && (
        <div className="fixed inset-0 z-50 bg-zinc-950/50 backdrop-blur-sm flex items-center justify-center p-4 animate-fade-in">
          <div className="bg-white rounded-2xl max-w-xl w-full shadow-2xl border border-zinc-200 overflow-hidden">
            <div className="p-6 border-b border-zinc-200 flex items-center justify-between">
              <div>
                <h3 className="text-lg font-bold text-zinc-900 flex items-center">
                  <Plus className="w-5 h-5 mr-2 text-emerald-600" />
                  Create Brand Governance Rule
                </h3>
                <p className="text-xs text-zinc-500 mt-1">
                  Adds a new rule with version 1 snapshot and creates an immutable audit trail entry.
                </p>
              </div>
              <button
                onClick={() => setCreateModalOpen(false)}
                className="p-1 rounded-lg text-zinc-400 hover:text-zinc-700"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreateNewRule} className="p-6 space-y-4 max-h-[65vh] overflow-y-auto">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-zinc-700 mb-1">Rule Code (Unique)</label>
                  <input
                    type="text"
                    required
                    placeholder="TONE_015"
                    value={createFormData.rule_code}
                    onChange={(e) => setCreateFormData({ ...createFormData, rule_code: e.target.value.toUpperCase() })}
                    className="w-full text-xs p-2.5 border border-zinc-300 rounded-lg font-mono focus:ring-2 focus:ring-emerald-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-zinc-700 mb-1">Pillar</label>
                  <select
                    value={createFormData.pillar}
                    onChange={(e) => setCreateFormData({ ...createFormData, pillar: e.target.value })}
                    className="w-full text-xs p-2.5 border border-zinc-300 rounded-lg bg-white"
                  >
                    <option value="TONE">TONE (Lexicon & Tone)</option>
                    <option value="FACTUAL">FACTUAL (Truth & Claims)</option>
                    <option value="VISUAL">VISUAL (Palettes & Fonts)</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-zinc-700 mb-1">Rule Title</label>
                <input
                  type="text"
                  required
                  placeholder="Prohibit Hyperbolic Growth Guarantees"
                  value={createFormData.title}
                  onChange={(e) => setCreateFormData({ ...createFormData, title: e.target.value })}
                  className="w-full text-xs p-2.5 border border-zinc-300 rounded-lg focus:ring-2 focus:ring-emerald-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-zinc-700 mb-1">Severity</label>
                  <select
                    value={createFormData.severity}
                    onChange={(e) => setCreateFormData({ ...createFormData, severity: e.target.value })}
                    className="w-full text-xs p-2.5 border border-zinc-300 rounded-lg bg-white"
                  >
                    <option value="BLOCKER">BLOCKER (Strict Stop)</option>
                    <option value="WARNING">WARNING (Advisory)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-zinc-700 mb-1">Enforcement</label>
                  <input
                    type="text"
                    value={createFormData.enforcement}
                    onChange={(e) => setCreateFormData({ ...createFormData, enforcement: e.target.value })}
                    className="w-full text-xs p-2.5 border border-zinc-300 rounded-lg"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-zinc-700 mb-1">Disallowed / Banned Term</label>
                  <input
                    type="text"
                    placeholder="guaranteed returns"
                    value={createFormData.banned_term}
                    onChange={(e) => setCreateFormData({ ...createFormData, banned_term: e.target.value, claims_disallowed: e.target.value })}
                    className="w-full text-xs p-2.5 border border-zinc-300 rounded-lg"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-zinc-700 mb-1">Mandated / Replacement Term</label>
                  <input
                    type="text"
                    placeholder="market-driven yield"
                    value={createFormData.replacement}
                    onChange={(e) => setCreateFormData({ ...createFormData, replacement: e.target.value, claims_allowed: e.target.value })}
                    className="w-full text-xs p-2.5 border border-zinc-300 rounded-lg"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-zinc-700 mb-1">Description / Rationale</label>
                <textarea
                  rows={2}
                  placeholder="Explains the regulatory reason or brand identity guideline..."
                  value={createFormData.rule_description}
                  onChange={(e) => setCreateFormData({ ...createFormData, rule_description: e.target.value })}
                  className="w-full text-xs p-2.5 border border-zinc-300 rounded-lg"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-zinc-700 mb-1">Source of Truth Reference</label>
                <input
                  type="text"
                  value={createFormData.source}
                  onChange={(e) => setCreateFormData({ ...createFormData, source: e.target.value })}
                  className="w-full text-xs p-2.5 border border-zinc-300 rounded-lg"
                />
              </div>

              <div className="p-4 border-t border-zinc-200 bg-zinc-50 -mx-6 -mb-6 flex items-center justify-end space-x-2">
                <button
                  type="button"
                  onClick={() => setCreateModalOpen(false)}
                  className="px-4 py-2 border border-zinc-300 text-zinc-700 text-xs font-semibold rounded-lg hover:bg-zinc-100 transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 bg-emerald-600 text-white text-xs font-semibold rounded-lg hover:bg-emerald-700 transition shadow-sm"
                >
                  Create Rule v1
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
