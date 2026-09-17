"""
Modular PDF Exporter Stub.
"""

from backend.document.model import DocumentModel
from backend.templates.schema import BookTemplate


class PdfExporter:
    def __init__(self, template: BookTemplate):
        self.template = template

    def export(self, doc_model: DocumentModel, output_path: str) -> str:
        raise NotImplementedError("Direct PDF export will be enabled via headless print renderer in future release.")
