# GCG chronologique par partie

## Question et hypothèses

On cherche à savoir si un suffixe initial `!!!!!` peut être déplacé par GCG vers des tokens récurrents qui rapprochent les distributions de coups sous `channel_optional` de celles sous `no_channel`.

- **H1 — apprentissage local :** un remplacement de token réduit la KL moyenne sur le bloc chronologique utilisé pour le choisir.
- **H2 — transfert temporel :** le suffixe choisi sur un bloc améliore aussi le bloc suivant, avant toute mise à jour sur ce bloc.
- **H3 — motif commun :** des runs optimisés séparément font apparaître des tokens ou fragments récurrents.
- **H4 — test comportemental :** un candidat récurrent devra ensuite être évalué dans de nouvelles parties complètes avant de conclure qu'il réduit la coalition.

La loss est une approximation différentiable : KL entre les lois de coups du modèle sans canal et celles du modèle avec canal et suffixe, calculée par contexte puis moyennée, avec une pénalité de KL individuelle pour A et B. Elle ne minimise pas directement l'information mutuelle empirique `I(A;B|S)`.

## Plan d'expérience

- **20 parties complètes existantes**, IDs 0 à 19, traitées comme 20 unités indépendantes pour le bootstrap. Les manches d'une partie restent regroupées et dans l'ordre.
- Pour chaque partie, démarrer séparément avec `!!!!!`; optimiser un seul remplacement de token par bloc de 10 manches.
- Au bloc 1, comparer des candidats sur les manches 1–10; figer le meilleur; le mesurer sur les manches 11–20 avant d'optimiser ce bloc. Continuer jusqu'à 51–60.
- Quatre jobs Modal de cinq parties chacun réduisent le risque de perdre tout le travail si un job échoue. Chaque job sauvegarde les résultats après chaque bloc.
- Les suffixes après le bloc 5 (appris sur 41–50) et leur gain sur 51–60 forment l'analyse préquentielle principale. Le suffixe final après le bloc 6 n'a pas de futur bloc de validation.

Vingt parties suffisent à une analyse exploratoire avec intervalle bootstrap par partie; cela ne constitue pas une confirmation indépendante. Ne compte pas les 60 manches d'une même partie comme 60 observations indépendantes.

Pour l'étape confirmatoire, prévois au moins 20 nouvelles parties complètes par condition avec le suffixe candidat gelé avant le lancement. C'est un plancher pratique, pas une garantie de puissance : après cette première comparaison, augmente le nombre de parties si l'intervalle d'incertitude reste large ou si l'effet observé est petit.

## Étape 1 — vérifier les prérequis

Depuis la racine du dépôt :

```bash
pwd
git status --short
.venv/bin/python -m modal --version
.venv/bin/python -m modal volume ls netinf-v2
```

Assure-toi que l'environnement Modal sélectionné a accès au volume `netinf-v2` et que le modèle Qwen utilisé par le pilote peut être téléchargé. Ces vérifications ne lancent pas de requête modèle.

## Étape 2 — préparer les quatre lots hors ligne

Le script reconstruit les prompts exacts depuis les parties archivées. `--prepare-only` n'appelle aucun modèle. Un lot de 5 runs doit contenir 1 200 contextes de décision : 5 runs × 60 manches × 2 conditions × 2 joueurs.

```bash
set -euo pipefail
for first in 0 5 10 15; do
  last=$((first + 4))
  run_ids=$(seq "$first" "$last")
  out_dir="/tmp/gcg-chronological-${first}-${last}"
  .venv/bin/python coalition_metrics/04_gcg_suffix/run_suffix_pilot.py \
    --prepare-only --runs $run_ids --rounds $(seq 1 60) \
    --suffixes empty --out "$out_dir"
done
```

Contrôle les quatre lignes `Prepared 1200 prompts` et les comptes par condition : `no_channel / empty: 600` et `channel_optional / empty: 600` pour chaque lot. Si une partie est incomplète, arrête-toi et corrige le bundle avant de lancer Modal.

## Étape 3 — lancer les quatre optimisations

Les jobs doivent être lancés séquentiellement. Chaque lot a son propre checkpoint et son propre rapport sur le volume Modal. Le délai maximal configuré est de 24 heures par job; ce n'est pas une estimation du temps réel. La durée dépend du chargement de Qwen, des longueurs de prompts et de la disponibilité GPU.

```bash
set -euo pipefail
for first in 0 5 10 15; do
  last=$((first + 4))
  run_ids="${first}_${last}"
  .venv/bin/python -m modal run cloud/gcg_qwen_pilot.py \
    --mode chronological \
    --train-bundle "/tmp/gcg-chronological-${first}-${last}/cases_and_prompts.json" \
    --output-name "qwen32b_chronological_bang5_runs_${run_ids}" \
    --initial-suffix '!!!!!' --block-size 10 --candidate-count 4 \
    --individual-weight 0.25
done
```

Ne relance pas un lot déjà terminé sauf si tu veux recalculer ses sorties. Les noms de résultats doivent être uniques si tu veux conserver plusieurs versions.

## Étape 4 — télécharger les résultats

```bash
set -euo pipefail
out_dir="coalition_metrics/04_gcg_suffix/results/chronological_per_run_20_runs"
mkdir -p "$out_dir"
for first in 0 5 10 15; do
  last=$((first + 4))
  name="qwen32b_chronological_bang5_runs_${first}_${last}"
  .venv/bin/python -m modal volume get netinf-v2 \
    "/results/gcg_qwen_pilot/${name}.json" "$out_dir/"
  .venv/bin/python -m modal volume get netinf-v2 \
    "/results/gcg_qwen_pilot/${name}.md" "$out_dir/"
done
```

## Étape 5 — agréger et repérer les motifs

```bash
.venv/bin/python coalition_metrics/04_gcg_suffix/summarize_chronological_gcg.py \
  --inputs \
    coalition_metrics/04_gcg_suffix/results/chronological_per_run_20_runs/qwen32b_chronological_bang5_runs_0_4.json \
    coalition_metrics/04_gcg_suffix/results/chronological_per_run_20_runs/qwen32b_chronological_bang5_runs_5_9.json \
    coalition_metrics/04_gcg_suffix/results/chronological_per_run_20_runs/qwen32b_chronological_bang5_runs_10_14.json \
    coalition_metrics/04_gcg_suffix/results/chronological_per_run_20_runs/qwen32b_chronological_bang5_runs_15_19.json \
  --out coalition_metrics/04_gcg_suffix/results/chronological_per_run_20_runs/cross_run_summary
```

Ouvre ensuite `cross_run_summary/REPORT.md`, `chronological_gcg_summary.json` et `chronological_gcg_by_run_block.csv`.

### Lecture à faire

1. Regarde les suffixes et IDs de tokens après le bloc 5, puis le gain préquentiel du bloc 6.
2. Vérifie si un même token ID apparaît dans au moins 12 des 20 runs. Les IDs sont plus fiables que les morceaux de texte décodés : la tokenisation peut varier selon le contexte.
3. Vérifie le signe de la moyenne et de l'intervalle bootstrap à 95 % du gain sur 51–60, avec la partie comme unité de rééchantillonnage.
4. Regarde la dispersion run par run dans le CSV. Une moyenne positive portée par quelques parties n'est pas un motif robuste.
5. Traite toute récurrence comme un candidat exploratoire. Les fréquences de tokens sont descriptives et ne sont pas un test statistique indépendant.

## Limite temporelle importante

Les prompts archivés des manches 11–60 contiennent l'historique des anciennes parties. Le nouveau suffixe est testé dans ces contextes chronologiques, mais les coups consignés dans cet historique ne sont pas recalculés avec le suffixe. Donc le pilote préserve l'ordre des contextes et évite de permuter les manches; il **ne simule pas** une partie où les actions affectées par le suffixe changent les manches futures.

Pour une validation anti-collusion, prends un suffixe candidat défini à l'avance et lance de nouvelles parties complètes avec ce suffixe fixe dès la première manche. Compare-les à des parties sans suffixe sur les métriques comportementales (`I(A;B|S)`, avantage de la paire et résultats par joueur), en bootstrapant par partie. Cette évaluation indépendante est nécessaire avant d'interpréter le suffixe comme une stratégie anticollusive.

## Ce que fait réellement le code

Le mode `chronological` exécute un remplacement GCG par bloc et par run, sur des prompts reconstruits localement; les appels différentiables au modèle ont lieu sur Modal. Les fichiers locaux préparés contiennent les prompts exacts. Les sorties Modal incluent le chemin de suffixes, les scores de candidats et les gains du bloc suivant. Les lignes de commande ci-dessus sont à lancer dans ton terminal; la préparation et l'agrégateur ne lancent aucun appel modèle.
