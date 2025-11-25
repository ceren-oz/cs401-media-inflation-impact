# -------------------------------------------------------------
# Disambiguation + Sentiment Analysis Pipeline
# -------------------------------------------------------------

import os
from MorphologicalAnalysis.FsmMorphologicalAnalyzer import FsmMorphologicalAnalyzer
from MorphologicalDisambiguation.LongestRootFirstDisambiguation import LongestRootFirstDisambiguation
from Corpus.Sentence import Sentence
from MorphologicalAnalysis.Transition import Transition
from SentiNet.SentiLiteralNet import SentiLiteralNet
import re

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
# GLOBAL COMPONENTS
# -------------------------------------------------------------
fsm_global = FsmMorphologicalAnalyzer()
disamb_global = LongestRootFirstDisambiguation()
transition_obj_mak = Transition("mak")
transition_obj_mek = Transition("mek")
senti_net = SentiLiteralNet()


# -------------------------------------------------------------
# DISAMBIGUATION
# -------------------------------------------------------------
def disambiguate_sentence(sentence_text):
    """
    Disambiguates a sentence using LongestRootFirstDisambiguation.
    Returns a list of FsmParse objects.
    """
    analysis = fsm_global.robustMorphologicalAnalysis(Sentence(sentence_text))
    selected = disamb_global.disambiguate(analysis)  # list of FsmParse objects
    return selected


# -------------------------------------------------------------
# SENTIMENT ANALYSIS
# -------------------------------------------------------------
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

        # SentiNet lookup using SentiLiteralNet
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
# SPLIT TEXT INTO SENTENCES
# -------------------------------------------------------------
def split_into_sentences(text):
    """
    Splits text into sentences using simple period/line breaks.
    Adjust this regex if needed for Turkish punctuation.
    """
    # Split on periods, question marks, exclamation marks or newlines
    sentences = re.split(r'(?<=[.!?])\s+|\n+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    return sentences


# -------------------------------------------------------------
# PROCESS SINGLE FILE
# -------------------------------------------------------------
def process_single_file_no_split(fp):
    out_file = fp + "-Disamb-Senti-02.txt"

    with open(fp, "r", encoding="utf-8") as f:
        text = f.read().strip()

    sentences = split_into_sentences(text)

    with open(out_file, "w", encoding="utf-8") as out:
        out.write(f"INPUT FILE: {fp}\n\n")

        for sentence_text in sentences:
            out.write("<S>\n")
            out.write(sentence_text + "\n\n")
            try:
                disamb = disambiguate_sentence(sentence_text)
                per_word, pos_total, neg_total = apply_transition_and_score(disamb)

                for (w, root, infinitive, p, n, parse_str) in per_word:
                    out.write(f"{w}\t{parse_str}\tPOS={p}\tNEG={n}\n")

                out.write(f"\nTOTAL_POS={pos_total}\n")
                out.write(f"TOTAL_NEG={neg_total}\n")

            except Exception as e:
                out.write(f"ERROR:\n{str(e)}\n")

            out.write("</S>\n\n")

    print(f"Finished → {out_file}")


# -------------------------------------------------------------
# MAIN
# -------------------------------------------------------------
if __name__ == "__main__":
    input_fp = r"C:\work\4th-Grade-Fall\CS401\DropboxBackUp\Ekonomi-Split-new\ATV\(controled) ATV20231201_atv Ana Haber ｜ 1 Aralık 2023.tr.txt"
    process_single_file_no_split(input_fp)
