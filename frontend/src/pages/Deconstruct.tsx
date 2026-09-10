import { useEffect, useState } from "react"
import { PageKey, Tag } from "../shared"
import { Arrow, Link, Upload } from "../icons"
import { api, errorText, readLocal, writeLocal, uploadAsset, useJob, type Analysis, type Capabilities, type ReferenceVideo } from "../api"

function selectedReference(): ReferenceVideo | null {
  try { return JSON.parse(readLocal("creatoros_reference") ?? "null") } catch { return null }
}

export default function Deconstruct({ go, capabilities }: { go: (k: PageKey) => void; capabilities: Capabilities | null }) {
  const [reference] = useState(selectedReference)
  const [url, setUrl] = useState(reference?.url ?? "")
  const [title, setTitle] = useState(reference?.title ?? "")
  const [transcript, setTranscript] = useState("")
  const [source, setSource] = useState<"url" | "upload">("url")
  const [upload, setUpload] = useState<{ id: string; url: string; name: string } | null>(null)
  const [uploading, setUploading] = useState(false)
  const [analysis, setAnalysis] = useState<Analysis | null>(null)
  const [history, setHistory] = useState<Analysis[]>([])
  const [error, setError] = useState("")
  const [copied, setCopied] = useState("")
  const task = useJob<Analysis>("creatoros_analysis_job", (result) => {
    setAnalysis(result)
    writeLocal("creatoros_analysis_id", result.id)
    setHistory((items) => [result, ...items.filter((item) => item.id !== result.id)])
  })
  useEffect(() => {
    let active = true
    api<Analysis[]>("/analyses").then((items) => { if (active) setHistory(items.filter((item) => item.source.title !== "测试参考视频")) }).catch((e) => { if (active) setError(errorText(e)) })
    return () => { active = false }
  }, [])

  const uploadVideo = async (file?: File) => {
    if (!file) return
    setError("")
    setUploading(true)
    try { setUpload(await uploadAsset(file)) } catch (e) { setError(errorText(e)) }
    finally { setUploading(false) }
  }
  const start = async () => {
    setError("")
    const useUpload = source === "upload"
    await task.submit("/analyses", {
      mode: "live",
      url: useUpload ? "" : url.trim(),
      title: title.trim(),
      transcript,
      uploadId: useUpload ? upload?.id ?? null : null,
      catalogId: !useUpload && reference && url.trim() === reference.url ? reference.id : null,
    })
  }
  const copy = async (label: string, text: string) => {
    try { await navigator.clipboard.writeText(text); setCopied(label) }
    catch { setError("复制失败，请检查浏览器剪贴板权限。") }
  }

  return (
    <div className="flex min-h-0 min-w-0 flex-1 flex-col">
      <div className="flex-1 overflow-auto p-4 sm:p-8 xl:p-10">
        <div className="mx-auto max-w-5xl">
          <div className="flex justify-end">
            <label className="flex max-w-full items-center gap-2 text-[12px] text-sub">
              历史记录
              <select aria-label="拆解历史" disabled={task.busy} value={analysis?.id ?? ""} onChange={(e) => { task.clear(); setAnalysis(history.find((a) => a.id === e.target.value) ?? null) }} className={"max-w-[280px] rounded-lg border border-line bg-card px-3 py-2 text-[13px] outline-none hover:border-slate-300 focus:border-primary " + (analysis ? "text-ink" : "text-sub")}>
                <option value="" disabled hidden className="text-sub">查看历史拆解</option>
                {history.map((item) => <option key={item.id} value={item.id}>{item.source.title}</option>)}
              </select>
            </label>
          </div>
          <fieldset disabled={task.busy || uploading} className="mt-4 space-y-4">
            <section className="rounded-lg border border-line bg-card p-4 sm:p-5">
              <div className="inline-grid grid-cols-2 rounded-lg border border-line bg-canvas p-1" role="tablist" aria-label="视频来源">
                <button type="button" role="tab" aria-selected={source === "url"} onClick={() => { setSource("url"); setError("") }} className={"min-w-28 rounded-md border px-4 py-2 text-[14px] font-medium transition-colors " + (source === "url" ? "border-primary bg-primary/10 text-primary" : "border-transparent text-sub hover:text-ink")}>视频链接</button>
                <button type="button" role="tab" aria-selected={source === "upload"} onClick={() => { setSource("upload"); setError("") }} className={"min-w-28 rounded-md border px-4 py-2 text-[14px] font-medium transition-colors " + (source === "upload" ? "border-primary bg-primary/10 text-primary" : "border-transparent text-sub hover:text-ink")}>本地视频</button>
              </div>
              <div className="mt-4">
                {source === "url" ? (
                  <>
                    <div className="flex min-w-0 items-center gap-3 rounded-lg border border-line bg-canvas px-4 py-3 focus-within:border-primary">
                      <Link className="size-5 shrink-0 text-sub" />
                      <input aria-label="参考视频链接" value={url} onChange={(e) => setUrl(e.target.value)} placeholder="粘贴公开视频链接" className="min-w-0 w-full bg-transparent text-[14px] outline-none" />
                    </div>
                    <p className="mt-2 text-[12px] leading-relaxed text-sub">从趋势雷达进入时会自动带入所选内容链接；平台限制读取时可切换为本地视频。</p>
                  </>
                ) : (
                  <>
                    <label className="flex min-h-[54px] cursor-pointer items-center justify-center gap-2 rounded-lg border border-dashed border-line bg-canvas px-4 py-3 text-[14px] font-medium hover:border-primary/40 hover:text-primary">
                      <Upload className="size-5" />{uploading ? "上传中…" : "选择本地视频"}
                      <input type="file" aria-label="上传参考视频" accept="video/mp4,video/quicktime" className="sr-only" onChange={(e) => { void uploadVideo(e.target.files?.[0]); e.target.value = "" }} />
                    </label>
                    {upload && <div className="mt-2 flex items-center gap-2 text-[12px]"><span className="min-w-0 flex-1 truncate text-sub">{upload.name}</span><button type="button" onClick={() => setUpload(null)} className="shrink-0 text-primary">移除</button></div>}
                    <p className="mt-2 text-[12px] text-sub">支持 MP4 / MOV，最大 64 MB</p>
                  </>
                )}
              </div>
            </section>
            <input aria-label="参考标题" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="参考标题（可选）" className="w-full rounded-lg border border-line bg-card px-4 py-2.5 text-[14px] outline-none focus:border-primary" />
            <label className="block text-[13px] text-sub">
              <span className="font-medium text-ink">补充字幕 / 观察笔记（选填）</span>
              <span className="mt-1 block text-[12px] leading-relaxed">这是你主动补充的视频台词、字幕或画面备注，不是链接自动带出的内容；系统能读取完整视频时可以留空。</span>
              <textarea aria-label="字幕或观察笔记" value={transcript} onChange={(e) => setTranscript(e.target.value)} rows={3} placeholder="例如：粘贴视频台词，或记录关键画面与反转点" className="mt-2 block w-full resize-y rounded-lg border border-line bg-card px-4 py-3 text-[14px] text-ink outline-none focus:border-primary" />
            </label>
            <div className="flex justify-end">
              <button onClick={start} disabled={!capabilities?.analysis || (source === "url" ? !url.trim() && !transcript.trim() : !upload && !transcript.trim())} className="rounded-lg bg-primary px-5 py-3 text-[14px] font-semibold text-white disabled:opacity-50">开始拆解</button>
            </div>
          </fieldset>
          {task.busy && <p role="status" className="mt-4 text-[14px] text-primary">{task.job?.stage ?? "提交任务中…"} · 可稍后返回查看</p>}
          {(error || task.error) && <p role="alert" className="mt-4 break-words text-[14px] text-red-600">{error || task.error}</p>}
          {analysis && (
            <div className="mt-8 grid gap-8 lg:grid-cols-[0.8fr_1.2fr]">
              <section>
                <h2 className="text-[15px] font-semibold text-sub">参考内容</h2>
                {analysis.source.uploadId ? <video controls preload="metadata" src={"/api/uploads/" + analysis.source.uploadId} className="mt-3 aspect-video w-full rounded-lg bg-black object-contain" /> : analysis.source.referenceId ? <img src={"/api/trends/" + analysis.source.referenceId + "/cover"} alt={analysis.source.title} className="mt-3 aspect-video w-full rounded-lg bg-black object-cover" /> : <div className="mt-3 border-y border-line py-5"><h3 className="text-[19px] font-bold">{analysis.source.title}</h3></div>}
                {analysis.source.url && <a href={analysis.source.url} target="_blank" rel="noreferrer" className="mt-3 inline-flex items-center gap-2 text-[14px] text-primary">打开原平台视频 <Arrow className="size-4" /></a>}
                <p className="mt-4 text-[13px] text-sub">{analysis.evidence === "demo" ? "演示结构，未分析原视频。" : analysis.evidence === "text" ? "仅文字分析，画面与声音未经验证。" : analysis.evidence === "cover" ? "基于真实封面与内容元数据的 AI 拆解；完整运动、声音与精确时序未经验证。" : analysis.evidence === "keyframes" ? "基于视频关键帧的视觉分析；音频、完整转场与精确时序未经验证。" : "基于视频画面与补充字幕；不等于恢复原始生成 prompt。"} </p>
                <button disabled={task.busy} onClick={() => { writeLocal("creatoros_analysis_id", analysis.id); writeLocal("creatoros_new_from_analysis", "1"); go("generate") }} className="mt-6 inline-flex items-center gap-2 rounded-lg bg-ink px-5 py-3 text-[14px] font-semibold text-white disabled:opacity-50">基于此结构，生成我的版本 <Arrow className="size-4" /></button>
              </section>
              <section>
                <h2 className="text-[15px] font-semibold text-sub">拆解报告</h2>
                <div className="mt-3 divide-y divide-line border-y border-line">
                  {analysis.report.map((r) => <div key={r.k} className="flex items-start gap-4 py-5"><Tag tone="primary">{r.k}</Tag><p className="min-w-0 break-words text-[14px] leading-relaxed">{r.v}</p></div>)}
                </div>
                <h2 className="mt-6 text-[15px] font-semibold">Prompt 包</h2>
                {([["角色定位", "rolePrompt"], ["原创剧本", "scriptPrompt"], ["分镜提示词", "storyboardPrompt"], ["视频提示词", "videoPrompt"], ["负面提示词", "negativePrompt"], ["封面提示词", "coverPrompt"]] as const).map(([label, key]) => (
                  <details key={key} className="border-b border-line py-3">
                    <summary className="cursor-pointer text-[14px] font-medium">{label}</summary>
                    <p className="mt-3 whitespace-pre-wrap break-words text-[13px] leading-relaxed text-sub">{analysis.promptPack[key] || "暂无"}</p>
                    <button onClick={() => copy(label, analysis.promptPack[key] ?? "")} className="mt-3 text-[13px] text-primary">{copied === label ? "已复制" : "复制提示词"}</button>
                  </details>
                ))}
              </section>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
