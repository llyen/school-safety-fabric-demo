import { ReportDecision } from './ReportDecision.js';
import { EscalationDecision } from './EscalationDecision.js';
import { TaskStatus } from './TaskStatus.js';
import { CommsDraft } from './CommsDraft.js';

export type AppSchema = {
  ReportDecision: ReportDecision;
  EscalationDecision: EscalationDecision;
  TaskStatus: TaskStatus;
  CommsDraft: CommsDraft;
};

export const schema = [ReportDecision, EscalationDecision, TaskStatus, CommsDraft];
