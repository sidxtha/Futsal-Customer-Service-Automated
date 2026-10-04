import { useState, useRef, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { api } from './api'

const USERS = [['Anonymous', null], ['Alice (all good)', '11111111-1111-1111-1111-111111111111'], ['Bob (paid, no booking)', '22222222-2222-2222-2222-222222222222'],
  ['Carol (charged twice)', '33333333-3333-3333-3333-333333333333'], ['Dave (payment pending)', '44444444-4444-4444-4444-444444444444']]
const CHIPS = ['What time do you open on Saturdays?', 'I paid Rs 1800 yesterday via eSewa but my booking is not showing', 'I was charged twice for booking F3001', 'मेरो पैसा कट्यो तर बुकिङ देखिएन']
const HELLO = { role: 'ai', text: 'Hello! How can I help you today? You can ask about bookings, payments or our futsal courts.' }

export default function Chat() {
  const [msgs, setMsgs] = useState([HELLO]); const [text, setText] = useState(''); const [busy, setBusy] = useState(false)
  const [user, setUser] = useState(0); const [dev, setDev] = useState(false); const end = useRef()
  useEffect(() => { end.current?.scrollIntoView({ behavior: 'smooth' }) }, [msgs, busy])

  const send = async (t) => {
    t = (t ?? text).trim(); if (!t || busy) return
    setText(''); setMsgs((m) => [...m, { role: 'me', text: t }]); setBusy(true)
    try {
      const r = await api.sendMessage(t, USERS[user][1]), nep = /nep/i.test(r.classification?.language ?? '')
      const fallback = nep ? 'धन्यवाद, मैले यो हाम्रो टोलीलाई पठाएको छु, उहाँहरूले सम्पर्क गर्नुहुनेछ।' : "Thanks, I've passed this to our team and they'll follow up."
      setMsgs((m) => [...m, { role: 'ai', text: r.reply ?? fallback, status: r.status, ticket: r.ticket_id, raw: r }])
    } catch (e) { setMsgs((m) => [...m, { role: 'ai', text: e.message, error: true }]) }
    setBusy(false)
  }
  return (
    <div className="min-h-screen p-4 md:p-8">
      <header className="mx-auto flex max-w-3xl flex-wrap items-center justify-between gap-3 pb-4">
        <div><h1 className="text-xl font-bold text-blue-600">FutsalHub Support</h1><p className="text-sm text-slate-500">Ask about bookings, payments or our courts.</p></div>
        <div className="flex items-center gap-3 text-xs text-slate-500">
          <label className="flex items-center gap-1"><input type="checkbox" checked={dev} onChange={(e) => setDev(e.target.checked)} />Developer view</label>
          <div><div>Demo mode, simulates a logged-in customer</div>
            <select aria-label="Demo customer" value={user} onChange={(e) => { setUser(+e.target.value); setMsgs([HELLO]) }} className="mt-1 w-full rounded-lg border border-slate-300 bg-white p-2 text-sm text-slate-900 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100">
              {USERS.map(([n], i) => <option key={n} value={i}>{n}</option>)}</select></div>
          <Link to="/staff" className="underline">Staff</Link></div>
      </header>
      <main className="mx-auto flex h-[70vh] max-w-3xl flex-col rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <div className="border-b border-slate-200 p-4 dark:border-slate-800"><div className="font-semibold">FutsalHub Assistant</div><div className="text-xs text-slate-500">Online • Always here to help</div></div>
        <div className="flex-1 space-y-4 overflow-y-auto p-4">
          {msgs.map((m, i) => (
            <div key={i} className={`flex ${m.role === 'me' ? 'justify-end' : 'justify-start'}`}>
              <div className="max-w-[80%]">
                <div className={`whitespace-pre-wrap rounded-2xl px-4 py-2 text-sm ${m.role === 'me' ? 'bg-blue-600 text-white' : m.error ? 'bg-red-50 text-red-700 dark:bg-red-950 dark:text-red-300' : 'bg-slate-100 dark:bg-slate-800'}`}>{m.text}</div>
                {m.status === 'needs_human' && <span className="mt-1 inline-block rounded-full border border-red-300 px-2 py-0.5 text-xs text-red-600">Passed to our team · Ticket #{m.ticket}</span>}
                {m.status === 'ai_resolved' && <span className="mt-1 inline-block text-xs text-green-600">Answered automatically</span>}
                {dev && m.raw && <details className="mt-1 text-xs text-slate-500"><summary className="cursor-pointer">Developer view</summary><pre className="overflow-auto rounded bg-slate-100 p-2 dark:bg-slate-800">{JSON.stringify(m.raw, null, 2)}</pre></details>}
              </div></div>))}
          {busy && <div className="w-fit animate-pulse rounded-2xl bg-slate-100 px-4 py-2 text-slate-400 dark:bg-slate-800">• • •</div>}
          <div ref={end} /></div>
        <div className="flex flex-wrap gap-2 px-4 pb-2">{CHIPS.map((c) => <button key={c} onClick={() => send(c)} className="rounded-full border border-blue-200 px-3 py-1 text-xs text-blue-700 hover:bg-blue-50 dark:border-blue-900 dark:text-blue-300 dark:hover:bg-slate-800">{c}</button>)}</div>
        <div className="flex items-end gap-2 border-t border-slate-200 p-4 dark:border-slate-800">
          <textarea aria-label="Message" rows={1} maxLength={4000} value={text} onChange={(e) => setText(e.target.value)} placeholder="Type your message..."
            onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }}
            className="flex-1 resize-none rounded-xl border border-slate-300 bg-transparent p-3 text-sm outline-none focus:ring-2 focus:ring-blue-500 dark:border-slate-700" />
          <span className="pb-3 text-xs text-slate-400">{text.length}/4000</span>
          <button onClick={() => send()} disabled={busy || !text.trim()} className="rounded-xl bg-blue-600 px-4 py-3 text-sm font-medium text-white disabled:opacity-40">Send</button></div>
      </main></div>)
}
