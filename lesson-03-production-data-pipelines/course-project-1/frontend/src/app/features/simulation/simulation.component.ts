import { Component, OnInit } from '@angular/core';
import { CommonModule, DatePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../core/services/api.service';

@Component({
  selector: 'app-simulation',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="grid-2">
      <div class="card">
        <div class="card-header">Simulation Control</div>

        <div class="section">
          <label>Scenario</label>
          <div class="scenario-buttons">
            <button class="btn btn-primary" (click)="loadScenario('normal_day')" [disabled]="loading">
              Normal Day (20 trucks)
            </button>
            <button class="btn btn-warning" (click)="loadScenario('peak_overload')" [disabled]="loading">
              Peak Overload (40 trucks)
            </button>
            <button class="btn btn-danger" (click)="loadScenario('late_arrivals')" [disabled]="loading">
              Late Arrivals (15 trucks)
            </button>
          </div>
        </div>

        <div class="section">
          <label>Advance Time</label>
          <div class="tick-controls">
            <button class="btn btn-primary btn-sm" (click)="tick(15)" [disabled]="loading">+15 min</button>
            <button class="btn btn-primary btn-sm" (click)="tick(30)" [disabled]="loading">+30 min</button>
            <button class="btn btn-primary btn-sm" (click)="tick(60)" [disabled]="loading">+1 hour</button>
            <button class="btn btn-primary btn-sm" (click)="tick(120)" [disabled]="loading">+2 hours</button>
            <button class="btn btn-primary btn-sm" (click)="tick(360)" [disabled]="loading">+6 hours</button>
          </div>
          <div class="custom-tick">
            <input type="number" [(ngModel)]="customMinutes" min="1" max="1440" placeholder="Minutes">
            <button class="btn btn-primary btn-sm" (click)="tick(customMinutes)" [disabled]="loading">Advance</button>
          </div>
        </div>

        <div class="section">
          <label>Agent Triggers</label>
          <div class="agent-buttons">
            <button class="btn btn-sm btn-primary" (click)="triggerAgent('coordinator')">Coordinator</button>
            <button class="btn btn-sm btn-primary" (click)="triggerAgent('alert')">Alert Check</button>
            <button class="btn btn-sm btn-primary" (click)="triggerAgent('shift_planner')">Plan Shifts</button>
            <button class="btn btn-sm btn-primary" (click)="triggerAgent('forecasting')">Forecast</button>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="card-header">Status</div>
        <div class="status-info">
          <div class="status-item">
            <span class="label">Current Time:</span>
            <span class="value">{{ currentTime || 'Not set' }}</span>
          </div>
          <div class="status-item" *ngIf="lastScenario">
            <span class="label">Scenario:</span>
            <span class="value">{{ lastScenario }}</span>
          </div>
          <div class="status-item" *ngIf="lastTickResult">
            <span class="label">Last Tick Events:</span>
            <span class="value">{{ lastTickResult.events.length }} truck arrivals</span>
          </div>
          <div class="status-item" *ngIf="lastTickResult">
            <span class="label">Staff On Shift:</span>
            <span class="value">{{ lastTickResult.staff_on_shift }}</span>
          </div>
        </div>

        <div class="event-log" *ngIf="eventLog.length > 0">
          <div class="card-header" style="margin-top: 16px">Event Log</div>
          <div *ngFor="let e of eventLog" class="event-entry">{{ e }}</div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .section { margin-bottom: 20px;
      label { display: block; font-weight: 600; margin-bottom: 8px; color: #666; text-transform: uppercase; font-size: 12px; }
    }
    .scenario-buttons, .tick-controls, .agent-buttons { display: flex; gap: 8px; flex-wrap: wrap; }
    .custom-tick { display: flex; gap: 8px; margin-top: 8px;
      input { width: 100px; padding: 6px 10px; border: 1px solid #ddd; border-radius: 4px; }
    }
    .status-info { display: flex; flex-direction: column; gap: 8px; }
    .status-item { display: flex; gap: 8px;
      .label { font-weight: 600; color: #666; min-width: 140px; }
      .value { color: #1a237e; font-weight: 500; }
    }
    .event-log { max-height: 300px; overflow-y: auto; }
    .event-entry { font-size: 12px; padding: 4px 8px; border-bottom: 1px solid #f0f0f0; font-family: monospace; }
  `]
})
export class SimulationComponent implements OnInit {
  currentTime: string = '';
  lastScenario: string = '';
  lastTickResult: any = null;
  loading = false;
  customMinutes = 30;
  eventLog: string[] = [];

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.api.getClock().subscribe(c => {
      this.currentTime = new Date(c.current_time).toLocaleString('uk-UA');
    });
  }

  loadScenario(name: string): void {
    this.loading = true;
    this.eventLog = [];
    this.api.loadScenario(name).subscribe(r => {
      this.lastScenario = `${r.scenario} - ${r.description}`;
      this.currentTime = new Date(r.current_time).toLocaleString('uk-UA');
      this.eventLog.push(`Loaded scenario: ${r.scenario}, ${r.trucks_scheduled} trucks scheduled`);
      this.loading = false;
    });
  }

  tick(minutes: number): void {
    this.loading = true;
    this.api.tick(minutes).subscribe(r => {
      this.currentTime = new Date(r.current_time).toLocaleString('uk-UA');
      this.lastTickResult = r;
      this.eventLog.push(`+${minutes}min -> ${this.currentTime}: ${r.events.length} arrivals, ${r.staff_on_shift} on shift`);
      this.loading = false;
    });
  }

  triggerAgent(name: string): void {
    this.api.triggerAgent(name).subscribe(() => {
      this.eventLog.push(`Triggered agent: ${name}`);
    });
  }
}
