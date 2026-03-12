"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import { PieChart, Table } from "lucide-react";

export function HeroAnimation() {
  return (
    <div className="relative w-full h-full flex flex-col items-center justify-end overflow-hidden pb-12">
      {/* Background Glow */}
      <div className="absolute inset-0 z-0 bg-purple-500/5 blur-[100px] rounded-full opacity-50 pointer-events-none" />

      {/* Connection Lines (Tree Branches) */}
      <svg
        className="absolute inset-0 w-full h-full z-40 pointer-events-none"
        viewBox="0 0 800 400"
        fill="none"
        preserveAspectRatio="xMidYMax slice"
      >
        <defs>
          <linearGradient id="gradient-main" x1="0%" y1="100%" x2="0%" y2="0%">
            <stop offset="0%" stopColor="#e9d5ff" /> {/* Purple-200 */}
            <stop offset="100%" stopColor="#a855f7" /> {/* Purple-500 */}
          </linearGradient>
        </defs>

        {/* --- Roots (Bottom to Trunk Base) --- */}
        {/* Left Card to Trunk */}
        <motion.path
          d="M 250 324 C 250 286, 374 286, 400 242"
          stroke="url(#gradient-main)"
          strokeWidth="8"
          strokeLinecap="round"
          fill="none"
          initial={{ pathLength: 0, opacity: 0 }}
          animate={{ pathLength: 1, opacity: 1 }}
          transition={{ duration: 1.2, ease: "easeOut", delay: 0.8 }}
        />
        {/* Center Card to Trunk */}
        <motion.path
          d="M 400 324 C 422 292, 420 260, 400 242"
          stroke="url(#gradient-main)"
          strokeWidth="10"
          strokeLinecap="round"
          fill="none"
          initial={{ pathLength: 0, opacity: 0 }}
          animate={{ pathLength: 1, opacity: 1 }}
          transition={{ duration: 1.0, ease: "easeOut", delay: 1.0 }}
        />
        {/* Right Card to Trunk */}
        <motion.path
          d="M 550 324 C 550 286, 426 286, 400 242"
          stroke="url(#gradient-main)"
          strokeWidth="8"
          strokeLinecap="round"
          fill="none"
          initial={{ pathLength: 0, opacity: 0 }}
          animate={{ pathLength: 1, opacity: 1 }}
          transition={{ duration: 1.2, ease: "easeOut", delay: 1.2 }}
        />

        {/* --- Main Trunk (Base to Branch Point) --- */}
        <motion.path
          d="M 400 242 C 386 218, 386 192, 400 172"
          stroke="url(#gradient-main)"
          strokeWidth="8"
          strokeLinecap="round"
          fill="none"
          initial={{ pathLength: 0, opacity: 0 }}
          animate={{ pathLength: 1, opacity: 1 }}
          transition={{ duration: 0.8, ease: "easeOut", delay: 2.0 }}
        />

        {/* --- Branches (Branch Point to Nodes) --- */}
        {/* Branch 1 (Far Left) - Target: (180, 100) */}
        <motion.path
          d="M 400 172 C 350 136, 220 144, 180 100"
          stroke="url(#gradient-main)"
          strokeWidth="6"
          strokeLinecap="round"
          fill="none"
          initial={{ pathLength: 0, opacity: 0 }}
          animate={{ pathLength: 1, opacity: 1 }}
          transition={{ duration: 1.0, ease: "easeOut", delay: 2.8 }}
        />
        {/* Branch 2 (Left) - Target: (280, 70) */}
        <motion.path
          d="M 400 172 C 360 126, 300 114, 280 70"
          stroke="url(#gradient-main)"
          strokeWidth="7"
          strokeLinecap="round"
          fill="none"
          initial={{ pathLength: 0, opacity: 0 }}
          animate={{ pathLength: 1, opacity: 1 }}
          transition={{ duration: 1.0, ease: "easeOut", delay: 2.9 }}
        />
        {/* Branch 3 (Center) - Slight curve so it doesn't visually merge with the trunk */}
        <motion.path
          d="M 400 172 C 408 136, 408 88, 400 50"
          stroke="url(#gradient-main)"
          strokeWidth="8"
          strokeLinecap="round"
          fill="none"
          initial={{ pathLength: 0, opacity: 0 }}
          animate={{ pathLength: 1, opacity: 1 }}
          transition={{ duration: 1.0, ease: "easeOut", delay: 3.0 }}
        />
        {/* Branch 4 (Right) - Target: (520, 70) */}
        <motion.path
          d="M 400 172 C 440 126, 500 114, 520 70"
          stroke="url(#gradient-main)"
          strokeWidth="7"
          strokeLinecap="round"
          fill="none"
          initial={{ pathLength: 0, opacity: 0 }}
          animate={{ pathLength: 1, opacity: 1 }}
          transition={{ duration: 1.0, ease: "easeOut", delay: 3.1 }}
        />
        {/* Branch 5 (Far Right) - Target: (620, 100) */}
        <motion.path
          d="M 400 172 C 450 136, 580 144, 620 100"
          stroke="url(#gradient-main)"
          strokeWidth="6"
          strokeLinecap="round"
          fill="none"
          initial={{ pathLength: 0, opacity: 0 }}
          animate={{ pathLength: 1, opacity: 1 }}
          transition={{ duration: 1.0, ease: "easeOut", delay: 3.2 }}
        />

      </svg>

      {/* Nodes (Circles at top) */}
      <div className="absolute inset-0 z-50 pointer-events-none">
        {[
          { cx: "22.5%", cy: "25%", delay: 3.8, color: "bg-purple-300" }, // Branch 1: (180, 100) / 800x400 = 22.5%, 25%
          { cx: "35%", cy: "17.5%", delay: 3.9, color: "bg-purple-400" }, // Branch 2: (280, 70) / 800x400 = 35%, 17.5%
          { cx: "50%", cy: "12.5%", delay: 4.0, color: "bg-purple-500" }, // Branch 3: (400, 50) / 800x400 = 50%, 12.5%
          { cx: "65%", cy: "17.5%", delay: 4.1, color: "bg-purple-600" }, // Branch 4: (520, 70) / 800x400 = 65%, 17.5%
          { cx: "77.5%", cy: "25%", delay: 4.2, color: "bg-purple-700" }, // Branch 5: (620, 100) / 800x400 = 77.5%, 25%
        ].map((node, i) => (
          <motion.div
            key={i}
            className={cn(
              "absolute w-12 h-12 rounded-full shadow-lg border-2 border-white/50 backdrop-blur-sm", // Removed transform to use center positioning logic if needed, but keeping it simple for now
              node.color
            )}
            style={{ 
              left: node.cx, 
              top: node.cy,
              marginLeft: "-24px", // Half of width (48px / 2)
              marginTop: "-24px"   // Half of height (48px / 2)
            }}
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{
              type: "spring",
              stiffness: 260,
              damping: 20,
              delay: node.delay,
            }}
          >
            {/* Inner pulse */}
            <div className="absolute inset-0 rounded-full bg-white/30 animate-pulse" />
          </motion.div>
        ))}
      </div>

      {/* Document Cards (Bottom) */}
      <div className="relative z-30 hidden gap-12 mt-auto">
        {/* Left Card: Chart */}
        <motion.div
          initial={{ y: 50, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ duration: 0.8, delay: 0.1 }}
          className="w-24 h-32 bg-white dark:bg-slate-900 rounded-lg shadow-xl border border-purple-100 dark:border-purple-900/50 flex flex-col p-2 items-center justify-center gap-2"
        >
          <div className="w-full h-16 bg-purple-50 dark:bg-purple-900/20 rounded flex items-end justify-center gap-1 p-1">
             <div className="w-2 bg-purple-300 h-[40%]" />
             <div className="w-2 bg-purple-400 h-[70%]" />
             <div className="w-2 bg-purple-500 h-[50%]" />
             <div className="w-2 bg-purple-600 h-[80%]" />
          </div>
          <div className="w-full h-1 bg-slate-100 dark:bg-slate-800 rounded" />
          <div className="w-2/3 h-1 bg-slate-100 dark:bg-slate-800 rounded" />
        </motion.div>

        {/* Center Card: Table */}
        <motion.div
          initial={{ y: 50, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ duration: 0.8, delay: 0.3 }}
          className="w-28 h-36 bg-white dark:bg-slate-900 rounded-lg shadow-2xl border border-purple-200 dark:border-purple-800 flex flex-col p-3 items-center relative -top-4"
        >
          <Table className="text-purple-600 mb-2 h-6 w-6" />
          <div className="grid grid-cols-3 gap-1 w-full">
            {[...Array(9)].map((_, i) => (
              <div
                key={i}
                className={cn(
                  "h-4 rounded-sm",
                  i < 3 ? "bg-purple-100 dark:bg-purple-900/40" : "bg-slate-50 dark:bg-slate-800"
                )}
              />
            ))}
          </div>
        </motion.div>

        {/* Right Card: Pie */}
        <motion.div
          initial={{ y: 50, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ duration: 0.8, delay: 0.5 }}
          className="w-24 h-32 bg-white dark:bg-slate-900 rounded-lg shadow-xl border border-purple-100 dark:border-purple-900/50 flex flex-col p-2 items-center justify-center gap-2"
        >
          <PieChart className="text-purple-500 h-10 w-10" />
          <div className="w-full h-1 bg-slate-100 dark:bg-slate-800 rounded" />
          <div className="w-full h-1 bg-slate-100 dark:bg-slate-800 rounded" />
        </motion.div>
      </div>
    </div>
  );
}
