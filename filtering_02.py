import os
import shutil

# Klasör yolları
base_path = r"C:\work\4th-Grade-Fall\CS401\DropboxBackUp"
ekonomi_path = os.path.join(base_path, "Ekonomi")
ekonomi_yapilmayan_path = os.path.join(base_path, "Ekonomi-Yapilmayanlar")
ekonomi_yapilan_path = os.path.join(base_path, "Ekonomi-Yapilanlar")

# Ekonomi-Yapilanlar klasörünü oluştur (yoksa)
os.makedirs(ekonomi_yapilan_path, exist_ok=True)

# Kelimeler
keywords = ["enflasyon", "zam"]

def read_text_file(filepath):
    try:
        with open(filepath, "r", encoding="utf-8-sig") as f:
            return f.read()
    except:
        pass

    try:
        with open(filepath, "r", encoding="cp1254") as f:
            return f.read()
    except:
        pass

    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


# 1. Ekonomi'de olup Ekonomi-Yapilmayanlar'da olmayan dosyaları kopyala
for channel in os.listdir(ekonomi_path):
    ekonomi_channel_path = os.path.join(ekonomi_path, channel)
    yapilmayan_channel_path = os.path.join(ekonomi_yapilmayan_path, channel)
    yapilan_channel_path = os.path.join(ekonomi_yapilan_path, channel)

    if not os.path.isdir(ekonomi_channel_path):
        continue

    os.makedirs(yapilan_channel_path, exist_ok=True)

    # Eğer Ekonomi-Yapilmayanlar'da kanal yoksa None olarak işarete gerek yok. Sadece kontrol yapacağız.
    channel_has_yapilmayan = os.path.exists(yapilmayan_channel_path)

    for file_name in os.listdir(ekonomi_channel_path):

        if file_name.lower() == "desktop.ini":
            continue

        ekonomi_file = os.path.join(ekonomi_channel_path, file_name)
        yapilan_file = os.path.join(yapilan_channel_path, file_name)

        if channel_has_yapilmayan:
            yapilmayan_file = os.path.join(yapilmayan_channel_path, file_name)
            file_exists_in_yapilmayan = os.path.exists(yapilmayan_file)
        else:
            file_exists_in_yapilmayan = False

        if not file_exists_in_yapilmayan:
            shutil.copy2(ekonomi_file, yapilan_file)


# 2. Yapilanlar klasöründeki dosyalarda sadece "enflasyon" ve "zam" geçen paragrafları bırak
for channel in os.listdir(ekonomi_yapilan_path):
    yapilan_channel_path = os.path.join(ekonomi_yapilan_path, channel)

    if not os.path.isdir(yapilan_channel_path):
        continue

    for file_name in os.listdir(yapilan_channel_path):

        if file_name.lower() == "desktop.ini":
            continue

        if not file_name.lower().endswith(".txt"):
            continue

        yapilan_file = os.path.join(yapilan_channel_path, file_name)
        text = read_text_file(yapilan_file)

        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        filtered_paragraphs = [p for p in paragraphs if any(k in p.lower() for k in keywords)]

        with open(yapilan_file, "w", encoding="utf-8") as f:
            f.write("\n\n".join(filtered_paragraphs))

print("✅ İşlem tamamlandı! Ekonomi-Yapilanlar klasöründe filtrelenmiş dosyalar hazır.")
