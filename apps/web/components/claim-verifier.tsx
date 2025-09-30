"use client";

import { ChangeEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface VerificationResult {
  verification_id: string;
  cached: boolean;
  verdict: "supports" | "refutes" | "mixed" | "uncertain";
  created_at: string;
  providers: string[];
  evidence_ids: string[];
  time_window: {
    start?: string | null;
    end?: string | null;
  };
}

interface ClaimVerifierProps {
  slug: string;
  adjudicatorUrl: string;
  defaultProviders: string[];
}

export function ClaimVerifier({ slug, adjudicatorUrl, defaultProviders }: ClaimVerifierProps) {
  const [startDate, setStartDate] = useState<string>("");
  const [endDate, setEndDate] = useState<string>("");
  const [selectedProviders, setSelectedProviders] = useState<string[]>(defaultProviders);
  const [forceRefresh, setForceRefresh] = useState(false);
  const [verification, setVerification] = useState<VerificationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const initialized = useRef(false);

  const providerSummary = useMemo(() => selectedProviders.join(", "), [selectedProviders]);

  const runVerification = useCallback(
    async (force: boolean) => {
      setLoading(true);
      setError(null);
      try {
        const params = new URLSearchParams();
        if (startDate) {
          params.set("time_start", startDate);
        }
        if (endDate) {
          params.set("time_end", endDate);
        }
        selectedProviders.forEach((provider) => params.append("providers[]", provider));
        if (force) {
          params.set("force", "true");
        }

        const response = await fetch(`${adjudicatorUrl}/claims/${slug}/verify?${params.toString()}`, {
          method: "POST",
          cache: "no-store",
        });

        if (!response.ok) {
          const message = await response.text();
          throw new Error(message || "Verification failed");
        }

        const payload: VerificationResult = await response.json();
        setVerification(payload);
      } catch (err) {
        console.error("Verification error", err);
        setError("Verification request failed. Please try again.");
      } finally {
        setLoading(false);
      }
    },
    [adjudicatorUrl, endDate, selectedProviders, slug, startDate],
  );

  useEffect(() => {
    if (!initialized.current) {
      initialized.current = true;
      runVerification(false);
      return;
    }
    runVerification(false);
  }, [runVerification]);

  const toggleProvider = (provider: string) => {
    setSelectedProviders((prev) => {
      if (prev.includes(provider)) {
        if (prev.length === 1) {
          return prev; // ensure at least one provider remains selected
        }
        return prev.filter((item) => item !== provider);
      }
      return [...prev, provider];
    });
  };

  const onForceToggle = (event: ChangeEvent<HTMLInputElement>) => {
    const next = event.target.checked;
    setForceRefresh(next);
    runVerification(next).finally(() => {
      if (next) {
        setForceRefresh(false);
      }
    });
  };

  const onManualVerify = () => {
    runVerification(forceRefresh);
  };

  return (
    <Card className="border bg-card/60">
      <CardHeader className="flex flex-row items-center justify-between space-y-0">
        <CardTitle className="text-lg font-semibold">Verification Controls</CardTitle>
        {verification?.cached && (
          <Badge variant="outline" className="border-green-500 text-green-700">
            Cached ✓
          </Badge>
        )}
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="grid gap-4 md:grid-cols-2">
          <div className="space-y-2">
            <label className="text-sm font-medium text-muted-foreground" htmlFor="time_start">
              Start date
            </label>
            <input
              id="time_start"
              type="date"
              value={startDate}
              onChange={(event) => setStartDate(event.target.value)}
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm focus:border-truce-500 focus:outline-none focus:ring-2 focus:ring-truce-500/40"
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium text-muted-foreground" htmlFor="time_end">
              End date
            </label>
            <input
              id="time_end"
              type="date"
              value={endDate}
              onChange={(event) => setEndDate(event.target.value)}
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm focus:border-truce-500 focus:outline-none focus:ring-2 focus:ring-truce-500/40"
            />
          </div>
        </div>

        <div className="space-y-3">
          <p className="text-sm font-medium text-muted-foreground">Providers</p>
          <div className="flex flex-wrap gap-3">
            {defaultProviders.map((provider) => {
              const checked = selectedProviders.includes(provider);
              return (
                <label key={provider} className={`flex items-center gap-2 rounded-full border px-3 py-1 text-sm ${checked ? "border-truce-500 bg-truce-50 text-truce-700" : "border-muted"}`}>
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={() => toggleProvider(provider)}
                    className="h-3 w-3"
                    aria-label={`Toggle ${provider}`}
                  />
                  {provider}
                </label>
              );
            })}
          </div>
        </div>

        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <label className="flex items-center gap-2 text-sm text-muted-foreground">
            <input
              type="checkbox"
              checked={forceRefresh}
              onChange={onForceToggle}
              className="h-4 w-4"
            />
            Refresh with latest
          </label>
          <Button onClick={onManualVerify} disabled={loading}>
            {loading ? "Verifying…" : "Verify claim"}
          </Button>
        </div>

        {error && <p className="text-sm text-red-600">{error}</p>}

        {verification && (
          <div className="space-y-2 rounded-lg border border-dashed bg-muted/30 p-4 text-sm">
            <div className="flex flex-wrap items-center gap-3">
              <span className="text-base font-medium capitalize">Verdict: {verification.verdict}</span>
              <Badge variant="outline">Providers: {providerSummary}</Badge>
              <Badge variant="outline">Evidence used: {verification.evidence_ids.length}</Badge>
            </div>
            <div className="flex flex-wrap gap-3 text-muted-foreground">
              <span>Verification ID: {verification.verification_id}</span>
              <span>Ran at: {new Date(verification.created_at).toLocaleString()}</span>
              {verification.time_window.start && (
                <span>From {verification.time_window.start}</span>
              )}
              {verification.time_window.end && (
                <span>To {verification.time_window.end}</span>
              )}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
