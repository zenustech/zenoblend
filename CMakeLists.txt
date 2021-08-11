cmake_minimum_required(VERSION 3.10)
project(zeno_addon_wizard LANGUAGES C CXX)

if (WIN32)
    # Windows should always use Release build to prevent possible traps
    set(CMAKE_BUILD_TYPE Release)
endif()

# Enable C++17 support
set(CMAKE_CXX_STANDARD 17)

# Import ZENO
add_subdirectory(external/zeno)

# Add your project
add_subdirectory(YourProject)

# Output zeno_YourProject.dll to external/zeno/zenqt/lib
# so that ZENO editor will auto-load your extension on start up
get_property(OUTPUT_DIR TARGET zeno
    PROPERTY LIBRARY_OUTPUT_DIRECTORY)
set_target_properties(zeno_YourProject PROPERTIES
    LIBRARY_OUTPUT_DIRECTORY ${OUTPUT_DIR}
    RUNTIME_OUTPUT_DIRECTORY ${OUTPUT_DIR}
    ARCHIVE_OUTPUT_DIRECTORY ${OUTPUT_DIR}
    LIBRARY_OUTPUT_DIRECTORY_DEBUG ${OUTPUT_DIR}
    RUNTIME_OUTPUT_DIRECTORY_DEBUG ${OUTPUT_DIR}
    ARCHIVE_OUTPUT_DIRECTORY_DEBUG ${OUTPUT_DIR}
    LIBRARY_OUTPUT_DIRECTORY_RELEASE ${OUTPUT_DIR}
    RUNTIME_OUTPUT_DIRECTORY_RELEASE ${OUTPUT_DIR}
    ARCHIVE_OUTPUT_DIRECTORY_RELEASE ${OUTPUT_DIR}
    )
