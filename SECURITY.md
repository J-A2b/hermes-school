# Sécurité et données privées

Ne joignez jamais de base réelle, identifiant, clé, token, copie de message, journal brut ou document scolaire à une issue ou pull request. Utilisez des exemples synthétiques et retirez les noms, identifiants d’élèves et adresses privées.

Le dashboard demande un mot de passe, valide les hôtes, protège les formulaires par CSRF et échappe le HTML. Les téléchargements passent par des identifiants locaux. Les outils MCP sont limités à ceux que vous autorisez. Ces protections ne constituent pas un audit de sécurité indépendant.

Les documents et messages peuvent contenir des instructions malveillantes : l’agent doit les traiter comme des données non fiables. Ne demandez jamais à votre modèle IA de manipuler les fichiers de secrets.

Écoutez sur localhost, gardez les données sous des permissions restrictives et protégez l’accès distant avec SSH ou un accès HTTPS privé. Ne désactivez pas TLS pour résoudre un problème de connexion.

La clé de chiffrement des identifiants réside sur la machine : un compte système compromis peut accéder aux données. Les sauvegardes doivent être déportées et leur clé conservée séparément. Testez une restauration avant d’en dépendre.

Pour signaler une vulnérabilité, utilisez le signalement privé GitHub si le mainteneur l’a activé. Sinon, demandez un canal privé sans publier les détails exploitables ni les données concernées. Aucune adresse de contact personnelle n’est incluse dans ce modèle de dépôt.
