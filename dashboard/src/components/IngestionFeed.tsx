"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { FileText, Loader2, CheckCircle } from "lucide-react"

type IngestionJob = {
  id: string
  filename: string
  progress: number
  status: "processing" | "completed"
}

export function IngestionFeed() {
  const [jobs, setJobs] = useState<IngestionJob[]>([
    { id: "1", filename: "Q3_Financials.pdf", progress: 100, status: "completed" },
    { id: "2", filename: "HR_Policy_2026.md", progress: 85, status: "processing" },
    { id: "3", filename: "Project_A_Specs.pdf", progress: 42, status: "processing" },
  ])

  // Simulate progress
  useEffect(() => {
    const interval = setInterval(() => {
      setJobs((prev) => 
        prev.map(job => {
          if (job.status === "completed") return job
          const nextProgress = Math.min(job.progress + Math.floor(Math.random() * 10), 100)
          return {
            ...job,
            progress: nextProgress,
            status: nextProgress === 100 ? "completed" : "processing"
          }
        })
      )
    }, 2000)
    return () => clearInterval(interval)
  }, [])

  return (
    <Card className="rounded-sm border-border bg-black h-full flex flex-col">
      <CardHeader>
        <CardTitle className="text-sm font-medium tracking-wide uppercase text-muted-foreground flex justify-between items-center">
          <span>Live Ingestion Feed</span>
          <span className="flex h-2 w-2 rounded-full bg-white animate-pulse" />
        </CardTitle>
      </CardHeader>
      <CardContent className="flex-1 overflow-y-auto pr-2 space-y-4">
        {jobs.map((job) => (
          <div key={job.id} className="p-3 border border-border rounded-sm bg-[#080808]">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center space-x-2 overflow-hidden">
                <FileText className="w-4 h-4 text-muted-foreground flex-shrink-0" />
                <span className="text-xs font-mono text-foreground truncate">{job.filename}</span>
              </div>
              {job.status === "processing" ? (
                <Loader2 className="w-3 h-3 text-muted-foreground animate-spin" />
              ) : (
                <CheckCircle className="w-3 h-3 text-white" />
              )}
            </div>
            <Progress value={job.progress} className="h-1" />
            <div className="text-[10px] text-right mt-1 text-muted-foreground font-mono">
              {job.progress}%
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  )
}
