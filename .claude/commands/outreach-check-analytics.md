# /outreach-check-analytics

Pull and analyze campaign performance metrics from Instantly.

## Instructions

You are analyzing FileFlo's cold outreach campaign performance.

### Step 1: Get Campaign List

Call `list_campaigns` to get all active campaigns. For each campaign, note:
- Campaign ID, name, status
- Lead count, sent count

### Step 2: Pull Analytics

For each active campaign (or a specific campaign if user specifies), call `get_campaign_analytics`.

If comparing over time, also call `get_daily_campaign_analytics` with appropriate date range.

### Step 3: Calculate Key Metrics

For each campaign, calculate and display:

| Metric | Formula | Target | Kill Threshold |
|--------|---------|--------|----------------|
| Reply Rate | replies / sent | 10%+ | Below 3% after 100 sends |
| Bounce Rate | bounces / sent | Below 2% | Above 5% |
| Unsubscribe Rate | unsubscribes / sent | Below 0.5% | Above 1% |
| Positive Reply Rate | (manual) positive / total replies | 50%+ | Below 30% |

### Step 4: Compare Variants

If A/B tests are running (same segment, different variants):
- Compare reply rates between Variant A and Variant B
- Flag if one variant has 2x+ better reply rate after 100+ sends each
- Recommend: **KILL** the loser, **PROMOTE** the winner

### Step 5: Generate Recommendations

Based on the data:

**If reply rate is below 3% after 100+ sends:**
- Recommend killing the variant
- Suggest testing a new subject line or opening hook

**If reply rate is 3-7%:**
- Campaign is working but improvable
- Suggest testing one variable (subject, CTA, or timing)

**If reply rate is 7%+:**
- Campaign is performing well
- Recommend scaling (add more leads, launch in new geographies)

**If bounce rate is above 5%:**
- URGENT: Pause campaign immediately
- Likely cause: bad email list or domain reputation issue
- Recommend: verify all remaining leads, check sender account health

**If unsubscribe rate is above 1%:**
- Review email copy for spam triggers
- Check if targeting is off (wrong ICP)

### Step 6: Output Report

Format as:

```
=== FILEFLO OUTREACH ANALYTICS ===
Date: [current date]

CAMPAIGN: [name]
  Status: [active/paused]
  Sent: [N] | Replies: [N] ([X]%) | Bounces: [N] ([X]%) | Unsubs: [N] ([X]%)
  Assessment: [PERFORMING WELL / NEEDS WORK / KILL]
  Action: [specific recommendation]

A/B TEST RESULTS (if applicable):
  Variant A: [reply rate]% | Variant B: [reply rate]%
  Winner: [A or B] | Confidence: [high/low - based on sample size]
  Action: [kill loser / need more data]

OVERALL PIPELINE:
  Total sent this week: [N]
  Total replies: [N] ([X]%)
  Campaigns active: [N]
  Next batch recommended: [yes/no + reasoning]
```

### Important Notes
- Minimum 100 sends before making statistical conclusions about variant performance
- Daily analytics are more useful than total analytics for spotting trends
- If ALL campaigns are underperforming, the issue is likely deliverability (check `/outreach-verify-warmup`)
- Track results over time to identify which day-of-week and time-of-day performs best
