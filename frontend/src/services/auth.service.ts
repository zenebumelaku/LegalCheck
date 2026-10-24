import { User } from '../types';
import { apiRequest, isDemoFallbackEnabled } from '../lib/api-client';

interface BackendUser {
  id: string;
  email: string;
  name: string;
  role: string;
  created_at: string;
  createdAt?: string;
  fullName?: string;
  organization?: string;
  dataRetentionDays?: number;
}

export class AuthService {
  private static userKey = 'lc_active_session_user';
  private static tokenKey = 'lc_auth_token';

  private static getStoredUser(): User | null {
    if (typeof window === 'undefined') return null;
    const stored = sessionStorage.getItem(this.userKey);
    if (!stored) return null;
    try {
      const parsed = JSON.parse(stored) as User;
      return parsed && parsed.email ? parsed : null;
    } catch {
      return null;
    }
  }

  private static normalizeUser(response: BackendUser | null | undefined, existing?: User | null): User | null {
    if (!response) return null;

    const role: User['role'] =
      response.role === 'admin' ? 'LEGAL_COUNSEL' : existing?.role ?? 'COMPLIANCE_OFFICER';
    const candidate = {
      id: String(response.id ?? existing?.id ?? ''),
      email: String(response.email ?? existing?.email ?? ''),
      fullName: String(response.fullName ?? response.name ?? existing?.fullName ?? ''),
      organization: String(response.organization ?? existing?.organization ?? ''),
      role,
      createdAt: String(response.createdAt ?? response.created_at ?? existing?.createdAt ?? new Date().toISOString()),
      dataRetentionDays: Number(response.dataRetentionDays ?? existing?.dataRetentionDays ?? 90)
    };

    if (!candidate.email) return null;
    return candidate;
  }

  static async getCurrentUser(): Promise<User | null> {
    const stored = this.getStoredUser();

    try {
      const user = await apiRequest<BackendUser>('/api/v1/auth/me');
      const normalized = this.normalizeUser(user, stored);
      if (normalized) {
        this.setUser(normalized);
      }
      return normalized ?? stored;
    } catch (error) {
      if (isDemoFallbackEnabled()) {
        return stored;
      }
      if (typeof window !== 'undefined') {
        this.clearSession();
      }
      return null;
    }
  }

  static async login(email: string, password: string): Promise<User> {
    const response = await apiRequest<{ access_token: string; user: BackendUser }>('/api/v1/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password })
    });

    if (typeof window !== 'undefined' && response.access_token) {
      sessionStorage.setItem(this.tokenKey, response.access_token);
    }

    const user = this.normalizeUser(response.user, this.getStoredUser());
    if (!user) {
      throw new Error('Authentication succeeded but the user payload was empty.');
    }

    this.setUser(user);
    return user;
  }

  static async register(data: {
    email: string;
    fullName: string;
    organization: string;
    role?: User['role'];
    password: string;
  }): Promise<User> {
    const payload = {
      name: data.fullName,
      email: data.email,
      password: data.password
    };

    const response = await apiRequest<BackendUser>('/api/v1/auth/register', {
      method: 'POST',
      body: JSON.stringify(payload)
    });

    const user = this.normalizeUser(
      {
        ...response,
        fullName: data.fullName,
        organization: data.organization,
        role: data.role ?? 'COMPLIANCE_OFFICER'
      },
      this.getStoredUser()
    );

    if (!user) {
      throw new Error('Registration succeeded but the returned user payload was empty.');
    }

    this.setUser(user);
    const authenticatedUser = await this.login(data.email, data.password);
    const registeredUser = { ...authenticatedUser, organization: data.organization, role: data.role ?? authenticatedUser.role };
    this.setUser(registeredUser);
    return registeredUser;
  }

  static async logout(): Promise<void> {
    try {
      await apiRequest('/api/v1/auth/logout', { method: 'POST' });
    } catch {
      // Ignore backend timeout/401 if the session is already invalid.
    } finally {
      this.clearSession();
    }
  }

  static async requestPasswordReset(email: string): Promise<{ success: boolean; message: string }> {
    const response = await apiRequest<{ message: string }>('/api/v1/auth/password-reset-request', {
      method: 'POST',
      body: JSON.stringify({ email })
    });
    return { success: true, message: response.message };
  }

  static async updateProfile(updates: Partial<User>): Promise<User> {
    if (!isDemoFallbackEnabled()) {
      throw new Error('Profile updates require the backend profile API to be available.');
    }

    const current = this.getStoredUser();
    if (!current) {
      throw new Error('An active user session is required to update the profile.');
    }
    const merged = { ...current, ...updates };
    this.setUser(merged);
    return merged;
  }

  private static clearSession(): void {
    if (typeof window === 'undefined') return;
    sessionStorage.removeItem(this.userKey);
    sessionStorage.removeItem(this.tokenKey);
  }

  private static setUser(user: User): void {
    if (typeof window !== 'undefined') {
      sessionStorage.setItem(this.userKey, JSON.stringify(user));
    }
  }
}
