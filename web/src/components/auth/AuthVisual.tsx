"use client";

import { motion } from "framer-motion";

export const AuthVisual = () => {
  return (
    <div className="relative flex h-full w-full items-center justify-center overflow-hidden bg-gray-950">
      <div
        className="absolute inset-0 h-full w-full"
        style={{
          backgroundImage:
            "linear-gradient(to right, hsl(var(--border)) 1px, transparent 1px), linear-gradient(to bottom, hsl(var(--border)) 1px, transparent 1px)",
          backgroundSize: "3rem 3rem",
        }}
      />
      <div className="relative h-full w-full">
        <motion.div
          animate={{
            x: ["-20%", "20%", "-20%"],
            y: ["-20%", "30%", "-20%"],
            rotate: [0, 180, 0],
          }}
          transition={{
            duration: 40,
            repeat: Infinity,
            repeatType: "reverse",
            ease: "easeInOut",
          }}
          className="absolute -top-1/4 -left-1/4 h-1/2 w-1/2 rounded-full bg-gradient-to-br from-blue-500/50 to-purple-600/50 blur-3xl filter"
        />
        <motion.div
          animate={{
            x: ["20%", "-20%", "20%"],
            y: ["20%", "-30%", "20%"],
            rotate: [0, -180, 0],
          }}
          transition={{
            duration: 35,
            repeat: Infinity,
            repeatType: "reverse",
            ease: "easeInOut",
          }}
          className="absolute -bottom-1/4 -right-1/4 h-2/3 w-2/3 rounded-full bg-gradient-to-tl from-cyan-400/40 to-indigo-500/40 blur-3xl filter"
        />
      </div>
      <div className="absolute inset-0 flex flex-col items-center justify-center bg-black/20 p-8 text-center text-white">
        <h1 className="mb-4 text-3xl font-bold tracking-tight">
          Where Culture Meets Capital.
        </h1>
        <p className="max-w-md text-lg text-white/80">
          Alloy is a financial-grade intelligence platform that de-risks acquisitions by replacing gut feeling with a data-driven Cultural Compatibility Score.
        </p>
      </div>
    </div>
  );
};