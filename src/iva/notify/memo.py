from jinja2 import Template
from ..models.recon import TruthCard

TPL = Template("""
<h3>Iva Truth Meter — {{ company }}</h3>
<p><b>URL:</b> {{ url }}<br/><b>Summary:</b> {{ summary }}<br/><b>Confidence:</b> {{ conf }}%</p>
{% for d in discrepancies %}
<div>
  <b>{{ d.type }}</b> ({{ d.severity }}, {{ (d.confidence*100)|round }}%):
  {% if d.claim_text %}<div><b>Claim:</b> "{{ d.claim_text }}"</div>{% endif %}
  <div>Why: {{ d.why_it_matters }}</div>
  <div>Expected evidence: {{ d.expected_evidence }}</div>
  <div>Findings:
    <ul>
    {% for f in d.findings %}
      <li>{{ f.key }} = {{ f.value }} ({{ f.status }}) — {{ f.citations[0].source if f.citations }}</li>
    {% endfor %}
    </ul>
  </div>
</div>
{% endfor %}
<small>Advisory only — not legal advice.</small>
""")

def render_html(card: TruthCard) -> str:
    return TPL.render(
        company=card.company,
        url=card.url,
        summary=card.severity_summary,
        conf=round(card.overall_confidence*100),
        discrepancies=card.discrepancies
    )
