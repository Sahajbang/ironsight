import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useRef, useState } from "react";
import { useLocation } from "react-router-dom";

import { useAssistantStatus, useSendMessage, type AssistantReply } from "../api/client";
import { Icon } from "../design";
import { LoaderGlyph } from "../guide/LoaderVehicle";
import { useApp, useGuide } from "../state/store";
import "./chat.css";

interface Turn {
  role: "user" | "assistant";
  text: string;
  reply?: AssistantReply;
}

const STARTERS = [
  "How do I report a safety issue?",
  "How long until I finish this task?",
  "Why is my idle time high?",
  "Show me trenching training",
];

export function ChatPanel() {
  const { operatorId, chatOpen, setChatOpen } = useApp();
  const { enabled, setEnabled, start } = useGuide();
  const location = useLocation();
  const send = useSendMessage();
  const { data: status } = useAssistantStatus();
  const [turns, setTurns] = useState<Turn[]>([]);
  const [draft, setDraft] = useState("");
  const scroller = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scroller.current?.scrollTo({ top: scroller.current.scrollHeight, behavior: "smooth" });
  }, [turns, send.isPending]);

  async function submit(text: string) {
    const message = text.trim();
    if (!message || send.isPending) return;
    setDraft("");
    setTurns((t) => [...t, { role: "user", text: message }]);
    try {
      const reply = await send.mutateAsync({
        message,
        operator_id: operatorId,
        route: location.pathname,
      });
      setTurns((t) => [...t, { role: "assistant", text: reply.reply, reply }]);
      if (reply.guide_actions.length) start(reply.guide_actions);
    } catch (err) {
      setTurns((t) => [
        ...t,
        { role: "assistant", text: `I could not reach the assistant. ${(err as Error).message}` },
      ]);
    }
  }

  return (
    <>
      <div className="chat-dock">
        {/* The guide switch: a loader in a circle. Off by default so nothing moves on screen
            unless the operator asks for it. */}
        <button
          className="guide-toggle"
          data-on={enabled}
          onClick={() => setEnabled(!enabled)}
          aria-pressed={enabled}
          aria-label={enabled ? "Turn AI guide pointer off" : "Turn AI guide pointer on"}
          title={enabled ? "AI guide pointer: ON — the loader will deliver the pointer" : "AI guide pointer: OFF"}
        >
          <LoaderGlyph size={24} />
          <span className="guide-toggle__lamp" />
        </button>

        <button
          className="chat-launch"
          data-open={chatOpen}
          onClick={() => setChatOpen(!chatOpen)}
          aria-label={chatOpen ? "Close assistant" : "Open assistant"}
          data-guide-id="chat-panel"
        >
          <Icon name={chatOpen ? "close" : "chat"} size={21} />
        </button>
      </div>

      <AnimatePresence>
        {chatOpen && (
          <motion.aside
            className="chat"
            initial={{ opacity: 0, y: 18, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 12, scale: 0.98 }}
            transition={{ duration: 0.22, ease: [0.22, 0.61, 0.36, 1] }}
            aria-label="AI assistant"
          >
            <header className="chat__head">
              <div className="col" style={{ gap: 1 }}>
                <strong className="chat__title">Ironsight Assistant</strong>
                <span className="chat__sub">
                  {status?.llm_configured ? "Nemotron · tool-calling" : "Offline mode · rule-based"}
                </span>
              </div>
              <span className={`chat__state ${status?.llm_configured ? "is-live" : ""}`}>
                {status?.llm_configured ? "Live" : "Local"}
              </span>
            </header>

            <div className="chat__body" ref={scroller}>
              {turns.length === 0 && (
                <div className="chat__intro">
                  <p className="chat__introtext">
                    Ask about your task, safety state or training. Turn the loader switch on and I will
                    drive the pointer to the right control instead of just describing it.
                  </p>
                  <div className="chat__starters">
                    {STARTERS.map((s) => (
                      <button key={s} className="chat__starter" onClick={() => submit(s)}>
                        {s}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {turns.map((turn, i) => (
                <div key={i} className={`bubble bubble--${turn.role}`}>
                  <p>{turn.text}</p>
                  {turn.reply && turn.reply.sources.length > 0 && (
                    <div className="bubble__sources">
                      {turn.reply.sources.slice(0, 3).map((s) => (
                        <span key={s.id} className="bubble__source">
                          <Icon name="file" size={12} />
                          {s.title}
                        </span>
                      ))}
                    </div>
                  )}
                  {turn.reply?.guide_actions.length ? (
                    <button
                      className="bubble__replay"
                      onClick={() => (enabled ? start(turn.reply!.guide_actions) : setEnabled(true))}
                    >
                      <LoaderGlyph size={15} />
                      {enabled ? "Show me again" : "Turn on the guide to be shown"}
                    </button>
                  ) : null}
                </div>
              ))}

              {send.isPending && (
                <div className="bubble bubble--assistant">
                  <span className="typing">
                    <i />
                    <i />
                    <i />
                  </span>
                </div>
              )}
            </div>

            <form
              className="chat__composer"
              onSubmit={(e) => {
                e.preventDefault();
                submit(draft);
              }}
            >
              <div className="input">
                <Icon name="chat" size={16} />
                <input
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  placeholder="Ask about your task, safety or training…"
                  aria-label="Message the assistant"
                />
              </div>
              <button className="chat__send" type="submit" disabled={!draft.trim() || send.isPending} aria-label="Send">
                <Icon name="send" size={17} />
              </button>
            </form>
          </motion.aside>
        )}
      </AnimatePresence>
    </>
  );
}
