"use client";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "../ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { AlertTriangle, TrendingUp, Zap, Link as LinkIcon, Globe, Users, Target, Scale, Briefcase, BarChart3, CheckCircle } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { Report, ClashSeverity } from "@/types/report";
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from "@/components/ui/resizable";
import {AIAnalystChat} from "./AIAnalystChat";
import Image from "next/image";
import Link from "next/link";
import { Bar, BarChart, ResponsiveContainer, XAxis, YAxis, Tooltip, RadialBar, RadialBarChart, PolarAngleAxis } from 'recharts';
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ChartContainer } from "../ui/chart";
import { ScrollArea } from "../ui/scroll-area";
import { Tooltip as TooltipPrimitive, TooltipContent as TooltipContentPrimitive, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import React, { useMemo } from "react";
import ReactMarkdown from "react-markdown";

interface ReportViewProps {
  report: Report;
  children?: React.ReactNode; 
}

// --- Helper Functions and Components ---
const useParsedReport = (report: Report) => {
    return useMemo(() => {
        const parsedReport = { ...report };
        if (report.analysis) {
            const mutableAnalysis = { ...report.analysis };
            const keys_to_parse = ['brand_archetype_summary', 'corporate_ethos_summary', 'persona_expansion_summary'];
            for (const key of keys_to_parse) {
                if (typeof (mutableAnalysis as any)[key] === 'string') {
                    try {
                        (mutableAnalysis as any)[key] = JSON.parse((mutableAnalysis as any)[key]);
                    } catch (e) {
                        console.error(`Failed to parse ${key}:`, (mutableAnalysis as any)[key]);
                        (mutableAnalysis as any)[key] = {};
                    }
                }
            }
            parsedReport.analysis = mutableAnalysis;
        }
        return parsedReport;
    }, [report]);
};

const CompanyLogo = ({ brandName, size = 'large' }: { brandName: string, size?: 'large' | 'small' }) => {
    const faviconUrl = `/api/v1/utils/favicon?brandName=${encodeURIComponent(brandName)}`;
    const config = {
        large: { dim: 40, text: 'text-xl', padding: 'p-1', gap: 'gap-3' },
        small: { dim: 24, text: 'text-base', padding: 'p-0.5', gap: 'gap-2' },
    }[size];

    return (
        <div className={cn("flex items-center", config.gap)}>
            <Image src={faviconUrl} alt={`${brandName} logo`} width={config.dim} height={config.dim} className={cn("rounded-lg border bg-background", config.padding)} unoptimized priority={false}/>
            <span className={cn("font-semibold", config.text)}>{brandName}</span>
        </div>
    );
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

const SourcePill = ({ url }: { url: string }) => {
    try {
        const domain = new URL(url).hostname?.replace('www.', '');
        const faviconUrl = `/api/v1/utils/favicon?url=${encodeURIComponent(url)}`;
        return (
            <Link href={url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-2 rounded-full border bg-secondary/50 px-3 py-1 text-sm text-secondary-foreground transition-colors hover:bg-secondary">
                <Image src={faviconUrl} alt={`${domain} favicon`} width={16} height={16} className="rounded-full" unoptimized/>
                {domain}
            </Link>
        )
    } catch (error) {
        return <Link href={url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-2 rounded-full border bg-secondary/50 px-3 py-1 text-sm text-secondary-foreground transition-colors hover:bg-secondary"><LinkIcon className="h-4 w-4" />{url}</Link>
    }
}

const DimensionItem = ({ text, icon: Icon, colorClass, tooltipContent }: { text: string; icon: React.ElementType; colorClass: string; tooltipContent: string; }) => (
    <TooltipProvider>
        <TooltipPrimitive>
            <TooltipTrigger asChild>
                <div className="flex items-start gap-3 p-2 rounded-md transition-colors hover:bg-muted/50 w-full text-left">
                    <div className={cn("flex-shrink-0 mt-1 w-4 h-4 flex items-center justify-center rounded-full", colorClass)}>
                        <Icon className="h-2.5 w-2.5 text-white" />
                    </div>
                    <p className="text-sm text-foreground truncate">{text}</p>
                </div>
            </TooltipTrigger>
            <TooltipContentPrimitive side="top" align="start" className="max-w-xs">
                <p>{tooltipContent}</p>
            </TooltipContentPrimitive>
        </TooltipPrimitive>
    </TooltipProvider>
);

const CulturalDimensionsVisual = ({ report }: { report: Report }) => {
    const acquirerUnique = report.culture_clashes.filter(c => c.description.includes("Acquirer"));
    const targetUnique = report.culture_clashes.filter(c => c.description.includes("Target"));
    const shared = report.untapped_growths;

    const columnHeaderClasses = "font-semibold text-foreground flex items-center gap-2 mb-3";

    return (
        <Card>
            <CardHeader>
                <CardTitle className="flex items-center gap-2"><Users /> Cultural Taste Dimensions</CardTitle>
                <CardDescription>A breakdown of unique and shared affinities between the two brand audiences.</CardDescription>
            </CardHeader>
            <CardContent className="grid md:grid-cols-3 gap-px bg-border border rounded-lg overflow-hidden">
                <div className="p-4 bg-card"><div className={columnHeaderClasses}><CompanyLogo brandName={report.acquirer_brand} size="small"/><span>Unique</span></div>
                    <ScrollArea className="h-64 pr-3"><div className="space-y-1">
                        {acquirerUnique.length > 0 ? acquirerUnique.map(clash => (<DimensionItem key={clash.id} text={clash.topic} icon={AlertTriangle} colorClass="bg-blue-500" tooltipContent={clash.description}/>)) : <p className="text-sm text-muted-foreground p-2">No unique tastes identified.</p>}
                    </div></ScrollArea>
                </div>
                <div className="p-4 bg-card"><div className={columnHeaderClasses}><Zap className="text-green-500" /><span>Shared Affinities</span></div>
                    <ScrollArea className="h-64 pr-3"><div className="space-y-1">
                        {shared.length > 0 ? shared.map(growth => (<DimensionItem key={growth.id} text={growth.description.match(/'([^']*)'/)?.[1] || "Growth Opportunity"} icon={TrendingUp} colorClass="bg-green-500" tooltipContent={growth.description}/>)) : <p className="text-sm text-muted-foreground p-2">No shared affinities identified.</p>}
                    </div></ScrollArea>
                </div>
                <div className="p-4 bg-card"><div className={columnHeaderClasses}><CompanyLogo brandName={report.target_brand} size="small"/><span>Unique</span></div>
                    <ScrollArea className="h-64 pr-3"><div className="space-y-1">
                        {targetUnique.length > 0 ? targetUnique.map(clash => (<DimensionItem key={clash.id} text={clash.topic} icon={AlertTriangle} colorClass="bg-purple-500" tooltipContent={clash.description}/>)) : <p className="text-sm text-muted-foreground p-2">No unique tastes identified.</p>}
                    </div></ScrollArea>
                </div>
            </CardContent>
        </Card>
    );
};


// --- Main View Sections ---

const ReportHeader = ({ report, children }: { report: Report, children?: React.ReactNode }) => (
    <div className="space-y-4">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <CompanyLogo brandName={report.acquirer_brand} />
            <span className="h-8 w-8 text-muted-foreground flex-shrink-0">
                ACQUIRING
            </span>
            <CompanyLogo brandName={report.target_brand} />
        </div>
        <Card>
            <CardHeader className='flex-row items-center justify-between'>
                <div>
                    <CardTitle className="text-3xl">{report.title}</CardTitle>
                    <CardDescription>Cultural due diligence report generated on {new Date(report.created_at).toLocaleString()}.</CardDescription>
                </div>
                <div className="flex-shrink-0">{children}</div>
            </CardHeader>
        </Card>
    </div>
);

const ScoreAndArchetypes = ({ report }: { report: Report }) => {
    const analysis = report.analysis;
    if (!analysis) return null;

    const archetypes = (analysis.brand_archetype_summary || {}) as { acquirer_archetype?: string, target_archetype?: string };
    const chartData = [{ name: 'Score', value: analysis.cultural_compatibility_score, fill: 'hsl(var(--primary))' }];
    
    return (
        <div className="grid md:grid-cols-2 gap-6">
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2"><Scale />Cultural Compatibility Score</CardTitle>
                    <CardDescription>Overall alignment based on audience taste.</CardDescription>
                </CardHeader>
                <CardContent className="flex items-center justify-center">
                    <ChartContainer config={{}} className="mx-auto aspect-square h-[200px] w-[200px]">
                        <RadialBarChart
                            data={chartData} 
                            cx="50%"
                            cy="50%"
                            startAngle={90} 
                            endAngle={-270} 
                            innerRadius="80%" 
                            outerRadius="100%" 
                            barSize={30}
                        >
                            <PolarAngleAxis type="number" domain={[0, 100]} tick={false} />
                            <RadialBar dataKey="value" background={{ fill: 'hsl(var(--muted))' }} cornerRadius={15} />
                            <text x="50%" y="50%" textAnchor="middle" dominantBaseline="middle" className="fill-foreground text-5xl font-bold">
                                {analysis.cultural_compatibility_score.toFixed(0)}
                            </text>
                            <text x="50%" y="65%" textAnchor="middle" dominantBaseline="middle" className="fill-muted-foreground text-sm">
                                / 100
                            </text>
                        </RadialBarChart>
                    </ChartContainer>
                </CardContent>
            </Card>
            <Card>
                <CardHeader>
                    <CardTitle>Brand Archetypes</CardTitle>
                    <CardDescription>AI-generated personalities from taste data.</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4 h-[200px] overflow-y-auto">
                    <div>
                        <h3 className="font-semibold text-foreground flex items-center gap-2"><Users className="h-4 w-4" />{report.acquirer_brand}</h3>
                        <p className="text-muted-foreground text-sm whitespace-pre-wrap">{archetypes.acquirer_archetype || "Analysis not available."}</p>
                    </div>
                    <Separator />
                    <div>
                        <h3 className="font-semibold text-foreground flex items-center gap-2"><Target className="h-4 w-4" />{report.target_brand}</h3>
                        <p className="text-muted-foreground text-sm whitespace-pre-wrap">{archetypes.target_archetype || "Analysis not available."}</p>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
};

const AffinityAnalysis = ({ report }: { report: Report }) => {
    if (!report.analysis) return null
    const shared = report.untapped_growths.slice(0, 5).map(g => ({ name: g.description.match(/'([^']*)'/)?.[1] || g.description.substring(0,20), score: g.potential_impact_score * 10 }));
    const acquirer_unique = report.culture_clashes.filter(c => c.description.includes("Acquirer")).slice(0, 5).map(c => ({ name: c.topic, score: 75 }));
    const target_unique = report.culture_clashes.filter(c => c.description.includes("Target")).slice(0, 5).map(c => ({ name: c.topic, score: 75 }));;

    const chartData = [
        { name: report.acquirer_brand, value: acquirer_unique.length, fill: '#3b82f6' },
        { name: 'Shared Affinity', value: shared.length, fill: 'hsl(var(--primary))' },
        { name: report.target_brand, value: target_unique.length, fill: '#8b5cf6' },
    ];

    return (
        <div className="space-y-6">
            <Card>
                <CardHeader>
                    <div className="flex justify-between items-start">
                        <div>
                            <CardTitle>Affinity Overlap</CardTitle>
                            <CardDescription>Number of distinct vs. shared cultural markers identified.</CardDescription>
                        </div>
                        <div className="text-right"><div className="text-2xl font-bold">{report.analysis.affinity_overlap_score.toFixed(1)}%</div><div className="text-xs text-muted-foreground">Taste Overlap</div></div>
                    </div>
                </CardHeader>
                <CardContent className="h-[250px]">
                    <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={chartData} layout="vertical" barCategoryGap="20%">
                            <XAxis type="number" hide />
                            <YAxis type="category" dataKey="name" hide />
                            <Tooltip cursor={{ fill: 'transparent' }} contentStyle={{backgroundColor: 'hsl(var(--background))', border: '1px solid hsl(var(--border))', borderRadius: 'var(--radius)'}}/>
                            <Bar dataKey="value" radius={5}>
                                {chartData.map((entry, index) => (
                                    <text
                                        key={`label-${index}`}
                                        x={10}
                                        y={index * (250 / chartData.length) + (250 / chartData.length) / 2}
                                        dy={5}
                                        fill="white"
                                        className="text-sm font-medium"
                                    >
                                        {entry.name}
                                    </text>
                                ))}
                            </Bar>
                        </BarChart>
                    </ResponsiveContainer>
                </CardContent>
            </Card>
            <CulturalDimensionsVisual report={report} />
        </div>
    );
};

const CorporateCultureAnalysis = ({ report }: { report: Report }) => {
    const analysis = report.analysis;
    if (!analysis || (!analysis.acquirer_corporate_profile && !analysis.target_corporate_profile)) {
        return <div className="text-center py-8 text-muted-foreground">No corporate culture analysis was performed for this report.</div>;
    }

    const ethos = (analysis.corporate_ethos_summary || {}) as { acquirer_ethos?: string, target_ethos?: string };

    return (
        <div className="space-y-6">
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2"><Briefcase /> Corporate Ethos Synthesis</CardTitle>
                    <CardDescription>A comparative analysis of leadership, values, and work culture.</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                    <div>
                        <h3 className="font-semibold text-foreground flex items-center gap-2"><Users className="h-4 w-4" />{report.acquirer_brand}</h3>
                        <p className="text-muted-foreground text-sm whitespace-pre-wrap">{ethos.acquirer_ethos || "Analysis not available."}</p>
                    </div>
                    <Separator />
                    <div>
                        <h3 className="font-semibold text-foreground flex items-center gap-2"><Target className="h-4 w-4" />{report.target_brand}</h3>
                        <p className="text-muted-foreground text-sm whitespace-pre-wrap">{ethos.target_ethos || "Analysis not available."}</p>
                    </div>
                </CardContent>
            </Card>

            <div className="grid md:grid-cols-2 gap-6">
                <Card>
                    <CardHeader>
                        <CardTitle>Acquirer Culture Profile</CardTitle>
                        <CardDescription>Raw intelligence gathered on {report.acquirer_brand}.</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <ScrollArea className="h-48">
                            {/* --- THE FIX IS HERE --- */}
                            <div className="prose prose-sm dark:prose-invert max-w-none text-muted-foreground">
                                <ReactMarkdown>{analysis.acquirer_corporate_profile || "No data found."}</ReactMarkdown>
                            </div>
                        </ScrollArea>
                        {analysis.acquirer_culture_sources && analysis.acquirer_culture_sources.length > 0 && <div><h4 className="text-xs font-semibold uppercase text-muted-foreground mb-2">Sources</h4><div className="flex flex-wrap gap-2">{analysis.acquirer_culture_sources.map(s => <SourcePill key={s.url} url={s.url} />)}</div></div>}
                    </CardContent>
                </Card>
                 <Card>
                    <CardHeader>
                        <CardTitle>Target Culture Profile</CardTitle>
                        <CardDescription>Raw intelligence gathered on {report.target_brand}.</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <ScrollArea className="h-48">
                            {/* --- THE FIX IS HERE --- */}
                             <div className="prose prose-sm dark:prose-invert max-w-none text-muted-foreground">
                                <ReactMarkdown>{analysis.target_corporate_profile || "No data found."}</ReactMarkdown>
                            </div>
                        </ScrollArea>
                        {analysis.target_culture_sources && analysis.target_culture_sources.length > 0 && <div><h4 className="text-xs font-semibold uppercase text-muted-foreground mb-2">Sources</h4><div className="flex flex-wrap gap-2">{analysis.target_culture_sources.map(s => <SourcePill key={s.url} url={s.url} />)}</div></div>}
                    </CardContent>
                </Card>
            </div>
        </div>
    );
};

const FinancialAnalysis = ({ report }: { report: Report }) => {
    const analysis = report.analysis;
    if (!analysis || (!analysis.acquirer_financial_profile && !analysis.target_financial_profile)) {
        return <div className="text-center py-8 text-muted-foreground">No financial & market analysis was performed for this report.</div>;
    }

    return (
        <div className="space-y-6">
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2"><BarChart3 /> Financial & Market Synthesis</CardTitle>
                    <CardDescription>A comparative summary of financial health and market positioning.</CardDescription>
                </CardHeader>
                <CardContent>
                    <p className="text-muted-foreground text-sm whitespace-pre-wrap">{analysis.financial_synthesis || "Analysis not available."}</p>
                </CardContent>
            </Card>

            <div className="grid md:grid-cols-2 gap-6">
                <Card>
                    <CardHeader>
                        <CardTitle>Acquirer Financial Profile</CardTitle>
                        <CardDescription>Raw intelligence gathered on {report.acquirer_brand}.</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <ScrollArea className="h-48">
                            {/* --- THE FIX IS HERE --- */}
                             <div className="prose prose-sm dark:prose-invert max-w-none text-muted-foreground">
                                <ReactMarkdown>{analysis.acquirer_financial_profile || "No data found."}</ReactMarkdown>
                            </div>
                        </ScrollArea>
                        {analysis.acquirer_financial_sources && analysis.acquirer_financial_sources.length > 0 && <div><h4 className="text-xs font-semibold uppercase text-muted-foreground mb-2">Sources</h4><div className="flex flex-wrap gap-2">{analysis.acquirer_financial_sources.map(s => <SourcePill key={s.url} url={s.url} />)}</div></div>}
                    </CardContent>
                </Card>
                 <Card>
                    <CardHeader>
                        <CardTitle>Target Financial Profile</CardTitle>
                        <CardDescription>Raw intelligence gathered on {report.target_brand}.</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <ScrollArea className="h-48">
                           {/* --- THE FIX IS HERE --- */}
                            <div className="text-sm text-muted-foreground whitespace-pre-wrap prose prose-sm dark:prose-invert prose-p:my-2">
                                <ReactMarkdown>{analysis.target_financial_profile || "No data found."}</ReactMarkdown>
                            </div>
                        </ScrollArea>
                        {analysis.target_financial_sources && analysis.target_financial_sources.length > 0 && <div><h4 className="text-xs font-semibold uppercase text-muted-foreground mb-2">Sources</h4><div className="flex flex-wrap gap-2">{analysis.target_financial_sources.map(s => <SourcePill key={s.url} url={s.url} />)}</div></div>}
                    </CardContent>
                </Card>
            </div>
        </div>
    );
};

const ExpansionPotentialCard = ({ report }: { report: Report }) => {
    if (!report.analysis?.persona_expansion_summary) return null;

    const expansionData = report.analysis.persona_expansion_summary as { expansion_score: number; latent_synergies: string[]; analysis: string };

    if (!expansionData || expansionData.expansion_score === undefined) return null;

    return (
        <Card>
            <CardHeader>
                <CardTitle className="flex items-center gap-2"><Zap className="text-yellow-400"/>Audience Expansion Potential</CardTitle>
                <CardDescription>Predicted synergies based on Qloo's Persona API, revealing latent growth opportunities.</CardDescription>
            </CardHeader>
            <CardContent className="grid md:grid-cols-2 gap-6 items-center">
                <div className="flex flex-col items-center justify-center">
                    <div className="text-6xl font-bold text-yellow-400">{expansionData.expansion_score.toFixed(1)}%</div>
                    <div className="text-sm font-medium text-muted-foreground mt-1">Latent Synergy Score</div>
                </div>
                <div>
                    <h4 className="font-semibold mb-2">Top Predicted Affinities</h4>
                    <p className="text-sm text-muted-foreground mb-3">{expansionData.analysis}</p>
                    <div className="space-y-2">
                        {expansionData.latent_synergies.map(item => (
                            <div key={item} className="flex items-center gap-2 text-xs text-foreground">
                                <CheckCircle className="h-3 w-3 text-green-500" />
                                {item}
                            </div>
                        ))}
                    </div>
                </div>
            </CardContent>
        </Card>
    );
}

export const ReportView = ({ report, children }: ReportViewProps) => {
    const parsedReport = useParsedReport(report);

    if (parsedReport.status === "FAILED") {
        return <div className="flex h-full items-center justify-center p-8 text-center">
            <div>
                <AlertTriangle className="mx-auto h-12 w-12 text-destructive" />
                <h2 className="mt-4 text-2xl font-bold">Report Generation Failed</h2>
                <p className="mt-2 text-muted-foreground">We were unable to generate this report. This can happen due to issues with source data availability. Please try again or create a new report with different brands.</p>
            </div>
        </div>
    }

    const allSources = [
        ...(parsedReport.analysis?.acquirer_sources || []),
        ...(parsedReport.analysis?.target_sources || []),
        ...(parsedReport.analysis?.search_sources || []),
        ...(parsedReport.analysis?.acquirer_culture_sources || []),
        ...(parsedReport.analysis?.target_culture_sources || []),
        ...(parsedReport.analysis?.acquirer_financial_sources || []),
        ...(parsedReport.analysis?.target_financial_sources || []),
    ];
    const uniqueSources = Array.from(new Set(allSources.map(s => s.url))).map(url => allSources.find(s => s.url === url)!);


    return (
        <ResizablePanelGroup direction="horizontal" className="h-full max-h-[calc(100vh-8rem)] w-full rounded-none border-0 sm:rounded-lg sm:border">
            <ResizablePanel defaultSize={65} minSize={50}>
                <ScrollArea className="h-full p-4 md:p-6">
                    <div className="space-y-6">
                        <ReportHeader report={parsedReport} children={children} />
                        <ScoreAndArchetypes report={parsedReport} />
                        <ExpansionPotentialCard report={parsedReport} />

                        <Tabs defaultValue="affinity">
                            <TabsList>
                                <TabsTrigger value="affinity">Audience Affinity</TabsTrigger>
                                <TabsTrigger value="corporate">Corporate Culture</TabsTrigger>
                                <TabsTrigger value="financial">Financial & Market</TabsTrigger>
                                <TabsTrigger value="sources">Sources</TabsTrigger>
                            </TabsList>
                            <TabsContent value="affinity" className="mt-4">
                                <AffinityAnalysis report={parsedReport} />
                            </TabsContent>
                            <TabsContent value="corporate" className="mt-4">
                                <CorporateCultureAnalysis report={parsedReport} />
                            </TabsContent>
                            <TabsContent value="financial" className="mt-4">
                                <FinancialAnalysis report={parsedReport} />
                            </TabsContent>
                             <TabsContent value="sources" className="mt-4">
                                 {uniqueSources.length > 0 ? (
                                    <Card>
                                        <CardHeader><CardTitle className="flex items-center gap-2"><Globe className="h-5 w-5 text-blue-500" />Grounding Sources</CardTitle><CardDescription>Web sources used for analysis.</CardDescription></CardHeader>
                                        <CardContent>
                                            <div className="columns-1 md:columns-2 lg:columns-3 gap-4 space-y-2">
                                                {uniqueSources.map(source => <SourcePill key={source.url} url={source.url} />)}
                                            </div>
                                        </CardContent>
                                    </Card>
                                  ) : <p className="text-muted-foreground text-center py-8">No external sources were used for this analysis.</p>}
                             </TabsContent>
                        </Tabs>
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


export const ReportViewSkeleton = () => {
  return (
    <div className="h-full w-full animate-pulse p-6 space-y-6">
      <div className="flex justify-between items-center"><Skeleton className="h-10 w-48" /><Skeleton className="h-10 w-48" /></div>
      <Skeleton className="h-24 w-full" />
      <div className="grid md:grid-cols-2 gap-6">
        <Skeleton className="h-64 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
      <Skeleton className="h-10 w-64" />
      <Skeleton className="h-80 w-full" />
    </div>
  );
};