'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { Shield, LayoutDashboard, Upload, FileText, Settings, LogOut } from 'lucide-react'
import { useAuth } from '@/lib/hooks/useAuth'
import { truncateAddress } from '@/lib/utils'
import { cn } from '@/lib/utils'

const navItems = [
  { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/dashboard/upload', label: 'Upload', icon: Upload },
  { href: '/dashboard/jobs', label: 'Jobs', icon: FileText },
  { href: '/dashboard/settings', label: 'Settings', icon: Settings },
]

export default function Navigation() {
  const pathname = usePathname()
  const { client, logout } = useAuth()

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-client-bg-dark/80 backdrop-blur-lg border-b border-client-border">
      <div className="max-w-7xl mx-auto px-6 py-3 flex items-center justify-between">
        {/* Logo */}
        <Link href="/dashboard" className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-client-teal to-client-blue flex items-center justify-center">
            <Shield className="w-5 h-5 text-white" />
          </div>
          <span className="text-lg font-semibold hidden sm:block">ClientSwarm</span>
        </Link>

        {/* Nav Links */}
        <div className="flex items-center gap-1">
          {navItems.map((item) => {
            const Icon = item.icon
            const isActive = pathname === item.href || pathname.startsWith(item.href + '/')

            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  'px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2',
                  isActive
                    ? 'bg-client-bg-card text-client-text'
                    : 'text-client-text-dim hover:text-client-text hover:bg-client-bg-card/50'
                )}
              >
                <Icon className="w-4 h-4" />
                <span className="hidden md:inline">{item.label}</span>
              </Link>
            )
          })}
        </div>

        {/* User */}
        <div className="flex items-center gap-4">
          <div className="text-right hidden sm:block">
            <div className="text-sm font-medium">
              {client?.ens || truncateAddress(client?.wallet || '')}
            </div>
            <div className="text-xs text-client-text-dim">
              {client?.free_scans_remaining} free scans
            </div>
          </div>
          <button
            onClick={logout}
            className="p-2 text-client-text-dim hover:text-client-text transition-colors"
            title="Logout"
          >
            <LogOut className="w-5 h-5" />
          </button>
        </div>
      </div>
    </nav>
  )
}
