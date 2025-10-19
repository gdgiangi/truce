'use client';

import React, { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { ExternalLink, ChevronDown, ChevronUp, AlertCircle } from "lucide-react";
import { ProviderLogo } from "@/components/provider-logo";

type ArgumentSide = "support" | "refute" | null;

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
  failed?: boolean;
  error?: string;
  error_details?: string;
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
  verdict?: string;
}

function getProviderInfo(modelName: string): { name: string; logo: string; shortName: string } {
  const name = modelName.toLowerCase();

  if (name.includes("gpt") || name.includes("openai") || name.startsWith("o1")) {
    return {
      name: "OpenAI",
      shortName: "OpenAI",
      logo: "https://www.svgrepo.com/show/306500/openai.svg",
    };
  }

  if (name.includes("grok")) {
    return {
      name: "xAI Grok",
      shortName: "Grok",
      logo: "https://upload.wikimedia.org/wikipedia/commons/5/53/X_logo_2023_original.svg",
    };
  }

  if (name.includes("gemini") || name.includes("google")) {
    return {
      name: "Google Gemini",
      shortName: "Gemini",
      logo: "https://www.svgrepo.com/show/475656/google-color.svg",
    };
  }

  if (name.includes("claude") || name.includes("anthropic") || name.includes("sonnet")) {
    return {
      name: "Anthropic",
      shortName: "Claude",
      logo: "https://registry.npmmirror.com/@lobehub/icons-static-png/1.64.0/files/light/anthropic.png",
    };
  }

  return {
    name: "AI Model",
    shortName: "AI",
    logo: "",
  };
}

function CitationHighlightedText({ 
  text, 
  citationLinks = [], 
  evidenceMap,
  onEvidenceClick 
}: {
  text: string;
  citationLinks?: CitationLink[];
  evidenceMap: Map<string, Evidence>;
  onEvidenceClick: (evidenceId: string) => void;
}) {
  if (!citationLinks || citationLinks.length === 0) {
    return <span>{text}</span>;
  }

  // Sort citation links by position to render in order
  const sortedLinks = [...citationLinks].sort((a, b) => a.start - b.start);
  const elements: React.ReactNode[] = [];
  let lastPosition = 0;

  sortedLinks.forEach((link, index) => {
    // Add text before the citation
    if (link.start > lastPosition) {
      elements.push(
        <span key={`text-${index}`}>
          {text.substring(lastPosition, link.start)}
        </span>
      );
    }

    // Add the highlighted citation
    const evidence = evidenceMap.get(link.evidence_id);
    elements.push(
      <span
        key={`citation-${index}`}
        className="bg-gray-100 hover:bg-gray-200 cursor-pointer rounded px-1 py-0.5 text-gray-800 border-b border-gray-300 transition-colors underline decoration-gray-400 decoration-dotted"
        onClick={() => onEvidenceClick(link.evidence_id)}
        title={evidence ? `From: ${evidence.publisher || evidence.domain}` : 'Evidence source'}
      >
        {link.text}
      </span>
    );

    lastPosition = link.end;
  });

  // Add any remaining text after the last citation
  if (lastPosition < text.length) {
    elements.push(
      <span key="text-final">
        {text.substring(lastPosition)}
      </span>
    );
  }

  return <span>{elements}</span>;
}

function ModelArgumentCard({ 
  modelVerdict, 
  evidenceMap,
  side 
}: { 
  modelVerdict: PanelModelVerdict;
  evidenceMap: Map<string, Evidence>;
  side: "support" | "refute";
}) {
  const [showEvidence, setShowEvidence] = useState(false);
  const [highlightedEvidenceId, setHighlightedEvidenceId] = useState<string | null>(null);
  const providerInfo = getProviderInfo(modelVerdict.model || modelVerdict.provider_id);
  const argument = side === "support" ? modelVerdict.approval_argument : modelVerdict.refusal_argument;
  const confidence = Math.round(argument.confidence * 100);

  const handleEvidenceClick = (evidenceId: string) => {
    setHighlightedEvidenceId(evidenceId);
    setShowEvidence(true);
  };

  return (
    <div className="group relative bg-white border border-gray-100 rounded-2xl p-6 hover:shadow-lg transition-all duration-300">
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          {providerInfo.logo && (
            <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-gray-100 bg-gray-50">
              <ProviderLogo
                src={providerInfo.logo}
                alt={`${providerInfo.name} logo`}
                className="h-6 w-6 object-contain"
              />
            </div>
          )}
          <div>
            <h4 className="font-semibold text-gray-900">{providerInfo.shortName}</h4>
            <p className="text-sm text-gray-500">{confidence}% confidence</p>
          </div>
        </div>
        <div className={`px-3 py-1 rounded-full text-xs font-medium ${
          side === "support" 
            ? "bg-emerald-50 text-emerald-700"
            : "bg-rose-50 text-rose-700"
        }`}>
          {confidence}%
        </div>
      </div>

      <p className="text-sm text-gray-700 leading-relaxed mb-4">
        <CitationHighlightedText
          text={argument.argument}
          citationLinks={argument.citation_links}
          evidenceMap={evidenceMap}
          onEvidenceClick={handleEvidenceClick}
        />
      </p>

      {argument.evidence_ids.length > 0 && (
        <div className="border-t border-gray-100 pt-4">
          <button
            onClick={() => setShowEvidence(!showEvidence)}
            className="flex items-center gap-2 text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors"
          >
            {showEvidence ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            {argument.evidence_ids.length} evidence source{argument.evidence_ids.length !== 1 ? 's' : ''}
          </button>
          
          {showEvidence && (
            <div className="mt-3 space-y-2">
              {argument.evidence_ids.map((citationId) => {
                const evidence = evidenceMap.get(citationId);
                if (!evidence) return null;

                return (
                  <a
                    key={citationId}
                    href={evidence.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className={`flex items-start gap-2 p-3 rounded-lg transition-colors group ${
                      highlightedEvidenceId === citationId
                        ? "bg-gray-200 border border-gray-400"
                        : "bg-gray-50 hover:bg-gray-100"
                    }`}
                    onMouseEnter={() => setHighlightedEvidenceId(citationId)}
                    onMouseLeave={() => setHighlightedEvidenceId(null)}
                  >
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-white border border-gray-200 text-gray-700">
                          {evidence.publisher || evidence.domain || "Source"}
                        </span>
                      </div>
                      {evidence.snippet && evidence.snippet !== "Content available at source." && (
                        <p className="text-xs text-gray-600 line-clamp-2">{evidence.snippet}</p>
                      )}
                    </div>
                    <ExternalLink className="w-4 h-4 text-gray-400 group-hover:text-gray-600 flex-shrink-0 mt-1" />
                  </a>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function ClaimVerdictDisplay({ 
  panelModels, 
  summary,
  evidenceMap 
}: { 
  panelModels: PanelModelVerdict[];
  summary: PanelSummary;
  evidenceMap: Record<string, Evidence>;
}) {
  const [selectedSide, setSelectedSide] = useState<ArgumentSide>(null);
  // If you need a Map for efficient lookup, reconstruct it locally:
  const evidenceMapObj = new Map(Object.entries(evidenceMap));

  const supportPercentage = Math.round(summary.support_confidence * 100);
  const refutePercentage = Math.round(summary.refute_confidence * 100);
  
  const totalModels = panelModels.length;
  const failedModels = panelModels.filter(m => m.failed).length;
  const successfulModels = totalModels - failedModels;

  const filteredModels = selectedSide === null 
    ? panelModels 
    : selectedSide === "support"
    ? panelModels.filter(m => m.approval_argument.confidence >= m.refusal_argument.confidence)
    : panelModels.filter(m => m.refusal_argument.confidence > m.approval_argument.confidence);

  return (
    <>
      {/* Verdict Visualization */}
      <div className="mb-12 max-w-5xl mx-auto">
        <div className="relative">
          {/* Main Verdict Display - Proportional bars */}
          <div className="relative rounded-3xl overflow-hidden shadow-xl border border-gray-200" style={{ display: 'flex' }}>
            {/* Support Side */}
            <button
              onClick={() => setSelectedSide(selectedSide === "support" ? null : "support")}
              style={{ width: `${supportPercentage}%` }}
              className={`relative p-12 transition-all duration-500 ${
                selectedSide === "support"
                  ? "bg-emerald-500 text-white scale-105 z-10"
                  : selectedSide === "refute"
                  ? "bg-gray-100 text-gray-400"
                  : "bg-gradient-to-br from-emerald-50 to-emerald-100 hover:from-emerald-100 hover:to-emerald-200 text-emerald-900"
              }`}
            >
              <div className="text-center">
                <div className="text-xs md:text-sm font-medium mb-2 uppercase tracking-wider">
                  Support
                </div>
                <div className="text-3xl md:text-5xl lg:text-6xl font-bold mb-1">
                  {supportPercentage}%
                </div>
                <div className="text-xs opacity-90">
                  {panelModels.filter(m => m.approval_argument.confidence >= m.refusal_argument.confidence).length} models
                </div>
              </div>
            </button>

            {/* Refute Side */}
            <button
              onClick={() => setSelectedSide(selectedSide === "refute" ? null : "refute")}
              style={{ width: `${refutePercentage}%` }}
              className={`relative p-12 transition-all duration-500 ${
                selectedSide === "refute"
                  ? "bg-rose-500 text-white scale-105 z-10"
                  : selectedSide === "support"
                  ? "bg-gray-100 text-gray-400"
                  : "bg-gradient-to-br from-rose-50 to-rose-100 hover:from-rose-100 hover:to-rose-200 text-rose-900"
              }`}
            >
              <div className="text-center">
                <div className="text-xs md:text-sm font-medium mb-2 uppercase tracking-wider">
                  Refute
                </div>
                <div className="text-3xl md:text-5xl lg:text-6xl font-bold mb-1">
                  {refutePercentage}%
                </div>
                <div className="text-xs opacity-90">
                  {panelModels.filter(m => m.refusal_argument.confidence > m.approval_argument.confidence).length} models
                </div>
              </div>
            </button>
          </div>

          {/* Hint Text */}
          <div className="text-center mt-6">
            <p className="text-sm text-gray-500 mb-2">
              Click on either side to view detailed model arguments • Widths reflect confidence distribution
            </p>
            {failedModels > 0 && (
              <div className="flex items-center justify-center gap-2 text-xs text-amber-700">
                <AlertCircle className="w-3.5 h-3.5" />
                <span>
                  {successfulModels} of {totalModels} models evaluated successfully • {failedModels} excluded from aggregate
                </span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Model Arguments */}
      {selectedSide && (
        <div className="max-w-5xl mx-auto mb-12">
          <div className="mb-6">
            <h2 className="text-2xl font-bold text-gray-900 mb-2">
              {selectedSide === "support" ? "Support" : "Refute"} Arguments
            </h2>
            <p className="text-gray-600">
              Detailed analysis from AI models that {selectedSide === "support" ? "support" : "refute"} this claim
            </p>
          </div>

          <div className="grid gap-6">
            {filteredModels.map((modelVerdict) => (
              <ModelArgumentCard
                key={`${modelVerdict.provider_id}-${modelVerdict.model}`}
                modelVerdict={modelVerdict}
                evidenceMap={evidenceMap}
                side={selectedSide}
              />
            ))}
          </div>
        </div>
      )}

      {/* All Models View (when no side selected) */}
      {!selectedSide && (
        <div className="max-w-5xl mx-auto mb-12">
          <div className="mb-6 text-center">
            <h2 className="text-2xl font-bold text-gray-900 mb-2">
              All Model Evaluations
            </h2>
            <p className="text-gray-600">
              Independent assessments from {totalModels} AI model{totalModels !== 1 ? 's' : ''}
              {failedModels > 0 && (
                <span className="text-amber-700"> ({successfulModels} successful, {failedModels} failed)</span>
              )}
            </p>
          </div>

          <div className="grid md:grid-cols-2 gap-6">
            {panelModels.map((modelVerdict) => {
              const providerInfo = getProviderInfo(modelVerdict.model || modelVerdict.provider_id);
              
              // Check if this model failed
              if (modelVerdict.failed) {
                return (
                  <div
                    key={`${modelVerdict.provider_id}-${modelVerdict.model}`}
                    className="bg-amber-50 border border-amber-200 rounded-2xl p-6"
                  >
                    <div className="flex items-center gap-3 mb-4">
                      {providerInfo.logo && (
                        <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-amber-200 bg-white opacity-50">
                          <ProviderLogo
                            src={providerInfo.logo}
                            alt={`${providerInfo.name} logo`}
                            className="h-6 w-6 object-contain grayscale"
                          />
                        </div>
                      )}
                      <div className="flex-1">
                        <h4 className="font-semibold text-gray-900">{providerInfo.name}</h4>
                        <div className="flex items-center gap-1.5 mt-1">
                          <AlertCircle className="w-4 h-4 text-amber-600" />
                          <span className="text-xs text-amber-700 font-medium">Evaluation Failed</span>
                        </div>
                      </div>
                    </div>

                    <div className="bg-white rounded-lg p-4 border border-amber-200">
                      <p className="text-sm text-gray-700 mb-3">
                        {modelVerdict.error || "This model was unable to complete evaluation."}
                      </p>
                      <details className="text-xs text-gray-600">
                        <summary className="cursor-pointer font-medium hover:text-gray-900 mb-2">
                          View error details
                        </summary>
                        <pre className="bg-gray-50 p-2 rounded border border-gray-200 overflow-x-auto whitespace-pre-wrap">
                          {modelVerdict.error_details || "No additional details available."}
                        </pre>
                      </details>
                    </div>

                    <p className="text-xs text-amber-700 mt-3 italic">
                      This model was excluded from the aggregate confidence scores.
                    </p>
                  </div>
                );
              }
              
              // Normalize confidences to sum to 100%
              const rawApproval = modelVerdict.approval_argument.confidence;
              const rawRefusal = modelVerdict.refusal_argument.confidence;
              const total = rawApproval + rawRefusal;
              
              const approvalConf = total > 0 
                ? Math.round((rawApproval / total) * 100)
                : 50;
              const refusalConf = total > 0
                ? Math.round((rawRefusal / total) * 100)
                : 50;
              
              const dominant = approvalConf >= refusalConf ? "support" : "refute";

              return (
                <div
                  key={`${modelVerdict.provider_id}-${modelVerdict.model}`}
                  className="bg-white border border-gray-100 rounded-2xl p-6 hover:shadow-lg transition-all duration-300"
                >
                  <div className="flex items-center gap-3 mb-4">
                    {providerInfo.logo && (
                      <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-gray-100 bg-gray-50">
                        <ProviderLogo
                          src={providerInfo.logo}
                          alt={`${providerInfo.name} logo`}
                          className="h-6 w-6 object-contain"
                        />
                      </div>
                    )}
                    <div className="flex-1">
                      <h4 className="font-semibold text-gray-900">{providerInfo.name}</h4>
                    </div>
                  </div>

                  {/* Proportional confidence bars */}
                  <div className="relative flex gap-1 h-16 rounded-xl overflow-hidden border border-gray-200">
                    <div 
                      style={{ width: `${approvalConf}%` }}
                      className={`flex flex-col items-center justify-center transition-all ${
                        dominant === "support" ? "bg-emerald-100" : "bg-emerald-50"
                      }`}
                    >
                      <div className="text-xs font-medium text-gray-600 mb-0.5">Support</div>
                      <div className={`text-lg font-bold ${
                        dominant === "support" ? "text-emerald-700" : "text-gray-700"
                      }`}>
                        {approvalConf}%
                      </div>
                    </div>
                    <div 
                      style={{ width: `${refusalConf}%` }}
                      className={`flex flex-col items-center justify-center transition-all ${
                        dominant === "refute" ? "bg-rose-100" : "bg-rose-50"
                      }`}
                    >
                      <div className="text-xs font-medium text-gray-600 mb-0.5">Refute</div>
                      <div className={`text-lg font-bold ${
                        dominant === "refute" ? "text-rose-700" : "text-gray-700"
                      }`}>
                        {refusalConf}%
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </>
  );
}
