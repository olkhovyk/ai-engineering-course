import { Component, Input } from '@angular/core';
import { CommonModule, DatePipe } from '@angular/common';
import { AgentLog } from '../../../core/models/models';

@Component({
  selector: 'app-agent-log',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="log-list">
      <div *ngFor="let log of logs" class="log-entry" [class]="'severity-bg-' + log.severity">
        <span class="time">{{ log.created_at | date:'HH:mm:ss' }}</span>
        <span class="agent">[{{ log.agent_name | uppercase }}]</span>
        <span [class]="'severity-' + log.severity" class="severity-tag">{{ log.severity | uppercase }}</span>
        <span class="message">{{ log.message }}</span>
      </div>
      <div *ngIf="logs.length === 0" class="empty">No agent activity yet. Load a scenario and advance time.</div>
    </div>
  `,
  styles: [`
    .log-list { max-height: 400px; overflow-y: auto; }
    .log-entry {
      display: flex; align-items: flex-start; gap: 8px;
      padding: 6px 10px; border-bottom: 1px solid #f0f0f0; font-size: 13px;
    }
    .time { color: #888; min-width: 65px; font-family: monospace; }
    .agent { font-weight: 600; min-width: 120px; color: #1a237e; }
    .severity-tag { font-size: 11px; font-weight: 600; min-width: 60px; }
    .message { flex: 1; }
    .severity-bg-warning { background: #fffde7; }
    .severity-bg-critical { background: #ffebee; }
    .empty { color: #999; text-align: center; padding: 20px; font-style: italic; }
  `]
})
export class AgentLogComponent {
  @Input() logs: AgentLog[] = [];
}
