create_project -force cat_chk D:/cat_chk -part xc7a100tcsg324-1
set_property ip_repo_paths D:/esn_ip_platform/ip_repo [current_project]
update_ip_catalog -rebuild
puts "IPDEFS FOUND:"
foreach d [get_ipdefs -all *esn*] { puts "  $d  ([get_property DISPLAY_NAME $d])" }
create_bd_design bd_chk
set c [create_bd_cell -type ip -vlnv [lindex [get_ipdefs -all *esn*] 0] esn_0]
puts "INSTANTIATED: $c"
report_property $c -regexp {CONFIG.*}
validate_bd_design
close_project