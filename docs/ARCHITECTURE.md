# Architecture

Le collecteur HTTP est isolé derrière un protocole `Source`. La normalisation, le stockage, la synchronisation, les analyses, le dashboard et les outils MCP restent séparés pour permettre de remplacer le client distant.

SQLite conserve des enregistrements identifiés par source, élève, type et identifiant distant. Le JSON original autorisé est conservé avec sa normalisation, son empreinte et ses dates d’observation. Un changement ajoute une version dans `change_events`. Des vues exposent notamment notes, devoirs, cours et emploi du temps ; les tâches, disponibilités, documents, notifications et sessions ont leurs propres structures.

Les migrations sont versionnées. Les connexions activent WAL et les clés étrangères. La synchronisation utilise des transactions par module : une réponse invalide ne doit pas importer la moitié d’un module ni effacer les données existantes. L’absence d’un objet n’est pas interprétée comme une suppression. Le premier import est distingué d’une nouvelle découverte pour limiter les alertes.

Les documents sont stockés par SHA-256 sur disque, avec provenance et texte extrait en base. FTS5 est initialisé lorsque disponible ; la recherche actuelle utilise LIKE pour rester compatible avec les builds sans FTS5.

Flask/Jinja et Waitress servent une interface sans compilation JavaScript. Les sessions sont signées, les formulaires protégés par CSRF et les téléchargements authentifiés. Les outils MCP stdio consultent le cache local : ils ne reçoivent pas les identifiants ÉcoleDirecte.

Le module du vendredi rassemble échéances, estimations et disponibilités sur 14 jours. Il ne dépend pas d’un modèle. Hermes Agent exploite ensuite ce contexte pour proposer un planning, avec les références nécessaires pour justifier ses recommandations.
