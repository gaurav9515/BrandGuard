import React, { useState, useEffect, useRef } from 'react';
import {
  ShieldAlert,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  AlertOctagon,
  FileText,
  UploadCloud,
  RefreshCw,
  ArrowRight,
  Check,
  Eye,
  Sliders,
  Sparkles,
  Layers,
  ChevronDown,
  ChevronUp,
  Info,
  Clock,
  ExternalLink,
  Lock,
  GitBranch,
  Wand2,
  Image as ImageIcon,
  RotateCcw,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useLanguage } from '../context/LanguageContext';
import { useCompany } from '../context/CompanyContext';
import { API_BASE } from '../config/api';
import Badge from './ui/Badge';
import Toast from './ui/Toast';
import Dialog from './ui/Dialog';
import SampleGalleryModal from './SampleGalleryModal';

export default function PreFlightInspectorView({
  onRequestException,
  onNavigateToRule,
  initialSubmissionId = null,
  apiBase = API_BASE,
}) {
  const { user, token, isAdmin, isWriter } = useAuth();
  const { t } = useLanguage();
  const { activeCompany, activeProject, projects, switchProject } = useCompany();

  // Submission State
  const [submissionId, setSubmissionId] = useState(initialSubmissionId);
  const [currentVersionNumber, setCurrentVersionNumber] = useState(1);
  const [draftTitle, setDraftTitle] = useState('Global Launch Campaign · Cross-Border Rails');
  const [channel, setChannel] = useState('LINKEDIN_POST');
  const [confidentialMode, setConfidentialMode] = useState(false);
  const [submissionStatus, setSubmissionStatus] = useState('IN_REVIEW');
  const [draftText, setDraftText] = useState(
    "Don't get wrecked by banks! Our cheap transfers settle in 24 hrs with a 0.5% FX fee. We delve into enterprise cross-border liquidity in today's fast-paced landscape."
  );

  // File / Visual state
  const [uploadedFile, setUploadedFile] = useState(null);
  const [imagePreviewUrl, setImagePreviewUrl] = useState(null);
  const [useSampleBanner, setUseSampleBanner] = useState(false);
  const [galleryOpen, setGalleryOpen] = useState(false);

  // Active Tab: 'text' | 'visual' | 'tone'
  const [activeTab, setActiveTab] = useState('text');

  // Inspection & Scoring State
  const [isAuditing, setIsAuditing] = useState(false);
  const [readinessScore, setReadinessScore] = useState(64.0);
  const [scoreBreakdown, setScoreBreakdown] = useState({
    base_score: 100.0,
    blockers_count: 2,
    blockers_deduction: 36.0,
    blocker_rate: 18.0,
    warnings_count: 0,
    warnings_deduction: 0.0,
    warning_rate: 8.0,
    approved_exceptions_count: 0,
    approved_exceptions_deduction: 0.0,
    total_deductions: 36.0,
    final_score: 64.0,
  });
  const [scoreBreakdownOpen, setScoreBreakdownOpen] = useState(false);

  // Findings & Voice Fingerprint
  const [findings, setFindings] = useState([]);
  const [voiceFingerprint, setVoiceFingerprint] = useState(null);
  const [selectedFindingId, setSelectedFindingId] = useState(null);

  // Interactive Features
  const [colorBlindMode, setColorBlindMode] = useState(false); // Deuteranopia toggle
  const [beforeAfterSliderPos, setBeforeAfterSliderPos] = useState(50); // 0-100%
  const [liveLintStatus, setLiveLintStatus] = useState('idle'); // 'idle' | 'linting' | 'clean' | 'flags_found'

  // Diff Preview & Undo Toast
  const [diffPreviewFinding, setDiffPreviewFinding] = useState(null);
  const [toastUndo, setToastUndo] = useState(null);
  const [simpleToast, setSimpleToast] = useState(null);

  // Debounce ref for live lexicon linting
  const liveLintTimerRef = useRef(null);

  // Auto-expand score breakdown if score is 0
  useEffect(() => {
    if (readinessScore === 0) {
      setScoreBreakdownOpen(true);
    }
  }, [readinessScore]);

  const showToast = (msg, type = 'success') => {
    setSimpleToast({ message: msg, type });
    setTimeout(() => setSimpleToast(null), 3500);
  };

  const getAuthHeaders = (isJson = true) => {
    const headers = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;
    if (activeCompany?.id) headers['X-Company-ID'] = activeCompany.id;
    if (isJson) headers['Content-Type'] = 'application/json';
    return headers;
  };

  // Run full multi-modal audit (POST /api/submissions/audit/)
  const handleRunAudit = async (customText = null, customUseBanner = null, customFile = null) => {
    setIsAuditing(true);
    const textToAudit = customText !== null ? customText : draftText;
    const bannerFlag = customUseBanner !== null ? customUseBanner : useSampleBanner;
    const fileToAudit = customFile !== null ? customFile : uploadedFile;

    try {
      let res;
      if (fileToAudit) {
        const formData = new FormData();
        formData.append('title', draftTitle);
        formData.append('channel_context', channel);
        formData.append('confidential_mode', confidentialMode ? 'true' : 'false');
        formData.append('raw_text', textToAudit);
        formData.append('file', fileToAudit);
        formData.append('use_sample_banner', bannerFlag ? 'true' : 'false');
        if (activeCompany?.id) formData.append('company_id', activeCompany.id);
        if (activeProject?.id) formData.append('project_id', activeProject.id);

        res = await fetch(`${apiBase}/api/submissions/audit/`, {
          method: 'POST',
          headers: getAuthHeaders(false),
          body: formData,
        });
      } else {
        res = await fetch(`${apiBase}/api/submissions/audit/`, {
          method: 'POST',
          headers: getAuthHeaders(true),
          body: JSON.stringify({
            title: draftTitle,
            channel_context: channel,
            confidential_mode: confidentialMode,
            raw_text: textToAudit,
            use_sample_banner: bannerFlag,
            company_id: activeCompany?.id,
            project_id: activeProject?.id,
          }),
        });
      }

      if (res.ok) {
        const subData = await res.json();
        setSubmissionId(subData.id);
        if (subData.status) setSubmissionStatus(subData.status);

        const latestVer = subData.versions?.[subData.versions.length - 1];
        if (latestVer) {
          setCurrentVersionNumber(latestVer.version_number);
          setReadinessScore(latestVer.compliance_score);
          if (latestVer.score_breakdown) setScoreBreakdown(latestVer.score_breakdown);
          if (latestVer.voice_fingerprint) setVoiceFingerprint(latestVer.voice_fingerprint);
          setFindings(latestVer.findings || []);

          if (latestVer.uploaded_file_url) {
            setImagePreviewUrl(`${apiBase}${latestVer.uploaded_file_url}`);
          }
        }
        showToast(`Pre-flight audit complete: ${latestVer?.findings?.length || 0} checks recorded.`);
      } else {
        showToast('Audit failed. Please verify input parameters.', 'error');
      }
    } catch (err) {
      console.error('Audit network error:', err);
      showToast('Network error during pre-flight audit.', 'error');
    } finally {
      setIsAuditing(false);
    }
  };

  // Real-time debounced live lexicon linting
  const triggerDebouncedLiveLint = (text) => {
    if (liveLintTimerRef.current) {
      clearTimeout(liveLintTimerRef.current);
    }
    setLiveLintStatus('linting');

    liveLintTimerRef.current = setTimeout(async () => {
      try {
        const res = await fetch(`${apiBase}/api/submissions/live-lint/`, {
          method: 'POST',
          headers: getAuthHeaders(true),
          body: JSON.stringify({
            raw_text: text,
            channel_context: channel,
          }),
        });

        if (res.ok) {
          const data = await res.json();
          if (data.score_breakdown) {
            setScoreBreakdown(data.score_breakdown);
            setReadinessScore(data.compliance_score);
          }
          if (data.voice_fingerprint) {
            setVoiceFingerprint(data.voice_fingerprint);
          }
          if (data.findings) {
            setFindings((prevFindings) => {
              const visualFindings = prevFindings.filter((f) => f.pillar === 'VISUAL');
              return [...visualFindings, ...data.findings];
            });
            setLiveLintStatus(data.findings.length > 0 ? 'flags_found' : 'clean');
          }
        }
      } catch (err) {
        setLiveLintStatus('idle');
      }
    }, 300);
  };

  // Text change handler
  const handleTextChange = (e) => {
    const val = e.target.value;
    setDraftText(val);
    triggerDebouncedLiveLint(val);
  };

  // 1-Click "Apply Patch" with 10s Undo
  const handleApplyPatch = async (finding) => {
    const fix = finding.suggested_fixes?.[0];
    if (!fix) return;

    let replacement = fix;
    if (replacement.startsWith("Replace with '") && replacement.endsWith("'")) {
      replacement = replacement.slice(14, -1);
    } else if (replacement.startsWith("Replace with ")) {
      replacement = replacement.slice(13);
    }

    const excerpt = finding.source_excerpt;
    let patchedText = draftText;
    if (excerpt && patchedText.includes(excerpt)) {
      patchedText = patchedText.replace(excerpt, replacement);
    } else {
      patchedText = `${patchedText} ${replacement}`;
    }

    // Save previous state for undo
    const prevText = draftText;
    const prevFindings = findings;
    const prevScore = readinessScore;
    const prevBreakdown = scoreBreakdown;

    setDraftText(patchedText);

    // Provide 10-second undo toast
    setToastUndo({
      message: `Applied patch: "${replacement}".`,
      onUndo: () => {
        setDraftText(prevText);
        setFindings(prevFindings);
        setReadinessScore(prevScore);
        setScoreBreakdown(prevBreakdown);
        triggerDebouncedLiveLint(prevText);
        setToastUndo(null);
        showToast('Reverted patch to previous version.', 'info');
      },
    });

    // If an active submission exists in backend, call resolve endpoint
    if (finding.id && submissionId) {
      try {
        const res = await fetch(`${apiBase}/api/findings/${finding.id}/resolve/`, {
          method: 'POST',
          headers: getAuthHeaders(true),
          body: JSON.stringify({
            action: 'ACCEPT_FIX',
            chosen_fix: fix,
          }),
        });

        if (res.ok) {
          const data = await res.json();
          if (data.submission?.status) setSubmissionStatus(data.submission.status);
          const latestVer = data.submission?.versions?.[data.submission.versions.length - 1];
          if (latestVer) {
            setCurrentVersionNumber(latestVer.version_number);
            setReadinessScore(latestVer.compliance_score);
            if (latestVer.score_breakdown) setScoreBreakdown(latestVer.score_breakdown);
            setFindings(latestVer.findings || []);
          }
          return;
        }
      } catch (err) {
        // Fallback to local patch
      }
    }

    // Local patch re-lint
    triggerDebouncedLiveLint(patchedText);
  };

  // "Apply all safe fixes" (deterministic text patches only)
  const handleApplyAllSafeFixes = async () => {
    const safeFindings = textFindings.filter(
      (f) => f.suggested_fixes && f.suggested_fixes.length > 0 && f.source_excerpt
    );

    if (safeFindings.length === 0) {
      showToast('No deterministic safe patches available to apply.', 'info');
      return;
    }

    const prevText = draftText;
    const prevFindings = findings;
    const prevScore = readinessScore;
    const prevBreakdown = scoreBreakdown;

    let updatedText = draftText;
    let appliedCount = 0;

    for (const finding of safeFindings) {
      const fix = finding.suggested_fixes[0];
      let replacement = fix;
      if (replacement.startsWith("Replace with '") && replacement.endsWith("'")) {
        replacement = replacement.slice(14, -1);
      } else if (replacement.startsWith("Replace with ")) {
        replacement = replacement.slice(13);
      }

      if (finding.source_excerpt && updatedText.includes(finding.source_excerpt)) {
        updatedText = updatedText.replaceAll(finding.source_excerpt, replacement);
        appliedCount++;
      }
    }

    if (appliedCount === 0) {
      showToast('No matching excerpts found to patch in current text.', 'info');
      return;
    }

    setDraftText(updatedText);

    setToastUndo({
      message: `Applied ${appliedCount} safe deterministic patches!`,
      onUndo: () => {
        setDraftText(prevText);
        setFindings(prevFindings);
        setReadinessScore(prevScore);
        setScoreBreakdown(prevBreakdown);
        triggerDebouncedLiveLint(prevText);
        setToastUndo(null);
        showToast('Reverted all bulk patches.', 'info');
      },
    });

    handleRunAudit(updatedText);
  };

  // Initial load
  useEffect(() => {
    if (initialSubmissionId) {
      fetch(`${apiBase}/api/submissions/${initialSubmissionId}/`, { headers: getAuthHeaders(false) })
        .then((res) => (res.ok ? res.json() : null))
        .then((data) => {
          if (data && data.id) {
            setSubmissionId(data.id);
            setDraftTitle(data.title);
            setChannel(data.channel_context);
            if (data.status) setSubmissionStatus(data.status);
            const latestVer = data.versions?.[data.versions.length - 1];
            if (latestVer) {
              setDraftText(latestVer.raw_text || '');
              setCurrentVersionNumber(latestVer.version_number);
              setReadinessScore(latestVer.compliance_score);
              if (latestVer.score_breakdown) setScoreBreakdown(latestVer.score_breakdown);
              if (latestVer.voice_fingerprint) setVoiceFingerprint(latestVer.voice_fingerprint);
              setFindings(latestVer.findings || []);
              if (latestVer.uploaded_file_url) {
                setImagePreviewUrl(`${apiBase}${latestVer.uploaded_file_url}`);
              }
            }
          }
        })
        .catch(() => {});
    } else {
      handleRunAudit();
    }
  }, [initialSubmissionId]);

  // Load sample banner helper
  const handleLoadSampleBanner = () => {
    setUseSampleBanner(true);
    setImagePreviewUrl(`${apiBase}/media/sample_offbrand_banner.png`);
    setActiveTab('visual');
    handleRunAudit(draftText, true);
  };

  // Load realistic corpus sample from 42-asset gallery
  const handleSelectCorpusSample = (file, sampleMeta) => {
    setUploadedFile(file);
    setImagePreviewUrl(URL.createObjectURL(file));
    setUseSampleBanner(false);
    setActiveTab('visual');
    showToast(`Loaded ${sampleMeta.title} into Inspector`, 'success');
    handleRunAudit(draftText, false, file);
  };

  // Export Executive PDF Audit Report
  const handleExportPdf = async () => {
    const targetId = submissionId || 'default';
    try {
      showToast('Generating executive PDF compliance report...', 'info');
      const res = await fetch(`${apiBase}/api/submissions/${targetId}/export-pdf/`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      if (!res.ok) {
        throw new Error(`Export failed (${res.status})`);
      }
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `BrandGuard_Audit_${draftTitle.replace(/[^a-zA-Z0-9]/g, '_')}_${String(targetId).slice(0, 8)}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      showToast('Executive PDF audit dossier downloaded!', 'success');
    } catch (err) {
      showToast(`PDF export failed: ${err.message}`, 'error');
    }
  };

  // Filter findings for active tab
  const visualFindings = findings.filter((f) => f.pillar === 'VISUAL');
  const textFindings = findings.filter((f) => f.pillar === 'TONE' || f.pillar === 'FACTUAL');
  const toneFindings = findings.filter((f) => f.pillar === 'TONE');

  // Math breakdown calculation: check if deductions exceed 100 points
  const totalCalculatedDeduction =
    (scoreBreakdown.blockers_count || 0) * (scoreBreakdown.blocker_rate || 18) +
    (scoreBreakdown.warnings_count || 0) * (scoreBreakdown.warning_rate || 8);
  const isScoreFlooredAtZero = totalCalculatedDeduction >= 100 || readinessScore === 0;

  return (
    <div className="w-full space-y-6">
      {/* SVG Daltonization Matrix Filter for Deuteranopia Simulation */}
      <svg className="hidden">
        <filter id="deuteranopia-cvd-matrix">
          <feColorMatrix
            type="matrix"
            values="0.625 0.375 0 0 0  0.7 0.3 0 0 0  0 0.3 0.7 0 0  0 0 0 1 0"
          />
        </filter>
      </svg>

      {/* 10-Second Undoable Toast Notification */}
      {toastUndo && (
        <Toast
          message={toastUndo.message}
          onUndo={toastUndo.onUndo}
          onDismiss={() => setToastUndo(null)}
          duration={10000}
          undoLabel="Undo Patch"
        />
      )}

      {/* Simple Toast Notification */}
      {simpleToast && (
        <div
          role="status"
          className={`fixed bottom-6 right-6 z-50 px-4 py-3 rounded-[var(--radius-card)] shadow-xl flex items-center space-x-2 text-xs font-medium border ${
            simpleToast.type === 'error'
              ? 'bg-[var(--surface)] text-[var(--blocker)] border-[var(--blocker)]/40'
              : simpleToast.type === 'info'
              ? 'bg-[var(--surface)] text-[var(--info)] border-[var(--info)]/40'
              : 'bg-[var(--surface)] text-[var(--cleared)] border-[var(--cleared)]/40'
          }`}
        >
          {simpleToast.type === 'error' ? (
            <AlertOctagon className="w-4 h-4 text-[var(--blocker)] shrink-0" />
          ) : (
            <CheckCircle2 className="w-4 h-4 text-[var(--cleared)] shrink-0" />
          )}
          <span>{simpleToast.message}</span>
        </div>
      )}

      {/* Top Breadcrumb & Live Status Bar */}
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <div className="text-[11px] font-mono font-semibold tracking-wider text-[var(--primary)] uppercase flex items-center gap-2">
          <span>PRE-FLIGHT COMPILER &amp; LINTER</span>
          <span className="text-[var(--border)]">/</span>
          <span>{channel.replace('_', ' ')}</span>
          <span className="text-[var(--border)]">/</span>
          <span className="text-[var(--text-muted)] font-mono">DRAFT v{currentVersionNumber}</span>
        </div>

        <div className="flex items-center space-x-2">
          {liveLintStatus === 'linting' && (
            <span className="text-[11px] font-mono text-[var(--text-muted)] flex items-center">
              <RefreshCw className="w-3 h-3 mr-1 animate-spin text-[var(--primary)]" />
              Live Lexicon Linting...
            </span>
          )}
          {liveLintStatus === 'flags_found' && (
            <span className="text-[11px] font-semibold text-[var(--blocker)] bg-[var(--blocker)]/10 px-2 py-0.5 rounded border border-[var(--blocker)]/20">
              Live Flags Active
            </span>
          )}
          {liveLintStatus === 'clean' && (
            <span className="text-[11px] font-semibold text-[var(--cleared)] bg-[var(--cleared)]/10 px-2 py-0.5 rounded border border-[var(--cleared)]/20 flex items-center">
              <Check className="w-3 h-3 mr-1" />
              Live Lexicon Clean
            </span>
          )}
        </div>
      </div>

      {/* Module 3: Stale Truth Re-Audit Banner */}
      {submissionStatus === 'STALE_REAUDIT_REQUIRED' && (
        <div className="p-4 rounded-[var(--radius-card)] bg-[var(--blocker)]/10 border-2 border-[var(--blocker)]/30 text-[var(--text)] flex flex-col md:flex-row md:items-center justify-between gap-3 shadow-sm animate-fade-in">
          <div className="flex items-start gap-3">
            <div className="p-2 rounded-lg bg-[var(--blocker)] text-white shrink-0 mt-0.5">
              <AlertOctagon className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h4 className="font-bold text-sm font-serif text-[var(--blocker)]">
                  Truth Changed in Product Code · Stale Re-Audit Required
                </h4>
                <Badge variant="blocker">STALE_REAUDIT_REQUIRED</Badge>
              </div>
              <p className="text-xs text-[var(--text-muted)] mt-1">
                A verified fact cited in this campaign copy was updated in product code ground-truth. Previous cryptographic clearance signatures have been revoked. Review the highlighted finding and apply the deterministic patch below to re-align with verified product truth.
              </p>
            </div>
          </div>

          <div className="shrink-0 flex items-center gap-2">
            <button
              type="button"
              onClick={handleApplyAllSafeFixes}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-[var(--radius-input)] bg-[var(--primary)] hover:bg-[var(--primary)]/90 text-white text-xs font-bold shadow-2xs transition cursor-pointer"
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>Apply Draft Patch</span>
            </button>
          </div>
        </div>
      )}

      {/* Main Header & Controls (Fix 5: No title squishing/cut-off; Fix 6: Top Request Exception removed) */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between pb-5 border-b border-[var(--border)] gap-4">
        <div className="flex-1 min-w-0">
          <input
            type="text"
            value={draftTitle}
            onChange={(e) => setDraftTitle(e.target.value)}
            title={draftTitle}
            className="text-2xl font-bold font-serif tracking-tight text-[var(--text)] bg-transparent border-b border-transparent hover:border-[var(--border)] focus:border-[var(--primary)] focus:outline-hidden w-full py-0.5 transition truncate"
            placeholder="Campaign Draft Title..."
          />
          <p className="text-xs text-[var(--text-muted)] mt-1 truncate">
            Deterministic pre-flight compiler for {activeCompany?.name || 'NovaPay'} · Project: {activeProject?.name || 'Global Launch Campaign'} · Multi-modal inspection across Visual, Text, and Voice.
          </p>
        </div>

        {/* Global Inspector Action Buttons (Top-level Request Exception removed) */}
        <div className="flex items-center flex-wrap gap-2.5 shrink-0">
          <button
            type="button"
            onClick={() => setGalleryOpen(true)}
            className="inline-flex items-center px-3 py-1.5 border border-[var(--border)] bg-[var(--surface-alt)] shadow-2xs text-xs font-semibold rounded-[var(--radius-input)] text-[var(--primary)] hover:bg-[var(--surface)] transition cursor-pointer"
            title="Browse all 42 realistic test corpus banners and documents"
          >
            <Layers className="w-3.5 h-3.5 mr-1.5 text-[var(--primary)]" />
            <span>Sample Gallery (42)</span>
          </button>

          <button
            type="button"
            onClick={handleLoadSampleBanner}
            className="inline-flex items-center px-3 py-1.5 border border-[var(--border)] bg-[var(--surface-alt)] shadow-2xs text-xs font-semibold rounded-[var(--radius-input)] text-[var(--text)] hover:bg-[var(--surface)] transition cursor-pointer"
            title="Load sample offbrand banner with visual violations"
          >
            <ImageIcon className="w-3.5 h-3.5 mr-1.5 text-[var(--primary)]" />
            <span>Sample Banner</span>
          </button>

          <button
            type="button"
            onClick={handleExportPdf}
            className="inline-flex items-center px-3 py-1.5 border border-[var(--border)] shadow-2xs text-xs font-semibold rounded-[var(--radius-input)] text-[var(--text)] bg-[var(--surface)] hover:bg-[var(--surface-alt)] transition cursor-pointer"
            title="Export executive PDF audit report dossier"
          >
            <FileText className="w-3.5 h-3.5 mr-1.5 text-[var(--cleared)]" />
            <span>{t('btn_export_pdf', 'Export PDF Audit Report')}</span>
          </button>

          <button
            type="button"
            disabled={isAuditing}
            onClick={() => handleRunAudit()}
            className="inline-flex items-center px-4 py-1.5 border border-transparent text-xs font-semibold rounded-[var(--radius-input)] shadow-2xs text-white bg-[var(--primary)] hover:bg-[var(--primary)]/90 transition disabled:opacity-50 cursor-pointer"
          >
            {isAuditing ? (
              <>
                <RefreshCw className="w-3.5 h-3.5 mr-1.5 animate-spin" />
                <span>Auditing...</span>
              </>
            ) : (
              <>
                <RefreshCw className="w-3.5 h-3.5 mr-1.5" />
                <span>Run Pre-Flight Audit</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Readiness Score Breakdown Banner (Fix 10: Explicit Math + Auto-Expand when floored at 0) */}
      <div className="bg-[var(--surface)] p-5 rounded-[var(--radius-card)] border border-[var(--border)] shadow-2xs">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center space-x-4">
            {/* Score Ring / Pill */}
            <div
              className={`px-4 py-3 rounded-xl border flex flex-col items-center justify-center min-w-[100px] ${
                readinessScore >= 90
                  ? 'bg-[var(--cleared)]/10 text-[var(--cleared)] border-[var(--cleared)]/30'
                  : readinessScore >= 75
                  ? 'bg-[var(--warning-text)]/10 text-[var(--warning-text)] border-[var(--warning-text)]/30'
                  : 'bg-[var(--blocker)]/10 text-[var(--blocker)] border-[var(--blocker)]/30'
              }`}
            >
              <span className="font-mono text-3xl font-extrabold leading-none">{readinessScore}</span>
              <span className="text-[10px] font-bold uppercase tracking-wider mt-1 opacity-80">Score / 100</span>
            </div>

            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2 flex-wrap">
                <h3 className="text-base font-bold font-serif text-[var(--text)]">
                  {readinessScore >= 90
                    ? 'Brand-Compliance Cleared'
                    : readinessScore >= 75
                    ? 'Advisory Warning Clearance Required'
                    : 'Publication Blocked'}
                </h3>
                <span
                  className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wide border ${
                    readinessScore >= 90
                      ? 'bg-[var(--cleared)]/10 text-[var(--cleared)] border-[var(--cleared)]/30'
                      : readinessScore >= 75
                      ? 'bg-[var(--warning-text)]/10 text-[var(--warning-text)] border-[var(--warning-text)]/30'
                      : 'bg-[var(--blocker)]/10 text-[var(--blocker)] border-[var(--blocker)]/30'
                  }`}
                >
                  {readinessScore >= 90 ? 'Ready' : readinessScore >= 75 ? 'Soft Stop' : 'Hard Stop'}
                </span>
              </div>
              <p className="text-xs text-[var(--text-muted)] mt-1">
                {readinessScore >= 90
                  ? 'All blocker rules passed. Campaign copy and visuals comply with NovaPay brand guidelines.'
                  : `Detected ${scoreBreakdown.blockers_count} blocker(s) and ${scoreBreakdown.warnings_count} advisory warning(s). Apply patches below to raise score.`}
              </p>

              {/* Fix 10: Explicit Math Floor display */}
              {isScoreFlooredAtZero && (
                <div className="mt-2 text-xs font-mono text-[var(--blocker)] bg-[var(--blocker)]/10 px-2.5 py-1 rounded-md border border-[var(--blocker)]/25 inline-block">
                  ⚠️ {scoreBreakdown.blockers_count} blockers × 18 + {scoreBreakdown.warnings_count} warnings × 8 = {totalCalculatedDeduction} points deduction, score floored at 0
                </div>
              )}
            </div>
          </div>

          {/* Breakdown Toggle */}
          <button
            type="button"
            onClick={() => setScoreBreakdownOpen(!scoreBreakdownOpen)}
            className="inline-flex items-center text-xs font-semibold text-[var(--text)] hover:text-[var(--primary)] bg-[var(--surface-alt)] px-3 py-2 rounded-[var(--radius-input)] border border-[var(--border)] transition self-start sm:self-center cursor-pointer shrink-0"
          >
            <span>Score Breakdown</span>
            {scoreBreakdownOpen ? <ChevronUp className="w-4 h-4 ml-1" /> : <ChevronDown className="w-4 h-4 ml-1" />}
          </button>
        </div>

        {/* Expandable Mathematical Breakdown Accordion */}
        {scoreBreakdownOpen && (
          <div className="mt-4 pt-4 border-t border-[var(--border)] text-xs animate-fade-in">
            <span className="font-bold text-[var(--text)] block mb-2 uppercase tracking-wide text-[11px] font-mono">
              Mathematical Score Attribution
            </span>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 bg-[var(--surface-alt)]/60 p-3.5 rounded-xl border border-[var(--border)] font-mono">
              <div>
                <span className="text-[var(--text-muted)] block text-[11px]">Base Score:</span>
                <span className="font-bold text-[var(--text)] text-sm">100.0 pts</span>
              </div>
              <div>
                <span className="text-[var(--blocker)] block text-[11px]">
                  Blockers ({scoreBreakdown.blockers_count} × -{scoreBreakdown.blocker_rate}):
                </span>
                <span className="font-bold text-[var(--blocker)] text-sm">-{scoreBreakdown.blockers_deduction} pts</span>
              </div>
              <div>
                <span className="text-[var(--warning-text)] block text-[11px]">
                  Warnings ({scoreBreakdown.warnings_count} × -{scoreBreakdown.warning_rate}):
                </span>
                <span className="font-bold text-[var(--warning-text)] text-sm">-{scoreBreakdown.warnings_deduction} pts</span>
              </div>
              <div>
                <span className="text-[var(--cleared)] block text-[11px]">
                  Approved Exceptions (+{scoreBreakdown.approved_exceptions_count}):
                </span>
                <span className="font-bold text-[var(--cleared)] text-sm">+{scoreBreakdown.approved_exceptions_deduction} pts</span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Pillar Tabs: Text | Visual | Tone */}
      <div className="flex items-center space-x-2 border-b border-[var(--border)]">
        <button
          type="button"
          onClick={() => setActiveTab('text')}
          className={`pb-3 px-3.5 text-xs font-semibold transition border-b-2 flex items-center space-x-2 cursor-pointer ${
            activeTab === 'text'
              ? 'border-[var(--primary)] text-[var(--primary)]'
              : 'border-transparent text-[var(--text-muted)] hover:text-[var(--text)]'
          }`}
        >
          <FileText className="w-4 h-4" />
          <span>Text &amp; Lexicon ({textFindings.length})</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('visual')}
          className={`pb-3 px-3.5 text-xs font-semibold transition border-b-2 flex items-center space-x-2 cursor-pointer ${
            activeTab === 'visual'
              ? 'border-[var(--primary)] text-[var(--primary)]'
              : 'border-transparent text-[var(--text-muted)] hover:text-[var(--text)]'
          }`}
        >
          <ImageIcon className="w-4 h-4" />
          <span>Visual &amp; CVD ({visualFindings.length})</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('tone')}
          className={`pb-3 px-3.5 text-xs font-semibold transition border-b-2 flex items-center space-x-2 cursor-pointer ${
            activeTab === 'tone'
              ? 'border-[var(--primary)] text-[var(--primary)]'
              : 'border-transparent text-[var(--text-muted)] hover:text-[var(--text)]'
          }`}
        >
          <Wand2 className="w-4 h-4" />
          <span>Tone &amp; Voice Fingerprint ({toneFindings.length})</span>
        </button>
      </div>

      {/* ============================================================== */}
      {/* TAB 1: TEXT & LEXICON FINDINGS                                 */}
      {/* ============================================================== */}
      {activeTab === 'text' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left Column: Editor & Tokenizer Highlighting */}
          <div className="lg:col-span-7 space-y-4">
            <div className="bg-[var(--surface)] p-5 rounded-[var(--radius-card)] border border-[var(--border)] shadow-2xs space-y-3">
              <div className="flex items-center justify-between pb-2 border-b border-[var(--border)]">
                <span className="text-xs font-bold text-[var(--text)] uppercase tracking-wide font-mono">
                  Copy Editor · {channel.replace('_', ' ')}
                </span>
                <span className="text-[11px] text-[var(--text-muted)] font-mono">
                  {draftText.length} chars · {draftText.split(/\s+/).filter(Boolean).length} words
                </span>
              </div>

              {/* Textarea */}
              <textarea
                rows={5}
                value={draftText}
                onChange={handleTextChange}
                placeholder="Enter campaign draft text..."
                className="w-full p-3.5 text-sm bg-[var(--surface-alt)]/60 border border-[var(--border)] rounded-[var(--radius-input)] text-[var(--text)] leading-relaxed focus:bg-[var(--surface)] focus:border-[var(--primary)] focus:outline-hidden transition font-sans"
              />

              {/* Tokenized Highlighting View */}
              <div className="pt-2">
                <span className="text-xs font-bold text-[var(--text)] uppercase tracking-wide block mb-2 font-mono">
                  Interactive Lexicon Highlighting
                </span>
                <div className="p-4 bg-[var(--surface-alt)]/60 rounded-[var(--radius-input)] border border-[var(--border)] text-sm leading-relaxed text-[var(--text)] font-sans min-h-[80px]">
                  {(() => {
                    const words = draftText.split(/(\s+)/);
                    return words.map((tokenStr, idx) => {
                      const clean = tokenStr.toLowerCase().replace(/[^a-z0-9]/g, '');
                      const matchFinding = findings.find(
                        (f) =>
                          f.source_excerpt &&
                          (tokenStr.toLowerCase().includes(f.source_excerpt.toLowerCase()) ||
                            clean === f.source_excerpt.toLowerCase() ||
                            f.source_excerpt.toLowerCase().includes(clean))
                      );

                      if (matchFinding) {
                        const isBlocker = matchFinding.severity === 'BLOCKER';
                        const isSelected = selectedFindingId === matchFinding.id;

                        return (
                          <span
                            key={idx}
                            onClick={() => setSelectedFindingId(matchFinding.id)}
                            className={`cursor-pointer px-1 py-0.5 rounded font-medium transition ${
                              isBlocker
                                ? 'bg-[var(--blocker)]/20 text-[var(--blocker)] underline decoration-[var(--blocker)] decoration-wavy'
                                : 'bg-[var(--warning-text)]/20 text-[var(--warning-text)] underline decoration-[var(--warning-text)] decoration-wavy'
                            } ${isSelected ? 'ring-2 ring-[var(--primary)]' : ''}`}
                            title={`[${matchFinding.rule_citation_code}] ${matchFinding.rule_citation_title}`}
                          >
                            {tokenStr}
                          </span>
                        );
                      }
                      return <span key={idx}>{tokenStr}</span>;
                    });
                  })()}
                </div>
              </div>
            </div>
          </div>

          {/* Right Column: Findings List (Fix 7 & 8: Red for blocker, amber for warning, never green border) */}
          <div className="lg:col-span-5 space-y-4">
            <div className="flex items-center justify-between gap-2 flex-wrap">
              <div>
                <span className="text-xs font-bold text-[var(--text)] uppercase tracking-wide font-mono">
                  Detected Rules &amp; Patches ({textFindings.length})
                </span>
                <span className="block text-[11px] text-[var(--text-muted)]">
                  Deterministic patches update copy into v{currentVersionNumber + 1}
                </span>
              </div>

              {/* "Apply all safe fixes" button */}
              {textFindings.some((f) => f.suggested_fixes && f.suggested_fixes.length > 0) && (
                <button
                  type="button"
                  onClick={handleApplyAllSafeFixes}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-[var(--surface-alt)] hover:bg-[var(--primary)] hover:text-white text-[var(--primary)] border border-[var(--border)] rounded-[var(--radius-input)] text-xs font-bold transition shadow-2xs cursor-pointer"
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>Apply all safe fixes</span>
                </button>
              )}
            </div>

            {textFindings.length === 0 ? (
              <div className="bg-[var(--surface)] p-8 rounded-[var(--radius-card)] border border-[var(--border)] text-center">
                <CheckCircle2 className="w-10 h-10 text-[var(--cleared)] mx-auto mb-2" />
                <h4 className="text-sm font-bold text-[var(--text)]">Zero Lexicon Violations</h4>
                <p className="text-xs text-[var(--text-muted)] mt-1">Copy passes all deterministic brand tone and fact checks.</p>
              </div>
            ) : (
              <div className="space-y-3">
                {textFindings.map((finding, idx) => {
                  const isBlocker = finding.severity === 'BLOCKER';
                  const isSelected = selectedFindingId === finding.id;
                  const isFactOrAccessibility =
                    finding.rule_citation_code?.startsWith('FACT_') ||
                    finding.pillar === 'FACTUAL' ||
                    finding.rule_citation_code?.includes('WCAG') ||
                    finding.rule_citation_code?.includes('CONTRAST') ||
                    finding.rule_citation_code?.includes('COLOR');

                  return (
                    <div
                      key={finding.id || idx}
                      onClick={() => setSelectedFindingId(finding.id)}
                      className={`p-4 rounded-[var(--radius-card)] border bg-[var(--surface)] transition-all cursor-pointer ${
                        isBlocker
                          ? 'border-l-4 border-l-[var(--blocker)] border-[var(--border)]'
                          : 'border-l-4 border-l-[var(--warning-text)] border-[var(--border)]'
                      } ${isSelected ? 'ring-2 ring-[var(--primary)]' : 'hover:shadow-2xs'}`}
                    >
                      {/* Header: Rule Code Chip + Severity Badge + Title */}
                      <div className="flex items-center justify-between gap-2 flex-wrap">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="font-mono text-xs px-2 py-0.5 rounded bg-[var(--surface-alt)] text-[var(--text)] font-bold border border-[var(--border)]">
                            {finding.rule_citation_code}
                          </span>
                          <Badge variant={isBlocker ? 'blocker' : 'warning'}>
                            {finding.severity}
                          </Badge>
                        </div>
                        <span className="text-[10px] font-mono text-[var(--text-muted)] uppercase">
                          {finding.pillar}
                        </span>
                      </div>

                      <h4 className="text-xs font-bold text-[var(--text)] mt-2">
                        {finding.rule_citation_title}
                      </h4>

                      <p className="text-xs text-[var(--text-muted)] mt-1 leading-relaxed">
                        {finding.explanation}
                      </p>

                      {/* Source Excerpt */}
                      {finding.source_excerpt && (
                        <div className="mt-2.5 p-2 rounded-[var(--radius-input)] bg-[var(--surface-alt)]/60 border border-[var(--border)] text-xs font-mono">
                          <span className="text-[var(--text-muted)]">Trigger: </span>
                          <span className="text-[var(--blocker)] font-bold">"{finding.source_excerpt}"</span>
                        </div>
                      )}

                      {/* Unclipped Recommendation Box */}
                      {finding.suggested_fixes && finding.suggested_fixes.length > 0 && (
                        <div className="mt-3 p-3 rounded-[var(--radius-input)] bg-[var(--surface-alt)] border border-[var(--border)] text-xs">
                          <div className="font-semibold text-[var(--primary)] flex items-center gap-1.5 mb-1">
                            <CheckCircle2 className="w-3.5 h-3.5 text-[var(--cleared)]" />
                            <span>Recommendation</span>
                          </div>
                          <div className="text-[var(--text)] font-sans leading-relaxed">
                            {finding.suggested_fixes[0]}
                          </div>
                        </div>
                      )}

                      {/* Action Buttons Row */}
                      <div className="mt-3.5 pt-3 border-t border-[var(--border)] flex items-center justify-between gap-2 flex-wrap">
                        <div className="flex items-center gap-2">
                          {finding.suggested_fixes && finding.suggested_fixes.length > 0 && (
                            <>
                              <button
                                type="button"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleApplyPatch(finding);
                                }}
                                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-[var(--radius-input)] bg-[var(--primary)] hover:bg-[var(--primary)]/90 text-white text-xs font-semibold shadow-2xs transition cursor-pointer"
                              >
                                <Sparkles className="w-3.5 h-3.5" />
                                <span>Apply patch</span>
                              </button>

                              <button
                                type="button"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setDiffPreviewFinding(finding);
                                }}
                                className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-[var(--radius-input)] border border-[var(--border)] bg-[var(--surface)] hover:bg-[var(--surface-alt)] text-[var(--text)] text-xs font-medium transition cursor-pointer"
                              >
                                <Eye className="w-3.5 h-3.5 text-[var(--text-muted)]" />
                                <span>Preview diff</span>
                              </button>
                            </>
                          )}
                        </div>

                        {/* Request Exception: Hidden for Admin; Disabled with tooltip for FACT/accessibility rules */}
                        {!isAdmin && (
                          <div className="relative group">
                            <button
                              type="button"
                              disabled={isFactOrAccessibility}
                              onClick={(e) => {
                                e.stopPropagation();
                                if (isFactOrAccessibility) return;
                                if (onRequestException) {
                                  onRequestException({
                                    submissionId: submissionId || 'DRAFT_024',
                                    draftTitle: draftTitle,
                                    channel: channel,
                                    quoteText: finding.source_excerpt || draftText.slice(0, 40),
                                    ruleCode: finding.rule_citation_code,
                                    ruleTitle: finding.rule_citation_title,
                                    explanation: finding.explanation,
                                  });
                                }
                              }}
                              className={`inline-flex items-center gap-1 px-2.5 py-1.5 rounded-[var(--radius-input)] border text-xs font-medium transition ${
                                isFactOrAccessibility
                                  ? 'opacity-40 border-[var(--border)] text-[var(--text-muted)] cursor-not-allowed bg-[var(--surface-alt)]/40'
                                  : 'border-[var(--border)] bg-[var(--surface)] hover:bg-[var(--surface-alt)] text-[var(--text)] cursor-pointer'
                              }`}
                              title={
                                isFactOrAccessibility
                                  ? 'Exceptions cannot be granted for factual claims or accessibility standards (non-waivable).'
                                  : 'Request manager exception'
                              }
                            >
                              {isFactOrAccessibility && <Lock className="w-3 h-3 text-[var(--text-muted)]" />}
                              <span>Request exception</span>
                            </button>
                            {isFactOrAccessibility && (
                              <span className="hidden group-hover:block absolute bottom-full right-0 mb-1 z-30 w-64 p-2 bg-[var(--surface)] text-[var(--text-muted)] border border-[var(--border)] shadow-md rounded-lg text-[10px] leading-tight">
                                Exceptions cannot be granted for factual claims or accessibility standards (non-waivable).
                              </span>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ============================================================== */}
      {/* TAB 2: VISUAL & CVD (BOUNDING BOXES, SLIDER, DEUTERANOPIA)      */}
      {/* ============================================================== */}
      {activeTab === 'visual' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left Column: Visual Inspector with Bounding Boxes & Before/After Slider */}
          <div className="lg:col-span-8 space-y-4">
            <div className="bg-[var(--surface)] p-5 rounded-[var(--radius-card)] border border-[var(--border)] shadow-2xs space-y-4">
              {/* Controls Toolbar: Deuteranopia Toggle + Before/After Slider toggle */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-[var(--border)] gap-3">
                <div className="flex items-center space-x-2">
                  <span className="text-xs font-bold text-[var(--text)] uppercase tracking-wide font-mono">
                    Computer Vision Canvas
                  </span>
                  <span className="text-[11px] text-[var(--text-muted)] font-mono">
                    (CIEDE2000 ΔE · WCAG 2.1 AA · Clear-Space)
                  </span>
                </div>

                {/* Color-Blind Deuteranopia Toggle Button */}
                <button
                  type="button"
                  onClick={() => setColorBlindMode(!colorBlindMode)}
                  className={`inline-flex items-center px-3 py-1.5 rounded-[var(--radius-input)] text-xs font-semibold transition border cursor-pointer ${
                    colorBlindMode
                      ? 'bg-[var(--warning-text)] text-white border-[var(--warning-text)] shadow-2xs'
                      : 'bg-[var(--surface-alt)] text-[var(--text)] border-[var(--border)] hover:bg-[var(--surface)]'
                  }`}
                >
                  <Eye className="w-3.5 h-3.5 mr-1.5" />
                  {colorBlindMode ? 'Deuteranopia CVD: ON' : 'Simulate Deuteranopia'}
                </button>
              </div>

              {/* Color Blind Notice */}
              {colorBlindMode && (
                <div className="p-3 rounded-xl bg-[var(--warning-text)]/10 border border-[var(--warning-text)]/30 text-xs text-[var(--text)] flex items-start space-x-2 animate-fade-in">
                  <Info className="w-4 h-4 text-[var(--warning-text)] mt-0.5 shrink-0" />
                  <span>
                    <strong>Deuteranopia Daltonization active (affects ~8% of males):</strong> Red and green luminance collapse into ambiguous yellowish-gray tones. Low-contrast elements become illegible.
                  </span>
                </div>
              )}

              {/* Image Canvas with Interactive Bounding Box Overlays */}
              <div
                className="relative rounded-xl border border-[var(--border)] overflow-hidden bg-zinc-950 flex items-center justify-center min-h-[360px]"
                style={{
                  filter: colorBlindMode ? 'url(#deuteranopia-cvd-matrix)' : 'none',
                }}
              >
                {imagePreviewUrl ? (
                  <div className="relative w-full h-full flex items-center justify-center">
                    <img
                      src={imagePreviewUrl}
                      alt="Audited Visual Asset"
                      className="max-h-[460px] w-auto object-contain select-none"
                    />

                    {/* Bounding Box Overlays */}
                    {visualFindings.map((vf, idx) => {
                      const loc = vf.location_json || {};
                      if (!loc.w_pct) return null;
                      const isBlocker = vf.severity === 'BLOCKER';
                      const isSelected = selectedFindingId === vf.id;

                      return (
                        <div
                          key={vf.id || idx}
                          onClick={() => setSelectedFindingId(vf.id)}
                          style={{
                            left: `${loc.x_pct}%`,
                            top: `${loc.y_pct}%`,
                            width: `${loc.w_pct}%`,
                            height: `${loc.h_pct}%`,
                          }}
                          className={`absolute cursor-pointer transition-all border-2 ${
                            loc.is_exclusion_zone ? 'border-dashed' : 'border-solid'
                          } ${
                            isSelected
                              ? 'border-[var(--primary)] bg-[var(--primary)]/20 ring-4 ring-[var(--primary)]/40'
                              : isBlocker
                              ? 'border-[var(--blocker)] bg-[var(--blocker)]/20 hover:bg-[var(--blocker)]/30'
                              : 'border-[var(--warning-text)] bg-[var(--warning-text)]/20 hover:bg-[var(--warning-text)]/30'
                          }`}
                        >
                          <span
                            className={`absolute -top-6 left-0 text-[10px] font-mono font-bold px-1.5 py-0.5 rounded shadow ${
                              isBlocker ? 'bg-[var(--blocker)] text-white' : 'bg-[var(--warning-text)] text-black'
                            }`}
                          >
                            {vf.rule_citation_code}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <div className="text-center p-8 text-zinc-400 space-y-3">
                    <UploadCloud className="w-10 h-10 mx-auto text-zinc-500" />
                    <div>
                      <p className="text-sm font-semibold text-zinc-300">No Visual Asset Loaded</p>
                      <p className="text-xs text-zinc-500">Upload a banner or load the sample banner to view CV bounding boxes.</p>
                    </div>
                    <div className="flex items-center justify-center gap-2">
                      <button
                        type="button"
                        onClick={() => setGalleryOpen(true)}
                        className="px-4 py-2 bg-[var(--primary)] hover:bg-[var(--primary)]/90 text-white rounded-[var(--radius-input)] text-xs font-semibold transition cursor-pointer flex items-center gap-1.5"
                      >
                        <Layers className="w-3.5 h-3.5" />
                        <span>Browse Sample Gallery (42)</span>
                      </button>
                      <button
                        type="button"
                        onClick={handleLoadSampleBanner}
                        className="px-4 py-2 bg-[var(--surface-alt)] hover:bg-[var(--surface)] text-[var(--text)] border border-[var(--border)] rounded-[var(--radius-input)] text-xs font-semibold transition cursor-pointer"
                      >
                        Load Quick Banner
                      </button>
                    </div>
                  </div>
                )}
              </div>

              {/* Before / After Comparison Slider */}
              <div className="pt-2">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-bold text-[var(--text)] uppercase tracking-wide font-mono">
                    Before vs After Compliance Adjustment Slider
                  </span>
                  <span className="text-[11px] font-mono text-[var(--text-muted)]">
                    Split Position: {beforeAfterSliderPos}%
                  </span>
                </div>

                <div className="flex items-center space-x-3">
                  <span className="text-[11px] font-bold text-[var(--blocker)]">Before (Off-brand)</span>
                  <input
                    type="range"
                    min="0"
                    max="100"
                    value={beforeAfterSliderPos}
                    onChange={(e) => setBeforeAfterSliderPos(Number(e.target.value))}
                    className="flex-1 accent-[var(--primary)] cursor-pointer h-1.5 bg-[var(--surface-alt)] rounded-lg"
                  />
                  <span className="text-[11px] font-bold text-[var(--cleared)]">After (Brand-Compliance Cleared)</span>
                </div>
              </div>
            </div>
          </div>

          {/* Right Column: Visual Findings List */}
          <div className="lg:col-span-4 space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-[var(--text)] uppercase tracking-wide font-mono">
                Visual Violations ({visualFindings.length})
              </span>
              <span className="text-[11px] text-[var(--text-muted)]">WCAG &amp; CIEDE2000</span>
            </div>

            {visualFindings.length === 0 ? (
              <div className="bg-[var(--surface)] p-8 rounded-[var(--radius-card)] border border-[var(--border)] text-center">
                <CheckCircle2 className="w-10 h-10 text-[var(--cleared)] mx-auto mb-2" />
                <h4 className="text-sm font-bold text-[var(--text)]">Visuals Compliant</h4>
                <p className="text-xs text-[var(--text-muted)] mt-1">
                  Palette swatches within ΔE 4.0 tolerance. Contrast ratios satisfy WCAG 2.1 AA (4.5:1).
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {visualFindings.map((vf, idx) => {
                  const isBlocker = vf.severity === 'BLOCKER';
                  const isSelected = selectedFindingId === vf.id;

                  return (
                    <div
                      key={vf.id || idx}
                      onClick={() => setSelectedFindingId(vf.id)}
                      className={`p-4 rounded-[var(--radius-card)] border transition cursor-pointer bg-[var(--surface)] ${
                        isBlocker
                          ? 'border-l-4 border-l-[var(--blocker)] border-[var(--border)]'
                          : 'border-l-4 border-l-[var(--warning-text)] border-[var(--border)]'
                      } ${isSelected ? 'ring-2 ring-[var(--primary)]' : 'hover:shadow-2xs'}`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold font-mono bg-[var(--surface-alt)] text-[var(--text)] border border-[var(--border)]">
                          {vf.rule_citation_code}
                        </span>
                        <Badge variant={isBlocker ? 'blocker' : 'warning'}>
                          {vf.severity}
                        </Badge>
                      </div>

                      <h4 className="text-xs font-bold text-[var(--text)] mt-2">{vf.rule_citation_title}</h4>
                      <p className="text-xs text-[var(--text-muted)] mt-1 leading-relaxed">{vf.explanation}</p>

                      {vf.suggested_fixes && vf.suggested_fixes.length > 0 && (
                        <div className="mt-3 pt-2 border-t border-[var(--border)] flex items-center justify-between gap-2">
                          <span className="text-[11px] text-[var(--primary)] font-semibold line-clamp-1">
                            ✓ {vf.suggested_fixes[0]}
                          </span>
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              showToast('Applied OpenCV color remediation patch.');
                            }}
                            className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-[var(--primary)] hover:bg-[var(--primary)]/90 text-white text-xs font-semibold shrink-0 cursor-pointer"
                          >
                            <Sparkles className="w-3 h-3" />
                            <span>Apply color fix</span>
                          </button>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ============================================================== */}
      {/* TAB 3: TONE & VOICE FINGERPRINT RADAR                          */}
      {/* ============================================================== */}
      {activeTab === 'tone' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left Column: 4-Axis Voice Radar Card */}
          <div className="lg:col-span-7 space-y-4">
            <div className="bg-[var(--surface)] p-6 rounded-[var(--radius-card)] border border-[var(--border)] shadow-2xs space-y-5">
              <div className="flex items-center justify-between border-b border-[var(--border)] pb-3">
                <div>
                  <h3 className="text-sm font-bold text-[var(--text)] flex items-center font-serif">
                    <Wand2 className="w-4 h-4 mr-2 text-[var(--primary)]" />
                    4-Axis Voice Fingerprint Radar
                  </h3>
                  <p className="text-xs text-[var(--text-muted)] mt-0.5">
                    Evaluates copy against the approved NovaPay institutional envelope for {channel.replace('_', ' ')}.
                  </p>
                </div>
                <span className="text-[11px] font-mono font-bold bg-[var(--surface-alt)] text-[var(--primary)] px-2 py-0.5 rounded border border-[var(--border)]">
                  Target: {channel}
                </span>
              </div>

              {/* 4-Axis Voice Indicators */}
              <div className="space-y-4">
                {[
                  {
                    axis: 'Confidence',
                    val: voiceFingerprint?.confidence || 0.82,
                    target: '0.70 - 0.90',
                    desc: 'Balanced institutional authority without overbearing arrogance.',
                  },
                  {
                    axis: 'Directness',
                    val: voiceFingerprint?.directness || 0.78,
                    target: '0.65 - 0.85',
                    desc: 'Clear, crisp value propositions; zero conversational AI filler.',
                  },
                  {
                    axis: 'Precision',
                    val: voiceFingerprint?.precision || 0.88,
                    target: '0.80 - 0.95',
                    desc: 'Quantifiable operational metrics (e.g. 24h settlement, 0.5% fee).',
                  },
                  {
                    axis: 'Warmth',
                    val: voiceFingerprint?.warmth || 0.55,
                    target: '0.40 - 0.65',
                    desc: 'Professional fintech courtesy without informal slang.',
                  },
                ].map((item) => (
                  <div key={item.axis} className="bg-[var(--surface-alt)]/60 p-3.5 rounded-xl border border-[var(--border)]">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-bold text-[var(--text)]">{item.axis}</span>
                      <span className="font-mono text-[var(--text-muted)]">
                        Observed: <strong className="text-[var(--text)]">{Math.round(item.val * 100)}%</strong> · Target: {item.target}
                      </span>
                    </div>
                    {/* Bar meter */}
                    <div className="mt-2 w-full h-2 bg-[var(--border)] rounded-full overflow-hidden">
                      <div
                        className="h-full bg-[var(--primary)] rounded-full transition-all duration-500"
                        style={{ width: `${Math.min(100, Math.round(item.val * 100))}%` }}
                      />
                    </div>
                    <p className="text-[11px] text-[var(--text-muted)] mt-1.5">{item.desc}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Right Column: Tone Violations & Softening Patches */}
          <div className="lg:col-span-5 space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-[var(--text)] uppercase tracking-wide font-mono">
                Tone Linter Findings ({toneFindings.length})
              </span>
              <span className="text-[11px] text-[var(--text-muted)]">Executive voice policy</span>
            </div>

            {toneFindings.length === 0 ? (
              <div className="bg-[var(--surface)] p-8 rounded-[var(--radius-card)] border border-[var(--border)] text-center">
                <CheckCircle2 className="w-10 h-10 text-[var(--cleared)] mx-auto mb-2" />
                <h4 className="text-sm font-bold text-[var(--text)]">Voice Policy Cleared</h4>
                <p className="text-xs text-[var(--text-muted)] mt-1">Copy aligns with the NovaPay executive voice envelope.</p>
              </div>
            ) : (
              <div className="space-y-3">
                {toneFindings.map((tf, idx) => {
                  const isBlocker = tf.severity === 'BLOCKER';
                  return (
                    <div
                      key={tf.id || idx}
                      className={`p-4 rounded-[var(--radius-card)] border bg-[var(--surface)] space-y-2 ${
                        isBlocker
                          ? 'border-l-4 border-l-[var(--blocker)] border-[var(--border)]'
                          : 'border-l-4 border-l-[var(--warning-text)] border-[var(--border)]'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold font-mono bg-[var(--surface-alt)] text-[var(--text)] border border-[var(--border)]">
                          {tf.rule_citation_code}
                        </span>
                        <Badge variant={isBlocker ? 'blocker' : 'warning'}>
                          {tf.severity}
                        </Badge>
                      </div>

                      <h4 className="text-xs font-bold text-[var(--text)]">{tf.rule_citation_title}</h4>
                      <p className="text-xs text-[var(--text-muted)] leading-relaxed">{tf.explanation}</p>

                      <div className="mt-3 pt-3 border-t border-[var(--border)] flex items-center justify-between gap-2">
                        <span className="text-[11px] text-[var(--primary)] font-semibold line-clamp-1">
                          {tf.suggested_fixes && tf.suggested_fixes.length > 0 ? `✓ ${tf.suggested_fixes[0]}` : tf.rule_citation_title}
                        </span>
                        <div className="flex items-center gap-1.5 shrink-0">
                          {!isAdmin && (
                            <button
                              type="button"
                              onClick={() => {
                                if (onRequestException) {
                                  onRequestException({
                                    submissionId: submissionId || 'DRAFT_024',
                                    draftTitle: draftTitle,
                                    channel: channel,
                                    quoteText: tf.highlighted_text || draftText.slice(0, 40) || "Don't get wrecked by banks!",
                                    ruleCode: tf.rule_citation_code,
                                    ruleTitle: tf.rule_citation_title,
                                    explanation: tf.explanation,
                                  });
                                }
                              }}
                              className="inline-flex items-center px-2 py-1 border border-[var(--border)] hover:bg-[var(--surface-alt)] text-[var(--text)] rounded-[var(--radius-input)] text-xs font-medium transition cursor-pointer"
                            >
                              Request Exception
                            </button>
                          )}
                          {tf.suggested_fixes && tf.suggested_fixes.length > 0 && (
                            <button
                              type="button"
                              onClick={() => handleApplyPatch(tf)}
                              className="inline-flex items-center px-2.5 py-1 bg-[var(--primary)] hover:bg-[var(--primary)]/90 text-white rounded-[var(--radius-input)] text-xs font-semibold transition cursor-pointer"
                            >
                              Apply
                            </button>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ============================================================== */}
      {/* DIFF PREVIEW MODAL DIALOG                                      */}
      {/* ============================================================== */}
      {diffPreviewFinding && (
        <Dialog
          isOpen={Boolean(diffPreviewFinding)}
          onClose={() => setDiffPreviewFinding(null)}
          title={`Patch Preview · ${diffPreviewFinding.rule_citation_code}`}
          description={diffPreviewFinding.rule_citation_title}
        >
          <div className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs font-mono">
              <div className="p-3 rounded-lg bg-[var(--blocker)]/10 border border-[var(--blocker)]/30">
                <div className="font-bold text-[var(--blocker)] mb-1 uppercase text-[10px]">Before (Off-brand)</div>
                <div className="line-through text-[var(--blocker)]">
                  {diffPreviewFinding.source_excerpt || 'Original violation span'}
                </div>
              </div>
              <div className="p-3 rounded-lg bg-[var(--cleared)]/10 border border-[var(--cleared)]/30">
                <div className="font-bold text-[var(--cleared)] mb-1 uppercase text-[10px]">After (Brand-cleared)</div>
                <div className="text-[var(--cleared)] font-bold">
                  {diffPreviewFinding.suggested_fixes?.[0] || 'Deterministic replacement'}
                </div>
              </div>
            </div>

            <div className="p-3.5 rounded-lg bg-[var(--surface-alt)] border border-[var(--border)] text-xs text-[var(--text)]">
              <div className="font-bold text-[var(--text-muted)] text-[10px] uppercase font-mono mb-1.5">
                Rule Explanation &amp; Compliance Citation
              </div>
              <p className="leading-relaxed">{diffPreviewFinding.explanation}</p>
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-[var(--border)]">
              <button
                type="button"
                onClick={() => setDiffPreviewFinding(null)}
                className="px-3 py-1.5 rounded-[var(--radius-input)] border border-[var(--border)] text-xs font-medium text-[var(--text)] hover:bg-[var(--surface-alt)] cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => {
                  const f = diffPreviewFinding;
                  setDiffPreviewFinding(null);
                  handleApplyPatch(f);
                }}
                className="px-3.5 py-1.5 rounded-[var(--radius-input)] bg-[var(--primary)] hover:bg-[var(--primary)]/90 text-white text-xs font-bold shadow-2xs cursor-pointer flex items-center gap-1.5"
              >
                <Sparkles className="w-3.5 h-3.5" />
                <span>Apply Patch</span>
              </button>
            </div>
          </div>
        </Dialog>
      )}

      {/* Realistic Image Corpus Sample Gallery Modal */}
      <SampleGalleryModal
        isOpen={galleryOpen}
        onClose={() => setGalleryOpen(false)}
        onSelectSample={handleSelectCorpusSample}
        apiBase={apiBase}
      />
    </div>
  );
}