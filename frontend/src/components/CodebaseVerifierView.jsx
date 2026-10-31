import React, { useState, useEffect } from 'react';
import {
  GitBranch,
  FolderGit2,
  RefreshCw,
  Plus,
  Trash2,
  CheckCircle2,
  AlertOctagon,
  AlertTriangle,
  Clock,
  ExternalLink,
  Shield,
  Layers,
  Sparkles,
  Database,
  Sliders,
  Check,
  X,
  Lock,
  ChevronRight,
  FileCode,
  Info,
  Calendar,
  Users,
  CheckSquare,
  Square,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { API_BASE } from '../config/api';
import Badge from './ui/Badge';
import Dialog from './ui/Dialog';
import Toast from './ui/Toast';

export default function CodebaseVerifierView({ apiBase = API_BASE }) {
  const { user, token, isAdmin } = useAuth();

  // Active sub-tab: 'repos' | 'proposals' | 'mappings' | 'constants'
  const [subTab, setSubTab] = useState('repos');

  // Data states
  const [repos, setRepos] = useState([]);
  const [mappings, setMappings] = useState([]);
  const [constants, setConstants] = useState([]);
  const [proposedChanges, setProposedChanges] = useState([]);
  const [facts, setFacts] = useState([]);
  const [loading, setLoading] = useState(true);

  // Active scan job state
  const [activeJob, setActiveJob] = useState(null);
  const [scanningRepoId, setScanningRepoId] = useState(null);

  // Modals
  const [connectModalOpen, setConnectModalOpen] = useState(false);
  const [repoFormData, setRepoFormData] = useState({
    repo_name: 'novapay/core-banking',
    repo_url: 'https://github.com/novapay/core-banking',
    branch: 'main',
    auth_token: '',
    webhook_secret: '',
  });

  const [mappingModalOpen, setMappingModalOpen] = useState(false);
  const [mappingFormData, setMappingFormData] = useState({
    symbol_name: '',
    pattern: '',
    semantic_key: '',
    target_fact_id: '',
    unit_type: 'PERCENTAGE',
    scale_factor: 100.0,
    display_format: '{value}%',
    confidence_weight: 1.0,
  });

  const [approveModalChange, setApproveModalChange] = useState(null);
  const [validUntilDate, setValidUntilDate] = useState('2027-12-31');
  const [rejectModalChange, setRejectModalChange] = useState(null);
  const [rejectionReason, setRejectionReason] = useState('');

  // Module 3: Blast Radius State
  const [blastRadiusModalOpen, setBlastRadiusModalOpen] = useState(false);
  const [blastRadiusData, setBlastRadiusData] = useState(null);
  const [selectedPatches, setSelectedPatches] = useState(new Set());
  const [isApplyingPatches, setIsApplyingPatches] = useState(false);
  const [confirmApplyModalOpen, setConfirmApplyModalOpen] = useState(false);

  // Toast
  const [toastMessage, setToastMessage] = useState('');
  const [toastType, setToastType] = useState('success');

  const showToast = (msg, type = 'success') => {
    setToastMessage(msg);
    setToastType(type);
    setTimeout(() => setToastMessage(''), 3500);
  };

  const getAuthHeaders = (isJson = true) => {
    const headers = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;
    if (isJson) headers['Content-Type'] = 'application/json';
    return headers;
  };

  // Fetch all module data
  const fetchData = async () => {
    setLoading(true);
    try {
      // 1. Fetch Repos
      const reposRes = await fetch(`${apiBase}/api/codebase/repos/`, { headers: getAuthHeaders(false) });
      if (reposRes.ok) {
        const d = await reposRes.json();
        setRepos(d.repos || []);
        if (d.repos?.[0]?.id) {
          fetchConstants(d.repos[0].id);
        }
      }

      // 2. Fetch Mappings
      const mappingsRes = await fetch(`${apiBase}/api/codebase/mappings/`, { headers: getAuthHeaders(false) });
      if (mappingsRes.ok) {
        const d = await mappingsRes.json();
        setMappings(d.mappings || []);
      }

      // 3. Fetch Proposed Changes
      const changesRes = await fetch(`${apiBase}/api/codebase/proposed-changes/`, { headers: getAuthHeaders(false) });
      if (changesRes.ok) {
        const d = await changesRes.json();
        setProposedChanges(d.proposed_changes || []);
      }

      // 4. Fetch Facts (for mapping selector)
      const factsRes = await fetch(`${apiBase}/api/facts/`, { headers: getAuthHeaders(false) });
      if (factsRes.ok) {
        const d = await factsRes.json();
        setFacts(d.facts || []);
      }
    } catch (err) {
      console.error('Failed to load codebase verifier data:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchConstants = async (repoId) => {
    try {
      const res = await fetch(`${apiBase}/api/codebase/repos/${repoId}/constants/`, { headers: getAuthHeaders(false) });
      if (res.ok) {
        const d = await res.json();
        setConstants(d.constants || []);
      }
    } catch (err) {
      console.error('Failed to load constants:', err);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  // Connect Repo Handler
  const handleConnectRepo = async (e) => {
    e.preventDefault();
    try {
      const res = await fetch(`${apiBase}/api/codebase/repos/`, {
        method: 'POST',
        headers: getAuthHeaders(true),
        body: JSON.stringify(repoFormData),
      });

      if (res.ok) {
        const createdRepo = await res.json();
        setRepos([createdRepo, ...repos]);
        setConnectModalOpen(false);
        setRepoFormData({
          repo_name: '',
          repo_url: '',
          branch: 'main',
          auth_token: '',
          webhook_secret: '',
        });
        showToast(`Repository '${createdRepo.repo_name}' connected with encrypted token.`);
      } else {
        const err = await res.json();
        showToast(err.error || 'Failed to connect repository.', 'error');
      }
    } catch (err) {
      showToast('Network error while connecting repository.', 'error');
    }
  };

  // Trigger Scan Handler
  const handleTriggerScan = async (repoId) => {
    setScanningRepoId(repoId);
    try {
      const res = await fetch(`${apiBase}/api/codebase/repos/${repoId}/scan/`, {
        method: 'POST',
        headers: getAuthHeaders(true),
        body: JSON.stringify({ synchronous: false }),
      });

      if (res.ok) {
        const d = await res.json();
        showToast('Codebase AST scan queued in background.');
        if (d.job_id) {
          pollJobProgress(d.job_id, repoId);
        }
      } else {
        showToast('Failed to queue scan.', 'error');
        setScanningRepoId(null);
      }
    } catch (err) {
      showToast('Network error triggering scan.', 'error');
      setScanningRepoId(null);
    }
  };

  // Poll Job Progress
  const pollJobProgress = (jobId, repoId) => {
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`${apiBase}/api/jobs/${jobId}/`, { headers: getAuthHeaders(false) });
        if (res.ok) {
          const jobData = await res.json();
          setActiveJob(jobData);
          if (jobData.status === 'SUCCESS' || jobData.status === 'FAILED') {
            clearInterval(interval);
            setScanningRepoId(null);
            setActiveJob(null);
            fetchData();
            if (jobData.status === 'SUCCESS') {
              showToast('Codebase scan completed successfully! New constants extracted.');
            } else {
              showToast(`Scan failed: ${jobData.error || 'Unknown error'}`, 'error');
            }
          }
        }
      } catch (err) {
        clearInterval(interval);
        setScanningRepoId(null);
      }
    }, 1500);
  };

  // Create Mapping Handler
  const handleCreateMapping = async (e) => {
    e.preventDefault();
    try {
      const res = await fetch(`${apiBase}/api/codebase/mappings/`, {
        method: 'POST',
        headers: getAuthHeaders(true),
        body: JSON.stringify(mappingFormData),
      });

      if (res.ok) {
        const created = await res.json();
        setMappings([created, ...mappings]);
        setMappingModalOpen(false);
        setMappingFormData({
          symbol_name: '',
          pattern: '',
          semantic_key: '',
          target_fact_id: '',
          unit_type: 'PERCENTAGE',
          scale_factor: 100.0,
          display_format: '{value}%',
          confidence_weight: 1.0,
        });
        showToast(`Created symbol mapping '${created.symbol_name}'.`);
      } else {
        const err = await res.json();
        showToast(err.error || 'Failed to create symbol mapping.', 'error');
      }
    } catch (err) {
      showToast('Network error creating mapping.', 'error');
    }
  };

  // Approve Proposed Change
  const handleApproveProposal = async () => {
    if (!approveModalChange) return;
    try {
      const res = await fetch(`${apiBase}/api/codebase/proposed-changes/${approveModalChange.id}/review/`, {
        method: 'POST',
        headers: getAuthHeaders(true),
        body: JSON.stringify({
          action: 'APPROVE',
          valid_until: validUntilDate,
        }),
      });

      if (res.ok) {
        const d = await res.json();
        showToast(d.message || 'Fact updated successfully!');
        setApproveModalChange(null);
        fetchData();

        // If blast radius detected affected assets, open Blast Radius report modal
        if (d.blast_radius && d.blast_radius.affected_assets_count > 0) {
          setBlastRadiusData(d.blast_radius);
          const allIds = new Set((d.blast_radius.draft_patches || []).map((p) => p.submission_id));
          setSelectedPatches(allIds);
          setBlastRadiusModalOpen(true);
        }
      } else {
        const err = await res.json();
        showToast(err.error || 'Failed to approve change.', 'error');
      }
    } catch (err) {
      showToast('Network error approving change.', 'error');
    }
  };

  // View Blast Radius for any Fact
  const handleViewBlastRadius = async (factId) => {
    try {
      showToast('Computing blast radius & dependency impact...', 'info');
      const res = await fetch(`${apiBase}/api/facts/${factId}/blast-radius/`, {
        headers: getAuthHeaders(false),
      });
      if (res.ok) {
        const d = await res.json();
        const report = d.report || d.blast_radius || d;
        setBlastRadiusData(report);
        const allIds = new Set((report.draft_patches || []).map((p) => p.submission_id));
        setSelectedPatches(allIds);
        setBlastRadiusModalOpen(true);
      } else {
        showToast('Failed to load blast radius.', 'error');
      }
    } catch (err) {
      showToast('Network error loading blast radius.', 'error');
    }
  };

  // Toggle selection for batch patching
  const handleToggleSelectPatch = (submissionId) => {
    setSelectedPatches((prev) => {
      const next = new Set(prev);
      if (next.has(submissionId)) {
        next.delete(submissionId);
      } else {
        next.add(submissionId);
      }
      return next;
    });
  };

  const handleToggleSelectAllPatches = () => {
    if (!blastRadiusData || !blastRadiusData.draft_patches) return;
    if (selectedPatches.size === blastRadiusData.draft_patches.length) {
      setSelectedPatches(new Set());
    } else {
      setSelectedPatches(new Set(blastRadiusData.draft_patches.map((p) => p.submission_id)));
    }
  };

  // Execute batch patch application
  const handleExecuteBatchPatch = async () => {
    if (!blastRadiusData) return;
    setIsApplyingPatches(true);
    try {
      const targetFact = facts.find((f) => f.fact_code === blastRadiusData.fact_code);
      const targetFactId = targetFact ? targetFact.id : (blastRadiusData.fact_id || blastRadiusData.id);
      const res = await fetch(`${apiBase}/api/facts/${targetFactId}/apply-patches/`, {
        method: 'POST',
        headers: getAuthHeaders(true),
        body: JSON.stringify({
          submission_ids: Array.from(selectedPatches),
        }),
      });
      if (res.ok) {
        const d = await res.json();
        showToast(`Successfully applied patches to ${d.patched_count} stale assets! Re-audits completed.`, 'success');
        setConfirmApplyModalOpen(false);
        setBlastRadiusModalOpen(false);
        fetchData();
      } else {
        const err = await res.json();
        showToast(err.error || 'Failed to apply batch patches.', 'error');
      }
    } catch (err) {
      showToast('Network error applying batch patches.', 'error');
    } finally {
      setIsApplyingPatches(false);
    }
  };

  // Reject Proposed Change
  const handleRejectProposal = async () => {
    if (!rejectModalChange) return;
    try {
      const res = await fetch(`${apiBase}/api/codebase/proposed-changes/${rejectModalChange.id}/review/`, {
        method: 'POST',
        headers: getAuthHeaders(true),
        body: JSON.stringify({
          action: 'REJECT',
          rejection_reason: rejectionReason,
        }),
      });

      if (res.ok) {
        showToast('Proposed change rejected.');
        setRejectModalChange(null);
        setRejectionReason('');
        fetchData();
      } else {
        const err = await res.json();
        showToast(err.error || 'Failed to reject change.', 'error');
      }
    } catch (err) {
      showToast('Network error rejecting change.', 'error');
    }
  };

  const pendingChanges = proposedChanges.filter((c) => c.status === 'PENDING');

  return (
    <div className="w-full space-y-6 animate-fade-in">
      {/* Toast */}
      {toastMessage && (
        <div
          role="status"
          className={`fixed bottom-6 right-6 z-50 px-4 py-3 rounded-[var(--radius-card)] shadow-xl flex items-center space-x-2 text-xs font-medium border ${
            toastType === 'error'
              ? 'bg-[var(--surface)] text-[var(--blocker)] border-[var(--blocker)]/40'
              : 'bg-[var(--surface)] text-[var(--cleared)] border-[var(--cleared)]/40'
          }`}
        >
          {toastType === 'error' ? (
            <AlertOctagon className="w-4 h-4 text-[var(--blocker)] shrink-0" />
          ) : (
            <CheckCircle2 className="w-4 h-4 text-[var(--cleared)] shrink-0" />
          )}
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Top Header & Breadcrumbs */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-[var(--border)] gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold font-serif text-[var(--text)]">
              Codebase-to-Claim Ground-Truth Verifier
            </h1>
            <span className="font-mono text-[10px] px-2 py-0.5 rounded bg-[var(--surface-alt)] text-[var(--primary)] font-bold border border-[var(--border)]">
              Module 2
            </span>
          </div>
          <p className="text-xs text-[var(--text-muted)] mt-1">
            Connects product repositories to extract hard constants via AST. Replaces assumption with ground truth.
          </p>
        </div>

        <div className="flex items-center gap-2.5 shrink-0">
          <button
            type="button"
            onClick={() => setConnectModalOpen(true)}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 bg-[var(--primary)] hover:bg-[var(--primary)]/90 text-white rounded-[var(--radius-input)] text-xs font-semibold shadow-2xs transition cursor-pointer"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Connect Repository</span>
          </button>
        </div>
      </div>

      {/* KPI Overview Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-[var(--surface)] p-4 rounded-[var(--radius-card)] border border-[var(--border)] shadow-2xs">
          <span className="text-[11px] font-mono text-[var(--text-muted)] uppercase block">Connected Repos</span>
          <span className="text-2xl font-bold font-serif text-[var(--text)] mt-1 block">{repos.length}</span>
          <span className="text-[10px] text-[var(--text-muted)] mt-1 block">GitHub Shallow Clone Sandboxes</span>
        </div>

        <div className="bg-[var(--surface)] p-4 rounded-[var(--radius-card)] border border-[var(--border)] shadow-2xs">
          <span className="text-[11px] font-mono text-[var(--text-muted)] uppercase block">Symbol Mappings</span>
          <span className="text-2xl font-bold font-serif text-[var(--text)] mt-1 block">{mappings.length}</span>
          <span className="text-[10px] text-[var(--text-muted)] mt-1 block">Admin-Editable Semantic Keys</span>
        </div>

        <div className="bg-[var(--surface)] p-4 rounded-[var(--radius-card)] border border-[var(--border)] shadow-2xs">
          <span className="text-[11px] font-mono text-[var(--text-muted)] uppercase block">Extracted Constants</span>
          <span className="text-2xl font-bold font-serif text-[var(--text)] mt-1 block">{constants.length}</span>
          <span className="text-[10px] text-[var(--text-muted)] mt-1 block">AST &amp; Config Literals</span>
        </div>

        <div className={`p-4 rounded-[var(--radius-card)] border shadow-2xs ${
          pendingChanges.length > 0
            ? 'bg-[var(--warning-text)]/10 border-[var(--warning-text)]/30'
            : 'bg-[var(--surface)] border-[var(--border)]'
        }`}>
          <span className="text-[11px] font-mono text-[var(--text-muted)] uppercase block">Pending Truth Changes</span>
          <div className="flex items-center gap-2 mt-1">
            <span className="text-2xl font-bold font-serif text-[var(--text)]">{pendingChanges.length}</span>
            {pendingChanges.length > 0 && (
              <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-[var(--warning-text)] text-white">
                Requires Review
              </span>
            )}
          </div>
          <span className="text-[10px] text-[var(--text-muted)] mt-1 block">Admin Approval Required</span>
        </div>
      </div>

      {/* Active Job Progress Banner */}
      {activeJob && (
        <div className="p-4 rounded-[var(--radius-card)] bg-[var(--surface)] border border-[var(--primary)]/40 shadow-xs space-y-2 animate-fade-in">
          <div className="flex items-center justify-between text-xs font-mono">
            <span className="flex items-center gap-2 text-[var(--text)] font-semibold">
              <RefreshCw className="w-3.5 h-3.5 animate-spin text-[var(--primary)]" />
              <span>AST Scan in Progress: {activeJob.status_message}</span>
            </span>
            <span className="font-bold text-[var(--primary)]">{activeJob.progress}%</span>
          </div>
          <div className="w-full h-2 bg-[var(--surface-alt)] rounded-full overflow-hidden">
            <div
              className="h-full bg-[var(--primary)] transition-all duration-300"
              style={{ width: `${activeJob.progress}%` }}
            />
          </div>
        </div>
      )}

      {/* Sub-Tabs Navigation */}
      <div className="flex items-center space-x-2 border-b border-[var(--border)]">
        <button
          type="button"
          onClick={() => setSubTab('repos')}
          className={`pb-3 px-3.5 text-xs font-semibold transition border-b-2 flex items-center space-x-2 cursor-pointer ${
            subTab === 'repos'
              ? 'border-[var(--primary)] text-[var(--primary)]'
              : 'border-transparent text-[var(--text-muted)] hover:text-[var(--text)]'
          }`}
        >
          <FolderGit2 className="w-4 h-4" />
          <span>Repositories ({repos.length})</span>
        </button>

        <button
          type="button"
          onClick={() => setSubTab('proposals')}
          className={`pb-3 px-3.5 text-xs font-semibold transition border-b-2 flex items-center space-x-2 cursor-pointer ${
            subTab === 'proposals'
              ? 'border-[var(--primary)] text-[var(--primary)]'
              : 'border-transparent text-[var(--text-muted)] hover:text-[var(--text)]'
          }`}
        >
          <Sparkles className="w-4 h-4" />
          <span>Proposed Truth Changes ({pendingChanges.length})</span>
        </button>

        <button
          type="button"
          onClick={() => setSubTab('mappings')}
          className={`pb-3 px-3.5 text-xs font-semibold transition border-b-2 flex items-center space-x-2 cursor-pointer ${
            subTab === 'mappings'
              ? 'border-[var(--primary)] text-[var(--primary)]'
              : 'border-transparent text-[var(--text-muted)] hover:text-[var(--text)]'
          }`}
        >
          <Sliders className="w-4 h-4" />
          <span>Symbol Mapping Table ({mappings.length})</span>
        </button>

        <button
          type="button"
          onClick={() => setSubTab('constants')}
          className={`pb-3 px-3.5 text-xs font-semibold transition border-b-2 flex items-center space-x-2 cursor-pointer ${
            subTab === 'constants'
              ? 'border-[var(--primary)] text-[var(--primary)]'
              : 'border-transparent text-[var(--text-muted)] hover:text-[var(--text)]'
          }`}
        >
          <FileCode className="w-4 h-4" />
          <span>Extracted Constants ({constants.length})</span>
        </button>
      </div>

      {/* ============================================================== */}
      {/* SUB-TAB 1: REPOSITORIES                                        */}
      {/* ============================================================== */}
      {subTab === 'repos' && (
        <div className="space-y-4">
          {repos.length === 0 ? (
            <div className="bg-[var(--surface)] p-8 rounded-[var(--radius-card)] border border-[var(--border)] text-center">
              <FolderGit2 className="w-10 h-10 text-[var(--text-muted)] mx-auto mb-2 opacity-50" />
              <h3 className="text-sm font-bold text-[var(--text)]">No Repositories Connected</h3>
              <p className="text-xs text-[var(--text-muted)] mt-1 max-w-sm mx-auto">
                Connect your product GitHub repository to automatically ground compliance claims against code constants.
              </p>
              <button
                type="button"
                onClick={() => setConnectModalOpen(true)}
                className="mt-4 px-4 py-2 bg-[var(--primary)] text-white text-xs font-semibold rounded-[var(--radius-input)] shadow-2xs hover:bg-[var(--primary)]/90 transition cursor-pointer"
              >
                Connect First Repo
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-4">
              {repos.map((r) => (
                <div
                  key={r.id}
                  className="bg-[var(--surface)] p-5 rounded-[var(--radius-card)] border border-[var(--border)] shadow-2xs flex flex-col md:flex-row md:items-center justify-between gap-4"
                >
                  <div className="space-y-1.5 min-w-0">
                    <div className="flex items-center gap-2.5 flex-wrap">
                      <span className="font-bold text-sm text-[var(--text)] font-serif">{r.repo_name}</span>
                      <span className="font-mono text-xs px-2 py-0.5 rounded bg-[var(--surface-alt)] text-[var(--text)] border border-[var(--border)] flex items-center gap-1">
                        <GitBranch className="w-3 h-3 text-[var(--primary)]" />
                        <span>{r.branch}</span>
                      </span>
                      {r.last_commit_sha && (
                        <span className="font-mono text-xs px-2 py-0.5 rounded bg-[var(--surface-alt)] text-[var(--text-muted)] border border-[var(--border)]">
                          SHA: {r.last_commit_sha.slice(0, 7)}
                        </span>
                      )}
                      <Badge variant={r.scan_status === 'SUCCESS' ? 'cleared' : r.scan_status === 'FAILED' ? 'blocker' : 'info'}>
                        {r.scan_status}
                      </Badge>
                    </div>

                    <div className="text-xs text-[var(--text-muted)] flex items-center gap-3 font-mono">
                      <span className="truncate max-w-sm">{r.repo_url}</span>
                      <span>·</span>
                      <span>{r.has_token ? '🔒 Read Token Encrypted' : 'Public Access'}</span>
                      <span>·</span>
                      <span>
                        Last scanned: {r.last_scanned_at ? new Date(r.last_scanned_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'Never'}
                      </span>
                    </div>

                    {r.scan_error && (
                      <p className="text-xs text-[var(--blocker)] font-mono mt-1">
                        Scan error: {r.scan_error}
                      </p>
                    )}
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    <button
                      type="button"
                      disabled={scanningRepoId === r.id}
                      onClick={() => handleTriggerScan(r.id)}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-[var(--radius-input)] bg-[var(--primary)] hover:bg-[var(--primary)]/90 text-white text-xs font-semibold shadow-2xs transition disabled:opacity-50 cursor-pointer"
                    >
                      <RefreshCw className={`w-3.5 h-3.5 ${scanningRepoId === r.id ? 'animate-spin' : ''}`} />
                      <span>{scanningRepoId === r.id ? 'Scanning...' : 'Scan Repo'}</span>
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ============================================================== */}
      {/* SUB-TAB 2: PROPOSED TRUTH CHANGES                              */}
      {/* ============================================================== */}
      {subTab === 'proposals' && (
        <div className="space-y-4">
          <div className="p-3.5 rounded-[var(--radius-card)] bg-[var(--surface)] border border-[var(--border)] text-xs text-[var(--text-muted)] flex items-start gap-2.5">
            <Info className="w-4 h-4 text-[var(--primary)] shrink-0 mt-0.5" />
            <span>
              <strong>Deterministic Ground-Truth Safety:</strong> Codebase scans <em>never</em> overwrite existing facts automatically. Every change creates a pending proposal requiring admin approval and explicit <code className="font-mono">valid_until</code> date assignment.
            </span>
          </div>

          {proposedChanges.length === 0 ? (
            <div className="bg-[var(--surface)] p-8 rounded-[var(--radius-card)] border border-[var(--border)] text-center">
              <CheckCircle2 className="w-10 h-10 text-[var(--cleared)] mx-auto mb-2" />
              <h3 className="text-sm font-bold text-[var(--text)]">Living Fact Ledger in Full Sync</h3>
              <p className="text-xs text-[var(--text-muted)] mt-1">
                Zero discrepancies between product code constants and verified brand claims.
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {proposedChanges.map((change) => {
                const isPending = change.status === 'PENDING';
                return (
                  <div
                    key={change.id}
                    className={`bg-[var(--surface)] p-5 rounded-[var(--radius-card)] border shadow-2xs space-y-3 ${
                      isPending ? 'border-l-4 border-l-[var(--warning-text)] border-[var(--border)]' : 'border-[var(--border)]'
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2 flex-wrap">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs px-2 py-0.5 rounded bg-[var(--surface-alt)] text-[var(--text)] font-bold border border-[var(--border)]">
                          {change.fact_code}
                        </span>
                        <span className="text-xs font-bold text-[var(--text)]">{change.fact_category}</span>
                      </div>
                      <Badge variant={change.status === 'APPROVED' ? 'cleared' : change.status === 'REJECTED' ? 'blocker' : 'warning'}>
                        {change.status}
                      </Badge>
                    </div>

                    {/* Code location citation */}
                    <div className="text-xs font-mono text-[var(--text-muted)] bg-[var(--surface-alt)]/60 p-2 rounded border border-[var(--border)]">
                      <span>Source: </span>
                      <strong className="text-[var(--text)]">{change.code_location}</strong>
                    </div>

                    {/* Side-by-side diff comparison */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs font-mono">
                      <div className="p-3 rounded-lg bg-[var(--blocker)]/10 border border-[var(--blocker)]/30">
                        <span className="text-[10px] font-bold text-[var(--blocker)] uppercase block mb-1">
                          Existing Verified Fact
                        </span>
                        <p className="text-[var(--blocker)] line-through">{change.old_value}</p>
                      </div>

                      <div className="p-3 rounded-lg bg-[var(--cleared)]/10 border border-[var(--cleared)]/30">
                        <span className="text-[10px] font-bold text-[var(--cleared)] uppercase block mb-1">
                          Product Code Ground-Truth
                        </span>
                        <p className="text-[var(--cleared)] font-bold">{change.new_value}</p>
                      </div>
                    </div>

                    {/* Action buttons */}
                    <div className="pt-3 border-t border-[var(--border)] flex items-center justify-between gap-2 flex-wrap">
                      <div>
                        {change.fact_id && (
                          <button
                            type="button"
                            onClick={() => handleViewBlastRadius(change.fact_id)}
                            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-[var(--radius-input)] border border-[var(--border)] text-xs font-medium text-[var(--text-muted)] hover:text-[var(--text)] hover:bg-[var(--surface-alt)] transition cursor-pointer"
                          >
                            <Layers className="w-3.5 h-3.5 text-[var(--primary)]" />
                            <span>View Blast Radius</span>
                          </button>
                        )}
                      </div>

                      <div className="flex items-center gap-2">
                        {isPending && (
                          <>
                            <button
                              type="button"
                              onClick={() => {
                                setRejectModalChange(change);
                                setRejectionReason('');
                              }}
                              className="px-3 py-1.5 rounded-[var(--radius-input)] border border-[var(--border)] text-xs font-medium text-[var(--text)] hover:bg-[var(--surface-alt)] transition cursor-pointer"
                            >
                              Reject Change
                            </button>

                            <button
                              type="button"
                              onClick={() => {
                                setApproveModalChange(change);
                                setValidUntilDate('2027-12-31');
                              }}
                              className="px-3.5 py-1.5 rounded-[var(--radius-input)] bg-[var(--primary)] hover:bg-[var(--primary)]/90 text-white text-xs font-bold shadow-2xs transition cursor-pointer flex items-center gap-1.5"
                            >
                              <Check className="w-3.5 h-3.5" />
                              <span>Approve &amp; Update Truth</span>
                            </button>
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* ============================================================== */}
      {/* SUB-TAB 3: SYMBOL MAPPINGS TABLE                               */}
      {/* ============================================================== */}
      {subTab === 'mappings' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between pb-2 border-b border-[var(--border)]">
            <span className="text-xs font-mono font-bold text-[var(--text)] uppercase">
              Admin-Editable Symbol &amp; Unit Conversion Table
            </span>
            <button
              type="button"
              onClick={() => setMappingModalOpen(true)}
              className="inline-flex items-center gap-1 px-3 py-1.5 bg-[var(--primary)] hover:bg-[var(--primary)]/90 text-white rounded-[var(--radius-input)] text-xs font-semibold shadow-2xs transition cursor-pointer"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Add Symbol Mapping</span>
            </button>
          </div>

          <div className="bg-[var(--surface)] rounded-[var(--radius-card)] border border-[var(--border)] overflow-hidden shadow-2xs">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-[var(--surface-alt)] text-[var(--text-muted)] font-mono uppercase text-[10px] border-b border-[var(--border)]">
                  <tr>
                    <th className="py-2.5 px-3 font-semibold">Code Symbol</th>
                    <th className="py-2.5 px-3 font-semibold">Semantic Key</th>
                    <th className="py-2.5 px-3 font-semibold">Target Fact</th>
                    <th className="py-2.5 px-3 font-semibold">Unit Type</th>
                    <th className="py-2.5 px-3 font-semibold">Scale</th>
                    <th className="py-2.5 px-3 font-semibold">Format</th>
                    <th className="py-2.5 px-3 font-semibold text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--border)] font-mono">
                  {mappings.map((m) => (
                    <tr key={m.id} className="hover:bg-[var(--surface-alt)]/40 transition">
                      <td className="py-2.5 px-3 font-bold text-[var(--text)]">{m.symbol_name}</td>
                      <td className="py-2.5 px-3 text-[var(--text-muted)]">{m.semantic_key}</td>
                      <td className="py-2.5 px-3">
                        {m.target_fact_code ? (
                          <span className="px-1.5 py-0.5 rounded bg-[var(--surface-alt)] text-[var(--primary)] font-bold">
                            {m.target_fact_code}
                          </span>
                        ) : (
                          <span className="text-[var(--text-muted)] italic">Unmapped</span>
                        )}
                      </td>
                      <td className="py-2.5 px-3">{m.unit_type}</td>
                      <td className="py-2.5 px-3">{m.scale_factor}×</td>
                      <td className="py-2.5 px-3 text-[var(--primary)]">{m.display_format}</td>
                      <td className="py-2.5 px-3 text-right">
                        <button
                          type="button"
                          onClick={async () => {
                            if (window.confirm(`Delete symbol mapping '${m.symbol_name}'?`)) {
                              await fetch(`${apiBase}/api/codebase/mappings/${m.id}/`, {
                                method: 'DELETE',
                                headers: getAuthHeaders(false),
                              });
                              setMappings(mappings.filter((x) => x.id !== m.id));
                              showToast('Symbol mapping removed.');
                            }
                          }}
                          className="p-1 rounded text-[var(--text-muted)] hover:text-[var(--blocker)] transition cursor-pointer"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* ============================================================== */}
      {/* SUB-TAB 4: EXTRACTED CONSTANTS TABLE                           */}
      {/* ============================================================== */}
      {subTab === 'constants' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between pb-2 border-b border-[var(--border)]">
            <span className="text-xs font-mono font-bold text-[var(--text)] uppercase">
              Parsed Repository Constants ({constants.length})
            </span>
            <span className="text-[11px] text-[var(--text-muted)] font-mono">
              AST ASTConstantExtractor · Read-Only Sandboxed
            </span>
          </div>

          <div className="bg-[var(--surface)] rounded-[var(--radius-card)] border border-[var(--border)] overflow-hidden shadow-2xs">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-[var(--surface-alt)] text-[var(--text-muted)] font-mono uppercase text-[10px] border-b border-[var(--border)]">
                  <tr>
                    <th className="py-2.5 px-3 font-semibold">Symbol Name</th>
                    <th className="py-2.5 px-3 font-semibold">Raw Value</th>
                    <th className="py-2.5 px-3 font-semibold">Normalized Value</th>
                    <th className="py-2.5 px-3 font-semibold">Source Location</th>
                    <th className="py-2.5 px-3 font-semibold">Commit SHA</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--border)] font-mono">
                  {constants.map((c) => (
                    <tr key={c.id} className="hover:bg-[var(--surface-alt)]/40 transition">
                      <td className="py-2.5 px-3 font-bold text-[var(--text)]">{c.symbol_name}</td>
                      <td className="py-2.5 px-3 text-[var(--text-muted)]">{c.raw_value}</td>
                      <td className="py-2.5 px-3 text-[var(--cleared)] font-bold">{c.normalized_value}</td>
                      <td className="py-2.5 px-3 text-[var(--text-muted)] truncate max-w-xs">
                        {c.file_path}:{c.line_number}
                      </td>
                      <td className="py-2.5 px-3 text-[var(--primary)]">{c.commit_sha?.slice(0, 7)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* ============================================================== */}
      {/* MODAL: CONNECT REPOSITORY                                      */}
      {/* ============================================================== */}
      <Dialog
        isOpen={connectModalOpen}
        onClose={() => setConnectModalOpen(false)}
        title="Connect Product Repository"
        description="Shallow clone sandbox for AST extraction. Repository code is never executed."
      >
        <form onSubmit={handleConnectRepo} className="space-y-4 text-xs font-sans">
          <div>
            <label className="block text-[11px] font-bold text-[var(--text)] uppercase font-mono mb-1">
              Repository Name
            </label>
            <input
              type="text"
              required
              value={repoFormData.repo_name}
              onChange={(e) => setRepoFormData({ ...repoFormData, repo_name: e.target.value })}
              placeholder="e.g. novapay/core-banking"
              className="w-full p-2 bg-[var(--surface-alt)] border border-[var(--border)] rounded-[var(--radius-input)] text-[var(--text)]"
            />
          </div>

          <div>
            <label className="block text-[11px] font-bold text-[var(--text)] uppercase font-mono mb-1">
              Repository URL (HTTPS / SSH)
            </label>
            <input
              type="text"
              required
              value={repoFormData.repo_url}
              onChange={(e) => setRepoFormData({ ...repoFormData, repo_url: e.target.value })}
              placeholder="https://github.com/novapay/core-banking"
              className="w-full p-2 bg-[var(--surface-alt)] border border-[var(--border)] rounded-[var(--radius-input)] text-[var(--text)]"
            />
            <span className="text-[10px] text-[var(--text-muted)] mt-0.5 block">
              SSRF protected. Localhost and private subnet addresses are forbidden.
            </span>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-[11px] font-bold text-[var(--text)] uppercase font-mono mb-1">
                Branch
              </label>
              <input
                type="text"
                required
                value={repoFormData.branch}
                onChange={(e) => setRepoFormData({ ...repoFormData, branch: e.target.value })}
                placeholder="main"
                className="w-full p-2 bg-[var(--surface-alt)] border border-[var(--border)] rounded-[var(--radius-input)] text-[var(--text)] font-mono"
              />
            </div>
            <div>
              <label className="block text-[11px] font-bold text-[var(--text)] uppercase font-mono mb-1">
                Webhook Secret (Optional)
              </label>
              <input
                type="text"
                value={repoFormData.webhook_secret}
                onChange={(e) => setRepoFormData({ ...repoFormData, webhook_secret: e.target.value })}
                placeholder="HMAC key for PR merges"
                className="w-full p-2 bg-[var(--surface-alt)] border border-[var(--border)] rounded-[var(--radius-input)] text-[var(--text)] font-mono"
              />
            </div>
          </div>

          <div>
            <label className="block text-[11px] font-bold text-[var(--text)] uppercase font-mono mb-1">
              Read-Only Access Token (GitHub App / PAT)
            </label>
            <input
              type="password"
              value={repoFormData.auth_token}
              onChange={(e) => setRepoFormData({ ...repoFormData, auth_token: e.target.value })}
              placeholder="ghp_..."
              className="w-full p-2 bg-[var(--surface-alt)] border border-[var(--border)] rounded-[var(--radius-input)] text-[var(--text)] font-mono"
            />
            <span className="text-[10px] text-[var(--text-muted)] mt-0.5 block flex items-center gap-1">
              <Lock className="w-3 h-3 text-[var(--cleared)] inline" />
              Token is AES-encrypted via Fernet upon receipt and never displayed again in UI or API responses.
            </span>
          </div>

          <div className="flex items-center justify-end gap-2 pt-2 border-t border-[var(--border)]">
            <button
              type="button"
              onClick={() => setConnectModalOpen(false)}
              className="px-3 py-1.5 rounded-[var(--radius-input)] border border-[var(--border)] text-[var(--text)]"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-1.5 rounded-[var(--radius-input)] bg-[var(--primary)] text-white font-bold"
            >
              Connect &amp; Encrypt
            </button>
          </div>
        </form>
      </Dialog>

      {/* ============================================================== */}
      {/* MODAL: ADD SYMBOL MAPPING                                      */}
      {/* ============================================================== */}
      <Dialog
        isOpen={mappingModalOpen}
        onClose={() => setMappingModalOpen(false)}
        title="Add Symbol to Fact Mapping"
        description="Links an extracted code symbol to a semantic truth key and target Fact Ledger entry."
      >
        <form onSubmit={handleCreateMapping} className="space-y-4 text-xs font-sans">
          <div>
            <label className="block text-[11px] font-bold text-[var(--text)] uppercase font-mono mb-1">
              Code Symbol Name
            </label>
            <input
              type="text"
              required
              value={mappingFormData.symbol_name}
              onChange={(e) => setMappingFormData({ ...mappingFormData, symbol_name: e.target.value })}
              placeholder="e.g. DEFAULT_FX_FEE"
              className="w-full p-2 bg-[var(--surface-alt)] border border-[var(--border)] rounded-[var(--radius-input)] text-[var(--text)] font-mono"
            />
          </div>

          <div>
            <label className="block text-[11px] font-bold text-[var(--text)] uppercase font-mono mb-1">
              Semantic Key
            </label>
            <input
              type="text"
              required
              value={mappingFormData.semantic_key}
              onChange={(e) => setMappingFormData({ ...mappingFormData, semantic_key: e.target.value })}
              placeholder="e.g. fx_fee_rate"
              className="w-full p-2 bg-[var(--surface-alt)] border border-[var(--border)] rounded-[var(--radius-input)] text-[var(--text)] font-mono"
            />
          </div>

          <div>
            <label className="block text-[11px] font-bold text-[var(--text)] uppercase font-mono mb-1">
              Target Fact Ledger Entry
            </label>
            <select
              value={mappingFormData.target_fact_id}
              onChange={(e) => setMappingFormData({ ...mappingFormData, target_fact_id: e.target.value })}
              className="w-full p-2 bg-[var(--surface-alt)] border border-[var(--border)] rounded-[var(--radius-input)] text-[var(--text)]"
            >
              <option value="">-- Select Target Fact (Optional) --</option>
              {facts.map((f) => (
                <option key={f.id} value={f.id}>
                  [{f.fact_code}] {f.category}: {f.claim_truth.slice(0, 50)}...
                </option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-3 gap-2">
            <div>
              <label className="block text-[10px] font-bold text-[var(--text)] uppercase font-mono mb-1">
                Unit Type
              </label>
              <select
                value={mappingFormData.unit_type}
                onChange={(e) => setMappingFormData({ ...mappingFormData, unit_type: e.target.value })}
                className="w-full p-2 bg-[var(--surface-alt)] border border-[var(--border)] rounded-[var(--radius-input)] text-[var(--text)]"
              >
                <option value="PERCENTAGE">Percentage</option>
                <option value="HOURS">Hours</option>
                <option value="DAYS">Days</option>
                <option value="COUNT">Count</option>
                <option value="CURRENCY">Currency</option>
                <option value="RAW">Raw</option>
              </select>
            </div>

            <div>
              <label className="block text-[10px] font-bold text-[var(--text)] uppercase font-mono mb-1">
                Scale Factor
              </label>
              <input
                type="number"
                step="any"
                value={mappingFormData.scale_factor}
                onChange={(e) => setMappingFormData({ ...mappingFormData, scale_factor: parseFloat(e.target.value) })}
                className="w-full p-2 bg-[var(--surface-alt)] border border-[var(--border)] rounded-[var(--radius-input)] text-[var(--text)] font-mono"
              />
            </div>

            <div>
              <label className="block text-[10px] font-bold text-[var(--text)] uppercase font-mono mb-1">
                Display Format
              </label>
              <input
                type="text"
                value={mappingFormData.display_format}
                onChange={(e) => setMappingFormData({ ...mappingFormData, display_format: e.target.value })}
                placeholder="{value}%"
                className="w-full p-2 bg-[var(--surface-alt)] border border-[var(--border)] rounded-[var(--radius-input)] text-[var(--text)] font-mono"
              />
            </div>
          </div>

          <div className="flex items-center justify-end gap-2 pt-2 border-t border-[var(--border)]">
            <button
              type="button"
              onClick={() => setMappingModalOpen(false)}
              className="px-3 py-1.5 rounded-[var(--radius-input)] border border-[var(--border)] text-[var(--text)]"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-1.5 rounded-[var(--radius-input)] bg-[var(--primary)] text-white font-bold"
            >
              Save Mapping
            </button>
          </div>
        </form>
      </Dialog>

      {/* ============================================================== */}
      {/* MODAL: APPROVE PROPOSED FACT CHANGE                            */}
      {/* ============================================================== */}
      {approveModalChange && (
        <Dialog
          isOpen={Boolean(approveModalChange)}
          onClose={() => setApproveModalChange(null)}
          title={`Approve Truth Change · ${approveModalChange.fact_code}`}
          description={`Update verified brand fact to match product code at ${approveModalChange.code_location}`}
        >
          <div className="space-y-4 text-xs font-sans">
            <div className="p-3 rounded-lg bg-[var(--surface-alt)] border border-[var(--border)]">
              <span className="text-[10px] font-mono text-[var(--text-muted)] uppercase block mb-1">
                Impact Warning
              </span>
              <p className="text-[var(--text)] leading-relaxed">
                Approving this proposal will overwrite Fact <code className="font-mono font-bold text-[var(--primary)]">{approveModalChange.fact_code}</code> in the Living Fact Ledger and trigger Module 3 Blast Radius calculation across all active marketing assets.
              </p>
            </div>

            <div className="grid grid-cols-2 gap-3 font-mono">
              <div className="p-2.5 rounded bg-[var(--blocker)]/10 border border-[var(--blocker)]/30">
                <span className="text-[10px] text-[var(--blocker)] font-bold uppercase block">Previous Value</span>
                <span className="text-[var(--blocker)] line-through">{approveModalChange.old_value}</span>
              </div>
              <div className="p-2.5 rounded bg-[var(--cleared)]/10 border border-[var(--cleared)]/30">
                <span className="text-[10px] text-[var(--cleared)] font-bold uppercase block">New Verified Value</span>
                <span className="text-[var(--cleared)] font-bold">{approveModalChange.new_value}</span>
              </div>
            </div>

            <div>
              <label className="block text-[11px] font-bold text-[var(--text)] uppercase font-mono mb-1 flex items-center gap-1.5">
                <Calendar className="w-3.5 h-3.5 text-[var(--primary)]" />
                <span>Fact Valid Until Date (Required - Admin Chosen)</span>
              </label>
              <input
                type="date"
                required
                value={validUntilDate}
                onChange={(e) => setValidUntilDate(e.target.value)}
                className="w-full p-2 bg-[var(--surface-alt)] border border-[var(--border)] rounded-[var(--radius-input)] text-[var(--text)] font-mono"
              />
              <span className="text-[10px] text-[var(--text-muted)] mt-0.5 block">
                Rule: valid_until is chosen by the administrator, never auto-invented.
              </span>
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-[var(--border)]">
              <button
                type="button"
                onClick={() => setApproveModalChange(null)}
                className="px-3 py-1.5 rounded-[var(--radius-input)] border border-[var(--border)] text-[var(--text)]"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleApproveProposal}
                className="px-4 py-1.5 rounded-[var(--radius-input)] bg-[var(--primary)] hover:bg-[var(--primary)]/90 text-white font-bold"
              >
                Confirm &amp; Update Truth
              </button>
            </div>
          </div>
        </Dialog>
      )}

      {/* ============================================================== */}
      {/* MODAL: REJECT PROPOSED FACT CHANGE                            */}
      {/* ============================================================== */}
      {rejectModalChange && (
        <Dialog
          isOpen={Boolean(rejectModalChange)}
          onClose={() => setRejectModalChange(null)}
          title={`Reject Truth Change · ${rejectModalChange.fact_code}`}
          description="Decline to update Fact Ledger with this extracted code constant."
        >
          <div className="space-y-4 text-xs font-sans">
            <div>
              <label className="block text-[11px] font-bold text-[var(--text)] uppercase font-mono mb-1">
                Rejection Reason (Audit Trail)
              </label>
              <textarea
                rows={3}
                value={rejectionReason}
                onChange={(e) => setRejectionReason(e.target.value)}
                placeholder="e.g. Constant reflects internal alpha microservice not yet released to production..."
                className="w-full p-2 bg-[var(--surface-alt)] border border-[var(--border)] rounded-[var(--radius-input)] text-[var(--text)]"
              />
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-[var(--border)]">
              <button
                type="button"
                onClick={() => setRejectModalChange(null)}
                className="px-3 py-1.5 rounded-[var(--radius-input)] border border-[var(--border)] text-[var(--text)]"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleRejectProposal}
                className="px-4 py-1.5 rounded-[var(--radius-input)] bg-[var(--blocker)] hover:bg-[var(--blocker)]/90 text-white font-bold"
              >
                Reject Proposal
              </button>
            </div>
          </div>
        </Dialog>
      )}
      {/* ============================================================== */}
      {/* MODAL: BLAST RADIUS & STALENESS IMPACT REPORT                   */}
      {/* ============================================================== */}
      {blastRadiusModalOpen && blastRadiusData && (
        <Dialog
          isOpen={blastRadiusModalOpen}
          onClose={() => setBlastRadiusModalOpen(false)}
          title={`Blast Radius & Staleness Impact · [${blastRadiusData.fact_code || 'FACT'}]`}
          description="Dependency graph analysis: Approved and in-review marketing assets affected by this truth change."
          maxWidth="max-w-3xl"
        >
          <div className="space-y-5 text-xs font-sans">
            {/* KPI Cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <div className="p-3 rounded-[var(--radius-card)] bg-[var(--surface-alt)]/60 border border-[var(--border)]">
                <span className="text-[10px] text-[var(--text-muted)] font-mono uppercase block">Affected Assets</span>
                <span className="text-xl font-bold font-serif text-[var(--text)] mt-0.5 block">
                  {blastRadiusData.affected_assets_count || 0}
                </span>
                <span className="text-[10px] text-[var(--blocker)] font-medium">Clearance Revoked</span>
              </div>

              <div className="p-3 rounded-[var(--radius-card)] bg-[var(--surface-alt)]/60 border border-[var(--border)]">
                <span className="text-[10px] text-[var(--text-muted)] font-mono uppercase block">Overall Severity</span>
                <div className="mt-1">
                  <Badge variant={blastRadiusData.severity === 'CRITICAL' ? 'blocker' : blastRadiusData.severity === 'HIGH' ? 'warning' : 'info'}>
                    {blastRadiusData.severity}
                  </Badge>
                </div>
                <span className="text-[10px] text-[var(--text-muted)] mt-1 block">
                  {blastRadiusData.severity === 'CRITICAL' ? 'Live Paid Ads detected' : 'Web & Social copy'}
                </span>
              </div>

              <div className="p-3 rounded-[var(--radius-card)] bg-[var(--surface-alt)]/60 border border-[var(--border)]">
                <span className="text-[10px] text-[var(--text-muted)] font-mono uppercase block">Est. Audience Reach</span>
                <span className="text-xl font-bold font-serif text-[var(--text)] mt-0.5 block">
                  {(blastRadiusData.estimated_reach || 0).toLocaleString()}
                </span>
                <span className="text-[10px] text-[var(--text-muted)]">Impressions exposure</span>
              </div>

              <div className="p-3 rounded-[var(--radius-card)] bg-[var(--surface-alt)]/60 border border-[var(--border)]">
                <span className="text-[10px] text-[var(--text-muted)] font-mono uppercase block">Affected Channels</span>
                <div className="flex flex-wrap gap-1 mt-1">
                  {Object.entries(blastRadiusData.channel_breakdown || {}).map(([ch, count]) => (
                    <span key={ch} className="font-mono text-[9px] px-1.5 py-0.5 rounded bg-[var(--surface)] border border-[var(--border)] text-[var(--text)]">
                      {ch}: {count}
                    </span>
                  ))}
                  {Object.keys(blastRadiusData.channel_breakdown || {}).length === 0 && (
                    <span className="text-[10px] text-[var(--text-muted)]">None</span>
                  )}
                </div>
              </div>
            </div>

            {/* Affected Asset Owners notification dispatch */}
            {blastRadiusData.affected_owners && blastRadiusData.affected_owners.length > 0 && (
              <div className="p-3 rounded-[var(--radius-card)] bg-[var(--surface-alt)]/40 border border-[var(--border)]">
                <div className="flex items-center gap-2 mb-1.5">
                  <Users className="w-3.5 h-3.5 text-[var(--primary)]" />
                  <span className="font-bold text-[11px] text-[var(--text)]">
                    Notified Asset Owners ({blastRadiusData.affected_owners.length})
                  </span>
                </div>
                <div className="flex flex-wrap gap-2">
                  {blastRadiusData.affected_owners.map((owner) => (
                    <span
                      key={owner.user_id}
                      className="px-2 py-1 rounded bg-[var(--surface)] border border-[var(--border)] text-[10px] text-[var(--text)] flex items-center gap-1.5"
                    >
                      <span className="w-1.5 h-1.5 rounded-full bg-[var(--warning-text)]" />
                      <strong>{owner.name || owner.username}</strong>
                      <span className="text-[var(--text-muted)] font-mono">({owner.asset_count} assets)</span>
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Stale Assets & Deterministic Draft Patches Table */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={handleToggleSelectAllPatches}
                    className="text-[var(--primary)] hover:text-[var(--primary)]/80 flex items-center gap-1 text-xs font-semibold cursor-pointer"
                  >
                    {selectedPatches.size === (blastRadiusData.draft_patches || []).length ? (
                      <CheckSquare className="w-4 h-4 text-[var(--primary)]" />
                    ) : (
                      <Square className="w-4 h-4 text-[var(--text-muted)]" />
                    )}
                    <span>
                      {selectedPatches.size === (blastRadiusData.draft_patches || []).length
                        ? 'Deselect All'
                        : `Select All (${blastRadiusData.draft_patches?.length || 0})`}
                    </span>
                  </button>
                </div>
                <span className="text-[11px] text-[var(--text-muted)] font-mono">
                  {selectedPatches.size} of {blastRadiusData.draft_patches?.length || 0} selected for batch patch
                </span>
              </div>

              <div className="max-h-64 overflow-y-auto rounded-[var(--radius-card)] border border-[var(--border)] bg-[var(--surface)] divide-y divide-[var(--border)]">
                {(!blastRadiusData.draft_patches || blastRadiusData.draft_patches.length === 0) ? (
                  <div className="p-4 text-center text-xs text-[var(--text-muted)]">
                    No active draft patches generated. All assets in sync.
                  </div>
                ) : (
                  blastRadiusData.draft_patches.map((patch) => {
                    const isSelected = selectedPatches.has(patch.submission_id);
                    return (
                      <div
                        key={patch.submission_id}
                        className={`p-3 text-xs transition flex items-start gap-3 ${
                          isSelected ? 'bg-[var(--surface-alt)]/30' : ''
                        }`}
                      >
                        <button
                          type="button"
                          onClick={() => handleToggleSelectPatch(patch.submission_id)}
                          className="mt-0.5 cursor-pointer text-[var(--primary)]"
                        >
                          {isSelected ? (
                            <CheckSquare className="w-4 h-4 text-[var(--primary)]" />
                          ) : (
                            <Square className="w-4 h-4 text-[var(--text-muted)]" />
                          )}
                        </button>

                        <div className="min-w-0 flex-1 space-y-1">
                          <div className="flex items-center gap-2">
                            <span className="font-bold text-[var(--text)]">{patch.title}</span>
                            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-[var(--surface-alt)] text-[var(--text-muted)] border border-[var(--border)]">
                              {patch.channel}
                            </span>
                            <Badge variant="blocker">STALE</Badge>
                          </div>

                          {/* Diff */}
                          <div className="font-mono text-[11px] flex items-center gap-2 flex-wrap">
                            <span className="px-2 py-0.5 rounded bg-[var(--blocker)]/10 text-[var(--blocker)] line-through border border-[var(--blocker)]/20">
                              {patch.old_excerpt}
                            </span>
                            <span className="text-[var(--text-muted)]">➔</span>
                            <span className="px-2 py-0.5 rounded bg-[var(--cleared)]/10 text-[var(--cleared)] font-bold border border-[var(--cleared)]/20">
                              {patch.replacement}
                            </span>
                          </div>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>

            {/* Footer Buttons */}
            <div className="flex items-center justify-between pt-3 border-t border-[var(--border)]">
              <button
                type="button"
                onClick={() => setBlastRadiusModalOpen(false)}
                className="px-3.5 py-1.5 rounded-[var(--radius-input)] border border-[var(--border)] text-xs font-medium text-[var(--text)] hover:bg-[var(--surface-alt)] transition cursor-pointer"
              >
                Close Report
              </button>

              <button
                type="button"
                disabled={selectedPatches.size === 0 || isApplyingPatches}
                onClick={() => setConfirmApplyModalOpen(true)}
                className="inline-flex items-center gap-1.5 px-4 py-1.5 rounded-[var(--radius-input)] bg-[var(--primary)] hover:bg-[var(--primary)]/90 text-white text-xs font-bold shadow-2xs transition disabled:opacity-50 cursor-pointer"
              >
                <Sparkles className="w-3.5 h-3.5" />
                <span>Apply Patches to Selected ({selectedPatches.size})</span>
              </button>
            </div>
          </div>
        </Dialog>
      )}

      {/* Confirmation Dialog for Wide Impact Batch Patching */}
      {confirmApplyModalOpen && (
        <Dialog
          isOpen={confirmApplyModalOpen}
          onClose={() => setConfirmApplyModalOpen(false)}
          title="Confirm Bulk Asset Remediation"
          description="Automated patch application and deterministic re-audit across campaign assets."
        >
          <div className="space-y-4 text-xs font-sans">
            <p className="text-[var(--text)]">
              You are about to patch <strong>{selectedPatches.size}</strong> stale assets with verified ground truth:
              <br />
              <code className="mt-1 block font-mono text-[11px] p-2 rounded bg-[var(--cleared)]/10 text-[var(--cleared)] border border-[var(--cleared)]/30 font-bold">
                {blastRadiusData?.new_value}
              </code>
            </p>
            <ul className="list-disc pl-4 space-y-1 text-[var(--text-muted)] text-[11px]">
              <li>Creates a new immutable version (v+1) for each selected asset.</li>
              <li>Runs deterministic lexicon, fact, and tone re-audits.</li>
              <li>Recalculates brand-compliance readiness scores automatically.</li>
              <li>Transitions assets from <strong>STALE_REAUDIT_REQUIRED</strong> to <strong>IN_REVIEW</strong>.</li>
              <li>Records FIX_ACCEPTED and SCAN events in the organization audit trail.</li>
            </ul>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-[var(--border)]">
              <button
                type="button"
                disabled={isApplyingPatches}
                onClick={() => setConfirmApplyModalOpen(false)}
                className="px-3.5 py-1.5 rounded-[var(--radius-input)] border border-[var(--border)] text-[var(--text)] text-xs font-medium cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={isApplyingPatches}
                onClick={handleExecuteBatchPatch}
                className="inline-flex items-center gap-1.5 px-4 py-1.5 rounded-[var(--radius-input)] bg-[var(--primary)] hover:bg-[var(--primary)]/90 text-white text-xs font-bold cursor-pointer disabled:opacity-50"
              >
                {isApplyingPatches ? (
                  <>
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                    <span>Applying Patches...</span>
                  </>
                ) : (
                  <>
                    <Check className="w-3.5 h-3.5" />
                    <span>Yes, Apply Patches &amp; Re-Audit</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </Dialog>
      )}
    </div>
  );
}
