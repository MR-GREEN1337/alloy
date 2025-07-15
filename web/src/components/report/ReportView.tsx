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
import { AlertTriangle, TrendingUp, Zap } from "lucide-react";
import {
  ChartConfig,
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from "@/components/ui/chart"
import { Bar, BarChart, CartesianGrid, XAxis, YAxis, Legend } from "recharts"
import { Skeleton } from "@/components/ui/skeleton";
import { Report, ClashSeverity, ReportAnalysis, CultureClash, UntappedGrowth } from "@/types/report";

// --- Type Definitions ---
interface ReportViewProps {
  report: Report;
}

// --- Severity Badge Component ---
const SeverityBadge = ({ severity }: { severity: ClashSeverity }) => {
  const config = {
    HIGH: { text: "High", className: "bg-red-200 text-red-800 border-red-300 dark:bg-red-900/50 dark:text-red-300 dark:border-red-700" },
    MEDIUM: { text: "Medium", className: "bg-yellow-200 text-yellow-800 border-yellow-300 dark:bg-yellow-900/50 dark:text-yellow-300 dark:border-yellow-700" },
    LOW: { text: "Low", className: "bg-blue-200 text-blue-800 border-blue-300 dark:bg-blue-900/50 dark:text-blue-300 dark:border-blue-700" },
  };
  const { text, className } = config[severity] || config.LOW;
  return <Badge className={`font-semibold ${className}`}>{text}</Badge>;
};

// --- Main Report View Component ---
export const ReportView = ({ report }: ReportViewProps) => {
    const analysis = report.analysis;
    const archetypes = analysis ? JSON.parse(analysis.brand_archetype_summary) : {};
    
    const chartData = [
        { brand: report.acquirer_brand, score: analysis?.cultural_compatibility_score ?? 0, fill: "var(--color-acquirer)" },
        { brand: report.target_brand, score: analysis?.cultural_compatibility_score ?? 0, fill: "var(--color-target)" },
    ];

    const chartConfig = {
        score: { label: "Score" },
        [report.acquirer_brand]: { label: report.acquirer_brand, color: "hsl(var(--chart-1))" },
        [report.target_brand]: { label: report.target_brand, color: "hsl(var(--chart-2))" },
    } satisfies ChartConfig

    return (
        <div className="container mx-auto py-6 space-y-6">
            {/* --- Header --- */}
            <Card>
                <CardHeader>
                    <CardTitle className="text-3xl">{report.title}</CardTitle>
                    <CardDescription>
                        Cultural due diligence report generated on {new Date(report.created_at).toLocaleString()}.
                    </CardDescription>
                </CardHeader>
            </Card>
            
            <div className="grid md:grid-cols-3 gap-6">
                {/* --- Main Analysis Column --- */}
                <div className="md:col-span-2 space-y-6">
                    <Card>
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2"><Zap className="h-5 w-5 text-primary" />Strategic Summary</CardTitle>
                        </CardHeader>
                        <CardContent>
                            <p className="text-muted-foreground whitespace-pre-wrap">{analysis?.strategic_summary}</p>
                        </CardContent>
                    </Card>

                    <Card>
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2"><TrendingUp className="h-5 w-5 text-green-500" />Untapped Growth Opportunities</CardTitle>
                             <CardDescription>Shared affinities that represent strategic pillars for post-acquisition integration.</CardDescription>
                        </CardHeader>
                        <CardContent>
                            <Table>
                                <TableHeader>
                                    <TableRow>
                                        <TableHead>Opportunity Description</TableHead>
                                        <TableHead className="text-right">Potential Impact</TableHead>
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    {report.untapped_growths.map((growth) => (
                                        <TableRow key={growth.id}>
                                            <TableCell className="font-medium whitespace-normal">{growth.description}</TableCell>
                                            <TableCell className="text-right font-bold text-green-600 dark:text-green-400">{growth.potential_impact_score}/10</TableCell>
                                        </TableRow>
                                    ))}
                                </TableBody>
                            </Table>
                        </CardContent>
                    </Card>

                     <Card>
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2"><AlertTriangle className="h-5 w-5 text-red-500" />Potential Culture Clashes</CardTitle>
                            <CardDescription>Divergent audience tastes that could pose integration risks.</CardDescription>
                        </CardHeader>
                        <CardContent>
                             <Table>
                                <TableHeader>
                                    <TableRow>
                                        <TableHead>Clash Topic</TableHead>
                                        <TableHead>Description</TableHead>
                                        <TableHead className="text-right">Severity</TableHead>
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    {report.culture_clashes.map((clash) => (
                                        <TableRow key={clash.id}>
                                            <TableCell className="font-semibold">{clash.topic}</TableCell>
                                            <TableCell className="text-muted-foreground whitespace-normal">{clash.description}</TableCell>
                                            <TableCell className="text-right"><SeverityBadge severity={clash.severity} /></TableCell>
                                        </TableRow>
                                    ))}
                                </TableBody>
                            </Table>
                        </CardContent>
                    </Card>
                </div>

                {/* --- Sidebar Column --- */}
                <div className="md:col-span-1 space-y-6">
                    <Card>
                        <CardHeader>
                            <CardTitle>Compatibility Score</CardTitle>
                            <CardDescription>A measure of cultural alignment based on audience taste data.</CardDescription>
                        </CardHeader>
                        <CardContent className="flex flex-col items-center justify-center">
                             <div className="text-7xl font-bold text-primary">{analysis?.cultural_compatibility_score}</div>
                             <p className="text-muted-foreground mt-1">out of 100</p>
                        </CardContent>
                    </Card>

                    <Card>
                        <CardHeader>
                            <CardTitle>Brand Archetypes</CardTitle>
                            <CardDescription>AI-generated personalities based on audience affinities.</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div>
                                <h3 className="font-semibold text-foreground">{report.acquirer_brand}</h3>
                                <p className="text-muted-foreground text-sm whitespace-pre-wrap">{archetypes.acquirer_archetype}</p>
                            </div>
                            <Separator />
                             <div>
                                <h3 className="font-semibold text-foreground">{report.target_brand}</h3>
                                <p className="text-muted-foreground text-sm whitespace-pre-wrap">{archetypes.target_archetype}</p>
                            </div>
                        </CardContent>
                    </Card>
                </div>
            </div>
        </div>
    );
};


// --- Skeleton Component for Loading State ---
export const ReportViewSkeleton = () => {
  return (
    <div className="container mx-auto py-6 space-y-6 animate-pulse">
      <Card>
        <CardHeader>
          <Skeleton className="h-8 w-3/4" />
          <Skeleton className="h-4 w-1/2" />
        </CardHeader>
      </Card>
      <div className="grid md:grid-cols-3 gap-6">
        <div className="md:col-span-2 space-y-6">
          <Card>
            <CardHeader><Skeleton className="h-6 w-1/3" /></CardHeader>
            <CardContent><Skeleton className="h-24 w-full" /></CardContent>
          </Card>
          <Card>
            <CardHeader><Skeleton className="h-6 w-1/3" /></CardHeader>
            <CardContent><Skeleton className="h-32 w-full" /></CardContent>
          </Card>
           <Card>
            <CardHeader><Skeleton className="h-6 w-1/3" /></CardHeader>
            <CardContent><Skeleton className="h-32 w-full" /></CardContent>
          </Card>
        </div>
        <div className="md:col-span-1 space-y-6">
          <Card>
             <CardHeader><Skeleton className="h-6 w-2/3" /></CardHeader>
            <CardContent className="flex flex-col items-center justify-center">
              <Skeleton className="h-20 w-24" />
            </CardContent>
          </Card>
           <Card>
             <CardHeader><Skeleton className="h-6 w-2/3" /></CardHeader>
            <CardContent className="space-y-4">
                <Skeleton className="h-16 w-full" />
                <Skeleton className="h-16 w-full" />
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};