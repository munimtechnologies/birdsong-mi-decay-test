"""Fail fast if the stage-7 audio and labelling dependencies are missing, so that the tests that
need them cannot be skipped silently inside the job. Apache-2.0, MV2, Munim, Inc. Made with AI
agents."""
import sys


def main():
    import librosa
    import numpy
    import scipy
    import sklearn
    import sklearn.cluster
    import umap
    import vocalseg.dynamic_thresholding  # noqa: F401
    import vocalseg.utils  # noqa: F401
    print("deps ok: numpy %s scipy %s librosa %s sklearn %s umap %s" % (
        numpy.__version__, scipy.__version__, librosa.__version__, sklearn.__version__,
        getattr(umap, "__version__", "?")), flush=True)
    if not hasattr(sklearn.cluster, "HDBSCAN"):
        print("sklearn has no HDBSCAN", flush=True)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
