from malcolm.yamlutil import make_include_creator, check_yaml_names

adbase_parts = make_include_creator(__file__, "adbase_parts.yaml")
filewriting_collection = make_include_creator(
    __file__, "filewriting_collection.yaml")
ndarray_parts = make_include_creator(__file__, "ndarray_parts.yaml")
ndpluginbase_parts = make_include_creator(__file__, "ndpluginbase_parts.yaml")

check_yaml_names(globals())
