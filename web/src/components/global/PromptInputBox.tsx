"use client";

import React, { useState, useRef, useEffect } from "react";
import * as TooltipPrimitive from "@radix-ui/react-tooltip";
import { ArrowUp, Paperclip, X, Search, Bot, Database, BrainCircuit, CheckCircle, AlertTriangle, Link as LinkIcon, Sparkles, Loader2, Microscope, MessageSquareQuote } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Textarea } from "../ui/textarea";
import { toast } from "sonner";
import { useAuth } from "./providers";
import useSWRMutation from 'swr/mutation';
import { motion, AnimatePresence } from "framer-motion";
import { ScrollArea } from "../ui/scroll-area";
import { Switch } from "../ui/switch";
import { Label } from "../ui/label";
import Image from "next/image";
import Link from "next/link";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "../ui/collapsible";

// API MUTATION
const createDraftReport = async (url: string, { arg }: { arg: { token: string }}) => {
    const res = await fetch(url, { method: 'POST', headers: { 'Authorization': `Bearer ${arg.token}` } });
    if (!res.ok) throw new Error('Failed to create draft session.');
    return res.json();
}

// TYPES
interface Step {
  id: string;
  status: 'info' | 'search' | 'source' | 'analysis' | 'reasoning' | 'synthesis' | 'saving' | 'complete' | 'error';
  message?: string;
  payload?: any;
}

interface UploadedFileStatus {
    id: string;
    name: string;
    status: 'uploading' | 'success' | 'error';
    message?: string;
}

interface PromptInputBoxProps {
  onReportCreated: () => void;
  onPristineChange: (isPristine: boolean) => void;
  className?: string;
}

// --- CHILD COMPONENTS ---

const TooltipProvider = TooltipPrimitive.Provider;
const Tooltip = TooltipPrimitive.Root;
const TooltipTrigger = TooltipPrimitive.Trigger;
const TooltipContent = React.forwardRef<React.ElementRef<typeof TooltipPrimitive.Content>, React.ComponentPropsWithoutRef<typeof TooltipPrimitive.Content>>(({ className, sideOffset = 4, ...props }, ref) => (
  <TooltipPrimitive.Content ref={ref} sideOffset={sideOffset} className={cn("z-50 overflow-hidden rounded-md border border-border bg-popover px-3 py-1.5 text-sm text-popover-foreground shadow-md animate-in fade-in-0", className)} {...props} />
));
TooltipContent.displayName = TooltipPrimitive.Content.displayName;

const SourceItem = ({ source }: { source: { url: string, title?: string }}) => {
    const domain = new URL(source.url).hostname?.replace('www.', '');
    const faviconUrl = `${process.env.NEXT_PUBLIC_API_URL}/utils/favicon?url=${encodeURIComponent(source.url)}`;
    return (
        <Link href={source.url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-2 group">
            <Image src={faviconUrl} alt="source favicon" width={16} height={16} className="rounded-full" unoptimized/>
            <span className="truncate group-hover:underline text-blue-600 dark:text-blue-400">{source.title || source.url}</span>
        </Link>
    );
};

const FaviconPreview = ({ url }: { url: string }) => {
    const faviconUrl = `${process.env.NEXT_PUBLIC_API_URL}/utils/favicon?url=${encodeURIComponent(url)}`;
    return <Image src={faviconUrl} alt="favicon" width={16} height={16} className="rounded-full" unoptimized/>;
}

const StepItem = ({ step }: { step: Step }) => {
    const ICONS = {
        info: <Bot className="h-4 w-4 text-primary" />,
        search: <Search className="h-4 w-4 text-blue-500" />,
        source: <LinkIcon className="h-4 w-4 text-muted-foreground" />,
        analysis: <Microscope className="h-4 w-4 text-purple-500" />,
        reasoning: <MessageSquareQuote className="h-4 w-4 text-gray-500" />,
        synthesis: <BrainCircuit className="h-4 w-4 text-amber-500" />,
        saving: <Database className="h-4 w-4 text-green-500" />,
        complete: <CheckCircle className="h-4 w-4 text-green-500" />,
        error: <AlertTriangle className="h-4 w-4 text-destructive" />
    };

    const renderContent = () => {
        if (step.status === 'source' && step.payload) {
            return <SourceItem source={step.payload} />;
        }
        return step.message;
    };

    return (
        <motion.div layout initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={{ duration: 0.3 }} className="flex items-start gap-3 text-sm">
            <div className="flex-shrink-0 mt-0.5">{ICONS[step.status] || <Sparkles className="h-4 w-4" />}</div>
            <div className={cn("flex-grow", 
                step.status === 'error' && "text-destructive font-medium",
                step.status === 'reasoning' && "text-muted-foreground italic"
            )}>{renderContent()}</div>
        </motion.div>
    );
};

// --- MAIN COMPONENT ---
export const PromptInputBox = React.forwardRef<HTMLDivElement, PromptInputBoxProps>(
  ({ onReportCreated, onPristineChange, className }, ref) => {
    const { accessToken } = useAuth();
    const API_URL = process.env.NEXT_PUBLIC_API_URL;

    const [draftReportId, setDraftReportId] = useState<number | null>(null);
    const [acquirer, setAcquirer] = useState("");
    const [target, setTarget] = useState("");
    const [notes, setNotes] = useState("");
    const [uploadedFile, setUploadedFile] = useState<UploadedFileStatus | null>(null);
    const [useGrounding, setUseGrounding] = useState(false);
    
    const [logSteps, setLogSteps] = useState<Step[]>([]);
    const [sources, setSources] = useState<Step[]>([]);
    const [isGenerating, setIsGenerating] = useState(false);
    const [isCollapsibleOpen, setIsCollapsibleOpen] = useState(true);

    const fileInputRef = useRef<HTMLInputElement>(null);
    const scrollAreaRef = useRef<HTMLDivElement>(null);

    const { trigger: triggerDraft, isMutating: isCreatingDraft } = useSWRMutation(`${API_URL}/reports/draft`, createDraftReport);
    const isLoading = isCreatingDraft || isGenerating || uploadedFile?.status === 'uploading';

    useEffect(() => {
        if (accessToken && !draftReportId && !isGenerating) {
            triggerDraft({ token: accessToken })
                .then(data => setDraftReportId(data.id))
                .catch(() => toast.error("Could not start a new session.", { description: "Please refresh the page." }));
        }
    }, [accessToken, draftReportId, triggerDraft, isGenerating]);
    
    useEffect(() => { onPristineChange(!acquirer && !target && !notes && !uploadedFile); }, [acquirer, target, notes, uploadedFile, onPristineChange]);
    useEffect(() => { if (scrollAreaRef.current) scrollAreaRef.current.scrollTo({ top: scrollAreaRef.current.scrollHeight, behavior: 'smooth' }); }, [logSteps, sources]);

    const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file || !draftReportId) return;
        const fileId = `${file.name}-${Date.now()}`;
        setUploadedFile({ id: fileId, name: file.name, status: 'uploading' });
        const formData = new FormData();
        formData.append('file', file);
        try {
            const res = await fetch(`${API_URL}/reports/${draftReportId}/upload_context_file`, { method: 'POST', headers: { 'Authorization': `Bearer ${accessToken!}` }, body: formData });
            if (!res.ok) { const errorData = await res.json(); throw new Error(errorData.detail || 'File upload failed'); }
            setUploadedFile({ id: fileId, name: file.name, status: 'success', message: 'Context uploaded' });
            toast.success("Context file uploaded successfully.");
        } catch (error: any) {
            setUploadedFile({ id: fileId, name: file.name, status: 'error', message: error.message });
            toast.error("File Upload Failed", { description: error.message });
        }
    };

    const handleSubmit = async () => {
        if (isLoading || !draftReportId || acquirer.trim().length < 2 || target.trim().length < 2) {
             toast.error("Invalid Input", { description: "Please provide full, official brand names."});
            return;
        }
        setIsGenerating(true); setLogSteps([]); setSources([]); setIsCollapsibleOpen(true);
        
        try {
            const response = await fetch(`${API_URL}/reports/${draftReportId}/generate`, {
                method: 'POST', headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${accessToken!}` },
                body: JSON.stringify({ acquirer_brand: acquirer, target_brand: target, title: `${acquirer} vs. ${target}`, context: notes, use_grounding: useGrounding })
            });
            if (!response.ok || !response.body) { throw new Error(response.statusText || "Server response was invalid."); }
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let accumulatedChunks = "";

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                accumulatedChunks += decoder.decode(value, { stream: true });
                const lines = accumulatedChunks.split('\n\n');
                accumulatedChunks = lines.pop() || "";

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const jsonData = JSON.parse(line.substring(6));
                        const newStep: Step = { id: `step-${Date.now()}-${Math.random()}`, ...jsonData };
                        if (newStep.status === 'source') { setSources(prev => [...prev, newStep]); } 
                        else { setLogSteps(prev => [...prev, newStep]); }
                        
                        if (newStep.status === 'complete') {
                            toast.success("Report generated successfully!");
                            onReportCreated();
                            setTimeout(() => handleReset(false), 1000);
                            return;
                        }
                        if (newStep.status === 'error') {
                            toast.error("Generation Failed", { description: newStep.message });
                            handleReset();
                            return;
                        }
                    }
                }
            }
        } catch (err: any) { toast.error("An error occurred", { description: err.message }); setIsGenerating(false); }
    };
    
    const handleReset = (resetId = true) => {
        setIsGenerating(false); setLogSteps([]); setSources([]);
        setAcquirer(""); setTarget(""); setNotes(""); setUploadedFile(null);
        if (resetId) setDraftReportId(null);
    }

    const canSubmit = acquirer.trim().length > 1 && target.trim().length > 1 && uploadedFile?.status !== 'uploading';

    if (isGenerating) {
        return <div ref={ref} className={cn("w-full max-w-3xl mx-auto", className)}>
            <motion.div layout className="relative w-full rounded-2xl border border-border bg-card shadow-xl transition-all">
                <div className="p-4"><h3 className="font-semibold text-center text-foreground">Generating Report...</h3><p className="text-center text-sm text-muted-foreground">{acquirer} vs. {target}</p></div>
                <ScrollArea className="h-[30rem] max-h-[60vh] px-4" ref={scrollAreaRef}>
                    <div className="space-y-3 py-4">
                        <AnimatePresence>{logSteps.map((step) => <StepItem key={step.id} step={step} />)}</AnimatePresence>
                        {sources.length > 0 && <Collapsible open={isCollapsibleOpen} onOpenChange={setIsCollapsibleOpen}>
                            <CollapsibleTrigger className="w-full p-2 rounded-md hover:bg-muted/50 text-left">
                                <div className="flex items-center justify-between"><div className="flex items-center gap-2 overflow-hidden"><Search className="h-4 w-4 text-blue-500 flex-shrink-0"/><span className="text-sm font-medium">Found {sources.length} sources</span>
                                <div className="flex items-center gap-1.5 flex-shrink min-w-0">
                                    {/* CORE FIX: Remove framer-motion from the list mapping */}
                                    {sources.map(source => <FaviconPreview key={source.id} url={source.payload.url}/>)}
                                </div>
                                </div><span className="text-xs text-muted-foreground">{isCollapsibleOpen ? 'Collapse' : 'Expand'}</span></div>
                            </CollapsibleTrigger>
                            <CollapsibleContent className="space-y-3 pt-2">{sources.map(source => <StepItem key={source.id} step={source} />)}</CollapsibleContent>
                        </Collapsible>}
                    </div>
                </ScrollArea>
                <div className="flex items-center justify-end p-2 border-t border-border"><Button onClick={() => handleReset(true)}>Create New Report</Button></div>
            </motion.div>
        </div>
    }

    return (
        <div ref={ref} className={cn("w-full max-w-3xl mx-auto", className)}>
            <motion.div layout className="relative w-full rounded-2xl border border-border bg-card shadow-xl transition-all">
              <div className="p-4 space-y-3">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <Input placeholder="Acquirer (e.g., The Walt Disney Company)" value={acquirer} onChange={(e) => setAcquirer(e.target.value)} className="h-10 bg-background" disabled={isLoading} />
                  <Input placeholder="Target (e.g., A24 Films)" value={target} onChange={(e) => setTarget(e.target.value)} className="h-10 bg-background" disabled={isLoading} />
                </div>
                <Textarea placeholder="Add optional notes or a specific query for the AI..." value={notes} onChange={(e) => setNotes(e.target.value)} className="bg-background min-h-[40px] max-h-48" rows={1} disabled={isLoading} />
                 {uploadedFile && <motion.div layout initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex items-center justify-between rounded-lg bg-background p-2">
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        {uploadedFile.status === 'uploading' && <Loader2 className="h-4 w-4 animate-spin" />}
                        {uploadedFile.status === 'success' && <CheckCircle className="h-4 w-4 text-green-500" />}
                        {uploadedFile.status === 'error' && <AlertTriangle className="h-4 w-4 text-destructive" />}
                        <span className="truncate">{uploadedFile.name}</span>
                    </div>
                    <Button variant="ghost" size="icon" className="h-6 w-6 rounded-full" onClick={() => setUploadedFile(null)}><X className="h-4 w-4" /></Button>
                </motion.div>}
              </div>
              <div className="flex items-center justify-between p-2 border-t border-border">
                <div className="flex items-center gap-1">
                    <TooltipProvider delayDuration={100}>
                        <Tooltip>
                            <TooltipTrigger asChild><Button size="icon" variant="ghost" className="h-8 w-8 text-muted-foreground" onClick={() => fileInputRef.current?.click()} disabled={isLoading}><Paperclip className="h-4 w-4" /></Button></TooltipTrigger>
                            <TooltipContent side="top">Attach Context (.pdf, .xlsx, .txt, .md)</TooltipContent>
                        </Tooltip>
                         <Tooltip>
                            <TooltipTrigger asChild><div className="flex items-center space-x-2 p-2"><Switch id="grounding-switch" checked={useGrounding} onCheckedChange={setUseGrounding} disabled={isLoading} /><Label htmlFor="grounding-switch" className="text-xs text-muted-foreground">Grounding</Label></div></TooltipTrigger>
                            <TooltipContent side="top">Use live web search to enrich analysis</TooltipContent>
                        </Tooltip>
                    </TooltipProvider>
                    <input type="file" ref={fileInputRef} onChange={handleFileChange} accept=".pdf,.xlsx,.xls,.txt,.md" className="hidden" disabled={!draftReportId || !!uploadedFile}/>
                </div>
                <Button onClick={handleSubmit} disabled={isLoading || !canSubmit}>
                    {isLoading ? "Processing..." : "Generate Report"}
                    <ArrowUp className="ml-2 h-4 w-4" />
                </Button>
              </div>
            </motion.div>
            <p className="text-center text-xs text-muted-foreground mt-3 px-4">
                Please use full, official brand names for best results. Data provided by Qloo, the AI for culture and taste.
            </p>
        </div>
    );
});
PromptInputBox.displayName = "PromptInputBox";