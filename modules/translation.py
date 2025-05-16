import boto3
import json
import time

from datetime import datetime


class AWSTranslator:
    def __init__(self, region_name=None, aws_access_key=None, aws_secret_key=None, supported_languages=None):
        """
        Initialise le traducteur AWS.

        :param region_name: Région AWS à utiliser
        :param aws_access_key: Clé d'accès AWS
        :param aws_secret_key: Clé secrète AWS
        :param supported_languages: Liste des langues cibles supportées
        """
        # Configuration du client AWS Translate
        if aws_access_key and aws_secret_key and region_name:
            self.translate_client = boto3.client(
                'translate',
                region_name=region_name,
                aws_access_key_id=aws_access_key,
                aws_secret_access_key=aws_secret_key
            )
        elif region_name:
            self.translate_client = boto3.client('translate', region_name=region_name)
        else:
            self.translate_client = boto3.client('translate')

        # Langues par défaut si non spécifiées
        if supported_languages is None:
            self.supported_languages = {
                'en': 'English',
                'es': 'Spanish',
                'de': 'German',
                'it': 'Italian',
                'pt': 'Portuguese',
                'nl': 'Dutch',
                'ar': 'Arabic',
                'zh': 'Chinese',
                'ru': 'Russian'
            }
        else:
            self.supported_languages = supported_languages

    def translate_text(self, text, source_lang="fr", target_lang="en"):
        """
        Traduit un texte d'une langue source vers une langue cible.

        :param text: Texte à traduire
        :param source_lang: Code de langue source (ISO 639-1)
        :param target_lang: Code de langue cible (ISO 639-1)
        :return: Texte traduit
        """
        if not text or text.isspace():
            return ""

        start_time = time.time()

        try:
            response = self.translate_client.translate_text(
                Text=text,
                SourceLanguageCode=source_lang,
                TargetLanguageCode=target_lang
            )

            translated_text = response['TranslatedText']
            elapsed_time = time.time() - start_time

            print(f"Traduction [{source_lang} → {target_lang}]: {elapsed_time:.2f}s")
            return translated_text

        except Exception as e:
            print(f"Erreur de traduction: {str(e)}")
            return f"ERREUR: {str(e)}"

    def translate_to_all(self, text, source_lang="fr"):
        translations = {source_lang: text}

        # Compte le nombre de caractères à traduire
        char_count = len(text) * len(self.supported_languages) - len(text)  # Soustraction du texte original
        print(f"Caractères à traduire: {char_count}")

        # À des fins de débogage et de suivi des coûts
        today = datetime.now().strftime('%Y-%m-%d')
        self.daily_char_count = getattr(self, 'daily_char_count', {})
        self.daily_char_count[today] = self.daily_char_count.get(today, 0) + char_count
        print(f"Total des caractères traduits aujourd'hui: {self.daily_char_count[today]}")

        for lang_code in self.supported_languages:
            if lang_code != source_lang:
                translations[lang_code] = self.translate_text(text, source_lang, lang_code)

        return translations