import { cn } from '@/lib/utils'

const statusConfig: Record<string, { bg: string; text: string; dot: string }> = {
  pending: {
    bg: 'bg-yellow-500/10',
    text: 'text-yellow-400',
    dot: 'bg-yellow-400',
  },
  processing: {
    bg: 'bg-blue-500/10',
    text: 'text-blue-400',
    dot: 'bg-blue-400 animate-pulse',
  },
  completed: {
    bg: 'bg-green-500/10',
    text: 'text-green-400',
    dot: 'bg-green-400',
  },
  failed: {
    bg: 'bg-red-500/10',
    text: 'text-red-400',
    dot: 'bg-red-400',
  },
}

interface JobStatusBadgeProps {
  status: string
  className?: string
}

export default function JobStatusBadge({ status, className }: JobStatusBadgeProps) {
  const config = statusConfig[status] || statusConfig.pending

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium',
        config.bg,
        config.text,
        className
      )}
    >
      <span className={cn('w-1.5 h-1.5 rounded-full', config.dot)} />
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  )
}
