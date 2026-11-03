# Definitional proc to organize widgets for parameters.
proc init_gui { IPINST } {
  ipgui::add_param $IPINST -name "Component_Name"
  #Adding Page
  set Page_0 [ipgui::add_page $IPINST -name "Page 0"]
  ipgui::add_param $IPINST -name "N_IN" -parent ${Page_0}
  ipgui::add_param $IPINST -name "N_RES" -parent ${Page_0}
  ipgui::add_param $IPINST -name "READ_LAT" -parent ${Page_0}
  ipgui::add_param $IPINST -name "T_MAX" -parent ${Page_0}


}

proc update_PARAM_VALUE.N_IN { PARAM_VALUE.N_IN } {
	# Procedure called to update N_IN when any of the dependent parameters in the arguments change
}

proc validate_PARAM_VALUE.N_IN { PARAM_VALUE.N_IN } {
	# Procedure called to validate N_IN
	return true
}

proc update_PARAM_VALUE.N_RES { PARAM_VALUE.N_RES } {
	# Procedure called to update N_RES when any of the dependent parameters in the arguments change
}

proc validate_PARAM_VALUE.N_RES { PARAM_VALUE.N_RES } {
	# Procedure called to validate N_RES
	return true
}

proc update_PARAM_VALUE.READ_LAT { PARAM_VALUE.READ_LAT } {
	# Procedure called to update READ_LAT when any of the dependent parameters in the arguments change
}

proc validate_PARAM_VALUE.READ_LAT { PARAM_VALUE.READ_LAT } {
	# Procedure called to validate READ_LAT
	return true
}

proc update_PARAM_VALUE.T_MAX { PARAM_VALUE.T_MAX } {
	# Procedure called to update T_MAX when any of the dependent parameters in the arguments change
}

proc validate_PARAM_VALUE.T_MAX { PARAM_VALUE.T_MAX } {
	# Procedure called to validate T_MAX
	return true
}


proc update_MODELPARAM_VALUE.N_IN { MODELPARAM_VALUE.N_IN PARAM_VALUE.N_IN } {
	# Procedure called to set VHDL generic/Verilog parameter value(s) based on TCL parameter value
	set_property value [get_property value ${PARAM_VALUE.N_IN}] ${MODELPARAM_VALUE.N_IN}
}

proc update_MODELPARAM_VALUE.N_RES { MODELPARAM_VALUE.N_RES PARAM_VALUE.N_RES } {
	# Procedure called to set VHDL generic/Verilog parameter value(s) based on TCL parameter value
	set_property value [get_property value ${PARAM_VALUE.N_RES}] ${MODELPARAM_VALUE.N_RES}
}

proc update_MODELPARAM_VALUE.T_MAX { MODELPARAM_VALUE.T_MAX PARAM_VALUE.T_MAX } {
	# Procedure called to set VHDL generic/Verilog parameter value(s) based on TCL parameter value
	set_property value [get_property value ${PARAM_VALUE.T_MAX}] ${MODELPARAM_VALUE.T_MAX}
}

proc update_MODELPARAM_VALUE.READ_LAT { MODELPARAM_VALUE.READ_LAT PARAM_VALUE.READ_LAT } {
	# Procedure called to set VHDL generic/Verilog parameter value(s) based on TCL parameter value
	set_property value [get_property value ${PARAM_VALUE.READ_LAT}] ${MODELPARAM_VALUE.READ_LAT}
}

