import os
import glob
from MorphologicalAnalysis.FsmMorphologicalAnalyzer import FsmMorphologicalAnalyzer

fsm = FsmMorphologicalAnalyzer()


# -------------------------------------------------------
# 1) Tek kelime için en uygun parse'i seç
# -------------------------------------------------------
def choose_best_parse(word):
    analysis = fsm.morphologicalAnalysis(word)
    parse_count = analysis.size()

    if parse_count == 0:
        return "_"  # hiç parse yoksa placeholder

    parses = [analysis.getFsmParse(i) for i in range(parse_count)]

    # Öncelik: VERB → NOUN → ADJ → NUM → ilk parse
    for p in parses:
        if p.getPos() == "VERB":
            return str(p)
    for p in parses:
        if p.getPos() == "NOUN":
            return str(p)
    for p in parses:
        if p.getPos() == "ADJ":
            return str(p)
    for p in parses:
        if p.getPos() == "NUM":
            return str(p)

    # Hiçbiri değilse ilk parse
    return str(parses[0])


# -------------------------------------------------------
# 2) Bir dosyayı işleyip "kelime \t seçilmiş_parse" üret
# -------------------------------------------------------
def create_disambiguation_lines(text):
    sentences = text.split("\n")  # Day-2 sonrası her satır bir cümle

    output_lines = []

    for sent in sentences:
        tokens = sent.strip().split()
        if not tokens:
            continue

        output_lines.append("<S>")  # cümle başlangıcı

        for token in tokens:
            best_parse = choose_best_parse(token)
            output_lines.append(f"{token}\t{best_parse}")

        output_lines.append("</S>")
        output_lines.append("")  # boş satır ekleyerek formatı koru

    return output_lines


# -------------------------------------------------------
# 3) Klasördeki tüm kanal klasörlerini ve txt dosyalarını tarayıp Day-3 üret
# -------------------------------------------------------
def process_directory_day3(base_path):
    output_base = base_path + "-With-Selected-Parse"
    os.makedirs(output_base, exist_ok=True)

    # Base path altındaki her kanal klasörünü tarıyoruz
    for channel_name in os.listdir(base_path):
        channel_path = os.path.join(base_path, channel_name)
        if not os.path.isdir(channel_path):
            continue  # klasör değilse atla

        # Çıktı klasörünü kanal bazlı oluştur
        output_channel_path = os.path.join(output_base, channel_name)
        os.makedirs(output_channel_path, exist_ok=True)

        # Kanal klasöründeki tüm txt dosyaları
        txt_files = glob.glob(os.path.join(channel_path, "*.txt"))

        for file_path in txt_files:
            file_name = os.path.basename(file_path)

            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()

            disamb_lines = create_disambiguation_lines(text)

            out_file = os.path.join(output_channel_path, file_name)
            with open(out_file, "w", encoding="utf-8") as out:
                for line in disamb_lines:
                    out.write(line + "\n")

    print(f"Day-3 tamamlandı → {base_path} işlendi → Çıktı klasörü: {output_base}")


# -------------------------------------------------------------------------
# 3 klasör için çalıştır
# -------------------------------------------------------------------------
paths = [
    r"C:\work\4th-Grade-Fall\CS401\DropboxBackUp\Ekonomi-Split",
    r"C:\work\4th-Grade-Fall\CS401\DropboxBackUp\Ekonomi-Yapilanlar-Split",
    r"C:\work\4th-Grade-Fall\CS401\DropboxBackUp\Ekonomi-Yapilmayanlar-Split"
]

for p in paths:
    process_directory_day3(p)
