"use client";

import { Container } from "@/components/layout/Container";

export function DemoSection() {
  return (
    <section id="demo" className="py-20 bg-secondary/30">
      <Container>
        <div className="flex flex-col items-center space-y-8">
          <div className="text-center space-y-4 max-w-3xl">
            <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">
              See MoDora in Action
            </h2>
            <p className="text-lg text-muted-foreground">
              From raw documents to grounded answers. MoDora parses, structures, and reasons over your data.
            </p>
          </div>

          <div className="relative w-full aspect-video rounded-xl overflow-hidden shadow-2xl border bg-background">
            <iframe
              src="https://player.vimeo.com/video/1168527529?badge=0&amp;autopause=0&amp;player_id=0&amp;app_id=58479"
              frameBorder="0"
              allow="autoplay; fullscreen; picture-in-picture; clipboard-write; encrypted-media"
              className="absolute inset-0 w-full h-full"
              title="MoDora_Demo"
            ></iframe>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-5 gap-4 w-full max-w-4xl pt-8">
            {["Upload", "Parse", "Tree Build", "Retrieval", "Answer"].map((step, i) => (
              <div key={step} className="flex flex-col items-center space-y-2">
                <div className="flex items-center justify-center w-8 h-8 rounded-full bg-primary/10 text-primary font-bold text-sm">
                  {i + 1}
                </div>
                <span className="text-sm font-medium">{step}</span>
              </div>
            ))}
          </div>
        </div>
      </Container>
    </section>
  );
}
