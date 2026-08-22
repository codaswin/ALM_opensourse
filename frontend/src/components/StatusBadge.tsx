const STATUS_CLASS: Record<string, string> = {
  // ApprovalRequest.status (backend/app/safety/approval_gate.py's
  // ApprovalStatusLiteral): pending, executing, succeeded, failed, rejected.
  pending: "badge badge-pending",
  executing: "badge badge-pending",
  succeeded: "badge badge-approved",
  failed: "badge badge-rejected",
  rejected: "badge badge-rejected",
  // LearningProposal.status (backend/app/learning/proposal_review.py's
  // ProposalStatusLiteral): pending, approved, rejected, auto_applied.
  approved: "badge badge-approved",
  auto_applied: "badge badge-approved",
  // Not currently used by either status enum above, kept for callers that
  // may pass a raw ToolExecutionResult.status through this component.
  success: "badge badge-approved",
  error: "badge badge-rejected",
  timeout: "badge badge-rejected",
  blocked: "badge badge-rejected",
};

export function StatusBadge({ status }: { status: string }) {
  return <span className={STATUS_CLASS[status] ?? "badge"}>{status.replace(/_/g, " ")}</span>;
}
