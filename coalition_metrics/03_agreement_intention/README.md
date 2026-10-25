# 03 — Accord observable et intention déclarée

## Question

Les agents expriment-ils un accord dans le canal ou leurs plans, et cet accord est-il exécuté ? Ces éléments concordent-ils avec les actions et les gains ?

## Première analyse

L’analyseur produit des mesures par partie et par condition : nombre de messages, plans parsés, taux de plans A/B concordants, taux d’exécution des plans concordants et taux de suivi du propre plan. Il exporte également les messages bruts pour une annotation humaine.

```bash
.venv/bin/python coalition_metrics/03_agreement_intention/analyze.py \
  results/llm_rps_v2/20261025-1834_same_model_qwen32b_big-v4 \
  results/llm_rps_v2/20261025-1837_same_model_glm32b_big-v4
```

Sorties : `game_metrics.csv`, `condition_summary.csv` et `messages_for_review.csv` dans ce dossier.

## Annotation recommandée

Pour les messages, annoter séparément : proposition de coordination, accord explicite, aide à un partenaire, cible extérieure, plan concret, désaccord/refus, et exécution ultérieure. Faire annoter un échantillon par deux personnes sans leur montrer les scores ni la condition, puis mesurer leur accord inter-annotateurs.

Les plans et messages sont des traces comportementales plus directes d’un accord que la seule corrélation des coups. Ils ne prouvent pas une intention interne. Réflexions et débriefs sont des auto-rapports des LLM et ne doivent pas être traités comme une vérité terrain.
