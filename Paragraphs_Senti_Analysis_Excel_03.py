import os
import re
import glob
import multiprocessing
from concurrent.futures import ProcessPoolExecutor, as_completed

import xlsxwriter

from MorphologicalAnalysis.FsmMorphologicalAnalyzer import FsmMorphologicalAnalyzer
from MorphologicalDisambiguation.LongestRootFirstDisambiguation import (
    LongestRootFirstDisambiguation,
)
from Corpus.Sentence import Sentence
from MorphologicalAnalysis.Transition import Transition
from SentiNet.SentiLiteralNet import SentiLiteralNet


# ===============================
# CONSTANTS
# ===============================
BACK_VOWELS = set("aıou")
FRONT_VOWELS = set("eiöü")


# ===============================
# HELPERS
# ===============================
def pick_infinitive_suffix(root: str) -> str:
    for ch in reversed(root):
        if ch in BACK_VOWELS:
            return "mak"
        if ch in FRONT_VOWELS:
            return "mek"
    return "mak"


def read_paragraphs_from_single_file(file_path: str):
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read().strip()

    return [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]


# ===============================
# NLP ANALYSIS
# ===============================
def analyze_paragraph(
    paragraph,
    fsm,
    disamb,
    senti_net,
    transition_mak,
    transition_mek,
):
    analysis = fsm.robustMorphologicalAnalysis(Sentence(paragraph))
    parses = disamb.disambiguate(analysis)

    pos_words = set()
    neg_words = set()

    pos_score = 0.0
    neg_score = 0.0

    for parse in parses:
        root = parse.getWord().getName().lower()
        pos = parse.getRootPos()

        if pos == "VERB":
            suffix = pick_infinitive_suffix(root)
            lemma = (
                transition_mak.makeTransition(parse.getWord(), root, None)
                if suffix == "mak"
                else transition_mek.makeTransition(parse.getWord(), root, None)
            ).lower()
        else:
            lemma = root

        try:
            literal = senti_net.getSentiLiteral(lemma)
            p = float(literal.getPositiveScore())
            n = float(literal.getNegativeScore())
        except Exception:
            p = n = 0.0

        if p > n:
            pos_words.add(lemma)
        elif n > p:
            neg_words.add(lemma)

        pos_score += p
        neg_score += n

    total = max(len(parses), 1)

    return (
        sorted(pos_words),
        sorted(neg_words),
        (pos_score - neg_score) / total,
        (len(pos_words) - len(neg_words)) / total,
    )


def get_lemma_of_word(
    word,
    fsm,
    disamb,
    transition_mak,
    transition_mek,
):
    analysis = fsm.robustMorphologicalAnalysis(Sentence(word))
    parses = disamb.disambiguate(analysis)

    if not parses:
        return None

    parse = parses[0]
    root = parse.getWord().getName().lower()
    pos = parse.getRootPos()

    if pos == "VERB":
        suffix = pick_infinitive_suffix(root)
        return (
            transition_mak.makeTransition(parse.getWord(), root, None)
            if suffix == "mak"
            else transition_mek.makeTransition(parse.getWord(), root, None)
        ).lower()

    return root


# ===============================
# EXCEL OUTPUT
# ===============================
def build_excel_with_colors(paragraphs, out_excel):
    workbook = xlsxwriter.Workbook(out_excel)
    worksheet = workbook.add_worksheet("Sentiment")

    headers = [
        "haber",
        "pozitif kelimeler",
        "negatif kelimeler",
        "skor_normalize",
        "frekans_normalize",
    ]

    for col, h in enumerate(headers):
        worksheet.write(0, col, h)

    # Formats
    normal_fmt = workbook.add_format({"text_wrap": True})
    pos_fmt = workbook.add_format({"font_color": "blue"})
    neg_fmt = workbook.add_format({"font_color": "red"})

    # Column widths
    worksheet.set_column(0, 0, 90)
    worksheet.set_column(1, 2, 40)
    worksheet.set_column(3, 4, 20)

    # NLP init (local, single process)
    fsm = FsmMorphologicalAnalyzer()
    disamb = LongestRootFirstDisambiguation()
    senti_net = SentiLiteralNet()
    transition_mak = Transition("mak")
    transition_mek = Transition("mek")

    row = 1

    for paragraph in paragraphs:
        pos_words, neg_words, s_norm, f_norm = analyze_paragraph(
            paragraph,
            fsm,
            disamb,
            senti_net,
            transition_mak,
            transition_mek,
        )

        worksheet.write(row, 1, ", ".join(pos_words))
        worksheet.write(row, 2, ", ".join(neg_words))
        worksheet.write(row, 3, s_norm)
        worksheet.write(row, 4, f_norm)

        rich = []

        for token in paragraph.split():
            clean = re.sub(r"[^\wçğıöşüÇĞİÖŞÜ']", "", token.lower())
            lemma = get_lemma_of_word(
                clean,
                fsm,
                disamb,
                transition_mak,
                transition_mek,
            )

            if lemma in pos_words:
                rich.extend([pos_fmt, token + " "])
            elif lemma in neg_words:
                rich.extend([neg_fmt, token + " "])
            else:
                rich.extend([normal_fmt, token + " "])

        if rich:
            worksheet.write_rich_string(row, 0, *rich)
        else:
            worksheet.write(row, 0, paragraph, normal_fmt)

        row += 1

    workbook.close()


# ===============================
# MULTIPROCESSING WRAPPER
# ===============================
def process_single_file(args):
    channel, txt_path, out_excel = args

    paragraphs = read_paragraphs_from_single_file(txt_path)
    build_excel_with_colors(paragraphs, out_excel)

    return txt_path


def iter_all_text_files(base_dir):
    for channel in os.listdir(base_dir):
        channel_path = os.path.join(base_dir, channel)
        if not os.path.isdir(channel_path):
            continue

        for txt_file in glob.glob(os.path.join(channel_path, "*.txt")):
            yield channel, txt_file


# ===============================
# MAIN
# ===============================
if __name__ == "__main__":

    BASE_DIR = r"C:\work\4th-Grade-Fall\CS401\DropboxBackUp\Ekonomi-Yapilanlar"
    OUT_DIR = r"C:\work\4th-Grade-Fall\CS401\ParagraphsSentiAnalysisExcel"

    os.makedirs(OUT_DIR, exist_ok=True)

    tasks = []

    for channel, txt_path in iter_all_text_files(BASE_DIR):
        file_name = os.path.splitext(os.path.basename(txt_path))[0]
        out_excel = os.path.join(OUT_DIR, f"{channel}_{file_name}.xlsx")
        tasks.append((channel, txt_path, out_excel))

    print(f">>> PARALLEL MODE: {len(tasks)} files")

    cpu_count = max(1, multiprocessing.cpu_count() - 1)

    with ProcessPoolExecutor(max_workers=cpu_count) as executor:
        futures = [executor.submit(process_single_file, t) for t in tasks]

        for future in as_completed(futures):
            try:
                txt_path = future.result()
                print(f"✔ Finished: {txt_path}")
            except Exception as e:
                print(f"✖ Error: {e}")

    print(">>> ALL FILES PROCESSED")
