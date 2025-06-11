# This file makes Python treat the `code_generator` directory as a package.
# It can also be used to expose parts of the package's API.
# For now, it's kept simple.
from .python_generator import create_new_script, add_function_to_script
