import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Dock, TimelineEntry } from '../../../core/models/models';

@Component({
  selector: 'app-dock-panel',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="card">
      <div class="card-header">Docks</div>
      <div class="docks-grid">
        <div *ngFor="let dock of docks" class="dock-card" [class]="'dock-' + dock.status">
          <div class="dock-code">{{ dock.code }}</div>
          <div class="dock-type">{{ dock.dock_type }}</div>
          <div class="dock-status">{{ dock.status | uppercase }}</div>
          <div class="dock-truck" *ngIf="getTruckAtDock(dock.code) as truck">
            {{ truck.truck_license_plate }}
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .docks-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
      gap: 12px;
    }
    .dock-card {
      border: 2px solid #e0e0e0;
      border-radius: 8px;
      padding: 12px;
      text-align: center;
      transition: all 0.3s;
    }
    .dock-code { font-size: 18px; font-weight: 700; }
    .dock-type { font-size: 11px; color: #888; margin: 2px 0; }
    .dock-status { font-size: 12px; font-weight: 600; margin: 4px 0; }
    .dock-truck { font-size: 13px; font-weight: 500; color: #1a237e; margin-top: 4px; }
    .dock-free { border-color: #4caf50; background: #e8f5e9; .dock-status { color: #4caf50; } }
    .dock-occupied { border-color: #f44336; background: #ffebee; .dock-status { color: #f44336; } }
    .dock-maintenance { border-color: #ff9800; background: #fff3e0; .dock-status { color: #ff9800; } }
  `]
})
export class DockPanelComponent {
  @Input() docks: Dock[] = [];
  @Input() timeline: TimelineEntry[] = [];

  getTruckAtDock(dockCode: string): TimelineEntry | undefined {
    return this.timeline.find(t => t.dock_code === dockCode && t.status === 'in_progress');
  }
}
