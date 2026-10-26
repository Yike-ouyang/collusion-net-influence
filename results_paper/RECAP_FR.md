# Récapitulatif du projet

## Question

Est-ce que le canal privé facultatif change les actions et les gains de deux LLM partenaires ? Peut-on apprendre un suffixe qui rapproche leur comportement de la condition sans canal ?

## Résultats principaux

- **Dépendance des actions :** sur 20 parties de 60 manches par condition et par modèle, `I(A;B | actions conjointes précédentes)` augmente avec le canal facultatif : Qwen 0,059 → 0,459 bit ; GLM 0,071 → 0,344 ; Mixtral 0,069 → 0,186. Les intervalles bootstrap appariés sur les parties pour l'augmentation sont respectivement +0,400 [+0,328, +0,419], +0,273 [+0,165, +0,322], +0,117 [+0,057, +0,159]. Le test par permutation est significatif avec canal facultatif (`p=0,001996`, 500 permutations) et ne l'est pas sans canal. C'est une dépendance ajustée sur l'historique, pas une preuve d'intention ou de collusion.
- **Avantage dans le jeu :** `(A+B)/2 − C` vaut -0,33 point/manche pour Qwen, -0,51 pour GLM et -0,09 pour Mixtral avec le canal facultatif. Les deux agents utilisent bien le canal (65%, 97% et 100%), mais aucune exécution de plan n'est enregistrée dans cette condition. Avec stratégie forcée, la paire exécute un plan dans 96% des parties Qwen, 44% GLM et 47% Mixtral ; son avantage devient +0,20, +0,03 et -0,02. Le canal seul ne conduit donc pas automatiquement à une stratégie efficace. Pourquoi cela arrive reste à vérifier dans les traces.
- **Premier GCG :** le suffixe appris `网` fait baisser l'objectif KL de validation de 41,407 à 39,620 nats, soit 2,579 bits par contexte par rapport au suffixe vide. Le petit jeu de validation a servi à sélectionner le candidat : résultat exploratoire, pas validation indépendante.
- **GCG chronologique :** Modal a été arrêté après sauvegarde : runs 0–7 terminés, run 8 partiel (quatre blocs), runs suivants non faits. Parmi les huit runs complets, `ない` a été nouvellement choisi au bloc 1 dans 5 runs sur 8 et `ある` au bloc 2 dans 4 sur 8. Sept suffixes finaux distincts apparaissent dans huit runs. La répétition précoce suggère des candidats à tester ; les suffixes finaux instables et non linguistiques ne montrent pas un suffixe universel.
- **Gain sur le bloc suivant :** le proxy KL s'améliore en moyenne de 3,1 à 5,6 bits sur le bloc de dix manches suivant l'optimisation ; 7 à 9 observations sur 8 ou 9 sont positives selon le bloc. Les blocs d'un même run sont dépendants et cette métrique reste une perte de recherche, pas une mesure de collusion.
- **Replay de prompts :** sur 11 anciens runs Qwen, aucun suffixe n'a montré de transfert fiable vers la référence sans canal. `ื่`, suffixe du run 0 au bloc 5, a un gain moyen de distance TV de seulement 0,00025 et est positif dans 1 run sur 11. Le replay garde l'historique fixe : il ne mesure ni la dépendance réelle des actions dans une nouvelle partie ni les scores.

## Raisonnement et étapes

1. Comparaison de cinq conditions v4 sur Qwen, GLM et Mixtral (20 parties × 60 manches par condition).
2. Séparation de trois signaux : dépendance entre les actions, transfert de gains vers A+B, et accords observables dans les messages/plans. Aucun de ces signaux isolé ne prouve une collusion.
3. Utilisation de l'information mutuelle, inspirée de Bonjour et al. (2022), puis ajustement par l'historique d'actions précédentes et comparaison à une distribution nulle par permutation.
4. Adaptation de GCG (Zou et al., 2023) pour rapprocher des lois de probabilité d'actions de la référence sans canal. Le suffixe `!!!!!` sert d'initialisation ; les remplacements sont guidés par le gradient sur Qwen.
5. Passage d'un petit test sur les manches 8–10 à une recherche chronologique, run par run et bloc de 10 manches, afin de conserver l'évolution des contextes.
6. Screening des suffixes sur d'autres contextes sauvegardés. Ce test n'étant pas une partie complète, le prochain résultat utile est une comparaison en nouvelles parties avec suffixes gelés.

## Résultats intéressants encore sous-exploités

- Les traces contiennent les actions, scores, messages privés et plans épisode par épisode. Une étude de conformité entre accord explicite, actions et gains pourrait compléter le signal de dépendance.
- Les mesures de calibration et d'influence nette déjà calculées peuvent être rapprochées de l'avantage `(A+B)/2 − C` pour savoir quels indicateurs prédisent effectivement le transfert de gains.
- Comparer les effets de canal facultatif, forcé, indice de canal, et stratégie forcée aiderait à séparer « communiquer », « reconnaître le canal », et « exécuter une stratégie ».
- Tester `ない` et `ある` sur des parties nouvelles constitue le test prioritaire. Le plan existe dans `coalition_metrics/05_gcg_suffix_evaluation/fresh_game_study/` ; il n'a pas encore été lancé.

## Limites à signaler dans un rapport

Le KL GCG est une fonction de recherche et non une mesure directe de collusion. Les suffixes sont choisis sur peu de trajectoires ; les runs et blocs successifs ne sont pas indépendants. Les replays gardent les anciens historiques fixes. Les résultats confirmatoires nécessitent des parties complètes nouvelles, des intervalles calculés sur les parties, et une séparation stricte des données d'optimisation et d'évaluation.

Les figures anglaises prêtes à consulter se trouvent dans [`figures/`](figures/). La synthèse complète et les liens vers les sources sont dans [`README.md`](README.md).
