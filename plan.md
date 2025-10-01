# Streamlined Search-to-Analysis Flow + Enhanced Evidence Gathering

## Goals
1. Transform the user experience from a complex search/cache flow to a simple, direct path: **Search → Loading → Results**
2. Fix deprecated Claude model and enhance evidence gathering for more comprehensive analysis

## Changes Made

### 1. Updated Search Bar Component
**File:** `apps/web/components/search-bar.tsx`

- Modified to directly initiate claim creation on submit
- Added loading state with spinner animation
- Navigates to `/analyzing` page with session ID instead of `/search`
- Removes the intermediate search results page from the flow

### 2. Created Analyzing Page
**File:** `apps/web/app/analyzing/page.tsx` (new)

- Minimalistic, elegant loading screen with progress animations
- Displays real-time progress updates via Server-Sent Events
- Shows current stage with appropriate icons and descriptions
- Progress bar with percentage indicator
- Collapsible detailed progress log
- Automatically redirects to claim page upon completion

**Key Features:**
- Clean, centered card design with gradient background
- Stage-based progress visualization (5% → 100%)
- Real-time updates for evidence gathering and model evaluation
- Smooth transitions and animations
- Error handling for failed connections
- Wrapped in Suspense boundary for proper Next.js SSR compatibility

### 3. Simplified Claim Page
**File:** `apps/web/app/claim/[slug]/page.tsx`

**Removed:**
- `ClaimVerifier` component and its controls
- Date pickers for time windows
- Provider selection checkboxes  
- "Refresh with latest" toggle
- Caching indicators

**Kept:**
- Evidence & Sources display (enhanced prominence)
- Model Panel Evaluation with detailed verdicts
- Model Consensus sidebar widget
- Replay bundle download
- Transparency information

### 4. Updated Verification Guide
**File:** `HOW_TO_VERIFY.md`

- Updated manual smoke tests to reflect new flow
- Removed references to verification controls
- Added instructions for testing the analyzing page
- Clarified the fresh analysis approach

## User Flow

```
┌─────────────┐
│  Home Page  │
│   Search    │
└──────┬──────┘
       │ [User enters query & clicks Search]
       ↓
┌──────────────┐
│  Analyzing   │ ← Real-time progress updates
│    Page      │   (SSE connection)
└──────┬───────┘
       │ [Automatic redirect on completion]
       ↓
┌──────────────┐
│  Claim Page  │
│   Results    │
└──────────────┘
```

## Technical Details

### Server-Sent Events Flow
1. User submits search → POST to `/claims/create-async`
2. Backend returns `session_id`
3. Frontend connects to `/claims/progress/{session_id}` (SSE)
4. Real-time progress events streamed to client
5. On completion event with slug, redirect to `/claim/{slug}`

### Progress Stages Tracked
- `initializing` (5%)
- `searching` (15%)
- `gathering_sources` (25%)
- `processing_evidence` (45-60%)
- `evaluating` (75%)
- `evaluation_complete` (95%)
- `complete` (100%)

## Benefits

1. **Simpler UX:** One-click from search to results
2. **Less Cognitive Load:** No caching controls to understand
3. **Transparent Progress:** Users see what's happening
4. **Fresh Analysis:** Every search generates new insights
5. **Cleaner UI:** Removed clutter from claim page

## Trade-offs

- **No Manual Re-verification:** Users can't tweak dates/providers after creation
- **Fresh Every Time:** No cache optimization (by design)
- **Network Dependency:** SSE connection required for progress updates

### 5. Fixed Claude Model Configuration
**Files:** `API_SETUP.md`, `apps/adjudicator/truce_adjudicator/panel/run_panel.py`

- Updated deprecated `claude-3-5-sonnet-20241022` to `claude-sonnet-4-20250514`
- Resolves 404 errors when using Anthropic's Claude models
- Uses the latest Claude Sonnet 4 with enhanced capabilities

### 6. Enhanced Evidence Gathering System
**Files:** Multiple backend files

**Major Improvements:**
- **Increased target evidence count**: From 8 to 20 sources
- **Removed gathering timeout**: No time limits for comprehensive evidence collection
- **Improved domain diversity**: Reduced share from 40% to 25% for more varied sources
- **Multiple search strategies**: Direct, academic, government, and news perspectives
- **Enhanced search parameters**: 
  - Increased results per query from 20 to 30
  - Enabled research mode for more comprehensive results
  - Improved query phrasing for diverse perspectives

**Technical Details:**
- `ExplorerAgent` now uses 4 different search strategies per claim
- Enhanced domain recognition for 50+ Canadian and international sources
- Rate-limited but comprehensive evidence collection
- Better deduplication across multiple search results

### 7. Agentic Loading UI + Error Handling
**Files:** `apps/web/app/analyzing/page.tsx`, multiple backend files

**UI Transformation:**
- **Removed progress bars** - No more artificial progress percentages
- **Real-time agent feed** - Shows each agent's activity as it happens
- **Agent-specific icons** - Academic Researcher, Policy Analyst, News Investigator, etc.
- **Live reasoning display** - Shows agent thoughts and decision-making
- **Source discovery tracking** - Real-time updates when sources are found
- **Multi-agent dashboard** - Overview of active agents and evidence collected

**Error Handling:**
- **No fallbacks** - System reports actual failures instead of hiding them
- **Graceful error communication** - Users see what went wrong and why
- **Agent-level error tracking** - Shows which agents encountered issues
- **Detailed error messages** - Explains API configuration issues, search failures, etc.
- **Transparent failure reporting** - Analysis continues with available data, users informed of limitations

### 8. Fixed Brave AI Grounding API Integration
**Files:** `apps/adjudicator/truce_adjudicator/mcp/web_search.py`, documentation

**API Implementation Fix:**
- **Corrected Authentication** - Using `x-subscription-token` header instead of incorrect OpenAI client
- **Proper Endpoint Usage** - Direct HTTP calls to `/chat/completions` endpoint
- **Enhanced Response Parsing** - Better extraction of citations and sources from AI responses
- **All 4 Agents Now Run** - Fixed early termination issue so Academic, Government, News, and Direct search agents all execute

**Configuration Requirements:**
- **Brave AI Grounding Plan Required** - Regular search API won't work
- **Proper API Key Setup** - Must be configured in BRAVE_SEARCH_API_KEY environment variable
- **Rate Limiting Respected** - 2 requests per second as per Brave documentation

## Files Modified
- `apps/web/components/search-bar.tsx`
- `apps/web/app/claim/[slug]/page.tsx`
- `apps/adjudicator/truce_adjudicator/panel/run_panel.py`
- `apps/adjudicator/truce_adjudicator/main.py`
- `apps/adjudicator/truce_adjudicator/mcp/explorer.py`
- `apps/adjudicator/truce_adjudicator/mcp/web_search.py`
- `API_SETUP.md`
- `HOW_TO_VERIFY.md`

## Files Created
- `apps/web/app/analyzing/page.tsx`

## Files Deprecated (Not Deleted)
- `apps/web/components/claim-verifier.tsx` (no longer used)
- `apps/web/app/search/page.tsx` (bypassed in new flow)

## Future Enhancements
- Add ability to cancel analysis in progress
- Show estimated time remaining
- Add retry logic for failed analyses
- Implement analysis history/bookmarking
