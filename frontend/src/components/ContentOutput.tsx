import { useState } from "react"
import { Sparkle, Link, Arrow } from "../icons"
import type { Capabilities, ContentCharacter } from "../api"
import type { useContentWorkflow } from "../useContentWorkflow"

const CHANNELS = [
  { key: "douyin", name: "抖音" }, { key: "kuaishou", name: "快手" },
  { key: "xhs", name: "小红书" }, { key: "bili", name: "B站" }, { key: "shipinhao", name: "视频号" },
]

export default function ContentOutput({ step, workflow: w, capabilities, characters, channels, toggleChannel }: {
  step: number; workflow: ReturnType<typeof useContentWorkflow>; capabilities: Capabilities | null;
  characters: ContentCharacter[]; channels: Set<string>; toggleChannel: (key: string) => void;
}) {
  const [editing, setEditing] = useState(false)
  const s = w.script
  const videoStale = !!w.draft && !!s && JSON.stringify(s.scenes) !== JSON.stringify(w.draft.script.scenes)
  const patchScene = (index: number, narration: string) => {
    if (s) w.setScript({ ...s, scenes: s.scenes.map((scene, i) => i === index ? { ...scene, narration, on_screen_text: narration } : scene) })
  }
  return (
    <div className="max-w-5xl">
      <div className="mb-5 flex flex-wrap items-center gap-3 text-[13px]">
        <span className="text-sub">{w.draft?.mode === "live" ? "AI 生成" : "示例剧本"}</span>
        {w.analysisId && <span className="text-primary">已关联拆解报告</span>}
        <select aria-label="草稿历史" disabled={w.busy} value={w.draft?.id ?? ""} onChange={(e) => e.target.value && w.restore(e.target.value)} className="ml-auto max-w-full rounded-lg border border-line bg-card px-3 py-2">
          <option value="">历史草稿</option>
          {w.history.map((d) => <option key={d.id} value={d.id}>{d.script.title} · {d.mode === "demo" ? "示例" : "AI"}</option>)}
        </select>
      </div>
      {w.busy && <p role="status" className="mb-4 text-[14px] text-primary">{w.stage}</p>}
      {w.error && <p role="alert" className="mb-4 whitespace-pre-wrap break-words text-[14px] text-red-600">{w.error}</p>}
      {w.notice && <p role="status" className="mb-4 text-[14px] text-success">{w.notice}</p>}
      {!s && <button disabled={w.busy} onClick={() => w.generate("demo")} className="rounded-lg border border-line bg-card px-4 py-2 text-[14px]">载入示例剧本</button>}
      {step === 2 && (
        <>
          <div className="mb-5 flex flex-wrap items-center gap-3">
            <button disabled={w.busy || !capabilities?.script} onClick={() => { setEditing(false); void w.generate("live") }} className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-[14px] font-semibold text-white disabled:opacity-40"><Sparkle className="size-4" />{w.draft?.mode === "live" ? "重新生成剧本" : "AI 生成我的剧本"}</button>
            <button disabled={w.busy} onClick={() => { setEditing(false); void w.generate("demo") }} className="rounded-lg border border-line bg-card px-4 py-2.5 text-[14px]">使用示例剧本</button>
            {!capabilities?.script && <span className="text-[13px] text-sub">模型未配置</span>}
          </div>
          {s && <div className="grid gap-6 lg:grid-cols-2">
            <section className="min-w-0 rounded-lg border border-line bg-card">
              <div className="flex items-center justify-between gap-3 border-b border-line px-5 py-4">
                <h2 className="text-[15px] font-bold">对话剧本</h2>
                <button disabled={w.busy} onClick={() => setEditing(!editing)} className="text-[13px] text-primary">{editing ? "预览剧本" : "编辑剧本"}</button>
              </div>
              <div className="space-y-5 p-5">
                {s.scenes.map((scene, i) => {
                  const character = characters.find((c) => c.name === scene.speaker)
                  return <div key={scene.index} className={"flex gap-3 " + (i % 2 ? "flex-row-reverse" : "")}>
                    {character?.img ? <img src={character.img} alt={scene.speaker + "头像"} className="size-9 shrink-0 rounded-lg object-cover" /> : <span className="grid size-9 shrink-0 place-items-center rounded-lg bg-canvas">{character?.emoji ?? "·"}</span>}
                    <div className="min-w-0 flex-1">
                      <div className="text-[12px] text-sub">{scene.speaker}{scene.emotion && "（" + scene.emotion + "）"}</div>
                      {editing ? <textarea aria-label={"第" + (i + 1) + "句台词"} rows={3} value={scene.narration} onChange={(e) => patchScene(i, e.target.value)} className="mt-2 w-full rounded-lg border border-line bg-canvas p-3 text-[14px]" /> : <p className={"mt-2 whitespace-pre-wrap break-words rounded-lg p-3 text-[14px] leading-relaxed " + (i % 2 ? "bg-primary/5" : "bg-canvas")}>{scene.narration}</p>}
                    </div>
                  </div>
                })}
                <button disabled={w.busy} onClick={w.saveChanges} className="rounded-lg border border-line px-4 py-2 text-[13px] text-primary">保存剧本</button>
              </div>
            </section>
            <section className="min-w-0">
              <h2 className="text-[15px] font-bold">视频预览</h2>
              {w.draft?.video && !videoStale ? <video controls preload="metadata" src={w.draft.video.url} className="mt-4 aspect-[9/16] max-h-[460px] w-full rounded-lg bg-black object-contain" /> : (
                <div className="mt-4 flex aspect-video items-center justify-center gap-4 rounded-lg border border-line bg-card p-5">
                  {characters.slice(0, 3).map((c) => c.img ? <img key={c.id} src={c.img} alt={c.name + "角色预览"} className="size-16 rounded-lg object-cover sm:size-20" /> : <span key={c.id} className="text-[32px]">{c.emoji}</span>)}
                </div>
              )}
              <p className="mt-3 text-[13px] text-sub">{videoStale ? "台词已修改，需重新生成成片。" : w.draft?.video ? `成片已生成 · ${w.draft.video.provider === "wan" ? "通义万相" : "角色一致性合成"}` : "尚未生成视频"}</p>
              <button disabled={w.busy || !capabilities?.video} onClick={w.render} className="mt-4 inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-[14px] font-semibold text-white disabled:opacity-40"><Sparkle className="size-4" />{w.draft?.video ? "重新生成成片" : "确认剧本并生成视频"}</button>
              <p className="mt-2 text-[12px] text-sub">{capabilities?.video ? "包含中文配音与画面字幕 · 最长 60 秒" : "视频服务未配置"}</p>
              {w.draft?.prompts && <details className="mt-5 border-t border-line pt-4"><summary className="cursor-pointer text-[14px]">视频 Prompt</summary>{w.draft.prompts.clips.map((clip) => <p key={clip.index} className="mt-3 whitespace-pre-wrap break-words text-[13px] text-sub">{clip.prompt}</p>)}</details>}
            </section>
          </div>}
        </>
      )}
      {step === 3 && s && (
        <>
          <h2 className="text-[22px] font-display font-extrabold">发布文案与渠道</h2>
          <div className="mt-6 grid gap-6 lg:grid-cols-[1.2fr_1fr]">
            <section className="min-w-0">
              <label className="text-[14px] font-semibold">发布文案
                <textarea aria-label="发布文案" disabled={w.busy} rows={8} value={s.caption} onChange={(e) => w.setScript({ ...s, caption: e.target.value })} className="mt-3 w-full resize-y rounded-lg border border-line bg-card p-4 text-[14px] font-normal leading-relaxed outline-none focus:border-primary" />
              </label>
              <label className="mt-4 block text-[13px] font-semibold">话题标签
                <input aria-label="话题标签" disabled={w.busy} value={s.hashtags.map((t) => "#" + t.replace(/^#/, "")).join(" ")} onChange={(e) => w.setScript({ ...s, hashtags: e.target.value.split(/\s+/).map((t) => t.replace(/^#/, "")).filter(Boolean) })} className="mt-2 w-full rounded-lg border border-line bg-card px-3 py-2 text-[13px] font-normal" />
              </label>
              <button disabled={w.busy} onClick={w.saveChanges} className="mt-4 rounded-lg border border-line bg-card px-4 py-2 text-[13px] text-primary">保存文案</button>
            </section>
            <fieldset disabled={w.busy} className="min-w-0">
              <legend className="text-[14px] font-semibold">发布渠道</legend>
              <div className="mt-3 space-y-3">
                {CHANNELS.map((c) => <label key={c.key} className="flex items-center justify-between rounded-lg border border-line bg-card px-4 py-3 text-[14px]">{c.name}<input type="checkbox" aria-label={"发布到" + c.name} checked={channels.has(c.key)} onChange={() => toggleChannel(c.key)} className="size-4 accent-primary" /></label>)}
              </div>
              <p className="mt-3 text-[13px] text-sub">平台未授权；加入队列不会直接发布。</p>
            </fieldset>
          </div>
          <div className="mt-6 flex flex-wrap gap-3">
            <button disabled={w.busy || !channels.size || !w.draft?.video || videoStale} onClick={() => w.queue(CHANNELS.filter((c) => channels.has(c.key)).map((c) => c.name))} className="inline-flex items-center gap-2 rounded-lg bg-primary px-5 py-3 text-[14px] font-semibold text-white disabled:opacity-40">加入待发布队列（{channels.size}）<Arrow className="size-4" /></button>
            <button disabled={w.busy} onClick={w.exportPackage} className="inline-flex items-center gap-2 rounded-lg border border-line bg-card px-5 py-3 text-[14px] font-semibold"><Link className="size-4" />导出发布包</button>
          </div>
        </>
      )}
    </div>
  )
}
