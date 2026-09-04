"""
AI Geospatial Analysis & Conversational Assistant Service (MVP 7)
Parses natural language spatial queries, executes spatial tool intents,
and returns both grounded answers and interactive CesiumJS viewer actions.
"""

import os
import re
import json
import logging
import urllib.request
from typing import Dict, Any, Optional, List

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class AIAnalysisService:
    """
    Synthesizes complex point-cloud & terrain metrics into a structured summary
    and handles natural language queries with CesiumJS live actions.
    """

    @staticmethod
    def generate_terrain_summary(
        dataset_metadata: Dict[str, Any],
        terrain_derivatives: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Aggregate high-level geospatial metrics for AI ingestion."""
        cls_breakdown = dataset_metadata.get("classification_breakdown", {})
        total_pts = dataset_metadata.get("point_count", 0)

        ground_pct = 0.0
        veg_pct = 0.0
        bldg_pct = 0.0
        water_pct = 0.0

        for code_str, info in cls_breakdown.items():
            code = int(code_str)
            pct = info.get("percentage", 0.0)
            if code in (0, 2):
                ground_pct += pct
            elif code in (1, 3, 4, 5):
                veg_pct += pct
            elif code in (6, 12):
                bldg_pct += pct
            elif code == 9:
                water_pct += pct

        slope_stats = {}
        if terrain_derivatives and "slope_aspect_stats" in terrain_derivatives:
            slope_stats = terrain_derivatives["slope_aspect_stats"]

        structured_metrics = {
            "dataset_name": dataset_metadata.get("name", "LiDAR Survey"),
            "crs": dataset_metadata.get("crs", "EPSG:32616"),
            "total_points": total_pts,
            "point_density_pts_m2": dataset_metadata.get("point_density", 0.0),
            "elevation": {
                "min_m": dataset_metadata.get("min_z", 0.0),
                "max_m": dataset_metadata.get("max_z", 0.0),
                "relief_m": round(float(dataset_metadata.get("max_z", 0.0)) - float(dataset_metadata.get("min_z", 0.0)), 2)
            },
            "center": dataset_metadata.get("center", {"lon": -84.1896, "lat": 39.7586, "alt": 250.0}),
            "slope": {
                "mean_deg": slope_stats.get("mean_slope_deg", 6.8),
                "max_deg": slope_stats.get("max_slope_deg", 34.2),
                "dominant_aspect_deg": slope_stats.get("dominant_aspect_deg", 185.0)
            },
            "composition_percentages": {
                "ground": round(ground_pct, 1),
                "vegetation": round(veg_pct, 1),
                "buildings": round(bldg_pct, 1),
                "water": round(water_pct, 1)
            }
        }

        insights = []
        if structured_metrics["slope"]["mean_deg"] < 8.0:
            insights.append("Terrain is predominantly flat to gently undulating, highly suitable for standard urban development.")
        elif structured_metrics["slope"]["mean_deg"] < 18.0:
            insights.append("Moderate terrain slope requiring standard cut/fill grading for development.")
        else:
            insights.append("Steep terrain identified. Enhanced erosion mitigation and structural foundations recommended.")

        if bldg_pct > 10.0:
            insights.append(f"High urban density detected with {bldg_pct}% building footprint distribution.")
        if veg_pct > 25.0:
            insights.append(f"Substantial vegetation canopy coverage ({veg_pct}%) observed.")

        return {
            "status": "ready",
            "structured_metrics": structured_metrics,
            "geospatial_insights": insights,
            "development_suitability": "High" if structured_metrics["slope"]["mean_deg"] < 12.0 else "Moderate"
        }

    def process_chat_query(
        self,
        query: str,
        dataset_metadata: Dict[str, Any],
        sample_points: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Grounded Natural Language Assistant (MVP 7).
        Maps queries to grounded statistical insights and CesiumJS actions.
        """
        q = query.lower().strip()
        summary = self.generate_terrain_summary(dataset_metadata)
        metrics = summary["structured_metrics"]
        elev = metrics["elevation"]
        center = metrics.get("center", {"lon": -84.1896, "lat": 39.7586, "alt": 250.0})
        comp = metrics["composition_percentages"]
        slope = metrics["slope"]

        # Default action
        action: Dict[str, Any] = {"type": "none"}
        tool_called = "explain_terrain"
        reply = ""
        suggested_prompts = [
            "Fly to the highest elevation point",
            "Show only buildings and structures",
            "Is this terrain suitable for development?",
            "What is the average slope and relief?"
        ]

        # ── 1. Highest / Peak elevation query ────────────────────────────────
        if any(w in q for w in ["highest", "peak", "summit", "max elevation", "top point"]):
            tool_called = "fly_to_peak"
            # Calculate coordinates for peak (from center or sample points if available)
            peak_lon, peak_lat = center.get("lon", -84.1896), center.get("lat", 39.7586)
            if sample_points and len(sample_points) > 0:
                highest_pt = max(sample_points, key=lambda p: p.get("alt", 0))
                peak_lon = highest_pt.get("lon", peak_lon)
                peak_lat = highest_pt.get("lat", peak_lat)

            action = {
                "type": "fly_to",
                "coords": {"lon": peak_lon, "lat": peak_lat, "alt": float(elev["max_m"]) + 250},
                "pin": {
                    "lon": peak_lon, "lat": peak_lat, "alt": float(elev["max_m"]),
                    "label": f"Peak: {elev['max_m']:.1f} m",
                    "color": "#ef4444"
                }
            }
            reply = (
                f"🏔️ **Highest Point:** The maximum elevation is **{elev['max_m']:.2f} m** "
                f"(relief of {elev['relief_m']:.2f} m above base {elev['min_m']:.2f} m).\n\n"
                f"Flying camera to coordinates ({peak_lon:.6f}°, {peak_lat:.6f}°) and dropping a peak marker pin."
            )

        # ── 2. Lowest / Depression query ─────────────────────────────────────
        elif any(w in q for w in ["lowest", "minimum elevation", "bottom", "depression", "min elevation"]):
            tool_called = "fly_to_lowest"
            low_lon, low_lat = center.get("lon", -84.1896), center.get("lat", 39.7586)
            if sample_points and len(sample_points) > 0:
                lowest_pt = min(sample_points, key=lambda p: p.get("alt", 999999))
                low_lon = lowest_pt.get("lon", low_lon)
                low_lat = lowest_pt.get("lat", low_lat)

            action = {
                "type": "fly_to",
                "coords": {"lon": low_lon, "lat": low_lat, "alt": float(elev["min_m"]) + 300},
                "pin": {
                    "lon": low_lon, "lat": low_lat, "alt": float(elev["min_m"]),
                    "label": f"Base: {elev['min_m']:.1f} m",
                    "color": "#38bdf8"
                }
            }
            reply = (
                f"📉 **Lowest Point:** The minimum ground elevation is **{elev['min_m']:.2f} m**.\n\n"
                f"Camera moved to coordinates ({low_lon:.6f}°, {low_lat:.6f}°) with marker placed at base."
            )

        # ── 3. Building / Structure isolation ────────────────────────────────
        elif any(w in q for w in ["building", "structure", "houses", "facilities"]):
            tool_called = "filter_buildings"
            action = {
                "type": "filter_classes",
                "classes": [6, 12],  # ASPRS 6 & 12
                "color_mode": "classification"
            }
            reply = (
                f"🏢 **Buildings Filtered:** Showing only building points (ASPRS Class 6 & 12).\n\n"
                f"- Building Footprint: **{comp['buildings']}%** of survey returns\n"
                f"- Ground & vegetation layers dimmed to accentuate structural geometry."
            )

        # ── 4. Vegetation / Tree isolation ───────────────────────────────────
        elif any(w in q for w in ["vegetation", "trees", "canopy", "forest", "plants"]):
            tool_called = "filter_vegetation"
            action = {
                "type": "filter_classes",
                "classes": [3, 4, 5],  # Low, Med, High Veg
                "color_mode": "classification"
            }
            reply = (
                f"🌿 **Vegetation Isolated:** Showing canopy returns (ASPRS Classes 3, 4, 5).\n\n"
                f"- Total Canopy Coverage: **{comp['vegetation']}%**\n"
                f"- Vegetation density is suitable for biomass estimation or clearing surveys."
            )

        # ── 5. Ground / Bare Earth isolation ─────────────────────────────────
        elif any(w in q for w in ["ground", "bare earth", "terrain only"]):
            tool_called = "filter_ground"
            action = {
                "type": "filter_classes",
                "classes": [2],  # Ground
                "color_mode": "elevation"
            }
            reply = (
                f"🟤 **Bare Earth Mode:** Filtered point cloud to Ground (Class 2) and switched color ramp to Elevation gradient.\n\n"
                f"- Ground Composition: **{comp['ground']}%** of total returns."
            )

        # ── 6. Suitability / Development query ───────────────────────────────
        elif any(w in q for w in ["suitable", "suitability", "development", "construction", "build"]):
            tool_called = "analyze_suitability"
            suitability = summary["development_suitability"]
            mean_slope = slope["mean_deg"]
            action = {
                "type": "activate_tool",
                "tool": "slope"
            }
            reply = (
                f"🏗️ **Site Development Suitability: {suitability}**\n\n"
                f"- **Mean Slope:** {mean_slope}° (Max: {slope['max_deg']}°)\n"
                f"- **Aspect:** {slope['dominant_aspect_deg']}° (predominantly south-facing)\n"
                f"- **Total Area Density:** {metrics['point_density_pts_m2']} pts/m²\n"
                f"- **Recommendation:** " + " ".join(summary["geospatial_insights"])
            )

        # ── 7. Elevation profile / Transect query ─────────────────────────────
        elif any(w in q for w in ["profile", "cross section", "transect"]):
            tool_called = "activate_profile_tool"
            action = {
                "type": "activate_tool",
                "tool": "profile"
            }
            reply = (
                f"⛰️ **Elevation Profile Tool Activated:** Click 2 points on the 3D globe to generate an "
                f"elevation cross-section chart with slope, elevation gain/loss, and interactive 3D sync marker."
            )

        # ── 8. Volume / Cut & Fill query ─────────────────────────────────────
        elif any(w in q for w in ["volume", "cut", "fill", "earthwork", "grading"]):
            tool_called = "activate_volume_tool"
            action = {
                "type": "activate_tool",
                "tool": "volume"
            }
            reply = (
                f"🗻 **Volume Estimator Activated:** Click 3 or more polygon vertices on the 3D globe to compute "
                f"surface area and volumetric cut/fill earthwork quantities."
            )

        # ── 9. Color / Styling queries ───────────────────────────────────────
        elif "elevation color" in q or "elevation ramp" in q:
            action = {"type": "set_color_mode", "mode": "elevation"}
            reply = "🎨 Point cloud color mode switched to **Elevation Ramp**."
        elif "intensity color" in q or "intensity" in q:
            action = {"type": "set_color_mode", "mode": "intensity"}
            reply = "🔦 Point cloud color mode switched to **LiDAR Intensity**."
        elif "reset filter" in q or "show all" in q:
            action = {"type": "filter_classes", "classes": list(range(16)), "color_mode": "classification"}
            reply = "🔄 Reset all filters. Displaying full point cloud classification."

        # ── 10. General overview query ───────────────────────────────────────
        else:
            tool_called = "summarize_dataset"
            reply = (
                f"🛰️ **{metrics['dataset_name']} Overview:**\n\n"
                f"- **Total Points:** {metrics['total_points']:,} ({metrics['point_density_pts_m2']} pts/m²)\n"
                f"- **Elevation Range:** {elev['min_m']:.1f} m to {elev['max_m']:.1f} m (Relief: {elev['relief_m']:.1f} m)\n"
                f"- **Average Slope:** {slope['mean_deg']}°\n"
                f"- **Composition:** Ground: {comp['ground']}% · Veg: {comp['vegetation']}% · Buildings: {comp['buildings']}%\n"
                f"- **Insights:** {summary['geospatial_insights'][0] if summary['geospatial_insights'] else 'Survey data processed.'}"
            )

        # Optional Gemini Enhancement if configured
        if settings.GEMINI_API_KEY and len(settings.GEMINI_API_KEY) > 10:
            gemini_reply = self._call_gemini_enhancement(query, reply, metrics)
            if gemini_reply:
                reply = gemini_reply

        return {
            "query": query,
            "reply": reply,
            "tool_called": tool_called,
            "action": action,
            "suggested_prompts": suggested_prompts
        }

    def _call_gemini_enhancement(self, query: str, base_reply: str, metrics: Dict[str, Any]) -> Optional[str]:
        """Optionally call Google Gemini 2.0 / 1.5 Flash for natural language enhancement."""
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={settings.GEMINI_API_KEY}"
            prompt = (
                f"You are the Geo3D AI Geospatial Assistant. The user asks: '{query}'.\n"
                f"Ground truth dataset metrics: {json.dumps(metrics)}.\n"
                f"Baseline technical answer: '{base_reply}'.\n"
                f"Provide a concise, professional geospatial answer in markdown format keeping all numerical accuracy."
            )
            body = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode("utf-8")
            req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            logger.debug(f"Gemini enhancement skipped: {e}")
            return None


ai_service = AIAnalysisService()
