# API Configuration Guide

This guide explains how to configure API keys for Truce's AI model panel and web search features.

## Required API Keys

### 1. Brave AI Grounding API (For Evidence Gathering)

The Brave AI Grounding API is used to gather evidence from the web for claim analysis using AI-powered search with verifiable citations.

**Get your API key:**
1. Visit [Brave Search API Dashboard](https://api-dashboard.search.brave.com/)
2. Sign up for an account 
3. Subscribe to the **AI Grounding** plan (required for the grounding endpoint)
4. Get your API key from the dashboard

**Configure:**
Add to your `.env` file:
```bash
BRAVE_SEARCH_API_KEY=your_brave_api_key_here
```

**Important Notes:**
- **AI Grounding subscription required** - The regular search API won't work
- Without this key configured, you'll see "0 evidence found" and agent errors
- The API provides 2 requests per second rate limit
- Uses endpoint: `https://api.search.brave.com/res/v1/chat/completions`

**Reference:** [Brave AI Grounding Documentation](https://api-dashboard.search.brave.com/app/documentation/ai-grounding/get-started)

---

### 2. OpenAI API (For GPT Models)

**Get your API key:**
1. Visit [OpenAI Platform](https://platform.openai.com/)
2. Sign up or log in
3. Go to [API Keys](https://platform.openai.com/api-keys)
4. Create a new secret key

**Configure:**
Add to your `.env` file:
```bash
OPENAI_API_KEY=sk-your_openai_api_key_here
```

**Models used:**
- `gpt-4o` - Latest GPT-4 Optimized model

---

### 3. xAI Grok API (For Grok Models)

**Get your API key:**
1. Visit [xAI Console](https://console.x.ai/)
2. Sign up or log in
3. Generate an API key

**Configure:**
Add to your `.env` file:
```bash
XAI_API_KEY=your_xai_api_key_here
```

**Models used:**
- `grok-3` - Latest Grok model (replaces deprecated grok-beta)

---

### 4. Google Gemini API (For Gemini Models)

**Get your API key:**
1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Sign in with your Google account
3. Create an API key

**Configure:**
Add to your `.env` file:
```bash
GOOGLE_API_KEY=your_google_api_key_here
```

**Models used:**
- `gemini-2.0-flash-exp` - Latest Gemini experimental model

---

### 5. Anthropic API (For Claude Models)

**Get your API key:**
1. Visit [Anthropic Console](https://console.anthropic.com/)
2. Sign up or log in
3. Go to API Keys section
4. Create a new API key

**Configure:**
Add to your `.env` file:
```bash
ANTHROPIC_API_KEY=sk-ant-your_anthropic_api_key_here
```

**Models used:**
- `claude-sonnet-4-20250514` - Latest Claude Sonnet 4 (enhanced capabilities)

---

## Complete .env File Example

Create a `.env` file in the `apps/adjudicator/` directory:

```bash
# Web Search
BRAVE_SEARCH_API_KEY=your_brave_api_key_here

# AI Model APIs
OPENAI_API_KEY=sk-your_openai_api_key_here
XAI_API_KEY=your_xai_api_key_here
GOOGLE_API_KEY=your_google_api_key_here
ANTHROPIC_API_KEY=sk-ant-your_anthropic_api_key_here
```

## Testing Your Configuration

1. After adding API keys, restart the services:
   ```bash
   make down && make up
   ```

2. Create a test claim through the UI

3. Check the logs to verify API calls:
   ```bash
   make logs-api
   ```

## Troubleshooting

### No Evidence Found
- **Problem:** Claims show "No evidence sources available"
- **Solution:** Configure `BRAVE_SEARCH_API_KEY`

### Stub Responses from Models
- **Problem:** Model responses show "deterministic offline assessment" or "stub response"
- **Solution:** Configure the appropriate model API keys (see errors for which ones)

### API Rate Limits
- **Problem:** "Rate limit exceeded" errors
- **Solution:** Most APIs have free tiers with limits. Consider upgrading or spacing out requests.

### Invalid Model Errors
- **Problem:** "model not found" or "404" errors
- **Solution:** Ensure you're using the correct model names listed above. Old model names (like `grok-beta`) are deprecated.

## Cost Considerations

All these APIs have usage-based pricing:
- **Brave Search:** Free tier available, then pay-per-search
- **OpenAI:** Pay-per-token (GPT-4o is ~$2.50-$10 per 1M tokens)
- **xAI:** Pay-per-token (similar to OpenAI)
- **Google Gemini:** Free tier generous, then pay-per-request
- **Anthropic:** Pay-per-token (similar to OpenAI)

For development/testing, the free tiers are usually sufficient.

## Security Notes

- **Never commit** your `.env` file to version control
- Keep your API keys secret
- Rotate keys periodically
- Monitor usage to prevent unexpected charges
- Use environment-specific keys (dev vs production)

