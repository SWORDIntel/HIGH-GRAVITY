cmake_minimum_required(VERSION 3.16)
project(highgravity_hmi LANGUAGES CXX)

find_package(Vulkan QUIET)
find_package(PkgConfig QUIET)
if(PkgConfig_FOUND)
    pkg_check_modules(XCB QUIET xcb)
endif()

add_library(highgravity_hmi STATIC hmi_ingest.cpp hmi_telemetry.cpp)
target_include_directories(highgravity_hmi PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
target_compile_features(highgravity_hmi PUBLIC cxx_std_17)
target_link_libraries(highgravity_hmi PUBLIC pthread)
if(Vulkan_FOUND)
    target_link_libraries(highgravity_hmi PUBLIC Vulkan::Vulkan)
endif()

add_executable(hmi_validate hmi_validate.cpp)
target_link_libraries(hmi_validate PRIVATE highgravity_hmi)

add_executable(hmi_telemetry_validate hmi_telemetry_validate.cpp)
target_link_libraries(hmi_telemetry_validate PRIVATE highgravity_hmi)

add_executable(hmi_runner hmi_runner.cpp)
target_link_libraries(hmi_runner PRIVATE highgravity_hmi)
if(Vulkan_FOUND AND XCB_FOUND)
    target_compile_definitions(hmi_runner PRIVATE HG_HMI_RUNNER_ENABLE_NATIVE)
    target_include_directories(hmi_runner PRIVATE ${XCB_INCLUDE_DIRS})
    target_link_libraries(hmi_runner PRIVATE Vulkan::Vulkan ${XCB_LIBRARIES})
    target_link_directories(hmi_runner PRIVATE ${XCB_LIBRARY_DIRS})
endif()

enable_testing()
add_test(NAME hmi_validate COMMAND $<TARGET_FILE:hmi_validate>)
add_test(NAME hmi_telemetry_validate COMMAND $<TARGET_FILE:hmi_telemetry_validate>)

find_program(GLSLC_EXECUTABLE glslc)
if(GLSLC_EXECUTABLE)
    file(MAKE_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/shaders)
    add_custom_command(
        OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/shaders/dashboard.vert.spv
        COMMAND ${GLSLC_EXECUTABLE}
                -fshader-stage=vert
                ${CMAKE_CURRENT_SOURCE_DIR}/shaders/dashboard.vert
                -o ${CMAKE_CURRENT_BINARY_DIR}/shaders/dashboard.vert.spv
        DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/shaders/dashboard.vert
        VERBATIM
    )
    add_custom_command(
        OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/shaders/dashboard.frag.spv
        COMMAND ${GLSLC_EXECUTABLE}
                -fshader-stage=frag
                ${CMAKE_CURRENT_SOURCE_DIR}/shaders/dashboard.frag
                -o ${CMAKE_CURRENT_BINARY_DIR}/shaders/dashboard.frag.spv
        DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/shaders/dashboard.frag
        VERBATIM
    )
    add_custom_target(highgravity_hmi_shaders
        DEPENDS
            ${CMAKE_CURRENT_BINARY_DIR}/shaders/dashboard.vert.spv
            ${CMAKE_CURRENT_BINARY_DIR}/shaders/dashboard.frag.spv)
endif()
