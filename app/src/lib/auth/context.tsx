"use client";

import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { authClient } from "./client";
import { AuthState } from "./types";


const AuthContext = createContext<AuthState>({
  user: null,
  isLoading: true,
  isAuthenticated: false,
});


export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>(authClient.getState());

  useEffect(() => {
    authClient.refresh().catch(() => { /* ignore */ });
    const unsub = authClient.subscribe(setState);
    return unsub;
  }, []);

  return <AuthContext.Provider value={state}>{children}</AuthContext.Provider>;
}


export function useAuth(): AuthState {
  return useContext(AuthContext);
}
