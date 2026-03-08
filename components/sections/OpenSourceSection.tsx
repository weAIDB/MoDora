import { Container } from "@/components/layout/Container";
import { Button } from "@/components/ui/button";
import { Github } from "lucide-react";
import Link from "next/link";

export function OpenSourceSection() {
  return (
    <section className="py-20 bg-primary text-primary-foreground">
      <Container>
        <div className="flex flex-col items-center text-center space-y-8">
          <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">
            Proudly Open Source
          </h2>
          <p className="text-lg text-primary-foreground/90 max-w-2xl">
            MoDora is built by the community, for the community. Join us in advancing the state of multimodal document analysis.
          </p>
          <Button size="lg" variant="secondary" className="h-12 px-8" asChild>
            <Link href="https://github.com/weAIDB/MoDora" target="_blank" rel="noopener noreferrer">
              <Github className="mr-2 h-5 w-5" />
              Star on GitHub
            </Link>
          </Button>
        </div>
      </Container>
    </section>
  );
}
