# Flight Radar beta sur VM Oracle partagée avec Nuvio

Date de vérification : 14 octobre 2026. Cet état peut changer.

## État actuellement vérifié

- VM Oracle existante : ARM64, ~9.7 Go RAM disponible, ~91 Go libres au moment du préflight.
- Nuvio : actif, santé HTTP 200. **Ne pas modifier** `/opt/nuvio`, `/etc/nuvio`, `/etc/caddy/Caddyfile` ou son service.
- Flight Radar : gateway localhost `127.0.0.1:18080` installé et testé HTTP 200.
- Illustrations locales : 18 SVG dans `/var/lib/flight-radar/images/destinations/`, tested from Oracle.
- Vercel : `https://flight-radar-oracle.vercel.app` publie le site, les images et les prix indiqués comme observés.
- **Blocage** : `fast-flights` retourne des erreurs de parsing depuis Oracle. Le collecteur de GitHub Actions a renvoyé de vrais relevés mais sans garantie de réservation.
- Le miroir Github → Oracle n'a **pas** été activé sur le serveur. Le script ci-dessous l'active sans modifier Nuvio ni Caddy.

## Activation unique (sur la VM Oracle)

Se connecter en SSH à la VM en utilisateur ayant `sudo`. Cette étape exige un accès Oracle valide. Aucun nouvel identifiant, port, mot de passe ou secret GitHub n'est nécessaire.

```bash
set -Eeuo pipefail
tmp="$(mktemp -d)"
git clone --depth 1 https://github.com/aziriel2020/flight-radar-oracle.git "$tmp/flight-radar"
cd "$tmp/flight-radar"
sudo bash deploy/oci/shared/enable_github_mirror.sh
```

Ce script :

1. vérifie que Nuvio, Caddy et le gateway Flight Radar sont actifs et que Nuvio répond HTTP 200 ;
2. installe `flight_radar/oracle_sync.py` et deux unités `systemd` isolées ;
3. désactive le timer qui interroge Google Flights depuis l'IP Oracle (il échoue à parser) ;
4. active le timer de miroir à 30 minutes et réalise un premier téléchargement immédiat des `data/*.json` publics GitHub ;
5. revérifie Nuvio HTTP 200 et le gateway Flight Radar.

Aucun changement de Caddy, de port public ou de service Nuvio.

## Vérification après activation

```bash
systemctl is-enabled flight-radar-sync.timer
systemctl is-active flight-radar-gateway.service
systemctl is-active nuvio.service
systemctl is-active caddy.service
curl -fsS http://127.0.0.1:18080/health
curl -fsS http://127.0.0.1:18080/api/market
sudo systemctl status flight-radar-sync.service --no-pager
sudo journalctl -u flight-radar-sync.service -n 30 --no-pager
```

Résultat attendu : timer `enabled`, services actifs, prix `observed` dans le JSON (si relevés encore présents) et santé Nuvio inchangée.

**Important :** Vercel consomme actuellement les observations directement depuis le flux public GitHub ; le miroir Oracle ajoute un stockage indépendant mais n'est pas encore le fournisseur primaire de Vercel. Aucun transfert de secrets vers Vercel ou Oracle.

## Si le miroir ne fonctionne pas

Les unités de collecte Oracle sont indépendantes de Nuvio. Ne pas relancer de collecte directe quand le fournisseur renvoie un blocage. Examiner les journaux avant toute intervention.

```bash
sudo journalctl -u flight-radar-sync.service -n 80 --no-pager
systemctl list-timers 'flight-radar-*' --all
```

Ne supprimer ni dossiers Nuvio ni règles Caddy. Sauvegardes : `/var/lib/flight-radar/backups`, timer quotidien local, aucune copie externe configurée. Les SVG générés sont des illustrations originales, **pas des photos de destination**.

## Capacité et conformité

Cette configuration vise **deux testeurs**. Les prix sont indicatifs et doivent être revérifiés auprès du vendeur ; les conditions d'utilisation et les limites du fournisseur doivent être respectées. Pas d'authentification ou de paiement dans la bêta, aucun déploiement commercial sur Vercel Hobby sans vérifier les conditions applicables.
