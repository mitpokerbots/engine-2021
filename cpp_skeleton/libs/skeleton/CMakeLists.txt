project(cpp-skeleton)

file(GLOB_RECURSE SKELETON_SRC ${PROJECT_SOURCE_DIR}/src/*.cpp)
file(GLOB_RECURSE SKELETON_HEADERS ${PROJECT_SOURCE_DIR}/src/*.h)

add_library(skeleton STATIC ${SKELETON_SRC})
target_include_directories(skeleton PUBLIC ${PROJECT_SOURCE_DIR}/include)

set(Boost_USE_STATIC_LIBS ON)
set(Boost_USE_MULTITHREAD OFF)

find_package(Boost REQUIRED date_time system)

include_directories(${Boost_INCLUDE_DIR})
target_link_libraries(skeleton ${Boost_SYSTEM_LIBRARY})

find_package(fmt)
target_link_libraries(skeleton fmt::fmt)
