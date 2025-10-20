"""
News Text Analysis: Word Cloud and Vocabulary Extraction
For analyzing media news impact on household inflation expectations

LIBRARIES EXPLAINED:
-------------------
1. pandas (pd): Works with data in table format (like Excel)
2. Counter: Counts how many times each item appears in a list
3. re: Regular expressions - finds/replaces text patterns
4. WordCloud: Creates the visual word cloud image
5. matplotlib.pyplot (plt): Creates charts and visualizations
6. nltk: Natural Language Toolkit - processes human language
   - stopwords: Common words like 'the', 'is', 'and'
   - word_tokenize: Splits text into individual words
"""

import pandas as pd
from collections import Counter
import re
from wordcloud import WordCloud
import matplotlib.pyplot as plt

# For text preprocessing
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize



class NewsTextAnalyzer:
    """Analyze news transcripts for vocabulary and word frequency"""

    def __init__(self, remove_stopwords=True, min_word_length=3, language='turkish'):
        """
        Initialize the analyzer (this runs when you create the analyzer)

        WHAT IS A CLASS?
        Think of it as a toolbox. The class contains all the tools (functions)
        you need for text analysis in one organized place.

        Parameters:
        - remove_stopwords: Should we remove common words like 'the', 'is', 'at'?
                           (True = yes, False = no)
        - min_word_length: Ignore words shorter than this (3 means ignore 'is', 'at')

        WHAT IS self?
        'self' refers to this specific toolbox instance. When you write
        self.min_word_length = 3, you're storing the value 3 in THIS toolbox
        so all tools inside can access it.
        """
        # Store settings in this toolbox
        self.remove_stopwords = remove_stopwords
        self.min_word_length = min_word_length

        # If we want to remove stopwords, load the list
        if remove_stopwords:
            # Get English stopwords from NLTK (words like: the, is, at, which, on)
            self.stop_words = set(stopwords.words('turkish'))

            # Add more words commonly found in news that don't add meaning
            # update() adds multiple items to a set at once
            turkish_news_stopwords = [

                # === Olumsuzluk ve Varlık Kelimeleri ===
                'değil', 'var', 'vardı', 'yok',

                # === Duraksama ve Dolgu (Filler) Kelimeleri ===
                'eee', 'tabii', 'peki', 'evet', 'zaten', 'hatta', 'artık',
                'efendim', 'hani',

                # === Belirsizlik, Sınırlama ve Vurgu İfadeleri ===
                'belli', 'işte', 'sadece', 'diğer', 'yine', 'böyle', 'şöyle', 'öyle', 'özellikle',

                # === Zamirler (Kişi, İşaret, Belirsiz) ===
                'ben', 'bana', 'biz', 'bizim', 'bizlerle', 'bize',
                'sen', 'size', 'onu', 'onun', 'onlar',
                'bunlar', 'buna', 'bunu', 'bunun', 'bundan', 'kendi',

                # === Yer ve Zaman Belirleyicileri ===
                'burada', 'orada', 'yer', 'yıl', 'gün', 'bugün', 'saat', 'şimdi', 'yarın',
                'hafta', 'zaman', 'son', 'arasında', 'sonra', 'önce', 'sırada',

                # === Miktar / Yoğunluk Belirleyicileri ===
                'biraz', 'bir', 'iki',

                # === Bağlaçlar ve Edatlar ===
                'dolayısıyla', 'göre', 'karşı', 'gibi', 'şekilde', 'kadar', 'ancak', 'çünkü',

                # === Fiil Türevleri ve Yardımcı Fiiller ===
                'olan', 'olarak', 'oldu', 'olacak', 'olmuş', 'oluyor',
                'etti', 'eden', 'edecek', 'ediyor', 'yapan', 'yapılan', 'yapıldı', 'yaptığı',
                'geldi', 'geliyor', 'olsun',

                # === Haber / Açıklama Kalıplarında Geçen Fiiller ===
                'dedi', 'diyor', 'söyledi', 'belirtti', 'açıkladı', 'ifade',

                # === Diğer ===
                'devam'
            ]

            self.stop_words.update(turkish_news_stopwords)
        else:
            # Empty set = no stopwords to remove
            self.stop_words = set()

    def preprocess_text(self, text):
        """
        Clean and preprocess text - this is the CORE cleaning function

        WHY PREPROCESSING?
        Raw text has problems: capitals, punctuation, common words
        "The price is $50!" and "price" should be treated as the same word

        Parameters:
        - text: Raw text string (e.g., "The inflation rate is 5%!")

        Returns:
        - List of cleaned words (e.g., ['inflation', 'rate'])

        STEP BY STEP EXAMPLE:
        Input: "The Inflation rate is 5%!"
        After lowercase: "the inflation rate is 5%!"
        After removing special chars: "the inflation rate is "
        After tokenizing: ['the', 'inflation', 'rate', 'is']
        After filtering: ['inflation', 'rate']
        """

        # STEP 1: Convert everything to lowercase
        # "Inflation" and "inflation" should be the same word
        text = text.lower()

        # STEP 2: Remove special characters and numbers
        # re.sub() = "substitute" (find and replace)
        # r'[^a-zA-Z\s]' means: replace anything that is NOT a letter or space
        # '' means: replace with nothing (delete it)
        # Example: "price is $5!" becomes "price is "
        text = re.sub(r'[^a-zA-ZığüşöçĞÜŞÖÇİ\s]', '', text)

        # STEP 3: Split text into individual words (tokenization)
        # "inflation rate is high" becomes ['inflation', 'rate', 'is', 'high']
        tokens = word_tokenize(text)

        # STEP 4: Filter out unwanted words
        # This is a "list comprehension" - a compact way to filter a list
        # Read it as: "keep each word IF it passes both conditions"
        tokens = [
            word for word in tokens  # For each word in tokens
            if len(word) >= self.min_word_length  # Condition 1: long enough
               and word not in self.stop_words  # Condition 2: not a stopword
        ]

        return tokens

    def extract_vocabulary(self, texts):
        """
        Extract unique vocabulary from all texts
        THIS IS YOUR "VOCABULARY" TASK

        WHAT IS VOCABULARY?
        All unique words that appear across all your news transcripts
        If "inflation" appears 100 times, it only counts once in vocabulary

        Parameters:
        - texts: Can be a single text string OR a list of texts
                 Example: ["text from channel 1", "text from channel 2"]

        Returns:
        - Sorted list of unique words (alphabetically ordered)

        EXAMPLE:
        Input: ["Inflation is rising", "Prices are rising rapidly"]
        After cleaning: ['inflation', 'rising', 'prices', 'rising', 'rapidly']
        Vocabulary (unique): ['inflation', 'prices', 'rapidly', 'rising']
        """

        # Handle if someone passes a single string instead of a list
        # isinstance() checks "is this variable of this type?"
        if isinstance(texts, str):
            texts = [texts]  # Convert single string to list with one item

        # set() is a data structure that automatically keeps only unique items
        # If you add 'inflation' 100 times, the set still has just one 'inflation'
        vocabulary = set()

        # Process each text document
        for text in texts:
            # Clean the text and get list of words
            tokens = self.preprocess_text(text)

            # Add all words to vocabulary set
            # update() adds multiple items at once
            # set automatically ignores duplicates
            vocabulary.update(tokens)

        # sorted() arranges alphabetically: ['apple', 'banana', 'cherry']
        return sorted(vocabulary)

    def get_word_frequencies(self, texts):
        """
        Count how many times each word appears
        THIS CREATES THE DATA FOR YOUR WORD CLOUD

        WHY WORD FREQUENCIES?
        To make word cloud, we need to know: which words appear most often?
        Most frequent words appear BIGGER in the cloud

        Parameters:
        - texts: List of text strings or single string

        Returns:
        - Counter object (like a dictionary: {word: count})
          Example: Counter({'inflation': 45, 'price': 32, 'economy': 28})

        EXAMPLE:
        Input: ["Inflation rising", "Prices rising"]
        After cleaning: ['inflation', 'rising', 'prices', 'rising']
        Frequencies: Counter({'rising': 2, 'inflation': 1, 'prices': 1})
        """

        # Handle single string input
        if isinstance(texts, str):
            texts = [texts]

        # all_tokens will store every word from every document
        # This WILL have duplicates (we want to count them!)
        all_tokens = []

        # Process each document
        for text in texts:
            tokens = self.preprocess_text(text)  # Clean and split
            all_tokens.extend(tokens)  # extend() adds all items from tokens

        # Counter() automatically counts each item
        # ['a', 'b', 'a', 'c'] becomes Counter({'a': 2, 'b': 1, 'c': 1})
        return Counter(all_tokens)

    def create_word_cloud(self, texts, width=800, height=400,
                          max_words=100, background_color='white',
                          colormap='viridis', save_path=None):
        """
        Create and display word cloud

        Parameters:
        - texts: List of text strings or single string
        - width, height: Dimensions of the word cloud
        - max_words: Maximum number of words to display
        - background_color: Background color
        - colormap: Color scheme (viridis, plasma, inferno, magma, etc.)
        - save_path: Path to save the image (optional)

        Returns:
        - WordCloud object
        """
        if isinstance(texts, str):
            texts = [texts]

        # Combine all texts
        combined_text = ' '.join(texts)

        # Create word cloud
        wc = WordCloud(
            width=width,
            height=height,
            max_words=max_words,
            background_color=background_color,
            colormap=colormap,
            stopwords=self.stop_words,
            collocations=False,  # Avoid repeated phrases
            min_word_length=self.min_word_length
        ).generate(combined_text)

        # Display
        plt.figure(figsize=(width / 100, height / 100))
        plt.imshow(wc, interpolation='bilinear')
        plt.axis('off')
        plt.title('Word Cloud - News Transcripts 2024', fontsize=16, pad=20)
        plt.tight_layout(pad=0)

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Word cloud saved to: {save_path}")

        plt.show()

        return wc


# ==============================================================================
# EXAMPLE USAGE
# ==============================================================================

if __name__ == "__main__":
    import glob
    import os

    # ========================================================================
    # ADIM 1: KLASÖR YAPISINI TANIMLAMA
    # ========================================================================

    # Ana klasör yolu - SİZİN YOLUNUZ
    base_path = r"C:\work\4th-Grade-Fall\CS401\DropboxBackUp\Ekonomi"

    # Çıktılar için klasör oluştur (wordcloud'lar ve CSV'ler için)
    output_dir = "output"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"✓ '{output_dir}' klasörü oluşturuldu")

    # ========================================================================
    # ADIM 2: ANALYZER'I BAŞLAT
    # ========================================================================

    print("\n" + "=" * 70)
    print("TÜRK HABER KANALLARI - WORD CLOUD ANALİZİ")
    print("=" * 70)

    analyzer = NewsTextAnalyzer(
        remove_stopwords=True,
        min_word_length=3,
        language='turkish'
    )

    # ========================================================================
    # ADIM 3: HER BİR HABER KANALI İÇİN WORD CLOUD OLUŞTUR
    # ========================================================================

    # Ekonomi klasörü altındaki tüm alt klasörleri bul (her biri bir kanal)
    channel_folders = [f for f in os.listdir(base_path)
                       if os.path.isdir(os.path.join(base_path, f))]

    print(f"\n✓ Bulunan haber kanalları: {len(channel_folders)}")
    for channel in channel_folders:
        print(f"  - {channel}")

    # Her kanal için işlem yap
    all_channels_data = {}  # Tüm kanalların verilerini sakla

    for channel_name in channel_folders:
        print("\n" + "=" * 70)
        print(f"İŞLENİYOR: {channel_name}")
        print("=" * 70)

        # Bu kanalın klasör yolu
        channel_path = os.path.join(base_path, channel_name)

        # Bu klasördeki tüm .txt dosyalarını bul
        txt_files = glob.glob(os.path.join(channel_path, "*.txt"))

        print(f"Bulunan metin dosyası sayısı: {len(txt_files)}")

        if len(txt_files) == 0:
            print(f"⚠ {channel_name} için metin dosyası bulunamadı, atlanıyor...")
            continue

        # Tüm metinleri oku
        channel_texts = []
        for txt_file in txt_files:
            try:
                with open(txt_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if content.strip():  # Boş değilse ekle
                        channel_texts.append(content)
            except Exception as e:
                print(f"  ⚠ Dosya okunamadı {os.path.basename(txt_file)}: {e}")

        print(f"✓ Başarıyla okunan dosya: {len(channel_texts)}")

        if len(channel_texts) == 0:
            print(f"⚠ {channel_name} için geçerli metin bulunamadı, atlanıyor...")
            continue

        # Kelime dağarcığı çıkar
        vocabulary = analyzer.extract_vocabulary(channel_texts)
        print(f"✓ Kelime dağarcığı boyutu: {len(vocabulary)} benzersiz kelime")

        # Kelime sıklıklarını hesapla
        word_freq = analyzer.get_word_frequencies(channel_texts)
        print(f"✓ Toplam kelime sayısı: {sum(word_freq.values())}")

        # En sık kullanılan 10 kelimeyi göster
        print(f"\nEn sık kullanılan 10 kelime:")
        for word, count in word_freq.most_common(10):
            print(f"  {word:20s}: {count:4d}")

        # Kelime sıklıklarını CSV'ye kaydet
        freq_df = pd.DataFrame(word_freq.most_common(),
                               columns=['kelime', 'sıklık'])
        csv_filename = os.path.join(output_dir, f"{channel_name}_frequencies.csv")
        freq_df.to_csv(csv_filename, index=False, encoding='utf-8-sig')
        print(f"\n✓ Kelime sıklıkları kaydedildi: {csv_filename}")

        # Kelime dağarcığını kaydet
        vocab_filename = os.path.join(output_dir, f"{channel_name}_vocabulary.txt")
        with open(vocab_filename, 'w', encoding='utf-8') as f:
            for word in vocabulary:
                f.write(word + '\n')
        print(f"✓ Kelime dağarcığı kaydedildi: {vocab_filename}")

        # Word Cloud oluştur
        wordcloud_filename = os.path.join(output_dir, f"{channel_name}_wordcloud.png")
        print(f"\n📊 Word cloud oluşturuluyor...")

        wc = analyzer.create_word_cloud(
            channel_texts,
            width=1600,
            height=800,
            max_words=150,
            colormap='RdYlBu_r',
            save_path=wordcloud_filename#optional, not given for now
        )

        print(f"✓ Word cloud kaydedildi: {wordcloud_filename}")

        # Bu kanalın verisini sakla (karşılaştırma için)
        all_channels_data[channel_name] = {
            'texts': channel_texts,
            'vocabulary': vocabulary,
            'word_freq': word_freq,
            'file_count': len(txt_files)
        }

    # ========================================================================
    # ADIM 4: TÜM KANALLAR İÇİN BİRLEŞİK ANALİZ
    # ========================================================================

    print("\n\n" + "=" * 70)
    print("TÜM KANALLAR - BİRLEŞİK ANALİZ")
    print("=" * 70)

    # Tüm metinleri birleştir
    all_texts = []
    for channel_data in all_channels_data.values():
        all_texts.extend(channel_data['texts'])

    if len(all_texts) > 0:
        # Genel kelime dağarcığı
        all_vocabulary = analyzer.extract_vocabulary(all_texts)
        print(f"\n✓ Toplam benzersiz kelime (tüm kanallar): {len(all_vocabulary)}")

        # Genel kelime sıklıkları
        all_word_freq = analyzer.get_word_frequencies(all_texts)
        print(f"✓ Toplam kelime sayısı (tüm kanallar): {sum(all_word_freq.values())}")

        print(f"\nTüm kanallarda en sık kullanılan 20 kelime:")
        for word, count in all_word_freq.most_common(20):
            print(f"  {word:20s}: {count:5d}")

        # Genel CSV kaydet
        all_freq_df = pd.DataFrame(all_word_freq.most_common(),
                                   columns=['kelime', 'sıklık'])
        all_csv = os.path.join(output_dir, "ALL_CHANNELS_frequencies.csv")
        all_freq_df.to_csv(all_csv, index=False, encoding='utf-8-sig')
        print(f"\n✓ Genel kelime sıklıkları kaydedildi: {all_csv}")

        # Genel word cloud
        all_wordcloud = os.path.join(output_dir, "ALL_CHANNELS_wordcloud.png")
        print(f"\n📊 Genel word cloud oluşturuluyor...")
        analyzer.create_word_cloud(
            all_texts,
            width=1920,
            height=1080,
            max_words=200,
            colormap='RdYlBu_r',
            save_path=all_wordcloud#optional, not given for now
        )
        print(f"✓ Genel word cloud kaydedildi: {all_wordcloud}")

    # ========================================================================
    # ADIM 5: ÖZET RAPOR
    # ========================================================================

    print("\n\n" + "=" * 70)
    print("ANALİZ ÖZET RAPORU")
    print("=" * 70)

    summary_data = []
    for channel, data in all_channels_data.items():
        summary_data.append({
            'Kanal': channel,
            'Dosya Sayısı': data['file_count'],
            'Benzersiz Kelime': len(data['vocabulary']),
            'Toplam Kelime': sum(data['word_freq'].values())
        })

    summary_df = pd.DataFrame(summary_data)
    print("\n" + summary_df.to_string(index=False))

    # Özet raporu kaydet
    summary_csv = os.path.join(output_dir, "SUMMARY_REPORT.csv")
    summary_df.to_csv(summary_csv, index=False, encoding='utf-8-sig')
    print(f"\n✓ Özet rapor kaydedildi: {summary_csv}")

    # Enflasyon kelimeleri analizi
    print("\n" + "=" * 70)
    print("ENFLASYON KELİMELERİ ANALİZİ (Tüm Kanallar)")
    print("=" * 70)

    inflation_keywords = ['enflasyon', 'fiyat', 'ücret', 'maaş', 'ekonomi',
                          'tüketici', 'merkez', 'banka', 'faiz', 'artış',
                          'yüksek', 'düşük', 'oran', 'gıda', 'enerji',
                          'tüfe', 'üfe', 'kur', 'döviz', 'büyüme']

    if len(all_texts) > 0:
        print("\nAnahtar kelimelerin görünme sıklığı:")
        inflation_counts = []
        for keyword in inflation_keywords:
            if keyword in all_word_freq:
                count = all_word_freq[keyword]
                print(f"  {keyword:15s}: {count:5d} kez")
                inflation_counts.append({'Kelime': keyword, 'Sıklık': count})
            else:
                print(f"  {keyword:15s}: bulunmadı")

        # Enflasyon kelimeleri raporunu kaydet
        if inflation_counts:
            inflation_df = pd.DataFrame(inflation_counts)
            inflation_csv = os.path.join(output_dir, "INFLATION_KEYWORDS.csv")
            inflation_df.to_csv(inflation_csv, index=False, encoding='utf-8-sig')
            print(f"\n✓ Enflasyon kelimeleri raporu: {inflation_csv}")

    print("\n" + "=" * 70)
    print("✓✓✓ TÜM ANALİZLER TAMAMLANDI! ✓✓✓")
    print("=" * 70)
    print(f"\nTüm çıktılar '{output_dir}' klasöründe:")
    print(f"  - Her kanal için word cloud (PNG)")
    print(f"  - Her kanal için kelime sıklıkları (CSV)")
    print(f"  - Her kanal için kelime dağarcığı (TXT)")
    print(f"  - Genel word cloud ve analizler")
    print(f"  - Özet rapor ve enflasyon analizi")
    print("=" * 70)