"use client";

import useSWR from 'swr';
import { useAuth } from '@/components/global/providers';
import { ReportView, ReportViewSkeleton } from '@/components/report/ReportView';
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { AlertCircle } from 'lucide-react';
import { useParams } from 'next/navigation';

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
    const { data: report, error, isLoading } = useSWR(
        accessToken ? [`${process.env.NEXT_PUBLIC_API_URL}/reports/${id}`, accessToken] : null,
        ([url, token]) => fetcher(url, token)
    );

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

    // The main view is now full-height, no container needed here.
    return <ReportView report={report} />;
}