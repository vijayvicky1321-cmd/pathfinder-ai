import { useRef, useState } from "react";

const API_URL = `${import.meta.env.VITE_API_BASE_URL || "http://localhost:8010"}/api/chat`;

function makeChat() {
  return { id: crypto.randomUUID(), title: "New chat", messages: [] };
}

export default function App() {
  const [chats, setChats] = useState([makeChat()]);
  const [activeId, setActiveId] = useState(chats[0].id);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const bottomRef = useRef(null);

  const activeChat = chats.find((c) => c.id === activeId);
  const messages = activeChat.messages;

  function updateActiveChat(updater) {
    setChats((prev) => prev.map((c) => (c.id === activeId ? updater(c) : c)));
  }

  function newChat() {
    const chat = makeChat();
    setChats((prev) => [chat, ...prev]);
    setActiveId(chat.id);
    setError(null);
  }

  async function sendText(text) {
    if (!text || loading) return;

    const nextMessages = [...messages, { role: "user", content: text }];
    const isFirstMessage = messages.length === 0;
    updateActiveChat((c) => ({
      ...c,
      messages: nextMessages,
      title: isFirstMessage ? text.slice(0, 40) : c.title,
    }));
    setInput("");
    setError(null);
    setLoading(true);

    try {
      const res = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: nextMessages.map((m) => ({
            role: m.role,
            content: m.content,
            type: m.type,
          })),
        }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `Request failed (${res.status})`);
      }
      const data = await res.json();
      updateActiveChat((c) => ({
        ...c,
        messages: [
          ...nextMessages,
          {
            role: "assistant",
            content: data.text,
            questions: data.questions || [],
            type: data.type,
          },
        ],
      }));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
      setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }), 50);
    }
  }

  function sendMessage() {
    sendText(input.trim());
  }

  function pickOption(questionText, option) {
    sendText(`${questionText} ${option}`);
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }

  return (
    <div className="layout">
      <aside className="sidebar">
        <button className="new-chat-button" onClick={newChat}>
          + New chat
        </button>
        <div className="chat-list">
          {chats.map((c) => (
            <div
              key={c.id}
              className={`chat-list-item ${c.id === activeId ? "active" : ""}`}
              onClick={() => setActiveId(c.id)}
            >
              {c.title}
            </div>
          ))}
        </div>
      </aside>

      <div className="main">
        <header className="topbar">
          <div className="app-name-block">
            <span className="app-name">Pathfinder AI</span>
            <span className="app-credit">Developed by Vijay</span>
          </div>
        </header>

        <div className="chat">
          {messages.length === 0 && (
            <div className="empty">Describe a problem to get started.</div>
          )}
          {messages.map((m, i) => {
            const isLast = i === messages.length - 1;
            return (
              <div key={i} className={`message-row ${m.role}`}>
                <div className={`message ${m.role}`}>
                  <div className="content">{m.content}</div>
                  {isLast && !loading && m.questions?.length > 0 && (
                    <div className="questions">
                      {m.questions.map((q, qi) => (
                        <div key={qi} className="question-block">
                          <div className="question-text">{q.question}</div>
                          <div className="option-row">
                            {q.options.map((opt, oi) => (
                              <button
                                key={oi}
                                className="option-button"
                                onClick={() => pickOption(q.question, opt)}
                              >
                                {opt}
                              </button>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
          {loading && (
            <div className="message-row assistant">
              <div className="message assistant">
                <span className="thinking-dots">
                  Thinking<span>.</span><span>.</span><span>.</span>
                </span>
              </div>
            </div>
          )}
          {error && (
            <div className="message-row assistant">
              <div className="message error">Error: {error}</div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        <div className="input-bar-wrap">
          <div className="input-bar">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Describe your problem..."
              rows={1}
            />
            <button onClick={sendMessage} disabled={loading || !input.trim()}>
              Send
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
