# FLIGHT RADAR ORACLE — prototype open source (V0.1)

Un socle exécutable pour suivre les tarifs aériens, construire un historique propre, classer les fortes baisses et diffuser **uniquement les offres vérifiées**. Écrit en Python standard (sauf collecteur optionnel), SQLite et une interface HTTP locale. Pensé pour un petit VPS ARM tel que Oracle Always Free.

## Ce qui fonctionne dans cette livraison

- Base SQLite avec historique horodaté des prix, suivi des erreurs des sources, file de candidats.
- Détection : comparaison avec le prix *minimum quotidien* observé au cours des 120 derniers jours, sur la **même route, les mêmes dates aller/retour, la même classe, le même bagage déclaré, la même compagnie et le même nombre d'escales**. Il faut au moins 8 jours de données distincts.
- Seuils configurables : au moins -25 % **et** 50 € d'écart pour devenir candidat, suppression des alertes redondantes dans les 48 h.
- Workflow `pending` → vérification de prix → `verified` → Telegram `sent` ; prix contrôlé à moins de 5 % au-dessus du prix récolté et données récentes (60 min maximum).
- Interface de supervision locale, endpoint `/api/deals`, et `/health`.
- Planificateur **70 % de suivis récurrents sur 14 jours / 30 % de découverte**, sur plusieurs aéroports et destinations (pour accumuler un historique utilisable).
- Import de données structurées JSON et adaptateur **expérimental/non officiel** `fast-flights` 3.x (sans certificat de fiabilité ni droits d'exploitation commerciale).
- 7 tests unitaires en local. Démonstration synthétique clairement étiquetée, aucune offre de vol inventée présentée comme réelle.

## Ce qui n'est PAS encore prouvé

- On n'a pas testé de collecte Google Flights **en réseau** dans ce contexte ; il faut tester sur une instance Oracle autorisée et mesurer les erreurs/limitations réelles.
- `fast-flights` utilise une interface Google non officielle : les champs de la version installée peuvent changer et l'accès peut être restreint. **Ne pas déployer un service commercial fondé sur cette source sans revue des conditions/permissions.** Aucun contournement de blocages n'est inclus.
- La correspondance exacte des tarifs aller-retour de l'outil tiers n'est pas garantie. Pour cette raison **aucune offre n'est publiée automatiquement sans deuxième vérification du prix complet**.
- On ne possède pas encore un historique statistique saisonnier suffisant ni le numéro de vol/itinéraire complet. Le comparatif est une *baisse observée*, pas un prix habituel prouvé du marché.
- Bagages, transferts autonomes, frais de paiement et possibilité réelle d'acheter doivent être vérifiés ; `baggage='unknown'` signale l'absence de certitude.
- Pas d'authentification du panneau d'administration, pas de paiement, pas de gestion de clients. **Ne pas exposer le serveur sur Internet** sans reverse proxy HTTPS, authentification, contrôle d'accès et protections de production.

## Prérequis

- Python 3.10+ ; SQLite intégré ; Linux ARM64 ou AMD64.
- Pour le connecteur Google Flights optionnel : `pip install -r requirements-optional.txt` (un réseau et des droits d'accès adéquats sont nécessaires).

## Utilisation immédiate

```bash
cd flight-radar-oracle
python3 -m venv .venv
source .venv/bin/activate
python -m flight_radar init
python -m unittest discover -s tests -v
python -m flight_radar demo
python -m flight_radar report
python -m flight_radar serve
```

Ouvrir `http://127.0.0.1:8080` **sur la machine**. En SSH distant, utiliser un tunnel :

```bash
ssh -L 8080:127.0.0.1:8080 ubuntu@IP_DU_SERVEUR
```

Accéder ensuite à `http://127.0.0.1:8080` sur le poste local. La démo doit afficher **BRU → LIS, 179 €** : il s'agit de données **100 % simulées**, pas d'un tarif trouvable aujourd'hui.

## Importer sa propre collecte, API autorisée ou fournisseur existant

```bash
python -m flight_radar scan --source json --file exemples-offres.json
```

Schéma de chaque élément du tableau JSON :

```json
{
  "origin": "BRU",
  "destination": "LIS",
  "departure_date": "2026-12-16",
  "return_date": "2026-12-23",
  "price_eur": 179,
  "carrier": "Nom vérifié de la compagnie",
  "source": "mon_fournisseur_autorise",
  "stops": 0,
  "cabin": "economy",
  "baggage": "unknown",
  "link": "https://exemple.com/recherche-de-vol",
  "details": "Prix réel à reconfirmer",
  "collected_at": "2026-10-14T12:00:00+00:00"
}
```

Pour recevoir un candidat, il faut avoir accumulé au moins huit journées de relevés sur une combinaison comparable. Les observations d'un même jour ne comptent qu'une fois dans l'historique. `collected_at` omis signifie l'heure actuelle. Après au moins huit jours distincts de surveillance d’un même couple de dates, le système dispose de sa référence minimale ; une analyse robuste demandera plus de recul. Le plan fixe une cohorte sur 14 jours pour rendre cela possible.

## Connecteur non officiel fast-flights (expérimentation seulement)

```bash
pip install -r requirements-optional.txt
python -m flight_radar plan --limit 10
python -m flight_radar scan --source fast-flights --limit 6 --allow-unofficial-collection
```

Le connecteur interroge une recherche EUR `economy`, avec au plus une escale et sans transfert autonome demandé. Il conserve un lien **de recherche** Google Flights, pas un lien de réservation garanti. Les données d’aller-retour renvoyées par l’outil tiers sont **à traiter comme candidates uniquement** jusqu’à vérification du total réel : la bibliothèque a déjà fait l’objet de signalements de résultats incomplets ou de prix divergents. Vérifier le schéma réellement retourné par la version utilisée. La conformité de la collecte et toute éventuelle utilisation commerciale restent à établir.

## Vérifier une offre avant envoi

```bash
python -m flight_radar report
# après vérification manuelle du même prix total (trajet A/R, bagages, taxes)
python -m flight_radar verify 3 --price 179
# aperçu de la notification
python -m flight_radar notify
# après définition du bot et du chat :
export TELEGRAM_BOT_TOKEN='VALEUR_SECRETE'
export TELEGRAM_CHAT_ID='CHAT_ID'
python -m flight_radar notify --send
```

Les données `DEMO_NON_REEL` ne sont jamais envoyées, même en cas de validation. L'envoi nécessite une revalidation datant de moins de 60 minutes. Une offre ancienne doit être recherchée une nouvelle fois.

## Oracle Cloud — déploiement minimal

1. Créer une VM Ubuntu ARM Ampere A1 **Always Free éligible** (selon quotas et disponibilité actuels du compte/région).
2. Mettre à jour Ubuntu et installer Python 3, `python3-venv`, `git` ; y copier ce dossier (SCP, Git ou déploiement CI).
3. Installer le venv et tester `python -m flight_radar demo` puis `python -m flight_radar serve` sur `127.0.0.1`.
4. Pour du long terme : ajouter un service `systemd` pour le tableau de bord, des tâches `systemd timer`/cron pour les scans **autorisés**, un suivi du taux d'erreurs par source et une sauvegarde quotidienne SQLite.
5. Monter ultérieurement un serveur HTTPS authentifié, et seulement ensuite l'exposer publiquement. Ne pas partager le jeton Telegram.

Voir `cron.example` pour la structure des commandes. **Ne pas activer l'exemple tel quel sans vérifier les conditions d'accès de la source.**

## Architecture évolutive

- **V0.1** : collecte JSON / outil tiers expérimental, données, seuils, tableau de supervision, Telegram contrôlé.
- **V0.2** : adaptateurs conformes pour données fournisseurs/partenaires, transactions idempotentes, tests de bout en bout, analyse de disponibilité et de frais complets.
- **V0.3** : planificateur adaptatif, couverture multi-aéroport et dates flexibles, saisonnalité, percentiles par durée, bagages, correspondances, détection des *error fares*, deuxième fournisseur de vérification.
- **V1.0** : comptes utilisateurs, alertes personnalisées, RGPD, facturation Stripe, newsletter transactionnelle avec SPF/DKIM/DMARC, limites utilisateurs et observabilité.
- **V2.0** : assistants de voyage, estimation porte-à-porte, bagages, hébergement, application mobile, espace agences/partenaires.

## Règles de qualité indispensables

- Jamais de fausse référence de prix « habituel ». Toujours indiquer période et méthode de comparaison.
- Jamais de prix aller-retour construit en multipliant arbitrairement un aller simple par deux.
- Ne pas affirmer qu'un vol est « disponible » avant une vérification récente du tarif complet et de la disponibilité.
- Distinguer le prix d'un voyageur du prix total du groupe, et le billet avec bagage de celui sans bagage.
- Horodatage et source obligatoire. Remonter les pannes de collecte, pas seulement les réussites.
- Si plusieurs sources sont en panne, afficher la fraîcheur des données et suspendre les alertes non vérifiées.
- Respecter droits de collecte et de réutilisation des données : source gratuite pour le public ≠ droits gratuits de scraping/revente.

## Ordres de grandeur de coût (hors frais variables)

L'hébergement, Python et SQLite peuvent coûter **0 € supplémentaires** tant qu'ils restent dans les limites Always Free. Néanmoins le domaine, envoi massif d'emails, acquisition clients, paiements, licences de données, maintenance et respect juridique peuvent être payants. Ce kit n'affirme pas être un service commercial rentable ou prêt à vendre.