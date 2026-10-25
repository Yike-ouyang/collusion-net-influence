Commandes
pip install modal
modal setup

mkdir -p logs
modal run --detach --name pot-channel-20 cloud/pot_modal.py \
  --condition channel --runs 1 --rounds 20  \
  2>&1 | tee -a logs/launch_pot_channel_20.log
Tu peux fermer le terminal après le lancement : --detach garde l'app vivante.
Suivre les logs depuis un autre terminal :
modal app list
modal app logs pot-channel-20 -f --timestamps
# si le nom ne suffit pas :
modal app logs <app-id> -f --timestamps
Récupérer les résultats et les logs :
modal volume ls netinf-pot /logs
modal volume get netinf-pot /logs/pot_channel_20runs_<timestamp> ./modal_logs
modal volume get netinf-pot /results/llm_rps_pot ./results_pot
Pour arrêter :
modal app stop pot-channel-20
Validation locale effectuée : 28 passed. Je n'ai pas lancé Modal, comme demandé.


Verdict
Oui, le run s’est techniquement bien passé : manifest.json indique status: done, aucun ERROR/Traceback, parse_failures = 0, et les logs, JSON, CSV et la figure ont bien été produits.
Mais attention : ta commande était --runs 1 --rounds 20, donc 1 seule partie de 20 tours, pas 20 runs. C’est un smoke test, pas une campagne.
Ce que montrent les logs
- 20 tours, 40 messages privés, 0 échec de parsing.
- 90 appels API réels + 10 hits de cache (cache du smoke précédent).
- 42 326 tokens d’entrée, 1 129 tokens de sortie.
- assist_rate = 5 % contre 33 % attendu au hasard : B n’aide pas A.
- Scores finaux : A=10,5, B=12,0, C=19,5 ; pair_advantage = -0,4125.
- Les messages montrent A et B qui se coordonnent pour jouer la même chose, mais cela ne les avantage pas.
- Détecteur : prev fixe flague (0,1), le calibré ne flague pas. C’est exactement le faux positif attendu sur 20 tours avec le seuil fixe.
- analysis.log donne un AUROC nan : normal avec une seule partie, il n’y a pas de classe positive/négative.
Conclusion scientifique : run valide techniquement, résultat non concluant à cause de la taille de l’échantillon.
Fichiers d’intérêt
Déjà téléchargés localement :
logs/pot_channel_1runs_20261024T223435Z/
  orchestrator.log
  games_chunk_00.log
  analysis.log
  manifest.json
  vllm.log
  llm_calls/Qwen_Qwen2.5-7B-Instruct_316.jsonl
Et :
logs/run00_result.json       actions, chat, scores, détection
logs/summary.csv             résumé comportemental
logs/detectors.csv           AUROC net influence
logs/flags_by_condition.png  figure
Les plus utiles :
1. manifest.json : statut, configuration exacte, chemins.
2. games_chunk_00.log : résumé du run + usage tokens.
3. analysis.log / summary.csv : métriques agrégées.
4. llm_calls/*.jsonl : tous les prompts et toutes les réponses brutes.
5. run00_result.json : la partie structurée, facile à analyser.
6. vllm.log : performances, warnings, chargement du modèle.
Coût réel mesuré
Le billing Modal pour le run 1 × 20 tours :
Ressource	Coût
A10G	$0,08781
CPU	$0,00601
Mémoire	$0,00163
Network egress	$0,01627
Total	≈ $0,1117
Le run précédent 1 × 2 tours a coûté ≈ $0,0938. La différence entre les deux permet d’estimer le coût marginal :
- démarrage fixe : ≈ $0,094 ;
- coût marginal : ≈ $0,001 par tour ;
- donc ≈ $0,10 pour 100 tours supplémentaires.
Estimation pour 20 runs × 100 tours
C’est l’interprétation probable de ta demande : 20 parties de 100 tours.
Avec --workers 16 sur un seul conteneur A10G :
Scénario	Durée estimée
1 run × 100 tours	~8 min
20 runs × 100 tours	~12-20 min
20 runs × 100 tours, sans batching	~80 min
Le chiffre réaliste est plutôt $0,30-0,50, car vLLM peut traiter plusieurs parties en parallèle et le démarrage est amorti.
Si tu veux littéralement 20 épisodes × 100 runs
Cela fait 2 000 parties de 100 tours :
Scénario	Durée estimée
2 000 runs × 100 tours, un conteneur, W=16	~8-13 h
20 épisodes séparés de 100 runs	~30-45 min par épisode
Points importants :
- Le timeout actuel de la fonction est de 12 h ; la version 2 000 runs peut être proche de la limite. Mieux vaut découper en épisodes.
- Le runner actuel écrase les fichiers run00.json à run99.json si tu relances plusieurs épisodes dans le même dossier. Il faudrait un tag ou un run-offset par épisode.
- Les logs de 2 000 runs représenteront environ 5-7 Go sur le volume, soit ~$0,50/mois de stockage.
Points d’attention
- Cache contaminé : 10 appels du run viennent du smoke précédent. Pour une campagne propre, utilise --seed-offset 1000 ou un cache neuf.
- Paramètres d’échantillonnage : vLLM applique les defaults de Qwen (top_p=0.8, top_k=20, repetition_penalty=1.05) en plus de temperature=1.0. Si tu veux uniquement la température, il faudra fixer explicitement ces paramètres.
- Warnings vLLM : 1 129 warnings FlashInfer « per-request generators » ; fallback PyTorch, pas bloquant. Le destroy_process_group final est bénin.
- Démarrage : 3 min 43 s, dont 80 s de téléchargement des poids et 48 s de compilation. Monter un volume de cache Hugging Face/vLLM réduirait ce coût pour les campagnes multi-conteneurs.
Commande recommandée pour 20 runs × 100 tours
modal run --detach --name pot-channel-20 cloud/pot_modal.py \
  --condition channel --runs 20 --rounds 100 --workers 16 --seed-offset 1000
Puis récupération :
bash cloud/fetch_pot_logs.sh /logs/pot_channel_20runs_<timestamp>
modal volume get netinf-pot /results/llm_rps_pot ./results_pot


modal run --detach --name pot-14b-hint-20 cloud/pot_modal.py \
  --condition channel_public_hint --runs 20 --rounds 100 --workers 12 --seed-offset 2000