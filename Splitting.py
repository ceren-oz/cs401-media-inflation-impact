import os
import glob
from MorphologicalAnalysis.FsmMorphologicalAnalyzer import FsmMorphologicalAnalyzer

fsm = FsmMorphologicalAnalyzer()


def split_sentences_by_verb(text):
    """
    Verb POS görüldüğünde direkt NOKTA koyar.
    Sonraki kelime büyük harf kontrolü YOKTUR.
    """
    words = text.split()
    result_words = []

    for i in range(len(words)):
        word = words[i]

        analysis = fsm.morphologicalAnalysis(word)

        if analysis.size() > 0:
            parse = analysis.getFsmParse(0)
            pos = parse.getPos()
        else:
            pos = None

        if pos == "VERB":
            result_words.append(word + ".")
        else:
            result_words.append(word)

    return " ".join(result_words)


def process_directory(base_path):
    """
    Verilen klasörü işler.
    İçindeki kanalları ve text dosyalarını bulur ve VERB tabanlı cümle ayırma uygular.
    Çıktıları yeni bir klasöre yazar.
    """

    # Çıktı klasörü adı
    output_path = base_path + "-Split"

    # Yeni çıktı klasörünü oluştur
    os.makedirs(output_path, exist_ok=True)

    # Haber kanallarını tarıyoruz
    for channel_folder in os.listdir(base_path):
        channel_path = os.path.join(base_path, channel_folder)

        if not os.path.isdir(channel_path):
            continue

        # Çıktıda kanal klasörünü oluştur
        output_channel_path = os.path.join(output_path, channel_folder)
        os.makedirs(output_channel_path, exist_ok=True)

        # Kanal klasöründeki tüm txt dosyaları
        txt_files = glob.glob(os.path.join(channel_path, "*.txt"))

        for file_path in txt_files:
            file_name = os.path.basename(file_path)

            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()

            # Verb tabanlı noktalama
            punctuated = split_sentences_by_verb(text)

            # Cümlelere ayır (nokta -> cümle sınırı)
            sentences = [s.strip() for s in punctuated.split(".") if s.strip()]

            # Çıkış dosya yolu
            output_file_path = os.path.join(output_channel_path, file_name)

            # Yaz
            with open(output_file_path, "w", encoding="utf-8") as out:
                for s in sentences:
                    out.write(s + "\n")

    print(f"Tamamlandı → {base_path} işlendi → Çıktı: {output_path}")


# -------------------------------------------------------------------------
# 3 Ana klasör için çalıştır
# -------------------------------------------------------------------------

paths = [
    r"C:\work\4th-Grade-Fall\CS401\DropboxBackUp\Ekonomi",
    r"C:\work\4th-Grade-Fall\CS401\DropboxBackUp\Ekonomi-Yapilanlar",
    r"C:\work\4th-Grade-Fall\CS401\DropboxBackUp\Ekonomi-Yapilmayanlar"
]

for p in paths:
    process_directory(p)
