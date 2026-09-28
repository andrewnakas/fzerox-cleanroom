"""Contamination scanner.

Given the *expressive* byte streams of a retail ROM (pixels, meshes, poses,
text, samples, note data...) and the byte streams of a clean build, report
every window of WINDOW bytes the build shares with retail expressive data.
Trivial windows (period <= 4, or fewer than MIN_DISTINCT distinct byte
values) are ignored because any encoder produces them.
"""
import numpy as np

WINDOW = 16
MIN_DISTINCT = 6


def _hashes(buf: bytes, window=WINDOW):
    a = np.frombuffer(buf, dtype=np.uint8)
    n = len(a) - window + 1
    if n <= 0:
        return np.zeros(0, np.uint64), np.zeros(0, bool)
    h = np.zeros(n, dtype=np.uint64)
    prime = np.uint64(1099511628211)
    with np.errstate(over="ignore"):
        for k in range(window):
            h = (h ^ a[k:k + n].astype(np.uint64)) * prime
    # Periodic windows (period 1, 2 or 4) carry no content.
    same4 = (a[4:] == a[:-4]).astype(np.int32)
    c = np.concatenate([[0], np.cumsum(same4)])
    span = window - 4
    periodic = np.zeros(n, bool)
    m = min(n, len(c) - span)
    periodic[:m] = (c[span:span + m] - c[:m]) == span
    # Low-information windows (fewer than MIN_DISTINCT byte values, e.g. an
    # identity matrix or unit quaternion) are shared by construction.
    win = np.lib.stride_tricks.sliding_window_view(a, window)
    srt = np.sort(win, axis=1)
    distinct = 1 + (srt[:, 1:] != srt[:, :-1]).sum(axis=1)
    return h, periodic | (distinct < MIN_DISTINCT)


CHUNK = 1 << 20


def _hashes_chunked(buf, window=WINDOW):
    """_hashes over 1 MB pieces (overlapping by window-1): same result, bounded temporary memory."""
    if len(buf) <= CHUNK + window:
        return _hashes(buf, window)
    hs, ps = [], []
    for o in range(0, len(buf) - window + 1, CHUNK):
        h, p = _hashes(buf[o:o + CHUNK + window - 1], window)
        hs.append(h)
        ps.append(p)
    return np.concatenate(hs), np.concatenate(ps)


def build_index(streams):
    """streams: iterable of bytes (retail expressive data)."""
    hs = []
    for s in streams:
        h, per = _hashes_chunked(s)
        hs.append(np.unique(h[~per]))
    return np.unique(np.concatenate(hs)) if hs else np.zeros(0, np.uint64)


FAIL_RUN = 32


def _max_run(mask):
    """Longest shared byte run implied by consecutive matching windows."""
    if not mask.any():
        return 0
    d = np.diff(np.concatenate([[0], mask.astype(np.int8), [0]]))
    starts, ends = np.nonzero(d == 1)[0], np.nonzero(d == -1)[0]
    return int((ends - starts).max()) + WINDOW - 1


def scan(index, labelled_streams):
    """labelled_streams: iterable of (label, bytes). Returns list of
    (label, first matching offset, number of matching windows, longest
    shared run in bytes)."""
    hits = []
    for label, s in labelled_streams:
        h, per = _hashes_chunked(s)
        if not len(h):
            continue
        pos = np.minimum(np.searchsorted(index, h), max(0, len(index) - 1))
        m = (index[pos] == h) & ~per if len(index) else np.zeros(len(h), bool)
        if m.any():
            idx = np.nonzero(m)[0]
            hits.append((label, int(idx[0]), int(m.sum()), _max_run(m)))
    return hits
