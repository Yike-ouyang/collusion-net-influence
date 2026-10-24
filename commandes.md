Commandes
pip install modal
modal setup

mkdir -p logs
modal run --detach --name pot-channel-20 cloud/pot_modal.py \
  --condition channel --runs 20 --rounds 100 --workers 16 \
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