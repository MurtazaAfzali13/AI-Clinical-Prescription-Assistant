"use client";

import { useState } from "react";
import { AlertTriangle, Loader2, MessageCircle, Send, ShieldCheck, User } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { ApiError, chatApi, type ChatTurn } from "@/lib/api/client";

const EXAMPLE_PROMPTS = [
  "Show me patient REC-0001",
  "Find Ahmad Karimi, father's name Mohammad",
  "Refer patient REC-0001 to colleague@watanhospital.af for a specialist opinion",
];

export function PatientChatWidget() {
  const [history, setHistory] = useState<ChatTurn[]>([]);
  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function sendMessage(message: string) {
    if (!message.trim() || isSending) return;

    setError(null);
    const nextHistory: ChatTurn[] = [...history, { role: "user", content: message }];
    setHistory(nextHistory);
    setInput("");
    setIsSending(true);

    try {
      const result = await chatApi.sendMessage({ message, history });
      setHistory([...nextHistory, { role: "assistant", content: result.reply }]);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
    } finally {
      setIsSending(false);
    }
  }

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    sendMessage(input);
  }

  return (
    <Card className="flex h-[70vh] flex-col">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <MessageCircle className="h-4 w-4 text-clinic-600" />
          Patient Records Assistant
        </CardTitle>
        <p className="flex items-center gap-1.5 text-xs text-ink/60">
          <ShieldCheck className="h-3.5 w-3.5 text-clinic-600" />
          Access is limited to patients you actively treat. Every lookup is logged.
        </p>
      </CardHeader>
      <CardContent className="flex flex-1 flex-col gap-3 overflow-hidden">
        <div className="flex-1 overflow-y-auto rounded-md border border-border bg-clinic-50/40 p-4">
          {history.length === 0 ? (
            <div className="flex h-full flex-col items-center justify-center gap-3 text-center">
              <p className="text-sm text-ink/50">
                Ask about a patient by name or record number, or refer a patient to a colleague.
              </p>
              <div className="flex flex-col gap-1.5">
                {EXAMPLE_PROMPTS.map((prompt) => (
                  <button
                    key={prompt}
                    type="button"
                    onClick={() => sendMessage(prompt)}
                    className="rounded-full border border-clinic-200 bg-white px-3 py-1.5 text-xs text-clinic-800 hover:bg-clinic-100"
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="flex flex-col gap-3">
              {history.map((turn, i) => (
                <div key={i} className={`flex gap-2 ${turn.role === "user" ? "justify-end" : "justify-start"}`}>
                  {turn.role === "assistant" && (
                    <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-clinic-900 text-white">
                      <MessageCircle className="h-3.5 w-3.5" />
                    </div>
                  )}
                  <div
                    className={`max-w-[80%] whitespace-pre-wrap rounded-lg px-3 py-2 text-sm ${
                      turn.role === "user"
                        ? "bg-clinic-800 text-white"
                        : "border border-border bg-white text-ink"
                    }`}
                  >
                    {turn.content}
                  </div>
                  {turn.role === "user" && (
                    <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-clinic-100 text-clinic-800">
                      <User className="h-3.5 w-3.5" />
                    </div>
                  )}
                </div>
              ))}
              {isSending && (
                <div className="flex items-center gap-2 text-xs text-ink/50">
                  <Loader2 className="h-3.5 w-3.5 animate-spin" /> Looking that up...
                </div>
              )}
            </div>
          )}
        </div>

        {error && (
          <div className="flex items-start gap-2 rounded-md border border-warn-red/30 bg-warn-red/5 p-2.5 text-xs text-warn-red">
            <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="flex gap-2">
          <Textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                sendMessage(input);
              }
            }}
            placeholder="e.g. Show me patient REC-0001"
            className="min-h-[44px] flex-1 resize-none py-2.5"
            rows={1}
          />
          <Button type="submit" disabled={isSending || !input.trim()}>
            <Send className="h-4 w-4" />
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
