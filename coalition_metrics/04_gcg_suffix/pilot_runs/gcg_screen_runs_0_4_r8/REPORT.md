# Qwen suffix screen — runs 0–4, round 8

60 requests were completed: five complete game IDs × round 8 × two conditions/seats, with five optional-channel suffix variants. Each test folder contains the paired exact prompts and responses, per-run metrics, and a JSON summary.

## Summary

| Test | Mean pair TV to no-channel | Mean pair TV vs optional empty | Closer to no-channel than empty (runs) | Unchanged vs optional empty (runs) |
|---|---:|---:|---:|---:|
| `empty` | 1.000 | 0.000000 | 0/5 | 5/5 |
| `short_init` | 1.000 | 0.000000 | 0/5 | 5/5 |
| `independent_1` | 1.000 | 0.000000 | 0/5 | 5/5 |
| `independent_2` | 1.000 | 0.000000 | 1/5 | 2/5 |
| `state_only` | 1.000 | 0.000000 | 0/5 | 5/5 |

## Lecture du premier test

- Aucun suffixe ne rapproche les distributions de coups de la référence `no_channel` par rapport au suffixe vide dans cette fenêtre.
- Les distributions renormalisées sont pratiquement invariantes entre suffixes : ce dépistage ne montre pas d’effet mesurable des formulations testées.
- Le TV de la loi conjointe est construit comme produit des distributions individuelles A × B. Ce n’est pas une mesure observée de dépendance entre les actions.
- Le code ne récupère que les cinq alternatives de log-probabilité autour du token de coup, puis renormalise sur les trois coups. Les probabilités manquantes sont donc censurées ; cette mesure est un proxy.
- Un seul contexte par partie/manche ne permet pas d’estimer (I(A;B\mid S)), ni l’effet sur les gains. Une validation comportementale nécessite des parties complètes avec le suffixe retenu.

## Fichiers

- `cases_and_prompts.json` : les 60 prompts reconstruits.
- `intermediate_results.json` : réponses et distributions brutes.
- `traces/` : traces des requêtes envoyées.
- `summary_by_test.csv` : synthèse comparative.
- `test_<suffix>/` : prompt/réponse appariés et mesures par test.

Aucune conclusion de performance ou de collusion ne doit être tirée de ce dépistage exploratoire.
