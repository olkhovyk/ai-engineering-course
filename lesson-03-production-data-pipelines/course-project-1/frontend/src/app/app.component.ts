import { Component } from '@angular/core';
import { RouterOutlet, RouterLink, RouterLinkActive } from '@angular/router';
import { CommonModule } from '@angular/common';
import { ApiService } from './core/services/api.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, RouterOutlet, RouterLink, RouterLinkActive],
  templateUrl: './app.component.html',
  styleUrl: './app.component.scss'
})
export class AppComponent {
  title = 'DC Multi-Agent System';
  notificationCount = 0;

  constructor(private api: ApiService) {
    this.loadNotificationCount();
    setInterval(() => this.loadNotificationCount(), 10000);
  }

  loadNotificationCount(): void {
    this.api.getDashboardSummary().subscribe(s => {
      this.notificationCount = s.unread_notifications;
    });
  }
}
