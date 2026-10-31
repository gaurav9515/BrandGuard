import React, { useState, useEffect } from 'react';
import {
  Download,
  Flame,
  ShieldAlert,
  ShieldCheck,
  RefreshCw,
  Search,
  Sliders,
  Filter,
  FileText,
  AlertTriangle,
  CheckCircle2,
  Clock,
  User,
  Users,
  ChevronRight,
  Info,
  Calendar,
  Layers,
  Sparkles,
  X,
  TrendingUp,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { API_BASE } from '../config/api';
import SystemHealthCard from './SystemHealthCard';

export default function TelemetryView({
  apiBase = API_BASE,
  onSelectRule,
  onViewAllRules,
}) {
  const { user, token, isAdmin, isWriter } = useAuth();

  // Tab switch for Admin: 'telemetry' | 'fact_ledger'
  const [activeTab, setActiveTab] = useState('telemetry');

  // Filters for Admin Telemetry
  const [windowDays, setWindowDays] = useState(30); // 7 | 30 | 90
  const [selectedChannel, setSelectedChannel] = useState('ALL');
  const [diagnosisFilter, setDiagnosisFilter] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [toastMessage, setToastMessage] = useState('');

  // Admin Telemetry Data
  const [telemetry, setTelemetry] = useState({
    kpis: {
      audit_volume: 0,
      first_pass_rate: 100.0,
      review_time_saved_hours: 0,
      review_time_saved_label: '0 hrs (estimated)',
      total_violations: 0,
      total_approved_overrides: 0,
      min_triggers: 10,
      minutes_per_audit: 5,
      selected_window_days: 30,
    },
    rules: [],
    writers: [],
    trend_sparkline: [],
  });

  // Drill-down Modal State
  const [drillDownRule, setDrillDownRule] = useState(null);

  // Writer Summary Data (Writer UI)
  const [writerSummary, setWriterSummary] = useState({
    writer: null,
    my_top_rules: [],
  });
  const [loadingWriterData, setLoadingWriterData] = useState(false);

  // Fact Ledger State (Admin)
  const [facts, setFacts] = useState([]);
  const [factSummary, setFactSummary] = useState({
    total_facts: 0,
    expiring_soon_count: 0,
    expired_count: 0,
  });

  // Blast radius modal state
  const [blastModalOpen, setBlastModalOpen] = useState(false);
  const [selectedFactForBlast, setSelectedFactForBlast] = useState(null);
  const [blastData, setBlastData] = useState(null);
  const [isBulkAuditing, setIsBulkAuditing] = useState(false);

  const showToast = (msg) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(''), 4000);
  };

  // 1. Fetch Admin Telemetry
  const fetchTelemetry = async () => {
    if (!isAdmin) return;
    setIsRefreshing(true);
    try {
      const chanParam = selectedChannel !== 'ALL' ? `&channel=${selectedChannel}` : '';
      const res = await fetch(`${apiBase}/api/telemetry/?days=${windowDays}${chanParam}`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      if (res.ok) {
        const data = await res.json();
        setTelemetry(data);
      } else if (res.status === 403) {
        showToast('HTTP 403: Admin permissions required for organization telemetry.');
      }
    } catch {
      showToast('Could not reach telemetry server.');
    } finally {
      setIsRefreshing(false);
    }
  };

  // 2. Fetch Writer Summary (Writer UI)
  const fetchWriterSummary = async () => {
    if (!isWriter) return;
    setLoadingWriterData(true);
    try {
      const res = await fetch(`${apiBase}/api/telemetry/writer-summary/`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      if (res.ok) {
        const data = await res.json();
        setWriterSummary(data);
      }
    } catch {
      // Fallback
    } finally {
      setLoadingWriterData(false);
    }
  };

  // 3. Fetch Facts for Fact Ledger Tab
  const fetchFacts = async () => {
    if (!isAdmin) return;
    try {
      const res = await fetch(`${apiBase}/api/facts/`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      if (res.ok) {
        const data = await res.json();
        setFacts(data.facts || []);
        setFactSummary({
          total_facts: data.total_facts || 0,
          expiring_soon_count: data.expiring_soon_count || 0,
          expired_count: data.expired_count || 0,
        });
      }
    } catch {
      // Fallback
    }
  };

  useEffect(() => {
    if (isAdmin) {
      fetchTelemetry();
      fetchFacts();
    } else if (isWriter) {
      fetchWriterSummary();
    }
  }, [apiBase, token, isAdmin, isWriter, windowDays, selectedChannel]);

  // Exports
  const handleExportCSV = () => {
    const chanParam = selectedChannel !== 'ALL' ? `&channel=${selectedChannel}` : '';
    const url = `${apiBase}/api/telemetry/export-csv/?days=${windowDays}${chanParam}`;
    fetch(url, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => res.blob())
      .then((blob) => {
        const a = document.createElement('a');
        a.href = window.URL.createObjectURL(blob);
        a.download = `brandguard_telemetry_${windowDays}d.csv`;
        a.click();
        showToast('Telemetry CSV exported successfully.');
      })
      .catch(() => showToast('Export failed.'));
  };

  const handleExportPDF = () => {
    const chanParam = selectedChannel !== 'ALL' ? `&channel=${selectedChannel}` : '';
    const url = `${apiBase}/api/telemetry/export-pdf/?days=${windowDays}${chanParam}`;
    fetch(url, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => res.blob())
      .then((blob) => {
        const a = document.createElement('a');
        a.href = window.URL.createObjectURL(blob);
        a.download = `brandguard_telemetry_${windowDays}d.pdf`;
        a.click();
        showToast('Executive PDF report generated and downloaded.');
      })
      .catch(() => showToast('PDF Export failed.'));
  };

  // Filter rules by diagnosis & search
  const filteredRules = (telemetry.rules || []).filter((r) => {
    const matchesDiagnosis =
      diagnosisFilter === 'ALL' || r.diagnosis === diagnosisFilter;
    const matchesSearch =
      !searchQuery ||
      r.rule_code.toLowerCase().includes(searchQuery.toLowerCase()) ||
      r.title.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesDiagnosis && matchesSearch;
  });

  // ==============================================================
  // RENDER: WRITER UI (Top 5 Triggered Rules & Training Tips)
  // ==============================================================
  if (isWriter && !isAdmin) {
    return (
      <div className="max-w-6xl mx-auto px-6 py-8">
        {toastMessage && (
          <div className="fixed top-16 right-6 z-50 bg-[#0F5132] text-white px-4 py-3 rounded-xl shadow-xl text-xs font-semibold flex items-center gap-2.5 border border-emerald-400/30">
            <CheckCircle2 className="w-4 h-4 text-emerald-300 shrink-0" />
            <span>{toastMessage}</span>
          </div>
        )}

        {/* Writer Header */}
        <div className="mb-8">
          <div className="flex items-center gap-2 text-xs font-mono font-bold text-emerald-800 dark:text-emerald-400 uppercase tracking-wider mb-2">
            <span>MY GOVERNANCE WORKSPACE</span>
            <span>·</span>
            <span>PERSONAL COMPLIANCE COACH</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold text-zinc-900 dark:text-white tracking-tight">
            My Top Triggered Rules &amp; Coaching Tips
          </h1>
          <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-1 max-w-2xl leading-relaxed">
            Personalized coaching based on rules flagged during your recent pre-flight audits. Adhere to these actionable tips to achieve zero-blocker clearances on your first pass.
          </p>
        </div>

        {/* Top 5 Rules Cards */}
        {loadingWriterData ? (
          <div className="py-16 text-center text-zinc-400 text-xs">
            Loading your compliance coaching data...
          </div>
        ) : (writerSummary.my_top_rules || []).length === 0 ? (
          <div className="bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800/60 rounded-2xl p-8 text-center max-w-lg mx-auto">
            <Sparkles className="w-8 h-8 text-emerald-600 dark:text-emerald-400 mx-auto mb-3" />
            <h3 className="text-sm font-bold text-emerald-900 dark:text-emerald-200">
              Clean Governance Track Record
            </h3>
            <p className="text-xs text-emerald-700 dark:text-emerald-300 mt-1 leading-relaxed">
              You have not triggered any persistent rule violations! All recent draft submissions adhere strictly to brand and fact guidelines.
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {writerSummary.my_top_rules.map((rule, idx) => (
              <div
                key={rule.rule_code}
                className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl p-5 shadow-xs hover:border-zinc-300 dark:hover:border-zinc-700 transition-colors"
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-zinc-100 dark:border-zinc-800">
                  <div className="flex items-center gap-3">
                    <span className="w-6 h-6 rounded-full bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 text-xs font-bold font-mono flex items-center justify-center">
                      #{idx + 1}
                    </span>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-bold text-xs text-zinc-900 dark:text-white">
                          {rule.rule_code}
                        </span>
                        <span
                          className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold uppercase ${
                            rule.severity === 'BLOCKER'
                              ? 'bg-rose-100 dark:bg-rose-950 text-rose-800 dark:text-rose-300 border border-rose-200 dark:border-rose-800'
                              : 'bg-amber-100 dark:bg-amber-950 text-amber-800 dark:text-amber-300 border border-amber-200 dark:border-amber-800'
                          }`}
                        >
                          {rule.severity}
                        </span>
                        <span className="text-[10px] font-mono uppercase bg-zinc-100 dark:bg-zinc-800 text-zinc-500 px-1.5 py-0.5 rounded">
                          {rule.pillar}
                        </span>
                      </div>
                      <h4 className="text-sm font-semibold text-zinc-800 dark:text-zinc-200 mt-0.5">
                        {rule.title}
                      </h4>
                    </div>
                  </div>

                  <div className="text-right">
                    <span className="text-xs text-zinc-400">Triggered:</span>{' '}
                    <span className="font-mono font-bold text-zinc-900 dark:text-white text-sm">
                      {rule.trigger_count} times
                    </span>
                  </div>
                </div>

                {/* Training Tip */}
                <div className="mt-3.5 bg-emerald-50/70 dark:bg-emerald-950/30 border border-emerald-200/80 dark:border-emerald-800/50 rounded-lg p-3.5 flex items-start gap-2.5">
                  <Sparkles className="w-4 h-4 text-emerald-600 dark:text-emerald-400 shrink-0 mt-0.5" />
                  <div className="text-xs text-emerald-900 dark:text-emerald-200 leading-relaxed">
                    <span className="font-bold">Coaching Tip: </span>
                    {rule.training_tip}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }

  // ==============================================================
  // RENDER: ADMIN UI (Full Governance Telemetry & Ambiguity Diagnostic)
  // ==============================================================
  return (
    <div className="max-w-7xl mx-auto px-6 py-8">
      {/* Toast Notification */}
      {toastMessage && (
        <div className="fixed top-16 right-6 z-50 bg-[#0F5132] text-white px-4 py-3 rounded-xl shadow-xl text-xs font-semibold flex items-center gap-2.5 border border-emerald-400/30 animate-fade-in">
          <CheckCircle2 className="w-4 h-4 text-emerald-300 shrink-0" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Top Header & Tab Switcher */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
        <div>
          <div className="flex items-center gap-2 text-[11px] font-mono font-bold text-emerald-800 dark:text-emerald-400 uppercase tracking-wider mb-1">
            <span>GOVERNANCE INTELLIGENCE</span>
            <span>·</span>
            <span>LIVE TELEMETRY &amp; AMBIGUITY DIAGNOSTIC</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold text-zinc-900 dark:text-white tracking-tight">
            Governance Velocity &amp; Policy Health
          </h1>
          <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-1 max-w-2xl leading-relaxed">
            Real-time telemetry computed dynamically from verified audit events within the selected window. Diagnose guideline ambiguity, friction scores, and creator adherence.
          </p>
        </div>

        {/* Global Action Buttons */}
        <div className="flex items-center gap-2.5 flex-wrap">
          <button
            type="button"
            onClick={fetchTelemetry}
            disabled={isRefreshing}
            className="border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 text-zinc-700 dark:text-zinc-300 text-xs px-3.5 py-2 rounded-lg flex items-center gap-1.5 hover:bg-zinc-50 dark:hover:bg-zinc-800 font-semibold shadow-2xs cursor-pointer transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-zinc-500 ${isRefreshing ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>

          <button
            type="button"
            onClick={handleExportCSV}
            className="border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 text-zinc-700 dark:text-zinc-300 text-xs px-3.5 py-2 rounded-lg flex items-center gap-1.5 hover:bg-zinc-50 dark:hover:bg-zinc-800 font-semibold shadow-2xs cursor-pointer transition-colors"
          >
            <Download className="w-3.5 h-3.5 text-zinc-500" />
            <span>Export CSV</span>
          </button>

          <button
            type="button"
            onClick={handleExportPDF}
            className="bg-zinc-900 dark:bg-zinc-100 hover:bg-zinc-800 dark:hover:bg-white text-white dark:text-zinc-900 text-xs px-4 py-2 rounded-lg flex items-center gap-1.5 font-semibold transition-colors shadow-xs cursor-pointer"
          >
            <FileText className="w-3.5 h-3.5" />
            <span>Export Executive PDF</span>
          </button>
        </div>
      </div>

      {/* Filter Bar: Window & Channel */}
      <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl p-4 mb-6 shadow-2xs flex flex-col md:flex-row md:items-center justify-between gap-4">
        {/* Time Window Buttons: 7 / 30 / 90 days */}
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-zinc-500 flex items-center gap-1.5">
            <Clock className="w-3.5 h-3.5" />
            <span>Window:</span>
          </span>
          <div className="flex items-center gap-1 bg-zinc-100 dark:bg-zinc-800 p-1 rounded-lg">
            {[7, 30, 90].map((d) => (
              <button
                key={d}
                type="button"
                onClick={() => setWindowDays(d)}
                className={`text-xs px-3 py-1 rounded-md font-semibold transition-colors cursor-pointer ${
                  windowDays === d
                    ? 'bg-white dark:bg-zinc-900 text-zinc-900 dark:text-white shadow-2xs'
                    : 'text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-200'
                }`}
              >
                {d} Days
              </button>
            ))}
          </div>
        </div>

        {/* Channel Filter */}
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-zinc-500 flex items-center gap-1.5">
            <Filter className="w-3.5 h-3.5" />
            <span>Channel:</span>
          </span>
          <select
            value={selectedChannel}
            onChange={(e) => setSelectedChannel(e.target.value)}
            className="bg-zinc-50 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 text-xs font-semibold rounded-lg px-3 py-1.5 text-zinc-800 dark:text-zinc-200 focus:outline-hidden"
          >
            <option value="ALL">All Channels</option>
            <option value="LINKEDIN_POST">LinkedIn Post</option>
            <option value="PRESS_RELEASE">Press Release</option>
            <option value="PITCH_DECK">Pitch Deck</option>
            <option value="LANDING_PAGE">Landing Page</option>
          </select>
        </div>
      </div>

      {/* KPI Cards (4 Cards) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {/* Card 1: Audit volume */}
        <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl p-5 shadow-2xs">
          <div className="text-xs font-semibold text-zinc-500 mb-1">Audit Volume</div>
          <div className="text-3xl font-bold text-zinc-900 dark:text-white tracking-tight">
            {(telemetry.kpis?.audit_volume || 0).toLocaleString()}
          </div>
          <div className="text-[11px] text-zinc-400 mt-1">
            Distinct submissions scanned in {windowDays}d window
          </div>
        </div>

        {/* Card 2: First-pass rate */}
        <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl p-5 shadow-2xs">
          <div className="text-xs font-semibold text-zinc-500 mb-1">First-Pass Rate</div>
          <div className="text-3xl font-bold text-zinc-900 dark:text-white tracking-tight">
            {(telemetry.kpis?.first_pass_rate || 100.0).toFixed(1)}%
          </div>
          <div className="text-[11px] text-emerald-600 dark:text-emerald-400 font-medium mt-1">
            Version 1 clean with 0 open blockers
          </div>
        </div>

        {/* Card 3: Review time saved */}
        <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl p-5 shadow-2xs">
          <div className="text-xs font-semibold text-zinc-500 mb-1 flex items-center justify-between">
            <span>Review Time Saved</span>
            <span className="text-[10px] font-mono text-zinc-400 font-bold bg-zinc-100 dark:bg-zinc-800 px-1.5 py-0.5 rounded">
              estimated
            </span>
          </div>
          <div className="text-3xl font-bold text-zinc-900 dark:text-white tracking-tight">
            {telemetry.kpis?.review_time_saved_hours || 0} hrs
          </div>
          <div className="text-[11px] text-zinc-400 mt-1">
            Based on admin setting: {telemetry.kpis?.minutes_per_audit || 5} min/audit
          </div>
        </div>

        {/* Card 4: Violations & Overrides */}
        <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl p-5 shadow-2xs">
          <div className="text-xs font-semibold text-zinc-500 mb-1">Total Rule Violations</div>
          <div className="text-3xl font-bold text-zinc-900 dark:text-white tracking-tight">
            {telemetry.kpis?.total_violations || 0}
          </div>
          <div className="text-[11px] text-zinc-400 mt-1">
            {telemetry.kpis?.total_approved_overrides || 0} exceptions approved
          </div>
        </div>
      </div>

      {/* Rule Performance & Ambiguity Diagnostic Table */}
      <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl overflow-hidden shadow-2xs mb-8">
        {/* Table Controls Header */}
        <div className="p-5 border-b border-zinc-200 dark:border-zinc-800 flex flex-col md:flex-row md:items-center justify-between gap-4 bg-zinc-50/50 dark:bg-zinc-800/30">
          <div>
            <h2 className="text-sm font-bold text-zinc-900 dark:text-white flex items-center gap-2">
              <Flame className="w-4 h-4 text-amber-500" />
              <span>Ambiguity Diagnostic &amp; Friction Leaderboard</span>
            </h2>
            <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-0.5">
              Diagnosis requires ≥ {telemetry.kpis?.min_triggers || 10} triggers. Friction = override_rate × ln(triggers + 1).
            </p>
          </div>

          {/* Diagnosis Filter & Search */}
          <div className="flex items-center gap-3 flex-wrap">
            <div className="flex items-center gap-1 bg-white dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 rounded-lg p-1 text-xs">
              {[
                { id: 'ALL', label: 'All' },
                { id: 'NEEDS_CLARIFICATION', label: 'Clarification' },
                { id: 'TRAINING_GAP', label: 'Training Gap' },
                { id: 'HEALTHY_GOVERNANCE', label: 'Healthy' },
                { id: 'NOT_ENOUGH_DATA', label: '< 10 Data' },
              ].map((diag) => (
                <button
                  key={diag.id}
                  type="button"
                  onClick={() => setDiagnosisFilter(diag.id)}
                  className={`px-2.5 py-1 rounded font-semibold transition-colors cursor-pointer text-[11px] ${
                    diagnosisFilter === diag.id
                      ? 'bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900'
                      : 'text-zinc-500 hover:text-zinc-900 dark:hover:text-white'
                  }`}
                >
                  {diag.label}
                </button>
              ))}
            </div>

            <div className="relative">
              <Search className="w-3.5 h-3.5 text-zinc-400 absolute left-2.5 top-2.5" />
              <input
                type="text"
                placeholder="Search rule..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-8 pr-3 py-1.5 text-xs bg-white dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 rounded-lg text-zinc-800 dark:text-zinc-200 placeholder-zinc-400 focus:outline-hidden"
              />
            </div>
          </div>
        </div>

        {/* Table Content */}
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-zinc-50 dark:bg-zinc-800/60 text-zinc-500 font-semibold uppercase tracking-wider text-[11px] border-b border-zinc-200 dark:border-zinc-800">
              <tr>
                <th scope="col" className="px-5 py-3.5">RULE CODE</th>
                <th scope="col" className="px-5 py-3.5">TITLE &amp; PILLAR</th>
                <th scope="col" className="px-5 py-3.5">SEVERITY</th>
                <th scope="col" className="px-5 py-3.5">TRIGGERS</th>
                <th scope="col" className="px-5 py-3.5">OVERRIDES</th>
                <th scope="col" className="px-5 py-3.5">OVERRIDE %</th>
                <th scope="col" className="px-5 py-3.5">FRICTION</th>
                <th scope="col" className="px-5 py-3.5">DIAGNOSIS</th>
                <th scope="col" className="px-5 py-3.5">LAST TRIGGERED</th>
                <th scope="col" className="px-5 py-3.5">ACTION</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-200 dark:divide-zinc-800 text-zinc-800 dark:text-zinc-200">
              {filteredRules.length === 0 ? (
                <tr>
                  <td colSpan={10} className="px-6 py-12 text-center text-zinc-400 text-xs">
                    No rules matching current filter criteria.
                  </td>
                </tr>
              ) : (
                filteredRules.map((row) => (
                  <tr
                    key={row.id || row.rule_code}
                    className="hover:bg-zinc-50/70 dark:hover:bg-zinc-800/40 transition-colors"
                  >
                    <td className="px-5 py-4 font-mono font-bold text-zinc-900 dark:text-white">
                      {row.rule_code}
                    </td>
                    <td className="px-5 py-4">
                      <div className="font-semibold text-zinc-900 dark:text-zinc-100">{row.title}</div>
                      <span className="text-[10px] font-mono uppercase text-zinc-500 bg-zinc-100 dark:bg-zinc-800 px-1.5 py-0.5 rounded mt-0.5 inline-block">
                        {row.pillar}
                      </span>
                    </td>
                    <td className="px-5 py-4">
                      <span
                        className={`font-mono text-[10px] px-2 py-0.5 rounded font-bold uppercase ${
                          row.severity === 'BLOCKER'
                            ? 'bg-rose-100 dark:bg-rose-950 text-rose-800 dark:text-rose-300 border border-rose-200 dark:border-rose-800'
                            : 'bg-amber-100 dark:bg-amber-950 text-amber-800 dark:text-amber-300 border border-amber-200 dark:border-amber-800'
                        }`}
                      >
                        {row.severity}
                      </span>
                    </td>
                    <td className="px-5 py-4 font-mono font-bold text-zinc-900 dark:text-white">
                      {row.triggers}
                    </td>
                    <td className="px-5 py-4 font-mono text-zinc-600 dark:text-zinc-400">
                      {row.overrides}
                    </td>
                    <td className="px-5 py-4 font-mono font-semibold">
                      {row.override_rate_pct}%
                    </td>
                    <td className="px-5 py-4 font-mono font-extrabold text-zinc-900 dark:text-white">
                      {row.friction_score}
                    </td>
                    <td className="px-5 py-4">
                      <span
                        className={`text-[10px] font-mono font-bold px-2.5 py-1 rounded-full uppercase border ${
                          row.diagnosis === 'NEEDS_CLARIFICATION'
                            ? 'bg-purple-50 dark:bg-purple-950 text-purple-700 dark:text-purple-300 border-purple-200 dark:border-purple-800'
                            : row.diagnosis === 'TRAINING_GAP'
                            ? 'bg-amber-50 dark:bg-amber-950 text-amber-700 dark:text-amber-300 border-amber-200 dark:border-amber-800'
                            : row.diagnosis === 'HEALTHY_GOVERNANCE'
                            ? 'bg-emerald-50 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300 border-emerald-200 dark:border-emerald-800'
                            : 'bg-zinc-100 dark:bg-zinc-800 text-zinc-500 border-zinc-200 dark:border-zinc-700'
                        }`}
                      >
                        {row.diagnosis_label}
                      </span>
                    </td>
                    <td className="px-5 py-4 font-mono text-[11px] text-zinc-500 dark:text-zinc-400">
                      {row.last_triggered_display || 'Never'}
                    </td>
                    <td className="px-5 py-4">
                      <button
                        type="button"
                        onClick={() => setDrillDownRule(row)}
                        className="text-emerald-700 dark:text-emerald-400 font-semibold hover:underline flex items-center gap-1 cursor-pointer"
                      >
                        <span>Drill-down</span>
                        <ChevronRight className="w-3.5 h-3.5" />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Bottom Grid: Per-Writer Breakdown & Trend Sparkline */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Trend Sparkline */}
        <div className="lg:col-span-7 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl p-6 shadow-2xs">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-bold text-zinc-900 dark:text-white flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-emerald-600" />
                <span>Audit Volume &amp; Violations Trend</span>
              </h3>
              <p className="text-xs text-zinc-500 mt-0.5">
                Dynamic daily activity computed from AuditEvent records in {windowDays}d window.
              </p>
            </div>
            <div className="flex items-center gap-3 text-xs text-zinc-600 dark:text-zinc-400">
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-xs bg-[#0F5132] inline-block"></span>
                <span>Audits</span>
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-xs bg-amber-500 inline-block"></span>
                <span>Violations</span>
              </span>
            </div>
          </div>

          <div className="h-40 flex items-end justify-between gap-1.5 pt-4 border-b border-zinc-100 dark:border-zinc-800 overflow-x-auto">
            {(telemetry.trend_sparkline || []).slice(-15).map((point, idx) => {
              const maxVal = Math.max(
                ...telemetry.trend_sparkline.map((p) => Math.max(p.audits, p.violations)),
                10
              );
              const auditH = `${Math.min(100, Math.round((point.audits / maxVal) * 100))}%`;
              const violH = `${Math.min(100, Math.round((point.violations / maxVal) * 100))}%`;

              return (
                <div key={idx} className="flex-1 min-w-[20px] flex flex-col items-center gap-1">
                  <div className="w-full flex items-end justify-center gap-0.5 h-28">
                    <div
                      style={{ height: auditH }}
                      className="w-2 bg-[#0F5132] rounded-t-xs transition-all"
                      title={`${point.date}: ${point.audits} Audits`}
                    />
                    <div
                      style={{ height: violH }}
                      className="w-2 bg-amber-500 rounded-t-xs transition-all"
                      title={`${point.date}: ${point.violations} Violations`}
                    />
                  </div>
                  <span className="text-[9px] font-mono text-zinc-400 truncate">
                    {point.date}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Per-Writer Breakdown */}
        <div className="lg:col-span-5 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl p-6 shadow-2xs">
          <h3 className="text-sm font-bold text-zinc-900 dark:text-white flex items-center gap-2 mb-1">
            <Users className="w-4 h-4 text-emerald-600" />
            <span>Per-Writer Compliance Adherence</span>
          </h3>
          <p className="text-xs text-zinc-500 mb-4">
            Total rule violations attributed in window.
          </p>

          <div className="space-y-3">
            {(telemetry.writers || []).length === 0 ? (
              <div className="text-center py-8 text-zinc-400 text-xs">
                No writer activity recorded in this window.
              </div>
            ) : (
              (telemetry.writers || []).map((w) => (
                <div
                  key={w.user_id}
                  className="flex items-center justify-between p-3 rounded-lg border border-zinc-100 dark:border-zinc-800 bg-zinc-50/50 dark:bg-zinc-800/30 text-xs"
                >
                  <div className="flex items-center gap-2.5">
                    <div className="w-7 h-7 rounded-full bg-emerald-100 dark:bg-emerald-950 text-emerald-800 dark:text-emerald-300 font-bold flex items-center justify-center font-mono">
                      {w.name ? w.name[0].toUpperCase() : 'U'}
                    </div>
                    <div>
                      <div className="font-semibold text-zinc-900 dark:text-white">
                        {w.name}
                      </div>
                      <div className="text-[10px] text-zinc-400 font-mono">@{w.username}</div>
                    </div>
                  </div>
                  <div className="text-right">
                    <span className="font-mono font-bold text-zinc-900 dark:text-white">
                      {w.violations_count}
                    </span>
                    <span className="text-zinc-400 text-[11px]"> violations</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Admin System Infrastructure & Production Health Card (Phase R4) */}
      <SystemHealthCard apiBase={apiBase} className="mt-8" />

      {/* ============================================================== */}
      {/* DRILL-DOWN MODAL                                               */}
      {/* ============================================================== */}
      {drillDownRule && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl max-w-xl w-full p-6 shadow-2xl animate-fade-in">
            <div className="flex items-start justify-between pb-4 border-b border-zinc-100 dark:border-zinc-800">
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-mono font-bold text-zinc-900 dark:text-white text-base">
                    {drillDownRule.rule_code}
                  </span>
                  <span
                    className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold uppercase ${
                      drillDownRule.severity === 'BLOCKER'
                        ? 'bg-rose-100 text-rose-800 border border-rose-200'
                        : 'bg-amber-100 text-amber-800 border border-amber-200'
                    }`}
                  >
                    {drillDownRule.severity}
                  </span>
                  <span className="text-[10px] font-mono uppercase bg-zinc-100 dark:bg-zinc-800 px-2 py-0.5 rounded text-zinc-500">
                    {drillDownRule.pillar}
                  </span>
                </div>
                <h3 className="text-sm font-bold text-zinc-800 dark:text-zinc-200 mt-1">
                  {drillDownRule.title}
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setDrillDownRule(null)}
                className="text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200 cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Drill-down Diagnostics & Math */}
            <div className="py-4 space-y-4 text-xs">
              <div className="bg-zinc-50 dark:bg-zinc-800/40 p-3.5 rounded-xl border border-zinc-200 dark:border-zinc-700">
                <div className="font-bold text-zinc-700 dark:text-zinc-300 mb-2">
                  Diagnostic Rationale:
                </div>
                <div className="flex items-center gap-2 mb-2">
                  <span
                    className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded uppercase border ${
                      drillDownRule.diagnosis === 'NEEDS_CLARIFICATION'
                        ? 'bg-purple-50 text-purple-700 border-purple-200'
                        : drillDownRule.diagnosis === 'TRAINING_GAP'
                        ? 'bg-amber-50 text-amber-700 border-amber-200'
                        : drillDownRule.diagnosis === 'HEALTHY_GOVERNANCE'
                        ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                        : 'bg-zinc-100 text-zinc-500 border-zinc-200'
                    }`}
                  >
                    {drillDownRule.diagnosis_label}
                  </span>
                  <span className="text-zinc-500">
                    ({drillDownRule.triggers} triggers, {drillDownRule.overrides} overrides)
                  </span>
                </div>
                <p className="text-zinc-600 dark:text-zinc-300 leading-relaxed">
                  {drillDownRule.hint}
                </p>
              </div>

              {/* Mathematical Formula Breakdown */}
              <div className="space-y-1 font-mono text-[11px] bg-zinc-900 text-zinc-100 p-3.5 rounded-xl">
                <div className="text-zinc-400 font-bold mb-1">// Mathematical Computation:</div>
                <div>override_rate = {drillDownRule.overrides} / {drillDownRule.triggers} = {drillDownRule.override_rate_pct}%</div>
                <div>friction_score = override_rate × ln(triggers + 1) = {drillDownRule.friction_score}</div>
                <div>last_triggered = {drillDownRule.last_triggered_display || 'Never'}</div>
              </div>
            </div>

            <div className="pt-3 border-t border-zinc-100 dark:border-zinc-800 flex justify-end">
              <button
                type="button"
                onClick={() => setDrillDownRule(null)}
                className="bg-zinc-900 text-white text-xs px-4 py-2 rounded-lg font-semibold hover:bg-zinc-800 cursor-pointer"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
