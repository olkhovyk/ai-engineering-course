import { Injectable, OnDestroy } from '@angular/core';
import { BehaviorSubject, interval, Subscription, switchMap } from 'rxjs';
import { ApiService } from './api.service';
import { DashboardSummary, Dock, Staff, AgentLog, TimelineEntry } from '../models/models';

@Injectable({ providedIn: 'root' })
export class DashboardService implements OnDestroy {
  summary$ = new BehaviorSubject<DashboardSummary | null>(null);
  docks$ = new BehaviorSubject<Dock[]>([]);
  staff$ = new BehaviorSubject<Staff[]>([]);
  agentLogs$ = new BehaviorSubject<AgentLog[]>([]);
  timeline$ = new BehaviorSubject<TimelineEntry[]>([]);

  private polling: Subscription | null = null;

  constructor(private api: ApiService) {}

  startPolling(intervalMs: number = 5000): void {
    this.refresh();
    this.polling = interval(intervalMs).subscribe(() => this.refresh());
  }

  stopPolling(): void {
    this.polling?.unsubscribe();
    this.polling = null;
  }

  refresh(): void {
    this.api.getDashboardSummary().subscribe(s => this.summary$.next(s));
    this.api.getDocks().subscribe(d => this.docks$.next(d));
    this.api.getStaff().subscribe(s => this.staff$.next(s));
    this.api.getAgentLogs(50).subscribe(l => this.agentLogs$.next(l));
    this.api.getTimeline().subscribe(t => this.timeline$.next(t));
  }

  ngOnDestroy(): void {
    this.stopPolling();
  }
}
