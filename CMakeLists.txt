cmake_minimum_required(VERSION 3.16)
project(HL_DIC LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release CACHE STRING "" FORCE)
endif()

add_compile_options(-O3 -Wall -Wextra)

add_library(dic
  src/image.cpp
  src/interpolation.cpp
  src/icgn.cpp
  src/correlation.cpp
  src/synthetic.cpp)
target_include_directories(dic PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)

add_executable(dic_demo apps/dic_demo.cpp)
target_link_libraries(dic_demo PRIVATE dic)

enable_testing()
foreach(t test_linalg test_interpolation test_icgn test_correlation)
  add_executable(${t} tests/${t}.cpp)
  target_link_libraries(${t} PRIVATE dic)
  target_include_directories(${t} PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/tests)
  add_test(NAME ${t} COMMAND ${t})
endforeach()
