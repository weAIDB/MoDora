"use client";

import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Container } from "@/components/layout/Container";
import { ArrowRight, Github, FileText, Database, Brain } from "lucide-react";
import Link from "next/link";

export function HeroSection() {
  return (
    <section className="relative overflow-hidden py-20 md:py-32 lg:py-40">
      {/* Abstract Background Visualization */}
      <div className="absolute inset-0 -z-10 overflow-hidden">
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[1000px] h-[500px] bg-primary/5 rounded-full blur-3xl opacity-50" />
        <div className="absolute bottom-0 right-0 w-[800px] h-[400px] bg-blue-400/5 rounded-full blur-3xl opacity-30" />
      </div>

      <Container>
        <div className="flex flex-col items-center text-center space-y-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="space-y-4 max-w-3xl"
          >
            <div className="inline-flex items-center rounded-full border px-3 py-1 text-sm font-medium text-muted-foreground bg-secondary/50 backdrop-blur-sm mb-4">
              <span className="flex h-2 w-2 rounded-full bg-primary mr-2"></span>
              Now Open Source
            </div>
            
            <h1 className="text-4xl md:text-6xl lg:text-7xl font-bold tracking-tight text-foreground">
              Multimodal Document <br className="hidden md:block" />
              <span className="text-primary">Analysis Assistant</span>
            </h1>
            
            <p className="text-lg md:text-xl text-muted-foreground max-w-2xl mx-auto leading-relaxed">
              Understand complex documents by organizing text, tables, and figures into a structured tree. 
              Perform grounded retrieval and reasoning with MoDora.
            </p>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
            className="flex flex-col sm:flex-row gap-4 w-full justify-center"
          >
            <Button size="lg" className="text-base px-8 h-12" asChild>
              <Link href="#demo">
                View Demo <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
            <Button size="lg" variant="outline" className="text-base px-8 h-12" asChild>
              <Link href="https://github.com/weAIDB/MoDora" target="_blank" rel="noopener noreferrer">
                <Github className="mr-2 h-4 w-4" /> GitHub
              </Link>
            </Button>
          </motion.div>

          {/* Abstract Tree Concept Visualization */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.8, delay: 0.4 }}
            className="mt-16 relative w-full max-w-4xl aspect-[2/1] rounded-xl border bg-background/50 backdrop-blur-sm shadow-2xl flex items-center justify-center overflow-hidden"
          >
             <div className="absolute inset-0 bg-grid-slate-100/50 [mask-image:linear-gradient(0deg,white,rgba(255,255,255,0.6))]" />
             
             {/* Concept Nodes */}
             <div className="relative z-10 flex flex-col items-center gap-8">
                <div className="p-4 bg-white rounded-lg shadow-lg border flex items-center gap-3">
                  <FileText className="h-6 w-6 text-primary" />
                  <span className="font-semibold">Complex Document</span>
                </div>
                
                <div className="w-px h-8 bg-border border-l-2 border-dashed" />
                
                <div className="flex gap-8">
                  <div className="p-3 bg-white rounded-lg shadow-md border flex items-center gap-2">
                    <Database className="h-5 w-5 text-blue-500" />
                    <span className="text-sm">Structured Tree</span>
                  </div>
                  <div className="p-3 bg-white rounded-lg shadow-md border flex items-center gap-2">
                    <Brain className="h-5 w-5 text-purple-500" />
                    <span className="text-sm">Reasoning</span>
                  </div>
                </div>
             </div>
          </motion.div>
        </div>
      </Container>
    </section>
  );
}
