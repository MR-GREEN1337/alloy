"use client";

import Link from "next/link";
import useSWRMutation from 'swr/mutation';
import { useAuth } from '@/components/global/providers';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import { AlertCircle, CheckCircle, Clock, FileText, PlusCircle, Trash2, XCircle } from "lucide-react";
import { Report } from "@/types/report";
import { toast } from "sonner";
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
import useSWR from "swr";

// --- SWR Handlers ---
const fetcher = (url: string, token: string): Promise<Report[]> => 
  fetch(url, { headers: { 'Authorization': `Bearer ${token}` } }).then(res => {
    if (!res.ok) throw new Error('An error occurred while fetching reports.');
    return res.json();
  });

async function deleteReport(url: string, { arg }: { arg: { reportId: number, token: string } }) {
    const response = await fetch(`${url}${arg.reportId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${arg.token}` }
    });
    if (!response.ok && response.status !== 204) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to delete report.');
    }
}

// --- Components ---
const StatusBadge = ({ status }: { status: Report['status'] }) => {
    const config = {
        COMPLETED: { variant: 'default', icon: CheckCircle, text: 'Completed', className: 'bg-green-500/20 text-green-700 border-green-500/30 dark:text-green-400' },
        PENDING: { variant: 'secondary', icon: Clock, text: 'In Progress', className: 'bg-yellow-500/20 text-yellow-700 border-yellow-500/30 dark:text-yellow-400' },
        FAILED: { variant: 'destructive', icon: XCircle, text: 'Failed', className: 'bg-red-500/20 text-red-700 border-red-500/30 dark:text-red-400' },
        DRAFT: { variant: 'outline', icon: FileText, text: 'Draft', className: 'bg-gray-500/20 text-gray-700 border-gray-500/30 dark:text-gray-400' },
    }[status];

    const Icon = config.icon;
    
    return (
        <Badge variant={config.variant as any} className={config.className}>
            <Icon className="w-3 h-3 mr-1" />
            {config.text}
        </Badge>
    );
};

// --- Main Reports Page Component ---
export default function ReportsPage() {
    const { accessToken } = useAuth();
    const API_URL = process.env.NEXT_PUBLIC_API_URL;
    const { data: reports, error, mutate, isLoading } = useSWR(
        accessToken ? [`${API_URL}/reports/`, accessToken] : null,
        ([url, token]) => fetcher(url, token)
    );
    const { trigger: triggerDelete } = useSWRMutation(`${API_URL}/reports/`, deleteReport);

    const handleDelete = async (reportId: number) => {
        toast.info("Deleting report...");
        try {
            await triggerDelete({ reportId, token: accessToken! });
            toast.success("Report deleted successfully.");
            mutate(reports?.filter(r => r.id !== reportId), false);
        } catch (err: any) {
            toast.error("Deletion Failed", { description: err.message });
        }
    };

    const renderContent = () => {
        if (isLoading) {
            return (
                <Table>
                    <TableHeader><TableRow><TableHead>Report</TableHead><TableHead>Score</TableHead><TableHead>Status</TableHead><TableHead>Date</TableHead><TableHead><span className="sr-only">Actions</span></TableHead></TableRow></TableHeader>
                    <TableBody>{[...Array(5)].map((_, i) => (<TableRow key={i}><TableCell><Skeleton className="h-5 w-48" /></TableCell><TableCell><Skeleton className="h-5 w-12" /></TableCell><TableCell><Skeleton className="h-6 w-20" /></TableCell><TableCell><Skeleton className="h-5 w-32" /></TableCell><TableCell className="flex gap-2"><Skeleton className="h-8 w-20" /><Skeleton className="h-8 w-8" /></TableCell></TableRow>))}</TableBody>
                </Table>
            );
        }

        if (error) {
            return <Alert variant="destructive"><AlertCircle className="h-4 w-4" /><AlertTitle>Error Loading Reports</AlertTitle><AlertDescription>{error.message}</AlertDescription></Alert>;
        }

        if (reports && reports.length === 0) {
            return (
                <div className="text-center py-16"><h3 className="text-xl font-semibold">No reports found</h3><p className="text-muted-foreground mt-2 mb-4">Get started by creating your first cultural analysis.</p><Button asChild><Link href="/dashboard"><PlusCircle className="mr-2 h-4 w-4" />Create New Report</Link></Button></div>
            );
        }

        if (reports) {
            return (
                <Table>
                    <TableHeader><TableRow><TableHead className="w-[40%]">Report</TableHead><TableHead>Score</TableHead><TableHead>Status</TableHead><TableHead>Date</TableHead><TableHead className="text-right">Actions</TableHead></TableRow></TableHeader>
                    <TableBody>
                        {reports.map((report) => (
                            <TableRow key={report.id}>
                                <TableCell className="font-medium">{report.title}</TableCell>
                                <TableCell className="font-semibold">{report.analysis?.cultural_compatibility_score ?? '--'}</TableCell>
                                <TableCell><StatusBadge status={report.status} /></TableCell>
                                <TableCell className="text-muted-foreground">{new Date(report.created_at).toLocaleDateString()}</TableCell>
                                <TableCell className="text-right space-x-2">
                                    <Button asChild variant="outline" size="sm"><Link href={`/dashboard/reports/${report.id}`}>View</Link></Button>
                                    <AlertDialog>
                                        <AlertDialogTrigger asChild><Button variant="ghost" size="icon" className="text-muted-foreground hover:text-destructive"><Trash2 className="h-4 w-4" /></Button></AlertDialogTrigger>
                                        <AlertDialogContent>
                                            <AlertDialogHeader><AlertDialogTitle>Are you absolutely sure?</AlertDialogTitle><AlertDialogDescription>This action cannot be undone. This will permanently delete the report for "{report.title}".</AlertDialogDescription></AlertDialogHeader>
                                            <AlertDialogFooter><AlertDialogCancel>Cancel</AlertDialogCancel><AlertDialogAction onClick={() => handleDelete(report.id)} className="bg-destructive text-destructive-foreground hover:bg-destructive/90">Delete Report</AlertDialogAction></AlertDialogFooter>
                                        </AlertDialogContent>
                                    </AlertDialog>
                                </TableCell>
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            );
        }

        return null;
    };

    return (
        <Card>
            <CardHeader className="flex flex-row items-center justify-between">
                <div><CardTitle>My Reports</CardTitle><CardDescription>A complete history of all generated cultural analyses.</CardDescription></div>
                <Button asChild><Link href="/dashboard"><PlusCircle className="mr-2 h-4 w-4" />Create New Report</Link></Button>
            </CardHeader>
            <CardContent>{renderContent()}</CardContent>
        </Card>
    );
}