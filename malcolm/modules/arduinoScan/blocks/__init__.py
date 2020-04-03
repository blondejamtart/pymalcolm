from malcolm.yamlutil import make_block_creator, check_yaml_names

arduino_motor_block = make_block_creator(__file__, "arduino_motor_block.yaml")
test_scan_scan = make_block_creator(__file__, "test_scan_scan.yaml")

__all__ = check_yaml_names(globals())
