import { useEffect, useRef, useState } from "react";

import { explainChat } from "../api/client.js";

export default function ChatWidget({ ticker }) {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState([]);
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const lastTickerRef = useRef(null);
  const historyRef = useRef(null);

  useEffect(() => {
    if (!ticker || lastTickerRef.current === ticker) return;
    lastTickerRef.current = ticker;
    setMessages([]);
    sendMessage(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ticker]);

  useEffect(() => {
    if (historyRef.current) {
      historyRef.current.scrollTop = historyRef.current.scrollHeight;
    }
  }, [messages, loading]);

  async function sendMessage(userQuestion) {
    if (userQuestion) {
      setMessages((prev) => [...prev, { role: "user", text: userQuestion }]);
    }
    setLoading(true);
    try {
      const data = await explainChat(ticker, userQuestion);
      setMessages((prev) => [...prev, { role: "ai", text: data.answer }]);
    } catch (err) {
      const text =
        err.response?.status === 404
          ? "Run an analysis for this ticker first."
          : err.response?.data?.detail || "Something went wrong. Please try again.";
      setMessages((prev) => [...prev, { role: "ai", text, isError: true }]);
    } finally {
      setLoading(false);
    }
  }

  function handleSubmit(e) {
    e.preventDefault();
    const trimmed = question.trim();
    if (!trimmed || loading) return;
    setQuestion("");
    sendMessage(trimmed);
  }

  if (!ticker) return null;

  if (!open) {
    return (
      <button type="button" className="chat-toggle" onClick={() => setOpen(true)} aria-label="Open chat">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z" />
        </svg>
      </button>
    );
  }

  return (
    <div className="chat-panel">
      <div className="chat-header">
        <span>Ask about {ticker}</span>
        <button type="button" onClick={() => setOpen(false)}>
          &times;
        </button>
      </div>
      <div className="chat-history" ref={historyRef}>
        {messages.map((m, i) => (
          <div key={i} className={`chat-message chat-${m.role}${m.isError ? " chat-error" : ""}`}>
            {m.text}
          </div>
        ))}
        {loading && <div className="chat-message chat-ai chat-loading">Thinking...</div>}
      </div>
      <form className="chat-input-row" onSubmit={handleSubmit}>
        <input
          type="text"
          placeholder="Ask a question..."
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          disabled={loading}
        />
        <button type="submit" className="btn-primary" disabled={loading || !question.trim()}>
          Send
        </button>
      </form>
    </div>
  );
}
