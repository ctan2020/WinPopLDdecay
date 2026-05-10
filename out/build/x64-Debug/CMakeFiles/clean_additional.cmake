# Additional clean files
cmake_minimum_required(VERSION 3.16)

if("${CONFIG}" STREQUAL "" OR "${CONFIG}" STREQUAL "Debug")
  file(REMOVE_RECURSE
  "src\\CMakeFiles\\PopLDdecayGUI_autogen.dir\\AutogenUsed.txt"
  "src\\CMakeFiles\\PopLDdecayGUI_autogen.dir\\ParseCache.txt"
  "src\\PopLDdecayGUI_autogen"
  )
endif()
