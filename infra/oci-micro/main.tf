terraform {
  required_version = ">= 1.5.0"
  required_providers {
    oci = { source = "oracle/oci", version = ">= 6.0.0" }
  }
}
# Use the authenticated OCI profile in Oracle Cloud Shell. No credentials committed.
provider "oci" { region = var.region }

data "oci_identity_region_subscriptions" "all" { tenancy_id = var.tenancy_ocid }
data "oci_identity_availability_domains" "all" { compartment_id = var.tenancy_ocid }
data "oci_core_images" "ubuntu" {
  compartment_id   = var.compartment_ocid
  operating_system = "Canonical Ubuntu"
  shape            = "VM.Standard.E2.1.Micro"
  sort_by          = "TIMECREATED"
  sort_order       = "DESC"
}
locals {
  home_regions = [
    for r in data.oci_identity_region_subscriptions.all.region_subscriptions :
    r.region_name if r.is_home_region
  ]
  home_region = one(local.home_regions)
  tags = { project = "flight-radar", workload = "standalone", tier = "always-free" }
}
# A distinct VCN. No resource here points to Nuvio's compute, VCN or Terraform state.
resource "oci_core_vcn" "radar" {
  compartment_id = var.compartment_ocid
  cidr_block = "10.93.0.0/16"
  display_name = "flight-radar-standalone-vcn"
  dns_label = "flightradar"
  freeform_tags = local.tags
  lifecycle { prevent_destroy = true }
}
resource "oci_core_internet_gateway" "radar" {
  compartment_id = var.compartment_ocid
  vcn_id = oci_core_vcn.radar.id
  display_name = "flight-radar-igw"
  enabled = true
  freeform_tags = local.tags
}
resource "oci_core_route_table" "radar" {
  compartment_id = var.compartment_ocid
  vcn_id = oci_core_vcn.radar.id
  display_name = "flight-radar-route"
  route_rules {
    destination = "0.0.0.0/0"
    destination_type = "CIDR_BLOCK"
    network_entity_id = oci_core_internet_gateway.radar.id
  }
  freeform_tags = local.tags
}
resource "oci_core_security_list" "radar" {
  compartment_id = var.compartment_ocid
  vcn_id = oci_core_vcn.radar.id
  display_name = "flight-radar-ssh-only"
  ingress_security_rules {
    protocol = "6"
    source = var.ssh_ingress_cidr
    description = "Restricted SSH only"
    tcp_options { min = 22, max = 22 }
  }
  egress_security_rules {
    protocol = "all"
    destination = "0.0.0.0/0"
  }
  freeform_tags = local.tags
}
resource "oci_core_subnet" "radar" {
  compartment_id = var.compartment_ocid
  vcn_id = oci_core_vcn.radar.id
  cidr_block = "10.93.10.0/24"
  display_name = "flight-radar-subnet"
  dns_label = "public"
  prohibit_public_ip_on_vnic = false
  route_table_id = oci_core_route_table.radar.id
  security_list_ids = [oci_core_security_list.radar.id]
  freeform_tags = local.tags
}
resource "oci_core_instance" "radar" {
  compartment_id = var.compartment_ocid
  availability_domain = data.oci_identity_availability_domains.all.availability_domains[var.availability_domain_index].name
  display_name = "flight-radar-standalone-free"
  shape = "VM.Standard.E2.1.Micro"
  preserve_boot_volume = false
  create_vnic_details {
    subnet_id = oci_core_subnet.radar.id
    assign_public_ip = true
    display_name = "flight-radar-primary-vnic"
    hostname_label = "flight-radar"
  }
  source_details {
    source_type = "image"
    source_id = data.oci_core_images.ubuntu.images[0].id
    boot_volume_size_in_gbs = 50
  }
  metadata = { ssh_authorized_keys = var.ssh_public_key }
  freeform_tags = local.tags
  lifecycle {
    prevent_destroy = true
    precondition {
      condition = var.region == local.home_region
      error_message = "Only the tenancy HOME REGION is allowed for Always Free."
    }
  }
}
