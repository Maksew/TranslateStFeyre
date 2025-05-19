from concurrent.futures import ThreadPoolExecutor
import boto3
import time


class AWSTranslator:
    def __init__(self,
                 aws_access_key: str,
                 aws_secret_key: str,
                 region_name: str,
                 supported_languages: dict):
        self.client = boto3.client(
            "translate",
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            region_name=region_name
        )
        self.supported_languages = supported_languages
        # Cache de traduction pour les phrases répétées
        self.translation_cache = {}
        self.max_cache_size = 500

    def translate_text(self, text: str, source_lang: str, target_lang: str) -> str:
        # Vérifier dans le cache
        cache_key = f"{text}_{source_lang}_{target_lang}"
        if cache_key in self.translation_cache:
            return self.translation_cache[cache_key]

        # Traduire si pas en cache
        resp = self.client.translate_text(
            Text=text,
            SourceLanguageCode=source_lang,
            TargetLanguageCode=target_lang
        )
        result = resp["TranslatedText"]

        # Mettre en cache
        if len(self.translation_cache) >= self.max_cache_size:
            # Vider 20% du cache si plein
            keys_to_delete = list(self.translation_cache.keys())[:int(self.max_cache_size * 0.2)]
            for k in keys_to_delete:
                del self.translation_cache[k]

        self.translation_cache[cache_key] = result
        return result

    def translate_to_all(self, text: str, source_lang: str = "fr") -> dict:
        """Retourne {lang: traduction} en parallèle (max_workers=3)."""
        translations = {source_lang: text}
        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = {
                pool.submit(self.translate_text, text, source_lang, tgt): tgt
                for tgt in self.supported_languages
                if tgt != source_lang
            }
            for fut, tgt in futures.items():
                translations[tgt] = fut.result()
        return translations