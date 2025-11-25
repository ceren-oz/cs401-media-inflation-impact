import os
import glob
import shutil
from MorphologicalAnalysis.FsmMorphologicalAnalyzer import FsmMorphologicalAnalyzer

fsm = FsmMorphologicalAnalyzer()

TARGET_TENSE_TAGS = {"PAST", "FUTURE", "PROGRESSIVE1", "NARRATIVE"}


def is_verb(word):
    """
    Returns True if ANY parse of the word has POS == VERB.
    Used ONLY for splitting.
    """
    analysis = fsm.morphologicalAnalysis(word)

    if analysis is None or analysis.size() == 0:
        return False

    for i in range(analysis.size()):
        parse = analysis.getFsmParse(i)
        if parse.getPos() == "VERB":
            return True

    return False


def is_strong_verb(word):
    """
    Returns True ONLY IF:
      - There is at least one VERB parse
      - AND that parse contains PAST/FUTURE/PROGRESSIVE1/NARRATIVE

    This information is computed but NOT used for splitting.
    """
    analysis = fsm.morphologicalAnalysis(word)

    if analysis is None or analysis.size() == 0:
        return False

    for i in range(analysis.size()):
        parse = analysis.getFsmParse(i)

        if parse.getPos() == "VERB":
            for tag in TARGET_TENSE_TAGS:
                if parse.containsTag(tag):
                    return True

    return False


def split_sentences_by_verb(text):
    """
    Splits ONLY when a word has ANY parse with POS=VERB.
    (Strong verb info is ignored for splitting.)
    """

    words = text.split()
    sentences = []
    current = []

    for word in words:

        # always add word to current sentence
        current.append(word)

        if is_verb(word):
            # strong_verb = is_strong_verb(word)   # computed if needed
            sentences.append(" ".join(current))
            current = []

    # leftover words
    if current:
        sentences.append(" ".join(current))

    return sentences


def process_directory(base_path):
    """
    Mirrors folder structure but CLEANS output folder first:
        Ekonomi → Ekonomi-Split
        Ekonomi-Yapilanlar → Ekonomi-Yapilanlar-Split
        Ekonomi-Yapilmayanlar → Ekonomi-Yapilmayanlar-Split
    """

    output_path = base_path + "-Split"

    # --- CLEANUP STEP ---
    if os.path.exists(output_path):
        print(f"Temizlik yapılıyor: {output_path} siliniyor...")
        shutil.rmtree(output_path)

    os.makedirs(output_path, exist_ok=True)
    # ---------------------

    for channel_folder in os.listdir(base_path):
        channel_path = os.path.join(base_path, channel_folder)

        if not os.path.isdir(channel_path):
            continue

        output_channel_path = os.path.join(output_path, channel_folder)
        os.makedirs(output_channel_path, exist_ok=True)

        txt_files = glob.glob(os.path.join(channel_path, "*.txt"))

        for fp in txt_files:
            file_name = os.path.basename(fp)

            with open(fp, "r", encoding="utf-8") as f:
                text = f.read()

            sentences = split_sentences_by_verb(text)

            out_fp = os.path.join(output_channel_path, file_name)

            with open(out_fp, "w", encoding="utf-8") as out:
                for s in sentences:
                    out.write(s + "\n")

    print(f"Tamamlandı → {base_path} işlendi → Çıktı: {output_path}")


# -------------------------------------------------------------------------
# Run for all 3 folders
# -------------------------------------------------------------------------
paths = [
    r"C:\work\4th-Grade-Fall\CS401\DropboxBackUp\Ekonomi",
    r"C:\work\4th-Grade-Fall\CS401\DropboxBackUp\Ekonomi-Yapilanlar",
    r"C:\work\4th-Grade-Fall\CS401\DropboxBackUp\Ekonomi-Yapilmayanlar"
]

for p in paths:
    process_directory(p)
