"use client";

import useSWR from 'swr';
import { useAuth } from '@/components/global/providers';
import { ReportView, ReportViewSkeleton } from '@/components/report/ReportView';
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { AlertCircle, Download, Loader2 } from 'lucide-react';
import { useParams } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { useState } from 'react';
import { toast } from 'sonner';

const fetcher = (url: string, token: string) => 
  fetch(url, { headers: { 'Authorization': `Bearer ${token}` } }).then(res => {
    if (!res.ok) {
        if (res.status === 404) {
            throw new Error('Report not found. You may not have access or it may not exist.');
        }
        throw new Error('An error occurred while fetching the report.');
    }
    return res.json();
  });

export default function ReportPage() {
    const { id } = useParams<{ id: string }>();
    const { accessToken } = useAuth();
    const API_URL = process.env.NEXT_PUBLIC_API_URL;
    const { data: report, error, isLoading } = useSWR(
        accessToken ? [`${API_URL}/reports/${id}`, accessToken] : null,
        ([url, token]) => fetcher(url, token)
    );
    const [isDownloading, setIsDownloading] = useState(false);

    const handleDownload = async () => {
        if (!report || !accessToken) return;
        setIsDownloading(true);
        try {
            const res = await fetch(`${API_URL}/reports/${report.id}/download-pdf`, {
                headers: { 'Authorization': `Bearer ${accessToken}` }
            });
            if (!res.ok) {
                const errorData = await res.json();
                throw new Error(errorData.detail || "Failed to download PDF.");
            }
            const blob = await res.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `Alloy_Report_${report.acquirer_brand}_vs_${report.target_brand}.pdf`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            a.remove();
        } catch (err: any) {
            toast.error("Download Failed", { description: err.message });
        } finally {
            setIsDownloading(false);
        }
    };

    if (isLoading) {
        return <ReportViewSkeleton />;
    }

    if (error) {
        return (
             <div className="container mx-auto py-10">
                <Alert variant="destructive">
                    <AlertCircle className="h-4 w-4" />
                    <AlertTitle>Error</AlertTitle>
                    <AlertDescription>{error.message}</AlertDescription>
                </Alert>
            </div>
        )
    }

    if (!report) {
        return null;
    }

    return (
        <ReportView report={report}>
            <Button onClick={handleDownload} disabled={isDownloading}>
                {isDownloading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Download className="mr-2 h-4 w-4" />}
                {isDownloading ? 'Preparing...' : 'Download PDF'}
            </Button>
        </ReportView>
    );
}