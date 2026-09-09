import { useEffect, useState } from "react"
import { api, errorText, post, readLocal, writeLocal, useJob, type Draft, type Script, type ContentCharacter } from "./api"

export function useContentWorkflow(characters: ContentCharacter[], topic: string, onRestore: (draft: Draft) => void) {
  const [draft, setDraft] = useState<Draft | null>(null)
  const [script, setScript] = useState<Script | null>(null)
  const [error, setError] = useState("")
  const [notice, setNotice] = useState("")
  const [working, setWorking] = useState(false)
  const [history, setHistory] = useState<Draft[]>([])
  const [analysisId, setAnalysisId] = useState(() => readLocal("creatoros_analysis_id"))
  const accept = (result: Draft) => {
    setDraft(result)
    setScript(result.script)
    writeLocal("creatoros_draft_id", result.id)
    setHistory((items) => [result, ...items.filter((d) => d.id !== result.id)])
    onRestore(result)
  }
  const task = useJob<Draft>("creatoros_content_job", accept)
  useEffect(() => {
    let active = true
    api<Draft[]>("/drafts").then((items) => { if (active) setHistory(items) }).catch((e) => { if (active) setError(errorText(e)) })
    if (readLocal("creatoros_new_from_analysis")) {
      task.clear()
      writeLocal("creatoros_draft_id", null)
      writeLocal("creatoros_new_from_analysis", null)
    } else {
      const id = readLocal("creatoros_draft_id")
      if (id && !readLocal("creatoros_content_job")) api<Draft>("/drafts/" + id).then((d) => { if (active) accept(d) }).catch((e) => { if (active) setError(errorText(e)) })
    }
    return () => { active = false }
  }, [])

  const reset = () => {
    task.clear()
    setDraft(null); setScript(null); setError(""); setNotice("")
    writeLocal("creatoros_draft_id", null)
  }
  const generate = async (mode: "live" | "demo") => {
    setError(""); setNotice("")
    await task.submit("/drafts", { characters, topic, analysisId, mode })
  }
  const save = async (): Promise<Draft> => {
    if (!draft || !script) throw new Error("请先生成剧本")
    if (JSON.stringify(script) === JSON.stringify(draft.script)) return draft
    const saved = await api<Draft>("/drafts/" + draft.id, { method: "PATCH", body: JSON.stringify({ script, revision: draft.revision }) })
    setDraft(saved); setScript(saved.script)
    return saved
  }
  const perform = async (action: () => Promise<void>) => {
    setError(""); setNotice(""); setWorking(true)
    try { await action() } catch (e) { setError(errorText(e)) }
    finally { setWorking(false) }
  }
  const saveChanges = () => perform(async () => { await save(); setNotice("草稿已保存") })
  const render = () => perform(async () => {
    const saved = await save()
    await task.submit("/drafts/" + saved.id + "/video")
  })
  const exportPackage = () => perform(async () => {
    const saved = await save()
    const result = await post<{ url: string; containsVideo: boolean }>("/drafts/" + saved.id + "/export")
    const link = document.createElement("a")
    link.href = result.url; link.download = "creatoros-publish.zip"; link.click()
    setNotice(result.containsVideo ? "发布包已导出，包含成片" : "文案包已导出，尚未生成视频")
  })
  const queue = (platforms: string[]) => perform(async () => {
    const saved = await save()
    const result = await post<{ message: string }>("/drafts/" + saved.id + "/queue", { platforms })
    setNotice(result.message)
  })
  const restore = (id: string) => perform(async () => {
    const saved = await api<Draft>("/drafts/" + id)
    task.clear()
    setAnalysisId(saved.analysisId)
    accept(saved)
  })
  return { draft, script, setScript, generate, reset, saveChanges, render, exportPackage, queue, restore, history,
    analysisId, clearAnalysis: () => { setAnalysisId(null); writeLocal("creatoros_analysis_id", null) },
    busy: working || task.busy, stage: task.job?.stage ?? "提交中…", error: error || task.error, notice }
}

