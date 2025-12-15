import os
import re
import math
import pandas as pd
from MorphologicalAnalysis.FsmMorphologicalAnalyzer import FsmMorphologicalAnalyzer
from functools import lru_cache
from collections import defaultdict, Counter

# ---------------------------
# CONFIG (tweakable)
# ---------------------------
MAIN_DICT_PATH = "words.txt"
CUSTOM_DICT_PATH = "custom_dictionary.txt"
OUTPUT_CSV = "incorrect_and_fixed_single_advanced.csv"

# Candidate search window
MIN_LEN_DELTA = -2
MAX_LEN_DELTA = 3

# Weighted Levenshtein thresholds
MAX_DIST_SHORT = 1   # for length <= 5
MAX_DIST_MED = 2     # for 6-9
MAX_DIST_LONG = 3    # for length >=10

# vowels for Turkish
VOWELS = set(list("aeıioöuüAEIİOÖUÜ"))

# ---------------------------
# Utilities: load dictionary
# ---------------------------
def load_dictionary(path):
    s = set()
    if not os.path.exists(path):
        return s
    with open(path, "r", encoding="utf-8") as f:
        for ln in f:
            w = ln.strip()
            if w:
                s.add(w)
                s.add(w.lower())
    return s

# ---------------------------
# Turkish-safe capitalization
# ---------------------------
def turkish_capitalize(word):
    if not word:
        return word

    first = word[0]
    rest = word[1:]

    if first == "i":
        first_cap = "İ"
    elif first == "ı":
        first_cap = "I"
    else:
        first_cap = first.upper()

    rest = rest.replace("I", "ı").replace("İ", "i").lower()
    return first_cap + rest

# ---------------------------
# Skip rules (improved)
# ---------------------------
def should_skip_word(word):
    w = word.strip()

    if not w:
        return True

    # Skip tokens containing digits (we removed % and numeric tokens earlier),
    # also skip tokens with colon/slash/percent patterns (times, fractions)
    if any(ch.isdigit() for ch in w):
        return True
    if re.search(r"[:/\\%]", w):
        return True

    # skip tokens that include other symbols (punctuation) - preserve apostrophe
    if re.search(r"[^A-Za-zÇĞİÖŞÜçğıöşü'\-]", w):
        return True

    # skip ALL CAPS (likely acronyms)
    if len(w) >= 2 and w.isupper():
        return True

    # skip 1-letter tokens (but keep 2-letter common words? keep >=2)
    if len(w) <= 1:
        return True

    return False

# ---------------------------
# Normalization helpers
# ---------------------------
def normalize_token(w):
    """
    - normalize curly apostrophes to straight
    - remove invisible unicode
    - collapse repeating letters heuristically for obvious OCR runs (aaa->a)
    - map common OCR confusions (l -> ı in some contexts)
    """
    if not w:
        return w

    # normalize apostrophes and similar
    w = w.replace("’", "'").replace("‘", "'").replace("`", "'")

    # remove zero-width / bidi marks
    w = re.sub(r"[\u200B-\u200F\u202A-\u202E]", "", w)

    # fix common OCR mistakes (heuristic)
    # sometimes l was read as ı and vice versa — don't force but do basic:
    # If contains 'l' and not many vowels but lowercase, keep as is.
    # collapse long repeating sequences of same letter (>=3)
    w = re.sub(r"(.)\1{2,}", r"\1", w)

    return w

# ---------------------------
# Tokenizer preserving whitespace & punctuation
# ---------------------------
def tokenize_preserve(text):
    # returns list of tokens where words, punctuation and whitespace are separate
    # \w will include digits — but we will filter numeric tokens later
    tokens = re.findall(r"\w+|[^\w\s]+|\s+", text, flags=re.UNICODE)
    return tokens

# ---------------------------
# FSM wrapper helpers
# ---------------------------
def fsm_accepts(fsm, w):
    """
    Returns True if FSM has any analysis for w.
    We'll try variants too (capitalize) inside this helper.
    """
    if not w:
        return False
    try:
        if fsm.morphologicalAnalysis(w).size() > 0:
            return True
        w_cap = turkish_capitalize(w)
        if fsm.morphologicalAnalysis(w_cap).size() > 0:
            return True
        if fsm.morphologicalAnalysis(w.upper()).size() > 0:
            return True
    except Exception:
        # in case FSM throws—treat as not accepted
        return False
    return False

# ---------------------------
# Weighted Levenshtein (vowel edits cheaper)
# ---------------------------
def weighted_levenshtein(a, b):
    """
    Compute a weighted edit distance between a and b.
    - substitution cost: 0 if equal, else 0.5 if either char is vowel, else 1.0
    - insertion/deletion cost: 0.5 if vowel inserted/removed, else 1.0
    This biases toward vowel edits (common in OCR / Turkish variants).
    """
    la, lb = len(a), len(b)
    # dp matrix
    dp = [[0.0]*(lb+1) for _ in range(la+1)]
    # init
    dp[0][0] = 0.0
    for i in range(1, la+1):
        ch = a[i-1]
        dp[i][0] = dp[i-1][0] + (0.5 if ch in VOWELS else 1.0)
    for j in range(1, lb+1):
        ch = b[j-1]
        dp[0][j] = dp[0][j-1] + (0.5 if ch in VOWELS else 1.0)

    for i in range(1, la+1):
        for j in range(1, lb+1):
            ca = a[i-1]
            cb = b[j-1]
            if ca == cb:
                cost_sub = 0.0
            else:
                # substitution cost lower if vowels involved
                cost_sub = 0.5 if (ca in VOWELS or cb in VOWELS) else 1.0
            # deletion cost (remove ca)
            cost_del = 0.5 if (ca in VOWELS) else 1.0
            # insertion cost (insert cb)
            cost_ins = 0.5 if (cb in VOWELS) else 1.0

            dp[i][j] = min(
                dp[i-1][j] + cost_del,      # deletion
                dp[i][j-1] + cost_ins,      # insertion
                dp[i-1][j-1] + cost_sub     # substitution
            )
    return dp[la][lb]

# ---------------------------
# Candidate generation: fast filters
# ---------------------------
def generate_candidates(word, dictionary):
    """
    Return small set of candidate dictionary words filtered by:
    - length window
    - same first letter (lowercase) OR first vowel equal
    - further distance check (weighted) applied afterwards
    """
    w = word.lower()
    L = len(w)
    min_len = max(1, L + MIN_LEN_DELTA)
    max_len = L + MAX_LEN_DELTA

    candidates = []
    first = w[0] if w else ""
    for cand in dictionary:
        lc = cand.lower()
        if len(lc) < min_len or len(lc) > max_len:
            continue
        if not lc:
            continue
        # quick first-letter or vowel match to reduce set
        if lc[0] == first or (any(v in lc for v in VOWELS) and any(v in w for v in VOWELS) and lc[0] != 'q'):
            candidates.append(cand)
    return candidates

# ---------------------------
# Scoring a candidate using FSM + context
# ---------------------------
def score_candidate(fsm, original, candidate, prev_token, next_token):
    """
    Lower score = better. Combines:
    - weighted edit distance
    - + large penalty if candidate not accepted by FSM
    - small bonus if candidate makes prev/next token morphologically valid when combined
    """
    wd = weighted_levenshtein(original.lower(), candidate.lower())

    # dynamic threshold base
    L = len(original)
    if L <= 5:
        base_thresh = MAX_DIST_SHORT
    elif L <= 9:
        base_thresh = MAX_DIST_MED
    else:
        base_thresh = MAX_DIST_LONG

    # big penalty if candidate is not morphologically valid
    fsm_ok = fsm_accepts(fsm, candidate)
    penalty = 0.0 if fsm_ok else 3.0  # large penalty to discard non-FSM words

    # context bonus: if candidate helps prev/next become accepted, bonus
    context_bonus = 0.0
    try:
        if prev_token and not fsm_accepts(fsm, prev_token):
            # combine prev + candidate to see if valid phrase root (basic)
            combined = f"{prev_token} {candidate}"
            # cheap heuristic: if candidate accepted and prev was not, reward
            if fsm_ok:
                context_bonus -= 0.5
        if next_token and not fsm_accepts(fsm, next_token):
            if fsm_ok:
                context_bonus -= 0.5
    except Exception:
        pass

    score = wd + penalty + context_bonus
    return score, base_thresh

# ---------------------------
# Main process_text pipeline (full)
# ---------------------------
# ---------------------------
# Build dictionary index once (fast candidate lookup)
# ---------------------------
def build_dict_index(dictionary):
    """
    Returns:
      - by_first: dict first_letter -> list of words
      - by_len: dict length -> list of words
    """
    by_first = defaultdict(list)
    by_len = defaultdict(list)
    for w in dictionary:
        if not w:
            continue
        lw = w.lower()
        by_first[lw[0]].append(w)
        by_len[len(lw)].append(w)
    # also store lengths available for quick range selection
    lengths = sorted(by_len.keys())
    return {"by_first": by_first, "by_len": by_len, "lengths": lengths}

# ---------------------------
# Fast lightweight similarity prefilter
# ---------------------------
def char_overlap_score(a, b):
    sa = Counter(a)
    sb = Counter(b)
    inter = sum((sa & sb).values())
    union = sum((sa | sb).values())
    if union == 0:
        return 0.0
    return inter / union  # 0..1 (higher = more similar)

# ---------------------------
# New process_text (uses cached fsm and cached lev)
# ---------------------------
def process_text(text, fsm, main_dict, custom_dict, dict_index,
                 max_candidates=200):
    """
    High-performance version:
      - expects dict_index built by build_dict_index()
      - uses fsm_cached(word) and cached_weighted_lev(a,b) created in caller
    """

    # prepare merged dictionary set and quick existence check
    merged_dict = set(main_dict) | set(custom_dict)
    merged_lower = set(w.lower() for w in merged_dict)

    tokens = tokenize_preserve(text)

    # collect candidate words (index in tokens, original token, normalized)
    words_to_check = []
    for idx, tok in enumerate(tokens):
        if tok.strip() == "":
            continue
        if re.fullmatch(r"[A-Za-zÇĞİÖŞÜçğıöşü']+", tok):
            norm = normalize_token(tok)
            if not norm:
                continue
            if should_skip_word(norm):
                continue
            # quick dict presence (variants)
            if norm in merged_dict or norm.lower() in merged_lower or turkish_capitalize(norm) in merged_dict:
                continue
            # FSM quick accept (use direct fsm; caller should provide cached wrapper)
            # We'll use fsm.morphologicalAnalysis here only as a last resort
            words_to_check.append((idx, tok, norm))

    replacements = {}
    incorrect_info = []

    by_first = dict_index["by_first"]
    by_len = dict_index["by_len"]
    lengths_available = dict_index["lengths"]

    # Pre-calc small helper: closure wrappers expected by this function
    # Caller must set these two in process_single_file: fsm_cached(word), cached_weighted_lev(a,b)
    # We'll refer to them via the global names; ensure they exist
    global fsm_cached_accepts, cached_weighted_lev
    if 'fsm_cached_accepts' not in globals() or 'cached_weighted_lev' not in globals():
        raise RuntimeError("Please ensure fsm_cached_accepts and cached_weighted_lev exist (set in process_single_file).")

    # iterate words
    for pos, orig_tok, norm_tok in words_to_check:
        # if FSM accepts normalized -> skip
        if fsm_cached_accepts(norm_tok):
            continue

        # quick presence in dict variants
        if norm_tok in merged_dict or norm_tok.lower() in merged_lower:
            continue

        # Candidate generation: fast filter using first letter & length window
        w = norm_tok.lower()
        L = len(w)
        min_len = max(1, L + MIN_LEN_DELTA)
        max_len = L + MAX_LEN_DELTA

        # lookup by first letter - fastest
        first = w[0]
        pool = by_first.get(first, [])

        # restrict by length window
        pool_filtered = [cand for cand in pool if min_len <= len(cand) <= max_len]

        # if pool too small, also add same-length words from by_len buckets nearby
        if len(pool_filtered) < 30:
            for ll in range(min_len, max_len + 1):
                if ll in by_len:
                    pool_filtered.extend(by_len[ll])

        # deduplicate and limit
        if not pool_filtered:
            replacements[norm_tok] = None
            incorrect_info.append({"incorrect_word": norm_tok, "corrected_word": ""})
            continue

        # prefilter by cheap char overlap to avoid heavy lev on far words
        scored_candidates = []
        for cand in set(pool_filtered):
            cand_l = cand.lower()
            overlap = char_overlap_score(w, cand_l)
            # require minimal overlap depending on length (tunable)
            if L <= 4 and overlap < 0.4:
                continue
            if 5 <= L <= 8 and overlap < 0.3:
                continue
            if L >= 9 and overlap < 0.2:
                continue
            scored_candidates.append((cand, overlap))

        # sort by overlap desc to evaluate best candidates first
        scored_candidates.sort(key=lambda x: -x[1])
        if not scored_candidates:
            # no good candidates
            replacements[norm_tok] = None
            incorrect_info.append({"incorrect_word": norm_tok, "corrected_word": ""})
            continue

        # limit candidate evaluations to max_candidates (balanced mode)
        pool_eval = [c for c,_ in scored_candidates[:max_candidates]]

        # Find previous/next word tokens (normalized) for context scoring
        prev_tok = None
        next_tok = None
        i = pos-1
        while i >= 0:
            if re.fullmatch(r"[A-Za-zÇĞİÖŞÜçğıöşü']+", tokens[i]):
                prev_tok = normalize_token(tokens[i])
                break
            i -= 1
        i = pos+1
        while i < len(tokens):
            if re.fullmatch(r"[A-Za-zÇĞİÖŞÜçğıöşü']+", tokens[i]):
                next_tok = normalize_token(tokens[i])
                break
            i += 1

        # score candidates using cached weighted lev + cached fsm checks
        best = None
        best_score = float("inf")
        chosen_thresh = None
        for cand in pool_eval:
            wd = cached_weighted_lev(w, cand.lower())
            # dynamic allowed threshold
            if L <= 5:
                base = MAX_DIST_SHORT
            elif L <= 9:
                base = MAX_DIST_MED
            else:
                base = MAX_DIST_LONG
            # penalty if not morphological valid
            fsm_ok = fsm_cached_accepts(cand)
            penalty = 0.0 if fsm_ok else 3.0

            # small context bonus if FSM helps neighbors (cheap)
            context_bonus = 0.0
            if fsm_ok:
                if prev_tok and not fsm_cached_accepts(prev_tok):
                    context_bonus -= 0.25
                if next_tok and not fsm_cached_accepts(next_tok):
                    context_bonus -= 0.25

            score = wd + penalty + context_bonus

            # quick acceptance rule: wd within base and fsm_ok => good
            if fsm_ok and wd <= base + 0.1:
                best = cand
                best_score = score
                chosen_thresh = base
                break  # good candidate found, stop early

            if score < best_score:
                best_score = score
                best = cand
                chosen_thresh = base

        # choose final candidate with acceptance rules
        if best and fsm_cached_accepts(best):
            replacements[norm_tok] = best
            incorrect_info.append({"incorrect_word": norm_tok, "corrected_word": best})
        else:
            # fallback: accept if best_score reasonably low relative to threshold
            if best and best_score <= (chosen_thresh + 0.8):
                replacements[norm_tok] = best
                incorrect_info.append({"incorrect_word": norm_tok, "corrected_word": best})
            else:
                replacements[norm_tok] = None
                incorrect_info.append({"incorrect_word": norm_tok, "corrected_word": ""})

    # Apply replacements to original text safely (longest-first to avoid substring issues)
    corrected_text = text
    for wrong in sorted(replacements.keys(), key=lambda x: -len(x)):
        correct = replacements[wrong]
        if correct:
            corrected_text = re.sub(rf"\b{re.escape(wrong)}\b", correct, corrected_text)
        else:
            corrected_text = re.sub(rf"\b{re.escape(wrong)}\b", f"[[{wrong}]]", corrected_text)

    return corrected_text, incorrect_info

# ---------------------------
# Updated process_single_file that prepares caches and indexes
# ---------------------------
def process_single_file(file_path,
                        main_dict_path=MAIN_DICT_PATH,
                        custom_dict_path=CUSTOM_DICT_PATH,
                        output_csv=OUTPUT_CSV):
    # instantiate FSM once
    fsm = FsmMorphologicalAnalyzer()

    # caching wrappers that capture fsm instance and are lru-cached by word(s)
    @lru_cache(maxsize=50000)
    def fsm_cached_accepts_local(word):
        if not word:
            return False
        try:
            if fsm.morphologicalAnalysis(word).size() > 0:
                return True
            wc = turkish_capitalize(word)
            if fsm.morphologicalAnalysis(wc).size() > 0:
                return True
            if fsm.morphologicalAnalysis(word.upper()).size() > 0:
                return True
        except Exception:
            return False
        return False

    @lru_cache(maxsize=200000)
    def cached_weighted_lev_local(a, b):
        return weighted_levenshtein(a, b)

    # expose to module-level names that process_text expects (so minimal signature changes)
    globals()['fsm_cached_accepts'] = fsm_cached_accepts_local
    globals()['cached_weighted_lev'] = cached_weighted_lev_local

    main_dict = load_dictionary(main_dict_path)
    custom_dict = load_dictionary(custom_dict_path)

    # build index for speed
    dict_index = build_dict_index(main_dict | custom_dict)

    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()

    corrected_text, incorrect_list = process_text(text, fsm, main_dict, custom_dict, dict_index)

    base, ext = os.path.splitext(file_path)
    corrected_path = base + "_corrected" + ext
    with open(corrected_path, "w", encoding="utf-8") as f:
        f.write(corrected_text)

    df = pd.DataFrame(incorrect_list)
    df.to_csv(output_csv, index=False, encoding="utf-8")

    print("Done. Corrected file:", corrected_path)
    print("CSV:", output_csv)
    return df

# ---------------------------
# MAIN (change test_file path)
# ---------------------------
if __name__ == "__main__":
    test_file = r"C:\work\4th-Grade-Fall\CS401\DropboxBackUp\Ekonomi-Yapilanlar\ATV\(controled) ATV20231201_atv Ana Haber ｜ 1 Aralık 2023.tr.txt"
    process_single_file(test_file)
