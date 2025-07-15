"use client";

import React, { useState, useRef, useEffect, FormEvent } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { toast } from 'sonner';
import useSWRMutation from 'swr/mutation';
import { useAuth } from '@/components/global/providers';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Input } from '../ui/input';
import { Button } from '../ui/button';
import { Label } from '../ui/label';
import { Switch } from '../ui/switch';
import { Textarea } from '../ui/textarea';
import { ArrowUp, Plus, Bot, User } from 'lucide-react';
import { ScrollArea } from '../ui/scroll-area';
import { cn } from '@/lib/utils';

interface Message {
  id: number;
  text: string;
  sender: 'bot' | 'user';
  component?: React.ReactNode;
}

interface ChatCreatorProps {
    onReportCreated: () => void;
}

const createReport = async (url: string, { arg }: { arg: any }) => {
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${arg.token}` },
    body: JSON.stringify(arg.data)
  });
  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.detail || 'Failed to create report.');
  }
  return response.json();
}

export const ChatCreator = ({ onReportCreated }: ChatCreatorProps) => {
  const { accessToken } = useAuth();
  const API_URL = process.env.NEXT_PUBLIC_API_URL;
  const { trigger: triggerCreate, isMutating: isCreating } = useSWRMutation(`${API_URL}/reports/`, createReport);

  const [messages, setMessages] = useState<Message[]>([
    { id: 1, text: "Welcome to Alloy. Let's de-risk your next acquisition. Who is the **acquiring** company?", sender: 'bot' }
  ]);
  const [inputValue, setInputValue] = useState('');
  const [stage, setStage] = useState<'acquirer' | 'target' | 'context' | 'ready'>('acquirer');
  const [acquirer, setAcquirer] = useState('');
  const [target, setTarget] = useState('');
  const [context, setContext] = useState('');
  const [useGrounding, setUseGrounding] = useState(false);
  const [showContext, setShowContext] = useState(false);

  const scrollAreaRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollAreaRef.current) {
      scrollAreaRef.current.scrollTo({ top: scrollAreaRef.current.scrollHeight, behavior: 'smooth' });
    }
  }, [messages]);

  const addMessage = (text: string, sender: 'bot' | 'user', component?: React.ReactNode) => {
    const newMessage: Message = { id: Date.now(), text, sender, component };
    setMessages(prev => [...prev, newMessage]);
  };

  const handleSendMessage = (e: FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim() || isCreating) return;

    addMessage(inputValue, 'user');

    switch (stage) {
      case 'acquirer':
        setAcquirer(inputValue);
        setStage('target');
        addMessage(`Great. And who is the **target** company?`, 'bot');
        break;
      case 'target':
        setTarget(inputValue);
        setStage('ready');
        addMessage(`Perfect. We're ready to analyze the cultural compatibility between **${acquirer}** (Acquirer) and **${inputValue}** (Target).`, 'bot', 
          <div className="mt-4 p-4 border rounded-lg bg-background/50 space-y-4">
              <div className="flex items-center justify-between">
                <Label htmlFor="grounding-switch" className="flex flex-col space-y-1">
                  <span>Enable Internet Grounding</span>
                  <span className="font-normal leading-snug text-muted-foreground text-xs">
                    Allow AI to use its knowledge to enrich analysis.
                  </span>
                </Label>
                <Switch id="grounding-switch" checked={useGrounding} onCheckedChange={setUseGrounding} />
              </div>
               <Button variant="ghost" size="sm" className="w-full justify-start" onClick={() => setShowContext(true)}>
                    <Plus className="mr-2 h-4 w-4" /> Add Supplementary Context
                </Button>
              {showContext && (
                <Textarea 
                    placeholder="Paste any relevant articles, memos, or data here..." 
                    value={context}
                    onChange={e => setContext(e.target.value)}
                    className="min-h-[100px]"
                />
              )}
          </div>
        );
        break;
    }
    setInputValue('');
  };

  const handleGenerateReport = async () => {
    if (!acquirer || !target || isCreating) return;

    let toastId = toast.loading("Kicking off analysis...", { description: "This may take a minute." });
    setTimeout(() => toast.loading("Analyzing taste profiles...", { id: toastId }), 2000);
    setTimeout(() => toast.loading("Synthesizing strategic insights...", { id: toastId }), 5000);

    try {
      await triggerCreate({
        token: accessToken!,
        data: {
          acquirer_brand: acquirer,
          target_brand: target,
          title: `${acquirer} vs. ${target}`,
          context: context || null,
          use_grounding: useGrounding
        }
      });
      toast.success("Report generated successfully!", { id: toastId });
      onReportCreated();
      // Reset state for next report
      setMessages([{ id: 1, text: "Welcome back. Let's analyze another deal. Who is the acquiring company?", sender: 'bot' }]);
      setStage('acquirer');
      setAcquirer('');
      setTarget('');
      setContext('');
      setUseGrounding(false);
      setShowContext(false);
    } catch (err: any) {
      toast.error("Report Generation Failed", { id: toastId, description: err.message });
    }
  };

  return (
    <Card className="lg:col-span-1 flex flex-col h-[500px] md:h-auto">
      <CardHeader>
        <CardTitle>Create New Alloy Report</CardTitle>
        <CardDescription>Use the chat to start your cultural analysis.</CardDescription>
      </CardHeader>
      <CardContent className="flex-grow flex flex-col gap-4 overflow-hidden">
        <ScrollArea className="flex-grow pr-4 -mr-4" ref={scrollAreaRef}>
            <div className="space-y-6">
            <AnimatePresence>
              {messages.map((message) => (
                <motion.div
                  key={message.id}
                  layout
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.3 }}
                  className={cn(
                    "flex items-start gap-3",
                    message.sender === 'user' ? 'justify-end' : 'justify-start'
                  )}
                >
                  {message.sender === 'bot' && (
                    <div className="bg-muted rounded-full p-2">
                      <Bot className="h-4 w-4" />
                    </div>
                  )}
                  <div className={cn(
                    "max-w-xs md:max-w-sm rounded-lg px-4 py-2 text-sm",
                    message.sender === 'bot' 
                      ? 'bg-muted rounded-bl-none' 
                      : 'bg-primary text-primary-foreground rounded-br-none'
                  )}>
                    <p dangerouslySetInnerHTML={{ __html: message.text }}></p>
                    {message.component}
                  </div>
                   {message.sender === 'user' && (
                    <div className="bg-primary/20 rounded-full p-2">
                      <User className="h-4 w-4" />
                    </div>
                  )}
                </motion.div>
              ))}
            </AnimatePresence>
            </div>
        </ScrollArea>
        
        {stage === 'ready' ? (
            <Button onClick={handleGenerateReport} disabled={isCreating} className="w-full">
              {isCreating ? 'Analyzing...' : 'Generate Report'}
            </Button>
        ) : (
            <form onSubmit={handleSendMessage} className="flex items-center gap-2">
                <Input
                    id="chat-input"
                    placeholder={
                        stage === 'acquirer' ? "e.g., Disney" :
                        stage === 'target' ? "e.g., A24 Films" :
                        "Enter your message..."
                    }
                    value={inputValue}
                    onChange={(e) => setInputValue(e.target.value)}
                    autoComplete="off"
                    disabled={isCreating}
                />
                <Button type="submit" size="icon" disabled={!inputValue.trim() || isCreating}>
                    <ArrowUp className="h-4 w-4" />
                </Button>
            </form>
        )}
      </CardContent>
    </Card>
  );
};