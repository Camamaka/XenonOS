import { FormEvent, useEffect, useState } from 'react'
import {
  Check,
  CheckCircle2,
  ChevronRight,
  Globe2,
  LogOut,
  Moon,
  Paperclip,
  Send,
  ShieldCheck,
  Sun,
  UserPlus,
  X,
} from 'lucide-react'
import {
  createUserWithEmailAndPassword,
  onAuthStateChanged,
  signInWithEmailAndPassword,
  signInWithPopup,
  signOut,
  User,
} from 'firebase/auth'
import { collection, doc, getDocs, query, setDoc, where } from 'firebase/firestore'
import { auth, db, googleProvider, isFirebaseConfigured } from './firebase'

type AuthMode = 'signin' | 'signup'
type LocalConversation = { name: string; email: string; messages: { id: number; text: string; sent: boolean }[] }

const tutorialSteps = [
  { title: 'Your private workspace', text: 'XenonChat starts with an empty inbox. Your conversations appear here after you connect with someone.' },
  { title: 'Find your people', text: 'Use the new conversation button to start a chat once contacts are connected to your account.' },
  { title: 'Stay in control', text: 'Your session is protected by Firebase Authentication. Sign out whenever you leave a shared device.' },
]

function App() {
  const [user, setUser] = useState<User | null>(null)
  const [authMode, setAuthMode] = useState<AuthMode>('signin')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [authError, setAuthError] = useState('')
  const [busy, setBusy] = useState(false)
  const [darkMode, setDarkMode] = useState(() => localStorage.getItem('xenonchat-theme') === 'dark')
  const [showTutorial, setShowTutorial] = useState(() => localStorage.getItem('xenonchat-tutorial-seen') !== 'true')
  const [tutorialStep, setTutorialStep] = useState(0)
  const [conversation, setConversation] = useState<LocalConversation | null>(null)
  const [showNewConversation, setShowNewConversation] = useState(false)
  const [contactName, setContactName] = useState('')
  const [contactEmail, setContactEmail] = useState('')
  const [draft, setDraft] = useState('')
  const [conversationError, setConversationError] = useState('')

  useEffect(() => onAuthStateChanged(auth, (nextUser) => {
    setUser(nextUser)
    if (nextUser) void setDoc(doc(db, 'users', nextUser.uid), { email: nextUser.email?.toLowerCase(), name: nextUser.displayName || nextUser.email?.split('@')[0] || 'XenonChat user' }, { merge: true })
  }), [])
  useEffect(() => {
    document.documentElement.dataset.theme = darkMode ? 'dark' : 'light'
    localStorage.setItem('xenonchat-theme', darkMode ? 'dark' : 'light')
  }, [darkMode])

  async function handleEmailAuth(event: FormEvent) {
    event.preventDefault()
    setAuthError('')
    setBusy(true)
    try {
      if (!isFirebaseConfigured) throw new Error('Firebase is not configured yet. Add the values from .env.example before signing in.')
      if (authMode === 'signup') await createUserWithEmailAndPassword(auth, email, password)
      else await signInWithEmailAndPassword(auth, email, password)
    } catch (error) {
      setAuthError(`${error instanceof Error ? error.message : 'Authentication failed. Please try again.'} Origin: ${window.location.origin}`)
    } finally {
      setBusy(false)
    }
  }

  async function handleGoogleAuth() {
    setAuthError('')
    if (!isFirebaseConfigured) {
      setAuthError('Google sign-in is not configured yet. Add the Firebase values from .env.example.')
      return
    }
    try {
      setBusy(true)
      await signInWithPopup(auth, googleProvider)
    } catch (error) {
      setAuthError(`${error instanceof Error ? error.message : 'Google sign-in failed. Please try again.'} Origin: ${window.location.origin}`)
    } finally {
      setBusy(false)
    }
  }

  function finishTutorial() {
    localStorage.setItem('xenonchat-tutorial-seen', 'true')
    setShowTutorial(false)
  }

  function openNewConversation() {
    setShowTutorial(false)
    setShowNewConversation(true)
  }

  async function startConversation(event: FormEvent) {
    event.preventDefault()
    const name = contactName.trim()
    const recipient = contactEmail.trim()
    if (!name || !recipient) return
    setConversationError('')
    try {
      const matches = await getDocs(query(collection(db, 'users'), where('email', '==', recipient.toLowerCase())))
      if (matches.empty) {
        setConversationError('No XenonChat account uses that email yet. Ask them to sign up first.')
        return
      }
    } catch {
      setConversationError('User lookup is unavailable. Create the Firestore database in Firebase, then try again.')
      return
    }
    setConversation({ name, email: recipient, messages: [] })
    setContactName('')
    setContactEmail('')
    setShowNewConversation(false)
  }

  function sendMessage(event: FormEvent) {
    event.preventDefault()
    const text = draft.trim()
    if (!text || !conversation) return
    setConversation({ ...conversation, messages: [...conversation.messages, { id: Date.now(), text, sent: true }] })
    setDraft('')
  }

  if (!user) {
    return (
      <main className="auth-shell">
        <div className="auth-decoration"><div className="brand-mark">X</div><span>Private conversations, thoughtfully made.</span></div>
        <section className="auth-card">
          <div className="auth-heading"><p className="eyebrow">Welcome to</p><h1>XenonChat</h1><p>Sign in to access your inbox. Unauthenticated visitors cannot send or receive messages.</p></div>
          <div className="auth-tabs"><button className={authMode === 'signin' ? 'selected' : ''} onClick={() => setAuthMode('signin')}>Sign in</button><button className={authMode === 'signup' ? 'selected' : ''} onClick={() => setAuthMode('signup')}>Create account</button></div>
          <button className="google-button" onClick={handleGoogleAuth} disabled={busy}><Globe2 size={18} /> Continue with Google</button>
          <div className="auth-divider"><span>or use email</span></div>
          <form className="auth-form" onSubmit={handleEmailAuth}>
            <label>Email<input type="email" value={email} onChange={(event) => setEmail(event.target.value)} required autoComplete="email" /></label>
            <label>Password<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} minLength={6} required autoComplete={authMode === 'signup' ? 'new-password' : 'current-password'} /></label>
            {authError && <p className="auth-error" role="alert">{authError}</p>}
            <button className="primary-button" disabled={busy}>{busy ? 'Please wait...' : authMode === 'signin' ? 'Sign in securely' : 'Create account'}</button>
          </form>
          {!isFirebaseConfigured && <p className="setup-note"><ShieldCheck size={15} /> Authentication is locked until Firebase is configured.</p>}
          <p className="legal-note">By continuing, you agree to keep your account secure and use XenonChat responsibly.</p>
        </section>
      </main>
    )
  }

  return (
    <main className="app-shell">
      <aside className="conversation-panel authenticated-sidebar">
        <header className="sidebar-header"><div className="brand-mark">X</div><div><p className="eyebrow">Workspace</p><h1>XenonChat</h1></div><button className="icon-button theme-button" aria-label="Toggle theme" onClick={() => setDarkMode((value) => !value)}>{darkMode ? <Sun size={18} /> : <Moon size={18} />}</button></header>
        <div className="secure-label"><ShieldCheck size={15} /><span>Private workspace</span><CheckCircle2 size={14} /></div>
        <div className="inbox-heading"><span>Inbox</span><span className="count">{conversation ? 1 : 0}</span></div>
        {conversation ? <button type="button" className="conversation-item active local-conversation" onClick={() => setConversation(conversation)}><div className="avatar blue">{conversation.name.slice(0, 2).toUpperCase()}</div><div className="conversation-copy"><div className="conversation-topline"><strong>{conversation.name}</strong><time>Now</time></div><div className="conversation-bottomline"><span>{conversation.messages.at(-1)?.text ?? 'New conversation'}</span></div></div></button> : <div className="empty-inbox"><div className="empty-icon"><Send size={22} /></div><h2>Your inbox is empty</h2><p>When you start a conversation, it will appear here. Your messages stay private to your account.</p><button type="button" className="empty-action" onClick={openNewConversation}><UserPlus size={16} /> New conversation</button></div>}
        <footer className="profile-footer"><div className="self-avatar">{(user.displayName || user.email || 'U').slice(0, 2).toUpperCase()}</div><div><strong>{user.displayName || user.email?.split('@')[0]}</strong><span>{user.email}</span></div><button className="icon-button" aria-label="Sign out" onClick={() => signOut(auth)}><LogOut size={17} /></button></footer>
      </aside>
      <section className="chat-panel empty-chat-panel">{conversation ? <><header className="chat-header"><div className="avatar blue small">{conversation.name.slice(0, 2).toUpperCase()}</div><div className="chat-person"><h2>{conversation.name}</h2><span>{conversation.email}</span></div></header><div className="message-area"><div className="message-stack">{conversation.messages.map((message) => <div className="message-row sent" key={message.id}><div className="message-content"><div className="bubble">{message.text}</div><div className="message-meta"><span>Now</span><Check size={14} /></div></div></div>)}</div></div><form className="composer" onSubmit={sendMessage}><div className="composer-box"><textarea value={draft} onChange={(event) => setDraft(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); sendMessage(event) } }} placeholder={`Message ${conversation.name}...`} rows={1} aria-label="Message" /><div className="composer-tools"><div><button type="button" className="tool-button" aria-label="Attach file"><Paperclip size={18} /></button></div><button type="submit" className="send-button" aria-label="Send message"><Send size={17} /></button></div></div></form></> : <div className="empty-chat-content"><div className="empty-chat-orbit"><Send size={27} /></div><p className="eyebrow">Ready when you are</p><h2>Start a private conversation</h2><p>Your workspace is clear. Choose the button below to connect with someone you trust.</p><button type="button" className="empty-action" onClick={openNewConversation}><UserPlus size={16} /> New conversation</button><div className="security-pills"><span><ShieldCheck size={14} /> Authenticated</span><span><Check size={14} /> Encrypted session</span></div></div>}</section>
      {showNewConversation && <div className="tutorial-backdrop"><section className="new-conversation-card"><button type="button" className="tutorial-close icon-button" onClick={() => setShowNewConversation(false)} aria-label="Close"><X size={18} /></button><p className="eyebrow">New message</p><h2>Start a conversation</h2><p>Only registered XenonChat users can be contacted.</p><form className="auth-form" onSubmit={startConversation}><label>Name<input value={contactName} onChange={(event) => setContactName(event.target.value)} placeholder="Their name" required /></label><label>Email<input type="email" value={contactEmail} onChange={(event) => setContactEmail(event.target.value)} placeholder="name@example.com" required /></label>{conversationError && <p className="auth-error" role="alert">{conversationError}</p>}<button type="submit" className="primary-button"><Send size={16} /> Create conversation</button></form></section></div>}
      {showTutorial && <div className="tutorial-backdrop"><section className="tutorial-card"><button className="tutorial-close icon-button" onClick={finishTutorial} aria-label="Close tutorial"><X size={18} /></button><div className="tutorial-graphic"><div className="tutorial-step-number">0{tutorialStep + 1}</div><div className="tutorial-line" /></div><p className="eyebrow">Quick tour</p><h2>{tutorialSteps[tutorialStep].title}</h2><p>{tutorialSteps[tutorialStep].text}</p><div className="tutorial-footer"><div className="tutorial-dots">{tutorialSteps.map((step, index) => <i className={index === tutorialStep ? 'active' : ''} key={step.title} />)}</div>{tutorialStep < tutorialSteps.length - 1 ? <button className="primary-button tutorial-next" onClick={() => setTutorialStep((step) => step + 1)}>Next <ChevronRight size={16} /></button> : <button className="primary-button tutorial-next" onClick={finishTutorial}>Get started <Check size={16} /></button>}</div></section></div>}
    </main>
  )
}

export default App
