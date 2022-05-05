# bison_yacc_parser_for_payload_validations

file is generated from payload files using generator.
This generator is a key component and correctness of generator is a very important in the  end-to-end work flow.
To test the generator, we need to make sure the contents of the generated file match with the original payload files.
This requires to parse the generated file, this parsing is acheived  by implmenting yacc/bison based parser generator.
