import { useId } from "react"

/**
 * CreatorOS 品牌图标 · Agent 星群
 * 一张向上生长的节点网络，一个高亮节点＝领跑的 AI Agent —— 传达「智能体 / 平台底座」。
 * 连线已加粗、提高不透明度，确保 16px favicon 与 28px 侧栏下依旧清晰。
 */
export default function Logo({
  className = "size-7",
  variant = "tile",
}: {
  className?: string
  /** tile: 渐变圆角底+白色图形 | gradient: 透明底+渐变图形 | mono: 透明底+白色图形 */
  variant?: "tile" | "gradient" | "mono"
}) {
  const gid = useId()
  const ink = variant === "gradient" ? `url(#${gid}-g)` : "#ffffff"

  const pts: [number, number][] = [
    [9, 20],
    [16, 9.5],
    [23, 18.5],
    [15.5, 22],
  ]
  const edges: [number, number][] = [
    [0, 1],
    [1, 2],
    [0, 3],
    [3, 2],
    [1, 3],
  ]

  return (
    <svg viewBox="0 0 32 32" className={className} role="img" aria-label="CreatorOS">
      <defs>
        <linearGradient id={`${gid}-g`} x1="4" y1="2" x2="28" y2="30" gradientUnits="userSpaceOnUse">
          <stop offset="0" stopColor="#6366F1" />
          <stop offset="1" stopColor="#A855F7" />
        </linearGradient>
      </defs>

      {variant === "tile" && <rect x="1" y="1" width="30" height="30" rx="9" fill={`url(#${gid}-g)`} />}

      {edges.map(([a, b], i) => (
        <line
          key={i}
          x1={pts[a][0]}
          y1={pts[a][1]}
          x2={pts[b][0]}
          y2={pts[b][1]}
          stroke={ink}
          strokeWidth="1.8"
          strokeLinecap="round"
          opacity="0.7"
        />
      ))}

      {pts.map(([x, y], i) => (
        <circle key={i} cx={x} cy={y} r={i === 1 ? 3.1 : 2.1} fill={ink} />
      ))}
    </svg>
  )
}
