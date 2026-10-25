# 01 — Signal de coordination

## Question

Les coups de A et B restent-ils dépendants après contrôle du contexte qu’ils partagent, et cette dépendance est-elle plus forte que celle des autres paires ?

## Première analyse

`analyze.py` mesure, par partie, `I(A;B | shared_die)`, `I(A;C | shared_die)` et `I(B;C | shared_die)` en nats. Il calcule aussi les deux marges d’influence nette du couple A–B :

```text
net_A_to_B = I(A;B|D) - I(B;C|D)
net_B_to_A = I(A;B|D) - I(A;C|D)
```

Le test nul permute les coups indépendamment dans chaque strate `(partie, shared_die)`, puis compare les trois paires avec correction de Bonferroni. Les intervalles de confiance sont rééchantillonnés par parties.

```bash
.venv/bin/python coalition_metrics/01_coordination_signal/analyze.py \
  results/llm_rps_v2/20261025-1834_same_model_qwen32b_big-v4 \
  results/llm_rps_v2/20261025-1837_same_model_glm32b_big-v4 \
  --permutations 999
```

Sorties : `game_metrics.csv` et `condition_summary.csv` dans ce dossier.

## Limites et suite

La permutation stratifiée ne conserve pas l’adaptation temporelle. Les p-values sont exploratoires. La prochaine comparaison est une permutation par blocs compatible avec les contextes et un bootstrap de parties complètes. Les analyses de taille d’échantillon doivent sous-échantillonner des parties, puis des manches à l’intérieur des parties, sans traiter les 60 manches comme indépendantes.

Une dépendance résiduelle est un signal de coordination, pas une preuve d’accord ou d’intention. Le nombre v4 est partagé par A et B, d’où le contrôle `shared_die`.
