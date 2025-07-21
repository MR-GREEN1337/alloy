"use client";

import { useState, useEffect } from "react";
import useSWR from 'swr';
import { PromptInputBox } from "@/components/global/PromptInputBox";
import { DashboardGreeting } from "@/components/global/DashboardGreeting";
import { useAuth } from "@/components/global/providers";
import { useRouter } from "next/navigation";
import { PageLoader } from "@/components/global/PageLoader";
import { Report } from "@/types/report";
import { DemoReportCard } from "@/components/global/DemoReportCard";
import { AnimatePresence, motion } from "framer-motion";

const DEMO_REPORT_TITLE = "Demo Report: Nike vs. Patagonia";
const DEMO_DISMISS_KEY = "alloy_demo_dismissed";

export default function DashboardPage() {
    const { isLoading, accessToken } = useAuth();
    const router = useRouter();
    const [isPristine, setIsPristine] = useState(true);

    // Fetch reports to find the demo
    const { data: reports } = useSWR<Report[]>(accessToken ? `/api/v1/reports` : null);

    const [demoReport, setDemoReport] = useState<Report | null>(null);
    const [showDemoCard, setShowDemoCard] = useState(false);

    useEffect(() => {
        if (reports) {
            const foundDemo = reports.find(r => r.title === DEMO_REPORT_TITLE);
            // Check localStorage only after a slight delay to prevent flash of content on load
            setTimeout(() => {
                const isDismissed = localStorage.getItem(DEMO_DISMISS_KEY) === 'true';
                if (foundDemo && !isDismissed) {
                    setDemoReport(foundDemo);
                    setShowDemoCard(true);
                } else {
                    setDemoReport(null);
                    setShowDemoCard(false);
                }
            }, 200);
        }
    }, [reports]);

    const handleDismissDemo = () => {
        setShowDemoCard(false);
        localStorage.setItem(DEMO_DISMISS_KEY, 'true');
    };

    const onReportCreated = () => {
        // After a report is created, reset the state and redirect
        setIsPristine(true);
        router.push('/dashboard/reports');
    };

    if (isLoading) {
      return <PageLoader />;
    }
    
    return (
        <div className="relative flex flex-col items-center justify-center min-h-[calc(100vh-8rem)] w-full transition-all duration-500 ease-in-out">
            {/* Subtle background pattern */}
            <div 
              className="absolute inset-0 z-[-1] h-full w-full bg-transparent"
              style={{
                backgroundImage: 'linear-gradient(to right, hsl(var(--border) / 0.4) 1px, transparent 1px), linear-gradient(to bottom, hsl(var(--border) / 0.4) 1px, transparent 1px)',
                backgroundSize: '36px 36px',
                maskImage: 'radial-gradient(ellipse 80% 50% at 50% 0%, #000 70%, transparent 110%)'
              }}
            />
            
            <div className="w-full max-w-3xl flex flex-col items-center gap-8 px-4 py-8">
                <DashboardGreeting isVisible={isPristine} />
            
                <PromptInputBox 
                  onReportCreated={onReportCreated} 
                  onPristineChange={setIsPristine} 
                />
            </div>

            {/* --- MODIFIED: Floating Demo Card Container in Bottom-Right --- */}
            <AnimatePresence>
                {showDemoCard && demoReport && (
                    <motion.div
                        className="fixed bottom-0 right-0 z-50 p-4 sm:p-6"
                        initial={{ opacity: 0, y: 100 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: 100, transition: { duration: 0.3 } }}
                        transition={{ type: 'spring', stiffness: 120, damping: 20, duration: 0.5 }}
                    >
                        <DemoReportCard report={demoReport} onDismiss={handleDismissDemo} />
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}