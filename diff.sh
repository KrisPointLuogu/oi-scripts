#!/bin/bash
# diff.sh - 对拍脚本
# 反复运行两个程序，对相同随机输入比较输出差异

VERSION="20240706"

CXX="g++"
CXXFLAGS=("-g" "-O2")

ITERATIONS=""

# 解析参数
while [ $# -gt 0 ]; do
    case "$1" in
        -h|--help)
            echo "用法: diff.sh [-n 迭代次数] <prog1> <prog2> <generator>"
            echo ""
            echo "反复运行两个程序，对相同随机输入比较输出差异。"
            echo ""
            echo "参数:"
            echo "  prog1, prog2, generator    源文件 (.cpp) 或已编译的可执行文件 (.out)。"
            echo "                              .cpp 文件会自动编译（缓存为 .out）。"
            echo ""
            echo "选项:"
            echo "  -n <次数>       指定测试迭代次数（默认交互询问）"
            echo "  -h, --help      显示此帮助信息"
            echo ""
            echo "示例:"
            echo "  diff.sh baoli.cpp bsfind.cpp random.cpp"
            echo "  diff.sh -n 5000 baoli.cpp bsfind.cpp random.cpp"
            exit 0
            ;;
        -n)
            if [ -z "$2" ] || [[ "$2" == -* ]]; then
                echo "错误: -n 缺少参数"
                exit 1
            fi
            ITERATIONS="$2"
            shift 2
            ;;
        --)
            shift
            break
            ;;
        -*)
            echo "错误: 未知选项 $1"
            echo "用法: diff.sh [-n 迭代次数] <prog1> <prog2> <generator>"
            exit 1
            ;;
        *)
            break
            ;;
    esac
done

if [ $# -ne 3 ]; then
    echo "错误: 需要 3 个参数，当前 $# 个"
    echo "用法: diff.sh [-n 迭代次数] <prog1> <prog2> <generator>"
    exit 1
fi

PROG1="$1"
PROG2="$2"
GEN="$3"

# 获取可执行文件路径
resolve_exe() {
    local f="$1"
    if [[ "$f" == *.out ]]; then
        echo "$f"
    elif [[ "$f" == *.cpp ]]; then
        echo "${f%.cpp}.out"
    else
        if [ -f "${f}.cpp" ]; then
            echo "${f}.out"
        elif [ -f "$f" ]; then
            echo "$f"
        else
            echo "${f}.out"
        fi
    fi
}

# 检查源文件是否存在
check_src() {
    local src="$1"
    if [[ "$src" == *.cpp ]] && [ ! -f "$src" ]; then
        echo "错误: 找不到源文件 $src"
        exit 1
    fi
}

# 获取 C++ 最高标准
detect_std() {
    if g++ -std=c++23 -dM -E -x c++ - </dev/null &>/dev/null; then
        echo "23"
    elif g++ -std=c++20 -dM -E -x c++ - </dev/null &>/dev/null; then
        echo "20"
    elif g++ -std=c++17 -dM -E -x c++ - </dev/null &>/dev/null; then
        echo "17"
    elif g++ -std=c++14 -dM -E -x c++ - </dev/null &>/dev/null; then
        echo "14"
    elif g++ -std=c++11 -dM -E -x c++ - </dev/null &>/dev/null; then
        echo "11"
    else
        echo ""
    fi
}

# 编译 .cpp 源文件
compile_if_needed() {
    local src="$1"
    if [[ "$src" != *.cpp ]]; then
        return 0
    fi
    check_src "$src"
    local target="${src%.cpp}.out"
    if [ ! -e "$target" ] || [ "$src" -nt "$target" ]; then
        echo "编译 $src ..."
        local std
        std=$(detect_std)
        if [ -n "$std" ]; then
            echo "$CXX -std=c++$std ${CXXFLAGS[*]} -o $target $src"
            $CXX "-std=c++$std" "${CXXFLAGS[@]}" -o "$target" "$src"
        else
            echo "$CXX ${CXXFLAGS[*]} -o $target $src"
            $CXX "${CXXFLAGS[@]}" -o "$target" "$src"
        fi
        if [ $? -ne 0 ]; then
            echo "编译失败: $src"
            exit 1
        fi
        echo "编译成功: $target"
    fi
}

# 解析并编译各文件
for arg in "$PROG1" "$PROG2" "$GEN"; do
    compile_if_needed "$arg"
done

EXE1=$(resolve_exe "$PROG1")
EXE2=$(resolve_exe "$PROG2")
EXEGEN=$(resolve_exe "$GEN")

# 检查可执行文件是否存在
for exe in "$EXE1" "$EXE2" "$EXEGEN"; do
    if [ ! -f "$exe" ] && [ ! -x "$exe" ]; then
        if [ ! -f "$exe" ]; then
            echo "错误: 找不到可执行文件 $exe"
            exit 1
        fi
    fi
done

# 交互询问迭代次数
if [ -z "$ITERATIONS" ]; then
    read -p "请输入迭代次数 (默认 1000): " input
    ITERATIONS="${input:-1000}"
fi

# 主循环
echo "开始对拍，共 $ITERATIONS 次..."
for i in $(seq 1 "$ITERATIONS"); do
    printf "\r%d" "$i"
    ./"$EXEGEN" > in
    ./"$EXE1" < in > out1
    ./"$EXE2" < in > out2
    diff out1 out2 || { echo -e "\n差异在第 $i 次"; exit 1; }
    rm -f in out1 out2
done
echo -e "\n全部通过！"
