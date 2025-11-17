import os
import glob
import pandas as pd
import re
from MorphologicalAnalysis.FsmMorphologicalAnalyzer import FsmMorphologicalAnalyzer


# --------------------------------------------------------
#  Kelime Normalize Fonksiyonu
# --------------------------------------------------------
def normalize(word, fsm):

    analysis = fsm.morphologicalAnalysis(word)
    if analysis.size() > 0:
        return word

    word_upper = word.upper()
    analysis_upper = fsm.morphologicalAnalysis(word_upper)
    if analysis_upper.size() > 0:
        return word_upper

    n = len(word)
    for i in range(1, n):

        root = word[:i]
        suffix = word[i:]

        if not root or not suffix:
            continue

        root_analysis = fsm.morphologicalAnalysis(root)
        if root_analysis.size() > 0:
            return root + "'" + suffix

        root_upper = root.upper()
        root_upper_analysis = fsm.morphologicalAnalysis(root_upper)
        if root_upper_analysis.size() > 0:
            return root_upper + "'" + suffix

    return word


# --------------------------------------------------------
#  Temizleme Fonksiyonu
# --------------------------------------------------------
def clean_word_keep_apostrophe(word):
    return re.sub(r"[^a-zA-ZçÇğĞıİöÖşŞüÜ']", "", word)


# --------------------------------------------------------
#  Ana Kod
# --------------------------------------------------------
base_path = r"C:\work\4th-Grade-Fall\CS401\DropboxBackUp\Ekonomi-Yapilmayanlar"

fsm = FsmMorphologicalAnalyzer()

results = []

window = 5  # çevreden alınacak kelime sayısı


for channel_folder in os.listdir(base_path):

    channel_path = os.path.join(base_path, channel_folder)
    if not os.path.isdir(channel_path):
        continue

    txt_files = glob.glob(os.path.join(channel_path, "*.txt"))

    for file_path in txt_files:

        file_name = os.path.basename(file_path)

        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()

        for line in lines:

            if not line.strip():
                continue

            words = line.split()

            for i, w in enumerate(words):

                w_clean = clean_word_keep_apostrophe(w)
                if not w_clean:
                    continue

                # --- FSM PARSE EDİYOR MU? ---
                analysis = fsm.morphologicalAnalysis(w_clean)

                if analysis.size() > 0:
                    continue  # kelime doğru → geç

                # --- normalize etmeyi dene ---
                normalized = normalize(w_clean, fsm)

                # normalize *gerçekten farklı sonuç üretmişse*
                if normalized != w_clean:

                    start = max(0, i - window)
                    end = min(len(words), i + window + 1)
                    context = " ".join(words[start:end])

                    results.append({
                        "Haber Kanalı": channel_folder,
                        "Dosya Adı": file_name,
                        "Yanlış Kelime": w_clean,
                        "Normalize Edilmiş": normalized,
                        "Bağlam": context,
                    })


# --------------------------------------------------------
# CSV Kaydet
# --------------------------------------------------------
df = pd.DataFrame(results)
df.to_csv("YANLIS_KELIMELER_NORMALIZE.csv", index=False, encoding="utf-8-sig")

print("Bitti! Toplam:", len(results), "YANLIŞ kelime bulundu ve normalize edildi.")
