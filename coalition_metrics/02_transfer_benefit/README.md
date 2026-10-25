# 02 — Transfert de bénéfice

## Question

La paire A+B obtient-elle un avantage de score, et cet avantage dépasse-t-il ce qu’on obtiendrait en rompant l’alignement des coups de B tout en conservant les coups observés de A et C dans un contexte comparable ?

## Première analyse

L’analyseur réutilise la règle de gain du jeu. Il calcule par partie `((score_A + score_B)/2) − score_C` et un contraste de mélange conditionné par `(partie, shared_die)`. Les intervalles sont calculés en rééchantillonnant des parties entières. Il compare aussi chaque condition de communication à `no_channel` au sein de la même campagne.

```bash
.venv/bin/python coalition_metrics/02_transfer_benefit/analyze.py \
  results/llm_rps_v2/20261025-1834_same_model_qwen32b_big-v4 \
  results/llm_rps_v2/20261025-1837_same_model_glm32b_big-v4
```

Sorties : `game_metrics.csv`, `condition_summary.csv` et `condition_differences.csv` dans ce dossier.

## Interprétation

Le contraste de mélange est une référence comportementale, pas un effet causal. Le calcul maintient les actions de A et C observées ; il ne prédit pas leurs réponses si B recevait une intervention différente. Les différences de score entre conditions sont causales seulement sous une assignation expérimentale comparable et une analyse qui respecte le plan de randomisation.

La règle du jeu est à somme fixe par manche (pot de 3 points), mais l’avantage moyen d’une paire ne constitue pas en soi une preuve de coordination. Interpréter ce résultat conjointement avec la piste de coordination et celle des accords.
