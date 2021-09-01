#set(CMAKE_LINK_WHAT_YOU_USE TRUE)

file(GLOB ZENOBLEND_SOURCE "*.cpp" "*.hpp" "*.h")
pybind11_add_module(pylib_zenoblend ${ZENOBLEND_SOURCE})

find_package(OpenMP)
if (TARGET OpenMP::OpenMP_CXX)
    message("found package: OpenMP::OpenMP_CXX")
    target_link_libraries(pylib_zenoblend PRIVATE OpenMP::OpenMP_CXX)
endif()

target_include_directories(pylib_zenoblend PRIVATE .)
target_link_libraries(pylib_zenoblend PRIVATE zeno)
