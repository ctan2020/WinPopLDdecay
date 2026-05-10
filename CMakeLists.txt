cmake_minimum_required(VERSION 3.16)
project(PopLDdecayGUI VERSION 1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Set MinGW compiler
set(CMAKE_C_COMPILER "C:/Qt/Tools/mingw1310_64/bin/gcc.exe")
set(CMAKE_CXX_COMPILER "C:/Qt/Tools/mingw1310_64/bin/g++.exe")

set(CMAKE_AUTOMOC ON)
set(CMAKE_AUTORCC ON)
set(CMAKE_AUTOUIC ON)

# Add Qt installation directory to the prefix path
set(CMAKE_PREFIX_PATH "C:/Qt/6.9.1/mingw_64")

# Make sure MinGW tools are in the path
set(CMAKE_MAKE_PROGRAM "C:/Qt/Tools/mingw1310_64/bin/mingw32-make.exe")
set(QT_QMAKE_EXECUTABLE "C:/Qt/6.9.1/mingw_64/bin/qmake.exe")

# Print paths for debugging
message(STATUS "CMAKE_PREFIX_PATH: ${CMAKE_PREFIX_PATH}")
message(STATUS "CMAKE_C_COMPILER: ${CMAKE_C_COMPILER}")
message(STATUS "CMAKE_CXX_COMPILER: ${CMAKE_CXX_COMPILER}")

find_package(Qt6 COMPONENTS Widgets Charts REQUIRED)
if(NOT Qt6_FOUND)
    message(FATAL_ERROR "Qt6 not found. Please set CMAKE_PREFIX_PATH to your Qt installation directory.")
endif()

add_subdirectory(src) 