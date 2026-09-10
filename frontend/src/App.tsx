import { useEffect, useState } from "react"
import { PageKey, Sidebar } from "./shared"
import Landing from "./pages/Landing"
import Login from "./pages/Login"
import About from "./pages/About"
import Dashboard from "./pages/Dashboard"
import Deconstruct from "./pages/Deconstruct"
import Character from "./pages/Character"
import Generate from "./pages/Generate"
import Review from "./pages/Review"
import Account from "./pages/Account"
import { loadAccountSettings, saveAccountSettings, type AccountSettings } from "./account"
import { api, errorText, type Capabilities } from "./api"

const PAGE_KEY = "creatoros_page"
const LOGIN_KEY = "creatoros_login_account"
const PUBLIC_PAGES = new Set<PageKey>(["landing", "login", "about"])

export default function App() {
  const [account, setAccount] = useState(loadAccountSettings)
  const [ready, setReady] = useState(false)
  const [backendError, setBackendError] = useState("")
  const [capabilities, setCapabilities] = useState<Capabilities | null>(null)
  useEffect(() => {
    let active = true
    const connect = async () => {
      try {
        const health = await api<{ capabilities: Capabilities }>("/health")
        const stored = await api<{ account: AccountSettings | null }>("/account")
        const settings = stored.account ?? loadAccountSettings()
        if (!stored.account) await api("/account", { method: "PUT", body: JSON.stringify(settings) })
        if (!active) return
        setAccount(settings)
        setCapabilities(health.capabilities)
      } catch (error) { if (active) setBackendError(errorText(error)) }
      finally { if (active) setReady(true) }
    }
    void connect()
    return () => { active = false }
  }, [])
  const saveAccount = async (settings: AccountSettings) => {
    await api("/account", { method: "PUT", body: JSON.stringify(settings) })
    try { saveAccountSettings(settings) } catch { /* The database already contains the saved account. */ }
    setAccount(settings)
  }
  const [page, setPage] = useState<PageKey>(() => {
    if (typeof localStorage === "undefined") return "landing"
    const saved = localStorage.getItem(PAGE_KEY) as PageKey | null
    const loggedIn = Boolean(localStorage.getItem(LOGIN_KEY))
    return saved && (PUBLIC_PAGES.has(saved) || loggedIn) ? saved : "landing"
  })
  const go = (k: PageKey) => {
    const loggedIn = typeof localStorage !== "undefined" && Boolean(localStorage.getItem(LOGIN_KEY))
    const target = PUBLIC_PAGES.has(k) || loggedIn ? k : "login"
    setPage(target)
    try {
      localStorage.setItem(PAGE_KEY, target)
    } catch {
      /* ignore */
    }
    window.scrollTo?.({ top: 0 })
  }
  const logout = () => {
    try { localStorage.removeItem(LOGIN_KEY) } catch { /* Account content remains stored. */ }
    go("login")
  }

  return (
    <div className="h-full flex flex-col bg-canvas text-ink">
      {page === "landing" ? (
        <div className="flex-1 overflow-auto">
          <Landing go={go} />
        </div>
      ) : page === "login" ? (
        <div className="flex-1 overflow-auto">
          <Login go={go} />
        </div>
      ) : page === "about" ? (
        <div className="flex-1 overflow-auto">
          <About go={go} />
        </div>
      ) : (
        <div className="flex min-h-0 flex-1 overflow-hidden">
          <Sidebar active={page} go={go} accountName={account.profile.name} accountAvatar={account.profile.avatar} />
          {!ready ? <p role="status" className="p-8 text-sub">连接后端中…</p> : <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
            {backendError && <div role="alert" className="border-b border-red-200 bg-red-50 px-4 py-2 text-[13px] text-red-700">{backendError} <button onClick={() => location.reload()} className="underline">重新连接</button></div>}
            {page === "dashboard" && <Dashboard go={go} />}
            {page === "deconstruct" && <Deconstruct go={go} capabilities={capabilities} />}
            {page === "character" && <Character account={account} onSave={saveAccount} />}
            {page === "generate" && <Generate account={account} capabilities={capabilities} />}
            {page === "review" && <Review />}
            {page === "account" && <Account account={account} onSave={saveAccount} onLogout={logout} />}
          </div>}
        </div>
      )}
    </div>
  )
}
