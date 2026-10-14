# Oracle Cloud Always Free / Ubuntu ARM64

Create an ARM Ampere A1 VM (subject to regional availability), with SSH access and an Ubuntu image. No OCI VM is provisioned by this repository. Do not expose the unauthenticated app to the public internet.

One-time manual install:

```bash
git clone https://github.com/aziriel2020/flight-radar-oracle.git
cd flight-radar-oracle
sudo bash deploy/oci/install.sh
curl http://127.0.0.1:18080/health
```

To view your private dashboard from your laptop:

```bash
ssh -L 18080:127.0.0.1:18080 ubuntu@YOUR_OCI_PUBLIC_IP
```

Then visit http://127.0.0.1:18080.

GitHub Actions **Deploy to Oracle Cloud (manual)** requires secrets `OCI_HOST`, `OCI_USER`, `OCI_SSH_KEY`, `OCI_SSH_KNOWN_HOSTS`. Provide pinned SSH known_hosts from a trusted channel; never disable StrictHostKeyChecking. The workflow does not provision an OCI instance.

Price scans are not scheduled automatically until an approved collection source is configured. The Google Flights connector is unofficial and opt-in; respect applicable provider restrictions.

The default dashboard is internal, **not** a public-facing commercial service. Add authentication, HTTPS, backup retention and compliance before public launch.

## Sur une VM partagée

Flight Radar s'installe dans /opt/flight-radar, avec des données séparées dans /var/lib/flight-radar, un utilisateur Unix `flightradar`, et uniquement le port local `127.0.0.1:18080`. Aucun changement automatique de Nginx, Caddy, de domaines, de ports publics ou des services existants. Vérifier les ressources et les ports (`free -h`, `df -h`, `sudo ss -lntp`) avant installation. L'installateur abandonne si ce port ou son service est déjà utilisé.
