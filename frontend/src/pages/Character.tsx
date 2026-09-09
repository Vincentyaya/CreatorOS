import { useEffect, useState } from "react"
import { Ban, Sparkle } from "../icons"
import CharacterAvatarDialog from "../components/CharacterAvatarDialog"
import { ACCENTS, FORMATS, PLATFORMS, TONES, type AccountCharacter as Char, type AccountSettings } from "../account"

function Field({
  label,
  value,
  onChange,
  multiline,
}: {
  label: string
  value: string
  onChange: (v: string) => void
  multiline?: boolean
}) {
  return (
    <label className="block min-w-0">
      <span className="text-[13px] font-semibold text-ink">{label}</span>
      {multiline ? (
        <textarea
          aria-label={label}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          rows={2}
          className="mt-2 w-full resize-none rounded-lg border border-slate-300 bg-card px-3.5 py-3 text-[14px] font-medium leading-relaxed text-ink outline-none transition-colors placeholder:text-slate-400 hover:border-slate-400 focus:border-primary focus:ring-2 focus:ring-primary/10"
        />
      ) : (
        <input
          aria-label={label}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="mt-2 h-11 w-full rounded-lg border border-slate-300 bg-card px-3.5 text-[14px] font-medium text-ink outline-none transition-colors placeholder:text-slate-400 hover:border-slate-400 focus:border-primary focus:ring-2 focus:ring-primary/10"
        />
      )}
    </label>
  )
}

function Choices({ label, options, values, onChange }: { label: string; options: string[]; values: string[]; onChange: (values: string[]) => void }) {
  return (
    <fieldset className="min-w-0">
      <legend className="text-[13px] font-medium text-sub">{label}</legend>
      <div className="mt-3 flex flex-wrap gap-x-5 gap-y-3">
        {options.map((option) => (
          <label key={option} className="inline-flex cursor-pointer items-center gap-2 text-[14px]">
            <input
              type="checkbox"
              checked={values.includes(option)}
              disabled={values.length === 1 && values.includes(option)}
              onChange={(event) => onChange(event.target.checked ? [...values, option] : values.filter((value) => value !== option))}
              className="size-4 accent-primary"
            />
            {option}
          </label>
        ))}
      </div>
    </fieldset>
  )
}

function CharCard({
  data,
  onChange,
  onRemove,
  onAvatar,
  canRemove,
}: {
  data: Char
  onChange: (patch: Partial<Char>) => void
  onRemove: () => void
  onAvatar: () => void
  canRemove: boolean
}) {
  return (
    <div className="min-w-0 rounded-lg border border-line bg-card p-5">
      <div className="flex items-center gap-4">
        <button
          onClick={onAvatar}
          aria-label={`生成或更换${data.name}的头像`}
          title="生成或更换头像"
          className="group relative grid size-16 shrink-0 place-items-center overflow-hidden rounded-2xl text-[32px] outline-none transition-shadow hover:ring-2 hover:ring-primary/30 focus-visible:ring-2 focus-visible:ring-primary"
          style={{ background: data.accent }}
        >
          {data.avatar ? (
            <img src={data.avatar} alt={`${data.name}头像`} className="size-full object-cover" onError={() => onChange({ avatar: undefined })} />
          ) : data.emoji}
          <span className="absolute bottom-0 right-0 grid size-6 place-items-center rounded-tl-lg bg-primary text-white"><Sparkle className="size-4" /></span>
        </button>
        <div className="min-w-0 flex-1">
          <input
            value={data.name}
            onChange={(e) => onChange({ name: e.target.value })}
            aria-label="角色名称"
            className="w-full rounded-lg border border-transparent bg-transparent font-display font-extrabold text-[22px] outline-none transition-colors hover:border-line focus:border-primary/50"
          />
          <input
            value={data.meta}
            onChange={(e) => onChange({ meta: e.target.value })}
            aria-label="角色标签"
            className="mt-0.5 w-full rounded-lg border border-transparent bg-transparent text-[13px] text-sub font-mono outline-none transition-colors hover:border-line focus:border-primary/50"
          />
        </div>
        {canRemove && (
          <button
            onClick={onRemove}
            aria-label="删除角色"
            title="删除角色"
            className="grid size-8 shrink-0 place-items-center rounded-lg text-slate-400 transition-colors hover:bg-[#fef2f2] hover:text-[#b91c1c]"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" className="size-[18px]">
              <path d="M5 7h14M9 7V5.5A1.5 1.5 0 0 1 10.5 4h3A1.5 1.5 0 0 1 15 5.5V7M7 7l.8 12.1A1.5 1.5 0 0 0 9.3 20.5h5.4a1.5 1.5 0 0 0 1.5-1.4L17 7" />
            </svg>
          </button>
        )}
      </div>
      <div className="mt-6 space-y-4">
        <Field label="人设" value={data.persona} onChange={(v) => onChange({ persona: v })} multiline />
        <div className="h-px bg-line" />
        <Field label="口癖" value={data.quirk} onChange={(v) => onChange({ quirk: v })} />
      </div>
    </div>
  )
}

export default function Character({ account, onSave }: { account: AccountSettings; onSave: (account: AccountSettings) => Promise<void> }) {
  const [view, setView] = useState<"positioning" | "roles">("positioning")
  const [profile, setProfile] = useState(account.profile)
  const [chars, setChars] = useState<Char[]>(account.chars)
  const [interaction, setInteraction] = useState(account.interaction)
  const [forbidden, setForbidden] = useState(account.forbidden)
  const [newRule, setNewRule] = useState("")
  const [saved, setSaved] = useState(false)
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState("")
  const [editingId, setEditingId] = useState<number | null>(null)
  const editingChar = chars.find((char) => char.id === editingId)

  useEffect(() => {
    setSaved(false)
    setSaveError("")
  }, [profile, chars, interaction, forbidden])

  const patch = (id: number, p: Partial<Char>) =>
    setChars((cs) => cs.map((c) => (c.id === id ? { ...c, ...p } : c)))

  const remove = (id: number) => setChars((cs) => cs.filter((c) => c.id !== id))

  const add = () =>
    setChars((cs) => [
      ...cs,
      {
        id: Math.max(0, ...cs.map((char) => char.id)) + 1,
        emoji: "✨",
        name: "新角色",
        meta: "年龄 · 地点",
        persona: "一句话人设",
        quirk: "标志性口头禅",
        accent: ACCENTS[cs.length % ACCENTS.length],
      },
    ])

  const addRule = () => {
    const v = newRule.trim()
    if (!v) return
    setForbidden((f) => [...f, v])
    setNewRule("")
  }

  const save = async () => {
    if (!profile.name.trim() || !profile.niche.trim() || !profile.audience.trim()) {
      setSaveError("请填写账号名称、内容赛道和目标人群。")
      return
    }
    if (!Number.isFinite(profile.duration) || profile.duration < 15 || profile.duration > 600) {
      setSaveError("视频时长请填写 15 到 600 秒。")
      return
    }
    if (chars.some((char) => !char.name.trim())) {
      setSaveError("请为每个账号角色填写名称。")
      return
    }
    try {
      setSaving(true)
      await onSave({ profile: { ...profile, name: profile.name.trim() }, chars, interaction, forbidden })
      setSaveError("")
      setSaved(true)
    } catch (error) {
      setSaved(false)
      setSaveError(error instanceof Error ? error.message : "保存失败，请重试。")
    } finally { setSaving(false) }
  }

  return (
    <div className="flex min-h-0 min-w-0 flex-1 flex-col">
      <div className="flex-1 overflow-auto p-4 sm:p-8 xl:p-10">
        <div className="max-w-4xl mx-auto">
          <nav className="flex gap-6 border-b border-line" aria-label="账号定位设置">
            <button
              onClick={() => setView("positioning")}
              className={`border-b-2 pb-3 text-[14px] font-semibold transition-colors ${view === "positioning" ? "border-primary text-primary" : "border-transparent text-sub hover:text-ink"}`}
            >
              定位设置
            </button>
            <button
              onClick={() => setView("roles")}
              className={`border-b-2 pb-3 text-[14px] font-semibold transition-colors ${view === "roles" ? "border-primary text-primary" : "border-transparent text-sub hover:text-ink"}`}
            >
              角色定义
            </button>
          </nav>

          {view === "positioning" && <>
          <section className="mt-7 border-b border-line pb-7" aria-labelledby="positioning-basics">
            <h2 id="positioning-basics" className="text-[17px] font-bold">基本定位</h2>
            <div className="mt-4 grid gap-5 md:grid-cols-2">
              <Field label="账号名称" value={profile.name} onChange={(name) => setProfile((p) => ({ ...p, name }))} />
              <Field label="内容赛道" value={profile.niche} onChange={(niche) => setProfile((p) => ({ ...p, niche }))} />
              <Field label="目标人群" value={profile.audience} onChange={(audience) => setProfile((p) => ({ ...p, audience }))} multiline />
              <Field label="账号价值" value={profile.valueProposition} onChange={(valueProposition) => setProfile((p) => ({ ...p, valueProposition }))} multiline />
            </div>
          </section>

          <section className="border-b border-line py-7" aria-labelledby="content-preferences">
            <h2 id="content-preferences" className="text-[17px] font-bold">内容偏好</h2>
            <div className="mt-4 space-y-5">
              <Field label="选题与表达偏好" value={profile.contentPreferences} onChange={(contentPreferences) => setProfile((p) => ({ ...p, contentPreferences }))} multiline />
              <Choices label="内容形式" options={FORMATS} values={profile.formats} onChange={(formats) => setProfile((p) => ({ ...p, formats }))} />
              <div className="grid gap-5 md:grid-cols-2">
                <label className="block min-w-0 text-[13px] font-semibold text-ink">
                  内容语气
                  <select aria-label="内容语气" value={profile.tone} onChange={(event) => setProfile((p) => ({ ...p, tone: event.target.value }))} className="mt-2 block h-11 w-full rounded-lg border border-slate-300 bg-card px-3.5 text-[14px] font-medium text-ink outline-none transition-colors hover:border-slate-400 focus:border-primary focus:ring-2 focus:ring-primary/10">
                    {TONES.map((tone) => <option key={tone}>{tone}</option>)}
                  </select>
                </label>
                <label className="block min-w-0 text-[13px] font-semibold text-ink">
                  目标视频时长（秒）
                  <input type="number" min={15} max={600} step={1} value={profile.duration || ""} onChange={(event) => setProfile((p) => ({ ...p, duration: Number(event.target.value) }))} className="mt-2 block h-11 w-full rounded-lg border border-slate-300 bg-card px-3.5 text-[14px] font-medium text-ink outline-none transition-colors hover:border-slate-400 focus:border-primary focus:ring-2 focus:ring-primary/10" />
                </label>
              </div>
              <Choices label="经营平台" options={PLATFORMS} values={profile.platforms} onChange={(platforms) => setProfile((p) => ({ ...p, platforms }))} />
            </div>
          </section>
          </>}

          {view === "roles" && <section className="mt-7" aria-labelledby="role-definition">
          <div>
            <h2 id="role-definition" className="text-[17px] font-bold">角色定义</h2>
            <p className="mt-1 text-[13px] text-sub">定义角色形象、性格和语言习惯，让每条内容保持一致。</p>
          </div>
          <div className="mt-4 grid gap-4 lg:grid-cols-2">
            {chars.map((c) => (
              <CharCard
                key={c.id}
                data={c}
                canRemove={chars.length > 1}
                onChange={(p) => patch(c.id, p)}
                onRemove={() => remove(c.id)}
                onAvatar={() => setEditingId(c.id)}
              />
            ))}

            <button
              onClick={add}
              className="group flex min-h-24 min-w-0 items-center justify-center gap-3 rounded-lg border border-dashed border-line bg-canvas/60 p-5 text-center transition-colors hover:border-primary/40 hover:bg-primary/[0.03]"
            >
              <div className="grid size-12 place-items-center rounded-2xl bg-primary/8 text-primary transition-colors group-hover:bg-primary/12">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" className="size-6">
                  <path d="M12 5v14M5 12h14" />
                </svg>
              </div>
              <div className="text-[14px] font-semibold text-sub group-hover:text-primary">新增角色</div>
            </button>
          </div>

          {/* interaction rule */}
          <div className="mt-7 border-t border-line pt-6">
            <div className="text-[13px] font-semibold text-ink">互动模式</div>
            <textarea
              aria-label="角色互动模式"
              value={interaction}
              onChange={(e) => setInteraction(e.target.value)}
              rows={2}
              className="mt-2 w-full resize-none rounded-lg border border-slate-300 bg-card px-3.5 py-3 text-[14px] font-medium leading-relaxed text-ink outline-none transition-colors hover:border-slate-400 focus:border-primary focus:ring-2 focus:ring-primary/10"
            />
          </div>

          {/* forbidden zone */}
          <div className="mt-7 border-t border-line pt-6">
            <div className="text-[13px] font-semibold text-[#b91c1c]">禁区 · 绝不触碰</div>
            <div className="mt-4 flex flex-wrap gap-2.5">
              {forbidden.map((t, i) => (
                <span
                  key={t + i}
                  className="group inline-flex items-center gap-1.5 rounded-full bg-white border border-[#fecaca] px-4 py-2 text-[13px] font-medium text-[#b91c1c]"
                >
                  <Ban className="size-4" /> {t}
                  <button
                    onClick={() => setForbidden((f) => f.filter((_, idx) => idx !== i))}
                    aria-label={`删除 ${t}`}
                    className="ml-0.5 grid size-4 place-items-center rounded-full text-[#b91c1c]/60 transition-colors hover:bg-[#fecaca] hover:text-[#b91c1c]"
                  >
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" className="size-3">
                      <path d="M6 6l12 12M18 6L6 18" />
                    </svg>
                  </button>
                </span>
              ))}
              <div className="inline-flex items-center rounded-full border border-dashed border-[#fca5a5] bg-white/60 pl-3.5 pr-1.5">
                <input
                  value={newRule}
                  onChange={(e) => setNewRule(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && addRule()}
                  placeholder="添加禁区..."
                  className="w-24 bg-transparent py-2 text-[13px] text-[#b91c1c] outline-none placeholder:text-[#b91c1c]/40"
                />
                <button
                  onClick={addRule}
                  aria-label="添加禁区"
                  className="grid size-6 place-items-center rounded-full text-[#b91c1c] transition-colors hover:bg-[#fecaca]"
                >
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" className="size-3.5">
                    <path d="M12 5v14M5 12h14" />
                  </svg>
                </button>
              </div>
            </div>
          </div>
          </section>}

        </div>
      </div>
      <div className="shrink-0 border-t border-line bg-card px-4 py-3 sm:px-8">
        <div className="mx-auto flex max-w-4xl flex-wrap items-center justify-end gap-3">
          {saveError && <p role="alert" className="min-w-0 flex-1 text-[13px] text-red-600">{saveError}</p>}
          <button onClick={save} disabled={saving} className="rounded-lg bg-primary px-5 py-2.5 text-[14px] font-semibold text-white hover:bg-primary/90 disabled:opacity-50">
            {saving ? "保存中…" : saved ? "已保存 ✓" : "保存账号定位"}
          </button>
        </div>
      </div>
      {editingChar && (
        <CharacterAvatarDialog
          key={editingChar.id}
          name={editingChar.name}
          avatar={editingChar.avatar}
          prompt={editingChar.avatarPrompt || `${editingChar.name}，${editingChar.persona}，${editingChar.meta}，正面角色头像。`}
          onClose={() => setEditingId(null)}
          onApply={(avatar, avatarPrompt) => {
            patch(editingChar.id, { avatar, avatarPrompt })
            setSaved(false)
            setEditingId(null)
          }}
        />
      )}
    </div>
  )
}
