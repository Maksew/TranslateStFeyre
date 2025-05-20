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
        self.max_cache_size = 1000

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
        """Retourne {lang: traduction} optimisé pour compte AWS standard."""
        # Si le texte est vide ou trop court, ne pas traduire
        if not text or len(text.strip()) < 3:
            return {source_lang: text}

        translations = {source_lang: text}
        target_langs = [lang for lang in self.supported_languages if lang != source_lang]

        # Utilisation optimisée pour compte AWS standard
        try:
            # Vérifier d'abord le cache pour toutes les langues
            cache_hits = 0
            for tgt in target_langs:
                cache_key = f"{text}_{source_lang}_{tgt}"
                if cache_key in self.translation_cache:
                    translations[tgt] = self.translation_cache[cache_key]
                    cache_hits += 1

            # Si toutes les traductions sont en cache, on termine
            if cache_hits == len(target_langs):
                return translations

            # Sinon, paralléliser les requêtes API pour les langues non-cachées
            remaining_langs = [lang for lang in target_langs if
                               f"{text}_{source_lang}_{lang}" not in self.translation_cache]

            # Utiliser 2 workers maximum pour éviter les limitations d'API sur compte standard
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = {
                    pool.submit(self.translate_text, text, source_lang, tgt): tgt
                    for tgt in remaining_langs
                }
                for fut, tgt in futures.items():
                    try:
                        translations[tgt] = fut.result()
                    except Exception as e:
                        print(f"Erreur de traduction pour {tgt}: {e}")
                        # Fallback avec une pause en cas d'erreur de limitation
                        time.sleep(0.5)
                        try:
                            translations[tgt] = self.translate_text(text, source_lang, tgt)
                        except:
                            translations[tgt] = f"[Erreur de traduction: {tgt}]"

        except Exception as e:
            print(f"Erreur globale de traduction: {e}")
            # Mode dégradé: traduire une langue à la fois avec pause
            for tgt in target_langs:
                if tgt not in translations:
                    try:
                        translations[tgt] = self.translate_text(text, source_lang, tgt)
                        time.sleep(0.2)  # Pause pour éviter les limitations
                    except:
                        translations[tgt] = f"[Erreur: {tgt}]"

        # Gestion de cache comme avant
        if len(self.translation_cache) >= self.max_cache_size:
            keys_to_delete = list(self.translation_cache.keys())[:int(self.max_cache_size * 0.2)]
            for k in keys_to_delete:
                del self.translation_cache[k]

        return translations