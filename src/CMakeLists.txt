# zlib: 基于当前源码目录，避免硬编码旧机器路径；EXISTS 检查防止静默用错路径
set(_ZLIB_BASE "${CMAKE_CURRENT_SOURCE_DIR}/zlib-develop/zlib-develop")
set(ZLIB_INCLUDE_DIR "${_ZLIB_BASE}")
set(ZLIB_LIBRARY "${_ZLIB_BASE}/build/libz.dll.a")
if(NOT EXISTS "${ZLIB_INCLUDE_DIR}")
  message(FATAL_ERROR "ZLIB include dir not found: ${ZLIB_INCLUDE_DIR}")
endif()
if(NOT EXISTS "${ZLIB_LIBRARY}")
  message(FATAL_ERROR "ZLIB library not found: ${ZLIB_LIBRARY}")
endif()

set(PROJECT_SOURCES
    main.cpp
    mainwindow.cpp
    mainwindow.h
    mainwindow.ui
    # PopLDdecay 源码文件
    Calculate.h
    CommFun.h
    CommFun.cpp
    DataClass.h
    EHHDeal.h
    FileDeal.h
    HeadIN.h
    LD_Decay.cpp
    PariWiseCal.h
    ProMethod1.h
    ProMethod2.h
    gzstream.cpp
    FilterGenotype.cpp
    # tmpcrc 子文件夹下的源码
    tmpcrc/ProMethod2.h
    tmpcrc/ProMethod3.h
    tmpcrc/FileDeal.h
    #tmpcrc/LD_Decay.cpp
    tmpcrc/ProMethod1.h
)

add_executable(PopLDdecayGUI
    ${PROJECT_SOURCES}
)

# 避免链接时旧 exe 被占用导致 Permission denied，改用不同输出名
set_target_properties(PopLDdecayGUI PROPERTIES
    OUTPUT_NAME "PopLDdecayGUI_run"
)

# 将 Python 脚本自动复制到运行目录（build/.../src），避免手动拷贝
add_custom_command(TARGET PopLDdecayGUI POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy_if_different
        "${CMAKE_CURRENT_SOURCE_DIR}/../../LICENSE"
        "$<TARGET_FILE_DIR:PopLDdecayGUI>/LICENSE"
    COMMAND ${CMAKE_COMMAND} -E copy_if_different
        "${CMAKE_CURRENT_SOURCE_DIR}/plot_lddecay_multi.py"
        "$<TARGET_FILE_DIR:PopLDdecayGUI>/plot_lddecay_multi.py"
    COMMAND ${CMAKE_COMMAND} -E copy_if_different
        "${CMAKE_CURRENT_SOURCE_DIR}/split_large_vcf.py"
        "$<TARGET_FILE_DIR:PopLDdecayGUI>/split_large_vcf.py"
)

include_directories(${ZLIB_INCLUDE_DIR})
target_link_libraries(PopLDdecayGUI PRIVATE
    Qt6::Widgets
    Qt6::Charts
    ${ZLIB_LIBRARY}
)
