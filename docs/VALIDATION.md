# Vérifications de la copie publique

Préparation : 29 octobre 2026, Windows avec Python 3.14.

- Suite exécutée sur les sources publiques : 48 tests réussis, un test POSIX ignoré sous Windows.
- Trois captures générées avec un serveur temporaire et exclusivement les données synthétiques de la commande `demo`.
- Connexion de démonstration, rendu desktop/mobile et absence d’erreur JavaScript vérifiés pendant la capture.
- Vérification des références locales du README, des fichiers distribués et des marqueurs personnels connus.
- Construction du paquet wheel réussie, avec métadonnées MIT et licence distribuée.
- Aucun dossier de données, secret, base SQLite ou historique Git personnel copié.

Ces vérifications ne constituent pas un audit de sécurité indépendant. Le workflow GitHub Actions Linux/Windows fourni reste à exécuter sur le futur dépôt ; aucune exécution distante de CI n’est présumée.

Pour refaire les captures : installer Playwright et son Chromium dans un environnement de développement, puis exécuter `python scripts/create-previews.py --python CHEMIN_DU_PYTHON_DU_VENV`. Ne pas utiliser de données réelles pour les illustrations publiques.
