import { User } from '../types';
import { apiRequest, isDemoFallbackEnabled } from '../lib/api-client';

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

  private static normalizeUser(response: any, existing?: User | null): User | null {
    if (!response) return null;

    const candidate = {
      id: String(response.id ?? existing?.id ?? ''),
      email: String(response.email ?? existing?.email ?? ''),
      fullName: String(response.fullName ?? response.name ?? existing?.fullName ?? ''),
      organization: String(response.organization ?? existing?.organization ?? ''),
      role: (response.role as User['role']) ?? existing?.role ?? 'COMPLIANCE_OFFICER',
      createdAt: String(response.createdAt ?? response.created_at ?? existing?.createdAt ?? new Date().toISOString()),
      dataRetentionDays: Number(response.dataRetentionDays ?? existing?.dataRetentionDays ?? 90)
    };

    if (!candidate.email) return null;
    return candidate;
  }

  static async getCurrentUser(): Promise<User | null> {
    const stored = this.getStoredUser();

    try {
      const user = await apiRequest<any>('/api/v1/auth/me');
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
    const response = await apiRequest<{ access_token: string; user: any }>('/api/v1/auth/login', {
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

    const response = await apiRequest<any>('/api/v1/auth/register', {
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
    return user;
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
    return await apiRequest<{ success: boolean; message: string }>('/api/v1/auth/password-reset-request', {
      method: 'POST',
      body: JSON.stringify({ email })
    });
  }

  static async updateProfile(updates: Partial<User>): Promise<User> {
    const current = this.getStoredUser() ?? this.normalizeUser({
      email: '',
      fullName: '',
      organization: '',
      role: 'COMPLIANCE_OFFICER'
    });
    const merged = { ...current, ...updates } as User;

    if (!isDemoFallbackEnabled()) {
      throw new Error('Profile updates require the backend profile API to be available.');
    }

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
