"""For projects that already fill their templates with jinja2: send the finished HTML and turn templating off.

    export DYNAMIC_DOCUMENT_API_KEY="dda_test_..."
    python render_local_jinja.py
"""

from pathlib import Path

from dynamic_document_api import DynamicDocumentApi
from jinja2 import Environment, FileSystemLoader, select_autoescape

from invoice_data import load_invoice

HERE = Path(__file__).parent

env = Environment(loader=FileSystemLoader(HERE), autoescape=select_autoescape(["html"]))
html = env.get_template("invoice.html").render(**load_invoice())

dda = DynamicDocumentApi()
render = dda.pdf.from_html(
    html=html,
    templating=False,  # the HTML is final: {{ }} in it is printed as text, not filled in again
    pdf={
        "paper": {"size": "Letter"},
        "margin": {"top": "16mm", "right": "16mm", "bottom": "20mm", "left": "16mm"},
        "footer": {"enabled": True, "right": "Page {{page}} of {{pages}}", "height": "12mm"},
    },
)
if render["status"] != "succeeded":
    render = dda.wait_for_render(render["id"])

Path("invoice-local.pdf").write_bytes(dda.files.download(render["files"][0]))
print("Wrote invoice-local.pdf")
