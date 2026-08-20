import { useCallback, useEffect, useState } from "react";
import { createBackup, fetchDiagnostics, listBackups } from "../api";
import { ErrorBanner } from "../components/ErrorBanner";
import type { BackupManifest, DiagnosticComponent, DiagnosticsReport } from "../types";

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function statusBadgeClass(status: string): string {
  if (status === "ok" || status === "running") return "badge badge-approved";
  if (status === "error") return "badge badge-rejected";
  return "badge badge-neutral";
}

function ComponentCard({ label, component }: { label: string; component: DiagnosticComponent }) {
  return (
    <article className="card">
      <div className="card-title-row">
        <h3>{label}</h3>
        <span className={statusBadgeClass(component.status)}>{component.status}</span>
      </div>
      {component.backend && (
        <p className="card-meta">
          <span className="mono-chip">{component.backend}</span>
        </p>
      )}
      {component.detail && <p className="card-reason">{component.detail}</p>}
      {typeof component.chunks === "number" && <p className="card-reason">{component.chunks} indexed chunks</p>}
    </article>
  );
}

export function DiagnosticsView() {
  const [report, setReport] = useState<DiagnosticsReport | null>(null);
  const [backups, setBackups] = useState<BackupManifest[]>([]);
  const [loading, setLoading] = useState(true);
  const [creatingBackup, setCreatingBackup] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [diagnosticsReport, backupList] = await Promise.all([fetchDiagnostics(), listBackups()]);
      setReport(diagnosticsReport);
      setBackups(backupList);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }, []);

  async function handleCreateBackup() {
    setCreatingBackup(true);
    setError(null);
    try {
      await createBackup();
      setBackups(await listBackups());
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setCreatingBackup(false);
    }
  }

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
        Live status of every service this app depends on — not just whether the app opened, but whether the
        database, background scheduler, vector search, and credential storage actually work right now.
      </p>
      <ErrorBanner message={error} />

      {report && (
        <div className="card-list">
          <ComponentCard label="Backend" component={report.components.backend} />
          <ComponentCard label="Database" component={report.components.database} />
          <ComponentCard label="Runtime state" component={report.components.runtime_state} />
          <ComponentCard label="Scheduler" component={report.components.scheduler} />
          <ComponentCard label="Vector store" component={report.components.vector_store} />
          <ComponentCard label="Credential store" component={report.components.credential_store} />

          <article className="card">
            <div className="card-title-row">
              <h3>Kill switch</h3>
              <span className={report.components.kill_switch.paused ? "badge badge-rejected" : "badge badge-approved"}>
                {report.components.kill_switch.paused ? "Paused" : "Active"}
              </span>
            </div>
            {report.components.kill_switch.paused && report.components.kill_switch.reason && (
              <p className="card-reason">
                {report.components.kill_switch.reason}
                {report.components.kill_switch.paused_by ? ` — paused by ${report.components.kill_switch.paused_by}` : ""}
              </p>
            )}
          </article>

          <article className="card">
            <div className="card-title-row">
              <h3>Backups</h3>
              {report.mode === "desktop" && (
                <button type="button" onClick={() => void handleCreateBackup()} disabled={creatingBackup}>
                  {creatingBackup ? "Backing up…" : "Back up now"}
                </button>
              )}
            </div>
            {report.mode !== "desktop" ? (
              <p className="card-reason">
                Hosted deployments back up PostgreSQL and Redis at the infrastructure level — ask your database
                operator about their backup process.
              </p>
            ) : backups.length === 0 ? (
              <p className="card-reason">
                No backups yet. A backup copies your database and search index into this installation's backups
                folder — restoring means closing the app and copying those files back, so keep this button for
                before risky changes, not as your only safety net.
              </p>
            ) : (
              <ul className="backup-list">
                {backups.map((backup) => (
                  <li key={backup.name} className="card-reason">
                    {backup.created_at} — {formatBytes(backup.size_bytes)}
                    {!backup.includes_database && " (no database yet)"}
                  </li>
                ))}
              </ul>
            )}
          </article>
        </div>
      )}
    </section>
  );
}
