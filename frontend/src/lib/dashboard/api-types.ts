import type { AppRole } from "@/lib/dashboard/nav";

export type RiskLevel = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export type ReviewStatus =
  | "OPEN"
  | "IN_REVIEW"
  | "APPROVED"
  | "CORRECTED"
  | "REJECTED"
  | "TRANSFERRED";

export type DocumentStatus =
  | "UPLOADED"
  | "PARSED"
  | "PENDING_REVIEW"
  | "APPROVED"
  | "DISABLED";

export type AttackType =
  | "PROMPT_INJECTION"
  | "ROLE_ESCALATION"
  | "DATA_EXFILTRATION"
  | "MALICIOUS_FILE"
  | "RATE_ABUSE"
  | string;

export interface AnswerCardData {
  procedureTitle: string;
  steps: string[];
  requiredDocuments: string[];
  competentAdministration: string;
  sources: string[];
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system";
  text?: string;
  answerCard?: AnswerCardData;
}

export interface ConversationSummary {
  id: string;
  title: string;
  updatedAt: string;
  messageCount: number;
}

export interface ProcedureSummary {
  id: string;
  title: string;
}

export interface ReviewCase {
  id: string;
  questionSummary: string;
  question: string;
  proposedAnswer: string;
  legalEvidence: string[];
  risk: RiskLevel;
  status: ReviewStatus;
  serviceName: string;
  requestedBy: string;
  createdAt: string;
}

export interface DocumentItem {
  id: string;
  title: string;
  fileName: string;
  fileType: "pdf" | "docx" | "txt" | string;
  sizeMb: number;
  status: DocumentStatus;
  uploadedAt: string;
  extractedPreview: string;
}

export interface UserRow {
  id: string;
  email: string;
  fullName: string;
  roles: AppRole[];
  disabled: boolean;
  createdAt: string;
}

export interface AuditEventRow {
  id: string;
  action: string;
  actor: string;
  entity: string;
  detail: string;
  createdAt: string;
}

export interface SecurityIncident {
  id: string;
  attackType: AttackType;
  risk: RiskLevel;
  decision: "ALLOW" | "RESTRICT" | "REVIEW" | "BLOCK";
  sourceIp: string;
  createdAt: string;
  reason: string;
  hasConversationContent: boolean;
  conversationContent?: string | null;
}

export interface BlockedRequest {
  id: string;
  attackType: AttackType;
  route: string;
  createdAt: string;
}

export interface RedTeamReport {
  id: string;
  filename?: string;
  scenario?: string;
  result?: "BLOCKED" | "PARTIAL" | "FAILED";
  runAt?: string;
  details?: string;
  verdict?: string;
  generated_at?: string;
  failures?: number;
  total?: number;
  cases?: {
    case: string;
    decision: string;
    expected: string;
    status: string;
    layer2: string;
  }[];
  content?: string;
}

export interface WorkflowExecution {
  id: string;
  workflow: string;
  status: "SUCCESS" | "ERROR" | "RUNNING";
  durationMs: number;
  startedAt: string;
}

export interface Kpis {
  users: number;
  requestsToday: number;
  blockedRequests: number;
  workflowErrors: number;
  requestsPerDay: { day: string; count: number }[];
  blockedByAttack: { type: AttackType; count: number }[];
}

export interface PermissionEntry {
  id: string;
  agent: string;
  tool: string;
  operation: "execute";
  allowed: boolean;
}
