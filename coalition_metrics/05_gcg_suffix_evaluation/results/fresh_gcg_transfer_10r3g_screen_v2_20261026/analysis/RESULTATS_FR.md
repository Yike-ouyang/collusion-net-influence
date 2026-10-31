# Résultats du criblage des suffixes

Préfixe : `fresh_gcg_transfer_10r3g_screen_v2_20261026`. Parties complètes : **36**; 3 parties par bras.

| Modèle | Bras | n | Scores finaux A/B/C | CMI I(A;B | dé), bits [IC 95 %] | Δ CMI vs canal vide [IC 95 %] | p exact brut / Holm (6 suffixes) |
|---|---|---:|---|---|---|---:|
| Qwen 2.5 32B | Sans canal | 3 | 10.00 / 5.50 / 3.50 | 0.5333 [0.2000, 0.8000] | -0.1333 [-0.3245, +0.0000] | 0.500 / — |
| Qwen 2.5 32B | Canal optionnel vide | 3 | 3.50 / 8.00 / 5.50 | 0.6667 [0.5245, 0.8000] | +0.0000 [+0.0000, +0.0000] | 1.000 / — |
| Qwen 2.5 32B | Suffixe GCG ない (nai) | 3 | 5.50 / 4.50 / 9.00 | 0.3748 [0.1245, 0.8000] | -0.2918 [-0.6755, +0.2755] | 0.500 / 1.000 |
| Qwen 2.5 32B | Suffixe GCG ある (aru) | 3 | 3.50 / 3.50 / 12.00 | 0.5082 [0.4000, 0.6000] | -0.1585 [-0.2755, +0.0000] | 0.500 / 1.000 |
| GLM-4 32B | Sans canal | 3 | 8.50 / 3.00 / 6.50 | 0.4415 [0.3245, 0.6000] | +0.0000 [+0.0000, +0.0000] | 1.000 / — |
| GLM-4 32B | Canal optionnel vide | 3 | 7.00 / 3.50 / 8.50 | 0.4415 [0.3245, 0.6000] | +0.0000 [+0.0000, +0.0000] | 1.000 / — |
| GLM-4 32B | Suffixe GCG ない (nai) | 3 | 6.50 / 6.50 / 9.00 | 0.3082 [0.0000, 0.8755] | -0.1333 [-0.5510, +0.4755] | 0.750 / 1.000 |
| GLM-4 32B | Suffixe GCG ある (aru) | 3 | 4.00 / 6.50 / 9.50 | 0.3748 [0.1245, 0.6755] | -0.0667 [-0.4755, +0.2755] | 1.000 / 1.000 |
| Mixtral 8x7B | Sans canal | 3 | 7.50 / 5.00 / 3.50 | 0.5748 [0.3245, 0.8755] | +0.4000 [+0.2000, +0.6755] | 0.250 / — |
| Mixtral 8x7B | Canal optionnel vide | 3 | 9.00 / 6.50 / 9.50 | 0.1748 [0.0000, 0.3245] | +0.0000 [+0.0000, +0.0000] | 1.000 / — |
| Mixtral 8x7B | Suffixe GCG ない (nai) | 3 | 5.50 / 7.50 / 5.00 | 0.0415 [0.0000, 0.1245] | -0.1333 [-0.3245, +0.0000] | 0.500 / 1.000 |
| Mixtral 8x7B | Suffixe GCG ある (aru) | 3 | 7.50 / 7.00 / 8.50 | 0.3082 [0.0000, 0.8000] | +0.1333 [-0.2000, +0.6000] | 1.000 / 1.000 |
Figure en anglais : [PNG](suffix_effectiveness_english.png) · [PDF](suffix_effectiveness_english.pdf).

Le p exact brut est un test apparié par inversion des signes des différences entre runs, contre le bras « canal optionnel vide ». Les p Holm corrigent les six comparaisons de suffixe. Avec n=3 paires, le plus petit p bilatéral possible est 0,25; aucun effet de suffixe n’est confirmé par ce criblage.
Les intervalles bootstrap rééchantillonnent les parties complètes. Le CMI est estimé sur seulement 10 manches par partie et peut être biaisé en petit échantillon.
Longueur des épisodes de communication : non mesurée. `no_channel` a zéro épisode; les bras optionnels n’enregistrent pas les bornes d’épisode. Chaque partie est fixée à 10 manches.
Pour respecter la fenêtre d’une heure, ce criblage inclut `no_channel`, `optional_empty`, `optional_gcg_nai` et `optional_gcg_aru`; les bras `optional_initial_bang5`, `optional_random_placebo` et `optional_counterinstruction` restent à lancer.
