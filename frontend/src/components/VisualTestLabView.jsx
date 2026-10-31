import React, { useState, useEffect } from 'react';
import {
  FlaskConical,
  CheckCircle2,
  AlertOctagon,
  AlertTriangle,
  Info,
  RefreshCw,
  Download,
  FileSpreadsheet,
  FileJson,
  Layers,
  Eye,
  Sliders,
  ShieldCheck,
  Check,
  Search,
  ExternalLink,
  ChevronRight,
  Filter
} from 'lucide-react';

export default function VisualTestLabView({ apiBase = '', onNavigate }) {
  const [loading, setLoading] = useState(true);
  const [runningHarness, setRunningHarness] = useState(false);
  const [reportData, setReportData] = useState(null);
  const [error, setError] = useState(null);
  const [categoryFilter, setCategoryFilter] = useState('ALL');
  const [classificationFilter, setClassificationFilter] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');

  // Fetch initial calibration harness report
  const fetchReport = async () => {
    setLoading(true);
    setError(null);
    try {
      const token = localStorage.getItem('token') || localStorage.getItem('brandguard_token');
      const headers = { 'Content-Type': 'application/json' };
      if (token) headers['Authorization'] = `Bearer ${token}`;

      const res = await fetch(`${apiBase}/api/visual-test-lab/run/`, { headers });
      if (!res.ok) {
        if (res.status === 403) {
          throw new Error('Forbidden: Admin access required for the Visual Identity Test Lab.');
        }
        throw new Error(`Failed to load calibration report (HTTP ${res.status})`);
      }
      const data = await res.json();
      setReportData(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReport();
  }, []);

  const handleRunHarness = async () => {
    setRunningHarness(true);
    setError(null);
    try {
      const token = localStorage.getItem('token') || localStorage.getItem('brandguard_token');
      const headers = { 'Content-Type': 'application/json' };
      if (token) headers['Authorization'] = `Bearer ${token}`;

      const res = await fetch(`${apiBase}/api/visual-test-lab/run/`, {
        method: 'POST',
        headers
      });
      if (!res.ok) {
        throw new Error(`Harness run failed (HTTP ${res.status})`);
      }
      const data = await res.json();
      setReportData(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setRunningHarness(false);
    }
  };

  const handleDownloadReport = (format = 'csv') => {
    const token = localStorage.getItem('token') || localStorage.getItem('brandguard_token');
    const url = `${apiBase}/api/visual-test-lab/report/?format=${format}`;
    window.open(url, '_blank');
  };

  const metrics = reportData?.metrics || {};
  const targets = reportData?.targets || {};
  const cm = reportData?.confusion_matrix || {};
  const ruleBreakdown = reportData?.per_rule_breakdown || [];
  const lowConfQueue = reportData?.low_confidence_detections || [];
  const assets = reportData?.asset_results || [];

  // Filter asset results
  const filteredAssets = assets.filter((asset) => {
    if (categoryFilter !== 'ALL' && asset.category !== categoryFilter) return false;
    if (classificationFilter !== 'ALL') {
      if (classificationFilter === 'TP' && !asset.classification?.startsWith('TP')) return false;
      if (classificationFilter === 'FP' && !asset.classification?.startsWith('FP')) return false;
      if (classificationFilter === 'TN' && !asset.classification?.startsWith('TN')) return false;
      if (classificationFilter === 'FN' && !asset.classification?.startsWith('FN')) return false;
    }
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchName = asset.filename?.toLowerCase().includes(q);
      const matchNotes = asset.notes?.toLowerCase().includes(q);
      if (!matchName && !matchNotes) return false;
    }
    return true;
  });

  const categories = [
    { id: 'ALL', label: 'All Categories' },
    { id: 'CLEAN_COMPLIANT', label: 'Clean Banners' },
    { id: 'SUBTLE_COLOR_VIOLATION', label: 'Subtle Colors' },
    { id: 'SEVERE_COLOR_VIOLATION', label: 'Severe Colors' },
    { id: 'LOW_CONTRAST_FAIL', label: 'Low Contrast' },
    { id: 'CVD_STRESS', label: 'CVD Stress' },
    { id: 'EXTREME_ASPECT_RATIO', label: 'Aspect Ratios' },
    { id: 'COMPRESSION_ROBUSTNESS', label: 'Compression' },
    { id: 'CLEAR_SPACE_VIOLATION', label: 'Clear-Space' },
  ];

  if (loading && !reportData) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[500px] text-center p-8">
        <RefreshCw className="w-8 h-8 text-[var(--primary)] animate-spin mb-4" />
        <h3 className="font-serif text-lg font-semibold text-[var(--text)]">
          Calibrating Visual Identity Engine
        </h3>
        <p className="text-sm text-[var(--text-muted)] max-w-md mt-1">
          Evaluating 42 marketing assets across CIELAB Delta-E, spatial contrast slicing, CVD Daltonization, and optical clear-space models...
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-8 pb-16">
      {/* Top Header Banner */}
      <div className="bg-[var(--surface)] border border-[var(--border)] rounded-xl p-6 sm:p-8 shadow-xs relative overflow-hidden">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 relative z-10">
          <div>
            <div className="flex items-center gap-2.5 mb-2">
              <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-[var(--surface-alt)] text-[var(--primary)] border border-[var(--border)]">
                <FlaskConical className="w-3.5 h-3.5" />
                Phase R3 Accuracy Calibration Lab
              </span>
              <span className="text-xs text-[var(--text-muted)]">
                Evaluated: {reportData?.total_images_evaluated || 42} assets
              </span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-serif font-bold text-[var(--text)] tracking-tight">
              Visual Engine Accuracy & Test Lab
            </h1>
            <p className="text-sm text-[var(--text-muted)] max-w-2xl mt-1.5 leading-relaxed">
              Automated precision/recall calibration harness verifying BrandGuard's deterministic computer-vision linter against the 42-asset realistic marketing corpus.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2.5 shrink-0">
            <button
              onClick={handleRunHarness}
              disabled={runningHarness}
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg bg-[var(--primary)] text-white font-medium text-sm hover:opacity-95 shadow-xs transition-all disabled:opacity-50 cursor-pointer"
            >
              <RefreshCw className={`w-4 h-4 ${runningHarness ? 'animate-spin' : ''}`} />
              {runningHarness ? 'Evaluating Corpus...' : 'Run Calibration Harness'}
            </button>

            <button
              onClick={() => handleDownloadReport('csv')}
              className="inline-flex items-center gap-2 px-3.5 py-2.5 rounded-lg bg-[var(--surface)] text-[var(--text)] border border-[var(--border)] hover:bg-[var(--surface-alt)] font-medium text-sm transition-colors cursor-pointer"
              title="Download detailed CSV report"
            >
              <FileSpreadsheet className="w-4 h-4 text-emerald-600" />
              <span>CSV Report</span>
            </button>

            <button
              onClick={() => handleDownloadReport('json')}
              className="inline-flex items-center gap-2 px-3.5 py-2.5 rounded-lg bg-[var(--surface)] text-[var(--text)] border border-[var(--border)] hover:bg-[var(--surface-alt)] font-medium text-sm transition-colors cursor-pointer"
              title="Download raw JSON report"
            >
              <FileJson className="w-4 h-4 text-blue-600" />
              <span>JSON</span>
            </button>
          </div>
        </div>

        {error && (
          <div className="mt-4 p-4 rounded-lg bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900 text-red-800 dark:text-red-200 text-sm flex items-start gap-2.5">
            <AlertOctagon className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
            <div>
              <div className="font-semibold">Harness Execution Notice</div>
              <div className="text-xs mt-0.5">{error}</div>
            </div>
          </div>
        )}
      </div>

      {/* Target Metrics Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        {/* Blocker Recall Target */}
        <div className={`p-5 rounded-xl border bg-[var(--surface)] shadow-2xs relative overflow-hidden ${
          targets.blocker_recall_met ? 'border-emerald-500/40' : 'border-red-500/40'
        }`}>
          <div className="flex items-center justify-between text-xs text-[var(--text-muted)] font-medium mb-1">
            <span>BLOCKER RECALL</span>
            <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold ${
              targets.blocker_recall_met
                ? 'bg-[var(--cleared-tint,rgba(46,158,91,0.12))] text-[var(--cleared)]'
                : 'bg-red-100 text-red-700'
            }`}>
              {targets.blocker_recall_met ? (
                <>
                  <Check className="w-3 h-3 stroke-[3]" />
                  PASS
                </>
              ) : 'FAIL'}
            </span>
          </div>
          <div className="text-3xl font-bold font-serif text-[var(--text)] tracking-tight">
            {(metrics.blocker_recall * 100).toFixed(1)}%
          </div>
          <div className="text-xs text-[var(--text-muted)] mt-1 flex items-center justify-between">
            <span>Target: ≥ 90.0%</span>
            <span className="font-mono text-[11px] text-[var(--primary)] font-semibold">
              {cm.true_positives || 0} / {(cm.true_positives || 0) + (cm.false_negatives || 0)} caught
            </span>
          </div>
          {/* Progress bar */}
          <div className="w-full bg-[var(--surface-alt)] h-1.5 rounded-full mt-3 overflow-hidden">
            <div
              className="bg-[var(--cleared)] h-full rounded-full transition-all duration-500"
              style={{ width: `${Math.min(100, (metrics.blocker_recall || 0) * 100)}%` }}
            />
          </div>
        </div>

        {/* Clean Banner FPR Target */}
        <div className={`p-5 rounded-xl border bg-[var(--surface)] shadow-2xs relative overflow-hidden ${
          targets.clean_banner_fpr_met ? 'border-emerald-500/40' : 'border-red-500/40'
        }`}>
          <div className="flex items-center justify-between text-xs text-[var(--text-muted)] font-medium mb-1">
            <span>CLEAN BANNER FPR</span>
            <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold ${
              targets.clean_banner_fpr_met
                ? 'bg-[var(--cleared-tint,rgba(46,158,91,0.12))] text-[var(--cleared)]'
                : 'bg-red-100 text-red-700'
            }`}>
              {targets.clean_banner_fpr_met ? (
                <>
                  <Check className="w-3 h-3 stroke-[3]" />
                  PASS
                </>
              ) : 'FAIL'}
            </span>
          </div>
          <div className="text-3xl font-bold font-serif text-[var(--text)] tracking-tight">
            {(metrics.clean_banner_fpr * 100).toFixed(1)}%
          </div>
          <div className="text-xs text-[var(--text-muted)] mt-1 flex items-center justify-between">
            <span>Target: ≤ 5.0%</span>
            <span className="font-mono text-[11px] text-[var(--text-muted)] font-semibold">
              {cm.false_positives || 0} false alarm
            </span>
          </div>
          <div className="w-full bg-[var(--surface-alt)] h-1.5 rounded-full mt-3 overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-500 ${
                targets.clean_banner_fpr_met ? 'bg-[var(--cleared)]' : 'bg-red-500'
              }`}
              style={{ width: `${Math.min(100, Math.max(5, (metrics.clean_banner_fpr || 0) * 100))}%` }}
            />
          </div>
        </div>

        {/* Overall Accuracy */}
        <div className="p-5 rounded-xl border border-[var(--border)] bg-[var(--surface)] shadow-2xs">
          <div className="text-xs text-[var(--text-muted)] font-medium mb-1">
            OVERALL ACCURACY
          </div>
          <div className="text-3xl font-bold font-serif text-[var(--text)] tracking-tight">
            {(metrics.accuracy * 100).toFixed(1)}%
          </div>
          <div className="text-xs text-[var(--text-muted)] mt-1">
            Corpus concordance: {(cm.true_positives || 0) + (cm.true_negatives || 0)} / {reportData?.total_images_evaluated || 42}
          </div>
          <div className="w-full bg-[var(--surface-alt)] h-1.5 rounded-full mt-3 overflow-hidden">
            <div
              className="bg-[var(--primary)] h-full rounded-full transition-all duration-500"
              style={{ width: `${(metrics.accuracy || 0) * 100}%` }}
            />
          </div>
        </div>

        {/* Overall Precision */}
        <div className="p-5 rounded-xl border border-[var(--border)] bg-[var(--surface)] shadow-2xs">
          <div className="text-xs text-[var(--text-muted)] font-medium mb-1">
            PRECISION
          </div>
          <div className="text-3xl font-bold font-serif text-[var(--text)] tracking-tight">
            {(metrics.precision * 100).toFixed(1)}%
          </div>
          <div className="text-xs text-[var(--text-muted)] mt-1">
            TP / (TP + FP) confidence index
          </div>
          <div className="w-full bg-[var(--surface-alt)] h-1.5 rounded-full mt-3 overflow-hidden">
            <div
              className="bg-blue-600 h-full rounded-full transition-all duration-500"
              style={{ width: `${(metrics.precision || 0) * 100}%` }}
            />
          </div>
        </div>

        {/* F1 Score */}
        <div className="p-5 rounded-xl border border-[var(--border)] bg-[var(--surface)] shadow-2xs">
          <div className="text-xs text-[var(--text-muted)] font-medium mb-1">
            HARMONIC F1 SCORE
          </div>
          <div className="text-3xl font-bold font-serif text-[var(--text)] tracking-tight">
            {(metrics.f1_score * 100).toFixed(1)}%
          </div>
          <div className="text-xs text-[var(--text-muted)] mt-1">
            Balanced precision & recall
          </div>
          <div className="w-full bg-[var(--surface-alt)] h-1.5 rounded-full mt-3 overflow-hidden">
            <div
              className="bg-indigo-600 h-full rounded-full transition-all duration-500"
              style={{ width: `${(metrics.f1_score || 0) * 100}%` }}
            />
          </div>
        </div>
      </div>

      {/* Middle Grid: Confusion Matrix & Per-Rule Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* 2x2 Confusion Matrix Visualizer */}
        <div className="lg:col-span-5 bg-[var(--surface)] border border-[var(--border)] rounded-xl p-6 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-base font-semibold text-[var(--text)] flex items-center gap-2">
                <Layers className="w-4 h-4 text-[var(--primary)]" />
                Confusion Matrix
              </h2>
              <span className="text-xs font-mono text-[var(--text-muted)]">
                N = {reportData?.total_images_evaluated || 42}
              </span>
            </div>
            <p className="text-xs text-[var(--text-muted)] mb-5">
              Partitioning deterministic CV detections into True/False classifications against human ground truth.
            </p>

            <div className="grid grid-cols-2 gap-3">
              {/* True Positives */}
              <div className="p-4 rounded-lg bg-[var(--cleared-tint,rgba(46,158,91,0.08))] border border-emerald-500/30 text-left">
                <div className="text-[11px] font-bold text-[var(--cleared)] flex items-center gap-1.5 mb-1">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  TRUE POSITIVES (TP)
                </div>
                <div className="text-2xl font-bold text-[var(--text)] font-serif">
                  {cm.true_positives || 0}
                </div>
                <div className="text-[11px] text-[var(--text-muted)] mt-1">
                  Brand violations accurately flagged
                </div>
              </div>

              {/* False Positives */}
              <div className="p-4 rounded-lg bg-red-50 dark:bg-red-950/30 border border-red-300 dark:border-red-900 text-left">
                <div className="text-[11px] font-bold text-red-600 dark:text-red-400 flex items-center gap-1.5 mb-1">
                  <AlertOctagon className="w-3.5 h-3.5" />
                  FALSE POSITIVES (FP)
                </div>
                <div className="text-2xl font-bold text-[var(--text)] font-serif">
                  {cm.false_positives || 0}
                </div>
                <div className="text-[11px] text-[var(--text-muted)] mt-1">
                  Clean assets with false alarm
                </div>
              </div>

              {/* False Negatives */}
              <div className="p-4 rounded-lg bg-amber-50 dark:bg-amber-950/30 border border-amber-300 dark:border-amber-900 text-left">
                <div className="text-[11px] font-bold text-amber-700 dark:text-amber-400 flex items-center gap-1.5 mb-1">
                  <AlertTriangle className="w-3.5 h-3.5" />
                  FALSE NEGATIVES (FN)
                </div>
                <div className="text-2xl font-bold text-[var(--text)] font-serif">
                  {cm.false_negatives || 0}
                </div>
                <div className="text-[11px] text-[var(--text-muted)] mt-1">
                  Violations slipped undetected
                </div>
              </div>

              {/* True Negatives */}
              <div className="p-4 rounded-lg bg-[var(--surface-alt)] border border-[var(--border)] text-left">
                <div className="text-[11px] font-bold text-[var(--primary)] flex items-center gap-1.5 mb-1">
                  <ShieldCheck className="w-3.5 h-3.5" />
                  TRUE NEGATIVES (TN)
                </div>
                <div className="text-2xl font-bold text-[var(--text)] font-serif">
                  {cm.true_negatives || 0}
                </div>
                <div className="text-[11px] text-[var(--text-muted)] mt-1">
                  Clean banners cleared cleanly
                </div>
              </div>
            </div>
          </div>

          <div className="mt-5 pt-4 border-t border-[var(--border)] text-xs text-[var(--text-muted)] flex items-center justify-between">
            <span>Accuracy Formula: (TP + TN) / Total</span>
            <span className="font-semibold text-[var(--primary)]">
              {(metrics.accuracy * 100).toFixed(1)}% Concordance
            </span>
          </div>
        </div>

        {/* Per-Rule Performance Breakdown Table */}
        <div className="lg:col-span-7 bg-[var(--surface)] border border-[var(--border)] rounded-xl p-6 shadow-xs">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-semibold text-[var(--text)] flex items-center gap-2">
              <Sliders className="w-4 h-4 text-[var(--primary)]" />
              Per-Rule Accuracy & Recall Breakdown
            </h2>
            <span className="text-xs text-[var(--text-muted)]">5 CV Rule Models</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-[var(--border)] text-[var(--text-muted)] font-medium">
                  <th className="py-2.5 px-3">Rule Code & Model</th>
                  <th className="py-2.5 px-2 text-center">TP</th>
                  <th className="py-2.5 px-2 text-center">FP</th>
                  <th className="py-2.5 px-2 text-center">FN</th>
                  <th className="py-2.5 px-2 text-right">Precision</th>
                  <th className="py-2.5 px-2 text-right">Recall</th>
                  <th className="py-2.5 px-3 text-right">F1</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border)]">
                {ruleBreakdown.map((r) => (
                  <tr key={r.rule_code} className="hover:bg-[var(--surface-alt)] transition-colors">
                    <td className="py-3 px-3">
                      <div className="font-mono font-semibold text-[var(--text)]">
                        {r.rule_code}
                      </div>
                      <div className="text-[11px] text-[var(--text-muted)] truncate max-w-[200px]">
                        {r.rule_name}
                      </div>
                    </td>
                    <td className="py-3 px-2 text-center font-mono font-medium text-[var(--cleared)]">
                      {r.tp}
                    </td>
                    <td className="py-3 px-2 text-center font-mono font-medium text-red-600">
                      {r.fp}
                    </td>
                    <td className="py-3 px-2 text-center font-mono font-medium text-amber-600">
                      {r.fn}
                    </td>
                    <td className="py-3 px-2 text-right font-mono font-medium">
                      {(r.precision * 100).toFixed(0)}%
                    </td>
                    <td className="py-3 px-2 text-right font-mono font-bold text-[var(--primary)]">
                      {(r.recall * 100).toFixed(0)}%
                    </td>
                    <td className="py-3 px-3 text-right font-mono font-semibold text-[var(--text)]">
                      {(r.f1_score * 100).toFixed(0)}%
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Low Confidence Human Review Lane Queue */}
      <div className="bg-[var(--surface)] border border-amber-500/30 dark:border-amber-900/60 rounded-xl p-6 shadow-xs">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-amber-100 dark:bg-amber-950/60 text-amber-700 dark:text-amber-400 flex items-center justify-center shrink-0">
              <Eye className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-[var(--text)]">
                Low-Confidence Human Review Lane Queue
              </h2>
              <p className="text-xs text-[var(--text-muted)]">
                Detections with confidence &lt; 0.75 are routed to human review rather than halting authors automatically.
              </p>
            </div>
          </div>
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-amber-100 dark:bg-amber-950/60 text-amber-800 dark:text-amber-300 border border-amber-300 dark:border-amber-800 shrink-0">
            {lowConfQueue.length} Detections In Queue
          </span>
        </div>

        {lowConfQueue.length === 0 ? (
          <div className="p-8 text-center text-xs text-[var(--text-muted)] bg-[var(--surface-alt)] rounded-lg">
            No near-threshold detections currently in the review queue. All engine outputs evaluated with high confidence.
          </div>
        ) : (
          <div className="overflow-x-auto mt-2">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-[var(--border)] text-[var(--text-muted)] font-medium">
                  <th className="py-2.5 px-3">Asset File</th>
                  <th className="py-2.5 px-3">Category</th>
                  <th className="py-2.5 px-3">Triggered Citation</th>
                  <th className="py-2.5 px-2 text-center">Confidence</th>
                  <th className="py-2.5 px-3">Engine Reason</th>
                  <th className="py-2.5 px-3">Observation</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border)]">
                {lowConfQueue.map((item, idx) => (
                  <tr key={idx} className="hover:bg-[var(--surface-alt)] transition-colors">
                    <td className="py-3 px-3 font-mono font-medium text-[var(--text)]">
                      {item.filename}
                    </td>
                    <td className="py-3 px-3">
                      <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-[var(--surface-alt)] text-[var(--text-muted)] border border-[var(--border)]">
                        {item.category}
                      </span>
                    </td>
                    <td className="py-3 px-3">
                      <div className="font-mono text-[var(--primary)] font-semibold">
                        {item.rule_code}
                      </div>
                      <div className="text-[11px] text-[var(--text-muted)]">
                        {item.rule_title}
                      </div>
                    </td>
                    <td className="py-3 px-2 text-center font-mono font-bold text-amber-600">
                      {(item.confidence * 100).toFixed(0)}%
                    </td>
                    <td className="py-3 px-3">
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300">
                        {item.reason}
                      </span>
                    </td>
                    <td className="py-3 px-3 text-[11px] text-[var(--text-muted)] max-w-xs truncate">
                      {item.source_excerpt || 'Near-boundary optical threshold measurement'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* 42-Asset Interactive Corpus Results Explorer */}
      <div className="bg-[var(--surface)] border border-[var(--border)] rounded-xl p-6 shadow-xs">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
          <div>
            <h2 className="text-base font-semibold text-[var(--text)]">
              Evaluation Asset Explorer (42 Corpus Samples)
            </h2>
            <p className="text-xs text-[var(--text-muted)]">
              Inspect ground-truth classifications, bounding boxes, and engine findings for each corpus image.
            </p>
          </div>

          {/* Search bar */}
          <div className="relative w-full md:w-64">
            <Search className="w-4 h-4 text-[var(--text-muted)] absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search assets or notes..."
              className="w-full pl-9 pr-3 py-1.5 text-xs rounded-lg bg-[var(--surface)] border border-[var(--border)] text-[var(--text)] placeholder-[var(--text-muted)] focus:outline-hidden focus:ring-1 focus:ring-[var(--primary)]"
            />
          </div>
        </div>

        {/* Filter Chips */}
        <div className="flex flex-wrap items-center gap-1.5 pb-4 border-b border-[var(--border)] mb-6">
          <span className="text-xs font-medium text-[var(--text-muted)] mr-2 flex items-center gap-1">
            <Filter className="w-3.5 h-3.5" /> Filter:
          </span>
          {categories.map((cat) => (
            <button
              key={cat.id}
              onClick={() => setCategoryFilter(cat.id)}
              className={`px-2.5 py-1 rounded-full text-xs font-medium transition-colors cursor-pointer ${
                categoryFilter === cat.id
                  ? 'bg-[var(--primary)] text-white'
                  : 'bg-[var(--surface-alt)] text-[var(--text-muted)] hover:text-[var(--text)] border border-[var(--border)]'
              }`}
            >
              {cat.label}
            </button>
          ))}

          <div className="h-4 w-px bg-[var(--border)] mx-1" />

          {['ALL', 'TP', 'FP', 'TN', 'FN'].map((cls) => (
            <button
              key={cls}
              onClick={() => setClassificationFilter(cls)}
              className={`px-2 py-0.5 rounded text-xs font-mono font-medium transition-colors cursor-pointer ${
                classificationFilter === cls
                  ? 'bg-[var(--text)] text-[var(--surface)]'
                  : 'bg-[var(--surface)] text-[var(--text-muted)] hover:bg-[var(--surface-alt)] border border-[var(--border)]'
              }`}
            >
              {cls}
            </button>
          ))}
        </div>

        {/* Asset Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredAssets.map((asset) => {
            const isTP = asset.classification?.startsWith('TP');
            const isFP = asset.classification?.startsWith('FP');
            const isTN = asset.classification?.startsWith('TN');
            const isFN = asset.classification?.startsWith('FN');

            return (
              <div
                key={asset.filename}
                className="p-4 rounded-xl border border-[var(--border)] bg-[var(--surface)] hover:border-[var(--primary)] transition-all flex flex-col justify-between shadow-2xs"
              >
                <div>
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <span className="font-mono text-xs font-bold text-[var(--text)] truncate max-w-[200px]" title={asset.filename}>
                      {asset.filename}
                    </span>
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold shrink-0 ${
                        isTP
                          ? 'bg-[var(--cleared-tint,rgba(46,158,91,0.1))] text-[var(--cleared)] border border-emerald-500/30'
                          : isTN
                          ? 'bg-[var(--surface-alt)] text-[var(--primary)] border border-[var(--border)]'
                          : isFP
                          ? 'bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300'
                          : 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300'
                      }`}
                    >
                      {asset.classification || 'UNKNOWN'}
                    </span>
                  </div>

                  <div className="flex items-center gap-1.5 mb-2">
                    <span className="text-[10px] font-medium px-2 py-0.5 rounded bg-[var(--surface-alt)] text-[var(--text-muted)] border border-[var(--border)]">
                      {asset.category}
                    </span>
                    <span className="text-[10px] font-mono text-[var(--text-muted)]">
                      GT: {asset.expected_pass_fail}
                    </span>
                  </div>

                  <p className="text-xs text-[var(--text-muted)] line-clamp-2 mb-3">
                    {asset.notes || 'No notes available.'}
                  </p>
                </div>

                <div className="pt-3 border-t border-[var(--border)] flex items-center justify-between text-xs">
                  <span className="text-[var(--text-muted)] font-mono">
                    Findings: <strong className="text-[var(--text)]">{asset.actual_findings_count}</strong> ({asset.blockers_count} Blocker, {asset.warnings_count} Warn)
                  </span>

                  <button
                    onClick={() => {
                      if (onNavigate) {
                        onNavigate('inspector');
                      }
                    }}
                    className="inline-flex items-center gap-1 text-[var(--primary)] font-semibold hover:underline cursor-pointer"
                  >
                    <span>Inspector</span>
                    <ChevronRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

