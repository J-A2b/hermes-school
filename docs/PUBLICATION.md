# Publier ce dossier sur GitHub

Ce dossier est une copie publique séparée de l’installation personnelle. Publier **son contenu**, pas le dossier parent qui contient des données scolaires.

Depuis PowerShell, dans ce dossier `github` :

```powershell
git init -b main
git add .
git status --short
git diff --cached --stat
```

Examiner les fichiers avant le premier commit. Aucune base, donnée scolaire, clé, capture réelle ou configuration personnelle ne doit apparaître. Le `.gitignore` n’efface pas un secret déjà commité.

```powershell
git commit -m "Initial release: Hermes School for Hermes Agent"
```

Créer un dépôt vide nommé par exemple `hermes-school` depuis GitHub. Ne pas initialiser un autre README distant. Reprendre l’URL donnée par GitHub :

```powershell
git remote add origin https://github.com/VOTRE-COMPTE/hermes-school.git
git push -u origin main
```

Description suggérée :

> Données scolaires ÉcoleDirecte locales et historisées, dashboard privé et outils MCP pour organiser son travail avec Hermes Agent.

Topics suggérés : `hermes-agent`, `mcp`, `ecoledirecte`, `python`, `sqlite`, `self-hosted`, `education`.

Après publication : vérifier les images du README, l’exécution de GitHub Actions et la licence MIT. Activer le signalement privé de vulnérabilités si disponible. Les échecs CI doivent être corrigés avant d’ajouter un badge de réussite.

Le bandeau SVG peut servir d’illustration de présentation. Les captures fournies montrent uniquement des données fictives. Le nom du dépôt et ses URLs pourront ensuite être ajoutés dans les métadonnées du projet.
