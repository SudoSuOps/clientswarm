'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { Shield, ArrowLeft, Loader2, Check } from 'lucide-react'
import { getNonce, register } from '@/lib/api'
import { useAuth } from '@/lib/hooks/useAuth'

export default function RegisterPage() {
  const router = useRouter()
  const { setAuth } = useAuth()
  const [subdomain, setSubdomain] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const isValidSubdomain = subdomain.length >= 3 && /^[a-z0-9]+$/.test(subdomain)

  const handleRegister = async () => {
    if (!isValidSubdomain) {
      setError('Subdomain must be at least 3 alphanumeric characters')
      return
    }

    setLoading(true)
    setError('')

    try {
      if (typeof window === 'undefined' || !window.ethereum) {
        setError('Please install MetaMask or another Web3 wallet')
        setLoading(false)
        return
      }

      const accounts = await window.ethereum.request({
        method: 'eth_requestAccounts',
      })
      const address = accounts[0]

      const { data: nonceData } = await getNonce()

      const domain = window.location.host
      const origin = window.location.origin
      const statement = `Register ${subdomain}.clientswarm.eth with ClientSwarm`

      const message = `${domain} wants you to sign in with your Ethereum account:
${address}

${statement}

URI: ${origin}
Version: 1
Chain ID: 1
Nonce: ${nonceData.nonce}
Issued At: ${new Date().toISOString()}`

      const signature = await window.ethereum.request({
        method: 'personal_sign',
        params: [message, address],
      })

      const { data } = await register(message, signature, subdomain)

      setAuth(data.token, data.client)
      router.push('/dashboard')
    } catch (err: any) {
      console.error('Registration error:', err)
      setError(err.response?.data?.detail || err.message || 'Failed to register')
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
            <h1 className="text-2xl font-bold mb-2">Create Account</h1>
            <p className="text-client-text-dim">Register your clinic identity</p>
          </div>

          {error && (
            <div className="bg-client-error/10 border border-client-error/30 text-client-error rounded-lg p-4 mb-6 text-sm">
              {error}
            </div>
          )}

          <div className="mb-6">
            <label className="block text-sm font-medium text-client-text-dim mb-2">
              Choose your ENS subdomain
            </label>
            <div className="flex items-center">
              <input
                type="text"
                value={subdomain}
                onChange={(e) => setSubdomain(e.target.value.toLowerCase().replace(/[^a-z0-9]/g, ''))}
                placeholder="xyzclinic"
                className="flex-1 px-4 py-3 bg-client-bg-elevated border border-client-border rounded-l-lg focus:outline-none focus:border-client-teal text-client-text"
              />
              <div className="px-4 py-3 bg-client-bg-dark border border-l-0 border-client-border rounded-r-lg text-client-text-dim">
                .clientswarm.eth
              </div>
            </div>
            {subdomain && (
              <p className={`text-sm mt-2 ${isValidSubdomain ? 'text-client-success' : 'text-client-warning'}`}>
                {isValidSubdomain ? (
                  <span className="flex items-center gap-1">
                    <Check className="w-4 h-4" />
                    {subdomain}.clientswarm.eth is available
                  </span>
                ) : (
                  'Min 3 characters, alphanumeric only'
                )}
              </p>
            )}
          </div>

          <button
            onClick={handleRegister}
            disabled={loading || !isValidSubdomain}
            className="w-full px-6 py-4 bg-client-teal hover:bg-client-teal-light text-white font-medium rounded-xl transition-colors flex items-center justify-center gap-3 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Registering...
              </>
            ) : (
              'Register & Sign In'
            )}
          </button>

          <div className="mt-6 p-4 bg-client-bg-elevated rounded-lg">
            <p className="text-xs text-client-text-muted text-center">
              By registering, you'll receive 10 free scans. Your ENS subdomain is your permanent identity on the network.
            </p>
          </div>

          <p className="text-center text-sm text-client-text-muted mt-6">
            Already have an account?{' '}
            <Link href="/login" className="text-client-teal hover:underline">
              Sign In
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}
