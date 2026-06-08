import { useQuery } from "@tanstack/react-query"
import { apiFetch } from "@/lib/api"
import { Job } from "@/types"
import { useRouter } from "next/navigation"
import { useEffect } from "react"
import { useRealtimeJob } from "./useRealtimeJob"

export function useJob(jobId: string | null) {
  const router = useRouter()
  useRealtimeJob(jobId)

  const { data: job } = useQuery({
    queryKey: ["job", jobId],
    queryFn: () => apiFetch<Job>(`/jobs/${jobId}`),
    enabled: !!jobId,
    refetchInterval: (query) => {
      const status = query.state.data?.status
      if (status === "completed" || status === "failed" || status === "cancelled") {
        return false
      }
      return 2000
    },
  })

  // Redirect to result when job completes
  useEffect(() => {
    if (!job) return
    if (job.status === "completed" && job.result_id) {
      if (job.job_type === "evaluation") {
        router.push(`/evaluations/${job.result_id}`)
      } else if (job.job_type === "benchmark") {
        router.push(`/benchmarks/runs/${job.result_id}`)
      }
    }
  }, [job, router])

  return job
}