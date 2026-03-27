# /outreach-weekly-report

Generate the Monday morning weekly performance report for the entire outreach pipeline.

## Instructions

You are generating a comprehensive weekly report for FileFlo's cold outreach pipeline.

### Step 1: Campaign Performance

Call `list_campaigns` to get all campaigns, then call `get_campaign_analytics` for each active campaign.

Also call `get_daily_campaign_analytics` with `start_date` = 7 days ago and `end_date` = today.

### Step 2: Sender Account Health

Call `list_accounts` to get all sender accounts.
Call `get_warmup_analytics` for all accounts with date range = last 7 days.

Flag accounts with:
- Inbox placement below 90%
- Spam rate above 2%
- Status != 1 (active)

### Step 3: Apollo Credit Balance

Call `apollo_users_api_profile` with `include_credit_usage: true`.

Calculate:
- Credits remaining
- Credits used this period
- Projected burn rate (credits/week)
- Weeks of credits remaining at current pace

### Step 4: Pipeline Summary

Aggregate across all campaigns:
- Total emails sent this week
- Total replies received
- Overall reply rate
- Bounce rate
- Unsubscribe rate

### Step 5: A/B Test Results

For each segment with multiple variants running:
- Compare reply rates
- Note statistical significance (need 100+ sends per variant)
- Recommend: kill loser, promote winner, or need more data

### Step 6: Generate Report

Format as:

```
======================================
FILEFLO OUTREACH - WEEKLY REPORT
Week of: [date range]
======================================

--- PIPELINE OVERVIEW ---
Emails Sent:        [N]
Replies:            [N] ([X]%)
Bounces:            [N] ([X]%)
Unsubscribes:       [N] ([X]%)
Meetings Booked:    [N] (manual input)
Trials Started:     [N] (manual input)
Conversions:        [N] (manual input)

--- CAMPAIGN BREAKDOWN ---
[For each campaign:]
  [Campaign Name]
  Status: [Active/Paused]
  Sent: [N] | Replies: [N] ([X]%) | Bounces: [N] ([X]%)
  Assessment: [emoji: green/yellow/red] [PERFORMING WELL / NEEDS WORK / KILL]

--- A/B TEST RESULTS ---
[Segment]: Variant A [X]% reply vs Variant B [X]% reply
  Winner: [A/B/too early]
  Sample size: [N] per variant
  Action: [recommendation]

--- SENDER ACCOUNT HEALTH ---
[N] accounts active, [N] with issues
[List any flagged accounts with reasons]

--- APOLLO CREDITS ---
Remaining: [N] / [total]
Burn rate: [N] credits/week
Runway: [N] weeks at current pace
Action needed: [yes/no + detail]

--- RECOMMENDATIONS ---
1. [Top priority action for this week]
2. [Second priority]
3. [Third priority]

--- NEXT WEEK PLAN ---
Batches to launch: [N] ([segments])
Leads to source: [N]
Variants to test: [description]
======================================
```

### Step 7: Action Items

Based on the report, generate specific action items:

**Kill campaigns** where reply rate is below 3% after 100+ sends.
**Scale campaigns** where reply rate is above 7%.
**Test new variants** for campaigns between 3-7% reply rate.
**Pause accounts** with deliverability issues.
**Upgrade Apollo** if credits will run out within 2 weeks.

### Important Notes
- Run this every Monday morning as the first outreach activity of the week
- Meetings booked and trial conversions are tracked manually -- ask the user for these numbers
- Compare week-over-week trends when historical data is available
- This report drives all decision-making for the week's outreach activities
