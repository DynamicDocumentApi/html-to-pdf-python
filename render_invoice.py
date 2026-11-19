"""Renders invoice.html with the data from invoice.json into invoice.pdf.

    pip install -r requirements.txt
    export DYNAMIC_DOCUMENT_API_KEY="dda_test_..."
    python render_invoice.py
"""

from pathlib import Path

from dynamic_document_api import DynamicDocumentApi

from invoice_data import load_invoice

HERE = Path(__file__).parent

dda = DynamicDocumentApi()  # reads DYNAMIC_DOCUMENT_API_KEY
invoice = load_invoice()

render = dda.pdf.from_html(
    html=(HERE / "invoice.html").read_text(encoding="utf-8"),
    data=invoice,
    pdf={
        "paper": {"size": "Letter"},
        "margin": {"top": "16mm", "right": "16mm", "bottom": "20mm", "left": "16mm"},
        "footer": {
            "enabled": True,
            "left": "{{ seller.name }} · Invoice {{ number }}",
            "right": "Page {{page}} of {{pages}}",
            "height": "12mm",
        },
        "metadata": {"title": f"Invoice {invoice['number']}", "author": invoice["seller"]["name"]},
    },
    filename="invoice-{{ data.number }}.pdf",
)

# A render that takes longer than the sync wait answers 202 and finishes in the background.
if render["status"] != "succeeded":
    render = dda.wait_for_render(render["id"])

file = render["files"][0]
Path(file["filename"]).write_bytes(dda.files.download(file))
print(f"Wrote {file['filename']} ({file['pages']} pages)")
