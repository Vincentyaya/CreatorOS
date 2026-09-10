import { NAV, PageKey } from "../shared"
import Logo from "../Logo"

function LoopRing() {
  const R = 40 // percent radius
  return (
    <div className="relative mx-auto aspect-square w-full max-w-[460px]">
      {/* rotating dashed ring with arrowheads */}
      <svg viewBox="0 0 100 100" className="absolute inset-0 size-full">
        <defs>
          <linearGradient id="ring" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor="#6366F1" />
            <stop offset="1" stopColor="#A855F7" />
          </linearGradient>
        </defs>
        <circle
          cx="50"
          cy="50"
          r={R}
          fill="none"
          stroke="url(#ring)"
          strokeWidth="0.8"
          strokeDasharray="2 3"
          strokeLinecap="round"
          style={{ transformOrigin: "50% 50%", animation: "spin-slow 40s linear infinite" }}
        />
      </svg>

      {/* center hub */}
      <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 text-center">
        <div className="size-24 rounded-full bg-card border border-line shadow-[0_20px_50px_-20px_rgba(79,70,229,0.45)] grid place-items-center">
          <div className="leading-tight">
            <div className="font-display font-extrabold text-primary text-[15px]">增长</div>
            <div className="font-display font-extrabold text-primary text-[15px]">飞轮</div>
          </div>
        </div>
      </div>

      {NAV.map(({ key, label, num, Icon }, i) => {
        const angle = (-90 + i * 72) * (Math.PI / 180)
        const x = 50 + R * Math.cos(angle)
        const y = 50 + R * Math.sin(angle)
        return (
          <div
            key={key}
            style={{ left: `${x}%`, top: `${y}%` }}
            className="absolute -translate-x-1/2 -translate-y-1/2 flex flex-col items-center gap-1.5"
          >
            <div className="size-14 rounded-2xl bg-card border border-line grid place-items-center shadow-[0_10px_30px_-14px_rgba(15,23,42,0.3)]">
              <Icon className="size-6 text-primary" />
            </div>
            <div className="text-center">
              <div className="font-mono text-[10px] text-slate-400">{num}</div>
              <div className="text-[12px] font-semibold whitespace-nowrap">{label}</div>
            </div>
          </div>
        )
      })}
    </div>
  )
}

export default function Landing({ go }: { go: (k: PageKey) => void }) {
  return (
    <div className="min-h-full">
      {/* nav */}
      <header className="sticky top-0 z-20 border-b border-line bg-canvas/80 backdrop-blur">
        <div className="mx-auto flex min-h-[68px] max-w-6xl flex-wrap items-center px-6 py-3 md:h-[68px] md:flex-nowrap md:py-0">
          <div className="flex items-center gap-2.5">
            <Logo className="size-7" />
            <span className="font-display font-extrabold text-[17px] tracking-tight">CreatorOS</span>
          </div>
          <nav className="order-3 mt-3 grid w-full grid-cols-4 border-t border-line pt-2 text-center text-[13px] text-sub md:order-none md:ml-10 md:mt-0 md:flex md:w-auto md:items-center md:gap-8 md:border-0 md:pt-0 md:text-left md:text-[14px]">
            <a className="py-1.5 transition-colors hover:text-ink md:py-0" href="#product">产品</a>
            <a className="py-1.5 transition-colors hover:text-ink md:py-0" href="#loop">解决方案</a>
            <a className="py-1.5 transition-colors hover:text-ink md:py-0" href="#cases">案例</a>
            <button onClick={() => go("about")} className="py-1.5 transition-colors hover:text-ink md:py-0">关于</button>
          </nav>
          <button
            onClick={() => go("login")}
            className="ml-auto rounded-xl bg-ink px-4 py-2 text-[14px] font-semibold text-white hover:bg-ink/90 transition-colors"
          >
            立即体验
          </button>
        </div>
      </header>

      {/* hero */}
      <section id="product" className="mx-auto max-w-6xl px-6 pt-16 pb-8 grid lg:grid-cols-[1.05fr_0.95fr] gap-12 items-center">
        <div>
          <div className="inline-flex items-center gap-2 rounded-full border border-line bg-card px-3 py-1.5 text-[12px] font-medium text-sub">
            <span className="size-1.5 rounded-full bg-success" />
            AI Agent 驱动 · AIGC 视频内容增长操作系统
          </div>
          <h1 className="mt-6 font-display font-extrabold tracking-tight text-[clamp(2.4rem,5vw,3.6rem)] leading-[1.06]">
            让每一个内容账号，
            <br />
            都能持续产出
            <span className="bg-gradient-to-r from-primary to-violet bg-clip-text text-transparent">爆款</span>
          </h1>
          <p className="mt-6 max-w-xl text-[16px] leading-relaxed text-sub">
            面向所有 AIGC 视频创作者的内容增长操作系统，覆盖
            <span className="text-ink font-medium"> 趋势发现 → 爆款拆解 → 账号定位 → 内容生成 → 数据复盘 </span>
            全链路闭环。
          </p>
        </div>

        <div id="loop" className="relative">
          <div className="absolute -inset-6 rounded-[32px] bg-gradient-to-br from-primary/5 to-violet/5 blur-2xl" />
          <div className="relative rounded-[28px] border border-line bg-card/60 p-8 shadow-[0_30px_80px_-40px_rgba(15,23,42,0.3)]">
            <div className="mb-4 text-center text-[12px] font-mono text-sub">五环节闭环 · 首尾相连</div>
            <LoopRing />
          </div>
        </div>
      </section>

      {/* five steps */}
      <section className="mx-auto max-w-6xl px-6 py-16">
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
          {NAV.map(({ key, num, label, Icon, sub }) => (
            <div
              key={key}
              className="rounded-2xl border border-line bg-card p-5"
            >
              <div className="flex items-center justify-between">
                <div className="size-10 rounded-xl bg-primary/8 grid place-items-center transition-colors group-hover:bg-primary/12">
                  <Icon className="size-5 text-primary" />
                </div>
                <span className="font-mono text-[13px] text-slate-300">{num}</span>
              </div>
              <div className="mt-4 font-display font-bold text-[16px]">{label}</div>
              <p className="mt-1.5 text-[13px] leading-relaxed text-sub">{sub}</p>
            </div>
          ))}
        </div>
      </section>

      {/* brand statement */}
      <section className="mx-auto max-w-6xl px-6 pb-16">
        <div className="relative overflow-hidden rounded-[28px] bg-ink px-8 py-16 text-center text-white">
          <div className="absolute -left-16 -top-16 size-64 rounded-full bg-primary/25 blur-3xl" />
          <div className="absolute -right-16 -bottom-16 size-64 rounded-full bg-violet/25 blur-3xl" />
          <div className="relative">
            <div className="font-mono text-[12px] text-white/50">OUR MISSION</div>
            <h2 className="mt-4 font-display font-extrabold tracking-tight text-[clamp(2rem,4.5vw,3.2rem)] leading-tight">
              让内容增长
              <span className="bg-gradient-to-r from-[#818cf8] to-[#c084fc] bg-clip-text text-transparent">可复制</span>
            </h2>
            <p className="mx-auto mt-4 max-w-lg text-[15px] leading-relaxed text-white/70">
              不止帮你做出一条爆款，而是把爆款背后的方法沉淀成一套可复用的系统。
            </p>
          </div>
        </div>
      </section>

      {/* cases */}
      <section id="cases" className="mx-auto max-w-6xl px-6 pb-20">
        <div className="flex items-end justify-between">
          <div>
            <h2 className="font-display font-extrabold text-[28px] tracking-tight">真实案例</h2>
            <p className="mt-1.5 text-[14px] text-sub">萌宠是我们率先跑通验证的赛道，方法论对任何 AIGC 视频方向同样成立。</p>
          </div>
          <span className="text-[13px] text-sub font-mono">CASE STUDY</span>
        </div>
        <div className="mt-6 grid gap-4 md:grid-cols-3">
          <div className="md:col-span-2 rounded-[24px] border border-line bg-gradient-to-br from-primary to-violet p-8 text-white overflow-hidden relative">
            <div className="absolute -right-10 -top-10 size-48 rounded-full bg-white/10 blur-2xl" />
            <div className="relative">
              <div className="flex items-center gap-3">
                <span className="rounded-full bg-white/15 px-2.5 py-1 text-[11px] font-mono">验证赛道 · 萌宠</span>
              </div>
              <div className="mt-4 flex items-center gap-3">
                <div className="text-3xl">🐱</div>
                <div className="text-3xl">🐶</div>
              </div>
              <h3 className="mt-4 font-display font-extrabold text-[26px]">甜甜与铁柱</h3>
              <p className="mt-2 max-w-md text-[14px] leading-relaxed text-white/85">
                一猫一狗的「人类观察日记」，用清醒与憨直的冲突感做萌宠脱口秀。我们用它跑通了整套 AIGC 视频生产链路——上线 6 周稳定日更，成为第一个可复制的样板账号。
              </p>
              <div className="mt-6 flex flex-wrap gap-6 font-mono">
                {[["涨粉", "12.4k"], ["爆款", "8 条"], ["完播率", "61%"]].map(([k, v]) => (
                  <div key={k}>
                    <div className="font-display font-extrabold text-[24px]">{v}</div>
                    <div className="text-[12px] text-white/70">{k}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
          <div className="rounded-[24px] border border-line bg-card p-8 flex flex-col">
            <div className="text-[13px] text-sub leading-relaxed">
              「以前一条内容要磨两天，人设还常常跑偏。现在从选题到发布包，一个下午能出三条，而且甜甜永远是甜甜。」
            </div>
            <div className="mt-auto pt-6">
              <div className="text-[14px] font-semibold">主理人 · Vincent</div>
              <div className="flex items-center gap-2 text-[12px] text-sub font-mono">
                <span className="text-ink">甜甜与铁柱</span>
                <span className="text-line">|</span>
                <span>人类观察日记 主理人</span>
              </div>
            </div>
          </div>
        </div>
      </section>

    </div>
  )
}
