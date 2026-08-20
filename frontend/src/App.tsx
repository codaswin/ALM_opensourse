import { Component, useEffect, useState, type ComponentType, type FormEvent, type ReactNode } from "react";
import { Activity, Bot, BrainCircuit, ChevronRight, CircleDollarSign, Command, Eye, EyeOff, LockKeyhole, LogOut, Menu, MessageSquareText, Moon, Network, Settings2, ShieldCheck, Sparkles, Sun, Users, UserRound, Workflow, X } from "lucide-react";
import { AnimatePresence, motion, MotionConfig } from "motion/react";
import "./App.css";
import { ApiError, getCurrentSession, getRuntimeBootstrap, initializeApiTransport, login, logout } from "./api";
import { ActivityBanner } from "./components/ActivityBanner";
import { ThemeProvider } from "./ThemeProvider";
import { useTheme } from "./themeStore";
import type { DashboardSession, RuntimeBootstrap } from "./types";
import { ApprovalQueueView } from "./views/ApprovalQueueView";
import { BrandVoiceView } from "./views/BrandVoiceView";
import { ConnectionsView } from "./views/ConnectionsView";
import { CostView } from "./views/CostView";
import { DiagnosticsView } from "./views/DiagnosticsView";
import { LandingPage } from "./views/LandingPage";
import { LearningProposalsView } from "./views/LearningProposalsView";
import { SettingsView } from "./views/SettingsView";
import { UsersView } from "./views/UsersView";
import { WorkflowsView } from "./views/WorkflowsView";

type NavIcon = ComponentType<{ size?: number; strokeWidth?: number; className?: string }>;
const TABS = [
  { id: "workflows", label: "Workflows", description: "Run agent tasks", icon: Workflow, group: "Workspace", adminOnly: false, render: () => <WorkflowsView /> },
  { id: "approvals", label: "Approval Queue", description: "Review gated actions", icon: ShieldCheck, group: "Workspace", adminOnly: false, render: () => <ApprovalQueueView /> },
  { id: "connections", label: "Connections", description: "Manage integrations", icon: Network, group: "Workspace", adminOnly: false, render: (session: DashboardSession) => <ConnectionsView currentUserId={session.user.id} /> },
  { id: "brand-voice", label: "Brand Voice", description: "Define writing style", icon: MessageSquareText, group: "Intelligence", adminOnly: false, render: () => <BrandVoiceView /> },
  { id: "learning", label: "Self-Learning", description: "Review proposals", icon: BrainCircuit, group: "Intelligence", adminOnly: false, render: () => <LearningProposalsView /> },
  { id: "settings", label: "Agent Settings", description: "Configure behavior", icon: Settings2, group: "System", adminOnly: false, render: () => <SettingsView /> },
  { id: "cost", label: "Usage & Cost", description: "Track daily spend", icon: CircleDollarSign, group: "System", adminOnly: false, render: () => <CostView /> },
  { id: "diagnostics", label: "Diagnostics", description: "Check service health", icon: Activity, group: "System", adminOnly: false, render: () => <DiagnosticsView /> },
  // Invite-only account creation — only admins can see or reach this tab
  // (also enforced server-side by require_role(minimum="admin") on
  // GET/POST /admin/users, so hiding the tab is a UX nicety, not the guard).
  { id: "users", label: "Users", description: "Invite teammates", icon: Users, group: "System", adminOnly: true, render: () => <UsersView /> },
] as const satisfies readonly { id: string; label: string; description: string; icon: NavIcon; group: string; adminOnly: boolean; render: (session: DashboardSession) => React.ReactNode }[];
const NAV_GROUPS = ["Workspace", "Intelligence", "System"] as const;
const SERVER_RUNTIME_FALLBACK: RuntimeBootstrap = {
  mode: "server",
  user: { id: "", username: "", role: "viewer" },
  capabilities: {
    requires_login: true,
    supports_multiple_users: true,
    supports_user_administration: true,
    uses_distributed_scheduler_coordination: true,
    runs_scheduler_only_while_app_is_open: false,
  },
  api_version: "unknown",
};

function ThemeToggle() {
  const { theme, toggleTheme } = useTheme();
  const nextTheme = theme === "light" ? "dark" : "light";
  // The icon itself is the feedback for what just happened (design skill
  // §13, causality) — it morphs into the new state rather than snapping,
  // so pressing the button reads as "the sun set" / "the sun rose" instead
  // of an inert glyph swap.
  return <button type="button" className="theme-toggle theme-toggle-morph" onClick={toggleTheme} aria-label={`Switch to ${nextTheme} theme`} title={`Switch to ${nextTheme} theme`}>
    <AnimatePresence mode="wait" initial={false}>
      <motion.span
        key={theme}
        className="theme-toggle-icon"
        initial={{ rotate: -90, scale: 0.4, opacity: 0 }}
        animate={{ rotate: 0, scale: 1, opacity: 1 }}
        exit={{ rotate: 90, scale: 0.4, opacity: 0 }}
        transition={{ type: "spring", stiffness: 500, damping: 30 }}
      >
        {theme === "light" ? <Moon size={17} /> : <Sun size={17} />}
      </motion.span>
    </AnimatePresence>
  </button>;
}

function LoginScreen({ onAuthenticated }: { onAuthenticated: (session: DashboardSession) => void }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [passwordVisible, setPasswordVisible] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      onAuthenticated(await login(username, password));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign in failed");
    } finally {
      setSubmitting(false);
    }
  }

  return <main className="login-shell">
    <motion.form
      className="login-panel"
      onSubmit={(event) => void handleSubmit(event)}
      initial={{ opacity: 0, scale: 0.96, filter: "blur(4px)" }}
      animate={{ opacity: 1, scale: 1, filter: "blur(0px)" }}
      transition={{ type: "spring", stiffness: 380, damping: 32 }}
    >
      <div className="login-brand"><span className="sidebar-brand-mark"><Bot size={22} /></span><span><strong>AI LinkedIn</strong><small>Manager</small></span></div>
      <div className="login-heading"><span><LockKeyhole size={19} /></span><div><h1>Dashboard sign in</h1><p>Use your assigned workspace account.</p></div></div>
      {error && <p className="login-error" role="alert">{error}</p>}
      <label className="login-field"><span>Username</span><input autoComplete="username" required value={username} onChange={(event) => setUsername(event.target.value)} /></label>
      <label className="login-field">
        <span>Password</span>
        <div className="login-password-field">
          <input
            type={passwordVisible ? "text" : "password"}
            autoComplete="current-password"
            required
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
          <button
            type="button"
            className="login-password-toggle"
            onClick={() => setPasswordVisible((visible) => !visible)}
            aria-label={passwordVisible ? "Hide password" : "Show password"}
            aria-pressed={passwordVisible}
            tabIndex={-1}
          >
            {passwordVisible ? <EyeOff size={16} /> : <Eye size={16} />}
          </button>
        </div>
      </label>
      <button className="login-submit" type="submit" disabled={submitting}>{submitting ? "Signing in..." : "Sign in"}</button>
    </motion.form>
  </main>;
}

function Dashboard({ session, runtime, onSignedOut }: { session: DashboardSession; runtime: RuntimeBootstrap; onSignedOut: () => void }) {
  const [activeTab, setActiveTab] = useState<(typeof TABS)[number]["id"]>("workflows");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const visibleTabs = TABS.filter((tab) => !tab.adminOnly || (runtime.capabilities.supports_user_administration && session.user.role === "admin"));
  const active = visibleTabs.find((tab) => tab.id === activeTab) ?? visibleTabs[0];
  const ActiveIcon = active.icon;

  useEffect(() => {
    if (!sidebarOpen) return;
    const closeOnEscape = (event: KeyboardEvent) => { if (event.key === "Escape") setSidebarOpen(false); };
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [sidebarOpen]);

  const selectTab = (id: (typeof TABS)[number]["id"]) => { setActiveTab(id); setSidebarOpen(false); };
  const handleLogout = async () => { await logout().catch(() => undefined); onSignedOut(); };

  return <div className="app-shell">
    <ActivityBanner />
    <div className="app-body">
      <header className="mobile-header">
        <button className="mobile-menu-toggle" type="button" onClick={() => setSidebarOpen(true)} aria-label="Open navigation" aria-controls="primary-sidebar" aria-expanded={sidebarOpen}><Menu size={19} /><span>Menu</span></button>
        <div className="mobile-brand"><span className="sidebar-brand-mark"><Bot size={18} /></span><span>AI LinkedIn Manager</span></div>
        <ThemeToggle />
      </header>
      <button className={sidebarOpen ? "sidebar-backdrop sidebar-backdrop-visible" : "sidebar-backdrop"} type="button" aria-label="Close navigation" onClick={() => setSidebarOpen(false)} />
      <aside id="primary-sidebar" aria-label="Application sidebar" className={sidebarOpen ? "app-sidebar app-sidebar-open" : "app-sidebar"}>
        <div className="sidebar-top">
          <div className="sidebar-brand"><span className="sidebar-brand-mark"><Bot size={19} strokeWidth={2.2} /></span><span className="sidebar-brand-copy"><strong>AI LinkedIn</strong><span>Manager</span></span></div>
          <button className="sidebar-close" type="button" onClick={() => setSidebarOpen(false)} aria-label="Close navigation"><X size={17} /><span>Close</span></button>
        </div>
        <div className="workspace-status"><span className="workspace-status-icon"><Sparkles size={15} /></span><span><strong>Agent workspace</strong><small><i /> Systems operational</small></span></div>
        <nav className="sidebar-nav" aria-label="Primary navigation">
          {NAV_GROUPS.map((group) => <div className="sidebar-group" key={group}>
            <span className="sidebar-group-label">{group}</span>
            {visibleTabs.filter((tab) => tab.group === group).map((tab) => {
              const Icon = tab.icon;
              const isActive = tab.id === activeTab;
              return <button key={tab.id} type="button" className={isActive ? "sidebar-item sidebar-item-active" : "sidebar-item"} onClick={() => selectTab(tab.id)} aria-current={isActive ? "page" : undefined}>
                {isActive && (
                  <motion.span
                    layoutId="sidebar-active-indicator"
                    className="sidebar-item-indicator"
                    transition={{ type: "spring", stiffness: 500, damping: 40 }}
                  />
                )}
                <span className="sidebar-item-icon"><Icon size={19} strokeWidth={1.9} /></span>
                <span className="sidebar-item-copy"><strong>{tab.label}</strong><small>{tab.description}</small></span>
                <ChevronRight className="sidebar-item-chevron" size={15} />
              </button>;
            })}
          </div>)}
        </nav>
        <div className="sidebar-footer">
          <div className="sidebar-user"><span className="sidebar-user-avatar"><UserRound size={16} /></span><span className="sidebar-user-details"><strong>{session.user.username}</strong><small>{session.user.role}</small></span></div>
          {runtime.capabilities.requires_login && <button type="button" className="theme-toggle" onClick={() => void handleLogout()} aria-label="Sign out" title="Sign out"><LogOut size={17} /></button>}
          <ThemeToggle />
        </div>
      </aside>
      <main className="app-main">
        <header className="workspace-header">
          <div className="page-context"><span>{active.group}</span><ChevronRight size={13} /><strong>{active.label}</strong></div>
          <div className="workspace-heading">
            <span className="workspace-heading-icon"><ActiveIcon size={22} /></span>
            <div><h1>{active.label}</h1><p>{active.description}</p></div>
            <span className="workspace-mode"><Command size={13} /> Human controlled</span>
          </div>
        </header>
        {/* popLayout takes the outgoing view out of flow immediately so the
            incoming one doesn't wait on it — switching tabs mid-animation
            redirects cleanly instead of queuing (design skill §3). */}
        <AnimatePresence mode="popLayout" initial={false}>
          <motion.div
            key={active.id}
            initial={{ opacity: 0, y: 8, filter: "blur(2px)" }}
            animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
            exit={{ opacity: 0, y: -8, filter: "blur(2px)" }}
            transition={{ type: "spring", stiffness: 380, damping: 34 }}
          >
            {active.render(session)}
          </motion.div>
        </AnimatePresence>
      </main>
    </div>
  </div>;
}

function DesktopWelcome({ onContinue }: { onContinue: () => void }) {
  return <main className="login-shell"><section className="login-panel">
    <div className="login-brand"><span className="sidebar-brand-mark"><Bot size={22} /></span><span><strong>AI LinkedIn</strong><small>Desktop Manager</small></span></div>
    <div className="login-heading"><span><ShieldCheck size={19} /></span><div><h1>Your private workspace is ready</h1><p>Data stays in this installation and credentials use your operating system's secure store.</p></div></div>
    <p>Scheduled work runs while this application is open. Every publish, reply, delete, schedule, and connection request still requires human approval.</p>
    <button className="login-submit" type="button" onClick={onContinue}>Open workspace</button>
  </section></main>;
}

function StartupFailure({ message, onRetry }: { message: string; onRetry: () => void }) {
  return <main className="login-shell"><section className="login-panel" role="alert">
    <div className="login-heading"><span><ShieldCheck size={19} /></span><div><h1>Local service needs attention</h1><p>{message}</p></div></div>
    <button className="login-submit" type="button" onClick={onRetry}>Retry startup</button>
  </section></main>;
}

class AppErrorBoundary extends Component<{ children: ReactNode }, { error: Error | null }> {
  state = { error: null as Error | null };
  static getDerivedStateFromError(error: Error) { return { error }; }
  render() {
    if (this.state.error) return <StartupFailure message={this.state.error.message} onRetry={() => window.location.reload()} />;
    return this.props.children;
  }
}

function AuthenticatedApp() {
  const [session, setSession] = useState<DashboardSession | null>(null);
  const [runtime, setRuntime] = useState<RuntimeBootstrap | null>(null);
  const [checking, setChecking] = useState(true);
  const [startupError, setStartupError] = useState<string | null>(null);
  const [startupAttempt, setStartupAttempt] = useState(0);
  const [desktopOnboarded, setDesktopOnboarded] = useState(() => localStorage.getItem("desktop-onboarding-complete-v1") === "true");
  // Signed-out visitors land on the marketing page first; returning users
  // with a live session skip straight past it into the dashboard.
  const [pastLanding, setPastLanding] = useState(false);

  useEffect(() => {
    setChecking(true);
    setStartupError(null);
    initializeApiTransport()
      .then(() => getRuntimeBootstrap())
      .then((bootstrap) => { setRuntime(bootstrap); return getCurrentSession(); })
      .then(setSession)
      .catch((error: unknown) => {
        if (error instanceof ApiError && error.status === 401) {
          setRuntime(SERVER_RUNTIME_FALLBACK);
          return;
        }
        console.error(error);
        setStartupError(error instanceof Error ? error.message : "Startup failed");
      })
      .finally(() => setChecking(false));
  }, [startupAttempt]);

  if (checking) return <div className="auth-loading"><span className="auth-spinner" /><span>Starting secure workspace</span></div>;
  if (startupError) return <StartupFailure message={startupError} onRetry={() => setStartupAttempt((value) => value + 1)} />;
  if (session && runtime) {
    if (runtime.mode === "desktop" && !desktopOnboarded) return <DesktopWelcome onContinue={() => { localStorage.setItem("desktop-onboarding-complete-v1", "true"); setDesktopOnboarded(true); }} />;
    return <Dashboard session={session} runtime={runtime} onSignedOut={() => { setSession(null); setPastLanding(false); }} />;
  }
  if (!pastLanding) return <LandingPage onEnter={() => setPastLanding(true)} />;
  return <LoginScreen onAuthenticated={setSession} />;
}

export default function App() {
  return <AppErrorBoundary><MotionConfig reducedMotion="user"><ThemeProvider><AuthenticatedApp /></ThemeProvider></MotionConfig></AppErrorBoundary>;
}
