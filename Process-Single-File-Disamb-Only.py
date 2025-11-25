from MorphologicalAnalysis.FsmMorphologicalAnalyzer import FsmMorphologicalAnalyzer
from MorphologicalDisambiguation.LongestRootFirstDisambiguation import LongestRootFirstDisambiguation
from Corpus.Sentence import Sentence
import os

# -------------------------------
# Initialize global components
# -------------------------------
fsm = FsmMorphologicalAnalyzer()
algorithm = LongestRootFirstDisambiguation()


# -------------------------------
# Disambiguation function
# -------------------------------
def disambiguate_text(sentence_text):
    """
    Takes a sentence string and returns a list of tuples:
    (word_surface, parse_string)
    """
    # Get morphological analysis for the sentence
    analysis = fsm.robustMorphologicalAnalysis(Sentence(sentence_text))

    # Disambiguate
    corrected = algorithm.disambiguate(analysis)  # returns list of FsmParse objects

    results = []
    for parse in corrected:
        word_surface = parse.getWord().getName()  # the root word
        parse_str = str(parse)  # full parse string
        results.append((word_surface, parse_str))

    return results


# -------------------------------
# Process a single file
# -------------------------------
def process_file_disamb_only(input_fp):
    """
    Reads a file, disambiguates the sentence, and writes results to a new file.
    """
    out_file = input_fp + "-Disamb.txt"

    with open(input_fp, "r", encoding="utf-8") as f:
        text = f.read().strip()

    with open(out_file, "w", encoding="utf-8") as out:
        out.write(f"INPUT FILE: {input_fp}\n\n")
        out.write(f"SENTENCE:\n{text}\n\n")

        try:
            disamb_results = disambiguate_text(text)
            for word_root, parse_str in disamb_results:
                out.write(f"{word_root}\t{parse_str}\n")

        except Exception as e:
            out.write(f"ERROR:\n{str(e)}\n")

    print(f"Finished → {out_file}")


# -------------------------------
# MAIN
# -------------------------------
if __name__ == "__main__":
    input_fp = r"C:\work\4th-Grade-Fall\CS401\DropboxBackUp\Ekonomi-Split-new\ATV\(controled) ATV20231201_atv Ana Haber ｜ 1 Aralık 2023.tr.txt"
    process_file_disamb_only(input_fp)
