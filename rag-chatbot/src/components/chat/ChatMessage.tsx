import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Message } from "@/types";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Bot, User, Copy, Check } from "lucide-react";
import { useState } from "react";
import CitationPopover from "./CitationPopover";

interface ChatMessageProps {
  message: Message;
}

export default function ChatMessage({ message }: ChatMessageProps) {
  const [copied, setCopied] = useState(false);

  const copyToClipboard = () => {
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div
      className={`flex gap-4 ${
        message.role === "user" ? "justify-end" : "justify-start"
      }`}
    >
      {message.role === "assistant" && (
        <Avatar className="shrink-0">
          <AvatarFallback className="bg-emerald-500 text-black">
            <Bot className="w-5 h-5" />
          </AvatarFallback>
        </Avatar>
      )}

      <div
        className={`max-w-2xl ${
          message.role === "user" ? "order-last" : ""
        }`}
      >
        <Card
          className={`p-4 shadow-lg border ${
            message.role === "user"
              ? "bg-black text-white border-emerald-500"
              : "bg-white dark:bg-gray-900 border-gray-200 dark:border-gray-800"
          }`}
        >
          <div className="prose prose-sm dark:prose-invert max-w-none">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {message.content}
            </ReactMarkdown>
          </div>

          {message.sources && message.sources.length > 0 && (
            <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700 flex flex-wrap gap-2">
              {message.sources.map((src, i) => (
                <CitationPopover key={i} index={i + 1} source={src} />
              ))}
            </div>
          )}

          {message.role === "assistant" && (
            <Button
              variant="ghost"
              size="sm"
              className="mt-3 h-8 px-2 text-xs"
              onClick={copyToClipboard}
            >
              {copied ? (
                <>
                  <Check className="w-3 h-3 mr-1" /> Copied!
                </>
              ) : (
                <>
                  <Copy className="w-3 h-3 mr-1" /> Copy
                </>
              )}
            </Button>
          )}
        </Card>
      </div>

      {message.role === "user" && (
        <Avatar className="shrink-0">
          <AvatarFallback className="bg-black text-emerald-500">
            <User className="w-5 h-5" />
          </AvatarFallback>
        </Avatar>
      )}
    </div>
  );
}