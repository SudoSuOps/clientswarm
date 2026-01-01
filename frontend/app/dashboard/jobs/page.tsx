'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import Navigation from '@/components/Navigation'
import JobStatusBadge from '@/components/JobStatusBadge'
import { FileText, Search, Filter, ChevronLeft, ChevronRight, ExternalLink } from 'lucide-react'
import { listJobs } from '@/lib/api'
import { formatDate, truncateCid } from '@/lib/utils'
import { cn } from '@/lib/utils'

interface Job {
  id: string
  job_id: string
  job_cid: string
  model: string
  status: string
  name?: string
  created_at: string
  completed_at?: string
  confidence?: number
  provider?: string
}

const STATUS_FILTERS = [
  { value: '', label: 'All' },
  { value: 'pending', label: 'Pending' },
  { value: 'processing', label: 'Processing' },
  { value: 'completed', label: 'Completed' },
  { value: 'failed', label: 'Failed' },
]

export default function JobsPage() {
  const [jobs, setJobs] = useState<Job[]>([])
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [statusFilter, setStatusFilter] = useState('')
  const [searchQuery, setSearchQuery] = useState('')

  const perPage = 20

  useEffect(() => {
    fetchJobs()
  }, [page, statusFilter])

  const fetchJobs = async () => {
    setLoading(true)
    try {
      const { data } = await listJobs(page, statusFilter || undefined)
      setJobs(data.jobs)
      setTotal(data.total)
    } catch (error) {
      console.error('Failed to fetch jobs:', error)
    } finally {
      setLoading(false)
    }
  }

  const filteredJobs = searchQuery
    ? jobs.filter(
        (job) =>
          job.job_id.includes(searchQuery) ||
          job.name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
          job.model.toLowerCase().includes(searchQuery.toLowerCase())
      )
    : jobs

  const totalPages = Math.ceil(total / perPage)

  return (
    <div className="min-h-screen bg-client-bg-dark">
      <Navigation />

      <main className="pt-20 pb-12 px-6">
        <div className="max-w-6xl mx-auto">
          <div className="flex items-center justify-between mb-8">
            <div>
              <h1 className="text-2xl font-bold mb-2">Jobs</h1>
              <p className="text-client-text-dim">
                Track and manage your inference jobs
              </p>
            </div>
            <Link
              href="/dashboard/upload"
              className="px-5 py-2.5 bg-client-teal hover:bg-client-teal-light text-white font-medium rounded-lg transition-colors"
            >
              New Job
            </Link>
          </div>

          {/* Filters */}
          <div className="flex flex-col md:flex-row gap-4 mb-6">
            {/* Search */}
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-client-text-dim" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search by job ID, name, or model..."
                className="w-full pl-10 pr-4 py-2.5 bg-client-bg-card border border-client-border rounded-lg focus:outline-none focus:border-client-teal"
              />
            </div>

            {/* Status Filter */}
            <div className="flex items-center gap-2">
              <Filter className="w-5 h-5 text-client-text-dim" />
              <div className="flex gap-1">
                {STATUS_FILTERS.map((filter) => (
                  <button
                    key={filter.value}
                    onClick={() => {
                      setStatusFilter(filter.value)
                      setPage(1)
                    }}
                    className={cn(
                      'px-3 py-1.5 text-sm rounded-lg transition-colors',
                      statusFilter === filter.value
                        ? 'bg-client-teal text-white'
                        : 'bg-client-bg-card text-client-text-dim hover:text-client-text'
                    )}
                  >
                    {filter.label}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Jobs Table */}
          <div className="bg-client-bg-card border border-client-border rounded-xl overflow-hidden">
            {loading ? (
              <div className="p-12 text-center text-client-text-dim">
                Loading jobs...
              </div>
            ) : filteredJobs.length === 0 ? (
              <div className="p-12 text-center text-client-text-dim">
                <FileText className="w-12 h-12 mx-auto mb-4 opacity-50" />
                <p className="text-lg mb-2">No jobs found</p>
                <p className="text-sm">Upload a scan to create your first job</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="text-left text-xs text-client-text-muted uppercase tracking-wider border-b border-client-border">
                      <th className="px-6 py-4 font-medium">Job ID</th>
                      <th className="px-6 py-4 font-medium">Model</th>
                      <th className="px-6 py-4 font-medium">Status</th>
                      <th className="px-6 py-4 font-medium">Confidence</th>
                      <th className="px-6 py-4 font-medium">Created</th>
                      <th className="px-6 py-4 font-medium"></th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-client-border">
                    {filteredJobs.map((job) => (
                      <tr key={job.id} className="hover:bg-client-bg-elevated/50">
                        <td className="px-6 py-4">
                          <div className="font-mono text-sm">{truncateCid(job.job_id)}</div>
                          {job.name && (
                            <div className="text-xs text-client-text-dim">{job.name}</div>
                          )}
                        </td>
                        <td className="px-6 py-4 text-sm text-client-text-dim">
                          {job.model}
                        </td>
                        <td className="px-6 py-4">
                          <JobStatusBadge status={job.status} />
                        </td>
                        <td className="px-6 py-4 text-sm">
                          {job.confidence ? (
                            <span className="text-client-success">
                              {(job.confidence * 100).toFixed(0)}%
                            </span>
                          ) : (
                            <span className="text-client-text-muted">-</span>
                          )}
                        </td>
                        <td className="px-6 py-4 text-sm text-client-text-dim">
                          {formatDate(job.created_at)}
                        </td>
                        <td className="px-6 py-4">
                          <Link
                            href={`/dashboard/jobs/${job.job_id}`}
                            className="p-2 text-client-text-dim hover:text-client-teal transition-colors"
                          >
                            <ExternalLink className="w-4 h-4" />
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between px-6 py-4 border-t border-client-border">
                <div className="text-sm text-client-text-dim">
                  Showing {(page - 1) * perPage + 1} - {Math.min(page * perPage, total)} of {total}
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    disabled={page === 1}
                    className="p-2 rounded-lg bg-client-bg-elevated hover:bg-client-border disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <ChevronLeft className="w-4 h-4" />
                  </button>
                  <span className="text-sm px-3">
                    Page {page} of {totalPages}
                  </span>
                  <button
                    onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                    disabled={page === totalPages}
                    className="p-2 rounded-lg bg-client-bg-elevated hover:bg-client-border disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <ChevronRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  )
}
