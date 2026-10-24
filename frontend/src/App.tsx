/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect } from 'react';
import { useRouter } from './hooks/useRouter';
import { User } from './types';
import { AuthService } from './services/auth.service';

// Layout components
import { Navbar } from './components/layout/Navbar';
import { AppSidebar } from './components/layout/AppSidebar';
import { DashboardHeader } from './components/layout/DashboardHeader';
import { Footer } from './components/layout/Footer';

// Views
import { LandingPage } from './views/LandingPage';
import { LoginPage, RegisterPage, ForgotPasswordPage } from './views/AuthPages';
import { DashboardPage } from './views/DashboardPage';
import { NewAuditPage } from './views/NewAuditPage';
import { AuditHistoryPage } from './views/AuditHistoryPage';
import { AuditDetailPage } from './views/AuditDetailPage';
import { LegalSourcesPage } from './views/LegalSourcesPage';
import { SettingsPage, ProfilePage } from './views/SettingsPages';

export default function App() {
  const { path, navigate } = useRouter();
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const [isAuthChecking, setIsAuthChecking] = useState(true);

  useEffect(() => {
    async function initUser() {
      try {
        const user = await AuthService.getCurrentUser();
        setCurrentUser(user);
      } catch (err) {
        console.error('Failed to init user session', err);
      } finally {
        setIsAuthChecking(false);
      }
    }
    initUser();
  }, []);

  const handleLogout = async () => {
    await AuthService.logout();
    setCurrentUser(null);
    navigate('/login');
  };

  const handleAuthSuccess = (user: User) => {
    setCurrentUser(user);
  };

  // Determine whether the current view is part of the private dashboard workspace
  const isDashboardView =
    path.startsWith('/dashboard') ||
    path.startsWith('/audits') ||
    path.startsWith('/settings') ||
    path.startsWith('/profile');

  // Match audit detail route: /audits/:id
  const auditDetailMatch = path.match(/^\/audits\/(aud-eth-[a-zA-Z0-9_-]+)/);

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 text-slate-900 font-sans">
      {/* If in Dashboard Workspace */}
      {isDashboardView ? (
        <div className="flex-1 flex min-h-screen">
          {/* Desktop Sidebar */}
          <div className="hidden md:block shrink-0">
            <AppSidebar
              currentPath={path}
              onNavigate={navigate}
              currentUser={currentUser}
              onLogout={handleLogout}
            />
          </div>

          {/* Mobile Sidebar Drawer */}
          {mobileSidebarOpen && (
            <div className="fixed inset-0 z-50 flex md:hidden">
              <div
                className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs"
                onClick={() => setMobileSidebarOpen(false)}
              />
              <div className="relative z-10 w-64">
                <AppSidebar
                  currentPath={path}
                  onNavigate={p => {
                    navigate(p);
                    setMobileSidebarOpen(false);
                  }}
                  currentUser={currentUser}
                  onLogout={() => {
                    setMobileSidebarOpen(false);
                    handleLogout();
                  }}
                />
              </div>
            </div>
          )}

          {/* Main Content Area */}
          <div className="flex-1 flex flex-col min-w-0">
            <DashboardHeader
              currentPath={path}
              onNavigate={navigate}
              currentUser={currentUser}
              onToggleMobileNav={() => setMobileSidebarOpen(!mobileSidebarOpen)}
            />

            <main className="flex-1 pb-12">
              {path === '/dashboard' && (
                <DashboardPage onNavigate={navigate} currentUser={currentUser} />
              )}
              {path === '/audits/new' && <NewAuditPage onNavigate={navigate} />}
              {path === '/audits' && <AuditHistoryPage onNavigate={navigate} />}
              {auditDetailMatch && (
                <AuditDetailPage auditId={auditDetailMatch[1]} onNavigate={navigate} />
              )}
              {path === '/settings' && (
                <SettingsPage
                  currentUser={currentUser}
                  onUpdateUser={setCurrentUser}
                  onLogout={handleLogout}
                  onNavigate={navigate}
                />
              )}
              {path === '/profile' && (
                <ProfilePage
                  currentUser={currentUser}
                  onUpdateUser={setCurrentUser}
                  onLogout={handleLogout}
                  onNavigate={navigate}
                />
              )}
            </main>
          </div>
        </div>
      ) : (
        /* Public & Authentication Layout */
        <div className="flex-1 flex flex-col">
          <Navbar
            currentPath={path}
            onNavigate={navigate}
            isAuthenticated={!!currentUser}
          />

          <main className="flex-1">
            {path === '/' && <LandingPage onNavigate={navigate} />}
            {path === '/login' && (
              <LoginPage onNavigate={navigate} onAuthSuccess={handleAuthSuccess} />
            )}
            {path === '/register' && (
              <RegisterPage onNavigate={navigate} onAuthSuccess={handleAuthSuccess} />
            )}
            {path === '/forgot-password' && (
              <ForgotPasswordPage onNavigate={navigate} />
            )}
            {path === '/legal-sources' && <LegalSourcesPage />}
          </main>

          <Footer onNavigate={navigate} />
        </div>
      )}
    </div>
  );
}
