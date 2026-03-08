import { Container } from "@/components/layout/Container";
import Link from "next/link";
import { Github } from "lucide-react";

export function Footer() {
  return (
    <footer className="border-t py-12 bg-background">
      <Container>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          <div className="col-span-1 md:col-span-2 space-y-4">
            <span className="text-xl font-bold tracking-tight">MoDora</span>
            <p className="text-sm text-muted-foreground max-w-xs">
              Multimodal Document Analysis Assistant.
              Organizing chaos into structured knowledge.
            </p>
          </div>
          
          <div className="space-y-4">
            <h4 className="text-sm font-semibold">Resources</h4>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li>
                <Link href="#" className="hover:text-foreground">Documentation</Link>
              </li>
              <li>
                <Link href="#" className="hover:text-foreground">API Reference</Link>
              </li>
              <li>
                <Link href="#" className="hover:text-foreground">Blog</Link>
              </li>
            </ul>
          </div>
          
          <div className="space-y-4">
            <h4 className="text-sm font-semibold">Community</h4>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li>
                <Link href="https://github.com/weAIDB/MoDora" target="_blank" rel="noopener noreferrer" className="flex items-center gap-2 hover:text-foreground">
                  <Github className="h-4 w-4" /> GitHub
                </Link>
              </li>
              <li>
                <Link href="#" className="hover:text-foreground">Discord</Link>
              </li>
              <li>
                <Link href="#" className="hover:text-foreground">Twitter</Link>
              </li>
            </ul>
          </div>
        </div>
        
        <div className="mt-12 border-t pt-8 flex flex-col md:flex-row justify-between items-center gap-4 text-xs text-muted-foreground">
          <p>&copy; {new Date().getFullYear()} MoDora. All rights reserved.</p>
          <div className="flex gap-4">
            <Link href="#" className="hover:text-foreground">Privacy Policy</Link>
            <Link href="#" className="hover:text-foreground">Terms of Service</Link>
          </div>
        </div>
      </Container>
    </footer>
  );
}
