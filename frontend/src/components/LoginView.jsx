import React, { useState, useEffect } from 'react';
import {
  Shield,
  Lock,
  Mail,
  User,
  ArrowRight,
  AlertCircle,
  CheckCircle2,
  Building,
  KeyRound,
  FileCheck,
  Check,
  Clock,
  Sparkles,
  RefreshCw,
  Sun,
  Moon,
  ChevronLeft,
  ShieldCheck,
  ExternalLink,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import PasswordStrengthMeter from './ui/PasswordStrengthMeter';
import ServerHealthPill from './ServerHealthPill';
import { API_BASE } from '../config/api';

export default function LoginView({ onLoginSuccess }) {
  const {
    login,
    loading,
    authError,
    registerAdmin,
    registerWriter,
    verifyEmail,
    requestPasswordReset,
    confirmPasswordReset,
  } = useAuth();
  const { isDark, toggleTheme } = useTheme();

  // Mode: 'writer_login' | 'admin_login' | 'admin_register' | 'writer_register' | 'verify_email' | 'reset_request' | 'reset_confirm' | 'waiting_approval'
  const [authMode, setAuthMode] = useState(() => {
    const path = window.location.pathname.toLowerCase();
    if (path.includes('/admin/login')) return 'admin_login';
    if (path.includes('/register/admin')) return 'admin_register';
    if (path.includes('/register/writer')) return 'writer_register';
    if (path.includes('/verify-email')) return 'verify_email';
    if (path.includes('/reset-password')) return 'reset_request';
    return 'writer_login';
  });

  // Form states
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [orgName, setOrgName] = useState('');
  const [inviteCode, setInviteCode] = useState(() => {
    const params = new URLSearchParams(window.location.search);
    return params.get('invite') || '';
  });
  const [verificationToken, setVerificationToken] = useState(() => {
    const params = new URLSearchParams(window.location.search);
    return params.get('token') || '';
  });
  const [resetToken, setResetToken] = useState(() => {
    const params = new URLSearchParams(window.location.search);
    return params.get('token') || '';
  });
  const [termsAccepted, setTermsAccepted] = useState(false);

  // Status & Feedback
  const [localError, setLocalError] = useState(null);
  const [localSuccess, setLocalSuccess] = useState(null);
  const [isTurnstileVerified, setIsTurnstileVerified] = useState(true);
  const [inviteOrgInfo, setInviteOrgInfo] = useState(null);
  const [validatingInvite, setValidatingInvite] = useState(false);
  const [pendingApprovalInfo, setPendingApprovalInfo] = useState(null);

  // Validate invite code on entry into writer registration
  useEffect(() => {
    if (authMode === 'writer_register' && inviteCode.trim()) {
      setValidatingInvite(true);
      fetch(`${API_BASE}/api/invites/validate/?code=${encodeURIComponent(inviteCode.trim())}`)
        .then((res) => res.json())
        .then((data) => {
          if (data.valid) {
            setInviteOrgInfo(data);
            setLocalError(null);
          } else {
            setInviteOrgInfo(null);
            setLocalError(data.error || 'Invalid or expired invite code.');
          }
        })
        .catch(() => {
          setInviteOrgInfo(null);
        })
        .finally(() => setValidatingInvite(false));
    }
  }, [authMode, inviteCode]);

  // Handle Writer / Admin Login
  const handleLoginSubmit = async (e) => {
    e.preventDefault();
    setLocalError(null);
    setLocalSuccess(null);

    const portal = authMode === 'admin_login' ? 'ADMIN' : 'WRITER';

    try {
      const loggedInUser = await login(username, password, portal);
      if (onLoginSuccess) {
        onLoginSuccess(loggedInUser);
      }
    } catch (err) {
      if (err.data?.needs_approval) {
        setPendingApprovalInfo({ username, email: username });
        setAuthMode('waiting_approval');
        return;
      }
      if (err.data?.needs_email_verification) {
        setLocalError('Please verify your email address before logging in.');
        setAuthMode('verify_email');
        return;
      }
      setLocalError(err.message || 'Login failed. Please verify credentials.');
    }
  };

  // Handle Admin Registration
  const handleAdminRegisterSubmit = async (e) => {
    e.preventDefault();
    setLocalError(null);
    setLocalSuccess(null);

    if (password !== confirmPassword) {
      setLocalError('Passwords do not match.');
      return;
    }
    if (!termsAccepted) {
      setLocalError('Please accept the Terms of Service and Compliance Policy.');
      return;
    }

    try {
      const res = await registerAdmin({
        org_name: orgName,
        name: fullName,
        email: username,
        password,
        confirm_password: confirmPassword,
        terms_accepted: termsAccepted,
      });

      setLocalSuccess(res.message || 'Organization registered! Please verify your email.');
      if (res.verification_token) {
        setVerificationToken(res.verification_token);
      }
      setAuthMode('verify_email');
    } catch (err) {
      setLocalError(err.message || 'Admin registration failed.');
    }
  };

  // Handle Writer Registration
  const handleWriterRegisterSubmit = async (e) => {
    e.preventDefault();
    setLocalError(null);
    setLocalSuccess(null);

    if (!inviteCode.trim()) {
      setLocalError('A valid invite code is required to register as a writer.');
      return;
    }
    if (password !== confirmPassword) {
      setLocalError('Passwords do not match.');
      return;
    }
    if (!termsAccepted) {
      setLocalError('Please accept the Terms of Service and Compliance Policy.');
      return;
    }

    try {
      const res = await registerWriter({
        invite_code: inviteCode.trim(),
        name: fullName,
        email: username,
        password,
        confirm_password: confirmPassword,
        terms_accepted: termsAccepted,
      });

      if (res.needs_approval) {
        setPendingApprovalInfo({ username, email: username });
      }
      if (res.verification_token) {
        setVerificationToken(res.verification_token);
      }
      setLocalSuccess(res.message || 'Registration submitted! Please verify your email.');
      setAuthMode('verify_email');
    } catch (err) {
      setLocalError(err.message || 'Writer registration failed.');
    }
  };

  // Handle Email Verification
  const handleVerifyEmailSubmit = async (e) => {
    e.preventDefault();
    setLocalError(null);
    setLocalSuccess(null);

    try {
      const res = await verifyEmail(verificationToken.trim());
      setLocalSuccess(res.message || 'Email verified successfully! You may now sign in.');
      if (res.is_approved === false) {
        setAuthMode('waiting_approval');
      } else {
        setTimeout(() => setAuthMode('writer_login'), 1500);
      }
    } catch (err) {
      setLocalError(err.message || 'Verification failed. Token may be invalid or expired.');
    }
  };

  // Handle Password Reset Request
  const handleResetRequestSubmit = async (e) => {
    e.preventDefault();
    setLocalError(null);
    setLocalSuccess(null);

    try {
      const res = await requestPasswordReset(username.trim());
      setLocalSuccess(res.message);
      if (res.reset_token) {
        setResetToken(res.reset_token);
        setAuthMode('reset_confirm');
      }
    } catch (err) {
      setLocalError(err.message || 'Password reset request failed.');
    }
  };

  // Handle Password Reset Confirm
  const handleResetConfirmSubmit = async (e) => {
    e.preventDefault();
    setLocalError(null);
    setLocalSuccess(null);

    if (password !== confirmPassword) {
      setLocalError('Passwords do not match.');
      return;
    }

    try {
      const res = await confirmPasswordReset({
        token: resetToken.trim(),
        password,
        confirm_password: confirmPassword,
      });
      setLocalSuccess(res.message);
      setTimeout(() => setAuthMode('writer_login'), 1500);
    } catch (err) {
      setLocalError(err.message || 'Password reset failed.');
    }
  };

  // Quick sign-in helper for development and demo inspection
  const handleQuickLogin = async (u, p, portal = 'WRITER') => {
    setLocalError(null);
    try {
      const loggedInUser = await login(u, p, portal);
      if (onLoginSuccess) {
        onLoginSuccess(loggedInUser);
      }
    } catch (err) {
      setLocalError(err.message);
    }
  };

  return (
    <div className="min-h-screen w-full flex bg-[var(--bg)] text-[var(--text)] transition-colors antialiased">
      {/* LEFT SIDE: Forest Theme Visual Canopy & Brand Illustration */}
      <div className="hidden lg:flex lg:w-1/2 relative bg-[var(--surface-alt)] border-r border-[var(--border)] flex-col justify-between p-12 overflow-hidden select-none">
        {/* Subtle Decorative Forest Leaf SVG Background Motif */}
        <svg
          className="absolute -right-20 -bottom-20 w-96 h-96 opacity-10 pointer-events-none text-[var(--primary)]"
          viewBox="0 0 200 200"
          fill="currentColor"
        >
          <path d="M42.7,-73.4C55.9,-67.2,67.8,-57.4,75.4,-44.8C83,-32.2,86.2,-16.1,85.2,-0.6C84.2,15,79,29.9,70.9,42.9C62.8,55.9,51.8,66.9,38.8,73.7C25.8,80.5,12.9,83,-0.6,84C-14.1,85,-28.2,84.4,-40.9,78.2C-53.6,72,-64.9,60.2,-73.4,46.7C-81.8,33.2,-87.5,18.1,-87.3,3.3C-87,-11.5,-80.9,-26,-72,-38.3C-63.1,-50.7,-51.4,-60.9,-38.5,-67.3C-25.6,-73.7,-11.5,-76.3,2.4,-80.5C16.3,-84.7,29.5,-79.6,42.7,-73.4Z" transform="translate(100 100)" />
        </svg>

        {/* Brand Shield & Header */}
        <div className="relative z-10">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-[var(--primary)] flex items-center justify-center border border-emerald-900/30 shadow-xs">
              <Shield className="w-5 h-5 text-white" />
            </div>
            <div>
              <span className="font-bold text-xl font-serif tracking-tight text-[var(--text)]">
                BrandGuard
              </span>
              <span className="ml-2 font-mono text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full bg-[var(--surface)] text-[var(--primary)] border border-[var(--border)]">
                Round 4 · v3.2
              </span>
            </div>
          </div>
          <p className="mt-3 text-xs font-mono text-[var(--text-muted)] tracking-wider">
            Deterministic Pre-Publication Compiler &amp; Multi-Tenant Linter
          </p>
        </div>

        {/* Center: Value Propositions & Quotes */}
        <div className="relative z-10 max-w-lg space-y-6">
          <blockquote className="space-y-3">
            <p className="font-serif text-2xl font-medium tracking-tight text-[var(--text)] leading-snug">
              "Brand compliance cleared deterministically before publishing — never legally cleared, always brand-aligned."
            </p>
            <footer className="text-xs text-[var(--text-muted)] font-mono">
              NovaPay Global Launch · Automated Governance Architecture
            </footer>
          </blockquote>

          {/* Three Feature Highlights */}
          <div className="space-y-3 pt-2">
            <div className="flex items-start gap-3 p-3 rounded-[var(--radius-card)] bg-[var(--surface)]/80 border border-[var(--border)] shadow-2xs">
              <div className="p-1.5 rounded-lg bg-[var(--cleared-tint)] text-[var(--cleared)] shrink-0 mt-0.5">
                <Check className="w-4 h-4" />
              </div>
              <div className="text-xs">
                <div className="font-bold text-[var(--text)]">Multi-Tenant Organization Isolation</div>
                <div className="text-[var(--text-muted)] mt-0.5">
                  Tenant boundaries enforced in every query. Scoped rules, facts, repos, and telemetry.
                </div>
              </div>
            </div>

            <div className="flex items-start gap-3 p-3 rounded-[var(--radius-card)] bg-[var(--surface)]/80 border border-[var(--border)] shadow-2xs">
              <div className="p-1.5 rounded-lg bg-[var(--info-tint)] text-[var(--info)] shrink-0 mt-0.5">
                <FileCheck className="w-4 h-4" />
              </div>
              <div className="text-xs">
                <div className="font-bold text-[var(--text)]">Invite-Only Writer Registration</div>
                <div className="text-[var(--text-muted)] mt-0.5">
                  Writers register solely with 7-day cryptographically signed invite tokens issued by Admins.
                </div>
              </div>
            </div>

            <div className="flex items-start gap-3 p-3 rounded-[var(--radius-card)] bg-[var(--surface)]/80 border border-[var(--border)] shadow-2xs">
              <div className="p-1.5 rounded-lg bg-[var(--warning-tint)] text-[var(--warning-text)] shrink-0 mt-0.5">
                <ShieldCheck className="w-4 h-4" />
              </div>
              <div className="text-xs">
                <div className="font-bold text-[var(--text)]">Enterprise Rate Limiting &amp; Lockout</div>
                <div className="text-[var(--text-muted)] mt-0.5">
                  Zero email discovery leaks, PBKDF2 hashing, and brute-force account locking.
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Footer: Live Server Health & Status */}
        <div className="relative z-10 flex items-center justify-between text-xs text-[var(--text-muted)] pt-6 border-t border-[var(--border)]">
          <ServerHealthPill compact />
          <span className="font-mono text-[11px]">WCAG AA Compliant · Forest Canopy</span>
        </div>
      </div>

      {/* RIGHT SIDE: Interactive Auth Forms */}
      <div className="w-full lg:w-1/2 flex flex-col justify-between p-6 sm:p-10 lg:p-12 overflow-y-auto">
        {/* Top Header: Portal Switcher, Theme Toggle & Status */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => {
                setLocalError(null);
                setLocalSuccess(null);
                setAuthMode('writer_login');
              }}
              className={`text-xs font-semibold px-3 py-1.5 rounded-lg transition cursor-pointer ${
                authMode === 'writer_login' || authMode === 'writer_register'
                  ? 'bg-[var(--surface-alt)] text-[var(--primary)] font-bold shadow-2xs border border-[var(--border)]'
                  : 'text-[var(--text-muted)] hover:text-[var(--text)]'
              }`}
            >
              Writer Studio
            </button>
            <button
              type="button"
              onClick={() => {
                setLocalError(null);
                setLocalSuccess(null);
                setAuthMode('admin_login');
              }}
              className={`text-xs font-semibold px-3 py-1.5 rounded-lg transition cursor-pointer ${
                authMode === 'admin_login' || authMode === 'admin_register'
                  ? 'bg-[var(--surface-alt)] text-[var(--primary)] font-bold shadow-2xs border border-[var(--border)]'
                  : 'text-[var(--text-muted)] hover:text-[var(--text)]'
              }`}
            >
              Admin Portal
            </button>
          </div>

          <button
            type="button"
            onClick={toggleTheme}
            aria-label="Toggle dark/light theme"
            className="p-2 rounded-lg border border-[var(--border)] bg-[var(--surface)] text-[var(--text-muted)] hover:text-[var(--text)] transition cursor-pointer"
          >
            {isDark ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4" />}
          </button>
        </div>

        {/* Central Auth Card */}
        <div className="max-w-md w-full mx-auto my-auto space-y-6">
          {/* Form Header Titles */}
          <div>
            <div className="text-[11px] font-mono font-semibold tracking-wider text-[var(--primary)] uppercase">
              {authMode === 'admin_login' && 'GOVERNANCE LEAD PORTAL'}
              {authMode === 'writer_login' && 'CONTENT WRITER STUDIO'}
              {authMode === 'admin_register' && 'CREATE NEW ORGANIZATION'}
              {authMode === 'writer_register' && 'INVITE-ONLY REGISTRATION'}
              {authMode === 'verify_email' && 'EMAIL VERIFICATION'}
              {authMode === 'reset_request' && 'ACCOUNT RECOVERY'}
              {authMode === 'reset_confirm' && 'SET NEW PASSWORD'}
              {authMode === 'waiting_approval' && 'WORKSPACE ACCESS PENDING'}
            </div>
            <h1 className="text-2xl font-bold font-serif tracking-tight text-[var(--text)] mt-1">
              {authMode === 'admin_login' && 'Sign in to Admin Console'}
              {authMode === 'writer_login' && 'Sign in to Writer Studio'}
              {authMode === 'admin_register' && 'Register Organization & Owner'}
              {authMode === 'writer_register' && 'Join via Invite Code'}
              {authMode === 'verify_email' && 'Verify Work Email'}
              {authMode === 'reset_request' && 'Reset your password'}
              {authMode === 'reset_confirm' && 'Create your new password'}
              {authMode === 'waiting_approval' && 'Waiting for Admin Approval'}
            </h1>
            <p className="text-xs text-[var(--text-muted)] mt-1.5">
              {authMode === 'admin_login' && 'Admin governance privileges only. Strict authentication applies.'}
              {authMode === 'writer_login' && 'Run pre-flight compliance audits and submit campaign copy.'}
              {authMode === 'admin_register' && 'Creates a brand new organization with you as the founding Admin.'}
              {authMode === 'writer_register' && 'Enter your 7-day invite code provided by your administrator.'}
              {authMode === 'verify_email' && 'Enter your single-use verification code to activate your account.'}
              {authMode === 'reset_request' && 'Enter your email address to receive secure reset instructions.'}
              {authMode === 'reset_confirm' && 'Choose a strong 12+ character password for your account.'}
              {authMode === 'waiting_approval' && 'Your account is created. An administrator must approve your access.'}
            </p>
          </div>

          {/* Feedback Banners */}
          {localError && (
            <div
              role="alert"
              className="p-3.5 rounded-[var(--radius-card)] bg-[var(--blocker-tint)] border border-[var(--blocker)]/30 text-[var(--blocker)] flex items-start gap-2.5 text-xs font-medium"
            >
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{localError}</span>
            </div>
          )}

          {localSuccess && (
            <div
              role="status"
              className="p-3.5 rounded-[var(--radius-card)] bg-[var(--cleared-tint)] border border-[var(--cleared)]/30 text-[var(--cleared)] flex items-start gap-2.5 text-xs font-medium"
            >
              <CheckCircle2 className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{localSuccess}</span>
            </div>
          )}

          {/* ============================================================ */}
          {/* VIEW: WRITER OR ADMIN LOGIN                                  */}
          {/* ============================================================ */}
          {(authMode === 'writer_login' || authMode === 'admin_login') && (
            <form onSubmit={handleLoginSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-[var(--text)] mb-1">
                  Username or Work Email
                </label>
                <div className="relative">
                  <User className="w-4 h-4 text-[var(--text-muted)] absolute left-3 top-3 pointer-events-none" />
                  <input
                    type="text"
                    required
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    placeholder={authMode === 'admin_login' ? 'admin@novapay.io' : 'writer@novapay.io'}
                    className="w-full pl-9 pr-3 py-2 text-xs bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius-input)] text-[var(--text)] placeholder:text-[var(--text-muted)] focus:outline-hidden focus:border-[var(--primary)] focus:ring-1 focus:ring-[var(--primary)] transition"
                  />
                </div>
              </div>

              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="text-xs font-semibold text-[var(--text)]">Password</label>
                  <button
                    type="button"
                    onClick={() => {
                      setLocalError(null);
                      setLocalSuccess(null);
                      setAuthMode('reset_request');
                    }}
                    className="text-[11px] font-medium text-[var(--primary)] hover:underline cursor-pointer"
                  >
                    Forgot password?
                  </button>
                </div>
                <div className="relative">
                  <Lock className="w-4 h-4 text-[var(--text-muted)] absolute left-3 top-3 pointer-events-none" />
                  <input
                    type="password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••••••"
                    className="w-full pl-9 pr-3 py-2 text-xs bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius-input)] text-[var(--text)] placeholder:text-[var(--text-muted)] focus:outline-hidden focus:border-[var(--primary)] focus:ring-1 focus:ring-[var(--primary)] transition"
                  />
                </div>
              </div>

              {/* Simulated Cloudflare Turnstile Human Verification */}
              <div className="p-2.5 rounded-[var(--radius-card)] bg-[var(--surface-alt)]/70 border border-[var(--border)] flex items-center justify-between text-[11px] text-[var(--text-muted)]">
                <span className="flex items-center gap-1.5 font-mono">
                  <ShieldCheck className="w-3.5 h-3.5 text-[var(--cleared)]" />
                  <span>Cloudflare Turnstile Verified</span>
                </span>
                <span className="text-[10px] text-[var(--cleared)] font-bold">Passed</span>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full py-2.5 px-4 rounded-[var(--radius-input)] bg-[var(--primary)] hover:bg-[var(--primary-hover)] text-white text-xs font-bold transition shadow-2xs flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
              >
                {loading && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                <span>{authMode === 'admin_login' ? 'Sign in as Admin' : 'Sign in as Writer'}</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>

              {/* Registration Links */}
              <div className="pt-2 text-center text-xs text-[var(--text-muted)] space-y-1">
                {authMode === 'admin_login' ? (
                  <div>
                    Need to establish a new organization?{' '}
                    <button
                      type="button"
                      onClick={() => {
                        setLocalError(null);
                        setLocalSuccess(null);
                        setAuthMode('admin_register');
                      }}
                      className="font-bold text-[var(--primary)] hover:underline cursor-pointer"
                    >
                      Register as Admin →
                    </button>
                  </div>
                ) : (
                  <div>
                    Have an admin invite link?{' '}
                    <button
                      type="button"
                      onClick={() => {
                        setLocalError(null);
                        setLocalSuccess(null);
                        setAuthMode('writer_register');
                      }}
                      className="font-bold text-[var(--primary)] hover:underline cursor-pointer"
                    >
                      Register with Invite Code →
                    </button>
                  </div>
                )}
              </div>
            </form>
          )}

          {/* ============================================================ */}
          {/* VIEW: ADMIN REGISTRATION (Creates New Organization)          */}
          {/* ============================================================ */}
          {authMode === 'admin_register' && (
            <form onSubmit={handleAdminRegisterSubmit} className="space-y-3.5">
              <div>
                <label className="block text-xs font-semibold text-[var(--text)] mb-1">
                  Organization / Company Name
                </label>
                <div className="relative">
                  <Building className="w-4 h-4 text-[var(--text-muted)] absolute left-3 top-3 pointer-events-none" />
                  <input
                    type="text"
                    required
                    value={orgName}
                    onChange={(e) => setOrgName(e.target.value)}
                    placeholder="e.g. Apex Global Payments"
                    className="w-full pl-9 pr-3 py-2 text-xs bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius-input)] text-[var(--text)] placeholder:text-[var(--text-muted)] focus:outline-hidden focus:border-[var(--primary)] transition"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-[var(--text)] mb-1">
                  Full Name
                </label>
                <div className="relative">
                  <User className="w-4 h-4 text-[var(--text-muted)] absolute left-3 top-3 pointer-events-none" />
                  <input
                    type="text"
                    required
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder="Jordan Lee"
                    className="w-full pl-9 pr-3 py-2 text-xs bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius-input)] text-[var(--text)] placeholder:text-[var(--text-muted)] focus:outline-hidden focus:border-[var(--primary)] transition"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-[var(--text)] mb-1">
                  Work Email
                </label>
                <div className="relative">
                  <Mail className="w-4 h-4 text-[var(--text-muted)] absolute left-3 top-3 pointer-events-none" />
                  <input
                    type="email"
                    required
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    placeholder="jordan.lee@apex.io"
                    className="w-full pl-9 pr-3 py-2 text-xs bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius-input)] text-[var(--text)] placeholder:text-[var(--text-muted)] focus:outline-hidden focus:border-[var(--primary)] transition"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-[var(--text)] mb-1">
                  Password (12+ characters)
                </label>
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  className="w-full px-3 py-2 text-xs bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius-input)] text-[var(--text)] focus:outline-hidden focus:border-[var(--primary)] transition"
                />
                <PasswordStrengthMeter password={password} />
              </div>

              <div>
                <label className="block text-xs font-semibold text-[var(--text)] mb-1">
                  Confirm Password
                </label>
                <input
                  type="password"
                  required
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="••••••••••••"
                  className="w-full px-3 py-2 text-xs bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius-input)] text-[var(--text)] focus:outline-hidden focus:border-[var(--primary)] transition"
                />
              </div>

              <div className="flex items-start gap-2 pt-1">
                <input
                  type="checkbox"
                  id="terms-admin"
                  required
                  checked={termsAccepted}
                  onChange={(e) => setTermsAccepted(e.target.checked)}
                  className="mt-0.5 rounded border-[var(--border)] text-[var(--primary)] focus:ring-[var(--primary)] cursor-pointer"
                />
                <label htmlFor="terms-admin" className="text-[11px] text-[var(--text-muted)] cursor-pointer">
                  I accept the automated brand compliance policy, tenant isolation safeguards, and organization terms.
                </label>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full py-2.5 px-4 rounded-[var(--radius-input)] bg-[var(--primary)] hover:bg-[var(--primary-hover)] text-white text-xs font-bold transition shadow-2xs flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
              >
                {loading && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                <span>Create Organization &amp; Admin</span>
              </button>

              <div className="text-center text-xs text-[var(--text-muted)]">
                Already registered?{' '}
                <button
                  type="button"
                  onClick={() => setAuthMode('admin_login')}
                  className="font-bold text-[var(--primary)] hover:underline cursor-pointer"
                >
                  Admin Sign In →
                </button>
              </div>
            </form>
          )}

          {/* ============================================================ */}
          {/* VIEW: WRITER REGISTRATION (Invite-Only)                       */}
          {/* ============================================================ */}
          {authMode === 'writer_register' && (
            <form onSubmit={handleWriterRegisterSubmit} className="space-y-3.5">
              <div>
                <label className="block text-xs font-semibold text-[var(--text)] mb-1">
                  Invite Code (Required)
                </label>
                <div className="relative">
                  <KeyRound className="w-4 h-4 text-[var(--text-muted)] absolute left-3 top-3 pointer-events-none" />
                  <input
                    type="text"
                    required
                    value={inviteCode}
                    onChange={(e) => setInviteCode(e.target.value)}
                    placeholder="bg_inv_••••••••••••••••"
                    className="w-full pl-9 pr-3 py-2 text-xs font-mono bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius-input)] text-[var(--text)] placeholder:text-[var(--text-muted)] focus:outline-hidden focus:border-[var(--primary)] transition"
                  />
                </div>
                {validatingInvite && (
                  <p className="text-[10px] text-[var(--text-muted)] mt-1 flex items-center gap-1 font-mono">
                    <RefreshCw className="w-3 h-3 animate-spin" /> Validating invite code...
                  </p>
                )}
                {inviteOrgInfo && (
                  <div className="p-2 mt-1.5 rounded-lg bg-[var(--surface-alt)] border border-[var(--border)] text-[11px] text-[var(--primary)] font-semibold flex items-center gap-1.5">
                    <Check className="w-3.5 h-3.5 text-[var(--cleared)]" />
                    <span>Invite valid for organization: {inviteOrgInfo.organization_name}</span>
                  </div>
                )}
              </div>

              <div>
                <label className="block text-xs font-semibold text-[var(--text)] mb-1">
                  Full Name
                </label>
                <div className="relative">
                  <User className="w-4 h-4 text-[var(--text-muted)] absolute left-3 top-3 pointer-events-none" />
                  <input
                    type="text"
                    required
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder="Alex Morgan"
                    className="w-full pl-9 pr-3 py-2 text-xs bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius-input)] text-[var(--text)] placeholder:text-[var(--text-muted)] focus:outline-hidden focus:border-[var(--primary)] transition"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-[var(--text)] mb-1">
                  Work Email
                </label>
                <div className="relative">
                  <Mail className="w-4 h-4 text-[var(--text-muted)] absolute left-3 top-3 pointer-events-none" />
                  <input
                    type="email"
                    required
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    placeholder="alex.morgan@novapay.io"
                    className="w-full pl-9 pr-3 py-2 text-xs bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius-input)] text-[var(--text)] placeholder:text-[var(--text-muted)] focus:outline-hidden focus:border-[var(--primary)] transition"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-[var(--text)] mb-1">
                  Password (12+ characters)
                </label>
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  className="w-full px-3 py-2 text-xs bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius-input)] text-[var(--text)] focus:outline-hidden focus:border-[var(--primary)] transition"
                />
                <PasswordStrengthMeter password={password} />
              </div>

              <div>
                <label className="block text-xs font-semibold text-[var(--text)] mb-1">
                  Confirm Password
                </label>
                <input
                  type="password"
                  required
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="••••••••••••"
                  className="w-full px-3 py-2 text-xs bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius-input)] text-[var(--text)] focus:outline-hidden focus:border-[var(--primary)] transition"
                />
              </div>

              <div className="flex items-start gap-2 pt-1">
                <input
                  type="checkbox"
                  id="terms-writer"
                  required
                  checked={termsAccepted}
                  onChange={(e) => setTermsAccepted(e.target.checked)}
                  className="mt-0.5 rounded border-[var(--border)] text-[var(--primary)] focus:ring-[var(--primary)] cursor-pointer"
                />
                <label htmlFor="terms-writer" className="text-[11px] text-[var(--text-muted)] cursor-pointer">
                  I accept the marketing compiler guidelines, terms of service, and author responsibilities.
                </label>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full py-2.5 px-4 rounded-[var(--radius-input)] bg-[var(--primary)] hover:bg-[var(--primary-hover)] text-white text-xs font-bold transition shadow-2xs flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
              >
                {loading && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                <span>Register as Writer</span>
              </button>

              <div className="text-center text-xs text-[var(--text-muted)]">
                Already registered?{' '}
                <button
                  type="button"
                  onClick={() => setAuthMode('writer_login')}
                  className="font-bold text-[var(--primary)] hover:underline cursor-pointer"
                >
                  Writer Sign In →
                </button>
              </div>
            </form>
          )}

          {/* ============================================================ */}
          {/* VIEW: EMAIL VERIFICATION                                     */}
          {/* ============================================================ */}
          {authMode === 'verify_email' && (
            <form onSubmit={handleVerifyEmailSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-[var(--text)] mb-1">
                  Email Verification Token
                </label>
                <input
                  type="text"
                  required
                  value={verificationToken}
                  onChange={(e) => setVerificationToken(e.target.value)}
                  placeholder="bg_emv_••••••••••••••••"
                  className="w-full px-3 py-2 text-xs font-mono bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius-input)] text-[var(--text)] focus:outline-hidden focus:border-[var(--primary)] transition"
                />
                <p className="text-[11px] text-[var(--text-muted)] mt-1">
                  Paste the verification token dispatched to your email address.
                </p>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full py-2.5 px-4 rounded-[var(--radius-input)] bg-[var(--primary)] hover:bg-[var(--primary-hover)] text-white text-xs font-bold transition shadow-2xs flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
              >
                {loading && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                <span>Verify Email &amp; Activate</span>
              </button>

              <div className="text-center text-xs text-[var(--text-muted)]">
                <button
                  type="button"
                  onClick={() => setAuthMode('writer_login')}
                  className="font-bold text-[var(--primary)] hover:underline cursor-pointer flex items-center justify-center gap-1 mx-auto"
                >
                  <ChevronLeft className="w-3.5 h-3.5" /> Back to Sign In
                </button>
              </div>
            </form>
          )}

          {/* ============================================================ */}
          {/* VIEW: PASSWORD RESET REQUEST                                 */}
          {/* ============================================================ */}
          {authMode === 'reset_request' && (
            <form onSubmit={handleResetRequestSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-[var(--text)] mb-1">
                  Registered Work Email
                </label>
                <div className="relative">
                  <Mail className="w-4 h-4 text-[var(--text-muted)] absolute left-3 top-3 pointer-events-none" />
                  <input
                    type="email"
                    required
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    placeholder="user@novapay.io"
                    className="w-full pl-9 pr-3 py-2 text-xs bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius-input)] text-[var(--text)] placeholder:text-[var(--text-muted)] focus:outline-hidden focus:border-[var(--primary)] transition"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full py-2.5 px-4 rounded-[var(--radius-input)] bg-[var(--primary)] hover:bg-[var(--primary-hover)] text-white text-xs font-bold transition shadow-2xs flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
              >
                {loading && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                <span>Send Password Reset Link</span>
              </button>

              <div className="text-center text-xs text-[var(--text-muted)]">
                <button
                  type="button"
                  onClick={() => setAuthMode('writer_login')}
                  className="font-bold text-[var(--primary)] hover:underline cursor-pointer flex items-center justify-center gap-1 mx-auto"
                >
                  <ChevronLeft className="w-3.5 h-3.5" /> Back to Sign In
                </button>
              </div>
            </form>
          )}

          {/* ============================================================ */}
          {/* VIEW: PASSWORD RESET CONFIRM                                 */}
          {/* ============================================================ */}
          {authMode === 'reset_confirm' && (
            <form onSubmit={handleResetConfirmSubmit} className="space-y-3.5">
              <div>
                <label className="block text-xs font-semibold text-[var(--text)] mb-1">
                  Reset Token
                </label>
                <input
                  type="text"
                  required
                  value={resetToken}
                  onChange={(e) => setResetToken(e.target.value)}
                  placeholder="bg_rst_••••••••••••••••"
                  className="w-full px-3 py-2 text-xs font-mono bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius-input)] text-[var(--text)] focus:outline-hidden focus:border-[var(--primary)] transition"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-[var(--text)] mb-1">
                  New Password (12+ characters)
                </label>
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  className="w-full px-3 py-2 text-xs bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius-input)] text-[var(--text)] focus:outline-hidden focus:border-[var(--primary)] transition"
                />
                <PasswordStrengthMeter password={password} />
              </div>

              <div>
                <label className="block text-xs font-semibold text-[var(--text)] mb-1">
                  Confirm New Password
                </label>
                <input
                  type="password"
                  required
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="••••••••••••"
                  className="w-full px-3 py-2 text-xs bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius-input)] text-[var(--text)] focus:outline-hidden focus:border-[var(--primary)] transition"
                />
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full py-2.5 px-4 rounded-[var(--radius-input)] bg-[var(--primary)] hover:bg-[var(--primary-hover)] text-white text-xs font-bold transition shadow-2xs flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
              >
                {loading && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                <span>Set New Password &amp; Login</span>
              </button>
            </form>
          )}

          {/* ============================================================ */}
          {/* VIEW: WAITING FOR ADMIN APPROVAL SCREEN (G)                  */}
          {/* ============================================================ */}
          {authMode === 'waiting_approval' && (
            <div className="p-6 rounded-[var(--radius-card)] bg-[var(--surface)] border border-[var(--border)] shadow-xs space-y-4 text-center">
              <div className="w-12 h-12 rounded-full bg-[var(--warning-tint)] text-[var(--warning-text)] flex items-center justify-center mx-auto">
                <Clock className="w-6 h-6" />
              </div>
              <div>
                <span className="font-mono text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-[var(--warning-tint)] text-[var(--warning-text)] border border-[var(--warning-text)]/30">
                  Status: Pending Approval
                </span>
                <h3 className="text-lg font-bold font-serif text-[var(--text)] mt-2">
                  Waiting for Admin Approval
                </h3>
                <p className="text-xs text-[var(--text-muted)] mt-1.5 leading-relaxed">
                  Your email has been verified. However, this organization requires an administrator to review and approve your workspace access before you can log in.
                </p>
              </div>

              <div className="p-3 rounded-lg bg-[var(--surface-alt)] border border-[var(--border)] text-left text-xs font-mono space-y-1">
                <div className="text-[var(--text-muted)]">Account: {pendingApprovalInfo?.email || username}</div>
                <div className="text-[var(--primary)] font-semibold">Notification dispatched to Governance Team.</div>
              </div>

              <div className="pt-2 flex flex-col gap-2">
                <button
                  type="button"
                  onClick={() => setAuthMode('writer_login')}
                  className="w-full py-2 px-3 rounded-[var(--radius-input)] bg-[var(--primary)] text-white text-xs font-bold hover:bg-[var(--primary-hover)] transition cursor-pointer"
                >
                  Check Status / Sign In
                </button>
              </div>
            </div>
          )}

          {/* Quick Demo Personas Dropdown / Switcher for Easy Verification */}
          <div className="pt-4 border-t border-[var(--border)]">
            <details className="text-xs group">
              <summary className="font-mono text-[11px] font-semibold text-[var(--text-muted)] hover:text-[var(--text)] cursor-pointer select-none">
                ▸ Quick Sign-In (Demo Testing Personas)
              </summary>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-3 pt-1">
                <button
                  type="button"
                  onClick={() => handleQuickLogin('admin', 'admin123', 'ADMIN')}
                  className="p-2.5 rounded-lg border border-emerald-900/30 bg-[var(--surface-alt)] hover:bg-[var(--surface)] text-left transition cursor-pointer shadow-2xs"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-xs text-[var(--text)]">Jordan Lee</span>
                    <span className="font-mono text-[9px] px-1.5 py-0.5 rounded bg-[var(--primary)] text-white font-bold">
                      ADMIN
                    </span>
                  </div>
                  <p className="text-[10px] text-[var(--text-muted)] mt-0.5 truncate">
                    NovaPay Lead · Full governance &amp; approvals
                  </p>
                </button>

                <button
                  type="button"
                  onClick={() => handleQuickLogin('writer1', 'writer123', 'WRITER')}
                  className="p-2.5 rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] hover:bg-[var(--surface)] text-left transition cursor-pointer shadow-2xs"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-xs text-[var(--text)]">Alex Morgan</span>
                    <span className="font-mono text-[9px] px-1.5 py-0.5 rounded bg-sky-700 text-white font-bold">
                      WRITER
                    </span>
                  </div>
                  <p className="text-[10px] text-[var(--text-muted)] mt-0.5 truncate">
                    Marketing Ops · Pre-flight linter &amp; patches
                  </p>
                </button>
              </div>
            </details>
          </div>
        </div>

        {/* Bottom Footer Note */}
        <div className="text-center text-[11px] text-[var(--text-muted)] font-mono pt-6">
          BrandGuard Autonomous Governance · Zero False Claims Standard
        </div>
      </div>
    </div>
  );
}
