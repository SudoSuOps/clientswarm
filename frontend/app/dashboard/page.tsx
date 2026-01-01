'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import Navigation from '@/components/Navigation'
import { Upload, FileText, Clock, CheckCircle, AlertCircle, DollarSign, TrendingUp, ArrowRight } from 'lucide-react'
import { getDashboardStats, listJobs } from '@/lib/api'
import { useAuth } from '@/lib/hooks/useAuth'
import JobStatusBadge from '@/components/JobStatusBadge'
import { formatDate, truncateCid, formatCurrency } from '@/lib/utils'

interface Stats {
  total_jobs: number
  pending_jobs: number
  completed_jobs: number
  failed_jobs: number
  total_spent: number
  avg_confidence: number
  jobs_today: number
  jobs_this_week: number
}

interface Job {
  id: string
  job_id: string
  job_cid: string
  model: string
  status: string
  created_at: string
  confidence?: number
}

export default function DashboardPage() {
  const { client, isAuthenticated } = useAuth()
  const [stats, setStats] = useState<Stats | null>(null)
  const [recentJobs, setRecentJobs] = useState<Job[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [statsRes, jobsRes] = await Promise.all([
          getDashboardStats(),
          listJobs(1),
        ])
        setStats(statsRes.data)
        setRecentJobs(jobsRes.data.jobs.slice(0, 5))
      } catch (error) {
        console.error('Failed to fetch dashboard data:', error)
      } finally {
        setLoading(false)
      }
    }

    if (isAuthenticated) {
      fetchData()
    }
  }, [isAuthenticated])

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-client-text-dim">Please log in to access the dashboard.</p>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-client-bg-dark">
      <Navigation />

      <main className="pt-20 pb-12 px-6">
        <div className="max-w-7xl mx-auto">
          {/* Header */}
          <div className="mb-8">
            <h1 className="text-2xl font-bold mb-2">
              Welcome back, {client?.ens || 'Client'}
            </h1>
            <p className="text-client-text-dim">
              Here's an overview of your medical imaging jobs.
            </p>
          </div>

          {/* Quick Actions */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
            <Link
              href="/dashboard/upload"
              className="p-6 bg-gradient-to-br from-client-teal/20 to-client-bg-card border border-client-teal/30 rounded-xl hover:border-client-teal/50 transition-colors group"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 rounded-xl bg-client-teal/20 flex items-center justify-center">
                    <Upload className="w-6 h-6 text-client-teal" />
                  </div>
                  <div>
                    <h3 className="font-semibold">Upload Scan</h3>
                    <p className="text-sm text-client-text-dim">Submit a new job</p>
                  </div>
                </div>
                <ArrowRight className="w-5 h-5 text-client-teal group-hover:translate-x-1 transition-transform" />
              </div>
            </Link>

            <Link
              href="/dashboard/jobs"
              className="p-6 bg-client-bg-card border border-client-border rounded-xl hover:border-client-blue/50 transition-colors group"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 rounded-xl bg-client-blue/20 flex items-center justify-center">
                    <FileText className="w-6 h-6 text-client-blue" />
                  </div>
                  <div>
                    <h3 className="font-semibold">View Jobs</h3>
                    <p className="text-sm text-client-text-dim">Track your submissions</p>
                  </div>
                </div>
                <ArrowRight className="w-5 h-5 text-client-blue group-hover:translate-x-1 transition-transform" />
              </div>
            </Link>
          </div>

          {/* Stats Grid */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            <div className="p-5 bg-client-bg-card border border-client-border rounded-xl">
              <div className="flex items-center gap-3 mb-3">
                <div className="w-10 h-10 rounded-lg bg-client-bg-elevated flex items-center justify-center">
                  <FileText className="w-5 h-5 text-client-text-dim" />
                </div>
              </div>
              <div className="text-2xl font-bold">{stats?.total_jobs || 0}</div>
              <div className="text-sm text-client-text-dim">Total Jobs</div>
            </div>

            <div className="p-5 bg-client-bg-card border border-client-border rounded-xl">
              <div className="flex items-center gap-3 mb-3">
                <div className="w-10 h-10 rounded-lg bg-yellow-500/10 flex items-center justify-center">
                  <Clock className="w-5 h-5 text-yellow-400" />
                </div>
              </div>
              <div className="text-2xl font-bold">{stats?.pending_jobs || 0}</div>
              <div className="text-sm text-client-text-dim">Pending</div>
            </div>

            <div className="p-5 bg-client-bg-card border border-client-border rounded-xl">
              <div className="flex items-center gap-3 mb-3">
                <div className="w-10 h-10 rounded-lg bg-green-500/10 flex items-center justify-center">
                  <CheckCircle className="w-5 h-5 text-green-400" />
                </div>
              </div>
              <div className="text-2xl font-bold">{stats?.completed_jobs || 0}</div>
              <div className="text-sm text-client-text-dim">Completed</div>
            </div>

            <div className="p-5 bg-client-bg-card border border-client-border rounded-xl">
              <div className="flex items-center gap-3 mb-3">
                <div className="w-10 h-10 rounded-lg bg-client-teal/10 flex items-center justify-center">
                  <TrendingUp className="w-5 h-5 text-client-teal" />
                </div>
              </div>
              <div className="text-2xl font-bold">
                {stats?.avg_confidence ? `${(stats.avg_confidence * 100).toFixed(0)}%` : '-'}
              </div>
              <div className="text-sm text-client-text-dim">Avg Confidence</div>
            </div>
          </div>

          {/* Balance Card */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
            <div className="p-6 bg-gradient-to-br from-client-bg-card to-client-bg-elevated border border-client-border rounded-xl">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold">Account Balance</h3>
                <DollarSign className="w-5 h-5 text-client-text-dim" />
              </div>
              <div className="text-3xl font-bold text-client-success mb-2">
                {formatCurrency(client?.balance || 0)}
              </div>
              <div className="text-sm text-client-text-dim mb-4">
                + {client?.free_scans_remaining || 0} free scans remaining
              </div>
              <Link
                href="/dashboard/settings"
                className="text-sm text-client-teal hover:underline"
              >
                Add Funds
              </Link>
            </div>

            <div className="lg:col-span-2 p-6 bg-client-bg-card border border-client-border rounded-xl">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold">Recent Jobs</h3>
                <Link href="/dashboard/jobs" className="text-sm text-client-teal hover:underline">
                  View All
                </Link>
              </div>
              {recentJobs.length === 0 ? (
                <div className="text-center py-8 text-client-text-dim">
                  <FileText className="w-8 h-8 mx-auto mb-2 opacity-50" />
                  <p>No jobs yet. Upload your first scan!</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {recentJobs.map((job) => (
                    <Link
                      key={job.id}
                      href={`/dashboard/jobs/${job.job_id}`}
                      className="flex items-center justify-between p-3 bg-client-bg-elevated rounded-lg hover:bg-client-border/30 transition-colors"
                    >
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-lg bg-client-bg-dark flex items-center justify-center">
                          <FileText className="w-4 h-4 text-client-text-dim" />
                        </div>
                        <div>
                          <div className="font-mono text-sm">{truncateCid(job.job_id)}</div>
                          <div className="text-xs text-client-text-dim">{job.model}</div>
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        <JobStatusBadge status={job.status} />
                        <span className="text-xs text-client-text-muted">
                          {formatDate(job.created_at)}
                        </span>
                      </div>
                    </Link>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}
