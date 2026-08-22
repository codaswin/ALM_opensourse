import { useCallback, useEffect, useState } from "react";
import { deleteCredentials, listCredentials, listRateLimits, saveCredentials, testCredentials, updateRateLimit } from "../api";
import { ErrorBanner } from "../components/ErrorBanner";
import type { ConnectionStatus, ConnectionTestResult, CredentialType, PlatformCredentialStatus, RateLimitStatus } from "../types";

// Platforms `POST /credentials/{id}/test` can actually reach live — the
// rest (e.g. LinkedIn itself, which is an OAuth-connected-account handled
// entirely through Composio) have no independent connectivity check yet.
const TESTABLE_PLATFORMS = new Set(["anthropic", "openai", "composio", "github", "reddit", "producthunt"]);

const TEST_STATUS_LABEL: Record<ConnectionStatus, string> = {
  connected: "Working",
  invalid: "Rejected",
  missing: "Missing",
  unavailable: "Unreachable",
};

// Plain-language label for each credential shape — this is the answer to
// "does this platform need a token, a login, an ID+secret pair, or an API
// key" the settings page exists to give, without making the reader learn
// what OAuth means first.
const CREDENTIAL_TYPE_LABEL: Record<CredentialType, string> = {
  api_key: "API key",
  token: "Access token",
  oauth_connected_account: "Login connection",
  client_credentials: "ID + secret",
  endpoint: "Server address",
};

const GROUP_ORDER = ["Publishing to LinkedIn", "AI models", "Research sources"];

function groupPlatforms(platforms: PlatformCredentialStatus[]): [string, PlatformCredentialStatus[]][] {
  const byGroup = new Map<string, PlatformCredentialStatus[]>();
  for (const p of platforms) {
    const list = byGroup.get(p.group) ?? [];
    list.push(p);
    byGroup.set(p.group, list);
  }
  const knownFirst = GROUP_ORDER.filter((g) => byGroup.has(g));
  const rest = [...byGroup.keys()].filter((g) => !GROUP_ORDER.includes(g));
  return [...knownFirst, ...rest].map((g) => [g, byGroup.get(g)!]);
}

function PlatformCard({
  platform,
  onChanged,
  currentUserId,
}: {
  platform: PlatformCredentialStatus;
  onChanged: () => void;
  currentUserId: string;
}) {
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [removing, setRemoving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<ConnectionTestResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const canSave = platform.fields.every((f) => !f.required || (draft[f.name] ?? "").trim());

  async function handleTest() {
    setTesting(true);
    setError(null);
    setTestResult(null);
    try {
      setTestResult(await testCredentials(platform.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setTesting(false);
    }
  }

  async function handleSave() {
    setSaving(true);
    setError(null);
    setTestResult(null);
    try {
      await saveCredentials(platform.id, draft);
      setDraft({});
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSaving(false);
    }
  }

  async function handleRemove() {
    setRemoving(true);
    setError(null);
    setTestResult(null);
    try {
      await deleteCredentials(platform.id);
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setRemoving(false);
    }
  }

  return (
    <form
      className="card connection-card"
      onSubmit={(event) => {
        event.preventDefault();
        void handleSave();
      }}
    >
      <div className="card-title-row">
        <h3>
          {platform.name}
          {platform.required && <span className="badge connection-required-badge">Needed to publish</span>}
        </h3>
        <span className={platform.connected ? "badge badge-approved" : "badge badge-neutral"}>
          {platform.connected ? "Connected" : "Not connected"}
        </span>
      </div>
      <p className="card-meta">
        <span className="mono-chip">{CREDENTIAL_TYPE_LABEL[platform.credential_type]}</span>
        {!platform.required && " · optional"}
      </p>
      <p className="card-reason">{platform.summary}</p>
      {platform.id === "linkedin" && (
        <p className="connection-help">
          Your Composio entity ID is <code className="mono-chip">{currentUserId}</code> — use this when creating
          your LinkedIn connected account in Composio's own dashboard, so it resolves back to your workspace here.
          If the account already exists under a different entity (Composio defaults new connections to{" "}
          <code className="mono-chip">default</code>), set the Entity ID override on the Composio card below instead
          of recreating the connection.
        </p>
      )}
      <ErrorBanner message={error} />

      <div className="connection-fields">
        {platform.fields.map((f) => (
          <label className="connection-field" key={f.name}>
            {f.label}
            <input
              type={f.secret ? "password" : "text"}
              placeholder={
                f.status === "saved_here"
                  ? `Saved — currently ${f.masked_preview}`
                  : f.status === "set_on_server"
                    ? "Already set on the server"
                    : f.placeholder
              }
              value={draft[f.name] ?? ""}
              autoComplete="off"
              onChange={(e) => setDraft((prev) => ({ ...prev, [f.name]: e.target.value }))}
            />
          </label>
        ))}
      </div>

      <p className="connection-help">{platform.help_text}</p>

      {testResult && (
        <p className="connection-help">
          <span className={testResult.status === "connected" ? "badge badge-approved" : "badge badge-rejected"}>
            {TEST_STATUS_LABEL[testResult.status]}
          </span>{" "}
          {testResult.detail}
        </p>
      )}

      <div className="card-actions">
        <button type="submit" disabled={saving || !canSave}>
          {saving ? "Saving…" : "Save"}
        </button>
        {platform.connected && TESTABLE_PLATFORMS.has(platform.id) && (
          <button type="button" onClick={() => void handleTest()} disabled={testing}>
            {testing ? "Testing…" : "Test connection"}
          </button>
        )}
        {platform.connected && (
          <button type="button" className="btn-reject" onClick={() => void handleRemove()} disabled={removing}>
            {removing ? "Removing…" : "Remove"}
          </button>
        )}
      </div>
    </form>
  );
}

function RateLimitRow({ status, onChanged }: { status: RateLimitStatus; onChanged: () => void }) {
  const [draft, setDraft] = useState(String(status.limit));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Keep the input in sync when a refresh brings back a value this row
  // didn't just save itself (e.g. usage ticking up elsewhere) — but never
  // clobber text the user is still mid-edit on.
  useEffect(() => {
    setDraft(String(status.limit));
  }, [status.limit]);

  const parsedDraft = Number(draft);
  const isValidDraft = draft.trim() !== "" && Number.isInteger(parsedDraft) && parsedDraft >= 0;
  const isDirty = isValidDraft && parsedDraft !== status.limit;
  const pct = status.limit > 0 ? Math.min((status.used / status.limit) * 100, 100) : 100;
  const atLimit = status.used >= status.limit;

  async function handleSave() {
    setSaving(true);
    setError(null);
    try {
      await updateRateLimit(status.action, parsedDraft);
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <form
      className="card rate-limit-row"
      onSubmit={(event) => {
        event.preventDefault();
        if (isDirty) void handleSave();
      }}
    >
      <div className="card-title-row">
        <h3>{status.label}</h3>
        <span className={atLimit ? "badge badge-rejected" : "badge badge-neutral"}>
          {status.used} of {status.limit} used today
        </span>
      </div>
      <div className="cost-bar-track rate-limit-bar-track">
        <div className={atLimit ? "cost-bar-fill cost-bar-over" : "cost-bar-fill"} style={{ width: `${pct}%` }} />
      </div>
      <ErrorBanner message={error} />
      <div className="card-actions">
        <label className="connection-field rate-limit-field">
          Daily limit
          <input
            type="text"
            inputMode="numeric"
            aria-label={`Daily limit for ${status.label}`}
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
          />
        </label>
        <button type="submit" disabled={saving || !isDirty}>
          {saving ? "Saving…" : "Save"}
        </button>
      </div>
    </form>
  );
}

export function ConnectionsView({ currentUserId }: { currentUserId: string }) {
  const [platforms, setPlatforms] = useState<PlatformCredentialStatus[]>([]);
  const [rateLimits, setRateLimits] = useState<RateLimitStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    // Settled, not all — these are two independent sections of this page;
    // one endpoint failing (e.g. a backend older than this frontend, still
    // missing /rate-limits) shouldn't also blank out the credentials list
    // that successfully loaded.
    const [platformsResult, rateLimitsResult] = await Promise.allSettled([listCredentials(), listRateLimits()]);
    if (platformsResult.status === "fulfilled") {
      setPlatforms(platformsResult.value);
    }
    if (rateLimitsResult.status === "fulfilled") {
      setRateLimits(rateLimitsResult.value);
    }
    const failure = platformsResult.status === "rejected" ? platformsResult.reason : rateLimitsResult.status === "rejected" ? rateLimitsResult.reason : null;
    if (failure) {
      setError(failure instanceof Error ? failure.message : String(failure));
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return (
    <section>
      <div className="view-header">
        <button type="button" onClick={() => void refresh()} disabled={loading}>
          {loading ? "Refreshing…" : "Refresh"}
        </button>
      </div>
      <p className="empty-state">
        Paste your logins, keys, and tokens here once — the app remembers them (encrypted) so you don't have to edit
        any config files. Nothing you type is ever shown again after saving; you'll just see the last few characters
        as a reminder of which one is on file.
      </p>
      <ErrorBanner message={error} />

      {rateLimits.length > 0 && (
        <div className="connection-group">
          <h3 className="connection-group-title">LinkedIn API daily limits</h3>
          <p className="connection-help rate-limit-intro">
            Each cap resets at midnight UTC. Lower it to publish more cautiously, or raise it once you trust the
            agents' judgment — the app will always refuse to go over whatever you set here.
          </p>
          <div className="card-list">
            {rateLimits.map((status) => (
              <RateLimitRow status={status} onChanged={() => void refresh()} key={status.action} />
            ))}
          </div>
        </div>
      )}

      {groupPlatforms(platforms).map(([group, platformsInGroup]) => (
        <div key={group} className="connection-group">
          <h3 className="connection-group-title">{group}</h3>
          <div className="card-list">
            {platformsInGroup.map((platform) => (
              <PlatformCard
                platform={platform}
                onChanged={() => void refresh()}
                currentUserId={currentUserId}
                key={platform.id}
              />
            ))}
          </div>
        </div>
      ))}
    </section>
  );
}
