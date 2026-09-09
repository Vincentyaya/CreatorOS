import { useState } from "react"
import { PageKey } from "../shared"
import { Arrow, Eye, EyeOff } from "../icons"
import Logo from "../Logo"

const ACCOUNT = "13918060823"
// 同时接受全角「！」与半角「!」结尾，避免输入法差异导致登录失败
const PASSWORDS = ["Admin@123！", "Admin@123!"]

export default function Login({ go }: { go: (k: PageKey) => void }) {
  const [account, setAccount] = useState("")
  const [password, setPassword] = useState("")
  const [show, setShow] = useState(false)
  const [error, setError] = useState("")

  const submit = (e: React.FormEvent) => {
    e.preventDefault()
    // 留空直接进入 demo 账号；或校验正确的账号密码
    const blank = account.trim() === "" && password === ""
    if (blank || (account.trim() === ACCOUNT && PASSWORDS.includes(password))) {
      setError("")
      try { localStorage.setItem("creatoros_login_account", account.trim() || "体验账号") } catch { /* Session label is optional. */ }
      go("dashboard")
    } else {
      setError("账号或密码不正确，请重试")
    }
  }

  return (
    <div className="min-h-full grid lg:grid-cols-2">
      {/* left brand panel */}
      <div className="relative hidden lg:flex flex-col justify-between overflow-hidden bg-gradient-to-br from-primary to-violet p-12 text-white">
        <div className="absolute -right-16 -top-16 size-72 rounded-full bg-white/10 blur-3xl" />
        <div className="absolute -left-10 bottom-10 size-56 rounded-full bg-white/10 blur-3xl" />
        <button onClick={() => go("landing")} className="relative flex items-center gap-2.5 w-fit">
          <Logo className="size-7" variant="mono" />
          <span className="font-display font-extrabold text-[17px] tracking-tight">CreatorOS</span>
        </button>
        <div className="relative">
          <h2 className="font-display font-extrabold text-[40px] leading-tight tracking-tight">
            让内容增长
            <br />
            可复制
          </h2>
          <p className="mt-4 max-w-sm text-[15px] leading-relaxed text-white/85">
            登录进入 CreatorOS 工作台，把每一次爆款沉淀成可复用的系统。
          </p>
        </div>
        <div className="relative flex gap-8 font-mono">
          {[["15 分钟", "单条产出"], ["100%", "角色一致性"], ["10+", "种子账号"]].map(([v, k]) => (
            <div key={k}>
              <div className="font-display font-extrabold text-[22px]">{v}</div>
              <div className="text-[12px] text-white/70">{k}</div>
            </div>
          ))}
        </div>
      </div>

      {/* right form */}
      <div className="flex flex-col justify-center px-6 py-12 sm:px-12">
        <div className="mx-auto w-full max-w-sm">
          <button onClick={() => go("landing")} className="lg:hidden mb-8 flex items-center gap-2.5">
            <Logo className="size-7" />
            <span className="font-display font-extrabold text-[17px] tracking-tight">CreatorOS</span>
          </button>

          <h1 className="font-display font-extrabold text-[28px] tracking-tight">欢迎回来</h1>
          <p className="mt-2 text-[14px] text-sub">登录你的账号，进入内容增长工作台</p>

          <form onSubmit={submit} className="mt-8 space-y-4">
            <div>
              <label className="text-[13px] font-medium text-sub">账号</label>
              <input
                value={account}
                onChange={(e) => setAccount(e.target.value)}
                className="mt-1.5 w-full rounded-xl border border-line bg-card px-4 py-3 text-[14px] outline-none transition-colors focus:border-primary/50"
                placeholder="请输入手机号"
                autoComplete="username"
              />
            </div>
            <div>
              <label className="text-[13px] font-medium text-sub">密码</label>
              <div className="relative mt-1.5">
                <input
                  type={show ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full rounded-xl border border-line bg-card px-4 py-3 pr-11 text-[14px] outline-none transition-colors focus:border-primary/50"
                  placeholder="请输入密码"
                  autoComplete="current-password"
                />
                <button
                  type="button"
                  onClick={() => setShow((s) => !s)}
                  aria-label={show ? "隐藏密码" : "显示密码"}
                  title={show ? "隐藏密码" : "显示密码"}
                  className="absolute right-2 top-1/2 -translate-y-1/2 grid size-8 place-items-center rounded-lg text-slate-400 transition-colors hover:bg-canvas hover:text-ink"
                >
                  {show ? <EyeOff className="size-[18px]" /> : <Eye className="size-[18px]" />}
                </button>
              </div>
            </div>

            {error && (
              <div className="rounded-xl bg-[#fef2f2] border border-[#fecaca] px-4 py-2.5 text-[13px] text-[#b91c1c]">
                {error}
              </div>
            )}

            <button
              type="submit"
              className="mt-2 inline-flex w-full items-center justify-center gap-2 rounded-xl bg-primary px-5 py-3 text-[15px] font-semibold text-white shadow-[0_16px_40px_-16px_rgba(79,70,229,0.7)] transition-colors hover:bg-primary/90"
            >
              登录并体验 <Arrow className="size-4" />
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
