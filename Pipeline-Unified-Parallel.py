# -------------------------------------------------------------
# Full Combined Pipeline: Split + Disambiguation + Sentiment Analysis (4-core parallel)
# -------------------------------------------------------------

import os
import glob
from concurrent.futures import ProcessPoolExecutor
from MorphologicalAnalysis.FsmMorphologicalAnalyzer import FsmMorphologicalAnalyzer
from MorphologicalDisambiguation.LongestRootFirstDisambiguation import LongestRootFirstDisambiguation
from Corpus.Sentence import Sentence
from MorphologicalAnalysis.Transition import Transition
from SentiNet.SentiLiteralNet import SentiLiteralNet

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
# GLOBAL COMPONENTS (to be initialized in each process)
# -------------------------------------------------------------
def init_globals():
    global fsm_global, disamb_global, transition_obj_mak, transition_obj_mek, senti_net
    fsm_global = FsmMorphologicalAnalyzer()
    disamb_global = LongestRootFirstDisambiguation()
    transition_obj_mak = Transition("mak")
    transition_obj_mek = Transition("mek")
    senti_net = SentiLiteralNet()

TARGET_TENSE_TAGS = {"PAST", "FUT", "PROG1", "NARR"}

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

# -------------------------------------------------------------
# DISAMBIGUATION
# -------------------------------------------------------------
def disambiguate_sentence(sentence_text):
    analysis = fsm_global.robustMorphologicalAnalysis(Sentence(sentence_text))
    selected = disamb_global.disambiguate(analysis)  # list of FsmParse objects
    return selected

# -------------------------------------------------------------
# SENTIMENT ANALYSIS
# -------------------------------------------------------------
def count_positive_negative_words(per_word_data):
    pos_count = 0
    neg_count = 0

    for (_, _, _, pos_score, neg_score, _) in per_word_data:
        if pos_score > neg_score:
            pos_count += 1
        elif neg_score > pos_score:
            neg_count += 1

    return pos_count, neg_count


def apply_transition_and_score(disamb_results):
    sentence_score_pos = 0.0
    sentence_score_neg = 0.0
    per_word_data = []

    for parse in disamb_results:
        root = parse.getWord().getName() if hasattr(parse.getWord(), "getName") else str(parse.getWord())
        pos = parse.getRootPos()

        # Infinitive for verbs
        if pos == "VERB":
            suffix = pick_infinitive_suffix(root)
            if suffix == "mak":
                infinitive = transition_obj_mak.makeTransition(parse.getWord(), parse.getWord().getName(), None)
            else:
                infinitive = transition_obj_mek.makeTransition(parse.getWord(), parse.getWord().getName(), None)
        else:
            infinitive = root

        # SentiNet lookup
        try:
            literal = senti_net.getSentiLiteral(infinitive)
            pos_score = float(literal.getPositiveScore())
            neg_score = float(literal.getNegativeScore())
        except Exception:
            pos_score = 0.0
            neg_score = 0.0

        sentence_score_pos += pos_score
        sentence_score_neg += neg_score

        per_word_data.append(
            (str(parse.getWord()), root, infinitive, pos_score, neg_score, str(parse))
        )

    return per_word_data, sentence_score_pos, sentence_score_neg

# -------------------------------------------------------------
# SPLIT FILE INTO SENTENCES
# -------------------------------------------------------------
def split_text_by_strong_verbs(text, fsm):
    words = text.split()
    sentences = []
    current = []
    for w in words:
        current.append(w)
        if is_strong_verb(w, fsm):
            sentences.append(" ".join(current))
            current = []
    if current:
        sentences.append(" ".join(current))
    return sentences

# -------------------------------------------------------------
# PROCESS SINGLE FILE
# -------------------------------------------------------------
def process_single_file(fp, out_folder):
    init_globals()  # initialize globals for this process
    os.makedirs(out_folder, exist_ok=True)
    filename = os.path.basename(fp)
    out_file = os.path.join(out_folder, filename)

    with open(fp, "r", encoding="utf-8") as f:
        text = f.read().strip()

    sentences = split_text_by_strong_verbs(text, fsm_global)

    with open(out_file, "w", encoding="utf-8") as out:
        out.write(f"INPUT FILE: {fp}\n\n")
        for sentence_text in sentences:
            out.write("<S>\n")
            out.write(sentence_text + "\n\n")
            try:
                disamb = disambiguate_sentence(sentence_text)
                per_word, pos_total, neg_total = apply_transition_and_score(disamb)
                pos_word_count, neg_word_count = count_positive_negative_words(per_word)

                for (w, root, infinitive, p, n, parse_str) in per_word:
                    out.write(f"{w}\t{parse_str}\tPOS={p}\tNEG={n}\n")

                out.write(f"\nTOTAL_POS={pos_total}\n")
                out.write(f"TOTAL_NEG={neg_total}\n")
                out.write(f"POSITIVE_WORD_COUNT={pos_word_count}\n")
                out.write(f"NEGATIVE_WORD_COUNT={neg_word_count}\n")


            except Exception as e:
                out.write(f"ERROR:\n{str(e)}\n")

            out.write("</S>\n\n")

# -------------------------------------------------------------
# PROCESS DIRECTORY (PARALLEL)
# -------------------------------------------------------------
def process_directory_parallel(base_path, output_base, max_workers=4):
    os.makedirs(output_base, exist_ok=True)
    tasks = []

    for channel_folder in os.listdir(base_path):
        channel_path = os.path.join(base_path, channel_folder)
        if not os.path.isdir(channel_path):
            continue

        out_channel_folder = os.path.join(output_base, channel_folder)
        os.makedirs(out_channel_folder, exist_ok=True)

        for fp in glob.glob(os.path.join(channel_path, "*.txt")):
            tasks.append((fp, out_channel_folder))

    # Parallel execution
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(process_single_file, fp, out_folder) for fp, out_folder in tasks]
        for f in futures:
            f.result()  # wait for completion

    print(f"Finished! Outputs stored under → {output_base}")

# -------------------------------------------------------------
# MAIN
# -------------------------------------------------------------
if __name__ == "__main__":
    ekonomi_folder = r"C:\work\4th-Grade-Fall\CS401\DropboxBackUp\Ekonomi-Yapilanlar"
    output_folder = r"C:\work\4th-Grade-Fall\CS401\DropboxBackUp\Ekonomi-Yapilanlar-Sentiment-Analysis-Count-Pos-Neg"
    process_directory_parallel(ekonomi_folder, output_folder, max_workers=4)
