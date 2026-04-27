import { Routes } from '@angular/router';

export const routes: Routes = [
  { path: '', redirectTo: 'dashboard', pathMatch: 'full' },
  {
    path: 'dashboard',
    loadComponent: () => import('./features/dashboard/dashboard.component').then(m => m.DashboardComponent),
  },
  {
    path: 'schedule',
    loadComponent: () => import('./features/schedule/schedule.component').then(m => m.ScheduleComponent),
  },
  {
    path: 'staff',
    loadComponent: () => import('./features/staff-management/staff-management.component').then(m => m.StaffManagementComponent),
  },
  {
    path: 'notifications',
    loadComponent: () => import('./features/notifications/notifications.component').then(m => m.NotificationsComponent),
  },
  {
    path: 'simulation',
    loadComponent: () => import('./features/simulation/simulation.component').then(m => m.SimulationComponent),
  },
];
