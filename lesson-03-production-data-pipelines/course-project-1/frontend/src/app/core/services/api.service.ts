import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import {
  Dock, Truck, Staff, Shift, Schedule, Assignment,
  AgentLog, Notification, DashboardSummary, TimelineEntry,
  SimulationClock, TickResult, ScenarioResult
} from '../models/models';

@Injectable({ providedIn: 'root' })
export class ApiService {
  private base = '/api/v1';

  constructor(private http: HttpClient) {}

  // Dashboard
  getDashboardSummary(): Observable<DashboardSummary> {
    return this.http.get<DashboardSummary>(`${this.base}/dashboard/summary`);
  }

  getTimeline(): Observable<TimelineEntry[]> {
    return this.http.get<TimelineEntry[]>(`${this.base}/dashboard/timeline`);
  }

  // Docks
  getDocks(): Observable<Dock[]> {
    return this.http.get<Dock[]>(`${this.base}/docks`);
  }

  // Trucks
  getTrucks(status?: string): Observable<Truck[]> {
    let params = new HttpParams();
    if (status) params = params.set('status', status);
    return this.http.get<Truck[]>(`${this.base}/trucks`, { params });
  }

  // Staff
  getStaff(): Observable<Staff[]> {
    return this.http.get<Staff[]>(`${this.base}/staff`);
  }

  // Shifts
  getActiveShifts(): Observable<Shift[]> {
    return this.http.get<Shift[]>(`${this.base}/shifts/active`);
  }

  getShifts(date?: string): Observable<Shift[]> {
    let params = new HttpParams();
    if (date) params = params.set('shift_date', date);
    return this.http.get<Shift[]>(`${this.base}/shifts`, { params });
  }

  // Schedules
  getTodaySchedules(): Observable<Schedule[]> {
    return this.http.get<Schedule[]>(`${this.base}/schedules/today`);
  }

  markArrived(scheduleId: number): Observable<Schedule> {
    return this.http.post<Schedule>(`${this.base}/schedules/${scheduleId}/arrive`, {});
  }

  markCompleted(scheduleId: number): Observable<Schedule> {
    return this.http.post<Schedule>(`${this.base}/schedules/${scheduleId}/complete`, {});
  }

  // Assignments
  getActiveAssignments(): Observable<Assignment[]> {
    return this.http.get<Assignment[]>(`${this.base}/assignments/active`);
  }

  // Agent logs
  getAgentLogs(limit: number = 50): Observable<AgentLog[]> {
    return this.http.get<AgentLog[]>(`${this.base}/agents/logs`, { params: { limit: limit.toString() } });
  }

  triggerAgent(name: string): Observable<any> {
    return this.http.post(`${this.base}/agents/trigger/${name}`, {});
  }

  // Notifications
  getNotifications(): Observable<Notification[]> {
    return this.http.get<Notification[]>(`${this.base}/notifications`);
  }

  markNotificationRead(id: number): Observable<any> {
    return this.http.patch(`${this.base}/notifications/${id}/read`, {});
  }

  markAllRead(): Observable<any> {
    return this.http.patch(`${this.base}/notifications/read-all`, {});
  }

  // Simulation
  getClock(): Observable<SimulationClock> {
    return this.http.get<SimulationClock>(`${this.base}/simulation/clock`);
  }

  tick(minutes: number): Observable<TickResult> {
    return this.http.post<TickResult>(`${this.base}/simulation/tick`, null, { params: { minutes: minutes.toString() } });
  }

  loadScenario(name: string): Observable<ScenarioResult> {
    return this.http.post<ScenarioResult>(`${this.base}/simulation/scenario/${name}`, {});
  }

  seedDatabase(): Observable<any> {
    return this.http.post(`${this.base}/simulation/seed`, {});
  }
}
