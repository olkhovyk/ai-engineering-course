import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService } from '../../core/services/api.service';
import { Staff, Shift } from '../../core/models/models';

@Component({
  selector: 'app-staff-management',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="grid-2">
      <div class="card">
        <div class="card-header">Staff</div>
        <table>
          <thead><tr><th>Name</th><th>Role</th><th>Status</th><th>Phone</th></tr></thead>
          <tbody>
            <tr *ngFor="let s of staff">
              <td>{{ s.full_name }}</td>
              <td>{{ s.role === 'loader' ? 'Loader' : 'Forklift' }}</td>
              <td><span [class]="'status-' + s.status">{{ s.status }}</span></td>
              <td>{{ s.phone || '-' }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="card">
        <div class="card-header">Active Shifts</div>
        <table>
          <thead><tr><th>Staff ID</th><th>Date</th><th>Start</th><th>End</th><th>Created By</th></tr></thead>
          <tbody>
            <tr *ngFor="let s of shifts">
              <td>{{ s.staff_id }}</td>
              <td>{{ s.shift_date }}</td>
              <td>{{ s.start_time }}</td>
              <td>{{ s.end_time }}</td>
              <td>{{ s.created_by }}</td>
            </tr>
          </tbody>
        </table>
        <div *ngIf="shifts.length === 0" style="text-align: center; padding: 20px; color: #999">No active shifts</div>
      </div>
    </div>
  `,
})
export class StaffManagementComponent implements OnInit {
  staff: Staff[] = [];
  shifts: Shift[] = [];

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.api.getStaff().subscribe(s => this.staff = s);
    this.api.getActiveShifts().subscribe(s => this.shifts = s);
  }
}
