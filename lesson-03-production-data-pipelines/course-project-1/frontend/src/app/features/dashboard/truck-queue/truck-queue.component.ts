import { Component, Input } from '@angular/core';
import { CommonModule, DatePipe } from '@angular/common';
import { TimelineEntry } from '../../../core/models/models';

@Component({
  selector: 'app-truck-queue',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="card">
      <div class="card-header">Truck Queue</div>

      <div class="section" *ngIf="waitingTrucks.length > 0">
        <div class="section-label">Waiting ({{ waitingTrucks.length }})</div>
        <div *ngFor="let t of waitingTrucks" class="truck-item waiting">
          <span class="plate">{{ t.truck_license_plate }}</span>
          <span class="time">arrived {{ t.actual_arrival | date:'HH:mm' }}</span>
        </div>
      </div>

      <div class="section" *ngIf="unloadingTrucks.length > 0">
        <div class="section-label">Unloading ({{ unloadingTrucks.length }})</div>
        <div *ngFor="let t of unloadingTrucks" class="truck-item unloading">
          <span class="plate">{{ t.truck_license_plate }}</span>
          <span class="dock">{{ t.dock_code }}</span>
        </div>
      </div>

      <div class="section" *ngIf="plannedTrucks.length > 0">
        <div class="section-label">En Route ({{ plannedTrucks.length }})</div>
        <div *ngFor="let t of plannedTrucks" class="truck-item planned">
          <span class="plate">{{ t.truck_license_plate }}</span>
          <span class="time">ETA {{ t.expected_arrival | date:'HH:mm' }}</span>
        </div>
      </div>

      <div *ngIf="waitingTrucks.length === 0 && unloadingTrucks.length === 0 && plannedTrucks.length === 0"
           class="empty">No trucks in queue</div>
    </div>
  `,
  styles: [`
    .section { margin-bottom: 12px; }
    .section-label { font-size: 12px; font-weight: 600; color: #666; text-transform: uppercase; margin-bottom: 6px; }
    .truck-item {
      display: flex; justify-content: space-between; align-items: center;
      padding: 6px 10px; border-radius: 4px; margin-bottom: 4px; font-size: 13px;
    }
    .plate { font-weight: 600; }
    .time { color: #888; font-size: 12px; }
    .dock { color: #1a237e; font-weight: 500; font-size: 12px; }
    .waiting { background: #fff3e0; border-left: 3px solid #ff9800; }
    .unloading { background: #f3e5f5; border-left: 3px solid #9c27b0; }
    .planned { background: #e3f2fd; border-left: 3px solid #2196f3; }
    .empty { color: #999; text-align: center; padding: 20px; font-style: italic; }
  `]
})
export class TruckQueueComponent {
  @Input() timeline: TimelineEntry[] = [];

  get waitingTrucks(): TimelineEntry[] {
    return this.timeline.filter(t => t.status === 'arrived');
  }
  get unloadingTrucks(): TimelineEntry[] {
    return this.timeline.filter(t => t.status === 'in_progress');
  }
  get plannedTrucks(): TimelineEntry[] {
    return this.timeline.filter(t => t.status === 'planned');
  }
}
