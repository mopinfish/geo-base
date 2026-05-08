import { User, TokenPair, AuthState, InvitationInfo } from "./types";
import { parseAuthError } from "./errors";


const API_URL = process.env.NEXT_PUBLIC_API_URL || "";


type Listener = (state: AuthState) => void;


class AuthClient {
  private accessToken: string | null = null;
  private refreshTimer: ReturnType<typeof setTimeout> | null = null;
  private listeners: Set<Listener> = new Set();
  private state: AuthState = { user: null, isLoading: true, isAuthenticated: false };
  private refreshing: Promise<User | null> | null = null;

  async login(email: string, password: string): Promise<User> {
    const res = await fetch(`${API_URL}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ email, password }),
    });
    if (!res.ok) throw await parseAuthError(res);
    const data: TokenPair = await res.json();
    this.setSession(data);
    return data.user;
  }

  async refresh(): Promise<User | null> {
    // 並行 refresh の重複防止
    if (this.refreshing) return this.refreshing;

    this.refreshing = this._doRefresh();
    try {
      return await this.refreshing;
    } finally {
      this.refreshing = null;
    }
  }

  private async _doRefresh(): Promise<User | null> {
    try {
      const res = await fetch(`${API_URL}/api/auth/refresh`, {
        method: "POST",
        credentials: "include",
      });
      if (!res.ok) {
        this.clearSession();
        return null;
      }
      const data: TokenPair = await res.json();
      this.setSession(data);
      return data.user;
    } catch {
      this.clearSession();
      return null;
    }
  }

  async logout(): Promise<void> {
    try {
      await fetch(`${API_URL}/api/auth/logout`, {
        method: "POST",
        credentials: "include",
      });
    } catch {
      // ignore network errors
    }
    this.clearSession();
  }

  async acceptInvitation(token: string, password: string, name: string): Promise<User> {
    const res = await fetch(`${API_URL}/api/auth/accept-invitation`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ token, password, name }),
    });
    if (!res.ok) throw await parseAuthError(res);
    const data = await res.json();
    this.setSession(data);
    return data.user;
  }

  async getInvitationInfo(token: string): Promise<InvitationInfo> {
    const res = await fetch(`${API_URL}/api/auth/invitations/${token}`);
    if (!res.ok) throw await parseAuthError(res);
    return res.json();
  }

  async requestPasswordReset(email: string): Promise<void> {
    await fetch(`${API_URL}/api/auth/password-reset/request`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email }),
    });
  }

  async confirmPasswordReset(token: string, newPassword: string): Promise<void> {
    const res = await fetch(`${API_URL}/api/auth/password-reset/confirm`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token, new_password: newPassword }),
    });
    if (!res.ok) throw await parseAuthError(res);
  }

  getAccessToken(): string | null {
    return this.accessToken;
  }

  getState(): AuthState {
    return this.state;
  }

  subscribe(listener: Listener): () => void {
    this.listeners.add(listener);
    listener(this.state);
    return () => {
      this.listeners.delete(listener);
    };
  }

  private setSession(data: TokenPair): void {
    this.accessToken = data.access_token;
    this.scheduleRefresh(data.expires_in);
    this.state = { user: data.user, isLoading: false, isAuthenticated: true };
    this.notify();
  }

  private clearSession(): void {
    this.accessToken = null;
    if (this.refreshTimer) {
      clearTimeout(this.refreshTimer);
      this.refreshTimer = null;
    }
    this.state = { user: null, isLoading: false, isAuthenticated: false };
    this.notify();
  }

  private scheduleRefresh(expiresInSec: number): void {
    if (this.refreshTimer) clearTimeout(this.refreshTimer);
    const refreshIn = Math.max((expiresInSec - 60) * 1000, 1000);
    this.refreshTimer = setTimeout(() => {
      this.refresh().catch(() => this.clearSession());
    }, refreshIn);
  }

  private notify(): void {
    this.listeners.forEach((l) => l(this.state));
  }
}


export const authClient = new AuthClient();
