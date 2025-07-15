"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

interface DashboardGreetingProps {
  isVisible: boolean;
}

const greetings = [
    { title: "Let's de-risk your next deal.", subtitle: "Enter the acquirer and target to begin your cultural analysis." },
    { title: "Ready for analysis?", subtitle: "Quantify the cultural fit for your next M&A." },
];

// A simple hash function to pick a greeting based on the day
const getDailyGreeting = () => {
    const day = new Date().getDate();
    return greetings[day % greetings.length];
};

export const DashboardGreeting = ({ isVisible }: DashboardGreetingProps) => {
  const greeting = getDailyGreeting();

  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: isVisible ? 1 : 0, y: isVisible ? 0 : -10 }}
      transition={{ duration: 0.5, ease: "easeInOut" }}
      className={cn("text-center mb-8", !isVisible && "pointer-events-none")}
    >
      <h1 className="text-3xl md:text-4xl font-semibold text-foreground tracking-tight">{greeting.title}</h1>
      <p className="mt-2 text-base text-muted-foreground">{greeting.subtitle}</p>
    </motion.div>
  );
};
