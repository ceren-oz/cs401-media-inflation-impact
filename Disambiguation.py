import os
import glob
import shutil

from MorphologicalAnalysis.FsmMorphologicalAnalyzer import FsmMorphologicalAnalyzer
from MorphologicalDisambiguation.LongestRootFirstDisambiguation import LongestRootFirstDisambiguation
from Corpus.Sentence import Sentence

# Initialize analyzers
fsm = FsmMorphologicalAnalyzer()
disamb = LongestRootFirstDisambiguation()


def disambiguate_sentence(sentence_text):
    """
    Runs robust analysis + disambiguation and returns:
        list of (word, selected_parse_string)
    """

    # Step 1: Analyze sentence
    analysis = fsm.robustMorphologicalAnalysis(Sentence(sentence_text))

    # Step 2: Disambiguate
    selected = disamb.disambiguate(analysis)

    word_parse_pairs = []

    # Step 3: Iterate through analyses and pull selected parse
    for i in range(selected.size()):
        word = selected.getWord(i)

        parse = selected.getParse(i)

        # convert parse object to readable string (root + tags)
        parse_str = parse.to_string()

        word_parse_pairs.append((word, parse_str))

    return word_parse_pairs


def process_directory(base_path):
    """
    Input folders:
        Ekonomi-Split
        Ekonomi-Yapilanlar-Split
        Ekonomi-Yapilmayanlar-Split

    Output folders:
        Ekonomi-Split-With-Selected-Parse
        ...
    """

    output_path = base_path + "-With-Selected-Parse"

    # CLEANUP
    if os.path.exists(output_path):
        print(f"Temizlik yapılıyor: {output_path} siliniyor...")
        shutil.rmtree(output_path)

    os.makedirs(output_path, exist_ok=True)

    # Process channel folders inside base_path
    for channel_folder in os.listdir(base_path):
        channel_path = os.path.join(base_path, channel_folder)

        if not os.path.isdir(channel_path):
            continue

        output_channel_path = os.path.join(output_path, channel_folder)
        os.makedirs(output_channel_path, exist_ok=True)

        # Read all splitted files
        txt_files = glob.glob(os.path.join(channel_path, "*.txt"))

        for fp in txt_files:
            file_name = os.path.basename(fp)

            with open(fp, "r", encoding="utf-8") as f:
                lines = [l.strip() for l in f.readlines() if l.strip()]

            out_fp = os.path.join(output_channel_path, file_name)

            with open(out_fp, "w", encoding="utf-8") as out:

                for sentence in lines:
                    try:
                        parsed = disambiguate_sentence(sentence)

                        out.write(f"SENTENCE: {sentence}\n")

                        for (word, parse_str) in parsed:
                            out.write(f"{word}\t{parse_str}\n")

                        out.write("\n")

                    except Exception as e:
                        # If something goes wrong, write the sentence for debugging
                        out.write(f"ERROR processing sentence: {sentence}\n")
                        out.write(str(e) + "\n\n")

    print(f"Tamamlandı → {base_path} işlendi → Çıktı: {output_path}")


# -----------------------------------------------------------------------------
# Run Step 2 for all 3 folders
# -----------------------------------------------------------------------------
paths = [
    r"C:\work\4th-Grade-Fall\CS401\DropboxBackUp\Ekonomi-Split",
    r"C:\work\4th-Grade-Fall\CS401\DropboxBackUp\Ekonomi-Yapilanlar-Split",
    r"C:\work\4th-Grade-Fall\CS401\DropboxBackUp\Ekonomi-Yapilmayanlar-Split"
]

for p in paths:
    process_directory(p)
