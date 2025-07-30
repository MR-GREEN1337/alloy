"use client";

import React, { useMemo } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { Report, ReportAnalysis, ClashSeverity } from "@/types/report";
import { cn } from "@/lib/utils";
import ReactMarkdown from "react-markdown";

// UI Components
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from "@/components/ui/resizable";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScrollArea } from "../ui/scroll-area";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ChartContainer } from "../ui/chart";
import { RadialBar, RadialBarChart, PolarAngleAxis } from 'recharts';


// Child Components
import { AIAnalystChat } from "./AIAnalystChat";

// Icons
import {
  AlertTriangle, TrendingUp, Zap, Link as LinkIcon, Globe, Users, Target, Scale,
  Briefcase, BarChart3, Info, BrainCircuit, FileText, XCircle
} from "lucide-react";

// --- Types & Interfaces ---
interface ReportViewProps {
  report: Report;
  children?: React.ReactNode;
}

// --- Utility Hooks & Components ---

const useParsedReport = (report: Report) => {
  return useMemo(() => {
    const parsedReport = { ...report };
    if (report.analysis) {
      const mutableAnalysis: ReportAnalysis = { ...report.analysis, report: parsedReport };
      mutableAnalysis.report = parsedReport; // Add back-reference

      const keysToParse = ['brand_archetype_summary', 'corporate_ethos_summary', 'persona_expansion_summary'];
      for (const key of keysToParse) {
        const field = key as keyof ReportAnalysis;
        if (typeof (mutableAnalysis as any)[field] === 'string') {
          try {
            (mutableAnalysis as any)[field] = JSON.parse(mutableAnalysis[field] as string);
          } catch (e) {
            (mutableAnalysis as any)[field] = {};
          }
        }
      }
      parsedReport.analysis = mutableAnalysis;
    }
    return parsedReport;
  }, [report]);
};

const IconHeader = ({ icon: Icon, title, description }: { icon: React.ElementType, title: string, description?: string }) => (
    <div className="space-y-1.5">
        <CardTitle className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10 text-primary flex-shrink-0">
                <Icon className="h-5 w-5" />
            </div>
            <span>{title}</span>
        </CardTitle>
        {description && <CardDescription>{description}</CardDescription>}
    </div>
);

const SourcePill = ({ url, title }: { url: string, title?: string }) => {
  try {
    const domain = new URL(url).hostname?.replace('www.', '');
    const faviconUrl = `/api/v1/utils/favicon?url=${encodeURIComponent(url)}`;
    return (
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <Link href={url} target="_blank" rel="noopener noreferrer" className="inline-flex max-w-full items-center gap-2 rounded-md border bg-secondary/50 px-3 py-1 text-sm text-secondary-foreground transition-colors hover:bg-secondary">
              <Image src={faviconUrl} alt={`${domain} favicon`} width={16} height={16} className="flex-shrink-0 rounded-full" unoptimized />
              <span className="truncate">{title || domain}</span>
            </Link>
          </TooltipTrigger>
          <TooltipContent><p>{url}</p></TooltipContent>
        </Tooltip>
      </TooltipProvider>
    );
  } catch (error) {
    return null;
  }
};

const SeverityBadge = ({ severity }: { severity: ClashSeverity }) => {
  const config = {
    HIGH: { text: "High", className: "bg-red-200 text-red-800 border-red-300 dark:bg-red-900/50 dark:text-red-300 dark:border-red-700" },
    MEDIUM: { text: "Medium", className: "bg-yellow-200 text-yellow-800 border-yellow-300 dark:bg-yellow-900/50 dark:text-yellow-300 dark:border-yellow-700" },
    LOW: { text: "Low", className: "bg-blue-200 text-blue-800 border-blue-300 dark:bg-blue-900/50 dark:text-blue-300 dark:border-blue-700" },
  };
  const { text, className } = config[severity] || config.LOW;
  return <Badge className={`font-semibold ${className}`}>{text}</Badge>;
};

// --- Report Section Components ---

const CompanyHeader = ({ brandName }: { brandName: string }) => (
    <div className="flex items-center gap-3">
        <Image 
            src={`/api/v1/utils/favicon?brandName=${encodeURIComponent(brandName)}`} 
            alt={`${brandName} logo`} 
            width={40} height={40} 
            className="rounded-lg border bg-background p-1" 
            unoptimized 
        />
        <span className="text-2xl font-semibold">{brandName}</span>
    </div>
);

const ReportHeader = ({ report, children }: ReportViewProps) => (
  <Card>
    <CardHeader className="space-y-4">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <CardTitle className="text-3xl">{report.title}</CardTitle>
          <CardDescription className="mt-2">Cultural due diligence report generated on {new Date(report.created_at).toLocaleString()}.</CardDescription>
        </div>
        <div className="flex-shrink-0">{children}</div>
      </div>
      <div className="flex items-center justify-between gap-4 pt-4 border-t">
          <CompanyHeader brandName={report.acquirer_brand} />
          <span className="text-muted-foreground font-medium sm:mx-4">ACQUIRING</span>
          <CompanyHeader brandName={report.target_brand} />
      </div>
    </CardHeader>
  </Card>
);

const StatCard = ({ icon: Icon, title, value, unit, description }: { icon: React.ElementType, title: string, value: string | number, unit?: string, description: string }) => (
    <Card className="flex flex-col justify-between">
        <CardHeader className="pb-2">
            <CardDescription className="flex items-center gap-2 text-sm"><Icon className="h-4 w-4" />{title}</CardDescription>
        </CardHeader>
        <CardContent>
            <span className="text-3xl font-bold">{value}</span>
            {unit && <span className="text-lg text-muted-foreground">{unit}</span>}
            <p className="text-xs text-muted-foreground mt-1">{description}</p>
        </CardContent>
    </Card>
);

const ScoreAndMetrics = ({ analysis }: { analysis: ReportAnalysis | null }) => {
  if (!analysis) return null;
  const expansionData = analysis.persona_expansion_summary as { expansion_score: number };
  const scoreData = [{ name: 'Score', value: analysis.cultural_compatibility_score, fill: 'hsl(var(--primary))' }];
  
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
            <CardHeader><IconHeader icon={Scale} title="Overall Compatibility Score" /></CardHeader>
            <CardContent className="h-48 flex items-center justify-center">
                 <ChartContainer config={{}} className="mx-auto aspect-square h-full max-h-[200px] dark:text-white">
                    <RadialBarChart data={scoreData} startAngle={90} endAngle={-270} innerRadius="80%" outerRadius="100%" barSize={20}>
                        <PolarAngleAxis type="number" domain={[0, 100]} tick={false} />
                        <RadialBar dataKey="value" background={{ fill: 'hsl(var(--muted))' }} cornerRadius={10} />
                        <text x="50%" y="50%" textAnchor="middle" dominantBaseline="middle" className="fill-foreground text-5xl font-bold">{analysis.cultural_compatibility_score.toFixed(0)}</text>
                        <text x="50%" y="65%" textAnchor="middle" dominantBaseline="middle" className="fill-muted-foreground text-sm">/ 100</text>
                    </RadialBarChart>
                </ChartContainer>
            </CardContent>
        </Card>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
            <StatCard icon={Users} title="Affinity Overlap" value={analysis.affinity_overlap_score.toFixed(1)} unit="%" description="Shared audience taste" />
            <StatCard icon={TrendingUp} title="Expansion Potential" value={expansionData?.expansion_score?.toFixed(1) ?? '--'} unit="%" description="Latent synergy score" />
            <StatCard icon={AlertTriangle} title="Culture Clashes" value={analysis.report.culture_clashes.length} description="Identified integration risks" />
            <StatCard icon={Zap} title="Growth Areas" value={analysis.report.untapped_growths.length} description="Shared passion points" />
        </div>
    </div>
  );
};

const ExecutiveSummary = ({ summary }: { summary?: string }) => {
  if (!summary) return null;
  return (
    <Card>
      <CardHeader>
        <IconHeader icon={Zap} title="Executive Summary" description="The synthesized, AI-generated overview of all strategic findings." />
      </CardHeader>
      <CardContent>
        <div className="prose prose-sm dark:prose-invert max-w-none text-muted-foreground">
          <ReactMarkdown>{summary}</ReactMarkdown>
        </div>
      </CardContent>
    </Card>
  );
};

const DeepDiveTabs = ({ report }: ReportViewProps) => {
  const analysis = report.analysis;
  if (!analysis) return null;

  const archetypes = analysis.brand_archetype_summary as { acquirer_archetype?: string; target_archetype?: string };
  const ethos = analysis.corporate_ethos_summary as { acquirer_ethos?: string; target_ethos?: string };
  const allSources = Array.from(new Map([...(analysis.search_sources || []), ...(analysis.acquirer_sources || []), ...(analysis.target_sources || []), ...(analysis.acquirer_culture_sources || []), ...(analysis.target_culture_sources || []), ...(analysis.acquirer_financial_sources || []), ...(analysis.target_financial_sources || [])].map(s => [s.url, s])).values());

  return (
    <Tabs defaultValue="audience">
      <TabsList className="grid w-full grid-cols-2 md:grid-cols-4">
        <TabsTrigger value="audience"><Users className="mr-2 h-4 w-4" />Audience</TabsTrigger>
        <TabsTrigger value="corporate"><Briefcase className="mr-2 h-4 w-4" />Corporate</TabsTrigger>
        <TabsTrigger value="financial"><BarChart3 className="mr-2 h-4 w-4" />Financial</TabsTrigger>
        <TabsTrigger value="sources"><Globe className="mr-2 h-4 w-4" />Sources</TabsTrigger>
      </TabsList>

      <TabsContent value="audience" className="mt-6 space-y-6">
        <Card>
            <CardHeader><IconHeader icon={BrainCircuit} title="Brand Archetypes" description="AI-generated brand personalities derived from underlying taste data." /></CardHeader>
            <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                    <h4 className="font-semibold text-foreground flex items-center gap-2 mb-2"><Users className="h-4 w-4" />{report.acquirer_brand}</h4>
                    <p className="text-sm text-muted-foreground whitespace-pre-wrap">{archetypes.acquirer_archetype || "N/A"}</p>
                </div>
                <div className="border-t pt-6 md:border-l md:border-t-0 md:pt-0 md:pl-6">
                    <h4 className="font-semibold text-foreground flex items-center gap-2 mb-2"><Target className="h-4 w-4" />{report.target_brand}</h4>
                    <p className="text-sm text-muted-foreground whitespace-pre-wrap">{archetypes.target_archetype || "N/A"}</p>
                </div>
            </CardContent>
        </Card>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card><CardHeader><IconHeader icon={AlertTriangle} title="Potential Culture Clashes" /></CardHeader><CardContent><Table><TableHeader><TableRow><TableHead>Topic</TableHead><TableHead>Severity</TableHead></TableRow></TableHeader><TableBody>{report.culture_clashes.map(c => <TableRow key={c.id}><TableCell className="font-medium">{c.topic}</TableCell><TableCell><SeverityBadge severity={c.severity}/></TableCell></TableRow>)}</TableBody></Table></CardContent></Card>
            <Card><CardHeader><IconHeader icon={TrendingUp} title="Untapped Growth Opportunities" /></CardHeader><CardContent><Table><TableHeader><TableRow><TableHead>Shared Affinity</TableHead><TableHead className="text-right">Impact Score</TableHead></TableRow></TableHeader><TableBody>{report.untapped_growths.map(g => <TableRow key={g.id}><TableCell className="font-medium">{g.description.match(/'([^']*)'/)?.[1]}</TableCell><TableCell className="text-right font-semibold">{g.potential_impact_score}/10</TableCell></TableRow>)}</TableBody></Table></CardContent></Card>
        </div>
      </TabsContent>

      <TabsContent value="corporate" className="mt-6 space-y-6">
        <Card><CardHeader><IconHeader icon={Info} title="Corporate Ethos Synthesis" description="A comparative summary of leadership, values, and work culture." /></CardHeader><CardContent><ReactMarkdown>{`${ethos.acquirer_ethos || ''}\n\n${ethos.target_ethos || 'Synthesis not available.'}`}</ReactMarkdown></CardContent></Card>
        <Card><CardHeader><CardTitle>Sourced Corporate Profiles</CardTitle></CardHeader><CardContent className="grid grid-cols-1 md:grid-cols-2 gap-6"><div><h4 className="font-semibold text-foreground mb-2">{report.acquirer_brand}</h4><ScrollArea className="h-48 pr-4"><ReactMarkdown>{analysis.acquirer_corporate_profile || "N/A"}</ReactMarkdown></ScrollArea></div><div className="border-t pt-6 md:border-l md:border-t-0 md:pt-0 md:pl-6"><h4 className="font-semibold text-foreground mb-2">{report.target_brand}</h4><ScrollArea className="h-48 pr-4"><ReactMarkdown>{analysis.target_corporate_profile || "N/A"}</ReactMarkdown></ScrollArea></div></CardContent></Card>
      </TabsContent>
      
      <TabsContent value="financial" className="mt-6 space-y-6">
         <Card><CardHeader><IconHeader icon={Info} title="Financial & Market Synthesis" /></CardHeader><CardContent><ReactMarkdown>{analysis.financial_synthesis || "Synthesis not available."}</ReactMarkdown></CardContent></Card>
         <Card><CardHeader><CardTitle>Sourced Financial Profiles</CardTitle></CardHeader><CardContent className="grid grid-cols-1 md:grid-cols-2 gap-6"><div><h4 className="font-semibold text-foreground mb-2">{report.acquirer_brand}</h4><ScrollArea className="h-48 pr-4"><ReactMarkdown>{analysis.acquirer_financial_profile || "N/A"}</ReactMarkdown></ScrollArea></div><div className="border-t pt-6 md:border-l md:border-t-0 md:pt-0 md:pl-6"><h4 className="font-semibold text-foreground mb-2">{report.target_brand}</h4><ScrollArea className="h-48 pr-4"><ReactMarkdown>{analysis.target_financial_profile || "N/A"}</ReactMarkdown></ScrollArea></div></CardContent></Card>
      </TabsContent>

      <TabsContent value="sources" className="mt-6">
        {allSources.length > 0 ? (
          <Card>
            <CardHeader><IconHeader icon={FileText} title="Grounding Sources" description={`The ${allSources.length} unique web sources used for analysis.`} /></CardHeader>
            <CardContent>
                <div className="flex flex-wrap gap-3">
                    {allSources.map(s => <SourcePill key={s.url} {...s} />)}
                </div>
            </CardContent>
          </Card>
        ) : <p className="text-muted-foreground text-center py-8">No external sources were used for this analysis.</p>}
      </TabsContent>

    </Tabs>
  );
};


// --- Main View & Skeleton ---

export const ReportView = ({ report, children }: ReportViewProps) => {
  const parsedReport = useParsedReport(report);

  if (parsedReport.status === "FAILED") {
    return (
      <div className="flex h-full flex-col items-center justify-center p-8 text-center">
        <XCircle className="mx-auto h-12 w-12 text-destructive" />
        <h2 className="mt-4 text-2xl font-bold">Report Generation Failed</h2>
        <p className="mt-2 max-w-md text-muted-foreground">We were unable to generate this report. This can happen due to issues with source data availability. Please try again or create a new report.</p>
      </div>
    );
  }

  return (
    <ResizablePanelGroup direction="horizontal" className="h-full max-h-[calc(100vh-8rem)] w-full rounded-none border-0 sm:rounded-lg sm:border">
      <ResizablePanel defaultSize={65} minSize={50}>
        <ScrollArea className="h-full">
          <div className="space-y-8 p-4 md:p-6">
            <ReportHeader report={parsedReport}>{children}</ReportHeader>
            <ScoreAndMetrics analysis={parsedReport.analysis} />
            <ExecutiveSummary summary={parsedReport.analysis?.strategic_summary} />
            <DeepDiveTabs report={parsedReport} />
            <div className="text-center text-xs text-muted-foreground pt-8">
              <p>Report ID: {parsedReport.id}</p>
              <p>Cultural taste data powered by <Link href="https://qloo.com" target="_blank" className="underline hover:text-foreground">Qloo, the AI for Culture and Taste</Link>.</p>
            </div>
          </div>
        </ScrollArea>
      </ResizablePanel>
      <ResizableHandle withHandle />
      <ResizablePanel defaultSize={35} minSize={25}>
        <AIAnalystChat report={parsedReport} />
      </ResizablePanel>
    </ResizablePanelGroup>
  );
};

export const ReportViewSkeleton = () => (
  <div className="h-full w-full animate-pulse p-4 md:p-6">
    <div className="space-y-8">
      <Skeleton className="h-32 w-full" />
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Skeleton className="h-48 w-full" />
        <div className="grid grid-cols-2 gap-6">
            <Skeleton className="h-20 w-full" />
            <Skeleton className="h-20 w-full" />
            <Skeleton className="h-20 w-full" />
            <Skeleton className="h-20 w-full" />
        </div>
      </div>
      <Skeleton className="h-40 w-full" />
      <Skeleton className="h-10 w-full" />
      <Skeleton className="h-64 w-full" />
    </div>
  </div>
);