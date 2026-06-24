import { useEffect, useState } from "react";
import type { ChatMessage, Persona } from "./api";
import { fetchPersonas, streamChat } from "./api";

export default function App() {
  const [personas, setPersonas] = useState<Persona[]>([]);
  const [personaId, setPersonaId] = useState("student");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    fetchPersonas().then(setPersonas);
  }, []);

  async function send() {
    if (!input.trim() || busy) return;
    const next: ChatMessage[] = [...messages, { role: "user", content: input }];
    setMessages([...next, { role: "assistant", content: "" }]);
    setInput("");
    setBusy(true);
    await streamChat(personaId, next, (text) => {
      setMessages((cur) => {
        const copy = [...cur];
        copy[copy.length - 1] = {
          role: "assistant",
          content: copy[copy.length - 1].content + text,
        };
        return copy;
      });
    });
    setBusy(false);
  }

  return (
    <main style={{ maxWidth: 640, margin: "2rem auto", fontFamily: "sans-serif" }}>
      <h1>Talk to Alan Turing</h1>
      <label>
        Audience:{" "}
        <select value={personaId} onChange={(e) => setPersonaId(e.target.value)}>
          {personas.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </select>
      </label>
      <div style={{ margin: "1rem 0", minHeight: 200 }}>
        {messages.map((m, i) => (
          <p key={i}>
            <strong>{m.role === "user" ? "You" : "Turing"}:</strong> {m.content}
          </p>
        ))}
      </div>
      <input
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && send()}
        placeholder="Ask Turing something…"
        style={{ width: "80%" }}
      />
      <button onClick={send} disabled={busy}>
        Send
      </button>
    </main>
  );
}
