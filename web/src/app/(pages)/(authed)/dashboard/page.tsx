"use client";

import { useState } from "react";
import { PromptInputBox } from "@/components/global/PromptInputBox";
import { DashboardGreeting } from "@/components/global/DashboardGreeting";
import { useAuth } from "@/components/global/providers";
import { useRouter } from "next/navigation";
import { PageLoader } from "@/components/global/PageLoader";

export default function DashboardPage() {
    const { isLoading } = useAuth();
    const router = useRouter();
    const [isPristine, setIsPristine] = useState(true);

    const onReportCreated = () => {
        // After a report is created, reset the state and redirect
        setIsPristine(true);
        router.push('/dashboard/reports');
    };

    if (isLoading) {
      return <PageLoader />;
    }
    
    return (
        <div className="relative flex flex-col items-center justify-center h-[calc(100vh-8rem)] w-full transition-all duration-500 ease-in-out">
            {/* Subtle background pattern */}
            <div 
              className="absolute inset-0 z-[-1] h-full w-full bg-transparent"
              style={{
                backgroundImage: 'linear-gradient(to right, hsl(var(--border) / 0.4) 1px, transparent 1px), linear-gradient(to bottom, hsl(var(--border) / 0.4) 1px, transparent 1px)',
                backgroundSize: '36px 36px',
                maskImage: 'radial-gradient(ellipse 80% 50% at 50% 0%, #000 70%, transparent 110%)'
              }}
            />
            
            <DashboardGreeting isVisible={isPristine} />
            
            <div className="w-full max-w-3xl px-4">
                <PromptInputBox 
                  onReportCreated={onReportCreated} 
                  onPristineChange={setIsPristine} 
                />
            </div>
        </div>
    );
}