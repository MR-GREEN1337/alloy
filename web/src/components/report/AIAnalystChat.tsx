// File: web/src/components/report/AIAnalystChat.tsx
"use client";

import React, { useState, useRef, useEffect, memo, FC } from 'react';
import { useAuth } from '@/components/global/providers';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import ReactMarkdown from "react-markdown";
import { ScrollArea } from '@/components/ui/scroll-area';
import { motion, AnimatePresence } from 'framer-motion';
import { Bot, User, CornerDownLeft, Loader2, XCircle, Sparkles } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Report } from '@/types/report';
import { toast } from 'sonner';
import Logo from '../global/Logo';
import { Avatar, AvatarFallback } from '../ui/avatar';

// --- Types ---
interface Message {
  id: string;
  sender: 'user' | 'bot' | 'error';
  text: string;
  isStreaming?: boolean;
}

interface AIAnalystChatProps {
  report: Report;
}


// --- Sub-components for better organization ---

const AssistantAvatar: FC<{ isError?: boolean }> = ({ isError }) => (
  <Avatar className="h-8 w-8">
    <AvatarFallback className={cn("bg-muted", isError && "bg-destructive text-destructive-foreground")}>
      {isError ? <XCircle className="h-5 w-5" /> : <Logo hideText className="h-5 w-5" />}
    </AvatarFallback>
  </Avatar>
);

const MessageBubble: FC<{ message: Message }> = memo(({ message }) => {
  const isUser = message.sender === 'user';
  return (
    <div className={cn("flex items-start gap-3 w-full", isUser && "justify-end")}>
      {!isUser && <AssistantAvatar isError={message.sender === 'error'} />}
      <div
        className={cn(
          "p-3 text-sm rounded-lg max-w-md prose prose-sm dark:prose-invert prose-p:my-0",
          isUser && "bg-primary text-primary-foreground rounded-br-none",
          message.sender === 'bot' && "bg-muted rounded-bl-none",
          message.sender === 'error' && "bg-destructive/10 text-destructive rounded-bl-none"
        )}
      >
        <ReactMarkdown>{message.text}</ReactMarkdown>
        {message.isStreaming && <span className="inline-block w-2 h-4 bg-foreground ml-1 animate-pulse" />}
      </div>
      {isUser && (
        <Avatar className="h-8 w-8">
          <AvatarFallback><User className="h-5 w-5"/></AvatarFallback>
        </Avatar>
      )}
    </div>
  );
});
MessageBubble.displayName = "MessageBubble";


const MessageList: FC<{ messages: Message[], isLoading: boolean }> = ({ messages, isLoading }) => {
  const endOfMessagesRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Use a small timeout to ensure the DOM is updated before we scroll
    const timer = setTimeout(() => {
      endOfMessagesRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, 100);
    return () => clearTimeout(timer);
  }, [messages, isLoading]);

  return (
    <ScrollArea className="h-full">
      <div className="p-4 space-y-6">
        <AnimatePresence>
          {messages.length === 0 ? (
            <motion.div
              key="empty"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="text-center text-muted-foreground text-sm pt-16"
            >
              <Sparkles className="h-10 w-10 mx-auto mb-4 opacity-50" />
              <p className="font-medium">Ask a follow-up question</p>
              <p>e.g., "Summarize the key risks" or "Expand on the opportunity with [topic]".</p>
            </motion.div>
          ) : (
            messages.map((message) => (
              <motion.div
                key={message.id}
                layout
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ duration: 0.3, ease: "easeOut", layout: { duration: 0.2 } }}
              >
                <MessageBubble message={message} />
              </motion.div>
            ))
          )}
        </AnimatePresence>
        {isLoading && messages[messages.length - 1]?.isStreaming === false && (
          <motion.div
            key="loading"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex items-start gap-3 w-full"
          >
            <AssistantAvatar />
            <div className="p-3 rounded-lg bg-muted"><Loader2 className="h-4 w-4 animate-spin" /></div>
          </motion.div>
        )}
        <div ref={endOfMessagesRef} />
      </div>
    </ScrollArea>
  );
};


// --- Main Component ---

export const AIAnalystChat = ({ report }: AIAnalystChatProps) => {
  const { accessToken } = useAuth();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage: Message = { id: `user-${Date.now()}`, sender: 'user', text: input };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    const historyForApi = [...messages, userMessage].map(msg => ({
        role: msg.sender === 'bot' ? 'assistant' : 'user',
        content: msg.text
    }));

    const botMessageId = `bot-${Date.now()}`;
    setMessages(prev => [...prev, { id: botMessageId, sender: 'bot', text: '', isStreaming: true }]);

    try {
        const reportContext = `Report Title: ${report.title}; Acquirer: ${report.acquirer_brand}; Target: ${report.target_brand}; Compatibility Score: ${report.analysis?.cultural_compatibility_score}; Strategic Summary: ${report.analysis?.strategic_summary};`;

      const res = await fetch(`/api/v1/reports/${report.id}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${accessToken}`
        },
        body: JSON.stringify({ messages: historyForApi, context: reportContext })
      });

      if (!res.ok || !res.body) throw new Error('Failed to get chat response from server.');
      
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let done = false;

      while (!done) {
        const { value, done: readerDone } = await reader.read();
        done = readerDone;
        const chunk = decoder.decode(value, { stream: true });
        setMessages(prev => prev.map(msg => 
            msg.id === botMessageId ? { ...msg, text: msg.text + chunk, isStreaming: !done } : msg
        ));
      }

    } catch (error: any) {
        const errorMessage = "I'm sorry, I encountered an error. Please try again.";
        toast.error("Chat Error", { description: error.message || "An unknown error occurred." });
        setMessages(prev => prev.map(msg => 
            msg.id === botMessageId ? { ...msg, text: errorMessage, isStreaming: false, sender: 'error' } : msg
        ));
    } finally {
        setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-background/50 border-l border-border">
      <div className="p-4 border-b border-border">
        <h3 className="font-semibold text-lg text-foreground">AI Analyst Chat</h3>
        <p className="text-sm text-muted-foreground">Ask questions about this report.</p>
      </div>
      <div className="flex-1 min-h-0">
        <MessageList messages={messages} isLoading={isLoading}/>
      </div>
      <div className="p-4 border-t border-border bg-background">
        <form onSubmit={handleSubmit} className="relative">
          <Textarea
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { handleSubmit(e); } }}
            placeholder="Ask a follow-up..."
            className="pr-12 min-h-[40px] max-h-48"
            disabled={isLoading}
            rows={1}
          />
          <Button type="submit" size="icon" className="absolute right-2 bottom-2 h-8 w-8" disabled={isLoading || !input.trim()}>
            {isLoading ? <Loader2 className="h-4 w-4 animate-spin"/> : <CornerDownLeft className="h-4 w-4" />}
          </Button>
        </form>
      </div>
    </div>
  );
};