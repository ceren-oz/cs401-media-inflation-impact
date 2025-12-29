import os
import re
import glob
import pandas as pd
from openpyxl import load_workbook
from openpyxl.cell.text import InlineFont
from openpyxl.cell.rich_text import TextBlock, CellRichText
import xlsxwriter


from openpyxl.cell.rich_text import TextBlock, CellRichText

from MorphologicalAnalysis.FsmMorphologicalAnalyzer import FsmMorphologicalAnalyzer
from MorphologicalDisambiguation.LongestRootFirstDisambiguation import LongestRootFirstDisambiguation
from Corpus.Sentence import Sentence
from MorphologicalAnalysis.Transition import Transition
from SentiNet.SentiLiteralNet import SentiLiteralNet

fsm = FsmMorphologicalAnalyzer()
disamb = LongestRootFirstDisambiguation()
senti_net = SentiLiteralNet()
transition_mak = Transition("mak")
transition_mek = Transition("mek")

BACK_VOWELS = set("aıou")
FRONT_VOWELS = set("eiöü")

def pick_infinitive_suffix(root):
    for ch in reversed(root):
        if ch in BACK_VOWELS:
            return "mak"
        if ch in FRONT_VOWELS:
            return "mek"
    return "mak"

def read_all_paragraphs(base_folder):
    paragraphs = []

    for channel in os.listdir(base_folder):
        channel_path = os.path.join(base_folder, channel)
        if not os.path.isdir(channel_path):
            continue

        for fp in glob.glob(os.path.join(channel_path, "*.txt")):
            with open(fp, "r", encoding="utf-8") as f:
                text = f.read().strip()

            chunks = re.split(r"\n\s*\n", text)
            for p in chunks:
                if p.strip():
                    paragraphs.append(p.strip())

    return paragraphs

def read_paragraphs_from_single_file(file_path):
    paragraphs = []

    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read().strip()

    chunks = re.split(r"\n\s*\n", text)
    for p in chunks:
        if p.strip():
            paragraphs.append(p.strip())

    return paragraphs


def analyze_paragraph(paragraph):
    analysis = fsm.robustMorphologicalAnalysis(Sentence(paragraph))
    parses = disamb.disambiguate(analysis)

    pos_words, neg_words = [], []
    pos_score, neg_score = 0.0, 0.0
    total_words = 0

    for parse in parses:
        root = parse.getWord().getName()
        pos = parse.getRootPos()

        if pos == "VERB":
            suffix = pick_infinitive_suffix(root)
            infinitive = (
                transition_mak.makeTransition(parse.getWord(), root, None)
                if suffix == "mak"
                else transition_mek.makeTransition(parse.getWord(), root, None)
            )
        else:
            infinitive = root

        try:
            literal = senti_net.getSentiLiteral(infinitive)
            p = float(literal.getPositiveScore())
            n = float(literal.getNegativeScore())
        except:
            p = n = 0.0

        if p > n:
            pos_words.append(infinitive)
        elif n > p:
            neg_words.append(infinitive)

        pos_score += p
        neg_score += n
        total_words += 1

    score_norm = (pos_score - neg_score) / max(total_words, 1)
    freq_norm = (len(pos_words) - len(neg_words)) / max(total_words, 1)

    return pos_words, neg_words, score_norm, freq_norm

def get_lemma_of_word(word: str):
    analysis = fsm.robustMorphologicalAnalysis(Sentence(word))
    parses = disamb.disambiguate(analysis)

    if not parses:
        return None

    parse = parses[0]
    root = parse.getWord().getName()
    pos = parse.getRootPos()

    if pos == "VERB":
        suffix = pick_infinitive_suffix(root)
        return (
            transition_mak.makeTransition(parse.getWord(), root, None)
            if suffix == "mak"
            else transition_mek.makeTransition(parse.getWord(), root, None)
        )

    return root



def build_excel_with_colors(paragraphs, out_excel):
    workbook = xlsxwriter.Workbook(out_excel)
    worksheet = workbook.add_worksheet("Sentiment")

    headers = [
        "haber",
        "pozitif kelimeler",
        "negatif kelimeler",
        "skor_normalize",
        "frekans_normalize"
    ]
    for col, h in enumerate(headers):
        worksheet.write(0, col, h)


    normal_fmt = workbook.add_format()
    pos_fmt = workbook.add_format({"font_color": "blue"})
    neg_fmt = workbook.add_format({"font_color": "red"})

    worksheet.set_column(0, 0, 90)
    worksheet.set_column(1, 2, 40)
    worksheet.set_column(3, 4, 20)

    row = 1

    for p in paragraphs:
        pos_words, neg_words, s_norm, f_norm = analyze_paragraph(p)


        worksheet.write(row, 1, ", ".join(pos_words))
        worksheet.write(row, 2, ", ".join(neg_words))
        worksheet.write(row, 3, s_norm)
        worksheet.write(row, 4, f_norm)

        rich = []
        for word in p.split():
            clean = re.sub(r"[^\wçğıöşüÇĞİÖŞÜ]", "", word.lower())
            lemma = get_lemma_of_word(clean)

            if lemma in pos_words:
                rich.extend([pos_fmt, word + " "])
            elif lemma in neg_words:
                rich.extend([neg_fmt, word + " "])
            else:
                rich.extend([normal_fmt, word + " "])

        worksheet.write_rich_string(row, 0, *rich)

        row += 1

    workbook.close()




if __name__ == "__main__":

    TEST_FILE = r"C:\work\4th-Grade-Fall\CS401\DropboxBackUp\Ekonomi-Yapilanlar\ATV\(controled) ATV20231223_atv Ana Haber ｜ 23 Aralık 2023.tr.txt"
    #OUT_EXCEL = r"C:\work\ATV_TEST_Sentiment.xlsx"
    OUT_EXCEL = r"C:\work\4th-Grade-Fall\CS401\ParagraphsSentiAnalysisExcel\ATV_TEST_Sentiment_2.xlsx"


    print(">>> TEST MODE: Single file processing started")

    paragraphs = read_paragraphs_from_single_file(TEST_FILE)
    print(f">>> Paragraph count: {len(paragraphs)}")

    build_excel_with_colors(paragraphs, OUT_EXCEL)

    print(">>> TEST MODE FINISHED – Excel created")

