set(CMAKE_LINK_WHAT_YOU_USE TRUE)

file(GLOB ZENOBLEND_SOURCE "*.cpp" "*.hpp" "*.h")
pybind11_add_module(pylib_zenoblend ${ZENOBLEND_SOURCE})

target_include_directories(pylib_zenoblend PRIVATE .)
target_link_libraries(pylib_zenoblend PRIVATE zeno)
target_link_libraries(pylib_zenoblend PRIVATE zeno_linkall)
