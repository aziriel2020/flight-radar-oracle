# Second Oracle VM — isolated Always Free AMD Micro

This deploys Flight Radar to its own **Oracle VM.Standard.E2.1.Micro** instance.
It does NOT reuse the Nuvio VM, Nuvio VCN, Nuvio Terraform state, Nuvio systemd services, or Nuvio credentials.

## Why AMD Micro?

The existing `aziriel2020/nuvio-last` plan assigns an Ampere A1 VM 2 OCPUs / 12GB RAM / 100GB boot storage. Oracle's **current** Always Free A1 allocation is 2 OCPUs / 12GB total per tenancy (not another 2 OCPUs). A second free A1 VM would exceed that allocation unless Nuvio is downsized. Up to two AMD E2.1.Micro machines are a separate Always Free allowance, subject to capacity. This new instance uses 50GB, bringing known Nuvio + Flight Radar boot storage to 150GB of 200GB Always Free block volume quota, **provided there are no other volumes**.

Oracle official guide: https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm

## Safety / limitations

- Separate named resources with `flight-radar` tags; own VCN `10.93.0.0/16`.
- SSH 22 allowed from **one /32 IPv4 only**. No web ports open.
- Only six OCI resources are allowed by `guard_plan.py`; any update/delete is rejected.
- Terraform `prevent_destroy` also protects the compute instance and VCN.
- Only tenancy **home region** is permitted. There is no Terraform reference to `nuvio-last` state.
- **No auto-apply workflow**: a state-less GitHub runner could accidentally create duplicate infrastructure.
- Do not run Nuvio's existing `provision-oracle.yml`: it restores production state and can invoke `terraform destroy` after a failed attempt.
- The 1GB AMD VM is fine for a modest Python/SQLite prototype, but not a guaranteed high-throughput browser scraper. Google Flights scraping is unofficial and may be blocked.
- The system does not publicly expose the unauthenticated dashboard.

## Provision from Oracle Cloud Shell (manual, with built-in OCI login)

Open your **Oracle Cloud Console > Cloud Shell** in the home region. Use this new repository, not the Nuvio repo. You need Terraform available there (install it if `terraform version` is missing), and sufficient permissions to create compute and network resources.

```bash
git clone https://github.com/aziriel2020/flight-radar-oracle.git
cd flight-radar-oracle/infra/oci-micro
terraform version

# Generate a NEW Flight-Radar-only SSH key. Never commit this private key.
ssh-keygen -t ed25519 -f ~/.ssh/flight_radar_oci -N "" -C flight-radar-oci

# Obtain these three values from OCI Console (tenancy / compartment / home region).
export TF_VAR_tenancy_ocid="ocid1.tenancy.oc1..REPLACE_ME"
export TF_VAR_compartment_ocid="ocid1.compartment.oc1..REPLACE_ME"
export TF_VAR_region="REPLACE_WITH_TENANCY_HOME_REGION"
export TF_VAR_ssh_public_key="$(cat ~/.ssh/flight_radar_oci.pub)"
export TF_VAR_ssh_ingress_cidr="$(curl -fsS https://api.ipify.org)/32"

terraform init
terraform validate
terraform plan -out=tfplan
terraform show -json tfplan > tfplan.json
python3 guard_plan.py tfplan.json
# Inspect the plan before executing: only CREATE, E2.1.Micro, 50GB, no Nuvio changes.
terraform apply tfplan
FLIGHT_IP="$(terraform output -raw flight_radar_public_ip)"
echo "Flight Radar new VM: $FLIGHT_IP"
```

If the shape is out of capacity, try a different availability-domain index, where applicable. **Never switch automatically to a paid shape.** Check the subscription's Always Free labeling and available compute and block-storage quotas in the tenancy first.

### Install Flight Radar on the new VM

Use OCI Cloud Shell while it still has the SSH key. Once the VM is reachable:

```bash
FLIGHT_IP="$(terraform output -raw flight_radar_public_ip)"
ssh -i ~/.ssh/flight_radar_oci "ubuntu@$FLIGHT_IP" \
  'sudo apt-get update && sudo apt-get install -y git'
ssh -i ~/.ssh/flight_radar_oci "ubuntu@$FLIGHT_IP" \
  'git clone https://github.com/aziriel2020/flight-radar-oracle.git && cd flight-radar-oracle && sudo bash deploy/oci/install.sh'
ssh -i ~/.ssh/flight_radar_oci "ubuntu@$FLIGHT_IP" \
  'systemctl is-active flight-radar && curl -fsS http://127.0.0.1:18080/health'
```

Dashboard remains only on `127.0.0.1:18080` on the **new** instance. Use an SSH tunnel if needed. Google Flights real scanning is **not** enabled automatically.

### State and update safety

Terraform local state must be backed up securely. **Do not publish `terraform.tfstate`, private keys, `.tfvars`, `tfplan`, or credentials to GitHub.** OCI Cloud Shell may not be a durable Terraform backend: export and secure state off-machine or configure an appropriate remote backend before repeat operations. No provisioning is automated because safe remote state persistence is not configured.

GitHub Actions manual deployment in `deploy-oci.yml` can target this VM **after** you set its own SSH secrets in this repository and allow its runner IP in the network rules. The Nuvio repository secrets do not automatically exist here.

## Status

Infrastructure as code published, **not provisioned**. No second VM public IP, Terraform state, or successful remote HTTP health check has yet been obtained.
