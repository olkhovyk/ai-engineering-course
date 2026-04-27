import { Component, OnInit } from '@angular/core';
import { CommonModule, DatePipe } from '@angular/common';
import { ApiService } from '../../core/services/api.service';
import { Notification } from '../../core/models/models';

@Component({
  selector: 'app-notifications',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="card">
      <div class="card-header" style="display: flex; justify-content: space-between; align-items: center;">
        <span>Notifications</span>
        <button class="btn btn-primary btn-sm" (click)="markAllRead()">Mark All Read</button>
      </div>
      <div *ngFor="let n of notifications" class="notification-item" [class.unread]="!n.is_read">
        <div class="notification-header">
          <span [class]="'severity-' + n.severity" class="severity-badge">{{ n.severity | uppercase }}</span>
          <span class="title">{{ n.title }}</span>
          <span class="time">{{ n.created_at | date:'HH:mm:ss' }}</span>
        </div>
        <div class="body">{{ n.body }}</div>
        <div class="source" *ngIf="n.source_agent">Agent: {{ n.source_agent }}</div>
        <button *ngIf="!n.is_read" class="btn btn-sm btn-primary" (click)="markRead(n.id)">Mark Read</button>
      </div>
      <div *ngIf="notifications.length === 0" style="text-align: center; padding: 20px; color: #999">
        No notifications
      </div>
    </div>
  `,
  styles: [`
    .notification-item {
      padding: 12px; border-bottom: 1px solid #e0e0e0;
      &.unread { background: #e3f2fd; }
    }
    .notification-header { display: flex; gap: 10px; align-items: center; margin-bottom: 4px; }
    .severity-badge { font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 3px; }
    .title { font-weight: 600; flex: 1; }
    .time { color: #888; font-size: 12px; }
    .body { font-size: 13px; color: #555; margin: 4px 0; }
    .source { font-size: 11px; color: #888; margin-bottom: 4px; }
  `]
})
export class NotificationsComponent implements OnInit {
  notifications: Notification[] = [];

  constructor(private api: ApiService) {}

  ngOnInit(): void { this.load(); }

  load(): void {
    this.api.getNotifications().subscribe(n => this.notifications = n);
  }

  markRead(id: number): void {
    this.api.markNotificationRead(id).subscribe(() => this.load());
  }

  markAllRead(): void {
    this.api.markAllRead().subscribe(() => this.load());
  }
}
