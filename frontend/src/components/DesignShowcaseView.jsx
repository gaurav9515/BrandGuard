import React, { useState } from 'react';
import {
  AlertOctagon,
  AlertTriangle,
  CheckCircle2,
  Info,
  Sun,
  Moon,
  Sparkles,
  Search,
  Download,
  RotateCcw,
  Layers,
  Shield,
  Eye,
} from 'lucide-react';
import { useTheme } from '../context/ThemeContext';
import Button from './ui/Button';
import Badge from './ui/Badge';
import Card, { CardHeader, CardContent, CardFooter } from './ui/Card';
import Input from './ui/Input';
import Dialog from './ui/Dialog';
import Toast from './ui/Toast';
import Skeleton from './ui/Skeleton';
import EmptyState from './ui/EmptyState';

export default function DesignShowcaseView() {
  const { isDark, toggleTheme } = useTheme();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [toastMessage, setToastMessage] = useState('');
  const [inputValue, setInputValue] = useState('BrandGuard');

  const triggerToast = () => {
    setToastMessage("Applied deterministic patch: 'NovaPay' replaced 'Novapay'.");
  };

  const tokens = [
    { name: '--bg', role: 'Page background (mist / night forest)', light: '#F4F7F2', dark: '#0E1A14' },
    { name: '--surface', role: 'Primary card & container surface', light: '#FFFFFF', dark: '#15251C' },
    { name: '--surface-alt', role: 'Secondary / moss tint shelf', light: '#E8EFE6', dark: '#1C3025' },
    { name: '--border', role: 'Organic border & subtle leaf lines', light: '#D3DED0', dark: '#2A4234' },
    { name: '--text', role: 'Main text (WCAG AAA)', light: '#14261C', dark: '#E6EFE8' },
    { name: '--text-muted', role: 'Subtitles & secondary copy (WCAG AA)', light: '#4F6558', dark: '#9BB3A5' },
    { name: '--primary', role: 'Forest canopy green (action buttons)', light: '#1F5A3A', dark: '#5FBF86' },
    { name: '--accent', role: 'Moss green accent', light: '#6B8F4E', dark: '#9BBF7A' },
    { name: '--bark', role: 'Neutral secondary woodland accent', light: '#6B5B45', dark: '#8C7B65' },
    { name: '--blocker', role: 'Hard compliance blocker (paired with icon)', light: '#B3261E', dark: '#FF8A80' },
    { name: '--warning-text', role: 'Advisory warning (dark amber AA)', light: '#8A5A00', dark: '#F2C46D' },
    { name: '--cleared', role: 'Cleared check emerald (paired with icon)', light: '#2E9E5B', dark: '#6FD39A' },
    { name: '--info', role: 'Informational notice', light: '#2B6CB0', dark: '#7DB6F0' },
  ];

  return (
    <div className="max-w-6xl mx-auto px-6 py-10 space-y-12">
      {/* Toast Demo */}
      <Toast
        message={toastMessage}
        onUndo={() => {
          setToastMessage('');
          alert('Patch reverted via undo history.');
        }}
        onDismiss={() => setToastMessage('')}
      />

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-[var(--border)]">
        <div>
          <div className="flex items-center gap-2 text-xs font-mono font-bold text-[var(--accent)] uppercase tracking-wider mb-1">
            <span>DESIGN SYSTEM</span>
            <span>·</span>
            <span>FOREST THEME SPECIFICATION</span>
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-[var(--text)] font-serif">
            Forest Design Tokens &amp; Components
          </h1>
          <p className="text-xs text-[var(--text-muted)] mt-1 max-w-xl leading-relaxed">
            Living showcase for BrandGuard’s calm, natural forest design system: design tokens, WCAG AA contrast compliance, accessible badge states, and actionable Apply interactions.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            size="sm"
            onClick={toggleTheme}
            icon={isDark ? Sun : Moon}
          >
            {isDark ? 'Switch to Light Mist' : 'Switch to Night Forest'}
          </Button>
          <Button variant="primary" size="sm" onClick={triggerToast} icon={RotateCcw}>
            Test 10s Undo Toast
          </Button>
        </div>
      </div>

      {/* Section 1: Color Tokens Table */}
      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold text-[var(--text)] font-serif flex items-center gap-2">
            <Layers className="w-4 h-4 text-[var(--primary)]" />
            <span>Design Tokens (CSS Variables)</span>
          </h2>
          <span className="text-xs font-mono text-[var(--text-muted)]">WCAG 2.1 AA Compliant</span>
        </div>

        <div className="bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius-card)] overflow-hidden shadow-2xs">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-[var(--surface-alt)]/60 text-[var(--text-muted)] font-semibold uppercase text-[11px] border-b border-[var(--border)]">
                <tr>
                  <th className="px-5 py-3">TOKEN NAME</th>
                  <th className="px-5 py-3">LIGHT PREVIEW</th>
                  <th className="px-5 py-3">DARK PREVIEW</th>
                  <th className="px-5 py-3">USAGE &amp; PURPOSE</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border)]/70 text-[var(--text)]">
                {tokens.map((tok) => (
                  <tr key={tok.name} className="hover:bg-[var(--surface-alt)]/30 transition-colors">
                    <td className="px-5 py-3.5 font-mono font-bold text-[var(--primary)]">
                      {tok.name}
                    </td>
                    <td className="px-5 py-3.5">
                      <div className="flex items-center gap-2">
                        <span
                          className="w-5 h-5 rounded-md border border-black/10 shrink-0 shadow-2xs"
                          style={{ backgroundColor: tok.light }}
                        />
                        <span className="font-mono text-[11px]">{tok.light}</span>
                      </div>
                    </td>
                    <td className="px-5 py-3.5">
                      <div className="flex items-center gap-2">
                        <span
                          className="w-5 h-5 rounded-md border border-white/10 shrink-0 shadow-2xs"
                          style={{ backgroundColor: tok.dark }}
                        />
                        <span className="font-mono text-[11px]">{tok.dark}</span>
                      </div>
                    </td>
                    <td className="px-5 py-3.5 text-[var(--text-muted)] text-xs">
                      {tok.role}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* Section 2: Color Language & Status Badges */}
      <section className="space-y-4">
        <h2 className="text-lg font-bold text-[var(--text)] font-serif flex items-center gap-2">
          <Shield className="w-4 h-4 text-[var(--primary)]" />
          <span>Color Language (Icon + Label Guaranteed)</span>
        </h2>
        <p className="text-xs text-[var(--text-muted)]">
          Rule: Never rely on color alone. Every compliance status pairs a distinct semantic hue with a standardized Lucide icon and text label.
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="p-4 bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius-card)] space-y-2">
            <div className="text-xs font-semibold text-[var(--text-muted)]">Blocker Status</div>
            <Badge status="BLOCKER" label="Publication Blocked" />
            <p className="text-[11px] text-[var(--text-muted)] mt-2">
              Crimson hue paired with Octagon icon. Blocks export and publish.
            </p>
          </div>

          <div className="p-4 bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius-card)] space-y-2">
            <div className="text-xs font-semibold text-[var(--text-muted)]">Warning Status</div>
            <Badge status="WARNING" label="Tone Advisory" />
            <p className="text-[11px] text-[var(--text-muted)] mt-2">
              High-contrast amber (#8A5A00) paired with Triangle icon. AA readable.
            </p>
          </div>

          <div className="p-4 bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius-card)] space-y-2">
            <div className="text-xs font-semibold text-[var(--text-muted)]">Cleared Status</div>
            <Badge status="CLEARED" label="Brand Cleared" />
            <p className="text-[11px] text-[var(--text-muted)] mt-2">
              Canopy emerald paired with CheckCircle icon. Ready for handoff.
            </p>
          </div>

          <div className="p-4 bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius-card)] space-y-2">
            <div className="text-xs font-semibold text-[var(--text-muted)]">Information Status</div>
            <Badge status="INFO" label="Verified in Code" />
            <p className="text-[11px] text-[var(--text-muted)] mt-2">
              Spruce blue paired with Info icon. Non-blocking provenance.
            </p>
          </div>
        </div>
      </section>

      {/* Section 3: Base Component Showcase */}
      <section className="space-y-6">
        <h2 className="text-lg font-bold text-[var(--text)] font-serif">
          Component Variants &amp; Interactive States
        </h2>

        {/* Buttons Grid */}
        <div className="bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius-card)] p-6 space-y-4 shadow-2xs">
          <h3 className="text-xs font-bold font-mono uppercase text-[var(--text-muted)]">
            Button Variants (8px radius, visible focus rings)
          </h3>
          <div className="flex items-center gap-3 flex-wrap">
            <Button variant="primary" icon={Sparkles}>Primary Forest</Button>
            <Button variant="secondary">Secondary Moss</Button>
            <Button variant="outline">Outline</Button>
            <Button variant="ghost">Ghost Button</Button>
            <Button variant="danger" icon={AlertOctagon}>Blocker Danger</Button>
            <Button variant="primary" loading>Loading...</Button>
            <Button variant="primary" disabled>Disabled</Button>
          </div>
        </div>

        {/* Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          <Card accent="BLOCKER">
            <CardHeader>
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs font-bold text-[var(--blocker)]">FACT_012</span>
                <Badge status="BLOCKER" size="sm" />
              </div>
              <h4 className="text-xs font-bold text-[var(--text)] mt-1">Blocker Card (Red Accent)</h4>
            </CardHeader>
            <CardContent>
              <p className="text-xs text-[var(--text-muted)]">
                Notice: Left accent bar and border are strictly red. Never a green border on a blocker finding.
              </p>
            </CardContent>
            <CardFooter>
              <Button variant="primary" size="sm">Apply Patch</Button>
            </CardFooter>
          </Card>

          <Card accent="WARNING">
            <CardHeader>
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs font-bold text-[var(--warning-text)]">VOICE_004</span>
                <Badge status="WARNING" size="sm" />
              </div>
              <h4 className="text-xs font-bold text-[var(--text)] mt-1">Warning Card (Amber Accent)</h4>
            </CardHeader>
            <CardContent>
              <p className="text-xs text-[var(--text-muted)]">
                Notice: Left accent bar is dark amber, dark enough for AA text contrast against mist surface.
              </p>
            </CardContent>
            <CardFooter>
              <Button variant="secondary" size="sm">Request Exception</Button>
            </CardFooter>
          </Card>

          <Card accent="CLEARED">
            <CardHeader>
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs font-bold text-[var(--cleared)]">VIS_WCAG_2.1</span>
                <Badge status="CLEARED" size="sm" />
              </div>
              <h4 className="text-xs font-bold text-[var(--text)] mt-1">Cleared Card (Green Accent)</h4>
            </CardHeader>
            <CardContent>
              <p className="text-xs text-[var(--text-muted)]">
                Contrast verification passed 4.5:1 ratio on all visual copy.
              </p>
            </CardContent>
            <CardFooter>
              <span className="text-[11px] font-mono text-[var(--cleared)] font-bold flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>Verified Clean</span>
              </span>
            </CardFooter>
          </Card>
        </div>

        {/* Inputs & Dialog Modal Test */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          <div className="bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius-card)] p-6 space-y-4 shadow-2xs">
            <h3 className="text-xs font-bold font-mono uppercase text-[var(--text-muted)]">
              Input Fields (8px radius)
            </h3>
            <Input
              label="Brand Profile Name"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              helperText="The active brand profile controlling all deterministic rules."
            />
            <Input
              label="Search Code Repository"
              placeholder="e.g. src/payments/constants.py"
              icon={Search}
            />
            <Input
              label="Prohibited Value Example"
              value="Unsubstantiated 100% Return"
              error="Violates regulatory rule LEX_003: Guaranteed returns prohibited."
            />
          </div>

          <div className="bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius-card)] p-6 space-y-4 shadow-2xs flex flex-col justify-between">
            <div>
              <h3 className="text-xs font-bold font-mono uppercase text-[var(--text-muted)] mb-3">
                Modal Dialog &amp; Skeleton Loaders
              </h3>
              <p className="text-xs text-[var(--text-muted)] mb-4">
                Accessible modal dialogues with background blur, escape key handlers, and mist/moss pulsing skeleton loaders.
              </p>
              <Button variant="outline" size="sm" onClick={() => setDialogOpen(true)}>
                Open Confirmation Dialog
              </Button>
            </div>

            <div className="space-y-2 pt-4 border-t border-[var(--border)]">
              <div className="text-[11px] font-mono text-[var(--text-muted)]">Skeleton Loading State:</div>
              <Skeleton variant="text" width="60%" />
              <Skeleton variant="text" />
              <Skeleton variant="rectangular" height="32px" />
            </div>
          </div>
        </div>

        {/* Empty State Component */}
        <div className="space-y-3">
          <h3 className="text-xs font-bold font-mono uppercase text-[var(--text-muted)]">
            Empty State (Low-Opacity Forest Leaf Illustration)
          </h3>
          <EmptyState
            title="All Brand Guidelines Adhered To"
            description="No active violations detected in this review partition. All text claims and visual assets satisfy the active ruleset."
            actionLabel="Run Fresh Pre-Flight Audit"
            onAction={() => alert('Starting audit execution...')}
          />
        </div>
      </section>

      {/* Test Dialog */}
      <Dialog
        isOpen={dialogOpen}
        onClose={() => setDialogOpen(false)}
        title="Apply Proposed Fact Change"
        subtitle="Requires administrative verification and triggers blast radius audit."
      >
        <p className="text-xs text-[var(--text)] leading-relaxed mb-4">
          Approving this proposed change will create a new fact version in the verified Fact Ledger and calculate the blast radius across dependent assets.
        </p>
        <div className="bg-[var(--surface-alt)] p-3 rounded-lg text-xs font-mono mb-4 text-[var(--text)]">
          <div>- Old: 0.5% FX Fee</div>
          <div className="text-[var(--cleared)] font-bold">+ New: 0.8% FX Fee (verified from src/constants.py)</div>
        </div>
        <div className="flex items-center justify-end gap-2 pt-3 border-t border-[var(--border)]">
          <Button variant="ghost" size="sm" onClick={() => setDialogOpen(false)}>
            Cancel
          </Button>
          <Button
            variant="primary"
            size="sm"
            onClick={() => {
              setDialogOpen(false);
              triggerToast();
            }}
          >
            Confirm &amp; Apply
          </Button>
        </div>
      </Dialog>
    </div>
  );
}

