import os
import re
import pandas as pd
from concurrent.futures import ProcessPoolExecutor
from MorphologicalAnalysis.FsmMorphologicalAnalyzer import FsmMorphologicalAnalyzer




# ========================================================
# Turkish-safe capitalization
# ========================================================
def turkish_capitalize(word: str) -> str:
    if not word:
        return word

    first = word[0]
    rest = word[1:]

    if first == "i":
        first = "İ"
    elif first == "ı":
        first = "I"
    else:
        first = first.upper()

    rest = rest.replace("I", "ı").replace("İ", "i").lower()
    return first + rest

def is_acronym_with_suffix(word: str) -> bool:
    return bool(re.match(r"^[A-ZÇĞİÖŞÜ]{2,}'[a-zçğıöşü]+$", word))


# ========================================================
# Skip rules
# ========================================================
def should_skip_word(word: str) -> bool:
    return (
        any(ch.isdigit() for ch in word) or
        (len(word) >= 2 and word.isupper()) or
        len(word) <= 2
    )

def normalize_unicode(text: str) -> str:
    return re.sub(r"[\u00AD\u200B\u200C\u200D\uFEFF]", "", text)

# ========================================================
# FSM normalization checks
# ========================================================
def fsm_normalize(word: str, fsm: FsmMorphologicalAnalyzer) -> str:
    if fsm.morphologicalAnalysis(word).size() > 0:
        return word

    for variant in (
        turkish_capitalize(word),
        word.upper()
    ):
        if fsm.morphologicalAnalysis(variant).size() > 0:
            return variant

    # Apostrophe variants
    for i in range(1, len(word)):
        root, suffix = word[:i], word[i:]
        for variant in (
            f"{root}'{suffix}",
            f"{turkish_capitalize(root)}'{suffix}",
            f"{root.upper()}'{suffix}",
        ):
            if fsm.morphologicalAnalysis(variant).size() > 0:
                return variant

    return word


# ========================================================
# Custom dictionary
# ========================================================
def load_custom_dictionary(path: str) -> set:
    dictionary = set()
    if not os.path.exists(path):
        return dictionary

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            entry = line.strip()
            if not entry:
                continue

            dictionary.add(entry)

            # 🔹 If multi-word name, also add last token
            if " " in entry:
                dictionary.add(entry.split()[-1])

    return dictionary



def is_in_custom_dict(word: str, custom_dict: set) -> bool:
    candidates = {
        word,
        turkish_capitalize(word),
        word.upper(),
        word.split("'")[0] if "'" in word else ""
    }
    return any(c in custom_dict for c in candidates)

def init_worker(custom_dict_path):
    global fsm_global, custom_dict_global
    fsm_global = FsmMorphologicalAnalyzer()
    custom_dict_global = load_custom_dictionary(custom_dict_path)

# ========================================================
# Incorrect word extraction
# ========================================================
def extract_incorrect_words(
    text: str,
    fsm: FsmMorphologicalAnalyzer,
    custom_dict: set,
    file_name: str,
    channel_name: str
) -> list[dict]:

    records = []

    # ============================
    # 🔹 ADD HERE (VERY IMPORTANT)
    # ============================
    text = normalize_unicode(text)
    text = re.sub(r"\s+", " ", text)

    # Remove percentage & numeric forms
    clean_text = re.sub(r"%\d+(?:[\.,]\d+)*'(?:[A-Za-zÇĞİÖŞÜçğıöşü]+)?", " ", text)
    clean_text = re.sub(r"%\d+(?:[\.,]\d+)*", " ", clean_text)
    clean_text = re.sub(r"\d+(?:[\.,]\d+)*'(?:[A-Za-zÇĞİÖŞÜçğıöşü]+)", " ", clean_text)

    words = re.findall(r"[A-Za-zÇĞİÖŞÜçğıöşü']+", clean_text)

    for w in words:

        if is_acronym_with_suffix(w):
            continue

        if should_skip_word(w):
            continue

        if is_in_custom_dict(w, custom_dict):
            continue

        normalized = fsm_normalize(w, fsm)
        if normalized != w:
            continue

        if fsm.morphologicalAnalysis(w).size() > 0:
            continue

        pos = text.find(w)
        context = text[max(0, pos - 40): pos + 40]

        records.append({
            "Haber kanalı": channel_name,
            "Dosya adı": file_name,
            "Yanlış yazılmış kelime": w,
            "Bağlam": context.strip()
        })

    return records


def process_single_file(args):
    file_path, channel = args
    file_name = os.path.basename(file_path)

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
    except Exception:
        return []

    return extract_incorrect_words(
        text=text,
        fsm=fsm_global,
        custom_dict=custom_dict_global,
        file_name=file_name,
        channel_name=channel
    )


# ========================================================
# Main processing
# ========================================================
def process_all_channels(
    root_folder: str,
    custom_dict_path: str,
    output_excel: str,
    max_workers: int = 4
):
    tasks = []

    # Collect tasks
    for channel in os.listdir(root_folder):
        channel_path = os.path.join(root_folder, channel)
        if not os.path.isdir(channel_path):
            continue

        for file in os.listdir(channel_path):
            if file.lower().endswith(".txt"):
                tasks.append((
                    os.path.join(channel_path, file),
                    channel
                ))

    all_records = []

    # Parallel execution
    with ProcessPoolExecutor(
        max_workers=max_workers,
        initializer=init_worker,
        initargs=(custom_dict_path,)
    ) as executor:
        for result in executor.map(process_single_file, tasks):
            all_records.extend(result)

    df = pd.DataFrame(all_records)
    # sort for clean output
    df.sort_values(
        by=["Haber kanalı", "Dosya adı", "Yanlış yazılmış kelime"],
        inplace=True
    )

    # ================= Excel output =================
    with pd.ExcelWriter(output_excel, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Yanlış Kelimeler")

        ws = writer.sheets["Yanlış Kelimeler"]
        ws.column_dimensions["A"].width = 20
        ws.column_dimensions["B"].width = 35
        ws.column_dimensions["C"].width = 28
        ws.column_dimensions["D"].width = 70

        for cell in ws["D"]:
            cell.alignment = cell.alignment.copy(wrap_text=True)


    print(f"\n✅ DONE — Excel file created:\n{output_excel}")
    return df


# ========================================================
# MAIN
# ========================================================
if __name__ == "__main__":
    process_all_channels(
        root_folder=r"C:\work\4th-Grade-Fall\CS401\DropboxBackUp\Ekonomi-Yapilanlar",
        custom_dict_path="custom_dictionary.txt",
        output_excel="yanlis_kelimeler-03.xlsx",
        max_workers = 4
    )
