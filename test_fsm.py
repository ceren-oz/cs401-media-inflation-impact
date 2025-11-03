import sys
import os
import glob
import pandas as pd
from MorphologicalAnalysis.FsmMorphologicalAnalyzer import FsmMorphologicalAnalyzer

# Suppress standard output temporarily
class DummyFile(object):
    def write(self, x): pass
    def flush(self): pass

# Morfolojik analizör
fsm = FsmMorphologicalAnalyzer()

# Haber klasör yolu
base_path = r"C:\work\4th-Grade-Fall\CS401\DropboxBackUp\Ekonomi-Yapilmayanlar"

# Sonuçları saklamak için liste
results = []

orig_stdout = sys.stdout
sys.stdout = DummyFile()  # suppress analyzer output


window_size = 5  # Number of words before/after the wrong word to include as context

for channel_folder in os.listdir(base_path):
    channel_path = os.path.join(base_path, channel_folder)
    if not os.path.isdir(channel_path):
        continue

    txt_files = glob.glob(os.path.join(channel_path, "*.txt"))
    for file_path in txt_files:
        file_name = os.path.basename(file_path)
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()

        # Split by lines instead of sentences (better for transcriptions)
        lines = text.splitlines()
        for line in lines:
            line = line.strip()
            if not line:
                continue

            words = line.split()
            for i, word in enumerate(words):
                fsmParseList = fsm.morphologicalAnalysis(word)
                if fsmParseList.size() == 0:
                    # Sliding window context
                    start = max(0, i - window_size)
                    end = min(len(words), i + window_size + 1)
                    context = " ".join(words[start:end])
                    results.append({
                        "Haber Kanalı": channel_folder,
                        "Dosya Adı": file_name,
                        "Yanlış Yazılmış Kelime": word,
                        "Bağlam": context
                    })

sys.stdout = orig_stdout  # restore printing

# Save results as a readable CSV
df = pd.DataFrame(results)
df.to_csv("yanlis_kelimeler.csv", index=False, encoding="utf-8")
print("Yanlış yazılmış kelimeler ve bağlamları CSV'ye kaydedildi.")