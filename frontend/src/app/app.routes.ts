import { Routes } from '@angular/router';
import { authGuard, guestGuard } from './auth/auth.guard';
import { MainLayoutComponent } from './main-layout/main-layout.component';
import { DashboardComponent } from './dashboard/dashboard.component';
import { ApisComponent } from './apis/apis.component';
import { IssuesComponent } from './issues/issues.component';
import { ChatComponent } from './chat/chat.component';
import { AlertsComponent } from './alerts/alerts.component';
import { ProjectsComponent } from './projects/projects.component';
import { ActionsComponent } from './actions/actions.component';
import { SettingsComponent } from './settings/settings.component';
import { ProfileComponent } from './settings/profile.component';
import { LoginComponent } from './auth/login.component';
import { RegisterComponent } from './auth/register.component';
import { EvolutionComponent } from './evolution/evolution.component';
import { SystemMapComponent } from './system-map/system-map.component';

export const routes: Routes = [
  { path: 'login', component: LoginComponent, canActivate: [guestGuard] },
  { path: 'register', component: RegisterComponent, canActivate: [guestGuard] },
  {
    path: '',
    component: MainLayoutComponent,
    canActivate: [authGuard],
    children: [
      { path: '', pathMatch: 'full', redirectTo: 'dashboard' },
      { path: 'dashboard', component: DashboardComponent },
      { path: 'alerts', component: AlertsComponent },
      { path: 'apis', component: ApisComponent },
      { path: 'issues', component: IssuesComponent },
      { path: 'chat', component: ChatComponent },
      { path: 'projects', component: ProjectsComponent },
      { path: 'actions', component: ActionsComponent },
      { path: 'evolution', component: EvolutionComponent },
      { path: 'system-map', component: SystemMapComponent },
      { path: 'settings/profile', component: ProfileComponent },
      { path: 'settings', component: SettingsComponent },
    ],
  },
];
