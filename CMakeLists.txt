cmake_minimum_required(VERSION 3.10)
set(CMAKE_CXX_STANDARD 17)
project(zeno_blender LANGUAGES C CXX)
set(CMAKE_BUILD_TYPE Debug)

set(ZENO_ENABLE_PYTHON OFF CACHE BOOL "For Embeding Usage")
set(ZENO_VISUALIZATION OFF CACHE BOOL "For Embeding Usage")
set(ZENO_GLOBALSTATE OFF CACHE BOOL "For Embeding Usage")
set(ZENO_FAULTHANDLER ON CACHE BOOL "For Embeding Usage")
set(EXTENSION_bmeshops ON CACHE BOOL "For Embeding Usage")
set(EXTENSION_oldzenbase OFF CACHE BOOL "For Embeding Usage")
set(EXTENSION_zenvdb ON CACHE BOOL "For Embeding Usage")
set(ZENOFX_ENABLE_OPENVDB ON CACHE BOOL "For Embeding Usage")
add_subdirectory(external/zeno)

include_directories(include)

add_subdirectory(external/pybind11)
add_subdirectory(zenoblend)

