const TOKEN_KEY = 'bookbridge_token';

// Each tab owns its login: a staff sign-in must not replace a student's JWT.
// Existing shared sessions are adopted once, then removed from shared storage.
export function getSessionToken(): string | null {
  const current = sessionStorage.getItem(TOKEN_KEY);
  if (current) return current;
  const legacy = localStorage.getItem(TOKEN_KEY);
  if (legacy) {
    sessionStorage.setItem(TOKEN_KEY, legacy);
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem('bookbridge_user');
  }
  return legacy;
}

export function saveSessionToken(token: string): void {
  sessionStorage.setItem(TOKEN_KEY, token);
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem('bookbridge_user');
}

export function clearSessionToken(): void {
  sessionStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem('bookbridge_user');
}
