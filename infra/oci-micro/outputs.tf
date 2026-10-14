output "flight_radar_instance_id" {
  value = oci_core_instance.radar.id
}
output "flight_radar_public_ip" {
  value = oci_core_instance.radar.public_ip
}
output "private_health_url" {
  value = "http://127.0.0.1:18080/health"
}
