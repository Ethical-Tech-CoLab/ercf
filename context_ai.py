"""
AI-powered country context analysis using Claude API.
Falls back to static data when ANTHROPIC_API_KEY is not set.
"""
import os, json
from world_risk import get_risk_by_iso3, WORLD_RISK

try:
    import anthropic
    _client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
    _AI_AVAILABLE = bool(os.environ.get("ANTHROPIC_API_KEY"))
except Exception:
    _client = None
    _AI_AVAILABLE = False


_SYSTEM = """You are a senior humanitarian analyst with expertise in IHL, ACAPS, UNHCR operations,
and the Evacuation Risk Classification Framework (ERCF). When asked about a country context,
provide a concise, actionable analysis for evacuation planning. Always respond with valid JSON only —
no markdown fences, no extra text. Populate every key exactly as specified."""

_PROMPT_TPL = """Analyze the humanitarian evacuation context for: {country} (ISO: {iso3})
Current ACAPS/INFORM crisis level: {level}/4 ({level_label})
Crisis description: {crisis}

Return a JSON object with these exact keys:
{{
  "summary": "2-sentence humanitarian situation summary",
  "population_at_risk": integer (estimated civilians at direct risk),
  "conflict_type": "IHL classification (IAC / NIAC / Complex Emergency / etc.)",
  "humanitarian_access": "current access level description (1-2 sentences)",
  "access_score": integer 0-5 (0=open, 5=extreme constraints),
  "exit_routes": [list of 3-5 viable evacuation routes with direction and status],
  "neighboring_safe_zones": [list of 2-4 safer neighboring areas with brief note],
  "humanitarian_actors": [list of key UN agencies, ICRC, major NGOs present],
  "ihl_framework": "applicable IHL instruments and key protections",
  "main_obstacles": [list of 3-5 main obstacles to successful evacuation],
  "ercf_level": integer 0-4 (recommended ERCF risk level),
  "ercf_justification": "1-2 sentence justification for the ERCF level",
  "dimension_scores": {{
    "d1_kinetic": float 1.0-5.0,
    "d2_vulnerability": float 1.0-5.0,  (D2 = mobility constraints: 1=fully mobile population, 5=mass casualty / complete mobility collapse — drives medical vehicle allocation)
    "d3_political": float 1.0-5.0,  (D3 = authorization: 1=full consent from all armed parties, 5=active refusal / no valid authorization — same direction as the other dimensions, higher is worse)
    "d4_logistics": float 1.0-5.0,
    "d5_destination": float 1.0-5.0,
    "d6_urgency": float 1.0-5.0,
    "d7_information": float 1.0-5.0
  }},
  "sphere_considerations": "key SPHERE standard considerations for this context",
  "last_updated": "June 2026"
}}"""


def _level_label(level: int) -> str:
    return ["Baseline","Low Risk","Moderate Risk","High Risk","Critical / Emergency"][level]


def _fallback_context(iso3: str) -> dict:
    """Build a structured response from static data when AI is unavailable."""
    d = get_risk_by_iso3(iso3)
    lvl = d.get("level", 0)
    # Map ERCF level to plausible dimension scores
    dim_map = {
        0: dict(d1_kinetic=1.0,d2_vulnerability=1.5,d3_political=3.0,d4_logistics=2.0,d5_destination=2.0,d6_urgency=1.0,d7_information=1.5),
        1: dict(d1_kinetic=2.0,d2_vulnerability=2.5,d3_political=3.5,d4_logistics=2.5,d5_destination=2.5,d6_urgency=2.0,d7_information=2.0),
        2: dict(d1_kinetic=3.0,d2_vulnerability=3.0,d3_political=3.5,d4_logistics=3.0,d5_destination=2.5,d6_urgency=3.0,d7_information=2.5),
        3: dict(d1_kinetic=4.0,d2_vulnerability=3.5,d3_political=3.5,d4_logistics=3.5,d5_destination=3.0,d6_urgency=4.0,d7_information=3.0),
        4: dict(d1_kinetic=5.0,d2_vulnerability=4.0,d3_political=4.5,d4_logistics=4.0,d5_destination=3.0,d6_urgency=4.5,d7_information=4.0),
    }
    return {
        "summary": f"{d['name']}: {d['crisis']}",
        "population_at_risk": d.get("pop_at_risk", 0),
        "conflict_type": d.get("conflict_type", "Unknown"),
        "humanitarian_access": d.get("access_label", "Unknown"),
        "access_score": d.get("access", 0),
        "exit_routes": d.get("exit_routes", []),
        "neighboring_safe_zones": d.get("exit_routes", [])[:3],
        "humanitarian_actors": d.get("actors", []),
        "ihl_framework": "GC IV + AP I/II applicable" if lvl >= 2 else "IHL monitoring",
        "main_obstacles": ["Data from static ACAPS dataset — enable AI for detailed analysis"],
        "ercf_level": lvl,
        "ercf_justification": f"ACAPS INFORM score {d.get('inform_score', 0):.1f}/5 maps to ERCF Level {lvl}.",
        "dimension_scores": dim_map[lvl],
        "sphere_considerations": "Standard SPHERE Handbook 2018 applies.",
        "last_updated": d.get("source", "ACAPS Dec 2025"),
        "_source": "static"
    }


def analyze_country(iso3: str, country_name: str, allow_ai: bool = True) -> dict:
    """Return AI-powered (or fallback) evacuation context for a country.

    allow_ai=False forces the free static analysis — used when the caller has
    exhausted the paid-API budget (see security.llm_budget_ok).
    """
    d = get_risk_by_iso3(iso3)
    level = d.get("level", 0)

    if not allow_ai:
        ctx = _fallback_context(iso3)
        ctx["_ai_note"] = "AI analysis quota reached — showing static ACAPS analysis."
        return ctx

    if not _AI_AVAILABLE:
        ctx = _fallback_context(iso3)
        ctx["_ai_note"] = "Set ANTHROPIC_API_KEY env variable for AI-powered analysis."
        return ctx

    prompt = _PROMPT_TPL.format(
        country=country_name or d["name"],
        iso3=iso3,
        level=level,
        level_label=_level_label(level),
        crisis=d.get("crisis", "Unknown"),
    )

    try:
        resp = _client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1200,
            system=_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
        text = resp.content[0].text.strip()
        result = json.loads(text)
        result["_source"] = "claude-haiku-4-5"
        return result
    except Exception as e:
        ctx = _fallback_context(iso3)
        ctx["_ai_error"] = str(e)
        return ctx
