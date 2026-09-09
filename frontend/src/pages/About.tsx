import { PageKey } from "../shared"
import Logo from "../Logo"

const PARAS = [
  "我是一名独立开发者，也是 AI 产品经理。毕业至今，一直在做 AI Native 相关的产品——从概念到落地，从模型能力到真实场景，我关心的是技术如何真正走进人的生活。",
  "我的专业背景比较「不按常理」：工科、商科、设计，横跨几个看似不相干的领域。这种「横跨」曾经让我困惑，后来才明白它是我做产品的方式——用工程师的逻辑想清可行性，用商业的视角判断价值，用设计的直觉打磨体验。",
]

const CREDO = [
  { k: "工程", v: "想清可行性" },
  { k: "商业", v: "判断真价值" },
  { k: "设计", v: "打磨真体验" },
]

const REST = [
  "工作之外，我痴迷于摄影摄像，拿过垂类领域的国家一等奖，也是一名签约摄影师。它让我对画面和节奏多了一份敏感，但我更清楚——一条内容真正的分水岭，从来不在画面上，而在它讲了一个什么故事。",
  "这也正是 CreatorOS 的核心。它持续观察那些正在起量的热点，拆解出好内容背后的结构、情绪与故事张力，再用 AI 把这些理解重新写成一条新的内容。画面、景别，都只是这个故事的自然载体。",
  "所以，我把自己对产品的理解、对商业的敬畏、对故事的直觉，都放进了 CreatorOS 里。",
]

export default function About({ go }: { go: (k: PageKey) => void }) {
  return (
    <div className="min-h-full flex flex-col">
      {/* nav */}
      <header className="sticky top-0 z-20 border-b border-line bg-canvas/80 backdrop-blur">
        <div className="mx-auto max-w-6xl px-6 h-[68px] flex items-center">
          <button onClick={() => go("landing")} className="flex items-center gap-2.5">
            <Logo className="size-7" />
            <span className="font-display font-extrabold text-[17px] tracking-tight">CreatorOS</span>
          </button>
          <nav className="ml-10 hidden md:flex items-center gap-8 text-[14px] text-sub">
            <button onClick={() => go("landing")} className="hover:text-ink transition-colors">产品</button>
            <button onClick={() => go("landing")} className="hover:text-ink transition-colors">解决方案</button>
            <button onClick={() => go("landing")} className="hover:text-ink transition-colors">案例</button>
            <span className="text-ink font-medium">关于</span>
          </nav>
          <button
            onClick={() => go("login")}
            className="ml-auto rounded-xl bg-ink px-4 py-2 text-[14px] font-semibold text-white hover:bg-ink/90 transition-colors"
          >
            立即体验
          </button>
        </div>
      </header>

      <main className="flex-1">
      {/* hero */}
      <section className="mx-auto max-w-3xl px-6 pt-20 pb-10">
        <div className="inline-flex items-center gap-2 rounded-full border border-line bg-card px-3 py-1.5 text-[12px] font-mono text-sub">
          About · 关于我
        </div>
        <h1 className="mt-6 font-display font-extrabold tracking-tight text-[clamp(1.9rem,4.5vw,2.8rem)] leading-[1.15]">
          一个不被定义的人，
          <br />
          在做一件想
          <span className="bg-gradient-to-r from-primary to-violet bg-clip-text text-transparent">定义清楚</span>
          的事。
        </h1>
      </section>

      {/* body */}
      <section className="mx-auto max-w-3xl px-6 pb-24">
        <div className="space-y-6 text-[16px] leading-[1.9] text-slate-700">
          {PARAS.map((p, i) => (
            <p key={i}>{p}</p>
          ))}
        </div>

        {/* credo triptych */}
        <div className="my-10 grid grid-cols-3 gap-3">
          {CREDO.map((c) => (
            <div key={c.k} className="rounded-2xl border border-line bg-card p-5 text-center">
              <div className="font-display font-extrabold text-[18px] text-primary">{c.k}</div>
              <div className="mt-1 text-[13px] text-sub">{c.v}</div>
            </div>
          ))}
        </div>

        {/* value pull-quote */}
        <blockquote className="my-10 rounded-[24px] border border-primary/20 bg-gradient-to-br from-primary/[0.06] to-violet/[0.06] p-8">
          <div className="text-[13px] font-mono text-primary">我对「价值」的定义很克制</div>
          <p className="mt-3 font-display font-bold text-[20px] leading-relaxed text-ink">
            满足用户的真实需求，同时获得应有的商业回报。
          </p>
          <p className="mt-2 text-[15px] text-sub">两者缺一，都不算做成。</p>
        </blockquote>

        <div className="space-y-6 text-[16px] leading-[1.9] text-slate-700">
          {REST.map((p, i) => (
            <p key={i}>{p}</p>
          ))}
        </div>
      </section>
      </main>
    </div>
  )
}
