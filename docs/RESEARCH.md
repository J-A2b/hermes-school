# Recherche technique initiale — octobre 2026

Les pages ci-dessous ont été consultées avant le développement ; leur disponibilité ne constitue pas une validation de l’API sur un compte réel.

| Ressource | Constat et conséquence |
|---|---|
| https://github.com/Scolup/docsdirecte | Documentation communautaire, licence EUPL-1.2 affichée. Aucun code repris. |
| https://github.com/EduWireApps/ecoledirecte-api-docs | Contrats utiles pour notes, cahier de textes et emploi du temps ; documentation non officielle. Aucune licence trouvée sur la page principale consultée, donc pas de copie du dépôt. |
| https://pypi.org/project/ecoledirecte/ | Client asynchrone, origine https://github.com/hacf-fr/ecoledirecte_api, GPLv3, version 0.4.0 observée. Exemple de callback QCM ; rubrique fonctionnalités encore marquée TODO. Le lien ReadTheDocs consulté renvoyait 404. Compatibilité exacte avec ce compte et Python Debian non vérifiée. |
| https://glama.ai/mcp/servers/riadh-mnasri/ecoledirecte-mcp | Catalogue consulté puis dépôt d’origine https://github.com/riadh-mnasri/ecoledirecte-mcp inspecté. MIT, TypeScript, cinq outils de lecture et cache. Pas de dashboard ni historisation répondant à ce projet. |
| https://hermes-agent.nousresearch.com/docs | Documentation Hermes et page MCP consultées ; transport stdio et `mcp_servers` documentés. Version installée inaccessible ici. |
| https://www.sqlite.org/docs.html | Base de référence SQLite, documentation des transactions, sauvegardes et pragmas ; SQLite domaine public. Version effective locale indiquée par `doctor`. |

## Choix

Un client HTTP dédié, limité aux opérations documentées, garde le nombre de dépendances réduit et permet de contrôler précisément les écritures distantes. Le protocole `Source` permet de lui substituer un client Python tiers. La GPLv3 n’est pas un obstacle à un usage privé ; l’absence de vérification de sa couverture exacte et la nécessité de contrôler les effets de bord ont motivé le choix du client dédié. Aucun code des clients tiers n’est incorporé.

Flask/Jinja et Waitress évitent une compilation JavaScript et servent directement les données SQLite. Le SDK MCP officiel est une dépendance optionnelle ; il assure le protocole stdio. Les lectures MCP ne nécessitent pas de connexion au réseau scolaire.

## Contrats retenus

Base fixe `https://api.ecoledirecte.com/v3/`, TLS vérifié, redirections refusées. Requêtes applicatives POST avec un champ form `data` JSON et `verbe` dans les paramètres. Enveloppe `code`, `data`, éventuellement renouvellement de `token`.

- GET `login.awp?gtk=1` puis POST `login.awp`, cookie conservé par la session et en-tête `X-Gtk`.
- Code 250 : `connexion/doubleauth.awp`, question/réponses base64 et choix explicitement humain ; second login avec `fa`.
- `eleves/{id}/notes.awp`, notes individuelles conservées avec barème, coefficient et période.
- `Eleves/{id}/cahierdetexte.awp` puis détail journalier `Eleves/{id}/cahierdetexte/{date}.awp`.
- `E/{id}/emploidutemps.awp`, fenêtre glissante de 21 jours.

Version configurable `ED_API_VERSION`, valeur initiale 4.101.4 mentionnée dans une capture décrite par le dépôt MCP d’origine. Ce n’est pas une promesse de compatibilité actuelle. Code 517 : vérifier la version côté fournisseur, sans essais agressifs. Les flags de publication connus sont respectés ; les moyennes cachées ne sont pas exploitées. Il reste à contrôler les paramètres d’affichage propres à l’établissement avant usage réel.

Les endpoints de messagerie peuvent avoir des effets sur la lecture : aucun appel de détail n’est activé. CAPTCHA, nouvelles MFA, protections et conditions contractuelles ne sont pas contournés. Vérifier les conditions d’utilisation applicables avant d’activer la collecte. Trois passages quotidiens, requêtes séquentielles, délais bornés et trois tentatives maximum sur les erreurs réseau/transitoires.
