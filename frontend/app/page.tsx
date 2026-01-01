'use client'

import Link from 'next/link'
import { Shield, Zap, FileCheck, ArrowRight } from 'lucide-react'

export default function LandingPage() {
  return (
    <div className="min-h-screen">
      {/* Navigation */}
      <nav className="fixed top-0 left-0 right-0 z-50 bg-client-bg-dark/80 backdrop-blur-lg border-b border-client-border">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-client-teal to-client-blue flex items-center justify-center">
              <Shield className="w-5 h-5 text-white" />
            </div>
            <span className="text-xl font-semibold">ClientSwarm</span>
          </div>
          <div className="flex items-center gap-4">
            <Link
              href="/login"
              className="px-4 py-2 text-client-text-dim hover:text-client-text transition-colors"
            >
              Sign In
            </Link>
            <Link
              href="/register"
              className="px-5 py-2.5 bg-client-teal hover:bg-client-teal-light text-white font-medium rounded-lg transition-colors"
            >
              Get Started
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="pt-32 pb-20 px-6">
        <div className="max-w-4xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-client-bg-card border border-client-border mb-8">
            <span className="w-2 h-2 rounded-full bg-client-success animate-pulse" />
            <span className="text-sm text-client-text-dim">Network Operational</span>
          </div>

          <h1 className="text-4xl md:text-6xl font-bold mb-6">
            <span className="text-client-text">Medical Imaging</span>
            <br />
            <span className="text-client-teal">Decentralized</span>
          </h1>

          <p className="text-xl text-client-text-dim mb-8 max-w-2xl mx-auto">
            Submit scans to the SwarmPool network. Get AI-powered analysis from sovereign compute providers. Pay per scan.
          </p>

          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link
              href="/register"
              className="px-8 py-3 bg-client-teal hover:bg-client-teal-light text-white font-semibold rounded-lg transition-colors flex items-center justify-center gap-2"
            >
              Start Free Trial
              <ArrowRight className="w-5 h-5" />
            </Link>
            <Link
              href="/login"
              className="px-8 py-3 bg-client-bg-card hover:bg-client-bg-elevated border border-client-border text-client-text font-semibold rounded-lg transition-colors"
            >
              Sign In with Wallet
            </Link>
          </div>

          <p className="text-sm text-client-text-muted mt-4">
            10 free scans included. No credit card required.
          </p>
        </div>
      </section>

      {/* Features */}
      <section className="py-20 px-6 bg-client-bg-card/50">
        <div className="max-w-5xl mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="p-6 bg-client-bg-card border border-client-border rounded-xl">
              <div className="w-12 h-12 rounded-lg bg-client-teal/20 flex items-center justify-center mb-4">
                <Shield className="w-6 h-6 text-client-teal" />
              </div>
              <h3 className="text-lg font-semibold mb-2">HIPAA Ready</h3>
              <p className="text-client-text-dim text-sm">
                Your data is encrypted end-to-end. Workers never see raw patient data. Only CIDs move through the network.
              </p>
            </div>

            <div className="p-6 bg-client-bg-card border border-client-border rounded-xl">
              <div className="w-12 h-12 rounded-lg bg-client-blue/20 flex items-center justify-center mb-4">
                <Zap className="w-6 h-6 text-client-blue" />
              </div>
              <h3 className="text-lg font-semibold mb-2">Fast Results</h3>
              <p className="text-client-text-dim text-sm">
                Distributed GPU network means quick turnaround. Most scans complete in under 2 minutes.
              </p>
            </div>

            <div className="p-6 bg-client-bg-card border border-client-border rounded-xl">
              <div className="w-12 h-12 rounded-lg bg-client-success/20 flex items-center justify-center mb-4">
                <FileCheck className="w-6 h-6 text-client-success" />
              </div>
              <h3 className="text-lg font-semibold mb-2">Cryptographic Proof</h3>
              <p className="text-client-text-dim text-sm">
                Every result includes a signed proof. Verify the worker, the model version, and the confidence score.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section className="py-20 px-6">
        <div className="max-w-3xl mx-auto text-center">
          <h2 className="text-3xl font-bold mb-4">Simple Pricing</h2>
          <p className="text-client-text-dim mb-12">Pay per scan. No subscriptions. No minimums.</p>

          <div className="bg-client-bg-card border border-client-border rounded-2xl p-8">
            <div className="text-5xl font-bold text-client-teal mb-2">$0.10</div>
            <div className="text-client-text-dim mb-6">per scan</div>

            <ul className="text-left space-y-3 mb-8">
              <li className="flex items-center gap-3 text-client-text-dim">
                <span className="w-5 h-5 rounded-full bg-client-success/20 flex items-center justify-center">
                  <span className="w-2 h-2 rounded-full bg-client-success" />
                </span>
                10 free scans to start
              </li>
              <li className="flex items-center gap-3 text-client-text-dim">
                <span className="w-5 h-5 rounded-full bg-client-success/20 flex items-center justify-center">
                  <span className="w-2 h-2 rounded-full bg-client-success" />
                </span>
                Pay with card or USDC
              </li>
              <li className="flex items-center gap-3 text-client-text-dim">
                <span className="w-5 h-5 rounded-full bg-client-success/20 flex items-center justify-center">
                  <span className="w-2 h-2 rounded-full bg-client-success" />
                </span>
                No data retained after processing
              </li>
              <li className="flex items-center gap-3 text-client-text-dim">
                <span className="w-5 h-5 rounded-full bg-client-success/20 flex items-center justify-center">
                  <span className="w-2 h-2 rounded-full bg-client-success" />
                </span>
                API access included
              </li>
            </ul>

            <Link
              href="/register"
              className="w-full px-8 py-3 bg-client-teal hover:bg-client-teal-light text-white font-semibold rounded-lg transition-colors inline-block text-center"
            >
              Start Free Trial
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-client-border py-12 px-6">
        <div className="max-w-5xl mx-auto flex flex-col md:flex-row justify-between items-center gap-6">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-client-teal to-client-blue flex items-center justify-center">
              <Shield className="w-4 h-4 text-white" />
            </div>
            <span className="font-semibold">ClientSwarm</span>
          </div>

          <div className="flex items-center gap-6 text-sm text-client-text-dim">
            <a href="https://swarmpool.eth.limo" className="hover:text-client-text">SwarmPool</a>
            <a href="https://swarmorb.eth.limo" className="hover:text-client-text">Explorer</a>
            <a href="https://docs.swarmpool.eth" className="hover:text-client-text">Docs</a>
          </div>

          <div className="text-sm text-client-text-muted">
            Powered by SwarmPool
          </div>
        </div>
      </footer>
    </div>
  )
}
