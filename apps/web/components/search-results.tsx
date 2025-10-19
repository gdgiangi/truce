"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Loader2, Plus, ArrowRight, CheckCircle, AlertCircle, Search, Bot, FileText, X } from "lucide-react";
import { Progress } from "@/components/ui/progress";
import Link from "next/link";

interface ClaimSearchHit {
  slug: string;
  text: string;
  score: number;
}

interface EvidenceSearchHit {
  claim_slug: string;
  evidence_id: string;
  snippet: string;
  publisher: string;
  url: string;
  score: number;
}

interface SearchResponse {
  query: string;
  claims: ClaimSearchHit[];
  evidence: EvidenceSearchHit[];
  suggestion_slug?: string;
}

const adjudicatorUrl = process.env.NEXT_PUBLIC_ADJUDICATOR_API_URL || "http://localhost:8000";

function formatScore(score: number): string {
  const relevance = 1 / (1 + score);
  return relevance.toFixed(2);
}

interface ProgressEvent {
  stage: string;
  message: string;
  timestamp: string;
  evidence_count?: number;
  model_count?: number;
  slug?: string;
  processed?: number;
  total?: number;
  unique_evidence?: number;
  progress_pct?: number;
  raw_sources?: number;
}

interface SearchResultsProps {
  initialQuery: string;
  initialResults: SearchResponse | null;
}

function ClaimCreationProgress({ 
  progress, 
  onComplete, 
  onCancel, 
  sessionId,
  canCancel = true 
}: { 
  progress: ProgressEvent[]; 
  onComplete: (slug: string) => void;
  onCancel: () => void;
  sessionId: string;
  canCancel?: boolean;
}) {
  const currentEvent = progress[progress.length - 1];
  
  // Progress calculation based on stages
  const getProgressValue = (stage: string, event?: ProgressEvent) => {
    // If we have granular progress from the event, use it
    if (event?.progress_pct !== undefined) {
      // Scale evidence processing (which is 30-60% range) to fit within our overall progress
      return 30 + (event.progress_pct * 0.3);
    }
    
    switch (stage) {
      case 'initializing': return 5;
      case 'searching': return 15;
      case 'gathering_sources': return 25;
      case 'processing_sources': return 30;
      case 'processing_evidence': return 45; // Will be overridden by progress_pct
      case 'sources_limited': return 40;
      case 'evidence_found': return 60;
      case 'evaluating': return 75;
      case 'evaluation_complete': return 95;
      case 'evaluation_error': return 90;
      case 'evaluation_timeout': return 85;
      case 'complete': return 100;
      case 'cancelled': return 0;
      case 'timeout_warning': return 50;
      case 'api_error': return 45;
      default: return 20; // Default progress for unknown stages
    }
  };

  const getStageIcon = (stage: string) => {
    switch (stage) {
      case 'initializing': return <FileText className="w-4 h-4" />;
      case 'searching':
      case 'gathering_sources':
      case 'processing_sources': return <Search className="w-4 h-4" />;
      case 'processing_evidence': return <Loader2 className="w-4 h-4 animate-spin text-blue-600" />;
      case 'sources_limited': return <AlertCircle className="w-4 h-4 text-amber-600" />;
      case 'evidence_found': return <CheckCircle className="w-4 h-4 text-green-600" />;
      case 'evaluating':
      case 'evaluation_complete': return <Bot className="w-4 h-4" />;
      case 'evaluation_error':
      case 'evaluation_timeout': return <AlertCircle className="w-4 h-4 text-amber-600" />;
      case 'complete': return <CheckCircle className="w-4 h-4 text-green-600" />;
      case 'cancelled': return <AlertCircle className="w-4 h-4 text-gray-600" />;
      case 'error': return <AlertCircle className="w-4 h-4 text-red-600" />;
      case 'timeout_warning':
      case 'api_error': return <AlertCircle className="w-4 h-4 text-orange-600" />;
      default: return <Loader2 className="w-4 h-4 animate-spin" />;
    }
  };

  const handleCancel = async () => {
    try {
      await fetch(`${adjudicatorUrl}/claims/progress/${sessionId}`, {
        method: 'DELETE',
      });
      onCancel();
    } catch (error) {
      console.error('Failed to cancel claim creation:', error);
    }
  };

  useEffect(() => {
    if (currentEvent?.stage === 'complete' && currentEvent?.slug) {
      setTimeout(() => onComplete(currentEvent.slug!), 1000);
    } else if (currentEvent?.stage === 'cancelled') {
      setTimeout(() => onCancel(), 500);
    }
  }, [currentEvent, onComplete, onCancel]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          {getStageIcon(currentEvent?.stage || '')}
          <h3 className="text-lg font-semibold">Creating Claim Analysis</h3>
        </div>
        {canCancel && currentEvent?.stage !== 'complete' && currentEvent?.stage !== 'cancelled' && (
          <Button 
            variant="outline" 
            size="sm" 
            onClick={handleCancel}
            className="text-red-600 hover:text-red-700 hover:border-red-300"
          >
            <X className="w-4 h-4 mr-1" />
            Cancel
          </Button>
        )}
      </div>
      
      <Progress 
        value={getProgressValue(currentEvent?.stage || '', currentEvent)} 
        className="w-full transition-all duration-300" 
      />
      
      <div className="space-y-2">
        {progress.map((event, index) => (
          <div 
            key={index} 
            className={`flex items-start gap-3 p-3 rounded-lg border transition-colors ${
              index === progress.length - 1 
                ? 'bg-truce-50 border-truce-200' 
                : 'bg-gray-50 border-gray-200'
            }`}
          >
            <div className="flex-shrink-0 mt-0.5">
              {getStageIcon(event.stage)}
            </div>
            <div className="flex-1">
              <p className="text-sm font-medium">{event.message}</p>
              {event.evidence_count && (
                <p className="text-xs text-muted-foreground mt-1">
                  Found {event.evidence_count} evidence sources
                </p>
              )}
              {event.model_count && (
                <p className="text-xs text-muted-foreground mt-1">
                  Evaluated by {event.model_count} AI models
                </p>
              )}
              {event.raw_sources && (
                <p className="text-xs text-muted-foreground mt-1">
                  Retrieved {event.raw_sources} raw sources
                </p>
              )}
              {event.processed && event.total && (
                <div className="mt-2">
                  <div className="flex justify-between text-xs text-muted-foreground mb-1">
                    <span>{event.processed}/{event.total} processed</span>
                    <span>{event.progress_pct}%</span>
                  </div>
                  <Progress value={event.progress_pct || 0} className="h-1" />
                  {event.unique_evidence && (
                    <p className="text-xs text-muted-foreground mt-1">
                      {event.unique_evidence} unique sources found
                    </p>
                  )}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {currentEvent?.stage === 'cancelled' && (
        <div className="p-3 bg-gray-50 border border-gray-200 rounded-lg">
          <p className="text-sm text-gray-800">
            Claim creation was cancelled. You can start a new analysis at any time.
          </p>
        </div>
      )}

      {currentEvent?.stage === 'error' && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-sm text-red-800">
            Something went wrong during claim creation. Please try again.
          </p>
        </div>
      )}

      {(currentEvent?.stage === 'timeout_warning' || currentEvent?.stage === 'api_error') && (
        <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg">
          <p className="text-sm text-amber-800">
            Some data sources are experiencing delays, but the analysis continues with available information.
          </p>
        </div>
      )}
    </div>
  );
}

export function SearchResults({ initialQuery, initialResults }: SearchResultsProps) {
  const router = useRouter();
  const [isCreating, setIsCreating] = useState(false);
  const [results, setResults] = useState(initialResults);
  const [progress, setProgress] = useState<ProgressEvent[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string>('');
  const eventSourceRef = useRef<EventSource | null>(null);

  const hasResults = results && (results.claims.length > 0 || results.evidence.length > 0);

  // Clean up event source on unmount
  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, []);

  const handleCreateClaim = async () => {
    if (!initialQuery.trim() || isCreating) return;

    console.log('Starting claim creation for:', initialQuery);
    console.log('Adjudicator URL:', adjudicatorUrl);

    setIsCreating(true);
    setProgress([]);
    
    try {
      // Start the async claim creation
      console.log('Calling create-async endpoint...');
      const response = await fetch(`${adjudicatorUrl}/claims/create-async`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: initialQuery.trim() })
      });

      console.log('Create-async response status:', response.status);

      if (response.ok) {
        const { session_id } = await response.json();
        console.log('Got session ID:', session_id);
        setCurrentSessionId(session_id);
        
        // Set up Server-Sent Events to listen for progress
        const sseUrl = `${adjudicatorUrl}/claims/progress/${session_id}`;
        console.log('Setting up SSE connection to:', sseUrl);
        const eventSource = new EventSource(sseUrl);
        eventSourceRef.current = eventSource;
        
        eventSource.onopen = () => {
          console.log('SSE connection opened');
        };
        
        eventSource.onmessage = (event) => {
          console.log('SSE message received:', event.data);
          try {
            const progressEvent: ProgressEvent = JSON.parse(event.data);
            
            // Ignore keepalive events
            if (progressEvent.stage === 'keepalive') {
              console.log('Keepalive event ignored');
              return;
            }
            
            console.log('Progress event:', progressEvent);
            setProgress(prev => [...prev, progressEvent]);
          } catch (error) {
            console.error('Error parsing progress event:', error);
          }
        };

        eventSource.onerror = (error) => {
          console.error('SSE Error:', error);
          eventSource.close();
          setIsCreating(false);
        };
      } else {
        throw new Error('Failed to start claim creation');
      }
    } catch (error) {
      console.error("Failed to create claim:", error);
      setIsCreating(false);
    }
  };

  const handleCreationComplete = (slug: string) => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }
    setIsCreating(false);
    router.push(`/claim/${slug}`);
  };

  const handleCreationCancel = () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }
    setIsCreating(false);
    setProgress([]);
    setCurrentSessionId('');
  };

  if (!initialQuery.trim()) {
    return (
      <Card className="border-dashed">
        <CardContent className="py-10 text-center text-muted-foreground">
          Enter a query to discover relevant claims and citations.
        </CardContent>
      </Card>
    );
  }

  if (!hasResults) {
    if (isCreating) {
      return (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Analyzing &ldquo;{initialQuery}&rdquo;</CardTitle>
              <CardDescription>
                Creating a comprehensive analysis with evidence and AI evaluation
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ClaimCreationProgress 
                progress={progress} 
                onComplete={handleCreationComplete}
                onCancel={handleCreationCancel}
                sessionId={currentSessionId}
              />
            </CardContent>
          </Card>
        </div>
      );
    }

    return (
      <div className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              No existing claims found
            </CardTitle>
            <CardDescription>
              No results found for <span className="font-medium">&ldquo;{initialQuery}&rdquo;</span>.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-col gap-4">
              <p className="text-muted-foreground">
                This appears to be a new topic. We can create a comprehensive claim analysis 
                by gathering evidence from multiple sources and running it through our AI panel.
              </p>
              <Button 
                onClick={handleCreateClaim} 
                disabled={isCreating}
                className="w-full sm:w-fit"
              >
                <Plus className="w-4 h-4 mr-2" />
                Create New Claim Analysis
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="grid gap-8 lg:grid-cols-[1.2fr_1fr]">
      <div className="space-y-6">
        <h2 className="text-xl font-semibold">Claims</h2>
        {results!.claims.map((claim) => (
          <Card key={claim.slug} className="transition hover:border-truce-400/60">
            <CardHeader>
              <CardTitle className="text-lg font-medium">
                <Link href={`/claim/${claim.slug}`} className="hover:text-truce-600">
                  {claim.text}
                </Link>
              </CardTitle>
              <div className="flex items-center justify-between">
                <Badge variant="outline" className="w-fit">
                  Relevance {formatScore(claim.score)}
                </Badge>
                <Button asChild size="sm" variant="ghost">
                  <Link href={`/claim/${claim.slug}`}>
                    View Analysis <ArrowRight className="w-4 h-4 ml-1" />
                  </Link>
                </Button>
              </div>
            </CardHeader>
          </Card>
        ))}
        
        {results!.claims.length === 0 && (
          <div className="space-y-4">
            <p className="text-sm text-muted-foreground">No direct claim matches.</p>
            
            {isCreating ? (
              <Card>
                <CardHeader>
                  <CardTitle className="text-base font-medium">
                    Creating Analysis for &ldquo;{initialQuery}&rdquo;
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <ClaimCreationProgress 
                    progress={progress} 
                    onComplete={handleCreationComplete}
                    onCancel={handleCreationCancel}
                    sessionId={currentSessionId}
                  />
                </CardContent>
              </Card>
            ) : (
              <Card className="border-dashed">
                <CardHeader>
                  <CardTitle className="text-base font-medium">
                    Create New Claim Analysis
                  </CardTitle>
                  <CardDescription>
                    Generate a comprehensive analysis for &ldquo;{initialQuery}&rdquo;
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <Button 
                    onClick={handleCreateClaim} 
                    disabled={isCreating}
                    variant="outline"
                    className="w-full"
                  >
                    <Plus className="w-4 h-4 mr-2" />
                    Create Analysis
                  </Button>
                </CardContent>
              </Card>
            )}
          </div>
        )}
      </div>

      <div className="space-y-6">
        <h2 className="text-xl font-semibold">Evidence</h2>
        {results!.evidence.map((evidence) => (
          <Card key={evidence.evidence_id} className="transition hover:border-truce-400/60">
            <CardHeader className="space-y-2">
              <div className="flex items-center gap-2 text-xs uppercase tracking-wide text-muted-foreground">
                <span>{evidence.publisher}</span>
                <Badge variant="outline">Relevance {formatScore(evidence.score)}</Badge>
              </div>
              <CardTitle className="text-base font-medium leading-6">
                <Link href={`/claim/${evidence.claim_slug}`} className="hover:text-truce-600">
                  {evidence.snippet}
                </Link>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <Link 
                href={evidence.url} 
                className="text-sm text-truce-600 hover:underline" 
                target="_blank" 
                rel="noopener noreferrer"
              >
                View source
              </Link>
            </CardContent>
          </Card>
        ))}
        {results!.evidence.length === 0 && (
          <p className="text-sm text-muted-foreground">No supporting evidence found.</p>
        )}
      </div>
    </div>
  );
}
