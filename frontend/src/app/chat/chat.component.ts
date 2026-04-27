import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { take } from 'rxjs/operators';
import { IntellisysApiService } from '../intellisys-api.service';

@Component({
  selector: 'app-chat',
  imports: [CommonModule, FormsModule],
  templateUrl: './chat.component.html',
  styleUrl: './chat.component.css',
})
export class ChatComponent implements OnInit {
  message = 'What APIs are defined and what should I check first?';
  reply = '';
  error = '';
  busy = false;

  constructor(
    private api: IntellisysApiService,
    private route: ActivatedRoute,
    private router: Router
  ) {}

  ngOnInit(): void {
    this.route.queryParamMap.pipe(take(1)).subscribe((params) => {
      const p = params.get('prompt');
      if (p != null && p.trim() !== '') {
        this.message = p;
        void this.router.navigate([], {
          relativeTo: this.route,
          replaceUrl: true,
          queryParams: {},
        });
      }
    });
  }

  get projectId(): number | null {
    return this.api.projectId();
  }

  send() {
    const id = this.projectId;
    if (id == null) {
      this.error = 'Set an active project on the dashboard.';
      return;
    }
    this.busy = true;
    this.error = '';
    this.api.chatMessage(id, this.message).subscribe({
      next: (r) => {
        this.reply = r.reply;
        this.busy = false;
      },
      error: (e) => {
        this.error = String(e?.error?.detail ?? e?.message ?? e);
        this.busy = false;
      },
    });
  }
}
