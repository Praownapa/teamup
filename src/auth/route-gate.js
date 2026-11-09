// What a protected page should show for the current sign-in state.
// The spinner appears only until the FIRST profile load: later refreshes (after saving the profile,
// accepting an invitation, creating a project...) keep the current page mounted, so it can show
// "Saved" / "Accepted" instead of being replaced by a spinner and losing that state.
export function routeGate({ user, profile, profileError, adminOnly = false, isAdmin = false }) {
  if (user === undefined) return 'loading';
  if (!user) return 'login';
  if (profileError) return 'error';
  if (!profile) return 'loading';
  if (adminOnly && !isAdmin) return 'home';
  return 'ok';
}
