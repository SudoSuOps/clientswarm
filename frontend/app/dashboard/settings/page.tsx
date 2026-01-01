'use client'

import { useState, useEffect } from 'react'
import Navigation from '@/components/Navigation'
import { User, CreditCard, Key, Bell, Loader2, Check, Plus, Trash2 } from 'lucide-react'
import { getProfile, updateProfile, getBilling, addFunds, generateApiKey, listApiKeys } from '@/lib/api'
import { useAuth } from '@/lib/hooks/useAuth'
import { formatCurrency } from '@/lib/utils'
import { cn } from '@/lib/utils'

type Tab = 'profile' | 'billing' | 'api-keys'

export default function SettingsPage() {
  const { client } = useAuth()
  const [activeTab, setActiveTab] = useState<Tab>('profile')
  const [loading, setLoading] = useState(false)
  const [saved, setSaved] = useState(false)

  // Profile state
  const [email, setEmail] = useState('')
  const [webhookUrl, setWebhookUrl] = useState('')
  const [notifyOnComplete, setNotifyOnComplete] = useState(true)

  // Billing state
  const [balance, setBalance] = useState(0)
  const [freeScans, setFreeScans] = useState(0)
  const [addAmount, setAddAmount] = useState(10)

  // API Keys state
  const [apiKeys, setApiKeys] = useState<any[]>([])
  const [newKey, setNewKey] = useState('')

  useEffect(() => {
    fetchData()
  }, [activeTab])

  const fetchData = async () => {
    try {
      if (activeTab === 'profile') {
        const { data } = await getProfile()
        setEmail(data.email || '')
        setWebhookUrl(data.webhook_url || '')
        setNotifyOnComplete(data.notify_on_complete ?? true)
      } else if (activeTab === 'billing') {
        const { data } = await getBilling()
        setBalance(data.balance)
        setFreeScans(data.free_scans_remaining)
      } else if (activeTab === 'api-keys') {
        const { data } = await listApiKeys()
        setApiKeys(data)
      }
    } catch (error) {
      console.error('Failed to fetch data:', error)
    }
  }

  const handleSaveProfile = async () => {
    setLoading(true)
    try {
      await updateProfile({ email, webhook_url: webhookUrl, notify_on_complete: notifyOnComplete })
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } catch (error) {
      console.error('Failed to save:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleAddFunds = async () => {
    setLoading(true)
    try {
      await addFunds(addAmount, 'stripe')
      await fetchData()
    } catch (error) {
      console.error('Failed to add funds:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleGenerateKey = async () => {
    setLoading(true)
    try {
      const { data } = await generateApiKey()
      setNewKey(data.key)
      await fetchData()
    } catch (error) {
      console.error('Failed to generate key:', error)
    } finally {
      setLoading(false)
    }
  }

  const tabs = [
    { id: 'profile', label: 'Profile', icon: User },
    { id: 'billing', label: 'Billing', icon: CreditCard },
    { id: 'api-keys', label: 'API Keys', icon: Key },
  ]

  return (
    <div className="min-h-screen bg-client-bg-dark">
      <Navigation />

      <main className="pt-20 pb-12 px-6">
        <div className="max-w-4xl mx-auto">
          <h1 className="text-2xl font-bold mb-8">Settings</h1>

          <div className="flex gap-6">
            {/* Sidebar */}
            <div className="w-48 flex-shrink-0">
              <div className="space-y-1">
                {tabs.map((tab) => {
                  const Icon = tab.icon
                  return (
                    <button
                      key={tab.id}
                      onClick={() => setActiveTab(tab.id as Tab)}
                      className={cn(
                        'w-full flex items-center gap-3 px-4 py-2.5 rounded-lg text-left transition-colors',
                        activeTab === tab.id
                          ? 'bg-client-bg-card text-client-text'
                          : 'text-client-text-dim hover:text-client-text hover:bg-client-bg-card/50'
                      )}
                    >
                      <Icon className="w-4 h-4" />
                      {tab.label}
                    </button>
                  )
                })}
              </div>
            </div>

            {/* Content */}
            <div className="flex-1">
              {activeTab === 'profile' && (
                <div className="bg-client-bg-card border border-client-border rounded-xl p-6">
                  <h2 className="text-lg font-semibold mb-6">Profile Settings</h2>

                  <div className="space-y-6">
                    <div>
                      <label className="block text-sm font-medium text-client-text-dim mb-2">
                        Wallet Address
                      </label>
                      <div className="px-4 py-3 bg-client-bg-elevated rounded-lg font-mono text-sm">
                        {client?.wallet}
                      </div>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-client-text-dim mb-2">
                        ENS Identity
                      </label>
                      <div className="px-4 py-3 bg-client-bg-elevated rounded-lg">
                        {client?.ens || 'Not registered'}
                      </div>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-client-text-dim mb-2">
                        Email (for notifications)
                      </label>
                      <input
                        type="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        placeholder="clinic@example.com"
                        className="w-full px-4 py-3 bg-client-bg-elevated border border-client-border rounded-lg focus:outline-none focus:border-client-teal"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-client-text-dim mb-2">
                        Webhook URL (for job completions)
                      </label>
                      <input
                        type="url"
                        value={webhookUrl}
                        onChange={(e) => setWebhookUrl(e.target.value)}
                        placeholder="https://your-server.com/webhook"
                        className="w-full px-4 py-3 bg-client-bg-elevated border border-client-border rounded-lg focus:outline-none focus:border-client-teal"
                      />
                    </div>

                    <div className="flex items-center gap-3">
                      <input
                        type="checkbox"
                        id="notify"
                        checked={notifyOnComplete}
                        onChange={(e) => setNotifyOnComplete(e.target.checked)}
                        className="w-4 h-4 rounded border-client-border"
                      />
                      <label htmlFor="notify" className="text-sm">
                        Email me when jobs complete
                      </label>
                    </div>

                    <button
                      onClick={handleSaveProfile}
                      disabled={loading}
                      className="px-6 py-2.5 bg-client-teal hover:bg-client-teal-light text-white font-medium rounded-lg transition-colors flex items-center gap-2"
                    >
                      {loading ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : saved ? (
                        <Check className="w-4 h-4" />
                      ) : null}
                      {saved ? 'Saved!' : 'Save Changes'}
                    </button>
                  </div>
                </div>
              )}

              {activeTab === 'billing' && (
                <div className="space-y-6">
                  <div className="bg-client-bg-card border border-client-border rounded-xl p-6">
                    <h2 className="text-lg font-semibold mb-6">Current Balance</h2>

                    <div className="grid grid-cols-2 gap-6">
                      <div className="p-4 bg-client-bg-elevated rounded-lg">
                        <div className="text-3xl font-bold text-client-success">
                          {formatCurrency(balance)}
                        </div>
                        <div className="text-sm text-client-text-dim">Available Balance</div>
                      </div>
                      <div className="p-4 bg-client-bg-elevated rounded-lg">
                        <div className="text-3xl font-bold text-client-teal">{freeScans}</div>
                        <div className="text-sm text-client-text-dim">Free Scans Remaining</div>
                      </div>
                    </div>
                  </div>

                  <div className="bg-client-bg-card border border-client-border rounded-xl p-6">
                    <h2 className="text-lg font-semibold mb-6">Add Funds</h2>

                    <div className="flex gap-3 mb-6">
                      {[10, 25, 50, 100].map((amount) => (
                        <button
                          key={amount}
                          onClick={() => setAddAmount(amount)}
                          className={cn(
                            'flex-1 py-3 rounded-lg font-medium transition-colors',
                            addAmount === amount
                              ? 'bg-client-teal text-white'
                              : 'bg-client-bg-elevated text-client-text-dim hover:text-client-text'
                          )}
                        >
                          ${amount}
                        </button>
                      ))}
                    </div>

                    <button
                      onClick={handleAddFunds}
                      disabled={loading}
                      className="w-full px-6 py-3 bg-client-teal hover:bg-client-teal-light text-white font-semibold rounded-lg transition-colors flex items-center justify-center gap-2"
                    >
                      {loading && <Loader2 className="w-4 h-4 animate-spin" />}
                      Add ${addAmount} (Demo Mode)
                    </button>

                    <p className="text-xs text-client-text-muted text-center mt-4">
                      In production, this would integrate with Stripe or USDC payments.
                    </p>
                  </div>
                </div>
              )}

              {activeTab === 'api-keys' && (
                <div className="bg-client-bg-card border border-client-border rounded-xl p-6">
                  <div className="flex items-center justify-between mb-6">
                    <h2 className="text-lg font-semibold">API Keys</h2>
                    <button
                      onClick={handleGenerateKey}
                      disabled={loading}
                      className="px-4 py-2 bg-client-teal hover:bg-client-teal-light text-white font-medium rounded-lg transition-colors flex items-center gap-2"
                    >
                      {loading ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <Plus className="w-4 h-4" />
                      )}
                      Generate Key
                    </button>
                  </div>

                  {newKey && (
                    <div className="mb-6 p-4 bg-client-success/10 border border-client-success/30 rounded-lg">
                      <p className="text-sm text-client-success mb-2">
                        New API key generated! Copy it now - it won't be shown again.
                      </p>
                      <code className="block p-3 bg-client-bg-dark rounded font-mono text-sm break-all">
                        {newKey}
                      </code>
                    </div>
                  )}

                  {apiKeys.length === 0 ? (
                    <div className="text-center py-8 text-client-text-dim">
                      <Key className="w-8 h-8 mx-auto mb-2 opacity-50" />
                      <p>No API keys yet</p>
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {apiKeys.map((key, index) => (
                        <div
                          key={index}
                          className="flex items-center justify-between p-4 bg-client-bg-elevated rounded-lg"
                        >
                          <div>
                            <div className="font-mono text-sm">{key.key}</div>
                            <div className="text-xs text-client-text-dim">
                              Created: {new Date(key.created_at).toLocaleDateString()}
                            </div>
                          </div>
                          <button className="p-2 text-client-text-dim hover:text-client-error transition-colors">
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      ))}
                    </div>
                  )}

                  <div className="mt-6 p-4 bg-client-bg-elevated rounded-lg">
                    <h3 className="font-medium mb-2">API Usage</h3>
                    <pre className="text-xs text-client-text-dim overflow-x-auto">
{`curl -X POST https://api.clientswarm.eth/jobs/submit \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{"model": "queenbee-spine", "input_cid": "bafybei..."}'`}
                    </pre>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}
