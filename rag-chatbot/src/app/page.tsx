"use client";

import { useState } from "react";
import { v4 as uuidv4 } from "uuid";
import MessageList from "@/components/chat/MessageList";
import ChatInput from "@/components/chat/ChatInput";
import { Message } from "@/types";

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);

  const sendMessage = async (content: string) => {
    const userMsg: Message = { id: uuidv4(), role: "user", content };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);

    try {
      const res = await fetch("http://localhost:8000/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: content }),
      });
      const data = await res.json();

      const assistantMsg: Message = {
        id: uuidv4(),
        role: "assistant",
        content: data.answer,
        sources: data.sources,
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          id: uuidv4(),
          role: "assistant",
          content: "Sorry, I couldn't connect to the backend. Is it running?",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full overflow-hidden h-full flex items-center justify-center bg-black">
      <div className="flex flex-col top-20 relative opacity-90 h-4/5 w-160 m-10 p-10 rounded-lg bg-white shadow-lg text-black">
      <MessageList messages={messages} />
      <ChatInput onSubmit={sendMessage} disabled={loading} />
    </div>
    </div>
  );
}