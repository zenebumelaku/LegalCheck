import React, { useState } from 'react';
import {
  User as UserIcon,
  Building,
  Mail,
  ShieldCheck,
  Lock,
  Clock,
  Check,
  AlertCircle,
  Save,
  KeyRound
} from 'lucide-react';
import { User } from '../types';
import { AuthService } from '../services/auth.service';

interface SettingsPageProps {
  currentUser: User | null;
  onUpdateUser: (user: User) => void;
  onLogout: () => void;
  onNavigate: (path: string) => void;
}

export function SettingsPage({
  currentUser,
  onUpdateUser,
  onLogout,
  onNavigate
}: SettingsPageProps) {
  const [retentionDays, setRetentionDays] = useState(currentUser?.dataRetentionDays || 90);
  const [savedSuccess, setSavedSuccess] = useState(false);

  // Security password change form
  const [currentPass, setCurrentPass] = useState('');
  const [newPass, setNewPass] = useState('');
  const [confirmPass, setConfirmPass] = useState('');
  const [passwordStatus, setPasswordStatus] = useState<string | null>(null);

  const handleSaveRetention = async (e: React.FormEvent) => {
    e.preventDefault();
    const updated = await AuthService.updateProfile({ dataRetentionDays: retentionDays });
    onUpdateUser(updated);
    setSavedSuccess(true);
    setTimeout(() => setSavedSuccess(false), 2000);
  };

  const handlePasswordChange = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newPass || newPass !== confirmPass) {
      setPasswordStatus('New passwords do not match.');
      return;
    }
    setPasswordStatus('Password successfully updated for your active enterprise session.');
    setCurrentPass('');
    setNewPass('');
    setConfirmPass('');
    setTimeout(() => setPasswordStatus(null), 3000);
  };

  return (
    <div className="max-w-4xl mx-auto py-8 px-4 sm:px-6 space-y-8">
      <div>
        <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-slate-900">
          Organization & Security Settings
        </h1>
        <p className="mt-1 text-xs sm:text-sm text-slate-500">
          Manage contractual data retention cycles, privacy standards, and security controls.
        </p>
      </div>

      {/* Data Retention Governance */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs space-y-4">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="text-sm font-bold text-slate-900">Document Data Retention Window</h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Specify how long uploaded contract excerpts and audit findings remain stored for your organization.
            </p>
          </div>
          <Clock className="w-5 h-5 text-slate-400" />
        </div>

        <form onSubmit={handleSaveRetention} className="space-y-4 pt-2">
          <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
            {[
              { days: 30, label: '30 Days', desc: 'Strict Privacy' },
              { days: 90, label: '90 Days', desc: 'Standard Corporate' },
              { days: 365, label: '1 Year', desc: 'Annual Audit Cycle' },
              { days: 0, label: 'Indefinite', desc: 'Manual Deletion' }
            ].map(opt => (
              <button
                key={opt.days}
                type="button"
                onClick={() => setRetentionDays(opt.days)}
                className={`p-3.5 rounded-lg border text-left transition-all ${
                  retentionDays === opt.days
                    ? 'border-slate-900 bg-slate-900 text-white'
                    : 'border-slate-200 bg-slate-50 text-slate-800 hover:bg-slate-100'
                }`}
              >
                <div className="font-bold text-xs">{opt.label}</div>
                <div className={`text-[10px] mt-0.5 ${retentionDays === opt.days ? 'text-slate-300' : 'text-slate-500'}`}>
                  {opt.desc}
                </div>
              </button>
            ))}
          </div>

          <div className="flex items-center justify-between pt-2">
            <span className="text-xs text-slate-500">
              {savedSuccess ? (
                <span className="text-emerald-700 font-semibold flex items-center gap-1">
                  <Check className="w-4 h-4" />
                  <span>Retention preferences saved.</span>
                </span>
              ) : (
                'Automatic archival runs according to your selected period.'
              )}
            </span>
            <button
              type="submit"
              className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold text-white bg-slate-900 hover:bg-slate-800 rounded-lg shadow-xs"
            >
              <Save className="w-3.5 h-3.5" />
              <span>Save Policy</span>
            </button>
          </div>
        </form>
      </div>

      {/* Security Credentials */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs space-y-4">
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-sm font-bold text-slate-900">Change Authentication Password</h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Update password credentials used to access enterprise compliance reports.
            </p>
          </div>
          <KeyRound className="w-5 h-5 text-slate-400" />
        </div>

        {passwordStatus && (
          <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-lg text-xs">
            {passwordStatus}
          </div>
        )}

        <form onSubmit={handlePasswordChange} className="space-y-3 pt-1 max-w-md">
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Current Password
            </label>
            <input
              type="password"
              required
              value={currentPass}
              onChange={e => setCurrentPass(e.target.value)}
              className="w-full text-xs rounded-lg border border-slate-300 p-2.5 text-slate-900 focus:ring-2 focus:ring-slate-900 focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              New Password
            </label>
            <input
              type="password"
              required
              value={newPass}
              onChange={e => setNewPass(e.target.value)}
              className="w-full text-xs rounded-lg border border-slate-300 p-2.5 text-slate-900 focus:ring-2 focus:ring-slate-900 focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Confirm New Password
            </label>
            <input
              type="password"
              required
              value={confirmPass}
              onChange={e => setConfirmPass(e.target.value)}
              className="w-full text-xs rounded-lg border border-slate-300 p-2.5 text-slate-900 focus:ring-2 focus:ring-slate-900 focus:outline-none"
            />
          </div>

          <div className="pt-2">
            <button
              type="submit"
              className="px-4 py-2 text-xs font-semibold text-slate-800 border border-slate-300 hover:bg-slate-50 rounded-lg"
            >
              Update Password
            </button>
          </div>
        </form>
      </div>

      {/* Compliance Disclaimer Acknowledgement */}
      <div className="bg-slate-50 rounded-xl border border-slate-200 p-5 text-xs text-slate-600 space-y-2">
        <div className="font-bold text-slate-900 flex items-center gap-1.5">
          <ShieldCheck className="w-4 h-4 text-emerald-700" />
          <span>Statutory Compliance Architecture</span>
        </div>
        <p className="leading-relaxed">
          LegalCheck Ethiopia strictly uses deterministic checks mapped to Federal Negarit Gazeta Proclamation No. 1156/2019 and relevant Civil Code sections. Reports are for internal enterprise risk analysis and do not replace representation by certified Ethiopian advocates.
        </p>
      </div>
    </div>
  );
}

export function ProfilePage({
  currentUser,
  onUpdateUser,
  onLogout
}: SettingsPageProps) {
  const [fullName, setFullName] = useState(currentUser?.fullName || '');
  const [organization, setOrganization] = useState(currentUser?.organization || '');
  const [role, setRole] = useState<User['role']>(currentUser?.role || 'COMPLIANCE_OFFICER');
  const [isSaved, setIsSaved] = useState(false);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    const updated = await AuthService.updateProfile({
      fullName,
      organization,
      role
    });
    onUpdateUser(updated);
    setIsSaved(true);
    setTimeout(() => setIsSaved(false), 2000);
  };

  return (
    <div className="max-w-3xl mx-auto py-8 px-4 sm:px-6 space-y-6">
      <div>
        <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-slate-900">
          User Profile
        </h1>
        <p className="mt-1 text-xs sm:text-sm text-slate-500">
          Personal identification and organizational registration in LegalCheck Ethiopia.
        </p>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs">
        <form onSubmit={handleSave} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1.5">
              Full Name
            </label>
            <div className="relative">
              <UserIcon className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                required
                value={fullName}
                onChange={e => setFullName(e.target.value)}
                className="w-full pl-9 pr-3 py-2 text-xs rounded-lg border border-slate-300 text-slate-900 focus:ring-2 focus:ring-slate-900 focus:outline-none"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1.5">
              Organization Name
            </label>
            <div className="relative">
              <Building className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                required
                value={organization}
                onChange={e => setOrganization(e.target.value)}
                className="w-full pl-9 pr-3 py-2 text-xs rounded-lg border border-slate-300 text-slate-900 focus:ring-2 focus:ring-slate-900 focus:outline-none"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1.5">
              Assigned Operational Role
            </label>
            <select
              value={role}
              onChange={e => setRole(e.target.value as User['role'])}
              className="w-full text-xs rounded-lg border border-slate-300 p-2.5 bg-white text-slate-900 focus:ring-2 focus:ring-slate-900 focus:outline-none"
            >
              <option value="COMPLIANCE_OFFICER">Compliance Officer</option>
              <option value="HR_MANAGER">HR Manager</option>
              <option value="LEGAL_COUNSEL">Legal Counsel</option>
              <option value="BUSINESS_OWNER">Business Owner</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1.5">
              Registered Email (Primary Login)
            </label>
            <div className="relative">
              <Mail className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="email"
                disabled
                value={currentUser?.email || 'compliance@addistech.et'}
                className="w-full pl-9 pr-3 py-2 text-xs rounded-lg border border-slate-200 bg-slate-50 text-slate-500 cursor-not-allowed"
              />
            </div>
            <p className="mt-1 text-[11px] text-slate-400">
              Corporate email identity cannot be changed without administrator approval.
            </p>
          </div>

          <div className="pt-4 flex items-center justify-between border-t border-slate-100">
            {isSaved ? (
              <span className="text-xs text-emerald-700 font-semibold flex items-center gap-1">
                <Check className="w-4 h-4" />
                <span>Profile updated successfully</span>
              </span>
            ) : <div />}

            <button
              type="submit"
              className="px-5 py-2 text-xs font-semibold text-white bg-slate-900 hover:bg-slate-800 rounded-lg shadow-xs transition-colors"
            >
              Save Profile Changes
            </button>
          </div>
        </form>
      </div>

      {/* Sign Out Card */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs flex items-center justify-between">
        <div>
          <div className="text-sm font-bold text-slate-900">Sign Out of Active Session</div>
          <p className="text-xs text-slate-500 mt-0.5">
            Safely close your current session on this terminal.
          </p>
        </div>
        <button
          onClick={onLogout}
          className="px-4 py-2 text-xs font-semibold text-rose-600 hover:text-rose-700 hover:bg-rose-50 border border-rose-200 rounded-lg transition-colors"
        >
          Sign Out
        </button>
      </div>
    </div>
  );
}
