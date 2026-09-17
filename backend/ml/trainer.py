"""
Local Adaptive Learner.

Continuously improves classifier accuracy by training on user-reviewed corrections
stored in the local SQLite database, without ever sending manuscript data to the cloud.
"""

from __future__ import annotations
import json
import os
from typing import Any, Dict, List, Optional
import numpy as np

from backend.document.model import Block, BlockType
from backend.storage.database import Database
from .classifier import DocumentElementClassifier
from .features import FeatureExtractor


class LocalAdaptiveTrainer:
    """
    Manages local model adaptation from human corrections.
    """

    def __init__(self, db: Database, classifier: DocumentElementClassifier):
        self.db = db
        self.classifier = classifier
        self.feature_extractor = FeatureExtractor()

    def train_from_corrections(
        self,
        output_model_path: Optional[str] = None,
        min_samples: int = 5,
    ) -> Dict[str, Any]:
        """
        Gathers verified user corrections from SQLite and refits the Random Forest.
        """
        corrections = self.db.get_corrections()
        if len(corrections) < min_samples:
            return {
                "status": "SKIPPED",
                "message": f"Need at least {min_samples} user corrections to adapt (currently {len(corrections)}).",
                "samples_count": len(corrections),
            }

        X_train: List[List[float]] = []
        y_train: List[str] = []

        for c in corrections:
            corrected_type = c["corrected_type"]
            features = json.loads(c.get("features_json") or "{}")

            if features and len(features) == len(FeatureExtractor.FEATURE_NAMES):
                vec = [features.get(n, 0.0) for n in FeatureExtractor.FEATURE_NAMES]
            else:
                # Re-synthesize feature vector from text if features_json missing
                synthetic_block = Block(
                    text=c.get("original_text", ""),
                    block_type=BlockType(corrected_type) if corrected_type in BlockType._value2member_map_ else BlockType.BODY,
                )
                vec = list(self.feature_extractor.extract_vector(synthetic_block))

            # Weight user corrections with high sample multiplicity
            for _ in range(5):
                jitter = [v + np.random.normal(0, 0.01) if v != 0.0 else 0.0 for v in vec]
                X_train.append(jitter)
                y_train.append(corrected_type)

        # Include base synthetic exemplars to prevent catastrophic forgetting
        for label, count in [
            (BlockType.CHAPTER_TITLE.value, 20),
            (BlockType.HEADING_1.value, 20),
            (BlockType.HEADING_2.value, 20),
            (BlockType.BODY.value, 40),
            (BlockType.QUOTE.value, 20),
            (BlockType.CAPTION.value, 20),
        ]:
            if label not in y_train:
                base = [0.0] * len(FeatureExtractor.FEATURE_NAMES)
                for _ in range(count):
                    X_train.append(base)
                    y_train.append(label)

        X = np.array(X_train, dtype=np.float32)
        y = np.array(y_train)

        self.classifier.classifier.fit(X, y)
        self.classifier.is_trained = True

        save_dest = output_model_path or self.classifier.model_path
        if save_dest:
            self.classifier.save(save_dest)

        return {
            "status": "SUCCESS",
            "message": f"Model successfully retrained on {len(corrections)} user corrections.",
            "samples_count": len(corrections),
            "classes": list(np.unique(y)),
        }
