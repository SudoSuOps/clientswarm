'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { Shield, Wallet, ArrowLeft, Loader2 } from 'lucide-react'
import { getNonce, login } from '@/lib/api'
import { useAuth } from '@/lib/hooks/useAuth'

export default function LoginPage() {
  const router = useRouter()
  const { setAuth } = useAuth()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleConnect = async () => {
    setLoading(true)
    setError('')

    try {
      // Check for window.ethereum
      if (typeof window === 'undefined' || !window.ethereum) {
        setError('Please install MetaMask or another Web3 wallet')
        setLoading(false)
        return
      }

      // Request accounts
      const accounts = await window.ethereum.request({
        method: 'eth_requestAccounts',
      })
      const address = accounts[0]

      // Get nonce
      const { data: nonceData } = await getNonce()

      // Create SIWE message
      const domain = window.location.host
      const origin = window.location.origin
      const statement = 'Sign in with Ethereum to ClientSwarm'

      const message = `${domain} wants you to sign in with your Ethereum account:
${address}

${statement}

URI: ${origin}
Version: 1
Chain ID: 1
Nonce: ${nonceData.nonce}
Issued At: ${new Date().toISOString()}`

      // Sign message
      const signature = await window.ethereum.request({
        method: 'personal_sign',
        params: [message, address],
      })

      // Login
      const { data } = await login(message, signature)

      // Store auth
      setAuth(data.token, data.client)

      // Redirect to dashboard
      router.push('/dashboard')
    } catch (err: any) {
      console.error('Login error:', err)
      setError(err.response?.data?.detail || err.message || 'Failed to login')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-6">
      <div className="w-full max-w-md">
        <Link
          href="/"
          className="inline-flex items-center gap-2 text-client-text-dim hover:text-client-text mb-8"
        >
          <ArrowLeft className="w-4 h-4" />
          Back
        </Link>

        <div className="bg-client-bg-card border border-client-border rounded-2xl p-8">
          <div className="text-center mb-8">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-client-teal to-client-blue flex items-center justify-center mx-auto mb-4">
              <Shield className="w-8 h-8 text-white" />
            </div>
            <h1 className="text-2xl font-bold mb-2">Welcome Back</h1>
            <p className="text-client-text-dim">Sign in with your Ethereum wallet</p>
          </div>

          {error && (
            <div className="bg-client-error/10 border border-client-error/30 text-client-error rounded-lg p-4 mb-6 text-sm">
              {error}
            </div>
          )}

          <button
            onClick={handleConnect}
            disabled={loading}
            className="w-full px-6 py-4 bg-client-bg-elevated hover:bg-client-border border border-client-border rounded-xl transition-colors flex items-center justify-center gap-3 disabled:opacity-50"
          >
            {loading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Wallet className="w-5 h-5" />
            )}
            <span className="font-medium">
              {loading ? 'Connecting...' : 'Connect Wallet'}
            </span>
          </button>

          <p className="text-center text-sm text-client-text-muted mt-6">
            Don't have an account?{' '}
            <Link href="/register" className="text-client-teal hover:underline">
              Register
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}

// Type declaration for window.ethereum
declare global {
  interface Window {
    ethereum?: any
  }
}
