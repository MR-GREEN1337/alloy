"use client";

import React, { useState, useRef, useEffect } from 'react';
import { useAuth } from '@/components/global/providers';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import ReactMarkdown from "react-markdown";
import { ScrollArea } from '@/components/ui/scroll-area';
import { motion, AnimatePresence } from 'framer-motion';
import { Bot, User, CornerDownLeft, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Report } from '@/types/report';
import { toast } from 'sonner';

interface Message {
  id: string;
  sender: 'user' | 'bot';
  text: string;
}

interface AIAnalystChatProps {
  report: Report;
}

export const AIAnalystChat = ({ report }: AIAnalystChatProps) => {
  const { accessToken } = useAuth();
  const API_URL = process.env.NEXT_PUBLIC_API_URL;
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const scrollAreaRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Scroll to bottom when new messages are added
    if (scrollAreaRef.current) {
      scrollAreaRef.current.scrollTo({ top: scrollAreaRef.current.scrollHeight, behavior: 'smooth' });
    }
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage: Message = { id: `user-${Date.now()}`, sender: 'user', text: input };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    const botMessageId = `bot-${Date.now()}`;
    setMessages(prev => [...prev, { id: botMessageId, sender: 'bot', text: '...' }]);

    try {
        const reportContext = `
        Report Title: ${report.title}
        Acquirer: ${report.acquirer_brand}
        Target: ${report.target_brand}
        Compatibility Score: ${report.analysis?.cultural_compatibility_score}
        Strategic Summary: ${report.analysis?.strategic_summary}
        Culture Clashes: ${report.culture_clashes.map(c => `- ${c.topic}: ${c.description} (Severity: ${c.severity})`).join('\n')}
        Untapped Growth: ${report.untapped_growths.map(g => `- ${g.description} (Impact: ${g.potential_impact_score})`).join('\n')}
      `;

      const res = await fetch(`${API_URL}/reports/${report.id}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${accessToken}`
        },
        body: JSON.stringify({ query: input, context: reportContext })
      });

      if (!res.ok || !res.body) {
        throw new Error('Failed to get chat response from server.');
      }
      
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      setMessages(prev => prev.map(msg => msg.id === botMessageId ? { ...msg, text: '' } : msg)); // Clear the "..."
      let done = false;

      while (!done) {
        const { value, done: readerDone } = await reader.read();
        done = readerDone;
        const chunk = decoder.decode(value);
        setMessages(prev => prev.map(msg => 
            msg.id === botMessageId ? { ...msg, text: msg.text + chunk } : msg
        ));
      }

    } catch (error: any) {
        const errorMessage = "I'm sorry, I encountered an error. Please try again.";
        toast.error("Chat Error", { description: error.message || "An unknown error occurred." });
        setMessages(prev => prev.map(msg => 
            msg.id === botMessageId ? { ...msg, text: errorMessage } : msg
        ));
        setMessages(prev => prev.filter(msg => msg.id !== botMessageId));
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
      <ScrollArea className="flex-grow p-4" ref={scrollAreaRef}>
        <div className="space-y-6">
            <AnimatePresence>
            {messages.length === 0 && (
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="text-center text-muted-foreground text-sm pt-8">
                    Ask a follow-up question like "Summarize the key risks" or "Expand on the opportunity with [topic]".
                </motion.div>
            )}
            {messages.map(message => (
                <motion.div
                    key={message.id}
                    layout
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.3 }}
                    className={cn(
                        "flex items-start gap-3 w-full",
                        message.sender === 'user' ? "justify-end" : "justify-start"
                    )}
                >
                    {message.sender === 'bot' && <div className="flex-shrink-0 bg-muted rounded-full p-2"><Bot className="h-4 w-4" /></div>}
                    <div className={cn(
                        "max-w-md rounded-lg px-4 py-2 text-sm prose prose-sm dark:prose-invert prose-p:my-2",
                        message.sender === 'bot' ? 'bg-muted rounded-bl-none' : 'bg-primary text-primary-foreground rounded-br-none'
                    )}>
                        <ReactMarkdown>{message.text}</ReactMarkdown>
                        {isLoading && message.id.startsWith('bot-') && messages[messages.length-1].id === message.id && <span className="inline-block w-2 h-4 bg-foreground ml-1 animate-pulse" />}
                    </div>
                    {message.sender === 'user' && <div className="flex-shrink-0 bg-primary/20 rounded-full p-2"><User className="h-4 w-4" /></div>}
                </motion.div>
            ))}
            </AnimatePresence>
        </div>
      </ScrollArea>
      <div className="p-4 border-t border-border bg-background">
        <form onSubmit={handleSubmit} className="relative">
          <Textarea
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    handleSubmit(e);
                }
            }}
            placeholder="Ask a follow-up..."
            className="pr-12 min-h-[40px] max-h-48"
            disabled={isLoading}
          />
          <Button type="submit" size="icon" className="absolute right-2 bottom-1.5 h-8 w-8" disabled={isLoading || !input.trim()}>
            {isLoading ? <Loader2 className="h-4 w-4 animate-spin"/> : <CornerDownLeft className="h-4 w-4" />}
          </Button>
        </form>
      </div>
    </div>
  );
};