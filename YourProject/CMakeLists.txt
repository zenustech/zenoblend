cmake_minimum_required(VERSION 3.10)

# ZENO extension must be a shared library with 'zeno_' as prefix:
add_library(zeno_YourProject SHARED CustomNumber.cpp MyPrimitiveOps.cpp)

# Link the libzeno.so to invoke ZENO API
target_link_libraries(zeno_YourProject PUBLIC zeno)
