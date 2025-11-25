# -------------------------------------------------------------
# Full Automatic Pipeline (Split + Split-With_Selected-Parse) — Combined per file
# Non-parallel version
# -------------------------------------------------------------

import os
import glob

from MorphologicalAnalysis.FsmMorphologicalAnalyzer import FsmMorphologicalAnalyzer
from MorphologicalDisambiguation.LongestRootFirstDisambiguation import LongestRootFirstDisambiguation
from Corpus.Sentence import Sentence
from MorphologicalAnalysis.Transition import Transition
from SentiNet.SentiNet import SentiNet

TARGET_TENSE_TAGS = {"PAST", "FUT", "PROG1", "NARR"}

# --- Vowel harmony for infinitives ---
BACK_VOWELS = set("aıou")
FRONT_VOWELS = set("eiöü")

def pick_infinitive_suffix(root: str):
    for ch in reversed(root):
        if ch in BACK_VOWELS:
            return "mak"
        if ch in FRONT_VOWELS:
            return "mek"
    return "mak"


# -------------------------------------------------------------
# Utilities
# -------------------------------------------------------------
def is_strong_verb(word, fsm: FsmMorphologicalAnalyzer):
    analysis = fsm.morphologicalAnalysis(word)
    if not analysis or analysis.size() == 0:
        return False
    for i in range(analysis.size()):
        parse = analysis.getFsmParse(i)
        if parse.getRootPos() != "VERB":
            continue
        for j in range(parse.tagSize()):
            if parse.getTag(j) in TARGET_TENSE_TAGS:
                return True
    return False

fsm_global = FsmMorphologicalAnalyzer()
disamb_global = LongestRootFirstDisambiguation()
senti = SentiNet()


def disambiguate_sentence(sentence_text):
    analysis = fsm_global.robustMorphologicalAnalysis(Sentence(sentence_text))
    selected = disamb_global.disambiguate(analysis)
    results = []
    for i in range(selected.size()):
        word = selected.getWord(i)
        parse = selected.getParse(i)
        results.append((word, parse))
    return results


def apply_transition_and_score(disamb_results):
    sentence_score_pos = 0.0
    sentence_score_neg = 0.0
    transition_obj_mak = Transition("mak")
    transition_obj_mek = Transition("mek")

    per_word_data = []

    for (word, parse) in disamb_results:
        root = parse.getWord().getName()
        pos = parse.getRootPos()

        if pos == "VERB":
            suffix = pick_infinitive_suffix(root)
            if suffix == "mak":
                word_obj = transition_obj_mak.makeTransition(parse.getWord(), None)
            else:
                word_obj = transition_obj_mek.makeTransition(parse.getWord(), None)
            infinitive = word_obj.getName()
        else:
            infinitive = root

        try:
            literal = senti.getSentiLiteral(infinitive)
            pos_score = literal.getPositiveScore()
            neg_score = literal.getNegativeScore()
        except:
            pos_score = 0.0
            neg_score = 0.0

        sentence_score_pos += pos_score
        sentence_score_neg += neg_score
        per_word_data.append((word, root, infinitive, pos_score, neg_score, parse.to_string()))

    return per_word_data, sentence_score_pos, sentence_score_neg


# -------------------------------------------------------------
# Combined per-file processing
# -------------------------------------------------------------
def process_single_file_combined(fp, split_out_file, pipeline_out_file):
    fsm = FsmMorphologicalAnalyzer()

    with open(fp, "r", encoding="utf-8") as f:
        text = f.read()
    words = text.split()

    # SPLIT
    sentences, current = [], []
    for w in words:
        current.append(w)
        if is_strong_verb(w, fsm):
            sentences.append(" ".join(current))
            current = []

    if current:
        sentences.append(" ".join(current))

    # --- Write split-only output ---
    with open(split_out_file, "w", encoding="utf-8") as out_split:
        for s in sentences:
            out_split.write(s + "\n")

    # --- Write full pipeline output ---
    with open(pipeline_out_file, "w", encoding="utf-8") as out_pipeline:
        for sentence in sentences:
            out_pipeline.write(f"SENTENCE: {sentence}\n")

            try:
                disamb = disambiguate_sentence(sentence)
                per_word, pos_total, neg_total = apply_transition_and_score(disamb)

                for (w, root, infinitive, p, n, parse_str) in per_word:
                    out_pipeline.write(f"{w}\t{root}\t{infinitive}\tPOS={p}\tNEG={n}\t{parse_str}\n")

                out_pipeline.write(f"SENTENCE_POS_TOTAL={pos_total}\n")
                out_pipeline.write(f"SENTENCE_NEG_TOTAL={neg_total}\n\n")

            except Exception as e:
                out_pipeline.write(f"ERROR: {sentence}\n{str(e)}\n\n")


# -------------------------------------------------------------
# Directory processing — combined mode
# -------------------------------------------------------------
def process_directory_combined(base_path):
    split_output = base_path + "-Split-new"
    pipeline_output = base_path + "-Split-With_Selected-Parse-new"

    os.makedirs(split_output, exist_ok=True)
    os.makedirs(pipeline_output, exist_ok=True)

    for channel_folder in os.listdir(base_path):
        channel_path = os.path.join(base_path, channel_folder)
        if not os.path.isdir(channel_path):
            continue

        out_split_channel = os.path.join(split_output, channel_folder)
        out_pipeline_channel = os.path.join(pipeline_output, channel_folder)
        os.makedirs(out_split_channel, exist_ok=True)
        os.makedirs(out_pipeline_channel, exist_ok=True)

        for fp in glob.glob(os.path.join(channel_path, "*.txt")):
            filename = os.path.basename(fp)
            split_file = os.path.join(out_split_channel, filename)
            pipeline_file = os.path.join(out_pipeline_channel, filename)

            process_single_file_combined(fp, split_file, pipeline_file)

    print(f"Finished! Split → {split_output}, Full pipeline → {pipeline_output}")


# -------------------------------------------------------------
# MAIN
# -------------------------------------------------------------
if __name__ == "__main__":
    ekonomi_folder = r"C:\work\4th-Grade-Fall\CS401\DropboxBackUp\Ekonomi"
    process_directory_combined(ekonomi_folder)
