"""
Modular EPUB Exporter Stub.
"""

from backend.document.model import DocumentModel
from backend.templates.schema import BookTemplate


class EpubExporter:
    def __init__(self, template: BookTemplate):
        self.template = template

    def export(self, doc_model: DocumentModel, output_path: str) -> str:
        raise NotImplementedError("EPUB reflowable export will be enabled in future release.")
