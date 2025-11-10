import sys
import os
import glob
import pandas as pd
import re
from MorphologicalAnalysis.FsmMorphologicalAnalyzer import FsmMorphologicalAnalyzer


# ------------------------
# Çıktıyı geçici olarak bastırmak için
# ------------------------
class DummyFile(object):
    def write(self, x): pass

    def flush(self): pass


# ------------------------
# Morfolojik analizör
# ------------------------
fsm = FsmMorphologicalAnalyzer()

# ------------------------
# Haber klasör yolu
# ------------------------
base_path = r"C:\work\4th-Grade-Fall\CS401\DropboxBackUp\Ekonomi-Yapilmayanlar"

# ------------------------
# Sonuçları saklamak için liste
# ------------------------
results = []

# Fsm çıktısını bastır
orig_stdout = sys.stdout
sys.stdout = DummyFile()

window_size = 5  # Yanlış kelimenin etrafındaki kelime sayısı

# Özel isim ekleri
proper_suffixes = [
    "da", "de", "ta", "te",
    "daki", "deki",
    "dan", "den", "tan", "ten",
    "ndan", "nden",
    "nın", "nin", "nun", "nün",
    "ın", "in", "un", "ün",
    "a", "e",
    "ya", "ye",
    "ı", "i", "u", "ü"
]

proper_names = set()  # özel isimler (küçük harf ile tutulacak)


# ------------------------
# Noktalama ve özel karakter temizleme
# ------------------------
def clean_word(word):
    return re.sub(r"[^a-zA-ZçÇğĞıİöÖşŞüÜ]", "", word)


def clean_word_keep_apostrophe(word):
    return re.sub(r"[^a-zA-ZçÇğĞıİöÖşŞüÜ']", "", word)


# ------------------------
# Özel isimleri çıkar
# ------------------------
def extract_proper_names(text):
    for w in text.split():
        w_clean = clean_word_keep_apostrophe(w)
        if len(w_clean) > 1:
            proper_names.add(w_clean.lower())  # tüm kelimeleri küçük harf olarak ekle


# ------------------------
# Özel isim ve ek kontrolleri
# ------------------------
def is_proper_name_with_suffix(word):
    cleaned = clean_word_keep_apostrophe(word)
    for suf in sorted(proper_suffixes, key=len, reverse=True):
        if cleaned.lower().endswith(suf):
            root = cleaned[:-len(suf)]
            if root.lower() in proper_names:
                return True
    return False


def is_acronym(word):
    return word.isupper() and len(word) > 1


# ------------------------
# 1. Tüm metinlerden özel isimleri çıkar
# ------------------------
for channel_folder in os.listdir(base_path):
    channel_path = os.path.join(base_path, channel_folder)
    if not os.path.isdir(channel_path):
        continue

    txt_files = glob.glob(os.path.join(channel_path, "*.txt"))
    for file_path in txt_files:
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
            extract_proper_names(text)

# ------------------------
# 2. Yanlış kelimeleri bul
# ------------------------
for channel_folder in os.listdir(base_path):
    channel_path = os.path.join(base_path, channel_folder)
    if not os.path.isdir(channel_path):
        continue

    txt_files = glob.glob(os.path.join(channel_path, "*.txt"))
    for file_path in txt_files:
        file_name = os.path.basename(file_path)
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()

        lines = text.splitlines()
        for line in lines:
            line = line.strip()
            if not line:
                continue

            words = line.split()
            cleaned_words = [clean_word_keep_apostrophe(w) for w in words]

            for i, word in enumerate(cleaned_words):
                if not word:
                    continue

                fsmParseList = fsm.morphologicalAnalysis(word)

                # FSM boşsa bile özel isim veya acronym ise affet
                if fsmParseList.size() == 0:
                    if is_proper_name_with_suffix(word) or is_acronym(words[i]):
                        continue

                    start = max(0, i - window_size)
                    end = min(len(words), i + window_size + 1)
                    context = " ".join(words[start:end])

                    results.append({
                        "Haber Kanalı": channel_folder,
                        "Dosya Adı": file_name,
                        "Yanlış Yazılmış Kelime": word,
                        "Bağlam": context
                    })

# ------------------------
# stdout'u geri al
# ------------------------
sys.stdout = orig_stdout

# ------------------------
# CSV olarak kaydet
# ------------------------
df = pd.DataFrame(results)
df.to_csv("yanlis_kelimeler_temiz-03.csv", index=False, encoding="utf-8-sig")
print(f"{len(results)} adet yanlış yazılmış kelime bulundu ve CSV'ye kaydedildi.")
