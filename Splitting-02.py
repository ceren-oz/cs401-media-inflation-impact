import os
import glob
import shutil
from concurrent.futures import ProcessPoolExecutor
from MorphologicalAnalysis.FsmMorphologicalAnalyzer import FsmMorphologicalAnalyzer

TARGET_TENSE_TAGS = {"PAST", "FUT", "PROG1", "NARR"}


# -------------- Worker-side functions (run inside each process) --------------

def process_single_file(args):
    fp, output_file = args

    fsm = FsmMorphologicalAnalyzer()

    def is_strong_verb(word):
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

    with open(fp, "r", encoding="utf-8") as f:
        text = f.read()

    words = text.split()
    sentences, current = [], []

    for w in words:
        current.append(w)
        if is_strong_verb(w):
            sentences.append(" ".join(current))
            current = []

    if current:
        sentences.append(" ".join(current))

    with open(output_file, "w", encoding="utf-8") as out:
        for s in sentences:
            out.write(s + "\n")

    return output_file


# --------------------------- Master process ------------------------------

def get_next_output_path(base_path):
    base = base_path + "-Split"
    counter = 1
    while True:
        candidate = f"{base}-{counter:02d}"
        if not os.path.exists(candidate):
            return candidate
        counter += 1


def process_directory_parallel(base_path):
    output_path = get_next_output_path(base_path)
    os.makedirs(output_path, exist_ok=True)

    tasks = []

    for channel_folder in os.listdir(base_path):
        channel_path = os.path.join(base_path, channel_folder)
        if not os.path.isdir(channel_path):
            continue

        output_channel = os.path.join(output_path, channel_folder)
        os.makedirs(output_channel, exist_ok=True)

        for fp in glob.glob(os.path.join(channel_path, "*.txt")):
            filename = os.path.basename(fp)
            output_file = os.path.join(output_channel, filename)
            tasks.append((fp, output_file))

    # ---- Parallel execution ----
    print(f"Processing {len(tasks)} files in parallel...")
    with ProcessPoolExecutor() as executor:
        for _ in executor.map(process_single_file, tasks):
            pass

    print(f"Completed → Output: {output_path}")


# --------------------------- Run all folders ------------------------------

if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()

    paths = [
        r"C:\work\4th-Grade-Fall\CS401\DropboxBackUp\Ekonomi",
        r"C:\work\4th-Grade-Fall\CS401\DropboxBackUp\Ekonomi-Yapilanlar",
        r"C:\work\4th-Grade-Fall\CS401\DropboxBackUp\Ekonomi-Yapilmayanlar"
    ]

    for p in paths:
        process_directory_parallel(p)

