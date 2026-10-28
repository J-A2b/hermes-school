# Installation et exploitation

## Installation locale

Voir le démarrage rapide du README. Utiliser Python >=3.11 et un venv natif, jamais le venv copié depuis un autre système. `init` crée le mot de passe du dashboard, `login` établit la connexion scolaire interactive et `sync` réalise le premier import.

## Audit Debian préalable

Depuis les sources :

```bash
bash scripts/audit-debian.sh
```

Contrôler Debian, Python, RAM, disque, heure, ports, permissions et services existants. Ne pas remplacer Python système. Les exemples suivants supposent un compte SSH avec sudo et une **première installation**, sans dossiers ni compte `hermes-school` préexistants.

## Installation dédiée

```bash
sudo apt-get update
sudo apt-get install python3-venv ca-certificates curl util-linux tzdata
sudo useradd --system --user-group --no-create-home --home-dir /var/lib/hermes-school --shell /usr/sbin/nologin hermes-school
sudo install -d -o hermes-school -g hermes-school -m 0700 /var/lib/hermes-school
sudo install -d -o root -g hermes-school -m 0750 /etc/hermes-school
sudo install -d -o "$(id -un)" -g "$(id -gn)" -m 0755 /opt/hermes-school
```

Copier uniquement les sources du dépôt dans `/opt/hermes-school`, sans données ni venv. Une archive peut être produite avec `python scripts/package-deploy.py`. Après extraction, remettre explicitement le dossier de code en 755 : une copie avec préservation des permissions peut modifier ses droits.

```bash
cd /opt/hermes-school
python3 -m venv .venv
.venv/bin/python -m pip install '.[test,mcp,documents]'
.venv/bin/python -m pip check
.venv/bin/python -m pytest -q
.venv/bin/python -m pip freeze > requirements-debian.lock
sudo chown -R root:root /opt/hermes-school
sudo chmod -R go-w /opt/hermes-school
sudo chmod 0755 /opt/hermes-school
sudo install -o root -g hermes-school -m 0640 config/environment.example /etc/hermes-school/environment
```

Définir dans Bash une fonction qui charge la configuration sous le compte dédié :

```bash
hs() {
  sudo -u hermes-school /bin/sh -c '
    set -eu
    set -a
    . /etc/hermes-school/environment
    set +a
    cd /opt/hermes-school
    exec /opt/hermes-school/.venv/bin/hermes-school "$@"
  ' hermes-school "$@"
}
hs doctor
hs init
hs login
hs sync
hs status
```

La fonction est à redéfinir après reconnexion. Vérifier que `data_dir` indique `/var/lib/hermes-school`. Le champ `server_audited: false` de `doctor` est un champ fixe, pas la mesure de votre audit manuel.

## Services

```bash
sudo install -m 0644 deploy/systemd/hermes-school-*.service /etc/systemd/system/
sudo install -m 0644 deploy/systemd/hermes-school-*.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemd-analyze verify /etc/systemd/system/hermes-school-*.service /etc/systemd/system/hermes-school-*.timer
sudo systemctl enable --now hermes-school-dashboard.service
sudo systemctl start hermes-school-sync.service
sudo journalctl -u hermes-school-sync.service -n 40 --no-pager
```

Après succès du test manuel, activer les timers sync et vendredi :

```bash
sudo systemctl enable --now hermes-school-sync.timer hermes-school-friday.timer
systemctl list-timers 'hermes-school-*' --all --no-pager
```

Un service oneshot redevient inactif après succès : vérifier `Result` et `ExecMainStatus`, pas seulement le mot `inactive`. Les timers persistants peuvent rattraper une échéance après arrêt. Le portable doit rester alimenté et ne pas se suspendre pour être disponible à l’heure prévue.

## Accès depuis Windows

```powershell
ssh -N -o ExitOnForwardFailure=yes -L 127.0.0.1:8766:127.0.0.1:8765 utilisateur@serveur-tailscale
```

Ouvrir http://127.0.0.1:8766. Le fichier `Ouvrir Hermes School.cmd` peut également lancer le tunnel ; il demande une destination SSH et ne stocke aucun mot de passe. Créer un raccourci vers ce fichier pour le bureau, sans déplacer le script hors du projet.

## Accès mobile privé HTTPS

Connecter le téléphone au même tailnet. Relever le nom DNS réel du serveur dans Tailscale. Adapter `serveur.exemple.ts.net` ci-dessous ; ce nom est un exemple.

Créer `/etc/hermes-school/mobile.environment`, root-owned, groupe `hermes-school`, mode 640 :

```ini
HERMES_SCHOOL_HTTPS=1
HERMES_SCHOOL_TRUSTED_HOSTS=serveur.exemple.ts.net
```

Le service mobile charge ce fichier après la configuration commune :

```bash
sudo systemctl enable --now hermes-school-mobile.service
sudo tailscale serve --bg --https=443 http://127.0.0.1:8767
sudo tailscale serve status
```

Tailscale peut demander une activation HTTPS depuis le compte administrateur. Vérifier les éventuels services Serve existants avant de configurer le port 443. Utiliser Serve privé, sans activer Funnel. Ouvrir ensuite l’URL HTTPS annoncée et vérifier le certificat, la page de connexion et l’authentification. Le backend mobile local séparé conserve le fonctionnement du tunnel HTTP Windows.

## Sauvegarder et restaurer

```bash
sudo -u hermes-school mkdir -m 0700 /var/lib/hermes-school/backups
hs keygen --output /var/lib/hermes-school/backup.key
sudo systemctl start hermes-school-backup.service
hs restore --input /var/lib/hermes-school/backups/latest.enc --key-file /var/lib/hermes-school/backup.key --output /var/lib/hermes-school/restore-test
sudo systemctl enable --now hermes-school-backup.timer
```

La destination de restauration doit être nouvelle. La sauvegarde contient la base et les documents, pas les identifiants, clés, sessions et toutes les préférences. Conserver une copie déportée et une clé séparée. `latest.enc` est remplacé chaque nuit ; organiser des copies datées pour conserver plusieurs générations.

Pour basculer vers une restauration, arrêter les timers, travaux, dashboard, backend mobile et processus MCP. Conserver le dossier de données précédent ; remplacer le dossier complet avec ses documents, jamais seulement SQLite par-dessus un WAL existant. Recréer les accès exclus de l’archive et tester avant de réactiver les services.

## Mise à jour et retrait

Sauvegarder et tester la restauration avant une mise à jour. Arrêter tous les services scolaires et MCP, conserver l’ancien code, les données et la configuration. Reconstruire le venv au même chemin absolu, exécuter les tests, appliquer les migrations et vérifier une synchronisation avant réactivation. Un retour arrière de schéma peut nécessiter de restaurer aussi les anciennes données.

Pour désinstaller, désactiver les timers et services scolaires, retirer l’entrée MCP et les unités concernées. Conserver données, configuration et clés tant que leur suppression n’est pas explicitement souhaitée. Ne pas modifier les autres services du serveur.
