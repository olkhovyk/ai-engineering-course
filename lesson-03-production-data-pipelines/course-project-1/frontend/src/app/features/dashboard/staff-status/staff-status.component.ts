import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Staff } from '../../../core/models/models';

@Component({
  selector: 'app-staff-status',
  standalone: true,
  imports: [CommonModule],
  template: `
    <table>
      <thead>
        <tr>
          <th>Name</th>
          <th>Role</th>
          <th>Status</th>
          <th>Phone</th>
        </tr>
      </thead>
      <tbody>
        <tr *ngFor="let s of staff">
          <td>{{ s.full_name }}</td>
          <td>{{ s.role === 'loader' ? 'Loader' : 'Forklift Operator' }}</td>
          <td><span [class]="'status-' + s.status">{{ s.status }}</span></td>
          <td>{{ s.phone || '-' }}</td>
        </tr>
      </tbody>
    </table>
    <div *ngIf="staff.length === 0" class="empty">No staff data</div>
  `,
  styles: [`.empty { color: #999; text-align: center; padding: 20px; font-style: italic; }`]
})
export class StaffStatusComponent {
  @Input() staff: Staff[] = [];
}
