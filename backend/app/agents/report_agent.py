"""
Report Agent: Assembles all agent results into a structured report,
generates HTML via Jinja2, then converts to PDF via WeasyPrint.
"""
import os
import uuid
import structlog
from datetime import datetime
from typing import Dict, Any
from jinja2 import Environment, BaseLoader
from app.services.llm_client import phi3
from app.config import settings

log = structlog.get_logger()

SYSTEM = """You are an executive report writer. Write clear, professional executive summaries
and conclusions based on intelligence findings. Be concise and actionable."""

EXEC_SUMMARY_PROMPT = """
Based on the following intelligence findings about "{company}":

Research: {research}
Competitors discovered: {competitors}
Risk score: {risk_score}
Verified findings: {verified_count} claims verified

Write a 3-paragraph executive summary and a bulleted list of 5 key actionable conclusions.

Return JSON:
{{
  "executive_summary": "...",
  "key_conclusions": ["conclusion1", "conclusion2", "conclusion3", "conclusion4", "conclusion5"]
}}
"""

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Inter', sans-serif; color: #1a1a2e; font-size: 11pt; line-height: 1.6; }
  .cover { background: linear-gradient(135deg, #0f3460, #16213e); color: white;
           padding: 60px 50px; min-height: 280px; }
  .cover h1 { font-size: 32pt; font-weight: 700; margin-bottom: 8px; }
  .cover .subtitle { font-size: 14pt; opacity: 0.8; margin-bottom: 20px; }
  .cover .meta { font-size: 10pt; opacity: 0.6; }
  .section { padding: 30px 50px; border-bottom: 1px solid #eee; }
  .section h2 { font-size: 16pt; color: #0f3460; margin-bottom: 16px;
                border-left: 4px solid #e94560; padding-left: 12px; }
  .section h3 { font-size: 12pt; color: #16213e; margin: 14px 0 8px; font-weight: 600; }
  .badge { display: inline-block; padding: 2px 10px; border-radius: 12px;
           font-size: 9pt; font-weight: 600; margin: 2px; }
  .badge-high { background: #fee2e2; color: #dc2626; }
  .badge-medium { background: #fef3c7; color: #d97706; }
  .badge-low { background: #d1fae5; color: #059669; }
  .competitor-card { background: #f8fafc; border: 1px solid #e2e8f0;
                     border-radius: 8px; padding: 16px; margin: 10px 0; }
  .confidence-bar-bg { background: #e2e8f0; border-radius: 4px; height: 8px; margin: 4px 0; }
  .confidence-bar { background: #0f3460; border-radius: 4px; height: 8px; }
  .sources { font-size: 9pt; color: #64748b; }
  .sources a { color: #0f3460; }
  ul { padding-left: 20px; }
  li { margin: 4px 0; }
  table { width: 100%; border-collapse: collapse; margin: 12px 0; }
  th { background: #0f3460; color: white; padding: 8px 12px; text-align: left; font-size: 10pt; }
  td { padding: 8px 12px; border-bottom: 1px solid #e2e8f0; font-size: 10pt; }
  tr:nth-child(even) td { background: #f8fafc; }
  .footer { padding: 20px 50px; font-size: 9pt; color: #94a3b8; text-align: center; }
</style>
</head>
<body>

<div class="cover">
  <h1>{{ company_name }}</h1>
  <div class="subtitle">Competitive Intelligence Report</div>
  <div class="meta">Generated: {{ generated_at }} | Powered by Phi-3 (Local AI)</div>
</div>

<div class="section">
  <h2>Executive Summary</h2>
  <p>{{ exec_summary }}</p>
  {% if key_conclusions %}
  <h3>Key Conclusions</h3>
  <ul>{% for c in key_conclusions %}<li>{{ c }}</li>{% endfor %}</ul>
  {% endif %}
</div>

<div class="section">
  <h2>Company Profile</h2>
  {% if research %}
    {% if research.overview %}<p>{{ research.overview }}</p>{% endif %}
    {% if research.founders %}<h3>Leadership</h3><p>{{ research.founders }}</p>{% endif %}
    {% if research.funding %}<h3>Funding & Revenue</h3><p>{{ research.funding }}</p>{% endif %}
    {% if research.products %}
      <h3>Products & Services</h3>
      {% if research.products is iterable and research.products is not string %}
        <ul>{% for p in research.products %}<li>{{ p }}</li>{% endfor %}</ul>
      {% else %}
        <p>{{ research.products }}</p>
      {% endif %}
    {% endif %}
  {% endif %}
</div>

<div class="section">
  <h2>Competitor Landscape</h2>
  {% for name, analysis in competitors.items() %}
  <div class="competitor-card">
    <h3>{{ name }}</h3>
    {% if analysis.strengths %}
    <p><strong>Strengths:</strong></p>
    <ul>{% for s in analysis.strengths %}<li>{{ s }}</li>{% endfor %}</ul>
    {% endif %}
    {% if analysis.weaknesses %}
    <p><strong>Weaknesses:</strong></p>
    <ul>{% for w in analysis.weaknesses %}<li>{{ w }}</li>{% endfor %}</ul>
    {% endif %}
    {% if analysis.market_share_est %}<p><strong>Market Share Est.:</strong> {{ analysis.market_share_est }}</p>{% endif %}
    {% if analysis.funding_valuation %}<p><strong>Funding:</strong> {{ analysis.funding_valuation }}</p>{% endif %}
  </div>
  {% else %}
  <p>No competitor data available.</p>
  {% endfor %}
</div>

<div class="section">
  <h2>Risk Assessment</h2>
  {% if risks %}
  <table>
    <tr><th>Category</th><th>Severity</th><th>Summary</th></tr>
    {% for cat, risk in risks.items() if cat != 'overall_risk_score' and cat != 'social_sentiment' %}
    <tr>
      <td>{{ cat | replace('_', ' ') | title }}</td>
      <td><span class="badge badge-{{ risk.severity | default('low') }}">{{ risk.severity | default('N/A') | upper }}</span></td>
      <td>{{ risk.summary | default('') }}</td>
    </tr>
    {% endfor %}
  </table>
  {% if risks.overall_risk_score is defined %}
  <p><strong>Overall Risk Score:</strong> {{ risks.overall_risk_score }} / 10</p>
  {% endif %}
  {% endif %}
</div>

<div class="section">
  <h2>Verified Findings</h2>
  {% for finding in verified_findings[:10] %}
  <div style="margin: 10px 0; padding: 10px; background: #f8fafc; border-radius: 6px;">
    <p><strong>{{ finding.claim }}</strong></p>
    <div class="confidence-bar-bg">
      <div class="confidence-bar" style="width: {{ (finding.confidence_score * 100) | int }}%;"></div>
    </div>
    <p style="font-size:9pt; color:#64748b;">
      Confidence: {{ "%.0f" | format(finding.confidence_score * 100) }}% |
      <span class="badge badge-{{ 'low' if finding.supported == 'no' else ('medium' if finding.supported == 'partial' else 'low') }}">
        {{ finding.supported | upper }}
      </span>
    </p>
  </div>
  {% else %}
  <p>No verified findings available.</p>
  {% endfor %}
</div>

<div class="section sources">
  <h2>Sources & Citations</h2>
  <ul>
  {% for src in sources %}
    <li><a href="{{ src }}">{{ src }}</a></li>
  {% endfor %}
  </ul>
</div>

<div class="footer">
  Confidential — Generated by Competitor Intelligence Platform | Local Phi-3 AI | {{ generated_at }}
</div>

</body>
</html>
"""


class ReportAgent:
    name = "report_agent"

    def __init__(self):
        os.makedirs(settings.REPORTS_DIR, exist_ok=True)
        self.env = Environment(loader=BaseLoader())

    async def run(
        self,
        session_id: str,
        company: str,
        agent_results: Dict[str, Any],
    ) -> dict:
        log.info("report_agent_start", company=company)

        research_data = agent_results.get("research_agent", {}).get("data", {})
        discovery_data = agent_results.get("competitor_discovery_agent", {}).get("data", {})
        analysis_data = agent_results.get("competitor_analysis_agent", {}).get("data", {})
        risk_data = agent_results.get("risk_analysis_agent", {}).get("data", {})
        verification_data = agent_results.get("verification_agent", {}).get("data", {})

        # Generate executive summary with Phi-3
        exec_prompt = EXEC_SUMMARY_PROMPT.format(
            company=company,
            research=str(research_data)[:800],
            competitors=str(discovery_data.get("top_competitors", []))[:400],
            risk_score=risk_data.get("overall_risk_score", "N/A"),
            verified_count=len(verification_data.get("verified_findings", [])),
        )
        exec_result = await phi3.generate_json(exec_prompt, system=SYSTEM)

        # Collect all sources
        all_sources = []
        for r in agent_results.values():
            all_sources.extend(r.get("sources", []))
        all_sources = list(dict.fromkeys(all_sources))  # Deduplicate

        # Render HTML
        template = self.env.from_string(HTML_TEMPLATE)
        competitors_analysis = analysis_data.get("competitor_analyses", {})
        html_content = template.render(
            company_name=company,
            generated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
            exec_summary=exec_result.get("executive_summary", ""),
            key_conclusions=exec_result.get("key_conclusions", []),
            research=research_data,
            competitors=competitors_analysis,
            risks=risk_data,
            verified_findings=verification_data.get("verified_findings", []),
            sources=all_sources[:30],
        )

        # Generate PDF
        pdf_path = os.path.join(settings.REPORTS_DIR, f"report_{session_id}.pdf")
        html_path = os.path.join(settings.REPORTS_DIR, f"report_{session_id}.html")

        with open(html_path, "w") as f:
            f.write(html_content)

        try:
            from weasyprint import HTML
            HTML(string=html_content).write_pdf(pdf_path)
            log.info("pdf_generated", path=pdf_path)
        except Exception as e:
            log.warning("pdf_generation_failed", error=str(e))
            pdf_path = None

        return {
            "agent": self.name,
            "company": company,
            "data": {
                "executive_summary": exec_result.get("executive_summary", ""),
                "key_conclusions": exec_result.get("key_conclusions", []),
                "html_path": html_path,
                "pdf_path": pdf_path,
                "sources_count": len(all_sources),
            },
        }
