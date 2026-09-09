import { useState } from "react"
import type { AccountSettings } from "../account"

const PHONE = "13918060824"
const EMAIL = "shulvsheyugong@126.com"

export default function Account({
  account,
  onSave,
  onLogout,
}: {
  account: AccountSettings
  onSave: (account: AccountSettings) => Promise<void>
  onLogout: () => void
}) {
  const [name, setName] = useState(account.profile.name)
  const [avatar, setAvatar] = useState(account.profile.avatar || account.chars[0]?.avatar || "")
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState("")

  const chooseAvatar = (file?: File) => {
    if (!file) return
    setSaved(false)
    setError("")
    if (!file.type.startsWith("image/") || file.size > 1024 * 1024) {
      setError("请选择小于 1 MB 的图片。")
      return
    }
    const reader = new FileReader()
    reader.onload = () => setAvatar(typeof reader.result === "string" ? reader.result : "")
    reader.onerror = () => setError("头像读取失败，请重新选择。")
    reader.readAsDataURL(file)
  }

  const save = async () => {
    const nextName = name.trim()
    if (!nextName) {
      setError("账号名称不能为空。")
      return
    }
    try {
      setSaving(true)
      setError("")
      await onSave({ ...account, profile: { ...account.profile, name: nextName, avatar: avatar || undefined } })
      setName(nextName)
      setSaved(true)
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "保存失败，请重试。")
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="flex min-h-0 min-w-0 flex-1 flex-col">
      <div className="flex-1 overflow-auto p-4 sm:p-8 xl:p-10">
        <div className="mx-auto max-w-3xl">
          <section aria-labelledby="account-profile">
            <h1 id="account-profile" className="text-[18px] font-bold">基础信息</h1>

            <div className="mt-5 border-y border-line">
              <div className="grid gap-3 py-5 sm:grid-cols-[150px_1fr] sm:items-center">
                <div className="text-[13px] text-sub">头像</div>
                <div className="flex items-center gap-4">
                  <label className="group relative grid size-16 shrink-0 cursor-pointer place-items-center overflow-hidden rounded-lg border border-slate-300 bg-primary/10 text-[13px] text-sub transition-colors hover:border-primary" title="更换头像">
                    {avatar ? <img src={avatar} alt="账号头像" className="size-full object-cover" /> : "上传头像"}
                    <span className="absolute inset-x-0 bottom-0 bg-black/55 py-1 text-center text-[10px] text-white opacity-0 transition-opacity group-hover:opacity-100">更换</span>
                    <input type="file" accept="image/*" className="sr-only" aria-label="更换账号头像" onChange={(event) => { chooseAvatar(event.target.files?.[0]); event.target.value = "" }} />
                  </label>
                  <div><p className="text-[13px] font-medium">点击头像更换</p><p className="mt-1 text-[12px] text-sub">JPG、PNG 或 WebP，小于 1 MB</p></div>
                </div>
              </div>

              <div className="grid gap-2 border-t border-line py-5 sm:grid-cols-[150px_1fr] sm:items-center">
                <label htmlFor="account-name" className="text-[13px] text-sub">账号名称</label>
                <input id="account-name" value={name} onChange={(event) => { setName(event.target.value); setSaved(false) }} className="h-11 w-full max-w-md rounded-lg border border-slate-300 bg-card px-3.5 text-[14px] font-medium outline-none transition-colors hover:border-slate-400 focus:border-primary focus:ring-2 focus:ring-primary/10" />
              </div>

              <dl>
                <div className="grid gap-1 border-t border-line py-5 sm:grid-cols-[150px_1fr]"><dt className="text-[13px] text-sub">套餐</dt><dd className="text-[14px] font-semibold">PRO</dd></div>
                <div className="grid gap-1 border-t border-line py-5 sm:grid-cols-[150px_1fr]"><dt className="text-[13px] text-sub">手机</dt><dd className="text-[14px] font-medium">{PHONE}</dd></div>
                <div className="grid gap-1 border-t border-line py-5 sm:grid-cols-[150px_1fr]"><dt className="text-[13px] text-sub">邮箱</dt><dd className="break-all text-[14px] font-medium">{EMAIL}</dd></div>
              </dl>
            </div>

            <div className="mt-4 flex flex-wrap items-center justify-end gap-3">
              {error && <p role="alert" className="mr-auto text-[13px] text-red-600">{error}</p>}
              <button type="button" onClick={() => void save()} disabled={saving} className="rounded-lg bg-primary px-5 py-2.5 text-[14px] font-semibold text-white transition-colors hover:bg-primary/90 disabled:opacity-50">{saving ? "保存中…" : saved ? "已保存" : "保存基础信息"}</button>
            </div>
          </section>

          <section className="mt-10" aria-labelledby="login-security">
            <h2 id="login-security" className="text-[17px] font-bold">登录与安全</h2>
            <div className="mt-4 flex flex-col gap-4 border-y border-line py-5 sm:flex-row sm:items-center sm:justify-between">
              <div><p className="text-[14px] font-semibold">退出当前账号</p><p className="mt-1 text-[12px] text-sub">账号定位、选题池和创作记录会继续保留。</p></div>
              <button type="button" onClick={onLogout} className="shrink-0 rounded-lg border border-red-200 bg-white px-4 py-2.5 text-[14px] font-semibold text-red-700 transition-colors hover:bg-red-50">退出登录</button>
            </div>
          </section>
        </div>
      </div>
    </div>
  )
}
