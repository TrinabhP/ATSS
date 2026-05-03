import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Send, MessageSquare, Upload, Loader2, Pencil, Check } from 'lucide-react';

const API_BASE = '';

/**
 * Simple markdown-to-JSX renderer for chat messages.
 * Handles: **bold**, *italic*, `code`, tables, <br>, bullet lists, and line breaks.
 */
function renderMarkdown(text) {
  if (!text) return null;

  // Split into blocks by double newline
  const blocks = text.split(/\n\n+/);

  return blocks.map((block, bi) => {
    const trimmed = block.trim();
    if (!trimmed) return null;

    // Detect markdown table (lines starting with |)
    const lines = trimmed.split('\n');
    if (lines.length >= 2 && lines[0].includes('|') && lines[1].match(/^\|?[\s-:|]+\|/)) {
      return renderTable(lines, bi);
    }

    // Detect bullet list
    if (lines.every(l => l.match(/^\s*[-*]\s/) || !l.trim())) {
      const items = lines.filter(l => l.trim());
      return (
        <ul key={bi} className="chat-md-list">
          {items.map((item, li) => (
            <li key={li}>{renderInline(item.replace(/^\s*[-*]\s+/, ''))}</li>
          ))}
        </ul>
      );
    }

    // Regular paragraph
    return <p key={bi} className="chat-md-para">{renderInline(trimmed)}</p>;
  });
}

function renderTable(lines, key) {
  // Parse header
  const headerCells = lines[0].split('|').map(c => c.trim()).filter(Boolean);
  // Skip separator line (index 1)
  const bodyLines = lines.slice(2);
  const rows = bodyLines
    .filter(l => l.includes('|'))
    .map(l => l.split('|').map(c => c.trim()).filter(Boolean));

  return (
    <div key={key} className="chat-md-table-wrap">
      <table className="chat-md-table">
        <thead>
          <tr>{headerCells.map((h, i) => <th key={i}>{renderInline(h)}</th>)}</tr>
        </thead>
        <tbody>
          {rows.map((row, ri) => (
            <tr key={ri}>{row.map((cell, ci) => <td key={ci}>{renderInline(cell)}</td>)}</tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function renderInline(text) {
  if (!text) return '';
  // Replace <br> tags with newlines
  let s = text.replace(/<br\s*\/?>/gi, '\n');
  // Split by inline patterns and rebuild as JSX
  const parts = [];
  let remaining = s;
  let idx = 0;

  // Process bold, italic, code inline
  const regex = /(\*\*(.+?)\*\*|\*(.+?)\*|`(.+?)`)/g;
  let match;
  let lastIndex = 0;

  while ((match = regex.exec(remaining)) !== null) {
    // Text before match
    if (match.index > lastIndex) {
      parts.push(<span key={idx++}>{remaining.slice(lastIndex, match.index)}</span>);
    }
    if (match[2]) {
      // **bold**
      parts.push(<strong key={idx++}>{match[2]}</strong>);
    } else if (match[3]) {
      // *italic*
      parts.push(<em key={idx++}>{match[3]}</em>);
    } else if (match[4]) {
      // `code`
      parts.push(<code key={idx++} className="chat-md-code">{match[4]}</code>);
    }
    lastIndex = match.index + match[0].length;
  }

  if (lastIndex < remaining.length) {
    parts.push(<span key={idx++}>{remaining.slice(lastIndex)}</span>);
  }

  return parts.length > 0 ? parts : s;
}

export default function ChatPanel({ isOpen, onClose, pipelineState, projectId }) {
  const [sessions, setSessions] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [sessionName, setSessionName] = useState('');
  const [editingName, setEditingName] = useState(false);
  const [editNameValue, setEditNameValue] = useState('');
  const [panelWidth, setPanelWidth] = useState(860);
  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);
  const resizingRef = useRef(false);
  const panelRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    if (isOpen) fetchSessions();
  }, [isOpen]);

  // Resize drag handling
  const handleResizeStart = (e) => {
    e.preventDefault();
    resizingRef.current = true;
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';

    const onMouseMove = (ev) => {
      if (!resizingRef.current) return;
      const newWidth = window.innerWidth - ev.clientX;
      setPanelWidth(Math.max(480, Math.min(newWidth, window.innerWidth - 100)));
    };

    const onMouseUp = () => {
      resizingRef.current = false;
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
      document.removeEventListener('mousemove', onMouseMove);
      document.removeEventListener('mouseup', onMouseUp);
    };

    document.addEventListener('mousemove', onMouseMove);
    document.addEventListener('mouseup', onMouseUp);
  };

  const fetchSessions = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/chat/sessions`);
      const data = await res.json();
      setSessions(data.sessions || []);
    } catch { /* ignore */ }
  };

  const handleUploadPdf = async (file) => {
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const res = await fetch(`${API_BASE}/api/chat/upload`, {
        method: 'POST',
        body: formData,
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        alert(err.detail || 'Failed to upload PDF');
        return;
      }
      const data = await res.json();
      setActiveSessionId(data.session_id);
      setSessionName('New Chat');
      setMessages([]);
      await fetchSessions();
    } catch (err) {
      alert('Upload failed: ' + err.message);
    } finally {
      setUploading(false);
    }
  };

  const handleUploadFromPipeline = async () => {
    if (!pipelineState?.final_recommendation) return;
    setUploading(true);
    try {
      const synthesis = (() => {
        try {
          const parsed = JSON.parse(pipelineState.final_recommendation);
          if (parsed.result || parsed.hypothesis || parsed.steps) return parsed;
        } catch { /* fallback */ }
        return { result: pipelineState.final_recommendation, hypothesis: '', steps: '', literature_citations: '' };
      })();

      const parts = [
        synthesis.result && `RESULT\n${synthesis.result}`,
        synthesis.hypothesis && `HYPOTHESIS\n${synthesis.hypothesis}`,
        synthesis.steps && `STEPS\n${synthesis.steps}`,
        synthesis.literature_citations && `LITERATURE CITATIONS\n${synthesis.literature_citations}`,
        pipelineState.action_items?.length && `ACTION ITEMS\n${pipelineState.action_items.map(a => `• ${a}`).join('\n')}`,
        pipelineState.caveats?.length && `CAVEATS\n${pipelineState.caveats.map(c => `• ${c}`).join('\n')}`,
      ].filter(Boolean).join('\n\n');

      const fullText = `LabOS Research Plan — Project #${projectId}\nConfidence: ${pipelineState.confidence_level || 'N/A'}\n\n${parts}`;

      const res = await fetch(`${API_BASE}/api/chat/from-text`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: fullText, name: 'Research Plan Chat' }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        alert(err.detail || 'Failed to create chat from pipeline results');
        return;
      }
      const data = await res.json();
      setActiveSessionId(data.session_id);
      setSessionName('Research Plan Chat');
      setMessages([]);
      await fetchSessions();
    } catch (err) {
      alert('Failed to create chat: ' + err.message);
    } finally {
      setUploading(false);
    }
  };

  const loadSession = async (sessionId) => {
    setActiveSessionId(sessionId);
    const session = sessions.find(s => s.session_id === sessionId);
    setSessionName(session?.name || 'Chat');
    try {
      const res = await fetch(`${API_BASE}/api/chat/${sessionId}/history`);
      const data = await res.json();
      setMessages(data.messages || []);
    } catch { setMessages([]); }
  };

  const handleSend = async () => {
    if (!input.trim() || !activeSessionId || sending) return;
    const userMsg = input.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: userMsg }]);
    setSending(true);
    try {
      const res = await fetch(`${API_BASE}/api/chat/${activeSessionId}/message`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userMsg }),
      });
      const data = await res.json();
      if (!res.ok) {
        setMessages(prev => [...prev, { role: 'assistant', content: `Error: ${data.detail || 'Failed to get response'}` }]);
        return;
      }
      setMessages(prev => [...prev, { role: 'assistant', content: data.response }]);
      if (data.session_name && data.session_name !== sessionName) {
        setSessionName(data.session_name);
        await fetchSessions();
      }
    } catch (err) {
      setMessages(prev => [...prev, { role: 'assistant', content: `Error: ${err.message}` }]);
    } finally {
      setSending(false);
    }
  };

  const handleRename = async () => {
    if (!editNameValue.trim() || !activeSessionId) return;
    try {
      await fetch(`${API_BASE}/api/chat/${activeSessionId}/rename`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: editNameValue.trim() }),
      });
      setSessionName(editNameValue.trim());
      setEditingName(false);
      await fetchSessions();
    } catch { /* ignore */ }
  };

  const handleDeleteSession = async (sid) => {
    try {
      await fetch(`${API_BASE}/api/chat/${sid}`, { method: 'DELETE' });
      if (activeSessionId === sid) {
        setActiveSessionId(null);
        setMessages([]);
        setSessionName('');
      }
      await fetchSessions();
    } catch { /* ignore */ }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="slide-panel-backdrop"
            onClick={onClose}
          />
          <motion.div
            initial={{ x: '100%' }} animate={{ x: 0 }} exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 25, stiffness: 200 }}
            className="chat-panel"
            ref={panelRef}
            style={{ width: panelWidth }}
          >
            {/* Resize handle */}
            <div className="chat-resize-handle" onMouseDown={handleResizeStart} />
            <div className="chat-panel-header">
              <div className="flex items-center gap-2">
                <MessageSquare size={18} color="var(--accent-primary)" />
                {editingName ? (
                  <div className="flex items-center gap-1">
                    <input
                      className="chat-rename-input"
                      value={editNameValue}
                      onChange={e => setEditNameValue(e.target.value)}
                      onKeyDown={e => e.key === 'Enter' && handleRename()}
                      autoFocus
                    />
                    <button className="btn-icon" onClick={handleRename}><Check size={14} /></button>
                    <button className="btn-icon" onClick={() => setEditingName(false)}><X size={14} /></button>
                  </div>
                ) : (
                  <div className="flex items-center gap-1">
                    <h2 className="font-mono text-sm font-semibold">{sessionName || 'Research Chat'}</h2>
                    {activeSessionId && (
                      <button className="btn-icon" onClick={() => { setEditingName(true); setEditNameValue(sessionName); }} title="Rename">
                        <Pencil size={12} />
                      </button>
                    )}
                  </div>
                )}
              </div>
              <button className="btn-icon" onClick={onClose}><X size={20} /></button>
            </div>

            <div className="chat-panel-body">
              <div className="chat-sessions-sidebar">
                <div className="chat-sessions-actions">
                  {pipelineState?.final_recommendation && (
                    <button className="chat-new-btn" onClick={handleUploadFromPipeline} disabled={uploading}>
                      {uploading ? <Loader2 size={14} className="spin" /> : <MessageSquare size={14} />}
                      Chat with Results
                    </button>
                  )}
                  <button className="chat-upload-btn" onClick={() => fileInputRef.current?.click()} disabled={uploading}>
                    {uploading ? <Loader2 size={14} className="spin" /> : <Upload size={14} />}
                    Upload PDF
                  </button>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".pdf"
                    style={{ display: 'none' }}
                    onChange={e => e.target.files?.[0] && handleUploadPdf(e.target.files[0])}
                  />
                </div>
                <div className="chat-sessions-list">
                  {sessions.map(s => (
                    <div
                      key={s.session_id}
                      className={`chat-session-item ${activeSessionId === s.session_id ? 'active' : ''}`}
                      onClick={() => loadSession(s.session_id)}
                    >
                      <span className="chat-session-name">{s.name || 'Untitled Chat'}</span>
                      <button
                        className="chat-session-delete"
                        onClick={e => { e.stopPropagation(); handleDeleteSession(s.session_id); }}
                        title="Delete"
                      >
                        <X size={12} />
                      </button>
                    </div>
                  ))}
                  {sessions.length === 0 && (
                    <p className="text-xs text-muted" style={{ padding: '8px' }}>No chats yet. Upload a PDF or chat with your results.</p>
                  )}
                </div>
              </div>

              <div className="chat-messages-area">
                {!activeSessionId ? (
                  <div className="chat-empty-state">
                    <MessageSquare size={48} color="var(--text-secondary)" strokeWidth={1} />
                    <p className="text-muted text-sm mt-4">Select a chat or start a new one</p>
                    <p className="text-muted text-xs mt-1">Upload a PDF or use your pipeline results as context</p>
                  </div>
                ) : (
                  <>
                    <div className="chat-messages">
                      {messages.length === 0 && (
                        <div className="chat-empty-state">
                          <p className="text-muted text-sm">Ask a question about your research document</p>
                        </div>
                      )}
                      {messages.map((msg, i) => (
                        <div key={i} className={`chat-message ${msg.role}`}>
                          <div className="chat-message-label">{msg.role === 'user' ? 'You' : 'LabOS'}</div>
                          <div className="chat-message-content">{msg.role === 'assistant' ? renderMarkdown(msg.content) : msg.content}</div>
                        </div>
                      ))}
                      {sending && (
                        <div className="chat-message assistant">
                          <div className="chat-message-label">LabOS</div>
                          <div className="chat-message-content chat-typing">
                            <span></span><span></span><span></span>
                          </div>
                        </div>
                      )}
                      <div ref={messagesEndRef} />
                    </div>
                    <div className="chat-input-area">
                      <textarea
                        className="chat-input"
                        value={input}
                        onChange={e => setInput(e.target.value)}
                        onKeyDown={handleKeyDown}
                        placeholder="Ask about your research..."
                        rows={1}
                        disabled={sending}
                      />
                      <button className="chat-send-btn" onClick={handleSend} disabled={!input.trim() || sending}>
                        {sending ? <Loader2 size={16} className="spin" /> : <Send size={16} />}
                      </button>
                    </div>
                  </>
                )}
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
