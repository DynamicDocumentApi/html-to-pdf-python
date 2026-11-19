"""A FastAPI endpoint that returns the invoice as a PDF.

    export DYNAMIC_DOCUMENT_API_KEY="dda_test_..."
    uvicorn app:app --reload
    open http://127.0.0.1:8000/invoices/INV-2026-0418.pdf
"""

from pathlib import Path

from dynamic_document_api import AsyncDynamicDocumentApi, DynamicDocumentApiError
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response

from invoice_data import load_invoice

HERE = Path(__file__).parent
TEMPLATE = (HERE / "invoice.html").read_text(encoding="utf-8")

app = FastAPI()
dda = AsyncDynamicDocumentApi()  # one client for the whole app: it reuses connections


@app.get("/invoices/{number}.pdf")
async def invoice_pdf(number: str) -> Response:
    invoice = load_invoice()  # in a real app: load the invoice from your database
    if number != invoice["number"]:
        raise HTTPException(status_code=404, detail="Invoice not found")

    try:
        pdf = await dda.renders.create_binary(
            input={"type": "html", "html": TEMPLATE},
            data=invoice,
            output={
                "format": "pdf",
                "pdf": {
                    "paper": {"size": "Letter"},
                    "margin": {"top": "16mm", "right": "16mm", "bottom": "20mm", "left": "16mm"},
                    "footer": {"enabled": True, "right": "Page {{page}} of {{pages}}", "height": "12mm"},
                },
            },
        )
    except DynamicDocumentApiError as error:
        raise HTTPException(status_code=502, detail=f"PDF rendering failed ({error.code})") from error

    return Response(
        content=pdf.content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="invoice-{number}.pdf"'},
    )
