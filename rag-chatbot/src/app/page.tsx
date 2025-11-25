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
    const userMsg: Message = {
      id: uuidv4(),
      role: "user",
      content,
      timestamp: new Date().toISOString(),
    };
    setMessages(prev => [...prev, userMsg]);
    setLoading(true);

    try {
      const res = await fetch("http://localhost:8000/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: content }),  // ← MUST BE "question"
      });

      if (!res.ok) throw new Error("Network error");

      const data = await res.json();
      const assistantMsg = data.messages[1]; // backend returns both

      setMessages(prev => [...prev, {
        id: uuidv4(),
        role: "assistant",
        content: assistantMsg.content,
        timestamp: assistantMsg.timestamp,
        sources: assistantMsg.sources || []
      }]);

    } catch (err) {
      setMessages(prev => [...prev, {
        id: uuidv4(),
        role: "assistant",
        content: "Sorry, I couldn't connect to the backend. Is it running?",
        timestamp: new Date().toISOString(),
      }]);
    } finally {
      setLoading(false);
    }
  };

  return (
   <div className=" flex justify-center">
     <div className="min-h-screen bg-black flex flex-col w-3/5 relative top-50 border-1 border-green-500 rounded-lg">
      <h1 className="text-white text-4xl text-center py-8 font-bold">
        Company Resource Search
      </h1>
      <div className="flex-1 max-w-4xl text-black mx-auto w-full p-4">
        <MessageList messages={messages} />
        <ChatInput onSubmit={sendMessage} disabled={loading} />
      </div>
    </div>
   </div>
  );
}