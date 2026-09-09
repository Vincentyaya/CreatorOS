import { useRef, useState } from "react"
import { Arrow, Check, Sparkle, Upload } from "../icons"
import CharacterAvatarDialog from "../components/CharacterAvatarDialog"
import ContentOutput from "../components/ContentOutput"
import { ACCENTS, type AccountSettings } from "../account"
import { errorText, readLocal, writeLocal, uploadAsset, type Capabilities, type ContentCharacter } from "../api"
import { useContentWorkflow } from "../useContentWorkflow"

const STEPS = ["选题", "角色", "生成", "发布"]
const TOPICS = [
  { topic: "#打工累得跟狗似的", match: 92, angle: "铁柱心疼打工人，甜甜一句反转戳中牛马日常" },
  { topic: "#周一综合症急救指南", match: 88, angle: "铁柱盲目乐观 VS 甜甜清醒吐槽，谁能治好周一？" },
  { topic: "#成年人的崩溃静音模式", match: 84, angle: "把加班的心声，翻译成猫狗听得懂的憨话" },
]
const SOURCES = [
  { key: "library", label: "已有角色" },
  { key: "generated", label: "自主生成" },
  { key: "upload", label: "上传图片" },
] as const
const CHANNELS = [
  { key: "douyin", name: "抖音" }, { key: "kuaishou", name: "快手" },
  { key: "xhs", name: "小红书" }, { key: "bili", name: "B站" }, { key: "shipinhao", name: "视频号" },
]

function Avatar({ character }: { character: ContentCharacter }) {
  return character.img ? <img src={character.img} alt={character.name + "头像"} className="size-12 shrink-0 rounded-lg object-cover" /> :
    <span className="grid size-12 shrink-0 place-items-center rounded-lg text-[22px]" style={{ background: character.accent }}>{character.emoji}</span>
}

export default function Generate({ account, capabilities }: { account: AccountSettings; capabilities: Capabilities | null }) {
  const [step, setStep] = useState(0)
  const [topicIndex, setTopicIndex] = useState(0)
  const [customTopic, setCustomTopic] = useState(() => {
    const saved = readLocal("creatoros_content_topic") ?? ""
    if (saved) writeLocal("creatoros_content_topic", null)
    return saved
  })
  const [characters, setCharacters] = useState<ContentCharacter[]>([])
  const [source, setSource] = useState<ContentCharacter["source"]>("library")
  const [roleName, setRoleName] = useState("新角色")
  const [rolePrompt, setRolePrompt] = useState("一只开朗的柴犬，擅长用幽默的语言解释复杂的知识，精致 3D 动画风格。")
  const [avatarDialog, setAvatarDialog] = useState(false)
  const [uploadError, setUploadError] = useState("")
  const [uploading, setUploading] = useState(false)
  const [channels, setChannels] = useState<Set<string>>(() => new Set(CHANNELS.filter((channel) => account.profile.platforms.includes(channel.name)).map((channel) => channel.key)))
  const fileRef = useRef<HTMLInputElement>(null)
  const topic = customTopic.trim() || TOPICS[topicIndex].topic
  const library: ContentCharacter[] = account.chars.map((character) => ({
    id: "account-" + character.id, source: "library", name: character.name, emoji: character.emoji,
    desc: character.persona, accent: character.accent, img: character.avatar,
  }))
  const workflow = useContentWorkflow(characters, topic, (draft) => {
    setCharacters(draft.characters)
    if (draft.topic && !TOPICS.some((item) => item.topic === draft.topic)) setCustomTopic(draft.topic)
  })
  const resetOutput = () => workflow.reset()
  const toggleChannel = (key: string) => setChannels((previous) => {
    const next = new Set(previous)
    next.has(key) ? next.delete(key) : next.add(key)
    return next
  })
  const toggleRole = (role: ContentCharacter) => {
    resetOutput()
    setCharacters((current) => current.some((item) => item.id === role.id) ? current.filter((item) => item.id !== role.id) : [...current, role])
  }
  const removeRole = (role: ContentCharacter) => {
    resetOutput()
    setCharacters((current) => current.filter((item) => item.id !== role.id))
  }
  const addGenerated = (img: string, description: string) => {
    resetOutput()
    setCharacters((current) => [...current, {
      id: "generated-" + crypto.randomUUID(), source: "generated", name: roleName.trim(),
      desc: description, emoji: "✨", accent: ACCENTS[2], img,
    }])
    setAvatarDialog(false)
  }
  const uploadRoles = async (files: FileList | null) => {
    if (!files?.length) return
    setUploading(true)
    setUploadError("")
    resetOutput()
    try {
      for (const file of Array.from(files)) {
        if (!["image/png", "image/jpeg", "image/webp"].includes(file.type) || file.size > 5 * 1024 * 1024) throw new Error("请选择小于 5 MB 的 PNG、JPG 或 WebP 图片。")
        const asset = await uploadAsset(file)
        setCharacters((current) => [...current, {
          id: asset.id, source: "upload", name: file.name.replace(/\.[^.]+$/, "") || "我的角色",
          desc: "已上传角色", emoji: "🖼️", accent: ACCENTS[4], img: asset.url,
        }])
      }
    } catch (error) { setUploadError(errorText(error)) }
    finally { setUploading(false) }
  }
  const go = (next: number) => {
    if (workflow.busy || uploading || next < 0 || next > 3) return
    if (next === 1 && !topic) return
    if (next >= 2 && !characters.length) return
    setStep(next)
    if (next === 2 && !workflow.draft) void workflow.generate(capabilities?.script ? "live" : "demo")
  }

  return (
    <div className="flex min-h-0 min-w-0 flex-1 flex-col">
      <nav aria-label="内容生成步骤" className="flex h-[68px] shrink-0 items-center border-b border-line px-3 sm:px-8">
        <div className="flex min-w-0 items-center gap-1 sm:gap-2">
          {STEPS.map((label, index) => <div key={label} className="flex min-w-0 items-center gap-1 sm:gap-2">
            <button onClick={() => go(index)} disabled={workflow.busy || uploading || (index > 0 && (!topic || (index > 1 && !characters.length)))} className={"rounded-full px-2 py-1.5 text-[13px] font-medium disabled:opacity-40 sm:px-3 " + (step === index ? "bg-primary text-white" : index < step ? "text-ink hover:bg-canvas" : "text-sub hover:bg-canvas")}>
              <span className="hidden sm:inline">{index < step ? "✓ " : (index + 1) + " "}</span>{label}
            </button>
            {index < STEPS.length - 1 && <span className="h-px w-3 bg-line sm:w-6" />}
          </div>)}
        </div>
      </nav>
      <div className="flex-1 overflow-auto p-4 sm:p-6 xl:p-8">
        <details className="mb-6 max-w-4xl border-b border-line pb-4">
          <summary className="cursor-pointer text-[13px] text-sub"><span className="font-semibold text-ink">{account.profile.name}</span> · 账号创作偏好</summary>
          <dl className="mt-3 grid gap-3 text-[13px] md:grid-cols-2">
            <div><dt className="text-sub">目标人群</dt><dd className="mt-1 break-words">{account.profile.audience}</dd></div>
            <div><dt className="text-sub">内容赛道</dt><dd className="mt-1 break-words">{account.profile.niche}</dd></div>
            <div><dt className="text-sub">内容偏好</dt><dd className="mt-1 break-words">{account.profile.contentPreferences}</dd></div>
            <div><dt className="text-sub">输出偏好</dt><dd className="mt-1">{account.profile.formats.join(" / ")} · {account.profile.tone} · {account.profile.duration} 秒</dd></div>
          </dl>
        </details>
        {step === 0 && <div className="max-w-3xl">
          <h1 className="font-display text-[22px] font-extrabold">选择今天的选题方向</h1>
          <label className="mt-5 block text-[13px] text-sub">自定义选题
            <input aria-label="自定义选题" value={customTopic} onChange={(event) => { resetOutput(); setCustomTopic(event.target.value) }} placeholder="输入本次想聊的话题" className="mt-2 w-full rounded-lg border border-line bg-card px-4 py-3 text-[14px] text-ink outline-none focus:border-primary" />
          </label>
          <p className="mt-3 text-[12px] text-sub">推荐选题和匹配度为演示数据。</p>
          <div className="mt-5 space-y-3">{TOPICS.map((item, index) => {
            const selected = !customTopic && topicIndex === index
            return <button key={item.topic} onClick={() => { resetOutput(); setCustomTopic(""); setTopicIndex(index) }} className={"w-full rounded-lg border bg-card p-5 text-left " + (selected ? "border-primary ring-2 ring-primary/15" : "border-line hover:border-primary/40")}>
              <div className="flex flex-wrap items-center gap-2"><span className="rounded-md bg-primary/10 px-2 py-1 font-mono text-[12px] text-primary">{item.topic}</span><span className="rounded-md bg-success/10 px-2 py-1 font-mono text-[12px] text-success">匹配度 {item.match}%</span>{selected && <Check className="ml-auto size-5 text-primary" />}</div>
              <p className="mt-3 text-[15px] font-medium">{item.angle}</p>
            </button>
          })}</div>
        </div>}
        {step === 1 && <div className="max-w-4xl">
          <h1 className="font-display text-[22px] font-extrabold">选择本次内容的角色</h1>
          <div role="tablist" aria-label="角色来源" className="mt-5 flex w-fit max-w-full gap-1 rounded-lg border border-line bg-card p-1">
            {SOURCES.map((item) => <button key={item.key} id={"role-source-" + item.key} role="tab" aria-selected={source === item.key} onClick={() => setSource(item.key)} className={"rounded-md px-3 py-2 text-[13px] " + (source === item.key ? "bg-primary/10 text-primary" : "text-sub hover:bg-canvas")}>{item.label}</button>)}
          </div>
          <section role="tabpanel" aria-labelledby={"role-source-" + source} className="mt-5">
            {source === "library" && <div className="grid gap-3 md:grid-cols-2">{library.map((role) => {
              const selected = characters.some((item) => item.id === role.id)
              return <label key={role.id} className={"flex cursor-pointer items-start gap-3 rounded-lg border bg-card p-4 " + (selected ? "border-primary bg-primary/[0.03]" : "border-line")}>
                <Avatar character={role} /><span className="min-w-0 flex-1"><span className="block text-[15px] font-semibold">{role.name}</span><span className="mt-1 block text-[13px] text-sub">{role.desc}</span></span>
                <input type="checkbox" aria-label={"选择角色" + role.name} checked={selected} onChange={() => toggleRole(role)} className="mt-1 size-4 accent-primary" />
              </label>
            })}</div>}
            {source === "generated" && <div className="max-w-xl space-y-4">
              <label className="block text-[13px] text-sub">新角色名称<input aria-label="新角色名称" value={roleName} maxLength={40} onChange={(event) => setRoleName(event.target.value)} className="mt-2 block w-full rounded-lg border border-line bg-card px-3 py-2 text-[14px] text-ink" /></label>
              <label className="block text-[13px] text-sub">新角色人设与形象<textarea aria-label="新角色人设与形象" value={rolePrompt} maxLength={1000} onChange={(event) => setRolePrompt(event.target.value)} rows={4} className="mt-2 block w-full resize-y rounded-lg border border-line bg-card px-3 py-2 text-[14px] text-ink" /></label>
              <button onClick={() => setAvatarDialog(true)} disabled={!roleName.trim() || !rolePrompt.trim()} className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-[14px] font-semibold text-white disabled:opacity-40"><Sparkle className="size-4" />生成角色</button>
            </div>}
            {source === "upload" && <div className="max-w-xl">
              <input ref={fileRef} aria-label="上传内容角色图片" type="file" accept="image/png,image/jpeg,image/webp" multiple hidden onChange={(event) => { void uploadRoles(event.target.files); event.target.value = "" }} />
              <button onClick={() => fileRef.current?.click()} disabled={uploading} className="grid min-h-36 w-full place-content-center justify-items-center gap-3 rounded-lg border border-dashed border-line bg-card px-4 py-8 text-sub hover:border-primary/40 hover:text-primary disabled:opacity-50"><Upload className="size-7" /><span className="text-[14px]">{uploading ? "上传中…" : "上传角色图片"}</span></button>
              {uploadError && <p role="alert" className="mt-3 text-[13px] text-red-600">{uploadError}</p>}
            </div>}
          </section>
          {characters.length > 0 && <section aria-label="已选角色" className="mt-6 border-t border-line pt-5"><p className="text-[12px] font-mono text-sub">已选角色 · {characters.length}</p><div className="mt-3 grid gap-3 md:grid-cols-2">{characters.map((role) => <div key={role.id} className="flex items-start gap-3 rounded-lg border border-line bg-card p-3"><Avatar character={role} /><div className="min-w-0 flex-1"><p className="text-[14px] font-semibold">{role.name}</p><p className="mt-1 text-[12px] text-sub">{role.desc}</p><p className="mt-1 text-[11px] text-primary">{SOURCES.find((item) => item.key === role.source)?.label}</p></div><button onClick={() => removeRole(role)} aria-label={"移除角色" + role.name} className="grid size-7 place-items-center rounded-lg text-sub hover:bg-canvas">×</button></div>)}</div></section>}
        </div>}
        {step >= 2 && <ContentOutput step={step} workflow={workflow} capabilities={capabilities} characters={characters} channels={channels} toggleChannel={toggleChannel} />}
      </div>
      <footer className="flex shrink-0 items-center justify-between gap-2 border-t border-line px-3 py-4 sm:px-8">
        <button onClick={() => go(step - 1)} disabled={step === 0 || workflow.busy || uploading} className="rounded-lg px-4 py-2.5 text-[14px] text-sub disabled:opacity-40">上一步</button>
        {step < 3 ? <button onClick={() => go(step + 1)} disabled={workflow.busy || uploading || (step === 1 && !characters.length)} className="inline-flex items-center gap-2 rounded-lg bg-primary px-5 py-2.5 text-[14px] font-semibold text-white disabled:opacity-40">下一步：{STEPS[step + 1]}<Arrow className="size-4" /></button> : <span className="text-[13px] text-sub">最后一步 · 发布</span>}
      </footer>
      {avatarDialog && <CharacterAvatarDialog name={roleName.trim()} prompt={rolePrompt} applyLabel="添加到本次内容" onClose={() => setAvatarDialog(false)} onApply={addGenerated} />}
    </div>
  )
}
