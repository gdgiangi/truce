import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ 
  subsets: ["latin"],
  display: 'swap',
  variable: '--font-inter',
});

export const metadata: Metadata = {
  title: "Truce - Transparent Dialogue Platform",
  description: "A system for transparent, de-escalating dialogue around contentious claims",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={`${inter.variable} font-sans`}>
        <div className="min-h-screen bg-background">
          <header className="sticky top-0 z-50 border-b border-border/40 bg-background/80 backdrop-blur-md">
            <div className="container flex h-16 md:h-20 items-center px-4 md:px-6 lg:px-8">
              <div className="flex items-center justify-between w-full">
                <a href="/" className="flex items-center space-x-2 group">
                  <span className="text-xl md:text-2xl font-light text-foreground group-hover:text-truce-600 transition-colors">
                    Truce
                  </span>
                </a>
                <nav className="hidden md:flex items-center space-x-6 lg:space-x-8">
                  <a href="/" className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors py-2">
                    Home
                  </a>
                  <a href="/claim/violent-crime-canada" className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors py-2">
                    Demo
                  </a>
                  <a href="/consensus/canada-crime" className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors py-2">
                    Consensus
                  </a>
                  <a href="/transparency" className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors py-2">
                    Transparency
                  </a>
                </nav>
                
                {/* Mobile Navigation */}
                <div className="md:hidden">
                  <details className="relative">
                    <summary className="flex items-center justify-center w-10 h-10 rounded-lg hover:bg-accent transition-colors cursor-pointer">
                      <div className="flex flex-col space-y-1">
                        <span className="w-5 h-0.5 bg-foreground transition-all"></span>
                        <span className="w-5 h-0.5 bg-foreground transition-all"></span>
                        <span className="w-5 h-0.5 bg-foreground transition-all"></span>
                      </div>
                    </summary>
                    <div className="absolute right-0 top-12 w-48 bg-background border border-border/40 rounded-lg shadow-lg backdrop-blur-md">
                      <nav className="flex flex-col py-2">
                        <a href="/" className="px-4 py-3 text-sm font-medium text-muted-foreground hover:text-foreground hover:bg-accent transition-colors">
                          Home
                        </a>
                        <a href="/claim/violent-crime-canada" className="px-4 py-3 text-sm font-medium text-muted-foreground hover:text-foreground hover:bg-accent transition-colors">
                          Demo
                        </a>
                        <a href="/consensus/canada-crime" className="px-4 py-3 text-sm font-medium text-muted-foreground hover:text-foreground hover:bg-accent transition-colors">
                          Consensus
                        </a>
                        <a href="/transparency" className="px-4 py-3 text-sm font-medium text-muted-foreground hover:text-foreground hover:bg-accent transition-colors">
                          Transparency
                        </a>
                      </nav>
                    </div>
                  </details>
                </div>
              </div>
            </div>
          </header>
          <main className="flex-1">
            {children}
          </main>
          <footer className="border-t border-border/40 bg-background/50 backdrop-blur-sm">
            <div className="container px-6 lg:px-8 py-12">
              <div className="flex flex-col md:flex-row items-center justify-between gap-6">
                <div className="text-sm text-muted-foreground text-center md:text-left">
                  <p>
                    Inspired by{" "}
                    <a href="https://pol.is" className="text-foreground hover:text-truce-600 transition-colors underline underline-offset-4">
                      Pol.is
                    </a>{" "}
                    methodology for consensus finding.
                  </p>
                </div>
                <div className="text-sm text-muted-foreground">
                  <p>
                    Open source on{" "}
                    <a href="#" className="text-foreground hover:text-truce-600 transition-colors underline underline-offset-4">
                      GitHub
                    </a>
                  </p>
                </div>
              </div>
            </div>
          </footer>
        </div>
      </body>
    </html>
  );
}
