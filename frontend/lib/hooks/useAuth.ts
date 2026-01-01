'use client'

import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface Client {
  wallet: string
  ens: string | null
  balance: number
  free_scans_remaining: number
  total_jobs: number
}

interface AuthState {
  token: string | null
  client: Client | null
  isAuthenticated: boolean
  setAuth: (token: string, client: Client) => void
  logout: () => void
}

export const useAuth = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      client: null,
      isAuthenticated: false,
      setAuth: (token, client) => {
        localStorage.setItem('token', token)
        set({ token, client, isAuthenticated: true })
      },
      logout: () => {
        localStorage.removeItem('token')
        set({ token: null, client: null, isAuthenticated: false })
      },
    }),
    {
      name: 'clientswarm-auth',
    }
  )
)
