import { useEffect, useState, useCallback } from 'react'
import { Link, Outlet, useNavigate, useParams } from 'react-router-dom'
import { api, MOCK } from './api'

const PRI = { urgent: 0, high: 1, medium: 2, low: 3 }
const PRI_C = { urgent: 'bg-red-100 text-red-700', high: 'bg-orange-100 text-orange-700', medium: 'bg-amber-100 text-amber-700', low: 'bg-slate-100 text-slate-600' }
const ST_C = { needs_human: 'border border-red-400 text-red-600', open: 'bg-slate-100 text-slate-600', in_progress: 'bg-blue-100 text-blue-700', ai_resolved: 'bg-green-100 text-green-700', closed: 'bg-slate-200 text-slate-500' }
const Badge = ({ cls, children }) => <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${cls}`}>{children}</span>
const age = (iso) => { const m = Math.max(1, Math.round((Date.now() - new Date(iso)) / 60000)); return m < 60 ? `${m} min ago` : m < 1440 ? `${Math.round(m / 60)} h ago` : `${Math.round(m / 1440)} d ago` }
const kt = (iso) => new Date(iso).toLocaleString('en-GB', { timeZone: 'Asia/Kathmandu' })
const card = 'rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900'
const sel = 'rounded-lg border border-slate-300 bg-white p-2 text-sm dark:border-slate-700 dark:bg-slate-900'

export function Login() {  // PLACEHOLDER auth: any non-empty values work. Replace with real auth before launch.
  const nav = useNavigate(); const [u, setU] = useState(''), [p, setP] = useState('')
  return (<div className="grid min-h-screen place-items-center p-4"><form className={`${card} w-full max-w-sm space-y-4`} onSubmit={(e) => { e.preventDefault(); if (u && p) { localStorage.setItem('token', MOCK ? 'demo' : p); nav('/staff') } }}>
    <h1 className="text-xl font-bold text-blue-600">FutsalHub Support</h1><p className="text-sm text-slate-500">Staff Login. This is a demo login; use any credentials.</p>
    <label className="block text-sm">Email or username<input className={`${sel} mt-1 w-full`} value={u} onChange={(e) => setU(e.target.value)} /></label>
    <label className="block text-sm">Password<input type="password" className={`${sel} mt-1 w-full`} value={p} onChange={(e) => setP(e.target.value)} /></label>
    <button className="w-full rounded-lg bg-blue-600 py-2 font-medium text-white">Sign in</button></form></div>)
}

export function Layout() {
  const nav = useNavigate(); const [dark, setDark] = useState(false)
  useEffect(() => { if (!localStorage.getItem('token')) nav('/staff/login') }, [nav])
  useEffect(() => { document.documentElement.classList.toggle('dark', dark) }, [dark])
  return (<div className="min-h-screen"><header className="flex items-center justify-between border-b border-slate-200 bg-white px-6 py-3 dark:border-slate-800 dark:bg-slate-900">
    <Link to="/staff" className="font-bold text-blue-600">FutsalHub Support · Staff</Link>
    <div className="flex items-center gap-3 text-sm">{MOCK && <Badge cls="bg-green-100 text-green-700">Mock data</Badge>}<Link to="/" className="underline">Chat</Link>
      <button onClick={() => setDark(!dark)}>{dark ? 'Light' : 'Dark'}</button>
      <button onClick={() => { localStorage.removeItem('token'); nav('/staff/login') }}>Log out</button></div></header>
    <main className="mx-auto max-w-6xl p-6"><Outlet /></main></div>)
}

export function Queue() {
  const nav = useNavigate(); const [rows, setRows] = useState(null), [err, setErr] = useState('')
  const [f, setF] = useState({ status: 'needs_human', priority: '', category: '', q: '' })
  const load = useCallback(() => api.listTickets().then((r) => { setRows(r); setErr('') }).catch((e) => setErr(e.message)), [])
  useEffect(() => { load(); const t = setInterval(load, 10000); return () => clearInterval(t) }, [load])
  if (err) return <p className="text-red-600">{err}</p>
  if (!rows) return <p className="animate-pulse text-slate-400">Loading tickets…</p>
  const open = rows.filter((t) => ['needs_human', 'open', 'in_progress'].includes(t.status))
  const shown = rows.filter((t) => (!f.status || t.status === f.status) && (!f.priority || t.priority === f.priority) && (!f.category || t.category === f.category)
    && (!f.q || `${t.id} ${t.summary}`.toLowerCase().includes(f.q.toLowerCase()))).sort((a, b) => PRI[a.priority] - PRI[b.priority] || new Date(a.created_at) - new Date(b.created_at))
  const opts = (k) => [...new Set(rows.map((t) => t[k]))]
  const stats = [['Needs human', rows.filter((t) => t.status === 'needs_human').length], ['Urgent/High open', open.filter((t) => ['urgent', 'high'].includes(t.priority)).length],
    ['Resolved by AI', rows.filter((t) => t.status === 'ai_resolved').length], ['AI resolution rate', `${Math.round((rows.filter((t) => t.status === 'ai_resolved').length / rows.length) * 100)}%`]]
  return (<div className="space-y-4"><div className="grid grid-cols-2 gap-3 md:grid-cols-4">{stats.map(([l, v]) => <div key={l} className={card}><div className="text-2xl font-bold">{v}</div><div className="text-xs text-slate-500">{l}</div></div>)}</div>
    <div className="flex flex-wrap gap-2">
      <input placeholder="Search tickets…" className={sel} value={f.q} onChange={(e) => setF({ ...f, q: e.target.value })} />
      {['status', 'priority', 'category'].map((k) => <select key={k} aria-label={k} className={sel} value={f[k]} onChange={(e) => setF({ ...f, [k]: e.target.value })}><option value="">All {k}</option>{opts(k).map((o) => <option key={o}>{o}</option>)}</select>)}
      <button onClick={load} className={sel}>Refresh</button></div>
    <div className={`${card} overflow-x-auto p-0`}><table className="w-full text-left text-sm"><thead className="border-b border-slate-200 text-slate-500 dark:border-slate-800"><tr>{['ID', 'Priority', 'Category', 'Status', 'Summary', 'Language', 'Age'].map((h) => <th key={h} className="p-3 font-medium">{h}</th>)}</tr></thead>
      <tbody>{shown.map((t) => <tr key={t.id} tabIndex={0} onClick={() => nav(`/staff/tickets/${t.id}`)} onKeyDown={(e) => e.key === 'Enter' && nav(`/staff/tickets/${t.id}`)} className="cursor-pointer border-b border-slate-100 hover:bg-slate-50 dark:border-slate-800 dark:hover:bg-slate-800">
        <td className="p-3 font-semibold text-blue-600">#{t.id}</td><td className="p-3"><Badge cls={PRI_C[t.priority]}>{t.priority}</Badge></td><td className="p-3">{t.category}</td>
        <td className="p-3"><Badge cls={ST_C[t.status]}>{t.status}</Badge></td><td className="max-w-xs truncate p-3">{t.summary}</td><td className="p-3">{t.language}</td><td className="p-3" title={kt(t.created_at)}>{age(t.created_at)}</td></tr>)}
        {!shown.length && <tr><td colSpan={7} className="p-6 text-center text-slate-500">No tickets match these filters.</td></tr>}</tbody></table></div></div>)
}

export function Detail() {
  const { id } = useParams(); const [t, setT] = useState(null), [txt, setTxt] = useState(''), [sending, setSending] = useState(false)
  const load = useCallback(() => api.getTicket(id).then((x) => setT({ ...x })), [id])
  useEffect(() => { load() }, [load])
  if (!t) return <p className="animate-pulse text-slate-400">Loading ticket…</p>
  const ex = t.extracted || {}, overrides = (t.logs || []).filter((l) => l.step === 'override').flatMap((l) => l.output.reasons || [])
  const row = (k, v) => <div key={k} className="flex justify-between gap-4 text-sm"><span className="text-slate-500">{k}</span><span>{v ?? '-'}</span></div>
  return (<div className="space-y-4"><Link to="/staff" className="text-sm text-slate-500">← Back to tickets</Link>
    <div className="flex flex-wrap items-center gap-3"><h1 className="text-2xl font-bold">Ticket #{t.id}</h1><Badge cls={ST_C[t.status]}>{t.status}</Badge><Badge cls={PRI_C[t.priority]}>{t.priority}</Badge>
      <div className="ml-auto flex gap-2"><button onClick={() => api.setStatus(t.id, 'in_progress').then(load)} className="rounded-lg bg-blue-600 px-3 py-2 text-sm text-white">Mark in progress</button>
        <button onClick={() => api.setStatus(t.id, 'closed').then(load)} className={sel}>Close ticket</button></div></div>
    <div className="grid gap-4 md:grid-cols-3"><div className="space-y-3 md:col-span-2"><div className={`${card} space-y-3`}>
      {(t.messages || []).map((m) => <div key={m.id} className={`flex ${m.role === 'customer' ? 'justify-end' : ''}`}><div className="max-w-[80%]"><div className={`rounded-2xl px-4 py-2 text-sm ${m.role === 'customer' ? 'bg-blue-600 text-white' : m.role === 'staff' ? 'bg-emerald-100 text-emerald-900' : 'bg-slate-100 dark:bg-slate-800'}`}>{m.content}</div><div className="mt-0.5 text-xs text-slate-400">{m.role} · {kt(m.created_at)}</div></div></div>)}</div>
      <form className="flex gap-2" onSubmit={async (e) => { e.preventDefault(); const c = txt.trim(); if (!c || sending) return; setSending(true); try { const m = await api.staffReply(t.id, c); setTxt(''); setT((x) => ({ ...x, messages: [...(x.messages || []), m] })) } catch (err) { alert('Reply failed: ' + err.message) } setSending(false) }}>
        <input aria-label="Staff reply" className={`${sel} flex-1`} placeholder="Reply as staff…" value={txt} onChange={(e) => setTxt(e.target.value)} /><button disabled={sending || !txt.trim()} className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 text-sm text-white disabled:opacity-50">{sending && <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />}{sending ? 'Sending…' : 'Send reply'}</button></form></div>
      <div className="space-y-3">
        <div className="rounded-xl border-2 border-amber-300 bg-amber-50 p-4 text-sm text-amber-900 dark:bg-amber-950 dark:text-amber-100"><div className="mb-1 font-semibold">Recommended action</div>{t.recommended_action || 'None for this ticket.'}
          <div className="mt-3 flex gap-2"><button disabled title="Approval workflow not connected yet" className="rounded-lg bg-green-600 px-3 py-1 text-white opacity-40">Approve</button><button disabled title="Approval workflow not connected yet" className="rounded-lg bg-red-600 px-3 py-1 text-white opacity-40">Reject</button></div></div>
        <div className={`${card} space-y-1`}><div className="font-semibold">AI summary</div><p className="text-sm">{t.summary}</p>{row('Category', t.category)}{row('Sentiment', t.sentiment)}{row('Language', t.language)}</div>
        <div className={`${card} space-y-1`}><div className="font-semibold">Extracted details</div>{row('Booking ID', ex.booking_id)}{row('Transaction ID', ex.transaction_id)}{row('Amount', ex.amount != null && `Rs ${ex.amount.toLocaleString()}`)}{row('Date', ex.date)}</div>
        {overrides.length > 0 && <div className={card}><div className="font-semibold">Safety overrides</div><ul className="list-disc pl-5 text-sm">{overrides.map((o) => <li key={o}>{o}</li>)}</ul></div>}
        <div className={card}><div className="mb-2 font-semibold">Agent timeline</div>{(t.logs || []).map((l) => <details key={l.id} className="border-t border-slate-100 py-1 text-sm dark:border-slate-800"><summary className="cursor-pointer">{l.step} <span className="text-xs text-slate-400">{kt(l.created_at)}</span></summary><pre className="overflow-auto text-xs">{JSON.stringify(l.output, null, 2)}</pre></details>)}</div></div></div></div>)
}
