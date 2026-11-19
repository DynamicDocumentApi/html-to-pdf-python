"""The same invoice without the SDK: one POST with requests, the PDF comes back in the response body.

    export DYNAMIC_DOCUMENT_API_KEY="dda_test_..."
    python render_requests.py
"""

import os
from pathlib import Path

import requests

from invoice_data import load_invoice

HERE = Path(__file__).parent
invoice = load_invoice()

response = requests.post(
    "https://api-eu.dynamicdocumentapi.com/v1/pdf/from-html",
    headers={"Authorization": f"Bearer {os.environ['DYNAMIC_DOCUMENT_API_KEY']}"},
    json={
        "html": (HERE / "invoice.html").read_text(encoding="utf-8"),
        "data": invoice,
        "pdf": {
            "paper": {"size": "Letter"},
            "margin": {"top": "16mm", "right": "16mm", "bottom": "20mm", "left": "16mm"},
            "footer": {"enabled": True, "right": "Page {{page}} of {{pages}}", "height": "12mm"},
        },
        "delivery": "binary",
    },
    timeout=130,  # a little above the longest sync wait, so a slow render answers 202 instead of timing out
)

if response.status_code != 200:
    raise SystemExit(f"Render failed: {response.status_code} {response.text}")

Path("invoice.pdf").write_bytes(response.content)
print(f"Wrote invoice.pdf ({response.headers.get('X-Pages')} pages)")
