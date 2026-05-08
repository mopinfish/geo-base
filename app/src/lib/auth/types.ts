export interface User {
  id: string;
  email: string | null;
  role: string | null;
  name: string | null;
  email_verified: boolean;
  app_metadata?: Record<string, unknown> | null;
  user_metadata?: Record<string, unknown> | null;
}

export interface TokenPair {
  access_token: string;
  expires_in: number;
  token_type: string;
  user: User;
}

export interface AuthState {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
}

export interface InvitationInfo {
  team_id: string;
  team_name: string;
  team_slug: string;
  role: string;
  email: string;
  inviter_name: string | null;
  expires_at: string;
  has_existing_account: boolean;
}
