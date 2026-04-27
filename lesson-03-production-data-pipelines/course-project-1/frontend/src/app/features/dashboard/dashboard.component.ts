import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DashboardService } from '../../core/services/dashboard.service';
import { DashboardSummary, Dock, Staff, AgentLog, TimelineEntry } from '../../core/models/models';
import { SummaryCardsComponent } from './summary-cards/summary-cards.component';
import { DockPanelComponent } from './dock-panel/dock-panel.component';
import { TruckQueueComponent } from './truck-queue/truck-queue.component';
import { StaffStatusComponent } from './staff-status/staff-status.component';
import { AgentLogComponent } from './agent-log/agent-log.component';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, SummaryCardsComponent, DockPanelComponent, TruckQueueComponent, StaffStatusComponent, AgentLogComponent],
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.scss',
})
export class DashboardComponent implements OnInit, OnDestroy {
  summary: DashboardSummary | null = null;
  docks: Dock[] = [];
  staff: Staff[] = [];
  agentLogs: AgentLog[] = [];
  timeline: TimelineEntry[] = [];
  activeTab: 'staff' | 'logs' = 'staff';

  constructor(private dashboardService: DashboardService) {}

  ngOnInit(): void {
    this.dashboardService.startPolling(5000);
    this.dashboardService.summary$.subscribe(s => this.summary = s);
    this.dashboardService.docks$.subscribe(d => this.docks = d);
    this.dashboardService.staff$.subscribe(s => this.staff = s);
    this.dashboardService.agentLogs$.subscribe(l => this.agentLogs = l);
    this.dashboardService.timeline$.subscribe(t => this.timeline = t);
  }

  ngOnDestroy(): void {
    this.dashboardService.stopPolling();
  }
}
