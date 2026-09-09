import { useEffect, useRef, useState } from "react"
import { Check, Sparkle, Upload } from "../icons"
import { api, errorText, post, type Job } from "../api"

type Props = {
  name: string
  prompt: string
  avatar?: string
  applyLabel?: string
  onApply: (avatar: string, prompt: string) => void
  onClose: () => void
}

const EXAMPLES = {
  cat: "/avatars/tiantian.png",
  dog: "/avatars/tiezhu.png",
}

export default function CharacterAvatarDialog({ name, prompt: initialPrompt, avatar, applyLabel = "应用到头像", onApply, onClose }: Props) {
  const dialog = useRef<HTMLDialogElement>(null)
  const upload = useRef<HTMLInputElement>(null)
  const request = useRef(0)
  const [prompt, setPrompt] = useState(initialPrompt)
  const [subject, setSubject] = useState<keyof typeof EXAMPLES>(/犬|狗|铁柱/.test(initialPrompt) ? "dog" : "cat")
  const [preview, setPreview] = useState(avatar ?? "")
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState("")

  useEffect(() => {
    const element = dialog.current!
    element.showModal()
    return () => {
      request.current += 1
      element.close()
    }
  }, [])

  const generatePreview = async () => {
    if (!prompt.trim()) return
    const current = ++request.current
    setBusy(true)
    setError("")
    try {
      type Avatar = { id: string; url: string; name: string }
      let job = await post<Job<Avatar>>("/avatars", {
        name,
        prompt: `${prompt.trim()}。角色类型：${subject === "dog" ? "犬类" : "猫科"}`,
      })
      const deadline = Date.now() + 240_000
      while (job.status === "queued" || job.status === "running") {
        if (Date.now() > deadline) throw new Error("角色生图超时，请稍后在素材记录中重试。")
        await new Promise((resolve) => setTimeout(resolve, 1500))
        job = await api<Job<Avatar>>("/jobs/" + job.id)
      }
      if (job.status === "failed" || !job.result) throw new Error(job.error || "角色生图失败，请重试或上传图片。")
      if (request.current === current) setPreview(job.result.url)
    } catch (err) {
      if (request.current === current) setError(errorText(err))
    } finally {
      if (request.current === current) setBusy(false)
    }
  }

  const onUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    event.target.value = ""
    if (!file) return
    if (!["image/png", "image/jpeg", "image/webp"].includes(file.type)) {
      setError("请选择 PNG、JPG 或 WebP 图片。")
      return
    }
    if (file.size > 1024 * 1024) {
      setError("请选择小于 1 MB 的头像图片。")
      return
    }
    const current = ++request.current
    setError("")
    setBusy(true)
    const reader = new FileReader()
    reader.onload = () => {
      if (request.current !== current) return
      setPreview(String(reader.result))
      setBusy(false)
    }
    reader.onerror = () => {
      if (request.current !== current) return
      setError("图片读取失败，请重新选择。")
      setBusy(false)
    }
    reader.readAsDataURL(file)
  }

  return (
    <dialog
      ref={dialog}
      aria-labelledby="avatar-dialog-title"
      onCancel={(event) => { event.preventDefault(); onClose() }}
      onClick={(event) => { if (event.target === event.currentTarget) onClose() }}
      className="m-auto max-h-[calc(100dvh_-_2rem)] w-[calc(100%_-_2rem)] max-w-md overflow-y-auto rounded-lg border border-line bg-card p-0 text-ink shadow-xl backdrop:bg-ink/40 backdrop:backdrop-blur-sm"
    >
      <div className="border-b border-line px-5 py-4 flex items-center justify-between gap-3">
        <h2 id="avatar-dialog-title" className="min-w-0 break-words text-[18px] font-bold">{name}的头像</h2>
        <span className="shrink-0 rounded-md bg-primary/10 px-2 py-1 text-[11px] text-primary">AI 生图</span>
      </div>
      <div className="p-5 space-y-4">
        <div className="relative mx-auto grid aspect-square w-40 place-items-center overflow-hidden rounded-lg border border-line bg-canvas" aria-busy={busy}>
          {preview ? (
            <img
              src={preview}
              alt={`${name}头像预览`}
              className="size-full object-cover"
              onError={() => { setPreview(""); setError("图片无法显示，请重新生成预览或上传。") }}
            />
          ) : <Sparkle className="size-8 text-slate-400" />}
          {busy && <div role="status" className="absolute inset-0 grid place-items-center bg-card/80 text-[13px] text-sub">正在生成预览…</div>}
        </div>
        <div>
          <label htmlFor="avatar-prompt" className="block text-[13px] font-medium">形象描述</label>
          <textarea
            id="avatar-prompt"
            value={prompt}
            onChange={(event) => setPrompt(event.target.value)}
            rows={3}
            maxLength={1000}
            className="mt-2 w-full resize-y rounded-lg border border-line bg-canvas px-3 py-2 text-[14px] leading-relaxed outline-none focus:border-primary"
          />
        </div>
        <div className="flex items-center gap-3">
          <label htmlFor="avatar-example" className="shrink-0 text-[13px] font-medium">角色类型</label>
          <select
            id="avatar-example"
            value={subject}
            onChange={(event) => setSubject(event.target.value as keyof typeof EXAMPLES)}
            className="min-w-0 flex-1 rounded-lg border border-line bg-card px-3 py-2 text-[13px] outline-none focus:border-primary"
          >
            <option value="cat">三花猫 · 甜甜</option>
            <option value="dog">柴犬 · 铁柱</option>
          </select>
        </div>
        {error && <p role="alert" className="text-[13px] text-red-600">{error}</p>}
        <div className="grid grid-cols-2 gap-3">
          <button
            onClick={generatePreview}
            disabled={busy || !prompt.trim()}
            className="inline-flex min-h-10 items-center justify-center gap-2 rounded-lg bg-primary px-3 py-2 text-[13px] font-semibold text-white hover:bg-primary/90 disabled:opacity-40"
          >
            <Sparkle className="size-4 shrink-0" />生成预览
          </button>
          <button
            onClick={() => upload.current?.click()}
            disabled={busy}
            className="inline-flex min-h-10 items-center justify-center gap-2 rounded-lg border border-line px-3 py-2 text-[13px] font-medium hover:bg-canvas disabled:opacity-40"
          >
            <Upload className="size-4 shrink-0" />上传图片
          </button>
          <input ref={upload} type="file" accept="image/png,image/jpeg,image/webp" onChange={onUpload} className="hidden" aria-label="上传角色头像" />
        </div>
      </div>
      <div className="flex justify-end gap-3 border-t border-line px-5 py-4">
        <button onClick={onClose} className="rounded-lg px-4 py-2 text-[13px] text-sub hover:bg-canvas">取消</button>
        <button
          onClick={() => onApply(preview, prompt.trim())}
          disabled={!preview || busy}
          className="inline-flex items-center gap-2 rounded-lg bg-ink px-4 py-2 text-[13px] font-semibold text-white hover:bg-ink/90 disabled:opacity-40"
        >
          <Check className="size-4" />{applyLabel}
        </button>
      </div>
    </dialog>
  )
}
