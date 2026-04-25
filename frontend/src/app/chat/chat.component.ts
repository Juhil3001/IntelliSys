import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { IntellisysApiService } from '../intellisys-api.service';

@Component({
  selector: 'app-chat',
  imports: [CommonModule, FormsModule],
  templateUrl: './chat.component.html',
  styleUrl: './chat.component.css',
})
export class ChatComponent {
  message = 'What APIs are defined and what should I check first?';
  reply = '';
  error = '';
  busy = false;

  constructor(private api: IntellisysApiService) {}

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
