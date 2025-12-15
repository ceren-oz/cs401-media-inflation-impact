import os
import re
import pandas as pd
from MorphologicalAnalysis.FsmMorphologicalAnalyzer import FsmMorphologicalAnalyzer


# --------------------------------------------------------
# Turkish-safe capitalization
# --------------------------------------------------------
def turkish_capitalize(word):
    if not word:
        return word

    first = word[0]
    rest = word[1:]

    if first == "i":
        first_cap = "İ"
    elif first == "ı":
        first_cap = "I"
    else:
        first_cap = first.upper()

    rest = rest.replace("I", "ı").replace("İ", "i").lower()
    return first_cap + rest


# --------------------------------------------------------
# Skip rules
# --------------------------------------------------------
def should_skip_word(word):
    if any(ch.isdigit() for ch in word):
        return True
    if len(word) >= 2 and word.isupper():
        return True
    if len(word) <= 2:
        return True
    return False


# --------------------------------------------------------
# FSM normalization checks
# --------------------------------------------------------
def fsm_normalize(word, fsm):
    if fsm.morphologicalAnalysis(word).size() > 0:
        return word

    word_cap = turkish_capitalize(word)
    if fsm.morphologicalAnalysis(word_cap).size() > 0:
        return word_cap

    word_upper = word.upper()
    if fsm.morphologicalAnalysis(word_upper).size() > 0:
        return word_upper

    # root + apostrophe + suffix check
    for i in range(1, len(word)):
        root = word[:i]
        suffix = word[i:]

        c1 = root + "'" + suffix
        if fsm.morphologicalAnalysis(c1).size() > 0:
            return c1

        c2 = turkish_capitalize(root) + "'" + suffix
        if fsm.morphologicalAnalysis(c2).size() > 0:
            return c2

        c3 = root.upper() + "'" + suffix
        if fsm.morphologicalAnalysis(c3).size() > 0:
            return c3

    return word


# --------------------------------------------------------
# Custom dictionary loader
# --------------------------------------------------------
def load_custom_dictionary(path):
    dictionary = set()
    if not os.path.exists(path):
        return dictionary

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            w = line.strip()
            if w:
                dictionary.add(w)

    return dictionary


# --------------------------------------------------------
# Check if word is in custom dictionary
# --------------------------------------------------------
def is_in_custom_dict(word, custom_dict):
    if word in custom_dict:
        return True

    if turkish_capitalize(word) in custom_dict:
        return True

    if word.upper() in custom_dict:
        return True

    if "'" in word:
        root = word.split("'")[0]
        if root in custom_dict or turkish_capitalize(root) in custom_dict:
            return True

    return False


# --------------------------------------------------------
# Extract incorrect words from a text
# --------------------------------------------------------
def extract_incorrect_words_from_text(text, fsm, custom_dict, file_name, channel_name):
    incorrect_records = []

    # --------------------------------------------------------
    # Remove %numbers (with or without apostrophe suffix) BEFORE regex
    # --------------------------------------------------------

    # Examples matched:
    # %40, %40'lar, %23.500, %23.500'de, %12'si
    clean_text = re.sub(r"%\d+(?:[\.,]\d+)*'(?:[A-Za-zÇĞİÖŞÜçğıöşü]+)?", " ", text)
    clean_text = re.sub(r"%\d+(?:[\.,]\d+)*", " ", clean_text)

    # Remove digit-apostrophe-suffix patterns:
    # 40'lar, 23.500'de, 2025'te, 12'si
    clean_text = re.sub(r"\d+(?:[\.,]\d+)*'(?:[A-Za-zÇĞİÖŞÜçğıöşü]+)", " ", clean_text)

    # Now extract normal words
    words = re.findall(r"[A-Za-zÇĞİÖŞÜçğıöşü']+", clean_text)

    for word in words:
        w = word.strip()

        if should_skip_word(w):
            continue

        # Custom dict → valid
        if is_in_custom_dict(w, custom_dict):
            continue

        normalized = fsm_normalize(w, fsm)

        # Normalization fixed the word → valid
        if normalized != w:
            continue

        # FSM accepts raw word → valid
        if fsm.morphologicalAnalysis(w).size() > 0:
            continue

        # Otherwise incorrect
        pos = text.find(w)
        context = text[max(0, pos - 30): pos + 30]

        incorrect_records.append({
            "incorrect_word": w,
            "file": file_name,
            "channel": channel_name,
            "context": context
        })

    return incorrect_records


# --------------------------------------------------------
# Process all channels + files
# --------------------------------------------------------
def process_all_channels(
    root_folder=r"C:\work\4th-Grade-Fall\CS401\DropboxBackUp\Ekonomi-Yapilanlar",
    custom_dict_path="custom_dictionary.txt",
    output_csv="incorrect_words_all_02.csv"
):
    fsm = FsmMorphologicalAnalyzer()
    custom_dict = load_custom_dictionary(custom_dict_path)

    all_records = []

    # Traverse each channel folder
    for channel in os.listdir(root_folder):
        channel_path = os.path.join(root_folder, channel)

        if not os.path.isdir(channel_path):
            continue

        # Process all text files inside the channel folder
        for file in os.listdir(channel_path):
            if not file.lower().endswith(".txt"):
                continue

            file_path = os.path.join(channel_path, file)

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    text = f.read()
            except:
                print(f"Could not read: {file_path}")
                continue

            recs = extract_incorrect_words_from_text(
                text=text,
                fsm=fsm,
                custom_dict=custom_dict,
                file_name=file,
                channel_name=channel
            )
            all_records.extend(recs)

    df = pd.DataFrame(all_records)
    df.to_csv(output_csv, index=False, encoding="utf-8")

    print(f"\n DONE — Incorrect words saved to {output_csv}")
    return df


# --------------------------------------------------------
# MAIN
# --------------------------------------------------------
if __name__ == "__main__":
    process_all_channels()
