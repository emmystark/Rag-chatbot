"use client";
import { useState, useRef, useEffect } from "react";
import { v4 as uuidv4 } from "uuid";
import MessageList from "@/components/chat/MessageList";
import ChatInput from "@/components/chat/ChatInput";
import { Message, Conversation } from "@/types";
import { Bot, Menu, Clock, Sparkles, Plus, MessageSquare, Trash2, Upload, X, FileText } from "lucide-react";

export default function Home() {
  const [conversations, setConversations] = useState<Conversation[]>([
    { id: uuidv4(), title: "New Conversation", messages: [], createdAt: new Date().toISOString() }
  ]);
  const [currentConversationId, setCurrentConversationId] = useState<string>(conversations[0].id);
  const [loading, setLoading] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [uploadedFiles, setUploadedFiles] = useState<Array<{ id: string; name: string; size: string; file: File }>>([]);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const currentConversation = conversations.find(c => c.id === currentConversationId);
  const currentMessages = currentConversation?.messages || [];

  // Save conversations to localStorage
  useEffect(() => {
    localStorage.setItem("conversations", JSON.stringify(conversations));
  }, [conversations]);

  // Load conversations from localStorage on mount
  useEffect(() => {
    const saved = localStorage.getItem("conversations");
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        if (parsed.length > 0) {
          setConversations(parsed);
          setCurrentConversationId(parsed[0].id);
        }
      } catch (e) {
        console.error("Failed to load conversations:", e);
      }
    }
  }, []);

  const createNewConversation = () => {
    const newConv: Conversation = {
      id: uuidv4(),
      title: "New Conversation",
      messages: [],
      createdAt: new Date().toISOString()
    };
    setConversations(prev => [newConv, ...prev]);
    setCurrentConversationId(newConv.id);
  };

  const deleteConversation = (id: string) => {
    if (conversations.length === 1) {
      // Don't delete the last conversation, just clear it
      setConversations([{
        id: uuidv4(),
        title: "New Conversation",
        messages: [],
        createdAt: new Date().toISOString()
      }]);
      setCurrentConversationId(conversations[0].id);
      return;
    }
    
    const filtered = conversations.filter(c => c.id !== id);
    setConversations(filtered);
    if (currentConversationId === id) {
      setCurrentConversationId(filtered[0].id);
    }
  };

  const updateConversationTitle = (id: string, firstMessage: string) => {
    const title = firstMessage.slice(0, 30) + (firstMessage.length > 30 ? "..." : "");
    setConversations(prev =>
      prev.map(c => c.id === id ? { ...c, title } : c)
    );
  };

  const sendMessage = async (content: string) => {
    const userMsg: Message = {
      id: uuidv4(),
      role: "user",
      content,
      timestamp: new Date().toISOString(),
    };

    // Update conversation with user message
    setConversations(prev =>
      prev.map(c =>
        c.id === currentConversationId
          ? { ...c, messages: [...c.messages, userMsg] }
          : c
      )
    );

    // Update title if this is the first message
    if (currentMessages.length === 0) {
      updateConversationTitle(currentConversationId, content);
    }

    setLoading(true);

    try {
      // Prepare form data for file upload
      const formData = new FormData();
      formData.append("question", content);
      
      // Add uploaded files if any
      uploadedFiles.forEach(file => {
        formData.append("files", file.file);
      });

      const res = await fetch("http://localhost:8000/api/chat", {
        method: "POST",
        body: uploadedFiles.length > 0 ? formData : JSON.stringify({ question: content }),
        headers: uploadedFiles.length > 0 ? {} : { "Content-Type": "application/json" },
      });

      if (!res.ok) throw new Error("Network error");
      const data = await res.json();
      const assistantMsg = data.messages[1];

      setConversations(prev =>
        prev.map(c =>
          c.id === currentConversationId
            ? {
                ...c,
                messages: [
                  ...c.messages,
                  {
                    id: uuidv4(),
                    role: "assistant",
                    content: assistantMsg.content,
                    timestamp: assistantMsg.timestamp,
                    sources: assistantMsg.sources || []
                  }
                ]
              }
            : c
        )
      );
    } catch (err) {
      setConversations(prev =>
        prev.map(c =>
          c.id === currentConversationId
            ? {
                ...c,
                messages: [
                  ...c.messages,
                  {
                    id: uuidv4(),
                    role: "assistant",
                    content: "Sorry, I couldn't connect to the backend. Is it running?",
                    timestamp: new Date().toISOString(),
                  }
                ]
              }
            : c
        )
      );
    } finally {
      setLoading(false);
      // Clear uploaded files after sending
      setUploadedFiles([]);
    }
  };

  const handleFileUpload = (files: FileList | null) => {
    if (!files) return;
    
    const newFiles = Array.from(files).map(file => ({
      id: uuidv4(),
      name: file.name,
      size: (file.size / 1024).toFixed(2) + " KB",
      file: file
    }));
    
    setUploadedFiles(prev => [...prev, ...newFiles]);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    handleFileUpload(e.dataTransfer.files);
  };

  const removeFile = (id: string) => {
    setUploadedFiles(prev => prev.filter(f => f.id !== id));
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-purple-950/20 to-slate-950 text-white font-sans overflow-hidden">
      {/* Animated background */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 -left-20 w-96 h-96 bg-purple-500/10 rounded-full blur-3xl animate-pulse"></div>
        <div className="absolute bottom-1/4 -right-20 w-96 h-96 bg-emerald-500/10 rounded-full blur-3xl animate-pulse" style={{ animationDelay: '1s' }}></div>
      </div>

      <div className="relative z-10 flex h-screen">
        {/* Sidebar */}
        <div className={`${sidebarOpen ? 'w-80' : 'w-0'} transition-all duration-300 ease-in-out overflow-hidden border-r border-white/5`}>
          <div className="h-full backdrop-blur-xl bg-white/5 p-4 flex flex-col">
            {/* New Chat Button */}
            <button
              onClick={createNewConversation}
              className="w-full mb-4 p-3 rounded-xl bg-gradient-to-br from-emerald-500 to-green-500 hover:from-emerald-600 hover:to-green-600 transition-all flex items-center justify-center gap-2 font-semibold"
            >
              <Plus className="w-5 h-5" />
              New Chat
            </button>

            {/* Upload Area */}
            <div
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              className={`mb-4 p-4 rounded-xl border-2 border-dashed transition-all cursor-pointer group ${
                isDragging
                  ? 'border-emerald-400 bg-emerald-500/10 scale-105'
                  : 'border-white/10 hover:border-emerald-400/50 hover:bg-white/5'
              }`}
              onClick={() => fileInputRef.current?.click()}
            >
              <input
                ref={fileInputRef}
                type="file"
                multiple
                className="hidden"
                onChange={(e) => handleFileUpload(e.target.files)}
                accept=".pdf,.txt,.doc,.docx,.csv,.json"
              />
              <div className="flex flex-col items-center gap-2 text-center">
                <div className="p-2 rounded-lg bg-white/5 group-hover:bg-emerald-500/20 transition-colors">
                  <Upload className="w-5 h-5 text-emerald-400" />
                </div>
                <div>
                  <p className="text-xs font-medium text-white/90">Upload Documents</p>
                  <p className="text-xs text-white/50 mt-0.5">Drag & drop or click</p>
                </div>
              </div>
            </div>

            {/* Uploaded Files */}
            {uploadedFiles.length > 0 && (
              <div className="mb-4 space-y-2 max-h-32 overflow-y-auto">
                {uploadedFiles.map((file) => (
                  <div
                    key={file.id}
                    className="p-2 rounded-lg bg-white/5 border border-white/10 group hover:bg-white/10 transition-all"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2 flex-1 min-w-0">
                        <FileText className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                        <div className="flex-1 min-w-0">
                          <p className="text-xs font-medium text-white/90 truncate">{file.name}</p>
                          <p className="text-xs text-white/50">{file.size}</p>
                        </div>
                      </div>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          removeFile(file.id);
                        }}
                        className="p-1 rounded hover:bg-red-500/20 transition-colors opacity-0 group-hover:opacity-100"
                      >
                        <X className="w-3 h-3 text-red-400" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Conversation History */}
            <div className="flex items-center gap-2 mb-3 px-2">
              <MessageSquare className="w-4 h-4 text-emerald-400" />
              <h2 className="text-sm font-semibold text-white/80">History</h2>
            </div>

            <div className="flex-1 overflow-y-auto space-y-2">
              {conversations.map((conv) => (
                <div
                  key={conv.id}
                  className={`group p-3 rounded-xl cursor-pointer transition-all ${
                    currentConversationId === conv.id
                      ? 'bg-emerald-500/20 border border-emerald-500/30'
                      : 'bg-white/5 hover:bg-white/10 border border-white/5'
                  }`}
                  onClick={() => setCurrentConversationId(conv.id)}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-white/90 truncate">
                        {conv.title}
                      </p>
                      <p className="text-xs text-white/50 mt-1">
                        {conv.messages.length} messages
                      </p>
                    </div>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        deleteConversation(conv.id);
                      }}
                      className="p-1.5 rounded-lg hover:bg-red-500/20 transition-colors opacity-0 group-hover:opacity-100"
                    >
                      <Trash2 className="w-3.5 h-3.5 text-red-400" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Main Chat Area */}
        <div className="flex-1 flex flex-col">
          {/* Header */}
          <div className="backdrop-blur-xl bg-white/5 border-b border-white/5 px-6 py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <button
                  onClick={() => setSidebarOpen(!sidebarOpen)}
                  className="p-2 rounded-xl hover:bg-white/10 transition-colors"
                >
                  <Menu className="w-5 h-5" />
                </button>
                <div className="flex items-center gap-3">
                  <div className="relative">
                    <div className="p-2 rounded-xl bg-gradient-to-br from-emerald-500 to-green-500">
                      <Bot className="w-6 h-6" />
                    </div>
                    <div className="absolute -bottom-1 -right-1 w-3 h-3 bg-green-400 rounded-full border-2 border-slate-950"></div>
                  </div>
                  <div>
                    <h1 className="text-lg font-bold">Company Resource Search</h1>
                    <p className="text-xs text-white/50">AI-Powered Knowledge Assistant</p>
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-2 text-xs text-white/50">
                <Clock className="w-4 h-4" />
                <span>{new Date().toLocaleDateString()}</span>
              </div>
            </div>
          </div>

          {/* Messages Area */}
          <div className="flex-1 overflow-scroll">
            <MessageList messages={currentMessages} />
          </div>

          {/* Input Area */}
          <div className="backdrop-blur-xl bg-white/5 text-black border-t border-white/5">
            <ChatInput onSubmit={sendMessage} disabled={loading} />
          </div>
        </div>
      </div>
    </div>
  );
}