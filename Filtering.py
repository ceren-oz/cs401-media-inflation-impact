import os
import glob
import re

# Anahtar kelimeler (kök + ek halleri)
keywords = [r"\benflasyon\w*", r"\bzam\w*"]

# Ana klasör
base_path = r"C:\work\4th-Grade-Fall\CS401\DropboxBackUp\Ekonomi"

# Çıktı klasörü
output_dir = os.path.join(base_path, "Filtrelenmis_Haberler_Sadece_Kelimeler")
os.makedirs(output_dir, exist_ok=True)

def extract_keyword_blocks(lines, window=2):
    """
    Satır bazlı blok çıkarma:
    - Anahtar kelime geçen satırlar
    - Önceki ve sonraki 'window' satır eklenir
    - Yakın bloklar (<=5 satır) birleştirilir
    """
    matches = []
    indices = []

    # Anahtar kelimenin geçtiği satırları bul
    for i, line in enumerate(lines):
        lower_line = line.lower()
        if any(re.search(pattern, lower_line) for pattern in keywords):
            indices.append(i)

    if not indices:
        return matches

    # Yakın satırları birleştir (5 satırdan azsa tek blok)
    merged_blocks = []
    current_block = [indices[0]]
    for idx in indices[1:]:
        if idx - current_block[-1] <= 5:
            current_block.append(idx)
        else:
            merged_blocks.append(current_block)
            current_block = [idx]
    merged_blocks.append(current_block)

    # Her blok için bağlam satırlarını ekle
    for block in merged_blocks:
        start = max(0, block[0] - window)
        end = min(len(lines), block[-1] + window + 1)
        context = "\n".join(lines[start:end])
        matches.append(context)

    return matches

# Tüm haber kanallarını tara
for channel_folder in os.listdir(base_path):
    channel_path = os.path.join(base_path, channel_folder)
    if not os.path.isdir(channel_path):
        continue

    txt_files = glob.glob(os.path.join(channel_path, "*.txt"))
    for file_path in txt_files:
        with open(file_path, "r", encoding="utf-8") as f:
            # Satırları oku ve boşları çıkar
            lines = [l.strip() for l in f.readlines() if l.strip()]

        relevant_blocks = extract_keyword_blocks(lines, window=2)

        # Eğer blok varsa, kaydet
        if relevant_blocks:
            file_name = os.path.basename(file_path)
            output_path = os.path.join(output_dir, f"{channel_folder}_{file_name}")

            with open(output_path, "w", encoding="utf-8") as out:
                out.write("\n\n".join(relevant_blocks))

            print(f" {file_name}: {len(relevant_blocks)} blok bulundu ve kaydedildi.")

print("İşlem tamamlandı! Sadece ilgili kelime blokları kaydedildi.")
