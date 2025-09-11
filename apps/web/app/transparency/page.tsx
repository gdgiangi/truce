import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { AlertTriangle, Shield, Eye, Download } from "lucide-react";
import { ProviderLogo } from "@/components/provider-logo";

export default function TransparencyPage() {
  return (
    <div className="container mx-auto px-4 py-8">
      <div className="max-w-4xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold mb-4">Transparency Report</h1>
          <p className="text-lg text-muted-foreground">
            How Truce works: our methods, models, and limitations
          </p>
        </div>

        <div className="space-y-6">
          {/* What We Log */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Eye className="w-5 h-5" />
                What We Track & Log
              </CardTitle>
              <CardDescription>
                Complete transparency about data collection and processing
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid md:grid-cols-2 gap-4">
                <div>
                  <h4 className="font-medium mb-2">Evidence Collection</h4>
                  <ul className="text-sm space-y-1 text-muted-foreground">
                    <li>• Source URLs and access timestamps</li>
                    <li>• Publisher and publication dates</li>
                    <li>• Data extraction methods</li>
                    <li>• API response caching</li>
                  </ul>
                </div>
                <div>
                  <h4 className="font-medium mb-2">Model Evaluations</h4>
                  <ul className="text-sm space-y-1 text-muted-foreground">
                    <li>• Complete prompts sent to models</li>
                    <li>• Model responses and timestamps</li>
                    <li>• Temperature and parameter settings</li>
                    <li>• Token usage and costs</li>
                  </ul>
                </div>
              </div>
              <div>
                <h4 className="font-medium mb-2">User Interactions</h4>
                <ul className="text-sm space-y-1 text-muted-foreground">
                  <li>• Anonymous session IDs for voting (no personal data)</li>
                  <li>• Vote patterns for consensus clustering</li>
                  <li>• Page views and interaction timestamps</li>
                  <li>• No IP addresses, cookies, or tracking beyond sessions</li>
                </ul>
              </div>
            </CardContent>
          </Card>

          {/* Model Panel */}
          <Card>
            <CardHeader>
              <CardTitle>AI Model Panel</CardTitle>
              <CardDescription>
                Independent evaluations from multiple AI systems
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid md:grid-cols-2 gap-4">
                <div className="space-y-3">
                  <h4 className="font-medium">Current Models</h4>
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <ProviderLogo 
                          src="https://www.svgrepo.com/show/306500/openai.svg" 
                          alt="OpenAI logo"
                          className="w-4 h-4 object-contain"
                        />
                        <span className="text-sm">GPT-4</span>
                      </div>
                      <Badge variant="outline">OpenAI</Badge>
                    </div>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <ProviderLogo 
                          src="https://registry.npmmirror.com/@lobehub/icons-static-png/1.64.0/files/light/anthropic.png" 
                          alt="Anthropic logo"
                          className="w-4 h-4 object-contain"
                        />
                        <span className="text-sm">Claude-3 Sonnet</span>
                      </div>
                      <Badge variant="outline">Anthropic</Badge>
                    </div>
                  </div>
                </div>
                <div className="space-y-3">
                  <h4 className="font-medium">Evaluation Process</h4>
                  <ul className="text-sm space-y-1 text-muted-foreground">
                    <li>• Identical evidence context for all models</li>
                    <li>• Structured response format required</li>
                    <li>• Temperature: 0.1 for consistency</li>
                    <li>• Must cite specific evidence</li>
                  </ul>
                </div>
              </div>
              
              <div className="bg-muted/50 p-4 rounded-lg">
                <h4 className="font-medium mb-2">Response Format</h4>
                <pre className="text-xs overflow-x-auto">
{`{
  "verdict": "supports|refutes|mixed|uncertain",
  "confidence": 0.85,
  "citations": ["evidence_id_1", "evidence_id_2"], 
  "rationale": "Detailed explanation with citations..."
}`}
                </pre>
              </div>
            </CardContent>
          </Card>

          {/* Data Sources */}
          <Card>
            <CardHeader>
              <CardTitle>Data Sources</CardTitle>
              <CardDescription>
                Official statistics and methodology notes
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <h4 className="font-medium mb-3">Statistics Canada</h4>
                <div className="space-y-2 text-sm">
                  <div className="flex items-start gap-2">
                    <Badge variant="outline" className="mt-0.5">Primary</Badge>
                    <div>
                      <p className="font-medium">Crime Severity Index (Table 35-10-0026-01)</p>
                      <p className="text-muted-foreground">
                        Police-reported crime severity data, 1998-2024. Accessed via WDS REST API.
                      </p>
                    </div>
                  </div>
                  <div className="flex items-start gap-2">
                    <Badge variant="outline" className="mt-0.5">Reference</Badge>
                    <div>
                      <p className="font-medium">Incident-based crime statistics (Table 35-10-0177-01)</p>
                      <p className="text-muted-foreground">
                        Detailed crime incident data for contextual analysis.
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              <div className="bg-yellow-50 p-4 rounded-lg border border-yellow-200">
                <h4 className="font-medium mb-2 flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 text-yellow-600" />
                  Data Limitations
                </h4>
                <ul className="text-sm space-y-1 text-muted-foreground">
                  <li>• Based on police-reported incidents only</li>
                  <li>• Under-reporting varies by crime type and jurisdiction</li>
                  <li>• Reporting practices change over time</li>
                  <li>• CSI methodology updated periodically</li>
                  <li>• Provincial trends may differ from national data</li>
                </ul>
              </div>
            </CardContent>
          </Card>

          {/* Consensus Method */}
          <Card>
            <CardHeader>
              <CardTitle>Consensus Methodology</CardTitle>
              <CardDescription>
                How we find common ground inspired by Pol.is
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid md:grid-cols-2 gap-4">
                <div>
                  <h4 className="font-medium mb-2">Voting Process</h4>
                  <ul className="text-sm space-y-1 text-muted-foreground">
                    <li>• Three options: Agree / Disagree / Pass</li>
                    <li>• Anonymous sessions (no login required)</li>
                    <li>• Statements limited to 140 characters</li>
                    <li>• Evidence-based statements preferred</li>
                  </ul>
                </div>
                <div>
                  <h4 className="font-medium mb-2">Clustering Algorithm</h4>
                  <ul className="text-sm space-y-1 text-muted-foreground">
                    <li>• K-means clustering on vote vectors</li>
                    <li>• Identifies users with similar patterns</li>
                    <li>• Minimum 3 users required per cluster</li>
                    <li>• Agreement calculated within clusters</li>
                  </ul>
                </div>
              </div>
              
              <div>
                <h4 className="font-medium mb-2">Consensus Thresholds</h4>
                <div className="grid grid-cols-3 gap-4 text-sm">
                  <div className="text-center p-3 bg-green-50 rounded">
                    <div className="font-medium text-green-700">Consensus</div>
                    <div className="text-muted-foreground">≥70% agreement</div>
                  </div>
                  <div className="text-center p-3 bg-yellow-50 rounded">
                    <div className="font-medium text-yellow-700">Divisive</div>
                    <div className="text-muted-foreground">30-70% agreement</div>
                  </div>
                  <div className="text-center p-3 bg-gray-50 rounded">
                    <div className="font-medium text-gray-700">Uncertain</div>
                    <div className="text-muted-foreground">&lt;3 votes</div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Reproducibility */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Download className="w-5 h-5" />
                Reproducibility
              </CardTitle>
              <CardDescription>
                Verify our work with replay bundles
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-sm text-muted-foreground">
                Every claim evaluation includes a downloadable "replay bundle" containing:
              </p>
              
              <div className="grid md:grid-cols-2 gap-4">
                <div>
                  <h4 className="font-medium mb-2">Inputs</h4>
                  <ul className="text-sm space-y-1 text-muted-foreground">
                    <li>• Original claim text</li>
                    <li>• All evidence sources and timestamps</li>
                    <li>• API endpoints and parameters</li>
                    <li>• Raw data files (CSV, JSON)</li>
                  </ul>
                </div>
                <div>
                  <h4 className="font-medium mb-2">Outputs</h4>
                  <ul className="text-sm space-y-1 text-muted-foreground">
                    <li>• Complete model prompts</li>
                    <li>• Full model responses</li>
                    <li>• Processing timestamps</li>
                    <li>• Final JSON-LD graph</li>
                  </ul>
                </div>
              </div>

              <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
                <h4 className="font-medium mb-2 flex items-center gap-2">
                  <Shield className="w-4 h-4 text-blue-600" />
                  Verification
                </h4>
                <p className="text-sm text-muted-foreground">
                  Replay bundles are in JSONL format and can be independently verified. 
                  Run the same inputs through the same models to validate our results.
                </p>
              </div>
            </CardContent>
          </Card>

          {/* Limitations */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-amber-500" />
                Limitations & Disclaimers
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid md:grid-cols-2 gap-4">
                <div>
                  <h4 className="font-medium mb-2">Technical Limitations</h4>
                  <ul className="text-sm space-y-1 text-muted-foreground">
                    <li>• AI models may hallucinate or misinterpret</li>
                    <li>• Limited to available evidence sources</li>
                    <li>• English-language processing only</li>
                    <li>• Simple clustering algorithm</li>
                  </ul>
                </div>
                <div>
                  <h4 className="font-medium mb-2">Usage Disclaimers</h4>
                  <ul className="text-sm space-y-1 text-muted-foreground">
                    <li>• For demonstration purposes only</li>
                    <li>• Not suitable for policy decisions</li>
                    <li>• Always verify against original sources</li>
                    <li>• Consensus ≠ truth</li>
                  </ul>
                </div>
              </div>
              
              <div className="bg-red-50 p-4 rounded-lg border border-red-200">
                <p className="text-sm font-medium mb-1">Important:</p>
                <p className="text-sm text-muted-foreground">
                  This system is a proof-of-concept for transparent dialogue tools. 
                  Always consult authoritative sources and domain experts for important decisions.
                </p>
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="mt-12 pt-8 border-t text-center text-sm text-muted-foreground">
          <p>
            Last updated: {new Date().toLocaleDateString()} • 
            <a href="https://github.com/gdgiangi/truce" className="ml-1 underline hover:text-foreground">
              View source code
            </a>
          </p>
        </div>
      </div>
    </div>
  );
}
