# 个人用OI自动化脚本

一组用于刷题/比赛的日常自动化脚本：编译运行、对拍、抓取洛谷题目。

- `b`：编译并运行单个 C++ 源文件，可选自动对比答案
- `diff.sh`：对拍（stress test），比较两份代码在随机数据下的输出
- `create_luogu.py`：创建洛谷题目目录，抓取题面/标签/样例并生成 `head.yaml`

---

### b - 编译运行脚本

`./b [选项] [源文件]` 编译并运行单个 C++ 源文件。

- 省略源文件时，若当前目录只有一个 `.cpp` 会自动选中，否则用 `fzf` 选择。
- 源文件后缀可省略（如 `./b P1002` 等价于 `./b P1002.cpp`）。
- 自动检测 g++ 支持的最高 C++ 标准；默认编译参数 `-g -DDEBUG -Wall`。
- 运行输入默认读当前目录的 `in`；不存在时用 `fzf` 选择 `*in*` 文件。
- 若存在 `ans`（或唯一的 `*.ans`），运行后自动对比输出：一致提示绿色 `AC`，不一致提示红色 `WA` 并打印 diff，退出码为 1。
- 存在同名 `.in` / `.ans`（如 `P1002.in` 配 `P1002.ans`）时，会自动作为输入/答案配对。

选项：

| 选项 | 说明 |
| --- | --- |
| `-i <文件>` | 指定源文件 |
| `-o <文件>` | 把程序输出重定向到文件 |
| `-I` | 不重定向输入（不需要输入文件） |
| `-c` | 手动用 `fzf` 选择输入文件 |
| `-d` | 生成 `_debug.out` 调试可执行文件 |
| `-n` | 只编译不运行 |
| `--std <标准>` | 指定 C++ 标准，如 `--std 17` |
| `-v, --version` | 版本信息 |
| `-h, --help` | 帮助信息 |

示例：

```bash
./b                 # 自动选择源文件并运行
./b P1002.cpp       # 编译运行 P1002
./b -n P1002        # 只编译不运行
./b -I P1002        # 运行时不读输入文件
```

---

### diff.sh - 对拍脚本

`./diff.sh [-n 迭代次数] <prog1> <prog2> <generator>`

反复用 `generator` 生成随机数据喂给两个程序，比较两者输出。

- 参数可以是 `.cpp` 源文件或已编译的 `.out` 可执行文件；`.cpp` 会自动编译（结果为同名 `.out`，源文件更新时重新编译）。
- 每次生成输入到 `in`，分别运行两程序得到 `out1`、`out2` 并用 `diff` 比较。
- 一旦发现差异立即停止，输出差异发生在第几次测试，并以退出码 1 结束；全部通过则提示成功。
- `-n` 指定迭代次数，缺省时交互询问（默认 1000）。

示例：

```bash
./diff.sh baoli.cpp bsfind.cpp random.cpp
./diff.sh -n 5000 baoli.cpp bsfind.cpp random.cpp
```

---

### create_luogu

用来自动创建洛谷题目的目录并生成 `head.yaml`、`main.cpp`、`problem.md` 和样例文件。

```bash
./create_luogu.py [题号]
```

- 默认创建到 `./problem/luogu/<题号>/`，可用 `-o/--dir` 或环境变量 `LUOGU_PROBLEM_DIR` 修改。
- 自动从洛谷抓取题目标题、标签、难度、相似题目和题面，写入 `head.yaml`、`problem.md`。
- 样例输入/输出分别保存为 `in`、`in2`… 与 `ans`、`ans2`…。
- 生成 `main.cpp` 模板时不覆盖已有代码（`-f` 可覆盖）。
- 创建完成后自动进入题目目录；设置环境变量 `CREATE_LUOGU_NO_CD` 或使用 `--no-cd` 可关闭。
- 题号支持 `P1002`、`B3647`、`AT_abc208_d` 等格式。

选项：

| 选项 | 说明 |
| --- | --- |
| `-t, --title` | 题目标题 |
| `-T, --tags` | 标签，逗号分隔 |
| `-d, --desc` | 题目描述 |
| `-D, --difficulty` | 难度 |
| `-c, --common` | 相似题目 ID，逗号分隔 |
| `-f, --force` | 目录存在时直接覆盖，不询问 |
| `--no-problem-md` | 不生成 `problem.md` |
| `--no-in` | 不创建样例 `in/ans` 文件 |
| `--no-main` | 不创建 `main.cpp` |
| `--no-cd` | 创建后不自动进入目录 |
| `-o, --dir` | 题目输出根目录 |
| `-v, --version` | 版本信息 |

示例：

```bash
./create_luogu.py P1002
./create_luogu.py B3647 --no-cd
./create_luogu.py AT_abc208_d -o ./problem/luogu
```
