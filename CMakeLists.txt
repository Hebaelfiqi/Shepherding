# CMakeLists.txt  -  headless Linux build for the Shepherding Library
#
# Place this file at the repository root, next to ClassLibraryProjects.sln.
# It does NOT replace the Visual Studio solution; it is an additional, Linux-friendly
# way to build the simulation core without SDL2 and without MSXML/COM.
#
# Prerequisites (Milestone M0.5 in REQUIREMENTS.md), done once before this builds cleanly:
#   1. In ShepherdingLibC/stdafx.h and ShepherdingSimC_V1/pch.h, guard the Windows includes:
#         #ifdef _WIN32
#         #include <windows.h>
#         #endif
#   2. Vendor tinyxml2 into third_party/tinyxml2/ (tinyxml2.h, tinyxml2.cpp), and reimplement
#      the config loader against it (replace the MSXML6/COM code in ShepherdingSimC_V1.cpp).
#   3. Add ShepherdingSimC_V1/main_headless.cpp: a main() that loads the config with the portable
#      loader, runs the Sim loop, writes CSV, and uses NO SDL and NO COM.
#
# Then:
#   cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
#   cmake --build build -j
#   ./build/shepherd_sim InputFiles/Config.xml

cmake_minimum_required(VERSION 3.16)
project(Shepherding LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release)
endif()

# ----------------------------------------------------------------------------
# 1) The physics library (portable core of ShepherdingLibC).
#    Explicit list so the Windows-only translation units are excluded:
#      - dllmain.cpp                     (DLL entry point)
#      - Properties/AssemblyInfo.cpp     (Windows assembly attributes)
# ----------------------------------------------------------------------------
set(LIBC ShepherdingLibC)
add_library(shepherding STATIC
  ${LIBC}/Agents.cpp
  ${LIBC}/Behaviors.cpp
  ${LIBC}/Environment.cpp
  ${LIBC}/Flock.cpp
  ${LIBC}/Modules.cpp
  ${LIBC}/SheepAgent.cpp
  ${LIBC}/SheepDogAgent.cpp
  ${LIBC}/ShepherdingLibC.cpp
  ${LIBC}/Terrain.cpp
  ${LIBC}/Time.cpp
  ${LIBC}/Traits.cpp
  ${LIBC}/Utilities.cpp
  ${LIBC}/stdafx.cpp
)
target_include_directories(shepherding PUBLIC ${LIBC} ShepherdingSimC_V1)

# ----------------------------------------------------------------------------
# 2) Portable XML parser for the config loader (vendored in M0.5).
# ----------------------------------------------------------------------------
# add_library(tinyxml2 STATIC third_party/tinyxml2/tinyxml2.cpp)
# target_include_directories(tinyxml2 PUBLIC third_party/tinyxml2)

# ----------------------------------------------------------------------------
# 3) Headless simulation executable.
#    Reuses the portable core sim files. Excludes Visualization.cpp (SDL2) and the
#    original ShepherdingSimC_V1.cpp (MSXML/COM/SDL main).
#    TODO(M0.5): add ShepherdingSimC_V1/main_headless.cpp and the portable config loader,
#                then uncomment tinyxml2 above and in target_link_libraries below.
# ----------------------------------------------------------------------------
set(SIM ShepherdingSimC_V1)
add_executable(shepherd_sim
  ${SIM}/Sim.cpp
  ${SIM}/SupportingCalc.cpp
  ${SIM}/CLI.cpp
  # ${SIM}/main_headless.cpp        # TODO(M0.5): create this
  # ${SIM}/ConfigLoaderPortable.cpp # TODO(M0.5): tinyxml2-based loader extracted from the old main
)
target_include_directories(shepherd_sim PRIVATE ${SIM} ${LIBC})
target_link_libraries(shepherd_sim PRIVATE shepherding)   # add tinyxml2 once vendored

# ----------------------------------------------------------------------------
# 4) Tests (Milestone M4+; see REQUIREMENTS.md Section 6).
# ----------------------------------------------------------------------------
# enable_testing()
# add_executable(unit_tests tests/unit_tests.cpp)
# target_link_libraries(unit_tests PRIVATE shepherding)
# add_test(NAME unit_tests COMMAND unit_tests)
