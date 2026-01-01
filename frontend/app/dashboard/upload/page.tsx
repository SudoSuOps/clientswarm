'use client'

import { useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { useDropzone } from 'react-dropzone'
import Navigation from '@/components/Navigation'
import { Upload, File, X, Loader2, CheckCircle, AlertCircle } from 'lucide-react'
import { uploadFile, submitJob } from '@/lib/api'
import { cn } from '@/lib/utils'

const MODELS = [
  { id: 'queenbee-spine', name: 'Spine MRI', description: 'Lumbar stenosis detection' },
  { id: 'queenbee-chest', name: 'Chest CT', description: 'Nodule detection' },
  { id: 'queenbee-ankle', name: 'Foot/Ankle', description: 'Fracture detection' },
]

export default function UploadPage() {
  const router = useRouter()
  const [files, setFiles] = useState<File[]>([])
  const [model, setModel] = useState(MODELS[0].id)
  const [jobName, setJobName] = useState('')
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState<'idle' | 'uploading' | 'submitting' | 'done' | 'error'>('idle')
  const [error, setError] = useState('')
  const [resultJobId, setResultJobId] = useState('')

  const onDrop = useCallback((acceptedFiles: File[]) => {
    setFiles((prev) => [...prev, ...acceptedFiles])
    setError('')
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/dicom': ['.dcm'],
      'application/x-nifti': ['.nii', '.nii.gz'],
      'image/png': ['.png'],
      'image/jpeg': ['.jpg', '.jpeg'],
      'application/gzip': ['.gz'],
    },
    maxSize: 500 * 1024 * 1024, // 500MB
  })

  const removeFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index))
  }

  const handleSubmit = async () => {
    if (files.length === 0) {
      setError('Please add at least one file')
      return
    }

    setUploading(true)
    setUploadProgress('uploading')
    setError('')

    try {
      // Upload first file (in production: handle multiple)
      const uploadRes = await uploadFile(files[0])
      const inputCid = uploadRes.data.cid

      setUploadProgress('submitting')

      // Submit job
      const jobRes = await submitJob(model, inputCid, jobName || undefined)
      const jobId = jobRes.data.job_id

      setResultJobId(jobId)
      setUploadProgress('done')

      // Redirect after delay
      setTimeout(() => {
        router.push(`/dashboard/jobs/${jobId}`)
      }, 2000)
    } catch (err: any) {
      console.error('Upload error:', err)
      setError(err.response?.data?.detail || 'Failed to submit job')
      setUploadProgress('error')
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="min-h-screen bg-client-bg-dark">
      <Navigation />

      <main className="pt-20 pb-12 px-6">
        <div className="max-w-3xl mx-auto">
          <h1 className="text-2xl font-bold mb-2">Upload Scan</h1>
          <p className="text-client-text-dim mb-8">
            Upload your medical imaging files to submit a new inference job.
          </p>

          {/* Progress States */}
          {uploadProgress !== 'idle' && uploadProgress !== 'error' && (
            <div className="mb-8 p-6 bg-client-bg-card border border-client-border rounded-xl">
              <div className="flex items-center gap-4">
                {uploadProgress === 'done' ? (
                  <CheckCircle className="w-8 h-8 text-client-success" />
                ) : (
                  <Loader2 className="w-8 h-8 text-client-teal animate-spin" />
                )}
                <div>
                  <div className="font-medium">
                    {uploadProgress === 'uploading' && 'Uploading to IPFS...'}
                    {uploadProgress === 'submitting' && 'Submitting job to SwarmPool...'}
                    {uploadProgress === 'done' && 'Job submitted successfully!'}
                  </div>
                  {uploadProgress === 'done' && (
                    <div className="text-sm text-client-text-dim">
                      Job ID: {resultJobId}
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {error && (
            <div className="mb-8 p-4 bg-client-error/10 border border-client-error/30 text-client-error rounded-xl flex items-center gap-3">
              <AlertCircle className="w-5 h-5 flex-shrink-0" />
              {error}
            </div>
          )}

          {/* Dropzone */}
          <div
            {...getRootProps()}
            className={cn(
              'p-12 border-2 border-dashed rounded-xl text-center cursor-pointer transition-colors mb-6',
              isDragActive
                ? 'border-client-teal bg-client-teal/10'
                : 'border-client-border hover:border-client-teal/50 bg-client-bg-card'
            )}
          >
            <input {...getInputProps()} />
            <Upload className="w-12 h-12 text-client-text-dim mx-auto mb-4" />
            <p className="text-lg font-medium mb-2">
              {isDragActive ? 'Drop files here' : 'Drag & drop files here'}
            </p>
            <p className="text-sm text-client-text-dim">
              or click to browse. Supports DICOM, NIfTI, PNG, JPEG
            </p>
          </div>

          {/* File List */}
          {files.length > 0 && (
            <div className="mb-6 space-y-2">
              {files.map((file, index) => (
                <div
                  key={index}
                  className="flex items-center justify-between p-4 bg-client-bg-card border border-client-border rounded-lg"
                >
                  <div className="flex items-center gap-3">
                    <File className="w-5 h-5 text-client-text-dim" />
                    <div>
                      <div className="font-medium text-sm">{file.name}</div>
                      <div className="text-xs text-client-text-dim">
                        {(file.size / 1024 / 1024).toFixed(2)} MB
                      </div>
                    </div>
                  </div>
                  <button
                    onClick={() => removeFile(index)}
                    className="p-1 text-client-text-dim hover:text-client-error transition-colors"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              ))}
            </div>
          )}

          {/* Model Selection */}
          <div className="mb-6">
            <label className="block text-sm font-medium text-client-text-dim mb-3">
              Select Model
            </label>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {MODELS.map((m) => (
                <button
                  key={m.id}
                  onClick={() => setModel(m.id)}
                  className={cn(
                    'p-4 rounded-lg border text-left transition-colors',
                    model === m.id
                      ? 'border-client-teal bg-client-teal/10'
                      : 'border-client-border bg-client-bg-card hover:border-client-teal/50'
                  )}
                >
                  <div className="font-medium mb-1">{m.name}</div>
                  <div className="text-xs text-client-text-dim">{m.description}</div>
                </button>
              ))}
            </div>
          </div>

          {/* Job Name */}
          <div className="mb-8">
            <label className="block text-sm font-medium text-client-text-dim mb-2">
              Job Name (optional)
            </label>
            <input
              type="text"
              value={jobName}
              onChange={(e) => setJobName(e.target.value)}
              placeholder="e.g., Patient ABC - Lumbar MRI"
              className="w-full px-4 py-3 bg-client-bg-card border border-client-border rounded-lg focus:outline-none focus:border-client-teal"
            />
          </div>

          {/* Submit Button */}
          <button
            onClick={handleSubmit}
            disabled={files.length === 0 || uploading}
            className="w-full px-6 py-4 bg-client-teal hover:bg-client-teal-light text-white font-semibold rounded-xl transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            {uploading ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Processing...
              </>
            ) : (
              <>
                <Upload className="w-5 h-5" />
                Submit Job ($0.10)
              </>
            )}
          </button>

          <p className="text-center text-sm text-client-text-muted mt-4">
            Your scan will be processed by the SwarmPool network
          </p>
        </div>
      </main>
    </div>
  )
}
