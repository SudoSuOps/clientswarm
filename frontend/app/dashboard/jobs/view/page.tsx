'use client'

import { Suspense, useEffect, useState } from 'react'
import { useSearchParams } from 'next/navigation'
import Link from 'next/link'
import Navigation from '@/components/Navigation'
import JobStatusBadge from '@/components/JobStatusBadge'
import {
  ArrowLeft,
  FileText,
  Clock,
  CheckCircle,
  User,
  Download,
  ExternalLink,
  RefreshCw,
  Loader2,
} from 'lucide-react'
import { getJob, refreshJob } from '@/lib/api'
import { formatDate, truncateCid } from '@/lib/utils'

interface Job {
  id: string
  job_id: string
  job_cid: string
  model: string
  input_cid: string
  status: string
  name?: string
  created_at: string
  completed_at?: string
  proof_cid?: string
  output_cid?: string
  confidence?: number
  provider?: string
}

function JobViewContent() {
  const searchParams = useSearchParams()
  const jobId = searchParams.get('id')
  const [job, setJob] = useState<Job | null>(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)

  useEffect(() => {
    if (jobId) {
      fetchJob()
    } else {
      setLoading(false)
    }
  }, [jobId])

  const fetchJob = async () => {
    if (!jobId) return
    try {
      const { data } = await getJob(jobId)
      setJob(data)
    } catch (error) {
      console.error('Failed to fetch job:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleRefresh = async () => {
    if (!jobId) return
    setRefreshing(true)
    try {
      await refreshJob(jobId)
      await fetchJob()
    } catch (error) {
      console.error('Failed to refresh:', error)
    } finally {
      setRefreshing(false)
    }
  }

  if (loading) {
    return (
      <main className="pt-20 pb-12 px-6">
        <div className="max-w-4xl mx-auto text-center py-12">
          <Loader2 className="w-8 h-8 animate-spin mx-auto text-client-teal" />
          <p className="mt-4 text-client-text-dim">Loading job details...</p>
        </div>
      </main>
    )
  }

  if (!jobId || !job) {
    return (
      <main className="pt-20 pb-12 px-6">
        <div className="max-w-4xl mx-auto text-center py-12">
          <FileText className="w-12 h-12 mx-auto mb-4 text-client-text-dim opacity-50" />
          <p className="text-lg">Job not found</p>
          <Link
            href="/dashboard/jobs"
            className="mt-4 inline-flex items-center gap-2 text-client-teal hover:underline"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Jobs
          </Link>
        </div>
      </main>
    )
  }

  return (
    <main className="pt-20 pb-12 px-6">
      <div className="max-w-4xl mx-auto">
        {/* Back Link */}
        <Link
          href="/dashboard/jobs"
          className="inline-flex items-center gap-2 text-client-text-dim hover:text-client-text mb-6"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Jobs
        </Link>

        {/* Header */}
        <div className="flex items-start justify-between mb-8">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <h1 className="text-2xl font-bold font-mono">{truncateCid(job.job_id, 12)}</h1>
              <JobStatusBadge status={job.status} />
            </div>
            {job.name && (
              <p className="text-client-text-dim">{job.name}</p>
            )}
          </div>
          {job.status !== 'completed' && (
            <button
              onClick={handleRefresh}
              disabled={refreshing}
              className="px-4 py-2 bg-client-bg-card border border-client-border rounded-lg hover:border-client-teal transition-colors flex items-center gap-2"
            >
              <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
              Refresh
            </button>
          )}
        </div>

        {/* Timeline */}
        <div className="bg-client-bg-card border border-client-border rounded-xl p-6 mb-6">
          <h2 className="font-semibold mb-4">Timeline</h2>
          <div className="space-y-4">
            <div className="flex items-start gap-4">
              <div className="w-8 h-8 rounded-full bg-client-success/20 flex items-center justify-center">
                <FileText className="w-4 h-4 text-client-success" />
              </div>
              <div>
                <div className="font-medium">Job Submitted</div>
                <div className="text-sm text-client-text-dim">{formatDate(job.created_at)}</div>
              </div>
            </div>

            {job.status === 'pending' && (
              <div className="flex items-start gap-4">
                <div className="w-8 h-8 rounded-full bg-yellow-500/20 flex items-center justify-center">
                  <Clock className="w-4 h-4 text-yellow-400 animate-pulse" />
                </div>
                <div>
                  <div className="font-medium">Waiting for Worker</div>
                  <div className="text-sm text-client-text-dim">Job is in the queue...</div>
                </div>
              </div>
            )}

            {job.status === 'processing' && (
              <div className="flex items-start gap-4">
                <div className="w-8 h-8 rounded-full bg-blue-500/20 flex items-center justify-center">
                  <Loader2 className="w-4 h-4 text-blue-400 animate-spin" />
                </div>
                <div>
                  <div className="font-medium">Processing</div>
                  <div className="text-sm text-client-text-dim">Worker is running inference...</div>
                </div>
              </div>
            )}

            {job.status === 'completed' && (
              <>
                <div className="flex items-start gap-4">
                  <div className="w-8 h-8 rounded-full bg-client-success/20 flex items-center justify-center">
                    <User className="w-4 h-4 text-client-success" />
                  </div>
                  <div>
                    <div className="font-medium">Processed by Worker</div>
                    <div className="text-sm text-client-text-dim font-mono">
                      {job.provider || 'Unknown provider'}
                    </div>
                  </div>
                </div>
                <div className="flex items-start gap-4">
                  <div className="w-8 h-8 rounded-full bg-client-success/20 flex items-center justify-center">
                    <CheckCircle className="w-4 h-4 text-client-success" />
                  </div>
                  <div>
                    <div className="font-medium">Completed</div>
                    <div className="text-sm text-client-text-dim">
                      {job.completed_at ? formatDate(job.completed_at) : 'Just now'}
                    </div>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>

        {/* Details Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
          <div className="bg-client-bg-card border border-client-border rounded-xl p-6">
            <h2 className="font-semibold mb-4">Job Details</h2>
            <div className="space-y-3">
              <div className="flex justify-between text-sm">
                <span className="text-client-text-dim">Model</span>
                <span>{job.model}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-client-text-dim">Job CID</span>
                <a
                  href={`https://ipfs.io/ipfs/${job.job_cid}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-mono text-client-teal hover:underline flex items-center gap-1"
                >
                  {truncateCid(job.job_cid)}
                  <ExternalLink className="w-3 h-3" />
                </a>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-client-text-dim">Input CID</span>
                <a
                  href={`https://ipfs.io/ipfs/${job.input_cid}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-mono text-client-teal hover:underline flex items-center gap-1"
                >
                  {truncateCid(job.input_cid)}
                  <ExternalLink className="w-3 h-3" />
                </a>
              </div>
            </div>
          </div>

          {job.status === 'completed' && (
            <div className="bg-client-bg-card border border-client-border rounded-xl p-6">
              <h2 className="font-semibold mb-4">Results</h2>
              <div className="space-y-3">
                <div className="flex justify-between text-sm">
                  <span className="text-client-text-dim">Confidence</span>
                  <span className="text-client-success font-medium">
                    {job.confidence ? `${(job.confidence * 100).toFixed(0)}%` : '-'}
                  </span>
                </div>
                {job.output_cid && (
                  <div className="flex justify-between text-sm">
                    <span className="text-client-text-dim">Output CID</span>
                    <a
                      href={`https://ipfs.io/ipfs/${job.output_cid}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="font-mono text-client-teal hover:underline flex items-center gap-1"
                    >
                      {truncateCid(job.output_cid)}
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  </div>
                )}
                {job.proof_cid && (
                  <div className="flex justify-between text-sm">
                    <span className="text-client-text-dim">Proof CID</span>
                    <a
                      href={`https://ipfs.io/ipfs/${job.proof_cid}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="font-mono text-client-teal hover:underline flex items-center gap-1"
                    >
                      {truncateCid(job.proof_cid)}
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Download Button */}
        {job.status === 'completed' && job.output_cid && (
          <a
            href={`https://ipfs.io/ipfs/${job.output_cid}`}
            target="_blank"
            rel="noopener noreferrer"
            className="w-full px-6 py-4 bg-client-teal hover:bg-client-teal-light text-white font-semibold rounded-xl transition-colors flex items-center justify-center gap-2"
          >
            <Download className="w-5 h-5" />
            Download Report
          </a>
        )}
      </div>
    </main>
  )
}

function LoadingFallback() {
  return (
    <main className="pt-20 pb-12 px-6">
      <div className="max-w-4xl mx-auto text-center py-12">
        <Loader2 className="w-8 h-8 animate-spin mx-auto text-client-teal" />
        <p className="mt-4 text-client-text-dim">Loading...</p>
      </div>
    </main>
  )
}

export default function JobViewPage() {
  return (
    <div className="min-h-screen bg-client-bg-dark">
      <Navigation />
      <Suspense fallback={<LoadingFallback />}>
        <JobViewContent />
      </Suspense>
    </div>
  )
}
