import React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { SearchBar } from "@/components/search-bar";
import { Search, Bot, Handshake, Shield } from "lucide-react";

export default function Home() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-background to-truce-50/20">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-12 sm:py-16 lg:py-24">
        <div className="max-w-6xl mx-auto">
        {/* Hero Section */}
        <div className="text-center mb-24 sm:mb-32">
          <div className="max-w-4xl mx-auto">
            <h1 className="text-5xl sm:text-6xl lg:text-7xl font-light tracking-tight mb-8 text-foreground">
              <span className="block font-medium bg-gradient-to-r from-truce-700 to-truce-500 bg-clip-text text-transparent">
                Truce
              </span>
            </h1>
            <p className="text-xl sm:text-2xl lg:text-3xl text-muted-foreground mb-16 max-w-3xl mx-auto leading-relaxed font-light">
              A transparent system for verifying contentious claims through multi-model analysis
            </p>
            <div className="mx-auto mb-8 max-w-3xl">
              <SearchBar placeholder="Enter any claim to verify with evidence and AI analysis..." />
            </div>
            <p className="text-sm text-muted-foreground font-light">
              Try: &ldquo;Violent crime in Canada is rising&rdquo; or &ldquo;Climate change affects global temperatures&rdquo;
            </p>
          </div>
        </div>

        {/* How it Works */}
        <div className="mb-32">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl font-light tracking-tight mb-6 text-foreground">How It Works</h2>
          </div>
          <div className="grid sm:grid-cols-3 gap-8 lg:gap-12 max-w-4xl mx-auto">
            <Card className="border-0 shadow-sm">
              <CardHeader className="pb-4">
                <div className="w-12 h-12 bg-truce-100 rounded-lg flex items-center justify-center mb-4">
                  <Search className="w-6 h-6 text-truce-600" />
                </div>
                <CardTitle className="text-lg font-medium">
                  Evidence Gathering
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground leading-relaxed">
                  Automatically searches and retrieves relevant data from authoritative sources with clear provenance
                </p>
              </CardContent>
            </Card>

            <Card className="border-0 shadow-sm">
              <CardHeader className="pb-4">
                <div className="w-12 h-12 bg-truce-100 rounded-lg flex items-center justify-center mb-4">
                  <Bot className="w-6 h-6 text-truce-600" />
                </div>
                <CardTitle className="text-lg font-medium">
                  Multi-Model Analysis
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground leading-relaxed">
                  Multiple AI models independently evaluate claims, showing verdicts, confidence levels, and rationale
                </p>
              </CardContent>
            </Card>

            <Card className="border-0 shadow-sm">
              <CardHeader className="pb-4">
                <div className="w-12 h-12 bg-truce-100 rounded-lg flex items-center justify-center mb-4">
                  <Shield className="w-6 h-6 text-truce-600" />
                </div>
                <CardTitle className="text-lg font-medium">
                  Transparent Results
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground leading-relaxed">
                  View all sources, model reasoning, and consensus metrics in a clear, accessible format
                </p>
              </CardContent>
            </Card>
          </div>
        </div>

        {/* Principles */}
        <div className="text-center">
          <div className="mb-12">
            <h2 className="text-2xl sm:text-3xl font-light tracking-tight mb-4 text-foreground">Built on Transparency</h2>
          </div>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-6 max-w-4xl mx-auto">
            <div className="group">
              <div className="w-12 h-12 bg-truce-100 rounded-lg flex items-center justify-center mb-4 mx-auto">
                <Shield className="w-6 h-6 text-truce-600" />
              </div>
              <h3 className="text-sm font-medium mb-2 text-foreground">Verifiable</h3>
              <p className="text-xs text-muted-foreground leading-relaxed">All sources tracked</p>
            </div>
            <div className="group">
              <div className="w-12 h-12 bg-truce-100 rounded-lg flex items-center justify-center mb-4 mx-auto">
                <Bot className="w-6 h-6 text-truce-600" />
              </div>
              <h3 className="text-sm font-medium mb-2 text-foreground">Independent</h3>
              <p className="text-xs text-muted-foreground leading-relaxed">Multiple AI models</p>
            </div>
            <div className="group">
              <div className="w-12 h-12 bg-truce-100 rounded-lg flex items-center justify-center mb-4 mx-auto">
                <Handshake className="w-6 h-6 text-truce-600" />
              </div>
              <h3 className="text-sm font-medium mb-2 text-foreground">Balanced</h3>
              <p className="text-xs text-muted-foreground leading-relaxed">Find common ground</p>
            </div>
            <div className="group">
              <div className="w-12 h-12 bg-truce-100 rounded-lg flex items-center justify-center mb-4 mx-auto">
                <Search className="w-6 h-6 text-truce-600" />
              </div>
              <h3 className="text-sm font-medium mb-2 text-foreground">Open</h3>
              <p className="text-xs text-muted-foreground leading-relaxed">Full transparency</p>
            </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
