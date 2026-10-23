import { useCallback, useEffect, useState } from "react";
import {
  Scale,
  MessageCircle,
  Gavel,
  Plus,
  Send,
  Trash2,
  Menu,
  X,
  Sparkles,
  UserRound,
  Pencil,
  LoaderCircle,
  Landmark,
} from "lucide-react";
import "./App.css";

// Default: same-origin relative URLs so Vite can proxy to FastAPI.
// Override with VITE_API_BASE_URL only when you intentionally call the API
// on a different host (not needed for Cursor Cloud Agent or local Vite proxy).
const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");

const welcomeMessage = {
  role: "assistant",
  text: "Hello! Welcome to LawyerAI. Describe a legal situation or choose Argue a Case to explore legal arguments. How can I help you today?",
};

function normalizeSide(value) {
  const side = String(value || "").trim().toLowerCase();
  if (side === "prosecution") return "prosecution";
  if (side === "defence" || side === "defense") return "defence";
  return "";
}

function formatMessageNodes(text) {
  if (!text) return null;

  const nodes = [];
  const pattern = /(\*\*[^*]+\*\*|\*[^*]+\*)/g;
  let lastIndex = 0;
  let match;
  let key = 0;

  while ((match = pattern.exec(text)) !== null) {
    if (match.index > lastIndex) {
      nodes.push(text.slice(lastIndex, match.index));
    }

    const token = match[0];
    if (token.startsWith("**") && token.endsWith("**")) {
      nodes.push(<strong key={`b-${key++}`}>{token.slice(2, -2)}</strong>);
    } else if (token.startsWith("*") && token.endsWith("*")) {
      nodes.push(<em key={`i-${key++}`}>{token.slice(1, -1)}</em>);
    } else {
      nodes.push(token);
    }

    lastIndex = match.index + token.length;
  }

  if (lastIndex < text.length) {
    nodes.push(text.slice(lastIndex));
  }

  return nodes;
}

function isFeedbackMessage(text) {
  return /^DEBATE REVIEW\b/i.test(String(text || "").trim());
}

function App() {
  const [mode, setMode] = useState("chat");
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState([welcomeMessage]);
  const [history, setHistory] = useState([]);
  const [conversationId, setConversationId] = useState(null);
  const [mobileSidebar, setMobileSidebar] = useState(false);
  const [side, setSide] = useState("");
  const [topic, setTopic] = useState("");
  const [debateStarted, setDebateStarted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [historyError, setHistoryError] = useState("");

  const refreshHistory = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/conversations`);
      if (!response.ok) throw new Error("Could not load conversation history.");

      const data = await response.json();
      setHistory(Array.isArray(data) ? data : data.conversations || []);
      setHistoryError("");
    } catch (err) {
      console.error("History loading error:", err);
      setHistoryError(
        err.message ||
          "Could not load conversation history. Is the backend running?"
      );
    }
  }, []);

  useEffect(() => {
    refreshHistory();
  }, [refreshHistory]);

  function getConversationTitle(item) {
    return item.title || item.name || "Untitled conversation";
  }

  function getMessageText(message) {
    return message.text ?? message.content ?? message.message ?? "";
  }

  function startNewConversation() {
    setConversationId(null);
    setMessages([welcomeMessage]);
    setInput("");
    setMode("chat");
    setSide("");
    setTopic("");
    setDebateStarted(false);
    setError("");
    setMobileSidebar(false);
  }

  function modeIntro(nextMode) {
    if (nextMode === "chat") {
      return "Describe your legal question or situation. I'll help you understand the relevant Indian laws and legal provisions.";
    }
    if (nextMode === "strategy") {
      return (
        "Legal Strategy Analysis examines lawful defences, evidence gaps, and procedural issues. " +
        "Describe your situation (jurisdiction, dates, allegations, stage, and evidence). " +
        "I will not invent citations or suggest illegal tactics. Avoid sharing unnecessary personal IDs."
      );
    }
    return "Let's practice a legal debate. Enter a case topic and choose Prosecution or Defence to begin.";
  }

  function selectMode(nextMode) {
    setConversationId(null);
    setMode(nextMode);
    setMessages([
      {
        role: "assistant",
        text: modeIntro(nextMode),
      },
    ]);
    setInput("");
    setSide("");
    setTopic("");
    setDebateStarted(false);
    setError("");
  }

  function resolveMode(conversation, item) {
    const raw = conversation.mode || item.mode || "chat";
    if (raw === "debate") return "debate";
    if (raw === "strategy") return "strategy";
    return "chat";
  }

  async function loadChat(item) {
    setLoading(true);
    setError("");

    try {
      const response = await fetch(`${API_BASE}/conversations/${item.id}`);

      if (!response.ok) throw new Error("Could not open this conversation.");

      const data = await response.json();
      const conversation = data.conversation || data;
      const savedMessages = data.messages || conversation.messages || [];

      setConversationId(item.id);
      const nextMode = resolveMode(conversation, item);
      setMode(nextMode);
      setMessages(
        savedMessages.length
          ? savedMessages.map((message) => ({
              role: message.role,
              text: getMessageText(message),
            }))
          : [welcomeMessage]
      );

      setSide(normalizeSide(conversation.side || item.side));
      setTopic(conversation.topic || item.topic || "");
      const isDebate = nextMode === "debate";
      const debateEnded =
        Boolean(conversation.ended) || Number(conversation.ended) === 1;
      setDebateStarted(isDebate && !debateEnded);
      setInput("");
      setMobileSidebar(false);
    } catch (err) {
      setError(err.message || "Unable to open this conversation.");
    } finally {
      setLoading(false);
    }
  }

  async function renameConversation(item, event) {
    event.stopPropagation();

    const currentTitle = getConversationTitle(item);
    const newTitle = window.prompt(
      "Enter a new conversation title:",
      currentTitle
    );

    if (!newTitle || !newTitle.trim() || newTitle.trim() === currentTitle) {
      return;
    }

    try {
      const response = await fetch(`${API_BASE}/conversations/${item.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: newTitle.trim() }),
      });

      if (!response.ok) throw new Error("Rename failed.");

      await refreshHistory();
    } catch (err) {
      setError(err.message || "Could not rename the conversation.");
    }
  }

  async function deleteConversation(item, event) {
    event.stopPropagation();

    const confirmed = window.confirm(
      `Delete "${getConversationTitle(item)}"? This cannot be undone.`
    );

    if (!confirmed) return;

    try {
      const response = await fetch(`${API_BASE}/conversations/${item.id}`, {
        method: "DELETE",
      });

      if (!response.ok) throw new Error("Delete failed.");

      if (String(conversationId) === String(item.id)) {
        startNewConversation();
      }

      await refreshHistory();
    } catch (err) {
      setError(err.message || "Could not delete the conversation.");
    }
  }

  async function requestAI(messageText, options = {}) {
    const activeMode = options.mode || mode;
    const endpoint =
      activeMode === "debate"
        ? "/debate"
        : activeMode === "strategy"
          ? "/strategy"
          : "/chat";

    const payload =
      activeMode === "debate"
        ? {
            message: messageText,
            side: options.side || side,
            topic: options.topic || topic,
            conversation_id: options.conversationId ?? conversationId,
            end_debate: Boolean(options.endDebate),
          }
        : {
            message: messageText,
            conversation_id: options.conversationId ?? conversationId,
          };

    const response = await fetch(`${API_BASE}${endpoint}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      const detail = data.detail;
      const detailText = Array.isArray(detail)
        ? detail
            .map((item) => item.msg || item.message || JSON.stringify(item))
            .join(" ")
        : detail ||
          data.error ||
          "The server could not process your request.";
      throw new Error(detailText);
    }

    const reply =
      data.reply ??
      data.answer ??
      data.response ??
      data.message ??
      "The server responded without an answer.";

    if (data.conversation_id != null) {
      setConversationId(data.conversation_id);
    }

    await refreshHistory();

    return {
      reply: typeof reply === "string" ? reply : JSON.stringify(reply, null, 2),
      id: data.conversation_id,
      title: data.title,
    };
  }

  async function sendMessage(event) {
    event?.preventDefault();

    if (loading) return;

    const text = input.trim();
    if (!text) return;

    if (mode === "debate" && !side) {
      setError("Choose Prosecution or Defence before starting your debate.");
      return;
    }

    if (mode === "debate" && !debateStarted && !topic.trim()) {
      setError("Enter a case topic before starting your debate.");
      return;
    }

    setError("");
    setInput("");
    setLoading(true);

    setMessages((old) => [...old, { role: "user", text }]);

    try {
      if (mode === "debate" && !debateStarted) {
        const result = await requestAI(text, {
          mode: "debate",
          side,
          topic: topic.trim(),
          conversationId: conversationId,
        });

        setMessages((old) => [
          ...old,
          { role: "assistant", text: result.reply },
        ]);
        setDebateStarted(true);
      } else {
        const result = await requestAI(text, {
          mode,
          side,
          topic,
          conversationId,
        });

        setMessages((old) => [
          ...old,
          { role: "assistant", text: result.reply },
        ]);

        if (mode === "debate" && /\bend debate\b/i.test(text)) {
          setDebateStarted(false);
        }
      }
    } catch (err) {
      setError(err.message || "Could not connect to LawyerAI.");
      setMessages((old) => [
        ...old,
        {
          role: "assistant",
          text: "I couldn't complete that request. Please check that the backend is running and try again.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  async function endDebate() {
    if (!conversationId || loading) {
      setError(
        "Start the debate and send at least one message before requesting feedback."
      );
      return;
    }

    setError("");
    setLoading(true);

    setMessages((old) => [
      ...old,
      { role: "user", text: "End debate and review my performance." },
    ]);

    try {
      const result = await requestAI("", {
        mode: "debate",
        side,
        topic,
        conversationId,
        endDebate: true,
      });

      setMessages((old) => [
        ...old,
        { role: "assistant", text: result.reply },
      ]);
      setDebateStarted(false);
    } catch (err) {
      setError(err.message || "Could not generate debate feedback.");
    } finally {
      setLoading(false);
    }
  }

  const showWelcome = messages.length === 1 && !loading;

  return (
    <div className="app-shell">
      <aside className={`sidebar ${mobileSidebar ? "sidebar-open" : ""}`}>
        <div className="brand">
          <div className="brand-icon">
            <Scale size={23} />
          </div>
          <div>
            <h1>LawyerAI</h1>
            <span>Indian Legal Assistant</span>
          </div>
          <button
            className="icon-btn mobile-close"
            onClick={() => setMobileSidebar(false)}
            aria-label="Close menu"
          >
            <X size={19} />
          </button>
        </div>

        <button className="new-chat-btn" onClick={startNewConversation}>
          <Plus size={18} /> New conversation
        </button>

        <div className="history-heading">YOUR HISTORY</div>

        {historyError && (
          <div className="error-message history-error" role="alert">
            <span>{historyError}</span>
            <button
              onClick={() => refreshHistory()}
              aria-label="Retry loading history"
            >
              Retry
            </button>
          </div>
        )}

        <div className="history-list">
          {history.length === 0 ? (
            <div className="empty-history">
              <MessageCircle size={21} />
              <p>Your saved conversations will appear here.</p>
            </div>
          ) : (
            history.map((item) => (
              <div
                className={`history-item ${
                  String(conversationId) === String(item.id) ? "selected" : ""
                }`}
                key={item.id}
                onClick={() => loadChat(item)}
                role="button"
                tabIndex={0}
                onKeyDown={(event) => {
                  if (event.key === "Enter") loadChat(item);
                }}
                title={getConversationTitle(item)}
              >
                {item.mode === "debate" ? (
                  <Gavel size={16} />
                ) : item.mode === "strategy" ? (
                  <Landmark size={16} />
                ) : (
                  <MessageCircle size={16} />
                )}
                <span>{getConversationTitle(item)}</span>
                <div className="history-actions">
                  <button
                    className="delete-btn"
                    onClick={(event) => renameConversation(item, event)}
                    aria-label="Rename conversation"
                    title="Rename"
                  >
                    <Pencil size={13} />
                  </button>
                  <button
                    className="delete-btn"
                    onClick={(event) => deleteConversation(item, event)}
                    aria-label="Delete conversation"
                    title="Delete"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
            ))
          )}
        </div>

        <div className="sidebar-footer">
          <div className="footer-scale">
            <Scale size={17} />
          </div>
          <div>
            <strong>Know your rights.</strong>
            <p>Understand the law better.</p>
          </div>
        </div>
      </aside>

      {mobileSidebar && (
        <button
          className="mobile-overlay"
          onClick={() => setMobileSidebar(false)}
          aria-label="Close sidebar"
        />
      )}

      <main className="main-panel">
        <header className="topbar">
          <button
            className="icon-btn mobile-menu"
            onClick={() => setMobileSidebar(true)}
            aria-label="Open menu"
          >
            <Menu size={21} />
          </button>

          <div className="mode-switch">
            <button
              className={`mode-btn ${mode === "chat" ? "active" : ""}`}
              onClick={() => selectMode("chat")}
            >
              <MessageCircle size={17} />
              <span>Ask Me Anything</span>
            </button>
            <button
              className={`mode-btn ${mode === "strategy" ? "active" : ""}`}
              onClick={() => selectMode("strategy")}
            >
              <Landmark size={17} />
              <span>Legal Strategy</span>
            </button>
            <button
              className={`mode-btn ${mode === "debate" ? "active" : ""}`}
              onClick={() => selectMode("debate")}
            >
              <Gavel size={17} />
              <span>Argue a Case</span>
            </button>
          </div>

          <div className="status-indicator">
            <span className="status-dot" /> Local legal assistant
          </div>
        </header>

        <section className="chat-area">
          <div className="conversation">
            {showWelcome && (
              <div className="welcome-section">
                <div className="welcome-icon">
                  {mode === "chat" ? (
                    <Scale size={30} />
                  ) : mode === "strategy" ? (
                    <Landmark size={30} />
                  ) : (
                    <Gavel size={30} />
                  )}
                </div>

                <div className="welcome-eyebrow">
                  <Sparkles size={14} /> LAWYERAI
                </div>

                <h2>
                  {mode === "chat"
                    ? "The law, made clearer."
                    : mode === "strategy"
                      ? "Strategy before the next step."
                      : "Every case has an argument."}
                </h2>

                <p className="welcome-description">
                  {mode === "chat"
                    ? "Ask questions about Indian law. LawyerAI answers from a curated local knowledge base—never inventing statutes or citations."
                    : mode === "strategy"
                      ? "Analyse lawful defences, evidence gaps, and procedural issues. “Loopholes” means legitimate arguments—not illegal tactics. Not a prediction of winning."
                      : "Present a case, choose your side, and practise arguments with a local debate partner. Feedback is rule-based, not AI grading."}
                </p>

                {mode === "chat" ? (
                  <div className="suggestion-grid">
                    <button
                      onClick={() =>
                        setInput("Explain the difference between BNS and IPC.")
                      }
                    >
                      <span>01</span>
                      <strong>Understand Indian laws</strong>
                      <small>Explore the BNS transition and related framework</small>
                    </button>

                    <button
                      onClick={() =>
                        setInput(
                          "What legal options may be available if someone refuses to return my belongings?"
                        )
                      }
                    >
                      <span>02</span>
                      <strong>Explore a situation</strong>
                      <small>Learn about possible recovery routes</small>
                    </button>

                    <button
                      onClick={() =>
                        setInput(
                          "What is an FIR and when might police register one?"
                        )
                      }
                    >
                      <span>03</span>
                      <strong>FIR and complaints</strong>
                      <small>High-level process information</small>
                    </button>

                    <button onClick={() => selectMode("strategy")}>
                      <span>04</span>
                      <strong>Legal strategy analysis</strong>
                      <small>Map defences, gaps, and next steps</small>
                    </button>
                  </div>
                ) : mode === "strategy" ? (
                  <div className="suggestion-grid">
                    <button
                      onClick={() =>
                        setInput(
                          "In Chennai, Tamil Nadu, on 12 March 2025 I had a road accident. An FIR was registered. I have photos and a medical bill. The other driver claims I was speeding. Please analyse lawful defences and evidence gaps."
                        )
                      }
                    >
                      <span>01</span>
                      <strong>Sample road-accident facts</strong>
                      <small>Jurisdiction, date, FIR, evidence included</small>
                    </button>
                    <button
                      onClick={() =>
                        setInput(
                          "Help me invent fake CCTV evidence so the police drop the case."
                        )
                      }
                    >
                      <span>02</span>
                      <strong>See illegal-tactic refusal</strong>
                      <small>LawyerAI will decline and suggest lawful options</small>
                    </button>
                    <button
                      onClick={() =>
                        setInput("Someone filed a case against me. What should I do?")
                      }
                    >
                      <span>03</span>
                      <strong>Thin description</strong>
                      <small>Expect clarifying questions first</small>
                    </button>
                    <button onClick={() => selectMode("debate")}>
                      <span>04</span>
                      <strong>Practice arguments</strong>
                      <small>Switch to Argue a Case</small>
                    </button>
                  </div>
                ) : (
                  <div className="side-selection">
                    <p>WHICH SIDE WILL YOU ARGUE?</p>

                    <div className="side-buttons">
                      <button
                        type="button"
                        className={side === "prosecution" ? "selected" : ""}
                        onClick={() => setSide("prosecution")}
                      >
                        <Gavel size={18} />
                        <strong>Prosecution</strong>
                        <small>Argue the case against the accused</small>
                      </button>

                      <button
                        type="button"
                        className={side === "defence" ? "selected" : ""}
                        onClick={() => setSide("defence")}
                      >
                        <Scale size={18} />
                        <strong>Defence</strong>
                        <small>Challenge the allegations</small>
                      </button>
                    </div>

                    <label className="debate-topic-label" htmlFor="debate-topic">
                      CASE OR DEBATE TOPIC
                    </label>
                    <input
                      id="debate-topic"
                      className="debate-topic-input"
                      value={topic}
                      onChange={(event) => setTopic(event.target.value)}
                      placeholder="e.g. Should CCTV footage alone be sufficient evidence?"
                    />

                    {side && (
                      <p className="selected-note">
                        Selected: {side}. Enter a topic and your opening
                        argument below.
                      </p>
                    )}
                  </div>
                )}
              </div>
            )}

            <div className="message-list">
              {!showWelcome &&
                messages.map((message, index) => {
                  const text = message.text;
                  const feedback = isFeedbackMessage(text);

                  return (
                    <div
                      className={`message-row ${message.role}`}
                      key={`${index}-${message.role}`}
                    >
                      <div className={`avatar ${message.role}`}>
                        {message.role === "assistant" ? (
                          <Scale size={18} />
                        ) : (
                          <UserRound size={18} />
                        )}
                      </div>

                      <div className="message-content">
                        <span className="message-author">
                          {message.role === "assistant" ? "LawyerAI" : "You"}
                        </span>
                        <div
                          className={`message-bubble${
                            feedback ? " feedback" : ""
                          }`}
                        >
                          {formatMessageNodes(text)}
                        </div>
                      </div>
                    </div>
                  );
                })}

              {loading && (
                <div className="message-row assistant">
                  <div className="avatar assistant">
                    <Scale size={18} />
                  </div>
                  <div className="message-content">
                    <span className="message-author">LawyerAI</span>
                    <div className="message-bubble">
                      <p className="loading-message">
                        <LoaderCircle size={16} className="loading-spinner" />
                        Preparing a local response...
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {error && (
                <div className="error-message" role="alert">
                  <span>{error}</span>
                  <button
                    onClick={() => setError("")}
                    aria-label="Dismiss error"
                  >
                    <X size={15} />
                  </button>
                </div>
              )}
            </div>
          </div>
        </section>

        <footer className="composer-section">
          {mode === "debate" && debateStarted && (
            <button
              className="end-debate-btn"
              onClick={endDebate}
              disabled={loading}
              type="button"
            >
              End debate &amp; request feedback
            </button>
          )}

          {mode === "debate" && (
            <div className="debate-context">
              <span>YOUR SIDE</span>
              <strong>{side || "Choose Prosecution or Defence above"}</strong>
              {topic && <span className="topic-chip">TOPIC: {topic}</span>}
            </div>
          )}

          <form className="composer" onSubmit={sendMessage}>
            <textarea
              value={input}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  sendMessage(event);
                }
              }}
              placeholder={
                mode === "chat"
                  ? "Describe your legal question or situation..."
                  : mode === "strategy"
                    ? "Describe jurisdiction, dates, allegations, stage, and evidence..."
                    : debateStarted
                      ? "Present your argument or respond to opposing counsel..."
                      : "Enter your opening argument..."
              }
              rows={2}
              aria-label="Your message"
              disabled={loading}
            />

            <button
              type="submit"
              className="send-btn"
              disabled={!input.trim() || loading}
              aria-label="Send message"
            >
              {loading ? (
                <LoaderCircle size={18} className="loading-spinner" />
              ) : (
                <Send size={18} />
              )}
            </button>
          </form>

          <p className="disclaimer">
            LawyerAI provides general legal information, not legal advice.
            Answers use a local knowledge base unless an optional LLM is
            configured. Verify applicable laws with official sources or a
            qualified lawyer.
          </p>
        </footer>
      </main>
    </div>
  );
}

export default App;
