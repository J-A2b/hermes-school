# Contribuer

Les contributions utiles portent sur la robustesse du collecteur, les contrats de réponse, la consultation MCP, les interfaces et le déploiement léger.

1. Décrivez le problème ou la capacité proposée.
2. Travaillez avec un venv et des données synthétiques.
3. Ajoutez un test lorsqu’il vérifie un comportement significatif.
4. Exécutez `python -m pytest -q` avec les extras `test,mcp,documents` installés.
5. Documentez les limites et les vérifications réellement effectuées.

N’ajoutez pas d’endpoint supposé, de contournement de protection ou de fallback silencieux vers une démo. Toute nouvelle lecture distante doit être examinée pour ses effets sur les statuts de lecture et les données sources. Aucune écriture ou livraison de message ne doit être activée par défaut.

Les captures, fixtures et logs partagés doivent être entièrement anonymisés ou synthétiques. Les changements de schéma exigent une migration versionnée et un examen des conséquences sur la restauration.
