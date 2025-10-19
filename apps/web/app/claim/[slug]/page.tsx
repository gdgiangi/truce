import React from "react";
import { notFound } from "next/navigation";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Download, Shield, AlertTriangle } from "lucide-react";
import { ClaimVerdictDisplay } from "@/components/claim-verdict-display";

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

interface CitationLink {
  start: number;
  end: number;
  evidence_id: string;
  text: string;
}

interface ArgumentWithEvidence {
  argument: string;
  evidence_ids: string[];
  citation_links?: CitationLink[];
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

export default async function ClaimPage({ params }: { params: { slug: string } }) {
  const claimData = await getClaim(params.slug);

  if (!claimData) {
    notFound();
  }

  const { claim, provenance_verified, replay_bundle_url, panel } = claimData;
  const panelModels = panel?.models ?? [];
  const evidenceRecord = Object.fromEntries(claim.evidence.map((item) => [item.id, item]));

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-50 to-white">
      <div className="container mx-auto px-4 py-12 max-w-7xl">
        {/* Header */}
        <div className="mb-12 text-center max-w-4xl mx-auto">
          <div className="flex items-center justify-center gap-3 mb-6">
            <Badge variant="outline" className="border-gray-300 text-gray-700 px-4 py-1">
              {claim.topic}
            </Badge>
            {provenance_verified && (
              <Badge className="flex items-center gap-1.5 bg-emerald-500 hover:bg-emerald-600 px-4 py-1">
                <Shield className="w-3.5 h-3.5" />
                Verified
              </Badge>
            )}
          </div>

          <h1 className="text-4xl md:text-5xl font-bold text-gray-900 mb-6 leading-tight">
            {claim.text}
          </h1>

          <div className="flex items-center justify-center gap-6 text-sm text-gray-500">
            <span>{new Date(claim.created_at).toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}</span>
            <span>•</span>
            <span>{claim.evidence.length} sources</span>
            <span>•</span>
            <span>{panel?.summary.model_count || 0} AI models</span>
          </div>
        </div>

        {panel ? (
          <ClaimVerdictDisplay
            panelModels={panelModels}
            summary={panel.summary}
            evidenceMap={evidenceRecord}
          />
        ) : (
          <div className="text-center py-12">
            <AlertTriangle className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <p className="text-gray-600">
              Panel evaluation not available for this claim.
            </p>
          </div>
        )}

        {/* Actions & Info */}
        <div className="max-w-5xl mx-auto grid md:grid-cols-3 gap-6 mt-12">
          <Card className="border-gray-200">
            <CardHeader>
              <CardTitle className="text-base">Methodology</CardTitle>
            </CardHeader>
            <CardContent>
              <Button variant="outline" className="w-full" asChild>
                <Link href="/transparency">View Details</Link>
              </Button>
            </CardContent>
          </Card>

          {replay_bundle_url && (
            <Card className="border-gray-200">
              <CardHeader>
                <CardTitle className="text-base">Replay Bundle</CardTitle>
              </CardHeader>
              <CardContent>
                <Button variant="outline" className="w-full" asChild>
                  <a href={`${adjudicatorUrl}${replay_bundle_url}`} target="_blank">
                    <Download className="w-4 h-4 mr-2" />
                    Download
                  </a>
                </Button>
              </CardContent>
            </Card>
          )}

          <Card className="border-gray-200">
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <AlertTriangle className="w-4 h-4" />
                Limitations
              </CardTitle>
            </CardHeader>
            <CardContent className="text-xs text-gray-600">
              <p>
                AI evaluations are based on available evidence and should not be used as the sole basis for decisions.
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}