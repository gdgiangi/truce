# Quick Start: Setting Up Real AI Evaluation

## The Problem

When you first run Truce without API keys configured, you'll see:

1. ❌ **No evidence gathered** - Claims show "No evidence sources available"
2. ❌ **Stub AI responses** - Models return placeholder text instead of real analysis
3. ❌ **Irrelevant results** - Search returns hardcoded fallback data

## The Solution

Configure API keys to enable real AI-powered claim verification.

## Step 1: Get Your API Keys (5-10 minutes)

You need at minimum:
- **Brave Search API** (for evidence gathering) - [Get key](https://brave.com/search/api/)
- **At least ONE AI model API**:
  - OpenAI (recommended) - [Get key](https://platform.openai.com/api-keys)
  - OR Anthropic - [Get key](https://console.anthropic.com/)
  - OR Google Gemini - [Get key](https://makersuite.google.com/app/apikey)
  - OR xAI Grok - [Get key](https://console.x.ai/)

## Step 2: Configure Environment

1. **Copy the example file:**
   ```bash
   cp env.example apps/adjudicator/.env
   ```

2. **Edit the file:**
   ```bash
   nano apps/adjudicator/.env
   ```

3. **Add your keys:**
   ```bash
   # Required for evidence gathering
   BRAVE_SEARCH_API_KEY=BSAxxx...your_brave_key

   # Add at least one AI API key
   OPENAI_API_KEY=sk-proj-xxx...your_openai_key
   ANTHROPIC_API_KEY=sk-ant-xxx...your_anthropic_key
   GOOGLE_API_KEY=AIzaSyxxx...your_google_key
   XAI_API_KEY=xai-xxx...your_xai_key
   ```

## Step 3: Restart Services

```bash
make down && make up
```

## Step 4: Test It

1. Open [http://localhost:3000](http://localhost:3000)
2. Search for a claim like: **"The sky is blue"**
3. Click "Create New Claim Analysis"
4. Watch the progress bar as it:
   - ✅ Gathers real evidence from the web
   - ✅ Gets real AI analysis from configured models
   - ✅ Shows proper citations and verdicts

## What Changed?

### Before (No API Keys):
```
Evidence: No evidence sources available
Model Response: "stub response to keep tests self-contained"
```

### After (With API Keys):
```
Evidence: 
  - Wikipedia: "Rayleigh scattering causes the sky to appear blue..."
  - NASA: "The atmosphere scatters blue light..."
  - Etc.

Model Response (GPT-4o): 
  "Based on the evidence from NASA and scientific sources about 
   Rayleigh scattering, the claim that the sky is blue is supported..."
```

## Troubleshooting

### Still seeing stubs?
- Check logs: `make logs-api`
- Verify API keys are correct (no extra spaces/quotes)
- Ensure you restarted services after adding keys

### No evidence found?
- Verify `BRAVE_SEARCH_API_KEY` is configured
- Check logs for "Web search API not available" message

### API errors?
- Check rate limits on your API dashboards
- Verify model names match current versions (see [API_SETUP.md](./API_SETUP.md))

## Cost Awareness

**Free Tiers:**
- Brave Search: 2,000 queries/month free
- OpenAI: $5 free credit for new accounts
- Anthropic: $5 free credit
- Google Gemini: Generous free tier
- xAI: Check current pricing

**For testing:** Free tiers are usually sufficient. A typical claim analysis uses:
- 1 Brave search (~15 results)
- 4 AI model calls (one per model configured)
- Total cost: ~$0.01-0.05 per claim with all 4 models

## Next Steps

- Read [API_SETUP.md](./API_SETUP.md) for detailed API configuration
- Configure all 4 AI APIs for the most comprehensive panel
- Try different claims and see how models agree/disagree
- Explore the consensus features for controversial claims

## Need Help?

Check the logs:
```bash
make logs-api    # Backend logs
make logs-web    # Frontend logs
```

Common issues are usually:
1. Forgot to restart services after adding keys
2. API key has typos or extra whitespace
3. Model names don't match current versions

