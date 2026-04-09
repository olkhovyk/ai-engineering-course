import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DashboardSummary } from '../../../core/models/models';

@Component({
  selector: 'app-summary-cards',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="grid-4" *ngIf="summary">
      <div class="card summary-card">
        <div class="label">Trucks Today</div>
        <div class="value">{{ summary.total_trucks_today }}</div>
        <div class="details">
          <span class="status-arrived">{{ summary.trucks_waiting }} waiting</span> |
          <span class="status-in_progress">{{ summary.trucks_unloading }} unloading</span> |
          <span class="status-completed">{{ summary.trucks_completed }} done</span>
        </div>
      </div>
      <div class="card summary-card">
        <div class="label">Docks</div>
        <div class="value">{{ summary.docks_occupied }}/{{ summary.docks_total }}</div>
        <div class="details">
          <span class="status-occupied">{{ summary.docks_occupied }} occupied</span> |
          <span class="status-free">{{ summary.docks_free }} free</span>
        </div>
      </div>
      <div class="card summary-card">
        <div class="label">Staff</div>
        <div class="value">{{ summary.staff_available }} avail</div>
        <div class="details">
          <span class="status-busy">{{ summary.staff_busy }} busy</span> |
          <span class="status-off_duty">{{ summary.staff_off_duty }} off</span>
        </div>
      </div>
      <div class="card summary-card">
        <div class="label">Alerts Today</div>
        <div class="value" [class.severity-warning]="summary.alerts_today > 0">{{ summary.alerts_today }}</div>
        <div class="details">
          <span>{{ summary.unread_notifications }} unread notifications</span>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .summary-card {
      text-align: center;
      .label { font-size: 13px; color: #666; text-transform: uppercase; font-weight: 600; }
      .value { font-size: 32px; font-weight: 700; color: #1a237e; margin: 4px 0; }
      .details { font-size: 12px; color: #888; }
    }
  `]
})
export class SummaryCardsComponent {
  @Input() summary: DashboardSummary | null = null;
}
