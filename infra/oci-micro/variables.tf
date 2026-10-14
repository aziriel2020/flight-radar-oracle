variable "tenancy_ocid" {
  type = string
  description = "OCI tenancy OCID (not secret)."
}
variable "compartment_ocid" {
  type = string
  description = "Compartment where Flight Radar will be deployed."
}
variable "region" {
  type = string
  description = "Tenancy home region only; e.g. eu-frankfurt-1."
}
variable "availability_domain_index" {
  type = number
  default = 0
  description = "E2 Micro may be available in just one AD."
  validation {
    condition = var.availability_domain_index >= 0 && var.availability_domain_index <= 2
    error_message = "AD index must be 0, 1 or 2."
  }
}
variable "ssh_public_key" {
  type = string
  description = "A new SSH public key solely for this VM."
  validation {
    condition = startswith(var.ssh_public_key, "ssh-ed25519 ") || startswith(var.ssh_public_key, "ssh-rsa ")
    error_message = "Use an OpenSSH public key; never a private key."
  }
}
variable "ssh_ingress_cidr" {
  type = string
  description = "SSH client public IP /32. Not 0.0.0.0/0."
  validation {
    condition = can(cidrhost(var.ssh_ingress_cidr, 0)) && endswith(var.ssh_ingress_cidr, "/32")
    error_message = "SSH ingress must be a valid /32 address."
  }
}
