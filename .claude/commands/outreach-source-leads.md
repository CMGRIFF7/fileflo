# /outreach-source-leads

Source a batch of insurance broker leads from Apollo, score them, and prepare for campaign import.

## Instructions

You are sourcing leads for FileFlo's cold outreach pipeline targeting insurance brokers.

### Step 1: Determine Segment

Ask the user which segment to source (if not specified):
- **trucking** = DOT/Trucking insurance brokers (commercial auto, fleet, transportation)
- **osha** = Workers comp/OSHA insurance brokers (construction, manufacturing, workplace safety)

Also ask for:
- Batch size (default: 100)
- Geographic focus (default: Texas, California, Florida, Georgia, Illinois, Ohio, Pennsylvania, Tennessee, Indiana, North Carolina)
- Minimum score threshold (default: 50)

### Step 2: Search Apollo

**For "trucking" segment**, use `apollo_mixed_people_api_search` with:
- `person_titles`: ["insurance broker", "commercial insurance broker", "commercial lines producer", "insurance agent", "insurance producer", "account executive"]
- `q_organization_keyword_tags`: ["insurance", "commercial auto", "trucking insurance", "fleet insurance", "transportation insurance"]
- `person_seniorities`: ["senior", "manager", "director", "vp", "owner"]
- `organization_num_employees_ranges`: ["1,10", "11,50", "51,200"]
- `organization_locations`: [user-specified states]
- `per_page`: 100
- `include_similar_titles`: true

**For "osha" segment**, use `apollo_mixed_people_api_search` with:
- `person_titles`: ["insurance broker", "workers compensation specialist", "commercial insurance producer", "risk management consultant", "safety consultant", "insurance agent"]
- `q_organization_keyword_tags`: ["insurance", "workers compensation", "workplace safety", "risk management", "OSHA"]
- Same seniority, size, and geography filters

### Step 3: Score Each Lead (0-100)

Apply this scoring rubric to every result:

| Signal | Points |
|--------|--------|
| Title contains "broker" or "producer" | +20 |
| Title contains "owner" or "principal" or "president" | +15 |
| Org keywords match segment-specific terms | +15 |
| Seniority is VP/Owner/Director | +15 |
| Org employee count 11-50 | +10 |
| Located in top-10 target state | +10 |
| Has verified email (email_status != "unavailable") | +10 |
| Has LinkedIn URL | +5 |

### Step 4: Filter and Sort

- Remove leads below the minimum score threshold
- Sort by score descending
- Separate into tiers:
  - **Priority A** (70+): Will get personalized outreach + enrichment
  - **Priority B** (50-69): Standard sequence
  - **Skip** (below 50): Do not import

### Step 5: Output Results

Present a formatted table with:
- Name, Title, Company, Location, Score, Tier, LinkedIn URL, Email Status
- Summary: Total found, Priority A count, Priority B count, Skipped count
- Credit usage: How many Apollo credits were consumed
- Recommendation: Whether to enrich Priority A leads next (run `/outreach-enrich-leads`)

Also check Apollo credit balance using `apollo_users_api_profile` with `include_credit_usage: true` and report remaining credits.

### Important Notes
- Never pull more than 100 leads per search (best reply rates come from <100 recipient campaigns)
- Always check credit balance before and after sourcing
- If the search returns <50 results, suggest broadening title or geography filters
- Track which states/titles have been searched to avoid duplicates across batches
