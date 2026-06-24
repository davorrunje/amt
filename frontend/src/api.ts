export interface Persona {
  id: string;
  name: string;
  description: string;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export async function fetchPersonas(): Promise<Persona[]> {
  const res = await fetch("/personas");
  return res.json();
}

export async function streamChat(
  personaId: string,
  messages: ChatMessage[],
  onToken: (text: string) => void,
): Promise<void> {
  const res = await fetch("/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ persona_id: personaId, messages }),
  });
  const reader = res.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() ?? "";
    for (const part of parts) {
      if (!part.startsWith("data: ")) continue;
      const event = JSON.parse(part.slice("data: ".length));
      if (event.type === "token") onToken(event.text);
      else if (event.type === "error") onToken(`\n[error: ${event.message}]`);
    }
  }
}
