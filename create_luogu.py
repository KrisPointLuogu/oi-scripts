#!/usr/bin/env python3
import os
import re
import sys
import shlex
import time
import argparse
import json
import yaml
import requests

# ============================================================
# 配置区：所有可调参数集中在这里，改这里就行
# ============================================================
VERSION = "20261122"

# ---- 目录与 URL ----
OJ = "luogu"

# 题目输出根目录，默认相对「运行脚本时所在目录」，即 ./problem/luogu。
# 想改路径：直接改这里，或用命令行 -o/--dir，或设环境变量 LUOGU_PROBLEM_DIR。
DEFAULT_PROBLEM_DIR = os.path.join(".", "problem", OJ)
LUOGU_URL = "https://www.luogu.com.cn/problem/{problem_id}"
TAG_API_URL = "https://www.luogu.com.cn/_lfe/tags/zh-CN"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# ---- 网络重试 ----
HTTP_RETRIES = 3            # 请求重试次数
HTTP_TIMEOUT = 15           # 题目页抓取超时（秒）
TAG_TIMEOUT = 10            # 标签接口超时（秒）
RETRY_SLEEP = 1.0           # 通用重试等待：RETRY_SLEEP * 尝试次数
PAGE_RETRY_SLEEP = 1.5      # 题目页重试等待基数

# ---- 生成的文件名 ----
HEAD_YAML_NAME = "head.yaml"
MAIN_CPP_NAME = "main.cpp"
PROBLEM_MD_NAME = "problem.md"
SAMPLE_IN_PREFIX = "in"     # in、in2、in3……
SAMPLE_ANS_PREFIX = "ans"   # ans、ans2、ans3……

# ---- 环境变量 ----
NO_CD_ENV = "CREATE_LUOGU_NO_CD"  # 设置后创建完不自动进入目录

MAIN_CPP_TEMPLATE = """#include <bits/stdc++.h>
using namespace std;

const int maxn = 1e6 + 5;
int n, m;

int main(int argc, char const *argv[])
{
    
    return 0;
}
"""

DIFFICULTY_MAP = {
    0: "暂无评定", 1: "入门", 2: "普及-", 3: "普及/提高-",
    4: "普及+/提高", 5: "提高+/省选-", 6: "省选/NOI-",
    7: "NOI", 8: "NOI+/CTSC",
}

PROBLEM_ID_RE = re.compile(r"^(?:[PBTU]\d+|UVA\d+|SP\d+|CF\d+[A-Z0-9]*|AT_[A-Za-z0-9_]+)$")


def normalize_problem_id(raw):
    pid = raw.strip()
    if pid[:3].upper() == "AT_":
        return "AT_" + pid[3:]
    return pid.upper()


_SESSION = None
_CACHED_PAGE = {}


def _get_session():
    global _SESSION
    if _SESSION is None:
        _SESSION = requests.Session()
        _SESSION.headers.update({"User-Agent": USER_AGENT})
    return _SESSION


def _request_with_retry(url, retries=HTTP_RETRIES, timeout=HTTP_TIMEOUT):
    session = _get_session()
    last_err = None
    for attempt in range(retries):
        try:
            r = session.get(url, timeout=timeout)
            r.raise_for_status()
            return r
        except requests.RequestException as e:
            last_err = e
            if attempt < retries - 1:
                time.sleep(RETRY_SLEEP * (attempt + 1))
    raise last_err


def fetch_tag_map():
    try:
        r = _request_with_retry(TAG_API_URL, timeout=TAG_TIMEOUT)
        data = r.json()
        return {t["id"]: t for t in data.get("tags", [])}
    except Exception:
        return {}


def fetch_page_data(problem_id, retries=HTTP_RETRIES):
    if problem_id in _CACHED_PAGE:
        return _CACHED_PAGE[problem_id]

    for attempt in range(retries):
        try:
            r = _request_with_retry(LUOGU_URL.format(problem_id=problem_id), retries=1, timeout=HTTP_TIMEOUT)
            m = re.search(r'<script id="lentille-context" type="application/json">(.*?)</script>', r.text, re.DOTALL)
            if m:
                data = json.loads(m.group(1))
                _CACHED_PAGE[problem_id] = data
                return data
        except Exception:
            pass
        if attempt < retries - 1:
            time.sleep(PAGE_RETRY_SLEEP * (attempt + 1))
    return None


def get_problem_title(problem_id):
    data = fetch_page_data(problem_id)
    return data["data"]["problem"].get("name", "") if data else ""


def get_problem_tags(problem_id):
    data = fetch_page_data(problem_id)
    if not data:
        return []
    tag_ids = data["data"]["problem"].get("tags", [])
    if not tag_ids:
        return []

    tag_map = fetch_tag_map()
    if not tag_map:
        return []
    return [
        tag_map[t]["name"]
        for t in tag_ids
        if t in tag_map and tag_map[t].get("type") == 2
    ]


def get_problem_difficulty(problem_id):
    data = fetch_page_data(problem_id)
    if not data:
        return ""
    diff_num = data["data"]["problem"].get("difficulty")
    if isinstance(diff_num, int):
        return DIFFICULTY_MAP.get(diff_num, "")
    return str(diff_num) if diff_num else ""


def get_problem_description(problem_id):
    data = fetch_page_data(problem_id)
    if not data:
        return ""
    problem = data["data"]["problem"]
    contenu = problem.get("contenu") or problem.get("content", {})
    return (contenu.get("description") or "").strip()


def fetch_similar_problems(problem_id):
    data = fetch_page_data(problem_id)
    if not data:
        return []
    recommendations = data["data"].get("recommendations", [])
    return [r["pid"] for r in recommendations if r.get("pid")]


def build_problem_md(data):
    problem = data["data"]["problem"]
    contenu = problem.get("contenu") or problem.get("content", {})
    title = contenu.get("name") or problem.get("name") or ""
    background = (contenu.get("background") or "").strip()
    description = (contenu.get("description") or "").strip()
    formatI = (contenu.get("formatI") or "").strip()
    formatO = (contenu.get("formatO") or "").strip()
    hint = (contenu.get("hint") or "").strip()
    samples = problem.get("samples", [])

    lines = []
    lines.append(f"# {title}")
    lines.append("")

    if background:
        lines.append("## 题目背景")
        lines.append("")
        lines.append(background)
        lines.append("")

    lines.append("## 题目描述")
    lines.append("")
    lines.append(description)
    lines.append("")

    lines.append("## 输入格式")
    lines.append("")
    lines.append(formatI)
    lines.append("")

    lines.append("## 输出格式")
    lines.append("")
    lines.append(formatO)
    lines.append("")

    for i, (inp, out) in enumerate(samples, 1):
        lines.append(f"## 输入输出样例 #{i}")
        lines.append("")
        lines.append("**输入**")
        lines.append("```")
        lines.append(inp.rstrip("\n"))
        lines.append("```")
        lines.append("")
        lines.append("**输出**")
        lines.append("```")
        lines.append(out.rstrip("\n"))
        lines.append("```")
        lines.append("")

    if hint:
        lines.append("## 提示")
        lines.append("")
        lines.append(hint)
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def prompt(label, default=None):
    if default is not None:
        prompt_text = f"{label} (default={default}): "
    else:
        prompt_text = f"{label}: "
    val = input(prompt_text).strip()
    if not val and default is not None:
        return default
    return val


def write_yaml(dirpath, data):
    os.makedirs(dirpath, exist_ok=True)
    filepath = os.path.join(dirpath, HEAD_YAML_NAME)
    with open(filepath, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    return filepath


def write_file(dirpath, filename, content):
    filepath = os.path.join(dirpath, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    return filepath


def write_main_cpp(dirpath, force=False):
    """创建 main.cpp，已存在且未指定 force 时不覆盖，避免冲掉已有代码。"""
    filepath = os.path.join(dirpath, MAIN_CPP_NAME)
    if os.path.exists(filepath) and not force:
        return None
    return write_file(dirpath, MAIN_CPP_NAME, MAIN_CPP_TEMPLATE)


def write_samples(dirpath, samples, force=False):
    """把每个样例输入写入 in、in2、in3……，期望输出写入 ans、ans2、ans3……

    输入与答案各自独立判断，已存在且未指定 force 时跳过。返回已创建或更新的
    文件路径列表。
    """
    created = []
    for idx, sample in enumerate(samples, 1):
        if isinstance(sample, (list, tuple)):
            inp = sample[0]
            out = sample[1] if len(sample) > 1 and sample[1] is not None else ""
        else:
            inp = sample
            out = ""

        in_name = SAMPLE_IN_PREFIX if idx == 1 else f"{SAMPLE_IN_PREFIX}{idx}"
        ans_name = SAMPLE_ANS_PREFIX if idx == 1 else f"{SAMPLE_ANS_PREFIX}{idx}"

        in_path = os.path.join(dirpath, in_name)
        if force or not os.path.exists(in_path):
            content = inp if inp.endswith("\n") else inp + "\n"
            with open(in_path, "w", encoding="utf-8") as f:
                f.write(content)
            created.append(in_path)

        if out:
            ans_path = os.path.join(dirpath, ans_name)
            if force or not os.path.exists(ans_path):
                content = out if out.endswith("\n") else out + "\n"
                with open(ans_path, "w", encoding="utf-8") as f:
                    f.write(content)
                created.append(ans_path)
        else:
            print(f"警告: 第 {idx} 个样例缺少输出，跳过 {ans_name}")
    return created


def jump_to_problem_dir(dirpath):
    """创建完成后进入题目目录。

    Python 无法修改父 shell 的工作目录，因此在交互式终端里直接 exec 一个
    子 shell（当前终端内 cd 到目标目录），非交互场景则打印 cd 命令。
    """
    target = os.path.abspath(dirpath)
    rel = os.path.relpath(target)

    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        print(f"请执行: cd {shlex.quote(rel)}")
        return

    shell = os.environ.get("SHELL") or "/bin/sh"
    print(f"正在进入目录: {rel}")
    print("（退出该 shell 后返回原目录）")
    sys.stdout.flush()
    try:
        os.chdir(target)
        os.execvp(shell, [shell])
    except OSError as e:
        print(f"无法启动 shell ({e})，请手动执行: cd {shlex.quote(rel)}")


def main():
    parser = argparse.ArgumentParser(description="创建 Luogu 题目目录及 head.yaml、main.cpp、problem.md，并进入题目目录")
    parser.add_argument("--version", "-v", action="version", version=f"{os.path.basename(__file__)} {VERSION}")
    parser.add_argument("problem_id", help="题目 ID，如 P1002、B3647 或 AT_abc208_d")
    parser.add_argument("--title", "-t", help="题目标题")
    parser.add_argument("--tags", "-T", help="标签，逗号分隔")
    parser.add_argument("--desc", "-d", help="题目描述")
    parser.add_argument("--difficulty", "-D", help="难度")
    parser.add_argument("--common", "-c", help="相似题目 ID，逗号分隔")
    parser.add_argument("--force", "-f", action="store_true", help="目录存在时直接覆盖，不询问")
    parser.add_argument("--no-problem-md", action="store_true", help="不抓取 problem.md")
    parser.add_argument("--no-in", action="store_true", help="不创建样例 in/ans 文件")
    parser.add_argument("--no-main", action="store_true", help="不创建 main.cpp")
    parser.add_argument("--no-cd", action="store_true", help="创建完成后不自动进入题目目录")
    parser.add_argument("--dir", "-o", dest="out_dir", help=f"题目输出根目录，默认 {DEFAULT_PROBLEM_DIR}")
    args = parser.parse_args()

    problem_id = normalize_problem_id(args.problem_id)
    if not PROBLEM_ID_RE.match(problem_id):
        print("错误：题目 ID 格式应如 P1002、B3647、AT_abc208_d")
        sys.exit(1)

    problem_dir = args.out_dir or os.environ.get("LUOGU_PROBLEM_DIR") or DEFAULT_PROBLEM_DIR
    dirpath = os.path.join(problem_dir, problem_id)

    if os.path.exists(dirpath):
        if args.force:
            print("目录已存在，因 -f 参数直接覆盖")
        else:
            ans = input(f"目录 {os.path.relpath(dirpath)} 已存在，覆盖? (y/N): ").strip().lower()
            if ans != "y":
                print("已取消")
                return

    auto_title = get_problem_title(problem_id)
    auto_tags = get_problem_tags(problem_id)
    auto_desc = get_problem_description(problem_id)
    auto_diff = get_problem_difficulty(problem_id)
    auto_common = fetch_similar_problems(problem_id)

    if auto_title:
        print(f"自动获取标题: {auto_title}")
    if auto_tags:
        print(f"自动获取标签: {', '.join(auto_tags)}")
    if auto_diff:
        print(f"自动获取难度: {auto_diff}")
    if auto_common:
        print(f"自动获取相似题目: {', '.join(auto_common)}")
    if auto_desc:
        print(f"自动获取描述: {auto_desc[:60]}{'...' if len(auto_desc) > 60 else ''}")

    has_cli_flag = any(getattr(args, f) is not None for f in ["title", "tags", "desc", "difficulty"])
    interactive = not has_cli_flag

    data = {"oj": OJ, "problem": problem_id}

    if interactive:
        title = prompt("title", default=auto_title or "")
        raw_tags = prompt("tags (逗号分隔)", default=",".join(auto_tags))
        desc = prompt("description", default=auto_desc or "")
        diff = prompt("difficulty", default=auto_diff or "")
    else:
        title = args.title if args.title is not None else (auto_title or "")
        raw_tags = args.tags if args.tags is not None else (",".join(auto_tags) if auto_tags else "")
        desc = args.desc if args.desc is not None else (auto_desc or "")
        diff = args.difficulty if args.difficulty is not None else (auto_diff or "")

    data["title"] = title
    tags = [t.strip() for t in raw_tags.split(",") if t.strip()] if raw_tags else []
    data["tags"] = tags
    data["description"] = desc
    data["difficulty"] = diff
    data["source"] = LUOGU_URL.format(problem_id=problem_id)

    if interactive:
        common_raw = prompt("common (逗号分隔)", default=",".join(auto_common) if auto_common else "")
        common = [c.strip() for c in common_raw.split(",") if c.strip()] if common_raw else []
    else:
        if args.common is not None:
            common_raw = args.common
        elif auto_common:
            common_raw = ",".join(auto_common)
        else:
            print("错误: 无法自动获取相似题目，请手动输入")
            common_raw = input("common (逗号分隔): ").strip()
        common = [c.strip() for c in common_raw.split(",") if c.strip()] if common_raw else []
    data["common"] = common

    os.makedirs(dirpath, exist_ok=True)
    yaml_path = write_yaml(dirpath, data)
    print(f"已创建: {os.path.relpath(yaml_path)}")

    if not args.no_main:
        main_path = write_main_cpp(dirpath, force=args.force)
        if main_path:
            print(f"已创建: {os.path.relpath(main_path)}")
        else:
            print("main.cpp 已存在，跳过（使用 -f 可覆盖）")

    if not args.no_problem_md or not args.no_in:
        page_data = None
        try:
            page_data = fetch_page_data(problem_id)
        except Exception as e:
            print(f"警告: 抓取页面数据失败 ({e})")

        if not args.no_problem_md:
            if page_data:
                md = build_problem_md(page_data)
                md_path = write_file(dirpath, PROBLEM_MD_NAME, md)
                print(f"已创建: {os.path.relpath(md_path)}")
            else:
                print("警告: 无法解析页面数据，跳过 problem.md")

        if not args.no_in:
            samples = page_data["data"]["problem"].get("samples", []) if page_data else []
            if samples:
                created = write_samples(dirpath, samples, force=args.force)
                for p in created:
                    print(f"已创建: {os.path.relpath(p)}")
                if not created:
                    print("样例 in/ans 文件已存在，跳过（使用 -f 可覆盖）")
            else:
                print("警告: 无样例数据，跳过 in/ans 文件")

    if not args.no_cd and not os.environ.get(NO_CD_ENV):
        jump_to_problem_dir(dirpath)


if __name__ == "__main__":
    main()
