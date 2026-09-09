import { Radar, Scan, Book, Sparkle, Chart } from "./icons"
import Logo from "./Logo"

export type PageKey =
  | "landing"
  | "login"
  | "about"
  | "dashboard"
  | "deconstruct"
  | "character"
  | "generate"
  | "review"
  | "account"

export const NAV: { key: PageKey; label: string; num: string; Icon: typeof Radar; sub: string }[] = [
  { key: "dashboard", label: "趋势雷达", num: "01", Icon: Radar, sub: "每天自动扫描平台热点，只推与你定位相关的选题" },
  { key: "deconstruct", label: "爆款拆解", num: "02", Icon: Scan, sub: "一条链接反解出钩子、节奏、结构与情绪配方" },
  { key: "character", label: "账号定位", num: "03", Icon: Book, sub: "定义目标人群、内容偏好与账号角色，保持创作方向一致" },
  { key: "generate", label: "内容生成", num: "04", Icon: Sparkle, sub: "剧本、画面与发布文案一体产出，15 分钟成片" },
  { key: "review", label: "数据复盘", num: "05", Icon: Chart, sub: "把每周表现沉淀为下周策略，越发越懂你" },
]

/* Sidebar for all in-app pages (2–6) */
export function Sidebar({
  active,
  go,
  accountName,
  accountAvatar,
}: {
  active: PageKey
  go: (k: PageKey) => void
  accountName: string
  accountAvatar?: string
}) {
  return (
    <aside className="w-16 sm:w-[236px] shrink-0 border-r border-line bg-card flex flex-col">
      <button
        onClick={() => go("landing")}
        className="group px-4 sm:px-6 h-[68px] flex items-center gap-2.5 border-b border-line w-full text-left"
        title="返回官网首页"
      >
        <Logo className="size-7 transition-transform group-hover:scale-105" />
        <span className="hidden sm:inline font-display font-extrabold text-[16px] tracking-tight group-hover:text-primary transition-colors">CreatorOS</span>
      </button>

      <nav className="p-2 sm:p-3 flex flex-col gap-0.5">
        {NAV.map(({ key, label, Icon }) => {
          const on = active === key
          return (
            <button
              key={key}
              onClick={() => go(key)}
              aria-label={label}
              title={label}
              className={`group flex items-center gap-3 rounded-xl px-3 py-2.5 text-[14px] font-medium transition-colors ${
                on ? "bg-primary/8 text-primary" : "text-sub hover:bg-canvas hover:text-ink"
              }`}
            >
              <Icon className={`size-[18px] ${on ? "text-primary" : "text-slate-400 group-hover:text-ink"}`} />
              <span className="hidden sm:inline">{label}</span>
              {on && <span className="hidden sm:block ml-auto size-1.5 rounded-full bg-primary" />}
            </button>
          )
        })}
      </nav>

      <div className="mt-auto p-2 sm:p-4">
        <button
          type="button"
          onClick={() => go("account")}
          aria-label="查看账号信息"
          title="查看账号信息"
          className={`w-full rounded-lg border p-2 text-left transition-colors sm:p-4 ${active === "account" ? "border-primary/30 bg-primary/[0.06]" : "border-line bg-canvas hover:border-primary/30 hover:bg-primary/[0.03]"}`}
        >
          <div className="flex items-center gap-2.5">
            <div className="size-9 overflow-hidden rounded-full bg-gradient-to-br from-primary to-violet grid place-items-center text-white text-[15px]">
              {accountAvatar ? <img src={accountAvatar} alt="" className="size-full object-cover" /> : "猫"}
            </div>
            <div className="hidden min-w-0 leading-tight sm:block">
              <div className="break-words text-[13px] font-semibold">{accountName}</div>
              <div className="text-[11px] text-sub font-mono">PRO</div>
            </div>
          </div>
        </button>
      </div>
    </aside>
  )
}

export function Tag({ children, tone = "ghost" }: { children: React.ReactNode; tone?: "ghost" | "primary" | "success" | "progress" }) {
  const map = {
    ghost: "bg-slate-100 text-sub",
    primary: "bg-primary/10 text-primary",
    success: "bg-success/12 text-success",
    progress: "bg-progress/12 text-[#b45309]",
  }
  return (
    <span className={`inline-flex items-center gap-1 rounded-lg px-2.5 py-1 text-[12px] font-medium font-mono ${map[tone]}`}>
      {children}
    </span>
  )
}
