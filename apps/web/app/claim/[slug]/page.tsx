import React from "react";
import { notFound } from "next/navigation";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { ExternalLink, Download, Shield, AlertTriangle, BarChart3, Bot } from "lucide-react";
import { ProviderLogo } from "@/components/provider-logo";

type PanelVerdictValue = "true" | "false" | "mixed" | "unknown";

interface Evidence {
  id: string;
  url: string;
  publisher: string;
  published_at?: string;
  snippet: string;
  provenance: string;
  domain?: string;
}

interface PanelModelVerdict {
  provider_id: string;
  model: string;
  approval_argument: ArgumentWithEvidence;
  refusal_argument: ArgumentWithEvidence;
}

interface ArgumentWithEvidence {
  argument: string;
  evidence_ids: string[];
  confidence: number;
}

interface PanelSummary {
  support_confidence: number;
  refute_confidence: number;
  model_count: number;
  verdict?: PanelVerdictValue;
}

interface PanelResult {
  prompt: Record<string, unknown>;
  models: PanelModelVerdict[];
  summary: PanelSummary;
  generated_at: string;
}

interface ModelAssessment {
  id: string;
  model_name: string;
  verdict: "supports" | "refutes" | "mixed" | "uncertain";
  confidence: number;
  citations: string[];
  rationale: string;
  created_at: string;
}

interface Claim {
  id: string;
  text: string;
  topic: string;
  entities: string[];
  evidence: Evidence[];
  model_assessments: ModelAssessment[];
  human_reviews: any[];
  created_at: string;
  updated_at: string;
}

interface ClaimResponse {
  claim: Claim;
  consensus_score?: number;
  provenance_verified: boolean;
  replay_bundle_url?: string;
  panel?: PanelResult;
}

const adjudicatorUrl = process.env.ADJUDICATOR_API_URL || "http://localhost:8000";

async function getClaim(slug: string): Promise<ClaimResponse | null> {
  try {
    const response = await fetch(`${adjudicatorUrl}/claims/${slug}`, {
      cache: 'no-store'
    });
    
    if (!response.ok) {
      return null;
    }
    
    return response.json();
  } catch (error) {
    console.error('Error fetching claim:', error);
    return null;
  }
}

function getVerdictColor(verdict: string): string {
  switch (verdict.toLowerCase()) {
    case "supports":
    case "true":
      return "supports";
    case "refutes":
    case "false":
      return "refutes";
    case "mixed":
      return "mixed";
    case "uncertain":
    case "unknown":
      return "uncertain";
    default:
      return "secondary";
  }
}

function getProviderInfo(modelName: string): { name: string; logo: string } {
  const name = modelName.toLowerCase();

  if (name.includes("gpt") || name.includes("openai") || name.startsWith("o1")) {
    return {
      name: "OpenAI",
      logo: "https://www.svgrepo.com/show/306500/openai.svg",
    };
  }

  if (name.includes("grok")) {
    return {
      name: "xAI Grok",
      logo: "https://upload.wikimedia.org/wikipedia/commons/5/53/X_logo_2023_original.svg",
    };
  }

  if (name.includes("gemini") || name.includes("google")) {
    return {
      name: "Google Gemini",
      logo: "https://www.svgrepo.com/show/475656/google-color.svg",
    };
  }

  if (name.includes("claude") || name.includes("anthropic") || name.includes("sonnet")) {
    return {
      name: "Anthropic",
      logo: "https://registry.npmmirror.com/@lobehub/icons-static-png/1.64.0/files/light/anthropic.png",
    };
  }

  if (name.includes("demo")) {
    return {
      name: "Demo Model",
      logo: "",
    };
  }

  return {
    name: "AI Model",
    logo: "",
  };
}

function formatPanelVerdict(verdict: PanelVerdictValue): string {
  switch (verdict) {
    case "true":
      return "Supports";
    case "false":
      return "Refutes";
    case "mixed":
      return "Mixed";
    case "unknown":
    default:
      return "Unknown";
  }
}

function mapLegacyVerdict(verdict: string): PanelVerdictValue {
  const lower = verdict.toLowerCase();
  if (lower === "supports") return "true";
  if (lower === "refutes") return "false";
  if (lower === "mixed") return "mixed";
  return "unknown";
}

function truncate(text: string, maxLength = 140): string {
  if (text.length <= maxLength) {
    return text;
  }
  return `${text.slice(0, maxLength - 1)}…`;
}

function AggregateVerdictScores({ summary }: { summary: PanelSummary }) {
  const supportPercentage = Math.round(summary.support_confidence * 100);
  const refutePercentage = Math.round(summary.refute_confidence * 100);
  
  return (
    <div className="space-y-6">
      {/* Support Confidence */}
      <div className="space-y-2">
        <div className="flex justify-between items-center">
          <span className="text-sm font-semibold text-green-700">Support</span>
          <span className="text-2xl font-bold text-green-700">{supportPercentage}%</span>
        </div>
        <div className="h-4 bg-gray-200 rounded-full overflow-hidden">
          <div 
            className="h-full bg-green-500 transition-all duration-500"
            style={{ width: `${supportPercentage}%` }}
          />
        </div>
      </div>

      {/* Refute Confidence */}
      <div className="space-y-2">
        <div className="flex justify-between items-center">
          <span className="text-sm font-semibold text-red-700">Refute</span>
          <span className="text-2xl font-bold text-red-700">{refutePercentage}%</span>
        </div>
        <div className="h-4 bg-gray-200 rounded-full overflow-hidden">
          <div 
            className="h-full bg-red-500 transition-all duration-500"
            style={{ width: `${refutePercentage}%` }}
          />
        </div>
      </div>

      <div className="pt-4 border-t">
        <div className="text-xs text-muted-foreground text-center">
          Based on {summary.model_count} independent agent{summary.model_count !== 1 ? 's' : ''}
        </div>
      </div>
    </div>
  );
}

export default async function ClaimPage({ params }: { params: { slug: string } }) {
  const claimData = await getClaim(params.slug);

  if (!claimData) {
    notFound();
  }

  const { claim, consensus_score, provenance_verified, replay_bundle_url, panel } = claimData;

  const panelModels = panel?.models ?? [];
  const modelCount = panel ? panel.summary.model_count : claim.model_assessments.length;
  const evidenceMap = new Map(claim.evidence.map((item) => [item.id, item]));

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center gap-2 mb-4">
            <Badge variant="outline">{claim.topic}</Badge>
            {provenance_verified && (
              <Badge variant="success" className="flex items-center gap-1">
                <Shield className="w-3 h-3" />
                Verified Sources
              </Badge>
            )}
          </div>
          
          <h1 className="text-3xl font-bold mb-4">{claim.text}</h1>
          
          <div className="flex items-center gap-4 text-sm text-muted-foreground">
            <span>Created: {new Date(claim.created_at).toLocaleDateString()}</span>
            <span>Evidence: {claim.evidence.length} sources</span>
            <span>Models: {modelCount} evaluations</span>
          </div>
        </div>

        <div className="grid lg:grid-cols-3 gap-6">
          {/* Main Content */}
          <div className="lg:col-span-2 space-y-6">
            {/* Evidence Section */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-3">
                  <BarChart3 className="w-5 h-5 text-truce-600" />
                  Evidence & Sources
                </CardTitle>
                <CardDescription>
                  Statistical data and official sources related to this claim
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {claim.evidence.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No evidence sources available yet.</p>
                ) : (
                  claim.evidence.map((evidence, index) => (
                    <div key={evidence.id} className="border rounded-lg p-4">
                      <div className="flex items-start justify-between mb-2">
                        <div className="flex-1">
                          <h4 className="font-medium text-sm">
                            {evidence.publisher || evidence.domain || "Unknown Source"}
                          </h4>
                          {evidence.published_at && (
                            <p className="text-xs text-muted-foreground">
                              Published: {new Date(evidence.published_at).toLocaleDateString()}
                            </p>
                          )}
                        </div>
                        <Button variant="ghost" size="sm" asChild>
                          <a href={evidence.url} target="_blank" rel="noopener noreferrer">
                            <ExternalLink className="w-4 h-4" />
                          </a>
                        </Button>
                      </div>
                      
                      {evidence.snippet && evidence.snippet !== "Content available at source." ? (
                        <p className="text-sm mb-2">{evidence.snippet}</p>
                      ) : (
                        <p className="text-sm mb-2 text-muted-foreground italic">
                          Content available at{" "}
                          <a 
                            href={evidence.url} 
                            target="_blank" 
                            rel="noopener noreferrer"
                            className="text-truce-600 hover:underline"
                          >
                            source
                          </a>
                        </p>
                      )}
                      
                      <p className="text-xs text-muted-foreground">
                        Source: {evidence.provenance}
                      </p>
                    </div>
                  ))
                )}
              </CardContent>
            </Card>

            {/* Model Assessments */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-3">
                  <Bot className="w-5 h-5 text-truce-600" />
                  Model Panel Evaluation
                </CardTitle>
                <CardDescription>
                  Independent AI model assessments of this claim
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                {panel ? (
                  <>
                    <div className="rounded-lg border bg-muted/40 p-4 text-sm">
                      <div className="flex flex-wrap items-center gap-3">
                        {panel.summary.verdict && (
                          <Badge variant={getVerdictColor(panel.summary.verdict) as "supports" | "refutes" | "mixed" | "uncertain" | "default" | "secondary" | "destructive" | "outline" | "success" | "warning"}>
                            Panel verdict: {formatPanelVerdict(panel.summary.verdict)}
                          </Badge>
                        )}
                        <span className="text-muted-foreground">
                          Support: {Math.round(panel.summary.support_confidence * 100)}% | Refute: {Math.round(panel.summary.refute_confidence * 100)}%
                        </span>
                        <span className="text-muted-foreground">
                          {panel.summary.model_count} models
                        </span>
                      </div>
                      <div className="mt-2 text-xs text-muted-foreground">
                        Updated {new Date(panel.generated_at).toLocaleString()}
                      </div>
                    </div>

                    <div className="space-y-4">
                      {panelModels.map((modelVerdict) => {
                        const providerInfo = getProviderInfo(modelVerdict.model || modelVerdict.provider_id);
                        const approvalConf = Math.round(modelVerdict.approval_argument.confidence * 100);
                        const refusalConf = Math.round(modelVerdict.refusal_argument.confidence * 100);

                        return (
                          <div key={`${modelVerdict.provider_id}-${modelVerdict.model}`} className="rounded-lg border p-4">
                            <div className="mb-4 flex items-start gap-3">
                              {providerInfo.logo && (
                                <div className="flex h-8 w-8 items-center justify-center rounded-lg border bg-gray-50">
                                  <ProviderLogo
                                    src={providerInfo.logo}
                                    alt={`${providerInfo.name} logo`}
                                    className="h-5 w-5 object-contain"
                                  />
                                </div>
                              )}
                              <div className="flex-1">
                                <h4 className="font-medium">{providerInfo.name}</h4>
                                <div className="mt-1 flex items-center gap-2">
                                  <Badge variant="outline" className="border-green-500 text-green-700">
                                    Support: {approvalConf}%
                                  </Badge>
                                  <Badge variant="outline" className="border-red-500 text-red-700">
                                    Refute: {refusalConf}%
                                  </Badge>
                                </div>
                              </div>
                            </div>

                            {/* Approval Argument */}
                            <div className="mb-4 rounded-md bg-green-50 p-3 border border-green-200">
                              <h5 className="text-xs font-semibold text-green-800 mb-2">
                                APPROVAL ARGUMENT ({approvalConf}% confidence)
                              </h5>
                              <p className="text-sm leading-6 text-gray-700">
                                {modelVerdict.approval_argument.argument}
                              </p>
                              {modelVerdict.approval_argument.evidence_ids.length > 0 && (
                                <div className="mt-2 pt-2 border-t border-green-200">
                                  <p className="text-xs font-medium text-green-800 mb-1">
                                    Evidence ({modelVerdict.approval_argument.evidence_ids.length})
                                  </p>
                                  <ul className="space-y-1 text-xs">
                                    {modelVerdict.approval_argument.evidence_ids.slice(0, 2).map((citationId) => {
                                      const evidence = evidenceMap.get(citationId);
                                      return (
                                        <li key={citationId} className="leading-snug text-gray-600">
                                          {evidence ? (
                                            <span>
                                              <span className="font-medium">{evidence.publisher || evidence.domain || "Source"}</span>
                                              {evidence.snippet && evidence.snippet !== "Content available at source." && `: ${truncate(evidence.snippet, 80)}`}
                                            </span>
                                          ) : (
                                            <span>Evidence ID: {String(citationId).substring(0, 8)}...</span>
                                          )}
                                        </li>
                                      );
                                    })}
                                    {modelVerdict.approval_argument.evidence_ids.length > 2 && (
                                      <li className="text-gray-500">+ {modelVerdict.approval_argument.evidence_ids.length - 2} more</li>
                                    )}
                                  </ul>
                                </div>
                              )}
                            </div>

                            {/* Refusal Argument */}
                            <div className="rounded-md bg-red-50 p-3 border border-red-200">
                              <h5 className="text-xs font-semibold text-red-800 mb-2">
                                REFUSAL ARGUMENT ({refusalConf}% confidence)
                              </h5>
                              <p className="text-sm leading-6 text-gray-700">
                                {modelVerdict.refusal_argument.argument}
                              </p>
                              {modelVerdict.refusal_argument.evidence_ids.length > 0 && (
                                <div className="mt-2 pt-2 border-t border-red-200">
                                  <p className="text-xs font-medium text-red-800 mb-1">
                                    Evidence ({modelVerdict.refusal_argument.evidence_ids.length})
                                  </p>
                                  <ul className="space-y-1 text-xs">
                                    {modelVerdict.refusal_argument.evidence_ids.slice(0, 2).map((citationId) => {
                                      const evidence = evidenceMap.get(citationId);
                                      return (
                                        <li key={citationId} className="leading-snug text-gray-600">
                                          {evidence ? (
                                            <span>
                                              <span className="font-medium">{evidence.publisher || evidence.domain || "Source"}</span>
                                              {evidence.snippet && evidence.snippet !== "Content available at source." && `: ${truncate(evidence.snippet, 80)}`}
                                            </span>
                                          ) : (
                                            <span>Evidence ID: {String(citationId).substring(0, 8)}...</span>
                                          )}
                                        </li>
                                      );
                                    })}
                                    {modelVerdict.refusal_argument.evidence_ids.length > 2 && (
                                      <li className="text-gray-500">+ {modelVerdict.refusal_argument.evidence_ids.length - 2} more</li>
                                    )}
                                  </ul>
                                </div>
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </>
                ) : (
                  <p className="text-sm text-muted-foreground">
                    Panel results are not available yet. Run the verification panel to populate this section.
                  </p>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Verdict Summary */}
            {panel && panel.summary && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Aggregate Verdict</CardTitle>
                  <CardDescription>Panel confidence scores</CardDescription>
                </CardHeader>
                <CardContent>
                  <AggregateVerdictScores summary={panel.summary} />
                </CardContent>
              </Card>
            )}

            {/* Actions */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Actions</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <Button asChild className="w-full" variant="outline">
                  <Link href="/consensus/canada-crime">
                    Join Discussion
                  </Link>
                </Button>
                
                {replay_bundle_url && (
                  <Button variant="outline" className="w-full" asChild>
                    <a href={`http://localhost:8000${replay_bundle_url}`} target="_blank">
                      <Download className="w-4 h-4 mr-2" />
                      Download Replay Bundle
                    </a>
                  </Button>
                )}
                
                <Button variant="ghost" className="w-full" asChild>
                  <Link href="/transparency">
                    View Methodology
                  </Link>
                </Button>
              </CardContent>
            </Card>

            {/* Transparency Info */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4" />
                  Limitations
                </CardTitle>
              </CardHeader>
              <CardContent className="text-sm space-y-2">
                <p>
                  Crime statistics reflect police-reported incidents only and may not capture unreported crimes.
                </p>
                <p>
                  Model evaluations are based on available evidence and may not reflect all relevant factors.
                </p>
                <p>
                  This analysis is for demonstration purposes and should not be used for policy decisions.
                </p>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}
