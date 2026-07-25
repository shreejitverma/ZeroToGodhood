"""Listing 147.1 - preprocessing and pipelines: scaling, and preventing data leakage.

Most models need PREPROCESSED features. A key step is SCALING: many algorithms (KNN,
SVM, anything distance- or gradient-based) are sensitive to feature magnitude, so a
feature 1000x larger than another dominates and swamps the rest. StandardScaler
transforms each feature to mean 0, standard deviation 1, putting them on equal footing.
The critical discipline (Chapter 65): preprocessing must be fit on the TRAINING data
only, or test information LEAKS into training. A scikit-learn PIPELINE chains
preprocessing and the model into one estimator that, when you fit it on the training
split, fits every step on train only, no leakage. This listing shows scaling and a
pipeline, deterministically.
"""

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


def main() -> None:
    print("--- StandardScaler: each feature to mean 0, std 1 ---")
    X = np.array([[1.0, 1000.0], [2.0, 2000.0], [3.0, 3000.0], [4.0, 4000.0]])
    scaler = StandardScaler().fit(X)
    scaled = scaler.transform(X)
    print(f"  original feature-1 range : {X[:, 1].min()} .. {X[:, 1].max()}")
    print(f"  scaled means (per feature, ~0)   : {[round(float(m), 6) for m in scaled.mean(axis=0)]}")
    print(f"  scaled stds  (per feature, ~1)   : {[round(float(s), 6) for s in scaled.std(axis=0)]}")
    print(f"  both features now comparable scale : {round(float(scaled[:, 0].std()), 6) == round(float(scaled[:, 1].std()), 6)}")

    print("--- a Pipeline chains preprocessing + model as ONE estimator ---")
    pipe = make_pipeline(StandardScaler(), LogisticRegression())
    print(f"  pipeline steps : {[name for name, _ in pipe.steps]}")

    print("--- fitting the pipeline fits every step; predict runs the whole chain ---")
    y = np.array([0, 0, 1, 1])
    pipe.fit(X, y)                        # scaler.fit + logreg.fit, in order
    preds = pipe.predict(X)
    print(f"  pipeline predicts : {preds.tolist()}")
    print(f"  it scaled then classified in one call : {len(preds) == len(X)}")

    print("--- why a pipeline: it fits preprocessing on TRAIN only (no leakage) ---")
    print(f"  a pipeline fit on the training split scales using TRAIN statistics,")
    print(f"  then applies them to test, test data never influences the scaler")

    print("--- the rule ---")
    print(f"  scale features for scale-sensitive models; wrap preprocessing + model in")
    print(f"  a Pipeline so fitting respects the train/test split (no data leakage)")


if __name__ == "__main__":
    main()
