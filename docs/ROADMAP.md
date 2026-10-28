# État et limites

## Version initiale disponible

Collecteur HTTP, normalisation, base SQLite historisée, synchronisation partielle, documents textuels, dashboard français, tâches et sessions locales, onze outils MCP, contexte du week-end et unités Debian.

La version d’origine a été utilisée sur un compte autorisé sous Windows puis déployée sur Debian. Ce retour d’usage ne garantit pas sa compatibilité avec tous les établissements ou les évolutions de l’API. Les tests automatisés utilisent des fixtures synthétiques. La CI du dépôt public doit encore être exécutée après publication.

## À connaître

- Messagerie distante désactivée pour éviter toute modification non autorisée du statut de lecture.
- Vie scolaire : modèle prévu, collecte non activée.
- Cours récupérés pour les dates présentes dans l’index de devoirs ; historique non exhaustif.
- Pièces jointes du cahier de textes limitées aux formats PDF textuels, DOCX et TXT ; pas d’OCR.
- Moyennes par matière indicatives ; règles officielles du bulletin non reconstruites.
- Calendrier en grille simple ; pas de planification avancée par glisser-déposer.
- Résultats MCP et recherches bornés ; absence d’un résultat ne prouve pas son inexistence.
- Notifications préparées en file mais aucun envoi actif.
- Contexte vendredi disponible, sans orchestration automatique de modèle ni passerelle de messagerie.
- Préférences de rétention partielles, aucune purge automatique.
- Une génération de sauvegarde locale ; rotation distante à organiser.
- Aucun connecteur Google Calendar ou CalDAV actuellement.

## Pistes de contribution

Validation de nouveaux contrats de réponse, indicateurs de couverture, tests d’intégration autorisés, moyennes officielles respectant les règles de visibilité, enrichissement des outils documentaires et planification plus fine. Toute extension doit conserver la confidentialité, la traçabilité et des écritures explicitement autorisées.
