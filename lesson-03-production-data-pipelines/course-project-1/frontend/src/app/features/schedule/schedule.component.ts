import { Component, OnInit } from '@angular/core';
import { CommonModule, DatePipe } from '@angular/common';
import { ApiService } from '../../core/services/api.service';
import { Schedule } from '../../core/models/models';

@Component({
  selector: 'app-schedule',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="card">
      <div class="card-header">Today's Delivery Schedule</div>
      <table>
        <thead>
          <tr>
            <th>#</th>
            <th>Expected</th>
            <th>Actual</th>
            <th>Status</th>
            <th>Unload (min)</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr *ngFor="let s of schedules">
            <td>{{ s.id }}</td>
            <td>{{ s.expected_arrival | date:'HH:mm' }}</td>
            <td>{{ s.actual_arrival ? (s.actual_arrival | date:'HH:mm') : '-' }}</td>
            <td><span [class]="'status-' + s.status">{{ s.status }}</span></td>
            <td>{{ s.estimated_unload_minutes }}</td>
            <td>
              <button class="btn btn-warning btn-sm" *ngIf="s.status === 'arrived'" (click)="markArrived(s.id)" disabled>Arrived</button>
              <button class="btn btn-warning btn-sm" *ngIf="s.status === 'planned'" (click)="markArrived(s.id)">Mark Arrived</button>
              <button class="btn btn-success btn-sm" *ngIf="s.status === 'in_progress'" (click)="markCompleted(s.id)">Complete</button>
              <span *ngIf="s.status === 'completed'" class="status-completed">Done</span>
            </td>
          </tr>
        </tbody>
      </table>
      <div *ngIf="schedules.length === 0" style="text-align: center; padding: 20px; color: #999">
        No schedules. Load a scenario first.
      </div>
    </div>
  `,
})
export class ScheduleComponent implements OnInit {
  schedules: Schedule[] = [];

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.api.getTodaySchedules().subscribe(s => this.schedules = s);
  }

  markArrived(id: number): void {
    this.api.markArrived(id).subscribe(() => this.load());
  }

  markCompleted(id: number): void {
    this.api.markCompleted(id).subscribe(() => this.load());
  }
}
