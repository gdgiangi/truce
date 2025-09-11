import React from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Search, Bot, Handshake, ArrowRight, Shield, Download } from "lucide-react";

export default function Home() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-background to-truce-50/20">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-12 sm:py-16 lg:py-24">
        <div className="max-w-6xl mx-auto">
        {/* Hero Section */}
        <div className="text-center mb-24 sm:mb-32">
          <div className="max-w-4xl mx-auto">
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-light tracking-tight mb-8 text-foreground">
              Welcome to
              <span className="block mt-2 font-medium bg-gradient-to-r from-truce-700 to-truce-500 bg-clip-text text-transparent">
                Truce
              </span>
            </h1>
            <p className="text-lg sm:text-xl lg:text-2xl text-muted-foreground mb-12 max-w-3xl mx-auto leading-relaxed font-light">
              A transparent system for de-escalating dialogue around contentious claims. 
              See the evidence, understand different perspectives, and find common ground.
            </p>
            <div className="flex flex-col sm:flex-row gap-6 justify-center items-center">
              <Button asChild size="lg" className="px-8 py-4 text-base elegant-hover">
                <Link href="/claim/violent-crime-canada" className="flex items-center gap-2">
                  View Demo Claim
                  <ArrowRight className="w-4 h-4" />
                </Link>
              </Button>
              <Button variant="outline" asChild size="lg" className="px-8 py-4 text-base elegant-hover">
                <Link href="/consensus/canada-crime">
                  Consensus Board
                </Link>
              </Button>
            </div>
          </div>
        </div>

        {/* How it Works */}
        <div className="mb-32">
          <div className="text-center mb-20">
            <h2 className="text-3xl sm:text-4xl lg:text-5xl font-light tracking-tight mb-6 text-foreground">How Truce Works</h2>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
              Our approach combines transparency, technology, and human dialogue
            </p>
          </div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6 sm:gap-8 lg:gap-12">
            <Card className="premium-card elegant-hover border-0 shadow-sm hover:shadow-xl">
              <CardHeader className="pb-6">
                <div className="w-12 h-12 bg-truce-100 rounded-lg flex items-center justify-center mb-4">
                  <Search className="w-6 h-6 text-truce-600" />
                </div>
                <CardTitle className="text-xl font-medium mb-2">
                  Provenance
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-muted-foreground leading-relaxed">
                  Every claim shows exactly where information came from, with clear citations and timestamps.
                </p>
              </CardContent>
            </Card>

            <Card className="premium-card elegant-hover border-0 shadow-sm hover:shadow-xl">
              <CardHeader className="pb-6">
                <div className="w-12 h-12 bg-truce-100 rounded-lg flex items-center justify-center mb-4">
                  <Bot className="w-6 h-6 text-truce-600" />
                </div>
                <CardTitle className="text-xl font-medium mb-2">
                  Multi-Model Analysis
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-muted-foreground leading-relaxed">
                  Multiple AI models evaluate claims independently, showing agreement levels and uncertainty.
                </p>
              </CardContent>
            </Card>

            <Card className="premium-card elegant-hover border-0 shadow-sm hover:shadow-xl">
              <CardHeader className="pb-6">
                <div className="w-12 h-12 bg-truce-100 rounded-lg flex items-center justify-center mb-4">
                  <Handshake className="w-6 h-6 text-truce-600" />
                </div>
                <CardTitle className="text-xl font-medium mb-2">
                  Consensus Finding
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-muted-foreground leading-relaxed">
                  Find areas of agreement through structured dialogue and nonviolent communication.
                </p>
              </CardContent>
            </Card>
          </div>
        </div>

        {/* Demo Section */}
        <div className="mb-32">
          <div className="text-center mb-20">
            <h2 className="text-4xl lg:text-5xl font-light tracking-tight mb-6 text-foreground">Live Demo</h2>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
              Explore our interactive platform with real data and analysis
            </p>
          </div>
          <div className="grid lg:grid-cols-2 gap-12 max-w-5xl mx-auto">
            <Card className="premium-card elegant-hover border-0 shadow-sm hover:shadow-xl p-2">
              <CardHeader className="p-8">
                <div className="flex items-start justify-between mb-4">
                  <div className="w-12 h-12 bg-truce-100 rounded-lg flex items-center justify-center">
                    <Shield className="w-6 h-6 text-truce-600" />
                  </div>
                  <Badge variant="outline" className="bg-truce-50 border-truce-200 text-truce-700 font-medium">Demo</Badge>
                </div>
                <CardTitle className="text-xl font-medium mb-2">Claim Analysis</CardTitle>
                <CardDescription className="text-lg font-medium text-foreground mb-2">
                  "Violent crime in Canada is rising."
                </CardDescription>
              </CardHeader>
              <CardContent className="px-8 pb-8">
                <p className="text-muted-foreground leading-relaxed mb-8">
                  Explore Statistics Canada data, model evaluations, and verifiable credentials
                  for this controversial claim about Canadian crime trends.
                </p>
                <Button asChild className="w-full py-3 elegant-hover">
                  <Link href="/claim/violent-crime-canada" className="flex items-center justify-center gap-2">
                    View Claim Analysis
                    <ArrowRight className="w-4 h-4" />
                  </Link>
                </Button>
              </CardContent>
            </Card>

            <Card className="premium-card elegant-hover border-0 shadow-sm hover:shadow-xl p-2">
              <CardHeader className="p-8">
                <div className="flex items-start justify-between mb-4">
                  <div className="w-12 h-12 bg-truce-100 rounded-lg flex items-center justify-center">
                    <Handshake className="w-6 h-6 text-truce-600" />
                  </div>
                  <Badge variant="outline" className="bg-truce-50 border-truce-200 text-truce-700 font-medium">Interactive</Badge>
                </div>
                <CardTitle className="text-xl font-medium mb-2">Consensus Board</CardTitle>
                <CardDescription className="text-lg font-medium text-foreground mb-2">
                  Find common ground on Canadian crime policy
                </CardDescription>
              </CardHeader>
              <CardContent className="px-8 pb-8">
                <p className="text-muted-foreground leading-relaxed mb-8">
                  Vote on evidence-based statements and discover areas of agreement
                  through our Pol.is-inspired consensus mechanism.
                </p>
                <Button asChild variant="outline" className="w-full py-3 elegant-hover">
                  <Link href="/consensus/canada-crime">
                    Join Discussion
                  </Link>
                </Button>
              </CardContent>
            </Card>
          </div>
        </div>

        {/* Principles */}
        <div className="text-center">
          <div className="mb-20">
            <h2 className="text-4xl lg:text-5xl font-light tracking-tight mb-6 text-foreground">Our Principles</h2>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
              The foundation of transparent dialogue and evidence-based discourse
            </p>
          </div>
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8 max-w-6xl mx-auto">
            <div className="group">
              <div className="w-16 h-16 bg-truce-100 rounded-xl flex items-center justify-center mb-6 mx-auto group-hover:bg-truce-200 transition-colors">
                <Shield className="w-8 h-8 text-truce-600" />
              </div>
              <h3 className="text-lg font-medium mb-4 text-foreground">Transparency</h3>
              <p className="text-muted-foreground leading-relaxed">All sources, methods, and model responses are visible and verifiable</p>
            </div>
            <div className="group">
              <div className="w-16 h-16 bg-truce-100 rounded-xl flex items-center justify-center mb-6 mx-auto group-hover:bg-truce-200 transition-colors">
                <Download className="w-8 h-8 text-truce-600" />
              </div>
              <h3 className="text-lg font-medium mb-4 text-foreground">Reproducibility</h3>
              <p className="text-muted-foreground leading-relaxed">Download replay bundles to independently verify any claim</p>
            </div>
            <div className="group">
              <div className="w-16 h-16 bg-truce-100 rounded-xl flex items-center justify-center mb-6 mx-auto group-hover:bg-truce-200 transition-colors">
                <Handshake className="w-8 h-8 text-truce-600" />
              </div>
              <h3 className="text-lg font-medium mb-4 text-foreground">De-escalation</h3>
              <p className="text-muted-foreground leading-relaxed">Built-in nonviolent communication and dialogue tools</p>
            </div>
            <div className="group">
              <div className="w-16 h-16 bg-truce-100 rounded-xl flex items-center justify-center mb-6 mx-auto group-hover:bg-truce-200 transition-colors">
                <Search className="w-8 h-8 text-truce-600" />
              </div>
              <h3 className="text-lg font-medium mb-4 text-foreground">Consensus</h3>
              <p className="text-muted-foreground leading-relaxed">Surface areas of agreement, not just points of disagreement</p>
            </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
