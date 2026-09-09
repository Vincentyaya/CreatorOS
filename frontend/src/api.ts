import { useEffect, useRef, useState } from "react"
import type { AccountSettings } from "./account"

export type Capabilities = { analysis: boolean; script: boolean; video: boolean; videoLive?: boolean; avatar: boolean; publishing: boolean; model: string; videoStrategy?: string }
export type ContentCharacter = { id: string; source: "library" | "generated" | "upload"; emoji: string; name: string; desc: string; accent: string; img?: string }
export type Scene = { index: number; duration_sec: number; visual: string; narration: string; on_screen_text: string; speaker: string; emotion: string }
export type Script = { title: string; hook: string; scenes: Scene[]; cta: string; caption: string; hashtags: string[] }
export type Draft = { id: string; mode: "demo" | "live"; topic: string; analysisId: string | null; script: Script; revision: number; characters: ContentCharacter[]; account: AccountSettings; video: { url: string; status: string; provider?: string; audio?: string; demo?: boolean } | null; prompts: { clips: { index: number; prompt: string; narration: string }[] } | null }
export type Analysis = { id: string; mode: "demo" | "live"; evidence: "demo" | "text" | "video" | "keyframes"; source: { title: string; url: string; uploadId: string | null; referenceId?: string | null }; report: { k: string; v: string }[]; promptPack: { rolePrompt: string; scriptPrompt: string; storyboardPrompt: string; videoPrompt: string; negativePrompt?: string; coverPrompt: string; rewriteGuardrails: string[] }; createdAt: string }
export type ReferenceVideo = { id: string; platform: string; title: string; author?: string; url: string; poster: string; likes?: string; plays?: string; angle: string; publishedAt?: string; category: string; metricsMode?: "source" | "official" | "unavailable"; localReference?: boolean }
export type Catalog = { mode: "demo" | "hybrid" | "official" | "source"; notice: string; verifiedAt: string; range?: string; fetchedAt?: string; picks: { topic: string; match: number; angle: string; hot: string; referenceId: string }[]; videos: ReferenceVideo[] }
export type TopicPoolItem = { id: string; topic: string; angle: string; referenceId: string; status: "待研究" | "已拆解" | "已生成" | "已发布" | "已复盘"; source?: "trend" | "review" }
export type Job<T> = { id: string; kind: string; status: "queued" | "running" | "completed" | "failed"; stage: string; result: T | null; error: string | null }

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), 20000)
  try {
    const response = await fetch("/api" + path, {
      ...options,
      signal: options.signal ?? controller.signal,
      headers: { ...(options.body instanceof FormData ? {} : { "Content-Type": "application/json" }), "X-CreatorOS-Client": "local-preview", ...options.headers },
    })
    const contentType = response.headers.get("content-type") ?? ""
    if (!contentType.includes("application/json")) throw new Error("后端未连接，请检查本地 API 服务。")
    const data = await response.json()
    if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : data.error ?? "请求失败，请重试。")
    return data as T
  } catch (error) {
    if (error instanceof Error && error.name === "AbortError") throw new Error("请求超时，请重试。")
    throw error
  } finally {
    clearTimeout(timeout)
  }
}

export const post = <T,>(path: string, body: unknown = {}) => api<T>(path, { method: "POST", body: JSON.stringify(body) })
export const errorText = (error: unknown) => error instanceof Error ? error.message : "请求失败，请重试。"

export async function uploadAsset(file: File) {
  const body = new FormData()
  body.set("file", file)
  return api<{ id: string; url: string; name: string }>("/uploads", { method: "POST", body })
}

export function readLocal(key: string) {
  try { return localStorage.getItem(key) } catch { return null }
}
export function writeLocal(key: string, value: string | null) {
  try { value === null ? localStorage.removeItem(key) : localStorage.setItem(key, value) } catch { /* Server persistence remains authoritative. */ }
}

export function useJob<T>(key: string, onComplete: (result: T) => void) {
  const [id, setId] = useState(() => readLocal(key))
  const [job, setJob] = useState<Job<T> | null>(null)
  const [error, setError] = useState("")
  const [submitting, setSubmitting] = useState(false)
  const completeRef = useRef(onComplete)
  completeRef.current = onComplete
  useEffect(() => {
    if (!id) return
    let stopped = false
    let timer: ReturnType<typeof setTimeout>
    const poll = async () => {
      try {
        const current = await api<Job<T>>("/jobs/" + id)
        if (stopped) return
        setJob(current)
        setError("")
        if (current.status === "completed" && current.result) {
          completeRef.current(current.result)
          writeLocal(key, null)
          setId(null)
          return
        }
        if (current.status === "failed") {
          setError(current.error ?? "任务失败")
          return
        }
      } catch (e) {
        if (stopped) return
        setError(errorText(e))
      }
      timer = setTimeout(poll, 1500)
    }
    void poll()
    return () => { stopped = true; clearTimeout(timer) }
  }, [id])
  const submit = async (path: string, body: unknown = {}) => {
    setSubmitting(true)
    setError("")
    try {
      const next = await post<Job<T>>(path, body)
      setJob(next)
      writeLocal(key, next.id)
      setId(next.id)
      return next
    } catch (e) {
      setError(errorText(e))
      return null
    } finally { setSubmitting(false) }
  }
  const clear = () => { setId(null); setJob(null); setError(""); writeLocal(key, null) }
  return { job, error, submit, clear, busy: submitting || Boolean(id && (!job || job.status === "queued" || job.status === "running")) }
}
