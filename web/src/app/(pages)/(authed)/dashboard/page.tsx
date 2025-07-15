"use client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { useAuth } from "@/components/global/providers";
import useSWR from 'swr';
import useSWRMutation from 'swr/mutation';
import { useState } from "react";
import { toast } from "sonner";
import Link from "next/link";
import { ArrowRight, Clock, CheckCircle, XCircle, Trash2 } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";

// --- SWR Fetchers and Mutators ---
const fetcher = (url: string, token: string) => 
  fetch(url, { headers: { 'Authorization': `Bearer ${token}` } }).then(res => {
    if (!res.ok) throw new Error('An error occurred while fetching the data.');
    return res.json();
  });

async function createReport(url: string, { arg }: { arg: { acquirer_brand: string, target_brand: string, title: string, token: string } }) {
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${arg.token}` },
    body: JSON.stringify({ acquirer_brand: arg.acquirer_brand, target_brand: arg.target_brand, title: arg.title })
  });
  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.detail || 'Failed to create report.');
  }
  return response.json();
}

async function deleteReport(url: string, { arg }: { arg: { reportId: number, token: string } }) {
    const response = await fetch(`${url}${arg.reportId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${arg.token}` }
    });
    if (!response.ok) {
        if (response.status === 204) return; // Success case
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to delete report.');
    }
}

// --- Components ---
const StatusBadge = ({ status }: { status: 'COMPLETED' | 'PENDING' | 'FAILED' }) => {
    const config = {
        COMPLETED: { variant: 'default', icon: CheckCircle, text: 'Completed', className: 'bg-green-500/20 text-green-700 border-green-500/30 dark:text-green-400' },
        PENDING: { variant: 'secondary', icon: Clock, text: 'Pending', className: 'bg-yellow-500/20 text-yellow-700 border-yellow-500/30 dark:text-yellow-400' },
        FAILED: { variant: 'destructive', icon: XCircle, text: 'Failed', className: 'bg-red-500/20 text-red-700 border-red-500/30 dark:text-red-400' },
    }[status];
    return <Badge variant={config.variant} className={config.className}><config.icon className="mr-1 h-3 w-3" />{config.text}</Badge>;
};

export default function DashboardPage() {
    const { accessToken } = useAuth();
    const API_URL = process.env.NEXT_PUBLIC_API_URL;
    const { data: reports, error, mutate, isLoading } = useSWR(
        accessToken ? [`${API_URL}/reports/`, accessToken] : null,
        ([url, token]) => fetcher(url, token)
    );
    
    const { trigger: triggerCreate, isMutating: isCreating } = useSWRMutation(`${API_URL}/reports/`, createReport);
    const { trigger: triggerDelete } = useSWRMutation(`${API_URL}/reports/`, deleteReport);

    const [acquirer, setAcquirer] = useState("");
    const [target, setTarget] = useState("");

    const handleGenerateReport = async () => {
        toast.info("Kicking off analysis...", { description: "This may take a minute." });
        try {
            await triggerCreate({
                acquirer_brand: acquirer,
                target_brand: target,
                title: `${acquirer} vs. ${target}`,
                token: accessToken!
            });
            toast.success("Report generated successfully!");
            mutate();
            setAcquirer("");
            setTarget("");
        } catch (err: any) {
            toast.error("Report Generation Failed", { description: err.message });
        }
    };

    const handleDeleteReport = async (reportId: number) => {
        toast.info("Deleting report...");
        try {
            await triggerDelete({ reportId, token: accessToken! });
            toast.success("Report deleted successfully.");
            mutate(reports?.filter(r => r.id !== reportId), false); // Optimistic update
        } catch (err: any) {
            toast.error("Deletion Failed", { description: err.message });
        }
    };
    
    return (
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            <Card className="lg:col-span-1">
                <CardHeader>
                    <CardTitle>Create New Alloy Report</CardTitle>
                    <CardDescription>Enter two brands to quantify their cultural compatibility.</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                    <div className="space-y-2"><Label htmlFor="acquirer">Acquirer Brand</Label><Input id="acquirer" placeholder="e.g., Disney" value={acquirer} onChange={e => setAcquirer(e.target.value)} /></div>
                    <div className="space-y-2"><Label htmlFor="target">Target Brand</Label><Input id="target" placeholder="e.g., A24 Films" value={target} onChange={e => setTarget(e.target.value)} /></div>
                    <Button onClick={handleGenerateReport} disabled={isCreating || !acquirer || !target} className="w-full">{isCreating ? 'Analyzing...' : 'Generate Report'}</Button>
                </CardContent>
            </Card>

            <Card className="lg:col-span-2">
                <CardHeader>
                    <CardTitle>Recent Reports</CardTitle>
                    <CardDescription>View your previously generated cultural analyses.</CardDescription>
                </CardHeader>
                <CardContent>
                    {isLoading && <div className="space-y-4">{[...Array(3)].map((_, i) => <Skeleton key={i} className="h-20 w-full" />)}</div>}
                    {error && <div className="text-destructive">Failed to load reports.</div>}
                    {reports && reports.length > 0 && (
                        <ul className="space-y-3">
                           {reports.map((report: any) => (
                               <li key={report.id} className="group flex items-center justify-between p-4 border rounded-lg hover:bg-muted/50 transition-colors">
                                   <Link href={`/reports/${report.id}`} className="flex-grow">
                                       <div className="font-semibold">{report.title}</div>
                                       <div className="text-sm text-muted-foreground">Compatibility: <span className="font-bold">{report.analysis?.cultural_compatibility_score || 'N/A'}</span></div>
                                   </Link>
                                   <div className="flex items-center gap-4">
                                       <StatusBadge status={report.status} />
                                       <AlertDialog>
                                           <AlertDialogTrigger asChild>
                                               <Button variant="ghost" size="icon" className="h-8 w-8 opacity-0 group-hover:opacity-100 transition-opacity text-muted-foreground hover:text-destructive"><Trash2 className="h-4 w-4" /></Button>
                                           </AlertDialogTrigger>
                                           <AlertDialogContent>
                                               <AlertDialogHeader><AlertDialogTitle>Are you sure?</AlertDialogTitle><AlertDialogDescription>This will permanently delete the report for "{report.title}". This action cannot be undone.</AlertDialogDescription></AlertDialogHeader>
                                               <AlertDialogFooter>
                                                   <AlertDialogCancel>Cancel</AlertDialogCancel>
                                                   <AlertDialogAction onClick={() => handleDeleteReport(report.id)} className="bg-destructive text-destructive-foreground hover:bg-destructive/90">Delete</AlertDialogAction>
                                               </AlertDialogFooter>
                                           </AlertDialogContent>
                                       </AlertDialog>
                                       <ArrowRight className="h-5 w-5 text-muted-foreground" />
                                   </div>
                               </li>
                           ))}
                        </ul>
                    )}
                     {reports && reports.length === 0 && <div className="text-center text-muted-foreground py-8">No reports found.</div>}
                </CardContent>
            </Card>
        </div>
    );
}