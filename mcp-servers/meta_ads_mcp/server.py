#!/usr/bin/env python3
"""
Meta (Facebook) Marketing API MCP Server.

Provides tools to create and manage Facebook/Instagram ad campaigns,
ad sets, ads, creatives, audiences, and insights via the Meta Marketing API.

Requires environment variables:
    META_ACCESS_TOKEN   - Long-lived or system user access token
    META_AD_ACCOUNT_ID  - Ad account ID (format: act_XXXXXXXXX)
    META_APP_ID         - Meta app ID (optional, for token debug)
    META_APP_SECRET     - Meta app secret (optional, for token debug)
"""

import json
import os
from enum import Enum
from typing import Any, Dict, List, Optional

import httpx
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field, field_validator

# ---------------------------------------------------------------------------
# Server Initialization
# ---------------------------------------------------------------------------
mcp = FastMCP("meta_ads_mcp")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
GRAPH_API_VERSION = "v21.0"
GRAPH_BASE_URL = f"https://graph.facebook.com/{GRAPH_API_VERSION}"
DEFAULT_TIMEOUT = 30.0


def _get_credentials() -> tuple[str, str]:
    """Return (access_token, ad_account_id) from env or raise."""
    token = os.environ.get("META_ACCESS_TOKEN", "")
    account = os.environ.get("META_AD_ACCOUNT_ID", "")
    if not token:
        raise ValueError(
            "META_ACCESS_TOKEN environment variable is not set. "
            "Set it to your Meta long-lived access token."
        )
    if not account:
        raise ValueError(
            "META_AD_ACCOUNT_ID environment variable is not set. "
            "Set it to your ad account ID (format: act_XXXXXXXXX)."
        )
    # Normalize account ID
    if not account.startswith("act_"):
        account = f"act_{account}"
    return token, account


# ---------------------------------------------------------------------------
# Shared HTTP Client
# ---------------------------------------------------------------------------
async def _graph_request(
    method: str,
    path: str,
    params: Optional[Dict[str, Any]] = None,
    data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Make a request to the Meta Graph API."""
    token, _ = _get_credentials()
    base_params = {"access_token": token}
    if params:
        base_params.update(params)

    url = f"{GRAPH_BASE_URL}/{path.lstrip('/')}"
    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
        if method.upper() == "GET":
            response = await client.get(url, params=base_params)
        elif method.upper() == "POST":
            response = await client.post(url, params=base_params, data=data or {})
        elif method.upper() == "DELETE":
            response = await client.delete(url, params=base_params)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")

        response.raise_for_status()
        return response.json()


async def _account_request(
    method: str,
    endpoint: str,
    params: Optional[Dict[str, Any]] = None,
    data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Make a request scoped to the configured ad account."""
    _, account_id = _get_credentials()
    return await _graph_request(method, f"{account_id}/{endpoint}", params, data)


# ---------------------------------------------------------------------------
# Error Handling
# ---------------------------------------------------------------------------
def _handle_error(e: Exception) -> str:
    if isinstance(e, httpx.HTTPStatusError):
        try:
            err = e.response.json().get("error", {})
            code = err.get("code", e.response.status_code)
            msg = err.get("message", str(e))
            tip = {
                190: "Access token is invalid or expired. Generate a new token at developers.facebook.com.",
                200: "Permission denied. Ensure your app has the ads_management permission.",
                272: "Ad account access denied. Check that META_AD_ACCOUNT_ID is correct.",
                100: "Invalid parameter. Check the field names and values you provided.",
                17: "Rate limit hit. Wait a few minutes and try again.",
            }.get(code, "Check Meta API docs for error code details.")
            return f"Meta API Error {code}: {msg}\nTip: {tip}"
        except Exception:
            return f"HTTP {e.response.status_code}: {e.response.text[:500]}"
    elif isinstance(e, ValueError):
        return f"Configuration Error: {e}"
    elif isinstance(e, httpx.TimeoutException):
        return "Error: Request timed out. Meta API may be slow — try again."
    return f"Unexpected error: {type(e).__name__}: {e}"


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class CampaignObjective(str, Enum):
    OUTCOME_AWARENESS = "OUTCOME_AWARENESS"
    OUTCOME_TRAFFIC = "OUTCOME_TRAFFIC"
    OUTCOME_ENGAGEMENT = "OUTCOME_ENGAGEMENT"
    OUTCOME_LEADS = "OUTCOME_LEADS"
    OUTCOME_APP_PROMOTION = "OUTCOME_APP_PROMOTION"
    OUTCOME_SALES = "OUTCOME_SALES"


class CampaignStatus(str, Enum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    DELETED = "DELETED"
    ARCHIVED = "ARCHIVED"


class BillingEvent(str, Enum):
    IMPRESSIONS = "IMPRESSIONS"
    LINK_CLICKS = "LINK_CLICKS"
    APP_INSTALLS = "APP_INSTALLS"
    PAGE_LIKES = "PAGE_LIKES"
    POST_ENGAGEMENT = "POST_ENGAGEMENT"
    THRUPLAY = "THRUPLAY"


class OptimizationGoal(str, Enum):
    REACH = "REACH"
    IMPRESSIONS = "IMPRESSIONS"
    LINK_CLICKS = "LINK_CLICKS"
    LANDING_PAGE_VIEWS = "LANDING_PAGE_VIEWS"
    LEAD_GENERATION = "LEAD_GENERATION"
    CONVERSATIONS = "CONVERSATIONS"
    APP_INSTALLS = "APP_INSTALLS"
    OFFSITE_CONVERSIONS = "OFFSITE_CONVERSIONS"


class InsightDatePreset(str, Enum):
    TODAY = "today"
    YESTERDAY = "yesterday"
    LAST_7_DAYS = "last_7d"
    LAST_14_DAYS = "last_14d"
    LAST_30_DAYS = "last_30d"
    LAST_90_DAYS = "last_90d"
    THIS_MONTH = "this_month"
    LAST_MONTH = "last_month"


class InsightLevel(str, Enum):
    ACCOUNT = "account"
    CAMPAIGN = "campaign"
    ADSET = "adset"
    AD = "ad"


# ---------------------------------------------------------------------------
# Pydantic Input Models
# ---------------------------------------------------------------------------
class CreateCampaignInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    name: str = Field(..., description="Campaign name (e.g., 'FileFlo - Trucking Owners Q1')", min_length=1, max_length=400)
    objective: CampaignObjective = Field(
        ...,
        description="Campaign objective. Use OUTCOME_LEADS for lead gen, OUTCOME_TRAFFIC for website traffic, OUTCOME_AWARENESS for brand awareness."
    )
    status: CampaignStatus = Field(default=CampaignStatus.PAUSED, description="Initial campaign status. Default: PAUSED (recommended for review before launch).")
    daily_budget: Optional[int] = Field(default=None, description="Daily budget in cents (e.g., 5000 = $50.00). Set either daily_budget or lifetime_budget, not both.", ge=100)
    lifetime_budget: Optional[int] = Field(default=None, description="Lifetime budget in cents (e.g., 100000 = $1000.00). Set either daily_budget or lifetime_budget, not both.", ge=100)
    special_ad_categories: Optional[List[str]] = Field(
        default_factory=list,
        description="Required for certain industries. Use ['HOUSING'], ['EMPLOYMENT'], ['CREDIT'], or ['ISSUES_ELECTIONS_POLITICS'] if applicable. Leave empty for most campaigns."
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Campaign name cannot be empty")
        return v.strip()


class UpdateCampaignInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    campaign_id: str = Field(..., description="Campaign ID to update (e.g., '120210000000001')")
    name: Optional[str] = Field(default=None, description="New campaign name")
    status: Optional[CampaignStatus] = Field(default=None, description="New status: ACTIVE, PAUSED, ARCHIVED")
    daily_budget: Optional[int] = Field(default=None, description="New daily budget in cents", ge=100)
    lifetime_budget: Optional[int] = Field(default=None, description="New lifetime budget in cents", ge=100)


class ListCampaignsInput(BaseModel):
    model_config = ConfigDict(validate_assignment=True, extra="forbid")

    status_filter: Optional[CampaignStatus] = Field(default=None, description="Filter by status: ACTIVE, PAUSED, ARCHIVED, DELETED")
    limit: int = Field(default=20, description="Number of campaigns to return", ge=1, le=100)


class CreateAdSetInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    name: str = Field(..., description="Ad set name (e.g., 'Trucking Owners - TX/CA - 35-65')", min_length=1, max_length=400)
    campaign_id: str = Field(..., description="Parent campaign ID")
    daily_budget: Optional[int] = Field(default=None, description="Daily budget in cents (overrides campaign budget if set)", ge=100)
    lifetime_budget: Optional[int] = Field(default=None, description="Lifetime budget in cents", ge=100)
    billing_event: BillingEvent = Field(default=BillingEvent.IMPRESSIONS, description="What you get billed for: IMPRESSIONS, LINK_CLICKS, etc.")
    optimization_goal: OptimizationGoal = Field(default=OptimizationGoal.LINK_CLICKS, description="What Meta optimizes for: LINK_CLICKS, LEAD_GENERATION, LANDING_PAGE_VIEWS, etc.")
    targeting_geo_locations: Optional[Dict[str, Any]] = Field(
        default=None,
        description='Geo targeting. Example: {"countries": ["US"]} or {"regions": [{"key": "3847"}]} for Texas.'
    )
    targeting_age_min: Optional[int] = Field(default=25, description="Minimum age (18-65)", ge=18, le=65)
    targeting_age_max: Optional[int] = Field(default=65, description="Maximum age (18-65)", ge=18, le=65)
    targeting_genders: Optional[List[int]] = Field(default=None, description="Gender targeting: 1=male, 2=female. Omit for all genders.")
    targeting_interests: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description='Interest targeting. Example: [{"id": "6003107902433", "name": "Trucking"}]. Use meta_search_targeting_interests to find IDs.'
    )
    targeting_behaviors: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description='Behavior targeting. Example: [{"id": "6002714895372", "name": "Small business owners"}].'
    )
    custom_audience_ids: Optional[List[str]] = Field(default=None, description="List of custom audience IDs to include")
    status: CampaignStatus = Field(default=CampaignStatus.PAUSED, description="Ad set status")
    start_time: Optional[str] = Field(default=None, description="Start time in ISO 8601 format (e.g., '2026-04-01T00:00:00-0500')")
    end_time: Optional[str] = Field(default=None, description="End time in ISO 8601 format")


class CreateAdCreativeInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    name: str = Field(..., description="Creative name for internal reference", min_length=1, max_length=400)
    page_id: str = Field(..., description="Facebook Page ID associated with the ad")
    headline: str = Field(..., description="Ad headline (max 40 chars for best display)", max_length=255)
    primary_text: str = Field(..., description="Main ad body text (primary text shown above the image)", max_length=2000)
    description: Optional[str] = Field(default=None, description="Link description shown below headline (max 30 chars for best display)", max_length=255)
    link_url: str = Field(..., description="Destination URL (e.g., 'https://getfileflo.com')")
    call_to_action: str = Field(default="LEARN_MORE", description="CTA button: LEARN_MORE, SIGN_UP, GET_QUOTE, CONTACT_US, BOOK_TRAVEL, DOWNLOAD, GET_OFFER")
    image_hash: Optional[str] = Field(default=None, description="Image hash from meta_upload_ad_image. Either image_hash or video_id required.")
    video_id: Optional[str] = Field(default=None, description="Video ID for video ads")
    instagram_actor_id: Optional[str] = Field(default=None, description="Instagram account ID if running on Instagram")


class CreateAdInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    name: str = Field(..., description="Ad name for internal reference", min_length=1, max_length=400)
    adset_id: str = Field(..., description="Parent ad set ID")
    creative_id: str = Field(..., description="Ad creative ID from meta_create_ad_creative")
    status: CampaignStatus = Field(default=CampaignStatus.PAUSED, description="Ad status")


class GetInsightsInput(BaseModel):
    model_config = ConfigDict(validate_assignment=True, extra="forbid")

    level: InsightLevel = Field(default=InsightLevel.CAMPAIGN, description="Aggregation level: account, campaign, adset, or ad")
    date_preset: InsightDatePreset = Field(default=InsightDatePreset.LAST_7_DAYS, description="Date range preset")
    object_id: Optional[str] = Field(default=None, description="Specific campaign/adset/ad ID. If omitted, returns account-level data.")
    fields: Optional[List[str]] = Field(
        default=None,
        description="Specific fields to return. Default: spend, impressions, clicks, ctr, cpc, cpm, reach, frequency, actions."
    )


class SearchTargetingInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    query: str = Field(..., description="Search term (e.g., 'trucking', 'commercial insurance', 'small business')", min_length=2)
    targeting_type: str = Field(default="adinterest", description="Type to search: adinterest, adeducationschool, adcity, adregion, adcountry, adzipcode, adlocale")
    limit: int = Field(default=20, description="Number of results to return", ge=1, le=50)


class CreateCustomAudienceInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    name: str = Field(..., description="Audience name (e.g., 'FileFlo Website Visitors 30d')", min_length=1, max_length=200)
    subtype: str = Field(
        ...,
        description="Audience type: WEBSITE (pixel-based), CUSTOM (uploaded list), LOOKALIKE (lookalike source), ENGAGEMENT (page/video engagers)"
    )
    description: Optional[str] = Field(default=None, description="Internal description of this audience")
    pixel_id: Optional[str] = Field(default=None, description="Meta Pixel ID (required for WEBSITE subtype)")
    retention_days: Optional[int] = Field(default=30, description="Days to retain website visitors (1-180, for WEBSITE subtype)", ge=1, le=180)


class DeleteObjectInput(BaseModel):
    model_config = ConfigDict(validate_assignment=True, extra="forbid")

    object_id: str = Field(..., description="Campaign, ad set, ad, or creative ID to delete")
    object_type: str = Field(..., description="Type of object: campaign, adset, ad, creative, audience")


# ---------------------------------------------------------------------------
# Tool: List Campaigns
# ---------------------------------------------------------------------------
@mcp.tool(
    name="meta_list_campaigns",
    annotations={
        "title": "List Meta Ad Campaigns",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def meta_list_campaigns(params: ListCampaignsInput) -> str:
    """List all ad campaigns in the Meta ad account.

    Returns campaign IDs, names, objectives, status, and budget information.
    Use this to get campaign IDs needed for creating ad sets or pulling insights.

    Args:
        params (ListCampaignsInput):
            - status_filter: Filter by ACTIVE, PAUSED, ARCHIVED, or DELETED
            - limit: Number of campaigns to return (1-100, default 20)

    Returns:
        str: JSON array of campaigns with id, name, objective, status, daily_budget, lifetime_budget.

    Examples:
        - "Show me all my active campaigns" -> status_filter=ACTIVE
        - "List all campaigns" -> no filter
    """
    try:
        fields = "id,name,objective,status,daily_budget,lifetime_budget,created_time,updated_time"
        query_params: Dict[str, Any] = {"fields": fields, "limit": params.limit}
        if params.status_filter:
            query_params["effective_status"] = json.dumps([params.status_filter.value])

        data = await _account_request("GET", "campaigns", params=query_params)
        campaigns = data.get("data", [])

        if not campaigns:
            return json.dumps({"campaigns": [], "count": 0, "message": "No campaigns found."})

        # Convert budgets from cents to dollars for readability
        for c in campaigns:
            for budget_field in ("daily_budget", "lifetime_budget"):
                if c.get(budget_field):
                    c[f"{budget_field}_dollars"] = int(c[budget_field]) / 100

        return json.dumps({"campaigns": campaigns, "count": len(campaigns)}, indent=2)
    except Exception as e:
        return _handle_error(e)


# ---------------------------------------------------------------------------
# Tool: Create Campaign
# ---------------------------------------------------------------------------
@mcp.tool(
    name="meta_create_campaign",
    annotations={
        "title": "Create Meta Ad Campaign",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
async def meta_create_campaign(params: CreateCampaignInput) -> str:
    """Create a new Meta (Facebook/Instagram) ad campaign.

    Creates the top-level campaign. After creating, add ad sets with meta_create_adset,
    then add ads with meta_create_ad. Campaign starts PAUSED by default for review.

    Args:
        params (CreateCampaignInput):
            - name: Campaign name
            - objective: OUTCOME_LEADS, OUTCOME_TRAFFIC, OUTCOME_AWARENESS, OUTCOME_SALES, OUTCOME_ENGAGEMENT
            - status: ACTIVE or PAUSED (default: PAUSED)
            - daily_budget: Budget in cents (e.g., 5000 = $50/day)
            - lifetime_budget: Total lifetime budget in cents
            - special_ad_categories: Required for housing/employment/credit ads. Usually empty.

    Returns:
        str: JSON with campaign id, name, and status.

    Examples:
        - "Create a lead gen campaign for $50/day" -> objective=OUTCOME_LEADS, daily_budget=5000
        - "Create traffic campaign with $500 total" -> objective=OUTCOME_TRAFFIC, lifetime_budget=50000
    """
    try:
        post_data: Dict[str, Any] = {
            "name": params.name,
            "objective": params.objective.value,
            "status": params.status.value,
            "special_ad_categories": json.dumps(params.special_ad_categories or []),
        }
        if params.daily_budget:
            post_data["daily_budget"] = params.daily_budget
        if params.lifetime_budget:
            post_data["lifetime_budget"] = params.lifetime_budget

        result = await _account_request("POST", "campaigns", data=post_data)
        return json.dumps({
            "success": True,
            "campaign_id": result.get("id"),
            "name": params.name,
            "objective": params.objective.value,
            "status": params.status.value,
            "message": f"Campaign created. ID: {result.get('id')}. Next: create an ad set with meta_create_adset."
        }, indent=2)
    except Exception as e:
        return _handle_error(e)


# ---------------------------------------------------------------------------
# Tool: Update Campaign
# ---------------------------------------------------------------------------
@mcp.tool(
    name="meta_update_campaign",
    annotations={
        "title": "Update Meta Ad Campaign",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def meta_update_campaign(params: UpdateCampaignInput) -> str:
    """Update an existing Meta ad campaign (name, status, budget).

    Use to pause/activate campaigns, rename them, or adjust budgets.

    Args:
        params (UpdateCampaignInput):
            - campaign_id: Campaign ID to update
            - name: New name (optional)
            - status: New status — ACTIVE, PAUSED, ARCHIVED (optional)
            - daily_budget: New daily budget in cents (optional)
            - lifetime_budget: New lifetime budget in cents (optional)

    Returns:
        str: Success confirmation with updated campaign ID.
    """
    try:
        post_data: Dict[str, Any] = {}
        if params.name:
            post_data["name"] = params.name
        if params.status:
            post_data["status"] = params.status.value
        if params.daily_budget:
            post_data["daily_budget"] = params.daily_budget
        if params.lifetime_budget:
            post_data["lifetime_budget"] = params.lifetime_budget

        if not post_data:
            return "Error: No fields provided to update. Provide at least one of: name, status, daily_budget, lifetime_budget."

        result = await _graph_request("POST", params.campaign_id, data=post_data)
        return json.dumps({"success": result.get("success", True), "campaign_id": params.campaign_id, "updated_fields": list(post_data.keys())}, indent=2)
    except Exception as e:
        return _handle_error(e)


# ---------------------------------------------------------------------------
# Tool: Create Ad Set
# ---------------------------------------------------------------------------
@mcp.tool(
    name="meta_create_adset",
    annotations={
        "title": "Create Meta Ad Set",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
async def meta_create_adset(params: CreateAdSetInput) -> str:
    """Create a new ad set within a campaign. Ad sets define targeting, budget, and schedule.

    Use meta_search_targeting to find interest/behavior IDs before creating.
    For trucking owner audiences, target interests like 'Trucking', 'Owner-operator',
    and behaviors like 'Small business owners'.

    Args:
        params (CreateAdSetInput):
            - name: Ad set name
            - campaign_id: Parent campaign ID
            - billing_event: What you pay for (default: IMPRESSIONS)
            - optimization_goal: What Meta optimizes for (default: LINK_CLICKS)
            - targeting_geo_locations: {"countries": ["US"]} or specific regions/cities
            - targeting_age_min/max: Age range (default: 25-65)
            - targeting_interests: List of {id, name} interest objects
            - targeting_behaviors: List of {id, name} behavior objects
            - custom_audience_ids: Custom audience IDs to include
            - daily_budget or lifetime_budget: In cents

    Returns:
        str: JSON with adset_id, name, and next steps.
    """
    try:
        # Build targeting spec
        targeting: Dict[str, Any] = {
            "age_min": params.targeting_age_min or 25,
            "age_max": params.targeting_age_max or 65,
        }
        if params.targeting_geo_locations:
            targeting["geo_locations"] = params.targeting_geo_locations
        else:
            targeting["geo_locations"] = {"countries": ["US"]}
        if params.targeting_genders:
            targeting["genders"] = params.targeting_genders
        if params.targeting_interests:
            targeting["interests"] = params.targeting_interests
        if params.targeting_behaviors:
            targeting["behaviors"] = params.targeting_behaviors
        if params.custom_audience_ids:
            targeting["custom_audiences"] = [{"id": aid} for aid in params.custom_audience_ids]

        post_data: Dict[str, Any] = {
            "name": params.name,
            "campaign_id": params.campaign_id,
            "billing_event": params.billing_event.value,
            "optimization_goal": params.optimization_goal.value,
            "targeting": json.dumps(targeting),
            "status": params.status.value,
        }
        if params.daily_budget:
            post_data["daily_budget"] = params.daily_budget
        if params.lifetime_budget:
            post_data["lifetime_budget"] = params.lifetime_budget
        if params.start_time:
            post_data["start_time"] = params.start_time
        if params.end_time:
            post_data["end_time"] = params.end_time

        result = await _account_request("POST", "adsets", data=post_data)
        return json.dumps({
            "success": True,
            "adset_id": result.get("id"),
            "name": params.name,
            "campaign_id": params.campaign_id,
            "message": f"Ad set created. ID: {result.get('id')}. Next: create a creative with meta_create_ad_creative, then an ad with meta_create_ad."
        }, indent=2)
    except Exception as e:
        return _handle_error(e)


# ---------------------------------------------------------------------------
# Tool: Create Ad Creative
# ---------------------------------------------------------------------------
@mcp.tool(
    name="meta_create_ad_creative",
    annotations={
        "title": "Create Meta Ad Creative",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
async def meta_create_ad_creative(params: CreateAdCreativeInput) -> str:
    """Create an ad creative (the visual + copy combination) for use in ads.

    Upload an image first with meta_upload_ad_image to get an image_hash.
    Creative defines the headline, body text, image, link, and CTA.

    Args:
        params (CreateAdCreativeInput):
            - name: Internal creative name
            - page_id: Your Facebook Page ID
            - headline: Short, punchy headline (40 chars ideal)
            - primary_text: Main ad copy shown above the image (up to 2000 chars)
            - description: Optional link description below headline
            - link_url: Destination URL
            - call_to_action: LEARN_MORE, SIGN_UP, GET_QUOTE, CONTACT_US, DOWNLOAD
            - image_hash: From meta_upload_ad_image
            - video_id: For video ads (alternative to image_hash)

    Returns:
        str: JSON with creative_id for use in meta_create_ad.
    """
    try:
        link_data: Dict[str, Any] = {
            "message": params.primary_text,
            "link": params.link_url,
            "name": params.headline,
            "call_to_action": {"type": params.call_to_action},
        }
        if params.description:
            link_data["description"] = params.description
        if params.image_hash:
            link_data["image_hash"] = params.image_hash

        object_story_spec: Dict[str, Any] = {
            "page_id": params.page_id,
        }
        if params.video_id:
            object_story_spec["video_data"] = {
                "video_id": params.video_id,
                "title": params.headline,
                "message": params.primary_text,
                "call_to_action": {"type": params.call_to_action, "value": {"link": params.link_url}},
            }
        else:
            object_story_spec["link_data"] = link_data

        if params.instagram_actor_id:
            object_story_spec["instagram_actor_id"] = params.instagram_actor_id

        post_data = {
            "name": params.name,
            "object_story_spec": json.dumps(object_story_spec),
        }

        result = await _account_request("POST", "adcreatives", data=post_data)
        return json.dumps({
            "success": True,
            "creative_id": result.get("id"),
            "name": params.name,
            "message": f"Creative created. ID: {result.get('id')}. Next: create an ad with meta_create_ad using this creative_id."
        }, indent=2)
    except Exception as e:
        return _handle_error(e)


# ---------------------------------------------------------------------------
# Tool: Create Ad
# ---------------------------------------------------------------------------
@mcp.tool(
    name="meta_create_ad",
    annotations={
        "title": "Create Meta Ad",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
async def meta_create_ad(params: CreateAdInput) -> str:
    """Create an ad by combining an ad set (targeting/budget) with a creative (copy/image).

    This is the final step in the campaign creation workflow:
    Campaign -> Ad Set -> Creative -> Ad

    Args:
        params (CreateAdInput):
            - name: Ad name for internal reference
            - adset_id: Parent ad set ID
            - creative_id: Creative ID from meta_create_ad_creative
            - status: ACTIVE or PAUSED (default: PAUSED)

    Returns:
        str: JSON with ad_id and confirmation.
    """
    try:
        post_data = {
            "name": params.name,
            "adset_id": params.adset_id,
            "creative": json.dumps({"creative_id": params.creative_id}),
            "status": params.status.value,
        }

        result = await _account_request("POST", "ads", data=post_data)
        return json.dumps({
            "success": True,
            "ad_id": result.get("id"),
            "name": params.name,
            "adset_id": params.adset_id,
            "creative_id": params.creative_id,
            "status": params.status.value,
            "message": f"Ad created successfully. ID: {result.get('id')}. Set status to ACTIVE when ready to launch."
        }, indent=2)
    except Exception as e:
        return _handle_error(e)


# ---------------------------------------------------------------------------
# Tool: Get Insights / Analytics
# ---------------------------------------------------------------------------
@mcp.tool(
    name="meta_get_insights",
    annotations={
        "title": "Get Meta Ad Insights",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def meta_get_insights(params: GetInsightsInput) -> str:
    """Pull performance analytics from Meta ad campaigns, ad sets, or ads.

    Returns spend, impressions, clicks, CTR, CPC, CPM, reach, frequency,
    and conversion actions. Use to monitor ROI and optimize campaigns.

    Args:
        params (GetInsightsInput):
            - level: account, campaign, adset, or ad (default: campaign)
            - date_preset: today, yesterday, last_7d, last_14d, last_30d, last_90d, this_month, last_month
            - object_id: Specific campaign/adset/ad ID (omit for account-level)
            - fields: Specific metrics to return (omit for default set)

    Returns:
        str: JSON with performance metrics including spend, impressions, clicks, CTR, CPC, actions.

    Examples:
        - "How did my campaigns perform this week?" -> level=campaign, date_preset=last_7d
        - "Show me ad-level breakdown for last 30 days" -> level=ad, date_preset=last_30d
        - "How much did campaign 12345 spend?" -> level=campaign, object_id="12345"
    """
    try:
        default_fields = [
            "campaign_name", "adset_name", "ad_name",
            "spend", "impressions", "clicks", "ctr", "cpc", "cpm",
            "reach", "frequency", "actions", "cost_per_action_type",
            "date_start", "date_stop"
        ]
        fields_to_fetch = params.fields or default_fields

        query_params: Dict[str, Any] = {
            "level": params.level.value,
            "date_preset": params.date_preset.value,
            "fields": ",".join(fields_to_fetch),
            "limit": 50,
        }

        # Route to object-level or account-level
        if params.object_id:
            data = await _graph_request("GET", f"{params.object_id}/insights", params=query_params)
        else:
            data = await _account_request("GET", "insights", params=query_params)

        results = data.get("data", [])
        if not results:
            return json.dumps({"message": f"No data found for {params.date_preset.value}. Campaign may have no spend yet.", "data": []})

        # Summarize totals
        total_spend = sum(float(r.get("spend", 0)) for r in results)
        total_impressions = sum(int(r.get("impressions", 0)) for r in results)
        total_clicks = sum(int(r.get("clicks", 0)) for r in results)
        avg_ctr = (total_clicks / total_impressions * 100) if total_impressions else 0

        return json.dumps({
            "summary": {
                "total_spend_usd": round(total_spend, 2),
                "total_impressions": total_impressions,
                "total_clicks": total_clicks,
                "avg_ctr_pct": round(avg_ctr, 3),
                "date_range": params.date_preset.value,
                "level": params.level.value,
            },
            "data": results,
            "count": len(results),
        }, indent=2)
    except Exception as e:
        return _handle_error(e)


# ---------------------------------------------------------------------------
# Tool: Search Targeting Options
# ---------------------------------------------------------------------------
@mcp.tool(
    name="meta_search_targeting",
    annotations={
        "title": "Search Meta Targeting Options",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def meta_search_targeting(params: SearchTargetingInput) -> str:
    """Search for Facebook targeting interests, behaviors, demographics, and locations.

    Use this BEFORE creating ad sets to find valid targeting IDs.
    Returns IDs and names to use in meta_create_adset targeting fields.

    Args:
        params (SearchTargetingInput):
            - query: Search term (e.g., 'trucking', 'owner operator', 'commercial insurance')
            - targeting_type: adinterest (default), adeducationschool, adcity, adregion
            - limit: Number of results (1-50)

    Returns:
        str: JSON list of targeting options with id, name, audience_size, path.

    Examples:
        - "Find trucking interests" -> query="trucking", targeting_type="adinterest"
        - "Find Texas regions" -> query="Texas", targeting_type="adregion"
        - "Find small business behaviors" -> query="small business", targeting_type="adinterest"
    """
    try:
        token, _ = _get_credentials()
        query_params = {
            "type": params.targeting_type,
            "q": params.query,
            "limit": params.limit,
            "access_token": token,
        }
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            response = await client.get(
                f"{GRAPH_BASE_URL}/search",
                params=query_params,
            )
            response.raise_for_status()
            data = response.json()

        results = data.get("data", [])
        if not results:
            return json.dumps({"message": f"No targeting options found for '{params.query}'.", "data": []})

        return json.dumps({
            "query": params.query,
            "type": params.targeting_type,
            "count": len(results),
            "results": results,
        }, indent=2)
    except Exception as e:
        return _handle_error(e)


# ---------------------------------------------------------------------------
# Tool: List Custom Audiences
# ---------------------------------------------------------------------------
@mcp.tool(
    name="meta_list_audiences",
    annotations={
        "title": "List Meta Custom Audiences",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def meta_list_audiences(params: BaseModel) -> str:
    """List all custom audiences in the ad account.

    Returns audience IDs, names, types, sizes, and status.
    Use audience IDs in meta_create_adset to target specific groups.

    Returns:
        str: JSON array of custom audiences.
    """
    try:
        fields = "id,name,subtype,approximate_count_lower_bound,approximate_count_upper_bound,delivery_status,description"
        data = await _account_request("GET", "customaudiences", params={"fields": fields, "limit": 50})
        audiences = data.get("data", [])
        return json.dumps({"audiences": audiences, "count": len(audiences)}, indent=2)
    except Exception as e:
        return _handle_error(e)


# ---------------------------------------------------------------------------
# Tool: Create Custom Audience
# ---------------------------------------------------------------------------
@mcp.tool(
    name="meta_create_audience",
    annotations={
        "title": "Create Meta Custom Audience",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
async def meta_create_audience(params: CreateCustomAudienceInput) -> str:
    """Create a custom audience for targeting.

    Supported types:
    - WEBSITE: Retarget people who visited your site (requires Meta Pixel)
    - CUSTOM: Upload a customer list (emails/phones)
    - ENGAGEMENT: People who engaged with your Facebook/Instagram content

    Args:
        params (CreateCustomAudienceInput):
            - name: Audience name
            - subtype: WEBSITE, CUSTOM, ENGAGEMENT
            - description: Optional description
            - pixel_id: Required for WEBSITE subtype
            - retention_days: Days to retain visitors (1-180, for WEBSITE)

    Returns:
        str: JSON with audience_id.
    """
    try:
        post_data: Dict[str, Any] = {
            "name": params.name,
            "subtype": params.subtype,
        }
        if params.description:
            post_data["description"] = params.description

        if params.subtype == "WEBSITE":
            if not params.pixel_id:
                return "Error: pixel_id is required for WEBSITE subtype audiences. Provide your Meta Pixel ID."
            post_data["rule"] = json.dumps({
                "inclusions": {
                    "operator": "or",
                    "rules": [{"event_sources": [{"id": params.pixel_id, "type": "pixel"}], "retention_seconds": (params.retention_days or 30) * 86400, "filter": {"operator": "and", "filters": [{"field": "event", "operator": "=", "value": "PageView"}]}}]
                }
            })

        result = await _account_request("POST", "customaudiences", data=post_data)
        return json.dumps({
            "success": True,
            "audience_id": result.get("id"),
            "name": params.name,
            "subtype": params.subtype,
            "message": f"Audience created. ID: {result.get('id')}. Use this ID in meta_create_adset custom_audience_ids."
        }, indent=2)
    except Exception as e:
        return _handle_error(e)


# ---------------------------------------------------------------------------
# Tool: Get Account Info
# ---------------------------------------------------------------------------
@mcp.tool(
    name="meta_get_account_info",
    annotations={
        "title": "Get Meta Ad Account Info",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def meta_get_account_info(params: BaseModel) -> str:
    """Get information about the configured Meta ad account.

    Returns account name, currency, timezone, spend limit, balance,
    and account status. Use to verify credentials and check spending caps.

    Returns:
        str: JSON with account details.
    """
    try:
        _, account_id = _get_credentials()
        fields = "id,name,account_status,currency,timezone_name,spend_cap,amount_spent,balance,owner"
        data = await _graph_request("GET", account_id, params={"fields": fields})

        # Convert amounts from cents
        for field in ("spend_cap", "amount_spent", "balance"):
            if data.get(field):
                data[f"{field}_dollars"] = int(data[field]) / 100

        account_statuses = {1: "ACTIVE", 2: "DISABLED", 3: "UNSETTLED", 7: "PENDING_RISK_REVIEW", 9: "IN_GRACE_PERIOD", 100: "PENDING_CLOSURE", 101: "CLOSED", 201: "ANY_ACTIVE", 202: "ANY_CLOSED"}
        if "account_status" in data:
            data["account_status_label"] = account_statuses.get(data["account_status"], "UNKNOWN")

        return json.dumps(data, indent=2)
    except Exception as e:
        return _handle_error(e)


# ---------------------------------------------------------------------------
# Tool: List Ad Sets
# ---------------------------------------------------------------------------
@mcp.tool(
    name="meta_list_adsets",
    annotations={
        "title": "List Meta Ad Sets",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def meta_list_adsets(params: ListCampaignsInput) -> str:
    """List all ad sets in the ad account with targeting and budget info.

    Args:
        params (ListCampaignsInput):
            - status_filter: Filter by status
            - limit: Number of results (1-100)

    Returns:
        str: JSON array of ad sets with id, name, campaign_id, status, budget, targeting.
    """
    try:
        fields = "id,name,campaign_id,status,daily_budget,lifetime_budget,targeting,optimization_goal,billing_event,created_time"
        query_params: Dict[str, Any] = {"fields": fields, "limit": params.limit}
        if params.status_filter:
            query_params["effective_status"] = json.dumps([params.status_filter.value])

        data = await _account_request("GET", "adsets", params=query_params)
        adsets = data.get("data", [])

        for s in adsets:
            for budget_field in ("daily_budget", "lifetime_budget"):
                if s.get(budget_field):
                    s[f"{budget_field}_dollars"] = int(s[budget_field]) / 100

        return json.dumps({"adsets": adsets, "count": len(adsets)}, indent=2)
    except Exception as e:
        return _handle_error(e)


# ---------------------------------------------------------------------------
# Tool: Delete Object
# ---------------------------------------------------------------------------
@mcp.tool(
    name="meta_delete_object",
    annotations={
        "title": "Delete Meta Ad Object",
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def meta_delete_object(params: DeleteObjectInput) -> str:
    """Delete or archive a campaign, ad set, ad, creative, or audience.

    WARNING: Deletion is permanent for most objects. Use ARCHIVED status
    via meta_update_campaign instead when possible to preserve data.

    Args:
        params (DeleteObjectInput):
            - object_id: ID of the object to delete
            - object_type: campaign, adset, ad, creative, or audience

    Returns:
        str: Confirmation of deletion.
    """
    try:
        result = await _graph_request("DELETE", params.object_id)
        return json.dumps({
            "success": result.get("success", True),
            "deleted_id": params.object_id,
            "object_type": params.object_type,
            "message": f"{params.object_type.title()} {params.object_id} has been deleted."
        }, indent=2)
    except Exception as e:
        return _handle_error(e)


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    mcp.run()
