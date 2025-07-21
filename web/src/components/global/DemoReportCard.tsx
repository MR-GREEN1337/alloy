"use client";

import Link from "next/link";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ArrowRight, FileText, Sparkles, X } from "lucide-react";
import { Report } from "@/types/report";
import Logo from "./Logo";

interface DemoReportCardProps {
  report: Report;
  onDismiss: () => void;
}

export const DemoReportCard = ({ report, onDismiss }: DemoReportCardProps) => {
  return (
    // MODIFIED: Changed max-width to create a "tall" rectangle
    <div className="w-full max-w-sm">
      <Card className="relative overflow-hidden border-primary/20 bg-card shadow-2xl">
        <div className="absolute -top-1/2 -right-1/4 h-full w-1/2 bg-primary/5 rounded-full blur-3xl -z-10" />
        <CardHeader>
            <div className="flex items-start justify-between">
                <div>
                    <CardTitle className="flex items-center gap-2">
                        <Logo className="h-5 w-5 text-primary" />
                        Your First Analysis is Ready
                    </CardTitle>
                    <CardDescription className="mt-1">
                        We've prepared a demo report to showcase Alloy's capabilities.
                    </CardDescription>
                </div>
                <Button variant="ghost" size="icon" className="h-7 w-7 flex-shrink-0" onClick={onDismiss}>
                    <X className="h-4 w-4" />
                </Button>
            </div>
        </CardHeader>
        {/* MODIFIED: Changed to a vertical flex layout */}
        <div className="flex flex-col items-start gap-4 p-6 pt-0">
             <div className="flex items-center gap-3 text-sm font-medium">
                <FileText className="h-5 w-5 text-primary/80"/>
                <span className="text-foreground">{report.title}</span>
            </div>
            <div className="w-full flex justify-end">
                <Button asChild>
                    <Link href={`/dashboard/reports/${report.id}`} onClick={onDismiss}>
                        View Report <ArrowRight className="ml-2 h-4 w-4" />
                    </Link>
                </Button>
            </div>
        </div>
      </Card>
    </div>
  );
};