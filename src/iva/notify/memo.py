from jinja2 import Template

from ..models.recon import TruthCard

TPL = Template(
    """
<h3>Iva Truth Meter — {{ company }}</h3>
<p><b>URL:</b> {{ url }}<br/><b>Summary:</b> {{ summary }}<br/><b>Confidence:</b> {{ conf }}%<br/><b>Generated:</b> {{ generated }}</p>
{% for d in discrepancies %}
<div>
  <b>{{ d.type }}</b> ({{ d.severity }}, {{ (d.confidence*100)|round }}%):
  {% set claim_texts = d.related_claim_texts if d.related_claim_texts else ([d.claim_text] if d.claim_text else []) %}
  {% if claim_texts %}
  <div><b>Claims:</b>
    <ul>{% for text in claim_texts %}<li>{{ text }}</li>{% endfor %}</ul>
  </div>
  {% endif %}
  {% if d.related_claims and d.related_claims|length > 1 %}<div><b>Related claim IDs:</b> {{ d.related_claims|join(', ') }}</div>{% endif %}
  <div>Why: {{ d.why_it_matters }}</div>
  <div>Expected evidence: {{ d.expected_evidence }}</div>
  <div>Verdict: {{ d.explanation.verdict }} ({{ (d.explanation.confidence*100)|round }}%)</div>
  {% if d.explanation.notes %}
  <div>Notes:
    <ul>{% for note in d.explanation.notes.split('\n') %}<li>{{ note }}</li>{% endfor %}</ul>
  </div>
  {% endif %}
  {% if d.explanation.follow_up_actions %}
  <div>Follow-ups:
    <ul>{% for action in d.explanation.follow_up_actions %}<li>{{ action }}</li>{% endfor %}</ul>
  </div>
  {% endif %}
  {% if d.explanation.supporting_evidence %}
  <div>Evidence:
    <ul>{% for e in d.explanation.supporting_evidence %}<li>{{ e.adapter }} • {{ e.finding_key }} — {{ e.summary }}{% if e.citation_urls %} (<a href="{{ e.citation_urls[0] }}" target="_blank" rel="noopener">Source</a>){% endif %}</li>{% endfor %}</ul>
  </div>
  {% endif %}
  {% if d.provenance %}
  <div>Provenance:
    <ul>{% for p in d.provenance %}<li>{{ p.adapter }} @ {{ p.observed_at }}{% if p.snippet %} — {{ p.snippet }}{% endif %}{% if p.source_urls %} (<a href="{{ p.source_urls[0] }}" target="_blank" rel="noopener">Source</a>){% endif %}</li>{% endfor %}</ul>
  </div>
  {% endif %}
</div>
{% endfor %}
<small>Advisory only — not legal advice.</small>
"""
)


def render_html(card: TruthCard) -> str:
    return TPL.render(
        company=card.company,
        url=card.url,
        summary=card.severity_summary,
        conf=round(card.overall_confidence * 100),
        generated=card.generated_at,
        discrepancies=card.discrepancies,
    )
