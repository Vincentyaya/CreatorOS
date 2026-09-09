export type AccountCharacter = {
  id: number
  emoji: string
  name: string
  meta: string
  persona: string
  quirk: string
  accent: string
  avatar?: string
  avatarPrompt?: string
}

export type AccountProfile = {
  avatar?: string
  name: string
  niche: string
  audience: string
  valueProposition: string
  contentPreferences: string
  formats: string[]
  tone: string
  duration: number
  platforms: string[]
}

export type AccountSettings = {
  profile: AccountProfile
  chars: AccountCharacter[]
  interaction: string
  forbidden: string[]
}

export const FORMATS = ["短视频", "图文", "长视频", "文字"]
export const TONES = ["轻松幽默", "温暖治愈", "知识科普", "犀利观点", "真实记录"]
export const PLATFORMS = ["抖音", "快手", "小红书", "B站", "视频号"]
export const ACCOUNT_STORAGE_KEY = "creatoros_account_settings_v1"
const LEGACY_STORAGE_KEY = "creatoros_character_settings_v1"

export const ACCENTS = [
  "linear-gradient(135deg,#eef2ff,#e0e7ff)",
  "linear-gradient(135deg,#fef3e2,#fde8c8)",
  "linear-gradient(135deg,#ecfdf5,#d1fae5)",
  "linear-gradient(135deg,#fdf4ff,#f5d0fe)",
  "linear-gradient(135deg,#eff6ff,#dbeafe)",
]

const DEFAULT_PROFILE: AccountProfile = {
  avatar: "/avatars/tiantian.png",
  name: "人类观察日记",
  niche: "萌宠 + 职场脱口秀",
  audience: "22–35 岁的年轻职场人，关注日常工作、生活压力与情绪共鸣。",
  valueProposition: "用猫狗的视角观察人类生活，让观众会心一笑，也获得一点轻松。",
  contentPreferences: "优先选择职场日常、生活反差和温和吐槽；偏好双角色对话，开场有钩子，结尾有反转。",
  formats: ["短视频", "图文"],
  tone: "轻松幽默",
  duration: 45,
  platforms: ["抖音", "小红书"],
}

export const DEFAULT_ACCOUNT: AccountSettings = {
  profile: DEFAULT_PROFILE,
  chars: [
    { id: 1, emoji: "🐱", name: "甜甜", meta: "3 岁 · 台北", persona: "人间清醒，专业泼冷水", quirk: "人类真是想太多", accent: ACCENTS[0], avatar: "/avatars/tiantian.png", avatarPrompt: "甜甜，一只三花猫，眼神清醒、略带俏皮，戴青绿色领巾，精致 3D 动画风格，正面半身头像。" },
    { id: 2, emoji: "🐶", name: "铁柱", meta: "2 岁 · 铁岭", persona: "清澈愚蠢，盲目乐观", quirk: "我觉得这事儿能行！", accent: ACCENTS[1], avatar: "/avatars/tiezhu.png", avatarPrompt: "铁柱，一只柴犬，眼神热情、笑容憨厚，戴珊瑚色领巾，精致 3D 动画风格，正面半身头像。" },
  ],
  interaction: "甜甜负责真相，铁柱负责捧哏，冲突即幽默",
  forbidden: ["不碰负面情绪宣泄", "不人身攻击", "不玩低俗梗"],
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value)
}

function isCharacter(value: unknown): value is AccountCharacter {
  return isRecord(value) && typeof value.id === "number" && Number.isFinite(value.id) &&
    ["emoji", "name", "meta", "persona", "quirk", "accent"].every((key) => typeof value[key] === "string") &&
    (value.avatar === undefined || typeof value.avatar === "string") &&
    (value.avatarPrompt === undefined || typeof value.avatarPrompt === "string")
}

function normalize(value: unknown): AccountSettings | null {
  if (!isRecord(value) || !Array.isArray(value.chars)) return null
  const chars = value.chars.filter(isCharacter)
  if (!chars.length) return null
  const p = isRecord(value.profile) ? value.profile : {}
  const text = (key: keyof AccountProfile): string => typeof p[key] === "string" ? p[key] as string : DEFAULT_PROFILE[key] as string
  const options = (key: "formats" | "platforms", allowed: string[]): string[] => {
    const selected = Array.isArray(p[key]) ? p[key].filter((item): item is string => typeof item === "string" && allowed.includes(item)) : []
    return selected.length ? [...new Set(selected)] : DEFAULT_PROFILE[key]
  }
  return {
    profile: {
      avatar: typeof p.avatar === "string" ? p.avatar : DEFAULT_PROFILE.avatar,
      name: text("name"), niche: text("niche"), audience: text("audience"),
      valueProposition: text("valueProposition"), contentPreferences: text("contentPreferences"),
      formats: options("formats", FORMATS), platforms: options("platforms", PLATFORMS),
      tone: TONES.includes(text("tone")) ? text("tone") : DEFAULT_PROFILE.tone,
      duration: typeof p.duration === "number" && Number.isFinite(p.duration) && p.duration >= 15 && p.duration <= 600 ? p.duration : DEFAULT_PROFILE.duration,
    },
    chars,
    interaction: typeof value.interaction === "string" ? value.interaction : DEFAULT_ACCOUNT.interaction,
    forbidden: Array.isArray(value.forbidden) ? value.forbidden.filter((rule): rule is string => typeof rule === "string") : DEFAULT_ACCOUNT.forbidden,
  }
}

export function loadAccountSettings(): AccountSettings {
  // Older avatar/role settings are retained when the account profile is introduced.
  for (const key of [ACCOUNT_STORAGE_KEY, LEGACY_STORAGE_KEY]) {
    try {
      const settings = normalize(JSON.parse(localStorage.getItem(key) ?? "null"))
      if (settings) return settings
    } catch { /* Fall through to the previous format or defaults. */ }
  }
  return DEFAULT_ACCOUNT
}

export function saveAccountSettings(settings: AccountSettings) {
  localStorage.setItem(ACCOUNT_STORAGE_KEY, JSON.stringify(settings))
}
