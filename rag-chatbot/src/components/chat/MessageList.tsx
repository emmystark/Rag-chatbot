import { ScrollArea } from "@/components/ui/scroll-area";
import { Message } from "@/types";
import ChatMessage from "./ChatMessage";

interface MessageListProps {
  messages: Message[];
}

export default function MessageList({ messages }: MessageListProps) {
  return (
    <ScrollArea className="flex-1 text-white p-6">
      <div className="max-w-4xl mx-auto space-y-8 pb-24">
        {messages.length === 0 ? (
          <div className="text-center py-20 text-black">
            <h1 className="text-4xl  font-bold mb-4">Company Knowledge Bot</h1>
            <p className="text-muted-foreground">
              Ask me anything about policies, products, or internal docs.
            </p>
          </div>
        ) : (
          messages.map((msg) => (
            <ChatMessage key={msg.id} message={msg} />
          ))
        )}
      </div>
    </ScrollArea>
  );
}