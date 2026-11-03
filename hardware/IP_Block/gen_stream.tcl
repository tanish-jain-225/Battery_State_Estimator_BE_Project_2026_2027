# Session 1: generate IP output products only (single thread)
set_param general.maxThreads 1
open_project D:/sys_stream/sys_stream.xpr
generate_target all [get_files sys.bd]
puts "GEN DONE"
close_project
