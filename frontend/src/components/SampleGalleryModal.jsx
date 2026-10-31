import React, { useState, useEffect } from 'react';
import {
  X,
  Search,
  Filter,
  CheckCircle2,
  AlertOctagon,
  AlertTriangle,
  FileText,
  Image as ImageIcon,
  Layers,
  Sparkles,
  ArrowRight,
  Eye,
  Check,
  RefreshCw
} from 'lucide-react';

export default function SampleGalleryModal({
  isOpen,
  onClose,
  onSelectSample,
  apiBase = ''
}) {
  const [samples, setSamples] = useState([]);
  const [loading, setLoading] = useState(true);
  const [categoryFilter, setCategoryFilter] = useState('ALL');
  const [passFilter, setPassFilter] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [loadingSample, setLoadingSample] = useState(null);

  useEffect(() => {
    if (!isOpen) return;
    const fetchSamples = async () => {
      setLoading(true);
      try {
        const res = await fetch(`${apiBase}/api/samples/`);
        if (res.ok) {
          const data = await res.json();
          setSamples(data.samples || []);
        }
      } catch (err) {
        console.error('Failed to fetch samples catalog:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchSamples();
  }, [isOpen, apiBase]);

  if (!isOpen) return null;

  const categories = [
    { id: 'ALL', label: 'All Samples (42)' },
    { id: 'CLEAN_COMPLIANT', label: 'Clean Banners (10)' },
    { id: 'SUBTLE_COLOR_VIOLATION', label: 'Subtle Colors (5)' },
    { id: 'SEVERE_COLOR_VIOLATION', label: 'Severe Colors (5)' },
    { id: 'LOW_CONTRAST_FAIL', label: 'Low Contrast (5)' },
    { id: 'CVD_STRESS', label: 'CVD Stress (4)' },
    { id: 'EXTREME_ASPECT_RATIO', label: 'Aspect Ratios (5)' },
    { id: 'COMPRESSION_ROBUSTNESS', label: 'Compression (5)' },
    { id: 'CLEAR_SPACE_VIOLATION', label: 'Clear-Space (3)' },
  ];

  const filteredSamples = samples.filter((s) => {
    if (categoryFilter !== 'ALL' && s.category !== categoryFilter) return false;
    if (passFilter === 'PASS' && s.pass_fail !== 'PASS') return false;
    if (passFilter === 'FAIL' && s.pass_fail !== 'FAIL') return false;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchName = s.filename.toLowerCase().includes(q);
      const matchTitle = s.title.toLowerCase().includes(q);
      const matchNotes = s.notes.toLowerCase().includes(q);
      if (!matchName && !matchTitle && !matchNotes) return false;
    }
    return true;
  });

  const handlePickSample = async (sample) => {
    setLoadingSample(sample.filename);
    try {
      // Fetch the sample asset as blob
      const sampleUrl = sample.sample_url.startsWith('http')
        ? sample.sample_url
        : `${apiBase}${sample.sample_url}`;

      const res = await fetch(sampleUrl);
      if (!res.ok) {
        throw new Error(`Failed to download sample file (HTTP ${res.status})`);
      }
      const blob = await res.blob();
      const file = new File([blob], sample.filename, { type: blob.type || 'image/png' });
      onSelectSample(file, sample);
      onClose();
    } catch (err) {
      console.error('Error loading sample into inspector:', err);
      alert(`Could not load sample file: ${err.message}`);
    } finally {
      setLoadingSample(null);
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 bg-black/60 backdrop-blur-xs animate-in fade-in duration-150"
    >
      <div className="bg-[var(--surface)] border border-[var(--border)] rounded-2xl w-full max-w-5xl max-h-[90vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Modal Header */}
        <div className="p-6 border-b border-[var(--border)] flex items-center justify-between gap-4 bg-[var(--surface)] shrink-0">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-[var(--surface-alt)] text-[var(--primary)] border border-[var(--border)]">
                <Sparkles className="w-3.5 h-3.5" />
                Phase R3 Realistic Corpus Gallery
              </span>
              <span className="text-xs text-[var(--text-muted)] font-mono">
                {samples.length} Curated Assets
              </span>
            </div>
            <h2 className="text-xl font-serif font-bold text-[var(--text)] tracking-tight">
              Sample Asset Gallery
            </h2>
            <p className="text-xs text-[var(--text-muted)] mt-0.5">
              Select any pre-calibrated marketing banner to instantly load and audit in the Pre-Flight Inspector.
            </p>
          </div>

          <button
            onClick={onClose}
            className="w-9 h-9 rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] hover:bg-[var(--surface)] text-[var(--text)] flex items-center justify-center transition cursor-pointer"
            title="Close Gallery"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Filter Controls Bar */}
        <div className="p-4 border-b border-[var(--border)] bg-[var(--surface-alt)]/50 shrink-0 space-y-3">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            {/* Search input */}
            <div className="relative w-full sm:w-72">
              <Search className="w-4 h-4 text-[var(--text-muted)] absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search by title, filename, rule..."
                className="w-full pl-9 pr-3 py-1.5 text-xs rounded-lg bg-[var(--surface)] border border-[var(--border)] text-[var(--text)] placeholder-[var(--text-muted)] focus:outline-hidden focus:ring-1 focus:ring-[var(--primary)]"
              />
            </div>

            {/* Pass / Fail quick toggle */}
            <div className="flex items-center gap-1">
              <span className="text-xs text-[var(--text-muted)] mr-1">Expected:</span>
              {['ALL', 'PASS', 'FAIL'].map((p) => (
                <button
                  key={p}
                  onClick={() => setPassFilter(p)}
                  className={`px-2.5 py-1 rounded text-xs font-medium transition cursor-pointer ${
                    passFilter === p
                      ? 'bg-[var(--primary)] text-white'
                      : 'bg-[var(--surface)] text-[var(--text-muted)] border border-[var(--border)] hover:bg-[var(--surface-alt)]'
                  }`}
                >
                  {p === 'PASS' ? 'Pass (Clean)' : p === 'FAIL' ? 'Fail (Violations)' : 'All'}
                </button>
              ))}
            </div>
          </div>

          {/* Category Chips Scroll */}
          <div className="flex items-center gap-1.5 overflow-x-auto pb-1 scrollbar-thin">
            {categories.map((cat) => (
              <button
                key={cat.id}
                onClick={() => setCategoryFilter(cat.id)}
                className={`px-3 py-1 rounded-full text-xs font-medium whitespace-nowrap transition cursor-pointer ${
                  categoryFilter === cat.id
                    ? 'bg-[var(--text)] text-[var(--surface)]'
                    : 'bg-[var(--surface)] text-[var(--text-muted)] border border-[var(--border)] hover:text-[var(--text)]'
                }`}
              >
                {cat.label}
              </button>
            ))}
          </div>
        </div>

        {/* Gallery Grid Viewport */}
        <div className="flex-1 overflow-y-auto p-6">
          {loading ? (
            <div className="flex flex-col items-center justify-center min-h-[300px] text-center">
              <RefreshCw className="w-8 h-8 text-[var(--primary)] animate-spin mb-3" />
              <div className="text-sm font-medium text-[var(--text)]">Loading Sample Corpus...</div>
            </div>
          ) : filteredSamples.length === 0 ? (
            <div className="text-center py-16 text-[var(--text-muted)] text-sm">
              No matching assets found in the corpus for the selected filters.
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
              {filteredSamples.map((sample) => {
                const isPass = sample.pass_fail === 'PASS';
                const isPdf = sample.format === 'PDF';
                const isSvg = sample.format === 'SVG';
                const isSelected = loadingSample === sample.filename;

                return (
                  <div
                    key={sample.filename}
                    className="group rounded-xl border border-[var(--border)] bg-[var(--surface)] hover:border-[var(--primary)] hover:shadow-md transition-all overflow-hidden flex flex-col justify-between"
                  >
                    <div>
                      {/* Image Preview Container */}
                      <div className="aspect-16/10 bg-[var(--surface-alt)] relative overflow-hidden flex items-center justify-center border-b border-[var(--border)]">
                        {isPdf ? (
                          <div className="flex flex-col items-center justify-center text-[var(--text-muted)] p-4 text-center">
                            <FileText className="w-10 h-10 text-red-500 mb-1" />
                            <span className="text-[11px] font-mono font-medium">Multi-Page PDF</span>
                            <span className="text-[10px] text-[var(--text-muted)]">Vector & Text Document</span>
                          </div>
                        ) : (
                          <img
                            src={sample.sample_url.startsWith('http') ? sample.sample_url : `${apiBase}${sample.sample_url}`}
                            alt={sample.title}
                            className="w-full h-full object-cover object-center group-hover:scale-105 transition-transform duration-300"
                            loading="lazy"
                            onError={(e) => {
                              e.currentTarget.style.display = 'none';
                              e.currentTarget.parentElement.innerHTML = `<div class="p-4 text-center text-xs text-[var(--text-muted)] font-mono">${sample.filename}</div>`;
                            }}
                          />
                        )}

                        {/* Top Badges */}
                        <div className="absolute top-2.5 left-2.5 right-2.5 flex items-center justify-between pointer-events-none">
                          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-black/70 text-white backdrop-blur-xs">
                            {sample.format}
                          </span>

                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-bold flex items-center gap-1 shadow-xs ${
                              isPass
                                ? 'bg-emerald-600 text-white'
                                : 'bg-red-600 text-white'
                            }`}
                          >
                            {isPass ? <Check className="w-2.5 h-2.5 stroke-[3]" /> : <AlertOctagon className="w-2.5 h-2.5" />}
                            {isPass ? 'COMPLIANT' : 'VIOLATION'}
                          </span>
                        </div>
                      </div>

                      {/* Content Metadata */}
                      <div className="p-3.5 space-y-2">
                        <div>
                          <div className="font-semibold text-xs text-[var(--text)] truncate" title={sample.title}>
                            {sample.title}
                          </div>
                          <div className="font-mono text-[10px] text-[var(--text-muted)] truncate">
                            {sample.filename}
                          </div>
                        </div>

                        {/* Category & Expected Findings */}
                        <div className="flex flex-wrap items-center gap-1">
                          <span className="text-[9px] font-medium px-1.5 py-0.5 rounded bg-[var(--surface-alt)] text-[var(--text-muted)] border border-[var(--border)]">
                            {sample.category}
                          </span>

                          {sample.expected_findings?.map((ef, idx) => (
                            <span
                              key={idx}
                              className={`text-[9px] font-mono font-semibold px-1.5 py-0.5 rounded ${
                                ef.severity === 'BLOCKER'
                                  ? 'bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300'
                                  : 'bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300'
                              }`}
                            >
                              {ef.rule_code}
                            </span>
                          ))}
                        </div>

                        <p className="text-[11px] text-[var(--text-muted)] line-clamp-2 leading-relaxed">
                          {sample.notes || 'Curated marketing compliance test asset.'}
                        </p>
                      </div>
                    </div>

                    {/* Footer Action Button */}
                    <div className="p-3 pt-0">
                      <button
                        onClick={() => handlePickSample(sample)}
                        disabled={isSelected}
                        className="w-full inline-flex items-center justify-center gap-1.5 py-2 px-3 rounded-lg bg-[var(--primary)] text-white hover:opacity-95 font-medium text-xs transition cursor-pointer disabled:opacity-60"
                      >
                        {isSelected ? (
                          <>
                            <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                            <span>Loading Asset...</span>
                          </>
                        ) : (
                          <>
                            <span>Inspect This Asset</span>
                            <ArrowRight className="w-3.5 h-3.5" />
                          </>
                        )}
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

