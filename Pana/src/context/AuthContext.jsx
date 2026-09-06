/**
 * Session state for the component tree.
 *
 * The session is fetched through TanStack Query like any other resource; this
 * provider exists to expose it as context and to react to a session that
 * expires mid-use, which no single component owns.
 *
 * @module context/AuthContext
 */

import { useCallback, useEffect, useMemo } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import AuthContext from './authContext.js';
import { useCurrentUser, useLogout } from '../hooks/queries/useAuth.js';
import { onSessionExpired } from '../lib/apiClient.js';
import { queryKeys } from '../lib/queryClient.js';

export const AuthProvider = ({ children }) => {
  const queryClient = useQueryClient();
  const { data: user, isPending } = useCurrentUser();
  const logoutMutation = useLogout();

  // A request may find the session gone at any moment -- a refresh token that
  // expired or was revoked elsewhere. The client reports it here so the tree
  // re-renders as signed out, instead of each component discovering its own 401.
  useEffect(
    () =>
      onSessionExpired(() => {
        queryClient.setQueryData(queryKeys.auth.currentUser, null);
      }),
    [queryClient],
  );

  const logout = useCallback(() => logoutMutation.mutateAsync(), [logoutMutation]);

  const value = useMemo(
    () => ({
      user: user ?? null,
      isAuthenticated: Boolean(user),
      loading: isPending,
      logout,
    }),
    [user, isPending, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export default AuthProvider;
