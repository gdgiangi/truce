"use client";

import { useEffect, useState, useRef, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { 
  Loader2, Search, FileText, Bot, AlertCircle, 
  BookOpen, Building, Newspaper, Database, Zap
} from "lucide-react";

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
  search_strategy?: string;
  agent_name?: string;
  reasoning?: string;
  error_message?: string;
  sources_found?: string[];
}

const adjudicatorUrl = "http://localhost:8000";

function getAgentIcon(agentName?: string, searchStrategy?: string) {
  if (searchStrategy === 'academic') return <BookOpen className="w-4 h-4 text-blue-500" />;
  if (searchStrategy === 'government') return <Building className="w-4 h-4 text-green-500" />;
  if (searchStrategy === 'news') return <Newspaper className="w-4 h-4 text-purple-500" />;
  if (searchStrategy === 'direct') return <Search className="w-4 h-4 text-orange-500" />;
  
  if (agentName?.includes('claude')) return <Bot className="w-4 h-4 text-indigo-500" />;
  if (agentName?.includes('gpt')) return <Zap className="w-4 h-4 text-emerald-500" />;
  if (agentName?.includes('gemini')) return <Database className="w-4 h-4 text-red-500" />;
  
  return <FileText className="w-4 h-4 text-truce-500" />;
}

function getAgentName(searchStrategy?: string, agentName?: string): string {
  if (searchStrategy === 'academic') return 'Academic Researcher';
  if (searchStrategy === 'government') return 'Policy Analyst';
  if (searchStrategy === 'news') return 'News Investigator';
  if (searchStrategy === 'direct') return 'Evidence Hunter';
  
  if (agentName?.includes('claude')) return 'Claude Analyst';
  if (agentName?.includes('gpt')) return 'GPT Evaluator';
  if (agentName?.includes('gemini')) return 'Gemini Reasoner';
  
  return 'System Agent';
}

function getStatusColor(stage: string, hasError?: boolean): string {
  if (hasError) return 'border-red-200 bg-red-50';
  if (stage === 'complete') return 'border-green-200 bg-green-50';
  if (stage === 'error') return 'border-red-200 bg-red-50';
  if (stage.includes('evaluating') || stage.includes('reasoning')) return 'border-blue-200 bg-blue-50';
  return 'border-truce-200 bg-truce-50';
}

function getSystemStatus(progress: ProgressEvent[]): { 
  activeAgents: number, 
  totalEvidence: number, 
  currentActivity: string,
  hasErrors: boolean 
} {
  const recentEvents = progress.slice(-10);
  const activeAgents = new Set(recentEvents.map(e => e.agent_name || e.search_strategy || 'system')).size;
  const totalEvidence = recentEvents.reduce((sum, e) => sum + (e.evidence_count || 0), 0);
  const hasErrors = recentEvents.some(e => e.stage === 'error' || e.error_message);
  
  const latestEvent = progress[progress.length - 1];
  let currentActivity = latestEvent?.message || 'Processing...';
  
  if (latestEvent?.stage === 'complete') currentActivity = 'Analysis complete';
  else if (latestEvent?.stage === 'error') currentActivity = 'Encountered issue';
  else if (latestEvent?.reasoning) currentActivity = 'Agent reasoning';
  
  return { activeAgents, totalEvidence, currentActivity, hasErrors };
}

function AnalyzingContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const sessionId = searchParams.get('session');
  const query = searchParams.get('q');
  
  const [progress, setProgress] = useState<ProgressEvent[]>([]);
  const [currentStage, setCurrentStage] = useState<string>('initializing');
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!sessionId) {
      router.push('/');
      return;
    }

    const sseUrl = `${adjudicatorUrl}/claims/progress/${sessionId}`;
    const eventSource = new EventSource(sseUrl);
    eventSourceRef.current = eventSource;
    
    eventSource.onmessage = (event) => {
      try {
        const progressEvent: ProgressEvent = JSON.parse(event.data);
        
        if (progressEvent.stage === 'keepalive') {
          return;
        }
        
        setProgress(prev => [...prev, progressEvent]);
        setCurrentStage(progressEvent.stage);

        // Redirect to claim page when complete
        if (progressEvent.stage === 'complete' && progressEvent.slug) {
          setTimeout(() => {
            eventSource.close();
            router.push(`/claim/${progressEvent.slug}`);
          }, 800);
        }
      } catch (error) {
        console.error('Error parsing progress event:', error);
      }
    };

    eventSource.onerror = (error) => {
      console.error('SSE Error:', error);
      eventSource.close();
    };

    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, [sessionId, router]);

  const systemStatus = getSystemStatus(progress);
  const recentEvents = progress.slice(-8).reverse();

  return (
    <div className="min-h-screen bg-gradient-to-b from-background to-truce-50/20 p-4">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <Card className="border-0 shadow-lg mb-6">
          <CardHeader className="pb-4">
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-xl font-light flex items-center gap-3">
                  <div className="relative">
                    <div className="w-3 h-3 bg-truce-500 rounded-full animate-pulse" />
                    <div className="absolute top-0 left-0 w-3 h-3 bg-truce-300 rounded-full animate-ping" />
                  </div>
                  Multi-Agent Analysis
                </CardTitle>
                {query && (
                  <p className="text-sm text-muted-foreground mt-1">
                    &ldquo;{query}&rdquo;
                  </p>
                )}
              </div>
              
              <div className="flex items-center gap-4 text-xs text-muted-foreground">
                <div className="flex items-center gap-1">
                  <Bot className="w-3 h-3" />
                  <span>{systemStatus.activeAgents} agents active</span>
                </div>
                <div className="flex items-center gap-1">
                  <Database className="w-3 h-3" />
                  <span>{systemStatus.totalEvidence} evidence found</span>
                </div>
              </div>
            </div>
            
            <div className="text-sm font-medium text-truce-600 mt-2">
              {systemStatus.currentActivity}
            </div>
          </CardHeader>
        </Card>

        {/* Agent Activity Feed */}
        <div className="space-y-3">
          {recentEvents.length === 0 ? (
            <Card className="border-dashed">
              <CardContent className="py-8 text-center text-muted-foreground">
                <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2" />
                <p>Initializing agents...</p>
              </CardContent>
            </Card>
          ) : (
            recentEvents.map((event, index) => (
              <Card 
                key={index} 
                className={`transition-all duration-300 ${getStatusColor(event.stage, !!event.error_message)}`}
              >
                <CardContent className="py-4">
                  <div className="flex items-start gap-3">
                    <div className="flex-shrink-0 mt-1">
                      {event.error_message ? (
                        <AlertCircle className="w-4 h-4 text-red-500" />
                      ) : (
                        getAgentIcon(event.agent_name, event.search_strategy)
                      )}
                    </div>
                    
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium">
                            {getAgentName(event.search_strategy, event.agent_name)}
                          </span>
                          {event.search_strategy && (
                            <span className="px-2 py-1 text-xs bg-white/50 rounded-full">
                              {event.search_strategy}
                            </span>
                          )}
                        </div>
                        <span className="text-xs text-muted-foreground">
                          {new Date(event.timestamp).toLocaleTimeString()}
                        </span>
                      </div>
                      
                      <p className="text-sm text-foreground mb-2">
                        {event.message}
                      </p>
                      
                      {event.reasoning && (
                        <div className="bg-white/30 rounded p-2 text-xs text-muted-foreground mb-2">
                          <strong>Reasoning:</strong> {event.reasoning}
                        </div>
                      )}
                      
                      {event.error_message && (
                        <div className="bg-red-100 border border-red-200 rounded p-2 text-xs text-red-700 mb-2">
                          <strong>Issue:</strong> {event.error_message}
                        </div>
                      )}
                      
                      <div className="flex flex-wrap gap-3 text-xs text-muted-foreground">
                        {event.evidence_count && (
                          <span>📄 {event.evidence_count} sources found</span>
                        )}
                        {event.processed && event.total && (
                          <span>⚡ {event.processed}/{event.total} processed</span>
                        )}
                        {event.unique_evidence && (
                          <span>✨ {event.unique_evidence} unique</span>
                        )}
                        {event.sources_found && event.sources_found.length > 0 && (
                          <span>🔗 Found: {event.sources_found.slice(0, 2).join(', ')}</span>
                        )}
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))
          )}
        </div>

        {/* Status Footer */}
        {systemStatus.hasErrors && (
          <Card className="mt-6 border-red-200 bg-red-50">
            <CardContent className="py-4 text-center">
              <div className="flex items-center justify-center gap-2 text-red-700">
                <AlertCircle className="w-4 h-4" />
                <span className="text-sm font-medium">
                  Some agents encountered issues, but analysis continues with available data
                </span>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}

export default function AnalyzingPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-gradient-to-b from-background to-truce-50/20 flex items-center justify-center px-4">
        <div className="w-full max-w-2xl">
          <Card className="border-0 shadow-2xl">
            <CardHeader className="space-y-6 pb-8">
              <div className="flex items-center justify-center">
                <div className="relative">
                  <div className="absolute inset-0 bg-truce-500/20 rounded-full blur-xl animate-pulse" />
                  <div className="relative bg-truce-100 rounded-full p-6">
                    <Loader2 className="w-5 h-5 animate-spin text-truce-500" />
                  </div>
                </div>
              </div>
              <div className="text-center space-y-2">
                <CardTitle className="text-2xl font-light">Loading...</CardTitle>
              </div>
            </CardHeader>
          </Card>
        </div>
      </div>
    }>
      <AnalyzingContent />
    </Suspense>
  );
}

