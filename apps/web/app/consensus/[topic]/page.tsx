"use client";

import { useState, useEffect } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { ThumbsUp, ThumbsDown, Minus, MessageSquare, TrendingUp, Users } from "lucide-react";

interface ConsensusStatement {
  id: string;
  text: string;
  topic: string;
  agree_count: number;
  disagree_count: number;
  pass_count: number;
  agree_rate: number;
  cluster_id?: number;
  evidence_links: string[];
  created_at: string;
}

interface ConsensusSummary {
  topic: string;
  statement_count: number;
  vote_count: number;
  overall_consensus: ConsensusStatement[];
  divisive: ConsensusStatement[];
  clusters: Array<{
    id: number;
    statements: string[];
    user_count: number;
    avg_agreement: number;
    description: string;
  }>;
  updated_at: string;
}

interface UserVotes {
  [statementId: string]: "agree" | "disagree" | "pass";
}

export default function ConsensusPage({ params }: { params: { topic: string } }) {
  const [summary, setSummary] = useState<ConsensusSummary | null>(null);
  const [userVotes, setUserVotes] = useState<UserVotes>({});
  const [sessionId] = useState(() => Math.random().toString(36).substring(7));
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"consensus" | "divisive" | "clusters">("consensus");

  useEffect(() => {
    loadConsensusSummary();
  }, [params.topic]);

  const loadConsensusSummary = async () => {
    try {
      const response = await fetch(`/api/consensus/${params.topic}/summary`);
      if (response.ok) {
        const data = await response.json();
        setSummary(data);
      }
    } catch (error) {
      console.error('Error loading consensus:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleVote = async (statementId: string, vote: "agree" | "disagree" | "pass") => {
    try {
      const response = await fetch(`/api/consensus/${params.topic}/votes`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          statement_id: statementId,
          vote: vote,
          session_id: sessionId
        }),
      });

      if (response.ok) {
        setUserVotes(prev => ({
          ...prev,
          [statementId]: vote
        }));
        
        // Reload summary to get updated counts
        await loadConsensusSummary();
      }
    } catch (error) {
      console.error('Error voting:', error);
    }
  };

  const StatementCard = ({ statement }: { statement: ConsensusStatement }) => {
    const totalVotes = statement.agree_count + statement.disagree_count;
    const userVote = userVotes[statement.id];
    
    return (
      <Card className="mb-4">
        <CardContent className="p-4">
          <p className="mb-3 text-sm leading-relaxed">{statement.text}</p>
          
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <span>{totalVotes} votes</span>
              {statement.agree_rate > 0 && (
                <Badge variant={statement.agree_rate >= 0.7 ? "success" : "secondary"} className="text-xs">
                  {Math.round(statement.agree_rate * 100)}% agree
                </Badge>
              )}
            </div>
            
            <div className="flex items-center gap-1">
              <Button
                variant={userVote === "disagree" ? "default" : "outline"}
                size="sm"
                onClick={() => handleVote(statement.id, "disagree")}
                className="h-8 px-2"
              >
                <ThumbsDown className="w-3 h-3" />
                <span className="ml-1 text-xs">{statement.disagree_count}</span>
              </Button>
              
              <Button
                variant={userVote === "pass" ? "default" : "outline"}
                size="sm"
                onClick={() => handleVote(statement.id, "pass")}
                className="h-8 px-2"
              >
                <Minus className="w-3 h-3" />
                <span className="ml-1 text-xs">{statement.pass_count}</span>
              </Button>
              
              <Button
                variant={userVote === "agree" ? "default" : "outline"}
                size="sm"
                onClick={() => handleVote(statement.id, "agree")}
                className="h-8 px-2"
              >
                <ThumbsUp className="w-3 h-3" />
                <span className="ml-1 text-xs">{statement.agree_count}</span>
              </Button>
            </div>
          </div>
          
          {totalVotes > 0 && (
            <div className="mt-3">
              <Progress 
                value={statement.agree_rate * 100} 
                className="h-2"
              />
            </div>
          )}
        </CardContent>
      </Card>
    );
  };

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="max-w-4xl mx-auto text-center">
          <p>Loading consensus data...</p>
        </div>
      </div>
    );
  }

  if (!summary) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="max-w-4xl mx-auto text-center">
          <h1 className="text-2xl font-bold mb-4">Topic Not Found</h1>
          <p>The consensus topic "{params.topic}" was not found.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold mb-4">Consensus Board</h1>
          <p className="text-muted-foreground mb-4">
            Find common ground on <strong>{summary.topic.replace('-', ' ')}</strong> through evidence-based dialogue.
          </p>
          
          <div className="flex items-center gap-4 text-sm">
            <div className="flex items-center gap-1">
              <MessageSquare className="w-4 h-4" />
              <span>{summary.statement_count} statements</span>
            </div>
            <div className="flex items-center gap-1">
              <Users className="w-4 h-4" />
              <span>{summary.vote_count} votes</span>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="mb-6">
          <div className="flex gap-1 bg-muted rounded-lg p-1">
            <button
              onClick={() => setActiveTab("consensus")}
              className={`flex-1 py-2 px-4 rounded-md text-sm font-medium transition-colors ${
                activeTab === "consensus" 
                  ? "bg-background text-foreground shadow-sm" 
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <TrendingUp className="w-4 h-4 inline mr-2" />
              Consensus ({summary.overall_consensus.length})
            </button>
            <button
              onClick={() => setActiveTab("divisive")}
              className={`flex-1 py-2 px-4 rounded-md text-sm font-medium transition-colors ${
                activeTab === "divisive" 
                  ? "bg-background text-foreground shadow-sm" 
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <MessageSquare className="w-4 h-4 inline mr-2" />
              Divisive ({summary.divisive.length})
            </button>
            <button
              onClick={() => setActiveTab("clusters")}
              className={`flex-1 py-2 px-4 rounded-md text-sm font-medium transition-colors ${
                activeTab === "clusters" 
                  ? "bg-background text-foreground shadow-sm" 
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <Users className="w-4 h-4 inline mr-2" />
              Clusters ({summary.clusters.length})
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="space-y-6">
          {activeTab === "consensus" && (
            <div>
              {summary.overall_consensus.length > 0 ? (
                <>
                  <h2 className="text-xl font-semibold mb-4 text-green-700">
                    Areas of Agreement
                  </h2>
                  <p className="text-muted-foreground mb-6 text-sm">
                    Statements with high agreement rates across participants.
                  </p>
                  {summary.overall_consensus.map(statement => (
                    <StatementCard key={statement.id} statement={statement} />
                  ))}
                </>
              ) : (
                <Card>
                  <CardContent className="p-8 text-center">
                    <h3 className="text-lg font-medium mb-2">No Clear Consensus Yet</h3>
                    <p className="text-muted-foreground">
                      Vote on statements to help identify areas of agreement.
                    </p>
                  </CardContent>
                </Card>
              )}
            </div>
          )}

          {activeTab === "divisive" && (
            <div>
              {summary.divisive.length > 0 ? (
                <>
                  <h2 className="text-xl font-semibold mb-4 text-yellow-700">
                    Divisive Statements
                  </h2>
                  <p className="text-muted-foreground mb-6 text-sm">
                    Statements that generate mixed reactions and deserve further discussion.
                  </p>
                  {summary.divisive.map(statement => (
                    <StatementCard key={statement.id} statement={statement} />
                  ))}
                </>
              ) : (
                <Card>
                  <CardContent className="p-8 text-center">
                    <h3 className="text-lg font-medium mb-2">No Divisive Statements Yet</h3>
                    <p className="text-muted-foreground">
                      As more people vote, divisive statements will appear here.
                    </p>
                  </CardContent>
                </Card>
              )}
            </div>
          )}

          {activeTab === "clusters" && (
            <div>
              {summary.clusters.length > 0 ? (
                <>
                  <h2 className="text-xl font-semibold mb-4">
                    Opinion Clusters
                  </h2>
                  <p className="text-muted-foreground mb-6 text-sm">
                    Groups of participants with similar voting patterns.
                  </p>
                  {summary.clusters.map(cluster => (
                    <Card key={cluster.id} className="mb-4">
                      <CardHeader>
                        <CardTitle className="text-lg">
                          Cluster {cluster.id + 1}
                        </CardTitle>
                        <CardDescription>
                          {cluster.user_count} participants • {Math.round(cluster.avg_agreement * 100)}% internal agreement
                        </CardDescription>
                      </CardHeader>
                      <CardContent>
                        <p className="text-sm text-muted-foreground">
                          {cluster.description}
                        </p>
                      </CardContent>
                    </Card>
                  ))}
                </>
              ) : (
                <Card>
                  <CardContent className="p-8 text-center">
                    <h3 className="text-lg font-medium mb-2">Clustering Not Available</h3>
                    <p className="text-muted-foreground">
                      Need more votes to identify opinion clusters.
                    </p>
                  </CardContent>
                </Card>
              )}
            </div>
          )}
        </div>

        {/* Footer Info */}
        <div className="mt-12 pt-8 border-t">
          <div className="text-xs text-muted-foreground space-y-2">
            <p>
              <strong>How it works:</strong> Vote on statements to find common ground. 
              Consensus emerges from areas of high agreement across diverse participants.
            </p>
            <p>
              <strong>Inspired by Pol.is:</strong> This approach helps surface shared values 
              and bridge divides in contentious topics.
            </p>
            <p>
              <strong>Privacy:</strong> Votes are anonymous and tied only to session IDs. 
              No personal information is collected.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
