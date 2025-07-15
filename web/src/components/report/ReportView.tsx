"use client";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { AlertTriangle, TrendingUp, Zap, Link as LinkIcon, Globe, Users, Target, Scaling, Trophy } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { Report, ClashSeverity } from "@/types/report";
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from "@/components/ui/resizable";
import { AIAnalystChat } from "./AIAnalystChat";
import Image from "next/image";
import Link from "next/link";
import { Bar, BarChart, ResponsiveContainer, XAxis, YAxis, Tooltip, RadialBar, RadialBarChart, Legend } from 'recharts';
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../ui/tabs";
import { ChartContainer, ChartTooltipContent } from "../ui/chart";
import { ScrollArea } from "../ui/scroll-area";

interface ReportViewProps {
  report: Report;
}

// --- Helper Components ---

const CompanyLogo = ({ url, brandName }: { url: string; brandName: string }) => {
    const API_URL = process.env.NEXT_PUBLIC_API_URL;
    const faviconUrl = `${API_URL}/utils/favicon?url=${encodeURIComponent(url)}`;
    return (
        <div className="flex items-center gap-3">
            <Image src={faviconUrl} alt={`${brandName} logo`} width={40} height={40} className="rounded-lg border bg-background p-1" unoptimized/>
            <span className="text-xl font-semibold">{brandName}</span>
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
        const domain = new URL(url).hostname.replace('www.', '');
        const faviconUrl = `https://satori-rho.vercel.app/api/image?url=${url}`;
        return (
            <Link href={url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-2 rounded-full border bg-secondary/50 px-3 py-1 text-sm text-secondary-foreground transition-colors hover:bg-secondary">
                <Image src={faviconUrl} alt={`${domain} favicon`} width={16} height={16} className="rounded-full" />
                {domain}
            </Link>
        )
    } catch (error) {
        return <Link href={url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-2 rounded-full border bg-secondary/50 px-3 py-1 text-sm text-secondary-foreground transition-colors hover:bg-secondary"><LinkIcon className="h-4 w-4" />{url}</Link>
    }
}

// --- Main View Sections ---

const ReportHeader = ({ report }: { report: Report }) => (
    <div className="space-y-4">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <CompanyLogo url={report.acquirer_brand} brandName={report.acquirer_brand} />
            <Zap className="h-8 w-8 text-muted-foreground flex-shrink-0" />
            <CompanyLogo url={report.target_brand} brandName={report.target_brand} />
        </div>
        <Card>
            <CardHeader>
                <CardTitle className="text-3xl">{report.title}</CardTitle>
                <CardDescription>Cultural due diligence report generated on {new Date(report.created_at).toLocaleString()}.</CardDescription>
            </CardHeader>
        </Card>
    </div>
);

const ScoreAndArchetypes = ({ report }: { report: Report }) => {
    const analysis = report.analysis;
    if (!analysis) return null;

    const archetypes = JSON.parse(analysis.brand_archetype_summary || '{}');
    const chartData = [{ name: 'Score', value: analysis.cultural_compatibility_score, fill: 'hsl(var(--primary))' }];
    
    return (
        <div className="grid md:grid-cols-2 gap-6">
            <Card>
                <CardHeader>
                    <CardTitle>Cultural Compatibility Score</CardTitle>
                    <CardDescription>Overall alignment based on audience taste.</CardDescription>
                </CardHeader>
                <CardContent>
                    <ChartContainer config={{}} className="mx-auto aspect-square h-[250px]">
                        <RadialBarChart 
                            data={chartData} 
                            startAngle={-270} 
                            endAngle={90} 
                            innerRadius="70%" 
                            outerRadius="100%" 
                            barSize={30}
                        >
                            <RadialBar dataKey="value" background={{ fill: 'hsl(var(--muted))' }} cornerRadius={15} />
                            <text x="50%" y="50%" textAnchor="middle" dominantBaseline="middle" className="fill-foreground text-5xl font-bold">
                                {analysis.cultural_compatibility_score}
                            </text>
                            <text x="50%" y="65%" textAnchor="middle" dominantBaseline="middle" className="fill-muted-foreground text-sm">
                                out of 100
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
                <CardContent className="space-y-4 h-[250px] overflow-y-auto">
                    <div>
                        <h3 className="font-semibold text-foreground flex items-center gap-2"><Users className="h-4 w-4" />{report.acquirer_brand}</h3>
                        <p className="text-muted-foreground text-sm whitespace-pre-wrap">{archetypes.acquirer_archetype}</p>
                    </div>
                    <Separator />
                    <div>
                        <h3 className="font-semibold text-foreground flex items-center gap-2"><Target className="h-4 w-4" />{report.target_brand}</h3>
                        <p className="text-muted-foreground text-sm whitespace-pre-wrap">{archetypes.target_archetype}</p>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
};

const TasteAnalysisCharts = ({ report }: { report: Report }) => {
    const shared = report.untapped_growths.slice(0, 5).map(g => ({ name: g.description.match(/'([^']*)'/)?.[1] || g.description.substring(0,20), score: g.potential_impact_score * 10 }));
    const acquirer_unique = report.culture_clashes.filter(c => c.description.includes("Acquirer")).slice(0, 5).map(c => ({ name: c.topic, score: 75 }));
    const target_unique = report.culture_clashes.filter(c => c.description.includes("Target")).slice(0, 5).map(c => ({ name: c.topic, score: 75 }));

    const CustomTooltip = ({ active, payload, label }: any) => {
        if (active && payload && payload.length) {
            return (
                <div className="rounded-lg border bg-background p-2 shadow-sm">
                    <p className="text-sm font-bold">{label}</p>
                </div>
            );
        }
        return null;
    };
    
    return (
        <div className="grid md:grid-cols-1 lg:grid-cols-3 gap-6">
            <Card className="lg:col-span-1">
                <CardHeader>
                    <CardTitle className="flex items-center gap-2"><Trophy className="h-5 w-5 text-amber-500" />Top Shared Affinities</CardTitle>
                </CardHeader>
                <CardContent>
                    <ResponsiveContainer width="100%" height={250}>
                        <BarChart data={shared} layout="vertical" margin={{ left: 20, right: 10 }}>
                            <XAxis type="number" hide />
                            <YAxis type="category" dataKey="name" width={100} stroke="hsl(var(--muted-foreground))" fontSize={12} tickLine={false} axisLine={false} />
                            <Tooltip content={<CustomTooltip />} cursor={{ fill: 'hsl(var(--muted))' }} />
                            <Bar dataKey="score" fill="hsl(var(--primary))" radius={[0, 4, 4, 0]} />
                        </BarChart>
                    </ResponsiveContainer>
                </CardContent>
            </Card>
            <Card className="lg:col-span-1">
                <CardHeader><CardTitle className="flex items-center gap-2"><Users className="h-5 w-5" />{report.acquirer_brand}'s DNA</CardTitle></CardHeader>
                <CardContent>
                     <ResponsiveContainer width="100%" height={250}>
                        <BarChart data={acquirer_unique} layout="vertical" margin={{ left: 20, right: 10 }}>
                            <XAxis type="number" hide />
                            <YAxis type="category" dataKey="name" width={100} stroke="hsl(var(--muted-foreground))" fontSize={12} tickLine={false} axisLine={false} />
                            <Tooltip content={<CustomTooltip />} cursor={{ fill: 'hsl(var(--muted))' }} />
                            <Bar dataKey="score" fill="#3b82f6" radius={[0, 4, 4, 0]} />
                        </BarChart>
                    </ResponsiveContainer>
                </CardContent>
            </Card>
            <Card className="lg:col-span-1">
                <CardHeader><CardTitle className="flex items-center gap-2"><Target className="h-5 w-5" />{report.target_brand}'s DNA</CardTitle></CardHeader>
                <CardContent>
                    <ResponsiveContainer width="100%" height={250}>
                        <BarChart data={target_unique} layout="vertical" margin={{ left: 20, right: 10 }}>
                            <XAxis type="number" hide />
                            <YAxis type="category" dataKey="name" width={100} stroke="hsl(var(--muted-foreground))" fontSize={12} tickLine={false} axisLine={false} />
                            <Tooltip content={<CustomTooltip />} cursor={{ fill: 'hsl(var(--muted))' }} />
                            <Bar dataKey="score" fill="#8b5cf6" radius={[0, 4, 4, 0]} />
                        </BarChart>
                    </ResponsiveContainer>
                </CardContent>
            </Card>
        </div>
    );
};

export const ReportView = ({ report }: ReportViewProps) => {
    return (
        <ResizablePanelGroup direction="horizontal" className="h-full max-h-[calc(100vh-8rem)] w-full rounded-lg border">
            <ResizablePanel defaultSize={65}>
                <ScrollArea className="h-full p-4 md:p-6">
                    <div className="space-y-6">
                        <ReportHeader report={report} />
                        <ScoreAndArchetypes report={report} />

                        <Tabs defaultValue="affinity">
                            <TabsList>
                                <TabsTrigger value="affinity">Affinity Analysis</TabsTrigger>
                                <TabsTrigger value="clashes">Culture Clashes</TabsTrigger>
                                <TabsTrigger value="growth">Growth Opportunities</TabsTrigger>
                                <TabsTrigger value="sources">Sources</TabsTrigger>
                            </TabsList>
                            <TabsContent value="affinity" className="mt-4">
                                <TasteAnalysisCharts report={report} />
                            </TabsContent>
                            <TabsContent value="clashes" className="mt-4">
                                <Card>
                                    <CardHeader><CardTitle className="flex items-center gap-2"><AlertTriangle className="h-5 w-5 text-red-500" />Potential Culture Clashes</CardTitle><CardDescription>Divergent audience tastes that could pose integration risks.</CardDescription></CardHeader>
                                    <CardContent>
                                        <Table><TableHeader><TableRow><TableHead>Clash Topic</TableHead><TableHead>Description</TableHead><TableHead className="text-right">Severity</TableHead></TableRow></TableHeader><TableBody>{report.culture_clashes.map((c) => (<TableRow key={c.id}><TableCell className="font-semibold">{c.topic}</TableCell><TableCell className="text-muted-foreground whitespace-normal">{c.description}</TableCell><TableCell className="text-right"><SeverityBadge severity={c.severity} /></TableCell></TableRow>))}</TableBody></Table>
                                    </CardContent>
                                </Card>
                            </TabsContent>
                            <TabsContent value="growth" className="mt-4">
                                <Card>
                                    <CardHeader><CardTitle className="flex items-center gap-2"><TrendingUp className="h-5 w-5 text-green-500" />Untapped Growth Opportunities</CardTitle><CardDescription>Shared affinities that represent strategic pillars for post-acquisition integration.</CardDescription></CardHeader>
                                    <CardContent>
                                        <Table><TableHeader><TableRow><TableHead>Opportunity</TableHead><TableHead className="text-right">Impact</TableHead></TableRow></TableHeader><TableBody>{report.untapped_growths.map((g) => (<TableRow key={g.id}><TableCell className="font-medium whitespace-normal">{g.description}</TableCell><TableCell className="text-right font-bold text-green-600 dark:text-green-400">{g.potential_impact_score}/10</TableCell></TableRow>))}</TableBody></Table>
                                    </CardContent>
                                </Card>
                            </TabsContent>
                             <TabsContent value="sources" className="mt-4">
                                 {report.analysis?.search_sources && report.analysis.search_sources.length > 0 ? (
                                    <Card>
                                        <CardHeader><CardTitle className="flex items-center gap-2"><Globe className="h-5 w-5 text-blue-500" />Grounding Sources</CardTitle><CardDescription>Web sources used for analysis.</CardDescription></CardHeader>
                                        <CardContent className="flex flex-wrap gap-2">
                                            {report.analysis.search_sources.map(source => <SourcePill key={source.url} url={source.url} />)}
                                        </CardContent>
                                    </Card>
                                 ) : <p className="text-muted-foreground text-center py-8">No external sources were used for this analysis.</p>}
                            </TabsContent>
                        </Tabs>
                    </div>
                </ScrollArea>
            </ResizablePanel>
            <ResizableHandle withHandle />
            <ResizablePanel defaultSize={35} minSize={25}>
                <AIAnalystChat report={report} />
            </ResizablePanel>
        </ResizablePanelGroup>
    );
};


export const ReportViewSkeleton = () => {
  return (
    <div className="h-full max-h-[calc(100vh-8rem)] w-full animate-pulse p-6 space-y-6">
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