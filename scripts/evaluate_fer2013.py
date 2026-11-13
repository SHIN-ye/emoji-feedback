"""Evaluate DeepFace's emotion classifier on the FER2013 cropped test faces."""
import argparse
import hashlib
import json
import os
from importlib.metadata import version
from pathlib import Path

import cv2
import numpy as np
import pyarrow.parquet as pq


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('parquet', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--threshold', type=float, default=0.6)
    args = parser.parse_args()
    if not 0 <= args.threshold <= 1:
        parser.error('Threshold must be in [0, 1]')

    cache = Path('artifacts/ai-model-cache').resolve()
    cache.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault('DEEPFACE_HOME', str(cache))
    from deepface import DeepFace
    from deepface.models.demography.Emotion import labels

    model = DeepFace.build_model('Emotion', task='facial_attribute').model
    dataset = pq.ParquetFile(args.parquet)
    metadata = json.loads(dataset.schema_arrow.metadata[b'huggingface'])
    dataset_labels = metadata['info']['features']['labels']['names']
    label_map = np.array([labels.index(label) for label in dataset_labels])
    matrix = np.zeros((len(labels), len(labels)), dtype=int)
    accepted = correct_accepted = 0
    for batch in dataset.iter_batches(batch_size=64, columns=['img_bytes', 'labels']):
        faces = []
        for raw in batch.column(0).to_pylist():
            face = cv2.imdecode(np.frombuffer(raw, dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
            if face is None:
                raise ValueError('Dataset contains an invalid image')
            faces.append(cv2.resize(face, (48, 48)))
        inputs = np.asarray(faces, dtype=np.float32)[..., None] / 255.0
        scores = model(inputs, training=False).numpy()
        predicted = scores.argmax(axis=1)
        expected = label_map[batch.column(1).to_numpy()]
        np.add.at(matrix, (expected, predicted), 1)
        keep = scores.max(axis=1) >= args.threshold
        accepted += int(keep.sum())
        correct_accepted += int((keep & (predicted == expected)).sum())
    total = int(matrix.sum())
    correct = int(matrix.trace())
    support = matrix.sum(axis=1)
    recalls = matrix.diagonal() / support
    with args.parquet.open('rb') as f:
        checksum = hashlib.file_digest(f, 'sha256').hexdigest()
    result = {
        'dataset': 'Jeneral/fer-2013, test split', 'dataset_sha256': checksum,
        'deepface': version('deepface'), 'labels': labels, 'samples': total,
        'correct': correct, 'accuracy': correct / total, 'macro_recall': float(recalls.mean()),
        'per_class': {label: {'samples': int(support[i]), 'recall': float(recalls[i])}
                      for i, label in enumerate(labels)},
        'threshold': args.threshold, 'accepted': accepted, 'correct_accepted': correct_accepted,
        'coverage': accepted / total, 'accepted_accuracy': correct_accepted / accepted if accepted else None,
        'confusion_matrix_rows_true_columns_predicted': matrix.tolist(),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({key: result[key] for key in ('samples', 'accuracy', 'macro_recall', 'coverage', 'accepted_accuracy')}))


if __name__ == '__main__':
    main()
