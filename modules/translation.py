from concurrent.futures import ThreadPoolExecutor
import boto3

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

    def translate_text(self, text: str, source_lang: str, target_lang: str) -> str:
        resp = self.client.translate_text(
            Text=text,
            SourceLanguageCode=source_lang,
            TargetLanguageCode=target_lang
        )
        return resp["TranslatedText"]

    def translate_to_all(self, text: str, source_lang: str = "fr") -> dict:
        """Retourne {lang: traduction} en parallèle (max_workers=5)."""
        translations = {source_lang: text}
        with ThreadPoolExecutor(max_workers=5) as pool:
            futures = {
                pool.submit(self.translate_text, text, source_lang, tgt): tgt
                for tgt in self.supported_languages
                if tgt != source_lang
            }
            for fut, tgt in futures.items():
                translations[tgt] = fut.result()
        return translations
