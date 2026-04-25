import { Routes } from '@angular/router';
import { DashboardComponent } from './dashboard/dashboard.component';
import { ApisComponent } from './apis/apis.component';
import { IssuesComponent } from './issues/issues.component';
import { ChatComponent } from './chat/chat.component';
import { AlertsComponent } from './alerts/alerts.component';

export const routes: Routes = [
  { path: '', pathMatch: 'full', redirectTo: 'dashboard' },
  { path: 'dashboard', component: DashboardComponent },
  { path: 'alerts', component: AlertsComponent },
  { path: 'apis', component: ApisComponent },
  { path: 'issues', component: IssuesComponent },
  { path: 'chat', component: ChatComponent },
];
