# TODO — Améliorations du dataset cron-finetuning

## 🔴 Priorité haute

### 1. ✅ Ajouter un split de test (train/val/test)

~~Actuellement seul train/valid existe (90/10). Sans test set, l'évaluation finale est biaisée car la validation sert à la fois à l'early stopping et à la métrique finale.~~
**Fait :** `split_dataset` produit trois splits (80/10/10), `test.jsonl` est écrit, `write_manifest` et `train.py` ignorent le test à l'entraînement. Un nouveau script `evaluate.py` gère l'évaluation finale sur le test set.

### 2. Splitter par seed pour éviter la fuite train/valid

Actuellement le split est aléatoire : deux paraphrases LLM issues du même template peuvent se retrouver une dans train, l'autre dans valid. Ça gonfle artificiellement les scores.  
**Plan :** dans `generate.py`, grouper les exemples par `target` identique avant le split. Tous les exemples partageant le même `target` (template + ses paraphrases) iront dans le même split. Utiliser un hash du `target` comme clé de groupement.

### 3. Rédiger une Dataset Card au standard HuggingFace

Le dataset n'a pas de `README.md` avec frontmatter YAML, donc pas de Dataset Viewer, pas de discoverability, pas de métadonnées structurées sur le Hub.  
**Plan :** créer un fichier `DATASET_CARD.md` (ou remplacer le README existant) avec le frontmatter YAML standard (`task_categories`, `language`, `tags`, `size_categories`, `configs`), une description du dataset, un tableau des familles, les stats train/valid/test, et des exemples. S'inspirer de [hf.co/datasets](https://huggingface.co/docs/hub/datasets-cards).

---

## 🟡 Priorité moyenne

### 4. Équilibrer les familles (50-100 exemples minimum par famille)

Le dataset souffre d'un fort déséquilibre : `daily_at` génère ~200 exemples, `monthly_on_day_at` en génère ~432 (12 jours × 6 heures × 6 phrasings), tandis que `multi_weekday_at` n'en a que ~36. Le modèle va sur-apprendre les familles lourdes.  
**Plan :** auditer chaque famille avec un script de comptage, ajouter des créneaux horaires et variantes de paraphrase pour les familles sous-représentées, éventuellement capter les familles dominantes à ~100 exemples max pour lisser la distribution.

### 5. Compléter la couverture syntaxique cron

Le dataset n'utilise que `*`, `*/N`, `N`, `N-M`, et `N,M,O`. Il manque les ranges avec step (`1-30/10`), les combos DoW + DoM simultanés (comportement OR implicite), et les alias manquants (`@reboot`, `@yearly`).  
**Plan :** ajouter une famille `step_ranges` pour les patterns `N-M/STEP`, enrichir `cron_aliases_examples` avec `@reboot`/`@yearly`/`@annually`, et créer une famille `dom_dow_interaction` pour les cas où les deux champs sont non-wildcard (piège classique des utilisateurs cron).

### 6. Monter le ratio INVALID à 15-20%

Avec seulement 40 exemples INVALID template + 50 LLM (~7% du total), le modèle risque d'halluciner des cron sur des inputs hors-sujet — ce qui est le pire mode de défaillance en production.  
**Plan :** enrichir `invalid_examples()` avec 60-80 prompts supplémentaires couvrant plus de domaines (small talk, code, langues étrangères, questions techniques ambiguës), et augmenter `generate_invalid_with_llm` de 50 à 100 exemples. Cibler un ratio final de 15-20% d'INVALID sur l'ensemble du dataset.

### 7. Ajouter des configurations HF au dataset

Un dataset HuggingFace professionnel expose plusieurs configs (`template-only`, `full`, `balanced`) pour que les utilisateurs puissent charger la variante qui les intéresse sans filtrer manuellement.  
**Plan :** créer un script `cron_dataset.py` compatible `datasets.DatasetBuilder` avec des configs définies dans `DATASET_CONFIGS`. Chaque config contrôle quelles familles et sources sont incluses. Remplacer `load_dataset_from_hub` par un appel à `load_dataset("user/cron-dataset", "full")` qui respecte ces configs.

---

## 🟢 Priorité basse

### 8. Convertir en Parquet avant le push

Le HF Dataset Viewer indexe le Parquet, pas le JSONL. Sans Parquet, pas de preview en ligne, pas de recherche, pas de stats automatiques.  
**Plan :** modifier `push_dataset_to_hub` pour convertir `train.jsonl`/`valid.jsonl`/`test.jsonl` en `.parquet` via `datasets.Dataset.to_parquet()` avant l'upload, ou utiliser `Dataset.push_to_hub()` qui gère la conversion automatiquement.

### 9. Ajouter une validation CI des labels

Aucun test automatisé ne vérifie que les templates produisent des cron valides. Une régression dans `families.py` pourrait introduire des labels incorrects silencieusement.  
**Plan :** ajouter un job `pytest` dans la CI GitHub qui : vérifie que chaque `target` est soit `"INVALID"` soit un cron 5-champs syntaxiquement valide avec des valeurs dans les plages légales, vérifie l'absence de doublons après normalisation, et vérifie la cohérence sémantique user↔target pour tous les exemples templates.

### 10. Versioning Git sémantique du dataset

Sans tags Git, impossible de référencer une version précise du dataset dans un papier ou de reproduire des résultats. Le dataset est vivant mais non versionné.  
**Plan :** tagger le repo avec des versions sémantiques (`v0.1.0`, `v0.2.0`) après chaque modification du dataset. Documenter dans le Dataset Card quelle version a été utilisée pour quel entraînement. Ajouter un champ `dataset_version` dans `manifest.json`.

### 11. Ajouter un compteur d'exemples par famille au manifest

Le `manifest.json` actuel liste les familles présentes mais pas leur distribution. Impossible de savoir d'un coup d'œil si le dataset est équilibré.  
**Plan :** ajouter une clé `"families_breakdown"` dans `write_manifest` qui compte les exemples par `(family, source)` et les trie par ordre décroissant. Afficher ce breakdown dans la sortie de `cron-generate`.

---

## ⚪ Backlog

- Support du cron 6 champs (secondes) pour AWS/Quartz
- Support des macros spéciales Quartz (`?`, `L`, `W`, `#`)
- Génération de prompts adversariaux (inputs ambigus type "tous les jours sauf le weekend à 8h")
- Export multi-langue (FR, ES, DE) pour les prompts utilisateur
- Split par famille pour l'évaluation fine-grained (accuracy par type de cron)
