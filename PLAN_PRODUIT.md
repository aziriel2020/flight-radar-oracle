# FLIGHT RADAR — stratégie produit et trajectoire de lancement

**Vision** : un comparateur d'opportunités aériennes personnalisé, autonome, transparent sur le prix réel et beaucoup moins cher qu'une newsletter de « bons plans » classique. L'architecture doit découpler le fournisseur de prix, l'intelligence de classement et les canaux d'envoi. 

## 1. Trois moteurs et un orchestrateur

### A. Découverte (« chercher des occasions »)

- Explorations par pays, aéroport de départ, destinations ouvertes (« n'importe où »), saisons et durées de séjour.
- Plage initiale conseillée : BRU, CRL, CDG, ORY, LIL, AMS, EIN, DUS → destinations communes en Europe + quelques long-courriers.
- Équilibre d'échantillonnage : 70 % de recherches répétées pendant plusieurs jours pour établir des séries temporelles ; 30 % d'exploration de nouveaux trajets.
- Sources : accès approuvés ou partenariats, données ouvertes/licenciées, et **connecteurs non officiels seulement si leur usage est autorisé**. Les résultats sont stockés séparément par fournisseur.

### B. Vérification (« ce billet est-il réellement achetable ? »)

- Rechercher un prix **aller-retour total**, taxes incluses, nombre de voyageurs clair, cabine et bagages pris en compte.
- Contrôler itinéraire complet, aéroports secondaires, escales, changement d'aéroport, auto-transfert, nuit imprévue, durée, politique de remboursement et date exacte.
- Revérification à la source (ou indépendamment via un fournisseur autorisé) avant toute alerte. Mettre en quarantaine les erreurs de parsing, les devises ambiguës et les prix incohérents.
- Ne publier que les tarifs vérifiés et horodatés ; afficher un lien de recherche, pas promettre une réservation directe lorsqu'il n'y en a pas.

### C. Personnalisation (« qui veut cette offre ? »)

- Profil volontaire : aéroports de départ, distances de rabattement, budget maximal, destinations, flexibilité, vacances scolaires, bagages, cabines, temps d'escale maximum.
- « Score de voyage » = économie observée + attractivité du tarif absolu + temps de trajet + correspondances + durée du séjour + adéquation au profil + fraîcheur.
- Publication unique par segment d'intérêts, pour éviter de spammer l'intégralité des abonnés à chaque petite baisse.

### Orchestrateur

- Jobs planifiés avec « budget de requêtes », limitations par source, contrôle des erreurs, retry limité/exponential backoff sur erreurs transitoires, sans contournement des protections d'accès.
- Historique et traces de chaque offre : fournisseur, heure, prix, frais connus, anomalies et résultat de validation.
- Alerte technique si le taux de succès du collecteur chute, si les prix s'effondrent artificiellement (erreur de devise) ou si les données sont trop anciennes.

## 2. L'IA là où elle crée réellement une valeur

- **Pas de LLM sur chaque vol** : les comparaisons, percentiles, dédoublonnage et anomalies sont des algorithmes classiques peu coûteux.
- Agent de recherche : choisit les itinéraires à explorer selon la saison, la demande et l'historique.
- Agent qualité : explique les écarts, détecte des bagages manquants ou une escale déraisonnable ; ne se substitue pas à la vérification du prix.
- Agent éditorial : transforme une offre vérifiée en fiche courte, accessible, dans la langue des abonnés (FR, NL, EN).
- Agent CRM : classe et personnalise l'envoi avec consentement, déduplication et désabonnement.
- Agent croissance : instrumentation SEO, pages destinations, statistiques de conversion ; jamais fabrication de faux prix ou faux avis.
- Pour un MVP, tous ces « agents » peuvent être de simples fonctions et tâches ; n'ajouter un modèle IA local que lorsque cela améliore les résultats.

## 3. Données et modèle de détection

Trois références à ne pas confondre :

1. **Baisse observée** : prix d'aujourd'hui comparé au prix historique collecté sur la même route, les mêmes dates et conditions comparables.
2. **Bon prix de marché** : percentile parmi des itinéraires réellement comparables, avec suffisamment d'échantillons et prise en compte de la saison ; à construire plus tard.
3. **Erreur tarifaire** : prix exceptionnel suspect qui doit être revérifié et éventuellement signalé comme potentiellement annulable, jamais garanti.

L'historique initial de la V0.1 utilise la première référence uniquement. Avec le temps, augmenter la sophistication : médiane mobile pondérée, percentiles p10/p25, écart interquartile, normalisation avance avant départ, heures de voyage, options bagages.

## 4. Stratégie de coûts très bas

- Oracle Cloud Always Free : si VM disponible et quotas respectés, coût d'hébergement additionnel nul en phase pilote.
- SQLite : idéal pour des milliers à quelques centaines de milliers de relevés (index, purge et sauvegarde à prévoir). Passer à PostgreSQL si les écritures/concurrence deviennent importantes.
- Front : page HTML légère + API, CDN possible ensuite. Pas de gros framework nécessaire au départ.
- Email/Telegram : Telegram pour bêta ; pour de gros volumes de mails, service d'envoi professionnel et contrôles SPF/DKIM/DMARC.
- IA : facultative pour les scores ; calculs déterministes à coût presque nul.
- Coûts non nuls à anticiper : sources autorisées et droits de réutilisation des données, maintenance, mises à jour des collecteurs, support client, frais de paiement, TVA, RGPD, acquisition clients, éventuelles assurances / aspects juridiques.

## 5. Freemium et proposition de valeur (prix proposés, pas benchmark de marché)

| Plan | Prix client proposé | Proposition |
|---|---:|---|
| Gratuit | 0 € | Sélection de vraies offres, quelques alertes hebdomadaires |
| Plus | 19,90 €/an | Alertes personnalisées, destinations et budgets, priorité d'envoi |
| Explorer | 39,90 €/an | Plusieurs aéroports et voyageurs, business/premium, automatisations avancées |

Ne pas limiter artificiellement la qualité des données : différencier les plans par personnalisation et volume. Les programmes d'affiliation de voyages peuvent compléter les recettes **seulement si contrats et règles d'attribution l'autorisent**.

### Exemples de chiffre d'affaires théorique

- 1 000 abonnés Plus : 19 900 €/an encaissés TTC si le prix affiché inclut TVA, avant paiement, acquisition, impôts et coûts.
- 10 000 abonnés Plus : 199 000 €/an.
- 50 000 abonnés Plus : 995 000 €/an.

**Ce n'est pas du bénéfice.** La TVA peut être différente selon pays et clientèle. À titre illustratif et uniquement pour des ventes taxées à 21 % incluses dans le prix, 199 000 € TTC donnent environ 164 463 € hors TVA, avant toutes les autres charges.

Le risque principal après la collecte est l'acquisition client : si l'abonné rapporte environ 20 € TTC par an et coûte 30 € à acquérir, la rentabilité n'existe pas pendant sa première année sans rétention ou autres revenus.

## 6. Le moat compétitif (difficile à copier)

- Historique longitudinal propre des prix par itinéraire ; impossible à obtenir instantanément à une qualité homogène.
- Détection des fausses bonnes affaires : transferts multiples, bagages additionnels, surcoût porte-à-porte.
- Délai entre constat et alerte réellement utile, mesuré plutôt que promis.
- Confiance : offres vérifiées et horodatées, source indiquée, économies clairement définies.
- Personnalisation sans bruit : chaque notification doit correspondre à un profil et idéalement être actionnable.
- Acquisition organique via pages destination et bouche-à-oreille ; communauté et données constituées progressivement.

## 7. Mesures de performance

Technique : `% de recherches qui retournent un prix`, temps de collecte, taux d'échec, ancienneté p95 des tarifs, part des alertes vérifiées, taux de faux positifs, requêtes par source et par jour.

Produit : abonnés actifs, opt-in notifications, taux de clic, taux de désabonnement, « clic utile » (tarif revérifié), conversion gratuit → payant, rétention annuelle, plaintes sur les prix expirés.

Business : marge de contribution par abonné, frais variables, coût d'acquisition réel (CAC), temps de remboursement du CAC, LTV par cohorte, taux de renouvellement, impact des canaux organiques.

## 8. Plan 0 → marché

- **Jours 1–7** : installation Oracle, 10 à 30 itinéraires fixes, validation du collecteur et des accès autorisés, logs, 3 jours de tests sur prix et devises.
- **Jours 8–21** : historique sur les routes récurrentes, grille de résultats, alertes contrôlées, bêta de 20–50 personnes. Mesurer manuellement chaque offre publiée.
- **Jours 22–45** : second fournisseur si nécessaire, enrichissement bagages et escales, tableaux « offre trouvée → offre vérifiée », UI profils, consentements.
- **Jours 46–90** : test freemium et paiement, 100–500 bêta-utilisateurs, conformité RGPD et source licences, A/B test de la fréquence des notifications, analyse du CAC.
- **Après validation** : amélioration algorithmique et extension géographique. Ne pas confondre milliers de trajets scrutés et milliers d'abonnés payants.

## 9. Critère de décision

Ne pas lancer commercialement tant que le pipeline ne démontre pas sur un échantillon de plusieurs semaines que :

1. Les offres détectées sont en majorité retrouvables au prix annoncé lors du clic.
2. Les conditions tarifaires sont correctement affichées.
3. Les données sont exploitées dans le cadre des droits disponibles.
4. Le coût de production **et** de recrutement par abonné est soutenable.

Le moteur est faisable techniquement ; la validation commerciale et de données reste une étape mesurable, pas une garantie.