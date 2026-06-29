#!/usr/bin/env bash
# ============================================================
#  project_audit.sh —— Python 项目"真实体检"一键脚本
# ------------------------------------------------------------
#  用法:
#     bash project_audit.sh [源码包目录] [测试命令]
#  例:
#     bash project_audit.sh src/myapp "-m pytest -q"
#     bash project_audit.sh                 # 自动探测,跳过覆盖率
#
#  所有产物输出到 ./_audit/ ,这些都是从代码直接提取的"事实",
#  不经过任何 LLM 脑补。跑完后按 _audit/00_INDEX.md 的指引喂给模型。
# ============================================================

set -uo pipefail

SRC="${1:-}"
TEST_CMD="${2:-}"
OUT="_audit"
VENV=".audit_venv"
PY="python3"

mkdir -p "$OUT"

log()  { printf '\n\033[1;36m▶ %s\033[0m\n' "$*"; }
ok()   { printf '\033[1;32m  ✓ %s\033[0m\n' "$*"; }
warn() { printf '\033[1;33m  ! %s\033[0m\n' "$*"; }

# run <输出文件名> <命令...> : 运行命令、落盘、失败不中断整体
run() {
  local f="$1"; shift
  { echo "\$ $*"; echo "----------------------------------------"; } > "$OUT/$f"
  if "$@" >> "$OUT/$f" 2>&1; then ok "$f"; else warn "$f (返回非0,产物可能不完整)"; fi
}

# ---------- 0. 定位源码包 ----------
if [ -z "$SRC" ]; then
  SRC=$(find . -maxdepth 3 -name "__init__.py" \
        -not -path "*/.*" -not -path "*/${VENV}/*" \
        -not -path "*/test*" -not -path "*/build/*" -not -path "*/dist/*" 2>/dev/null \
        | head -n1 | xargs -r dirname)
fi
if [ -z "$SRC" ] || [ ! -d "$SRC" ]; then
  warn "未能自动确定源码包,默认用当前目录 '.'(可重跑并手动指定:bash project_audit.sh path/to/pkg)"
  SRC="."
fi
ABS_SRC="$(cd "$SRC" && pwd)"
log "源码目录: $SRC"

# ---------- 准备隔离环境 ----------
log "准备隔离工具环境(不污染你的项目依赖)"
$PY -m venv "$VENV" >/dev/null 2>&1 || true
# shellcheck disable=SC1090
source "$VENV/bin/activate"
pip install -q --upgrade pip >/dev/null 2>&1
TOOLS="radon vulture pylint pydeps ruff deptry pip-audit gitingest coverage pytest"
if pip install -q $TOOLS >/dev/null 2>&1; then ok "工具安装完成"; else warn "部分工具安装失败,相关步骤会被跳过"; fi

# ---------- ① 规模 / 复杂度 / 可维护性 ----------
log "① 规模 / 复杂度 / 可维护性 (radon)"
run 01_loc_raw.txt           radon raw "$SRC" -s
run 01_complexity_cc.txt     radon cc  "$SRC" -s -a --total-average
run 01_maintainability.txt   radon mi  "$SRC" -s

# ---------- ② 真实依赖 / 架构 ----------
log "② 真实依赖与架构 (pyreverse → mermaid, pydeps → 循环依赖)"
if ( cd "$OUT" && pyreverse -o mmd -p Project "$ABS_SRC" >/dev/null 2>&1 ); then
  ok "02_packages_Project.mmd / 02_classes_Project.mmd (mermaid,可直接粘到任意 mermaid 渲染器)"
  # pyreverse 命名为 packages_Project.mmd,统一加前缀
  [ -f "$OUT/packages_Project.mmd" ] && mv "$OUT/packages_Project.mmd" "$OUT/02_packages_Project.mmd"
  [ -f "$OUT/classes_Project.mmd" ]  && mv "$OUT/classes_Project.mmd"  "$OUT/02_classes_Project.mmd"
else
  warn "pyreverse 失败(包结构可能不规范)"
fi
run 02_import_cycles.txt pydeps "$SRC" --show-cycles --no-output --noshow
if command -v dot >/dev/null 2>&1; then
  ( pydeps "$SRC" -o "$OUT/02_imports.svg" --noshow --max-bacon=4 >/dev/null 2>&1 ) \
    && ok "02_imports.svg(依赖关系图)" || warn "依赖图渲染失败"
else
  warn "未检测到 graphviz(dot),跳过 svg 依赖图。装一下更直观:apt install graphviz / brew install graphviz"
fi

# ---------- ③ 死代码 ----------
log "③ 死代码 (vulture 静态 + coverage 运行时)"
run 03_deadcode_vulture.txt vulture "$SRC" --min-confidence 60
if [ -n "$TEST_CMD" ]; then
  log "③b 运行时覆盖率(执行你的测试,0% 覆盖≈疑似死模块)"
  coverage erase >/dev/null 2>&1
  if eval "coverage run --source=\"$SRC\" $TEST_CMD" >/dev/null 2>&1; then
    coverage report --show-missing > "$OUT/03_coverage.txt" 2>&1 && ok "03_coverage.txt"
  else
    warn "测试执行失败,跳过覆盖率。确认 TEST_CMD 格式,例:\"-m pytest -q\""
  fi
else
  warn "未提供测试命令,跳过运行时覆盖率(此步可选)"
fi

# ---------- ④ 重复代码 ----------
log "④ 重复 / 复制粘贴代码 (pylint duplicate-code)"
run 04_duplication.txt pylint "$SRC" --disable=all --enable=duplicate-code --min-similarity-lines=6 -sn

# ---------- ⑤ 依赖健康度 ----------
log "⑤ 依赖健康度 (deptry 未用/缺失依赖, pip-audit 漏洞)"
run 05_deps_unused_missing.txt deptry .
if [ -f requirements.txt ]; then
  run 05_deps_vulnerabilities.txt pip-audit -r requirements.txt
else
  run 05_deps_vulnerabilities.txt pip-audit
fi

# ---------- ⑥ Lint / 坏味道 ----------
log "⑥ Lint 统计 (ruff)"
run 06_ruff.txt ruff check "$SRC" --statistics

# ---------- ⑦ Git 变更热点 ----------
log "⑦ Git 变更热点(改动次数最多的文件 = 优先重构对象)"
if [ -d .git ]; then
  { echo "# 近12个月各 .py 文件被修改次数(降序,top 40)"; echo;
    git log --since="12 months ago" --name-only --pretty=format: 2>/dev/null \
      | grep -E '\.py$' | sort | uniq -c | sort -rn | head -40; } \
    > "$OUT/07_git_hotspots.txt" && ok "07_git_hotspots.txt"
else
  warn "非 git 仓库,跳过"
fi

# ---------- ⑧ 打包全量代码给大模型 ----------
log "⑧ 打包全量代码 (repomix / gitingest)"
PACKED=""
if command -v npx >/dev/null 2>&1; then
  if npx -y repomix --style xml -o "$OUT/08_repomix.xml" >/dev/null 2>&1; then
    ok "08_repomix.xml(文件树+全量源码+token 计数)"; PACKED="08_repomix.xml"
  fi
fi
if [ -z "$PACKED" ]; then
  if gitingest . -o "$OUT/08_digest.txt" >/dev/null 2>&1; then
    ok "08_digest.txt(全量摘要,文末含 token 估算)"; PACKED="08_digest.txt"
  else
    warn "打包失败:装 node 用 repomix,或 pip 装 gitingest"
  fi
fi

# ---------- 生成目标模板 ----------
cat > "$OUT/TARGET_TEMPLATE.md" <<'EOF'
# 项目目标定义(请你本人填写——工具和模型都猜不出你的终点)

> "离最终目标还有多远"这种判断,必须有一个你定义的基准。
> 花 20 分钟把下面填实,后面那份差距报告才有意义。

## 1. 一句话定位
这个产品最终要解决谁的什么问题:

## 2. 最终形态的核心功能(按优先级)
- [ ] P0(没有就不成立):
- [ ] P0:
- [ ] P1(重要但非阻断):
- [ ] P2(锦上添花):

## 3. MVP / 第一个可付费版本必须包含
-

## 4. 明确"不做"的范围(防止跑偏)
-

## 5. 关键非功能要求
- 性能 / 成本约束:
- 目标用户规模:
- 技术约束(硬件、预算、语言):

## 6. 你自己感觉"失控"的地方(主观,但很有用)
-
EOF
ok "TARGET_TEMPLATE.md(请填写)"

# ---------- 生成喂给模型的提示词 ----------
cat > "$OUT/AUDIT_PROMPT.md" <<'EOF'
# 给大模型的审计提示词
# 用法:把【填好的 TARGET.md】+【_audit/ 里的全部事实文件】+【打包文件 08_*】
# 一起作为上下文,然后发送下面这段。

你拿到的是一个 Python 项目的客观分析产物(依赖图、死代码、重复代码、
复杂度、依赖健康度、git 热点、全量源码),以及作者本人写的目标定义文档。

铁律:只基于这些材料下结论。任何无法从材料中确认的判断,明确写"无法确认",
不要用命名习惯或常识脑补。区分清楚"代码事实"与"你的推测"。

请按顺序输出:

## A. 真实架构
1. 实际存在的核心模块及各自职责——以 pyreverse/pydeps 依赖图为准,不以文件名/目录名为准。
2. 模块间真实依赖关系;明确列出循环依赖(来自 02_import_cycles)。
3. 用一段话描述真实的分层/数据流;若代码里看不出清晰分层,直接说"无清晰分层"。

## B. 对照目标的差距(逐条)
对 TARGET.md 里每个 P0/P1 功能,标注:已实现 / 部分实现 / 未实现 / 无法确认,
并指出对应代码位置。最后单列一类:**代码里存在、但目标文档没提到的东西**
(这些往往是历史跑偏或 AI 生成的冗余功能)。

## C. 屎山风险清单(按严重度排序)
- 死代码:综合 vulture(静态)与 coverage(运行时 0% 覆盖)交叉确认。
- 重复代码块:来自 04_duplication。
- 高复杂度 / 低可维护性文件:radon cc 高 + mi 低,且同时出现在 git 热点里的,
  标为"最高优先级重构对象"。
- 未使用 / 缺失依赖:来自 deptry。

## D. 文档与代码不对齐之处
对比项目自带的 README/日志/设计文档(若在材料中)与上面的代码事实,
列出声称已做、但代码里找不到对应实现,或实现与描述不符的地方。

## E. 下一步行动(不超过10条,可执行)
按"先止血(清死代码/降复杂度)再推进(补 P0 缺口)"排序,每条给出具体文件/模块。
EOF
ok "AUDIT_PROMPT.md"

# ---------- 生成索引 ----------
cat > "$OUT/00_INDEX.md" <<EOF
# 项目体检产物索引

源码目录: \`$SRC\`   生成时间: $(date '+%Y-%m-%d %H:%M')

## 事实文件(从代码直接提取,无 LLM 参与)
| 文件 | 内容 | 用途 |
|---|---|---|
| 01_loc_raw.txt | 各文件真实 LOC/注释/空行 | 看体量分布 |
| 01_complexity_cc.txt | 圈复杂度 | 找复杂函数 |
| 01_maintainability.txt | 可维护性指数(MI) | MI 低=该重构 |
| 02_packages_Project.mmd | 包依赖图(mermaid) | 真实架构 |
| 02_classes_Project.mmd | 类图(mermaid) | 真实结构 |
| 02_import_cycles.txt | 循环依赖 | 架构腐化信号 |
| 02_imports.svg | 依赖关系图(需 graphviz) | 直观看耦合 |
| 03_deadcode_vulture.txt | 静态死代码 | 屎山 |
| 03_coverage.txt | 运行时 0% 覆盖(需测试) | 死模块 |
| 04_duplication.txt | 重复代码块 | 屎山 |
| 05_deps_unused_missing.txt | 未用/缺失依赖 | 依赖屎山 |
| 05_deps_vulnerabilities.txt | 依赖漏洞 | 安全 |
| 06_ruff.txt | Lint 坏味道统计 | 整体质量 |
| 07_git_hotspots.txt | 改动最频繁的文件 | 重构优先级 |
| ${PACKED:-08_(打包失败)} | 全量源码打包 | 喂给大模型 |

## 接下来做什么
1. 填写 \`TARGET_TEMPLATE.md\` → 另存为 \`TARGET.md\`。
2. 选一种方式生成报告:
   - **A. 大窗口模型通读**:把 ${PACKED:-打包文件} 连同本目录其余 txt/mmd + TARGET.md
     一起丢给 1M 上下文模型(Claude Opus 4.8 / Gemini 3.1 Pro),发送 AUDIT_PROMPT.md。
   - **B. Claude Code 编排**:在仓库里让 Claude Code 读取 _audit/ 全部文件 + TARGET.md,
     执行 AUDIT_PROMPT.md。适合代码量大、想让它边读边核对。
3. **交叉验证**:模型说的架构,必须与 02_*.mmd 的图对得上;对不上的地方以图为准。
EOF
ok "00_INDEX.md"

deactivate 2>/dev/null || true

log "完成 ✅  全部产物在 ./$OUT/  —— 先读 00_INDEX.md"
echo "可选增强:graphviz(依赖图) + node(repomix 打包,token 计数更准)"
