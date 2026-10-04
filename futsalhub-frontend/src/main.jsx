import React from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import './index.css'
import Chat from './Chat'
import { Login, Layout, Queue, Detail } from './Staff'

class ErrorBoundary extends React.Component {
  state = { error: null }
  static getDerivedStateFromError(error) { return { error } }
  render() {
    if (!this.state.error) return this.props.children
    return (<div style={{ padding: 24, fontFamily: 'system-ui' }}>
      <h1 style={{ fontSize: 20, fontWeight: 700 }}>Something broke in the page</h1>
      <p>Copy the text below and send it to whoever is helping you debug.</p>
      <pre style={{ whiteSpace: 'pre-wrap', background: '#fee', padding: 12 }}>{String(this.state.error?.stack || this.state.error)}</pre>
      <button onClick={() => location.reload()}>Reload</button></div>)
  }
}

createRoot(document.getElementById('root')).render(
  <ErrorBoundary><BrowserRouter><Routes>
    <Route path="/" element={<Chat />} />
    <Route path="/staff/login" element={<Login />} />
    <Route path="/staff" element={<Layout />}>
      <Route index element={<Queue />} />
      <Route path="tickets/:id" element={<Detail />} />
    </Route>
  </Routes></BrowserRouter></ErrorBoundary>)
