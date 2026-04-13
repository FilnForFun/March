# -*- coding: utf-8 -*-
"""
巴别塔全方位自检引擎
===================
整合每日三思与系统自维护机制，覆盖巴别塔六层架构。

三时段三层自检:
- 晨思(08:00): 对话层+记忆层 → 质量评分 + 达尔文进化 + 上下文压缩
- 午思(12:00): 任务层+项目层 → 任务审计 + 失败分析 + 优先级重排
- 夕思(23:00): 知识层+谱系层 → 知识图谱健康 + 索引完整度 + 压缩率分析

自愈权限: 按达尔文进化规则 + 各技能内置规则执行
输出: 飞书自检报告
"""

import sys
import io
import json
import os
import time
import traceback
from pathlib import Path
from datetime import datetime, timedelta

# Fix Windows console encoding
if sys.stdout.encoding and 'gbk' in sys.stdout.encoding.lower():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if sys.stderr.encoding and 'gbk' in sys.stderr.encoding.lower():
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

WORKSPACE = Path(r"C:\Users\30959\.openclaw\workspace")
STATE_DIR = WORKSPACE / "shared-storage" / ".state"
LOG_DIR = WORKSPACE / "shared-storage" / "logs" / "selfcheck"
MEMORY_DIR = WORKSPACE / "memory"
REPORT_DIR = WORKSPACE / "shared-storage" / "reports" / "selfcheck"

LOG_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# 工具函数
# ============================================================

def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def file_age_days(filepath):
    """文件修改距今天数"""
    try:
        mtime = os.path.getmtime(filepath)
        return (time.time() - mtime) / 86400
    except:
        return 999

def file_size_kb(filepath):
    try:
        return os.path.getsize(filepath) / 1024
    except:
        return 0

def get_dir_files(directory, pattern="*.md"):
    """获取目录下匹配的文件列表"""
    try:
        return list(Path(directory).glob(pattern))
    except:
        return []

def log(section, message, level="INFO"):
    """记录日志"""
    ts = now_str()
    # Replace emoji with ASCII-safe markers
    safe_msg = message.replace('✅', '[OK]').replace('⚠️', '[WARN]').replace('❌', '[FAIL]')
    print(f"[{ts}] [{level}] [{section}] {safe_msg}")

def save_report(phase, report_data):
    """保存自检报告到 JSON"""
    filepath = REPORT_DIR / f"selfcheck-{phase}-{datetime.now().strftime('%Y%m%d')}.json"
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)
    log("REPORT", f"报告已保存: {filepath}")
    return filepath


# ============================================================
# 层健康评分
# ============================================================

def score_health(components):
    """
    计算层健康评分 (0-100)
    components: list of {"name", "weight", "score", "issues"}
    """
    total_weight = sum(c["weight"] for c in components)
    if total_weight == 0:
        return 0, []

    weighted = sum(c["score"] * c["weight"] for c in components) / total_weight
    issues = []
    for c in components:
        if c["score"] < 60:
            issues.append(f"[{c['name']}] {c.get('issues', '评分过低')}")

    return round(weighted, 1), issues


# ============================================================
# 晨思-忠: 对话层 + 记忆层自检 (08:00)
# ============================================================

def morning_selfcheck():
    """
    晨思自检:
    1. 对话层 - 昨日会话质量评估
    2. 记忆层 - MEMORY.md 新鲜度 + memory/*.md 衰减检测
    3. 达尔文进化 - 用进废退扫描
    4. 上下文压缩 - 膨胀文件检测
    """
    log("MORNING", "=== 晨思-忠 自检开始 ===")
    report = {
        "phase": "晨思-忠",
        "time": now_str(),
        "layers": ["对话层", "记忆层"],
        "health_score": 0,
        "components": [],
        "self_heal_actions": [],
        "summary": ""
    }

    # --- 1. 对话层自检 ---
    log("MORNING", ">>> 对话层自检")
    archives = get_dir_files(MEMORY_DIR / "archives", "*.json")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    yesterday_archive = MEMORY_DIR / "archives" / f"{yesterday}.json"

    archive_ok = yesterday_archive.exists()
    archive_size = file_size_kb(yesterday_archive) if archive_ok else 0
    conv_score = 80 if archive_ok else 30
    conv_issues = []
    if not archive_ok:
        conv_issues.append(f"昨日归档缺失 (期望 {yesterday}.json)")
    if archive_size > 500:
        conv_issues.append(f"归档文件过大 ({archive_size:.0f}KB)")

    report["components"].append({
        "name": "对话层",
        "weight": 40,
        "score": conv_score,
        "issues": conv_issues,
        "details": {
            "昨日归档": "✅" if archive_ok else "❌ 缺失",
            "归档大小": f"{archive_size:.0f}KB" if archive_ok else "N/A"
        }
    })

    # --- 2. 记忆层自检 ---
    log("MORNING", ">>> 记忆层自检")
    memory_file = WORKSPACE / "MEMORY.md"
    memory_age = file_age_days(memory_file)
    memory_size = file_size_kb(memory_file)

    # 检测低频记忆文件 (>30天未修改)
    stale_files = []
    for f in get_dir_files(MEMORY_DIR, "20*.md"):
        age = file_age_days(f)
        if age > 30:
            stale_files.append({"file": f.name, "age_days": round(age, 1)})

    memory_score = 90
    memory_issues = []
    if memory_age > 7:
        memory_score -= 30
        memory_issues.append(f"MEMORY.md 已超过 {memory_age:.0f} 天未更新")
    if memory_size > 100:
        memory_score -= 10
        memory_issues.append(f"MEMORY.md 过大 ({memory_size:.0f}KB)，建议压缩")
    if stale_files:
        memory_score -= min(len(stale_files) * 5, 20)
        memory_issues.append(f"{len(stale_files)} 个记忆文件超过 30 天未更新")

    report["components"].append({
        "name": "记忆层",
        "weight": 40,
        "score": max(memory_score, 10),
        "issues": memory_issues,
        "details": {
            "MEMORY.md 年龄": f"{memory_age:.0f} 天",
            "MEMORY.md 大小": f"{memory_size:.0f}KB",
            "低频文件数": len(stale_files),
        }
    })

    # --- 3. 达尔文进化扫描 ---
    log("MORNING", ">>> 达尔文进化扫描")
    darwin_status = {"scanned": 0, "flagged_stale": 0, "flagged_bloat": 0}

    # 检查 skills 目录
    skills_dir = WORKSPACE / "skills"
    if skills_dir.exists():
        for skill in skills_dir.iterdir():
            if not skill.is_dir():
                continue
            darwin_status["scanned"] += 1

            # 检查 SKILL.md 新鲜度
            skill_md = skill / "SKILL.md"
            if skill_md.exists():
                age = file_age_days(skill_md)
                if age > 90:
                    darwin_status["flagged_stale"] += 1

    report["components"].append({
        "name": "达尔文进化",
        "weight": 10,
        "score": 70 if darwin_status["flagged_stale"] == 0 else 50,
        "issues": [f"{darwin_status['flagged_stale']} 个技能超过 90 天未更新"] if darwin_status["flagged_stale"] > 0 else [],
        "details": {
            "扫描技能数": darwin_status["scanned"],
            "标记陈旧": darwin_status["flagged_stale"],
        }
    })

    # --- 4. 上下文压缩检测 ---
    log("MORNING", ">>> 上下文压缩检测")
    compress_candidates = []
    for fname in ["MEMORY.md", "AGENTS.md", "TASKS.md"]:
        fpath = WORKSPACE / fname
        if fpath.exists():
            size_kb = file_size_kb(fpath)
            if size_kb > 50:  # >50KB 标记为压缩候选
                compress_candidates.append({"file": fname, "size_kb": round(size_kb, 1)})

    compress_score = 90 if not compress_candidates else max(90 - len(compress_candidates) * 15, 40)
    report["components"].append({
        "name": "上下文压缩",
        "weight": 10,
        "score": compress_score,
        "issues": [f"{c['file']} 体积过大 ({c['size_kb']}KB)" for c in compress_candidates],
        "details": {
            "压缩候选": len(compress_candidates),
            "候选文件": [c["file"] for c in compress_candidates]
        }
    })

    # --- 计算总分 ---
    health_score, all_issues = score_health(report["components"])
    report["health_score"] = health_score

    # --- 自愈动作 ---
    heal_actions = []
    if stale_files:
        heal_actions.append(f"[达尔文·废退] 标记 {len(stale_files)} 个低频记忆文件为降级候选")
    if compress_candidates:
        heal_actions.append(f"[压缩引擎] 标记 {len(compress_candidates)} 个膨胀文件待压缩")

    report["self_heal_actions"] = heal_actions
    report["summary"] = (
        f"晨思-忠自检完成 | 总分 {health_score}/100\n"
        f"对话层 {'✅' if conv_score >= 60 else '⚠️'} | "
        f"记忆层 {'✅' if memory_score >= 60 else '⚠️'}\n"
        f"问题: {len(all_issues)} 个 | "
        f"自愈: {len(heal_actions)} 项"
    )

    save_report("morning", report)
    log("MORNING", report["summary"])
    return report


# ============================================================
# 午思-信: 任务层 + 项目层自检 (12:00)
# ============================================================

def noon_selfcheck():
    """
    午思自检:
    1. 任务层 - Windows 任务计划状态审计
    2. 巴别塔任务注册表同步
    3. 失败任务根因分析
    4. 待办优先级重排
    """
    log("NOON", "=== 午思-信 自检开始 ===")
    report = {
        "phase": "午思-信",
        "time": now_str(),
        "layers": ["任务层", "项目层"],
        "health_score": 0,
        "components": [],
        "self_heal_actions": [],
        "summary": ""
    }

    # --- 1. 任务层审计 ---
    log("NOON", ">>> 任务层状态审计")
    import subprocess

    try:
        result = subprocess.run(
            ["schtasks", "/query", "/fo", "CSV", "/v"],
            capture_output=True, text=True, timeout=30,
            encoding="utf-8", errors="replace"
        )
        lines = result.stdout.strip().split("\n")
    except Exception as e:
        log("NOON", f"获取任务状态失败: {e}", "ERROR")
        lines = []

    # 解析我们关心的任务
    our_tasks = []
    keywords = ["OpenClaw", "Babel", "Garmin", "GitHub", "晨思", "午思", "夕思",
                "Position", "Data-Analyst", "Research", "Monitor", "SkillHub", "Molili"]

    for line in lines[1:]:  # 跳过标题行
        if not line.strip():
            continue
        parts = line.split('","')
        if len(parts) < 3:
            continue
        task_name = parts[0].replace('"', '').strip()
        if any(kw.lower() in task_name.lower() for kw in keywords):
            status = parts[-1].replace('"', '').strip() if len(parts) > 1 else "Unknown"
            next_run = parts[-2].replace('"', '').strip() if len(parts) > 1 else "N/A"
            our_tasks.append({"name": task_name, "status": status, "next_run": next_run})

    total_tasks = len(our_tasks)
    ready_tasks = sum(1 for t in our_tasks if "就绪" in t.get("status", ""))
    failed_tasks = [t for t in our_tasks if "失败" in t.get("status", "") or "错误" in t.get("status", "")]

    task_score = 100
    task_issues = []
    if total_tasks > 0:
        ready_ratio = ready_tasks / total_tasks
        task_score = round(ready_ratio * 100)
    if failed_tasks:
        task_issues.append(f"{len(failed_tasks)} 个任务上次执行失败: {', '.join(f['name'] for f in failed_tasks[:5])}")

    report["components"].append({
        "name": "任务执行状态",
        "weight": 50,
        "score": task_score,
        "issues": task_issues,
        "details": {
            "任务总数": total_tasks,
            "就绪": ready_tasks,
            "待执行": total_tasks - ready_tasks,
            "失败任务": [f["name"] for f in failed_tasks]
        }
    })

    # --- 2. 巴别塔任务注册表同步检查 ---
    log("NOON", ">>> 巴别塔任务注册表检查")
    tasks_json = STATE_DIR / "tasks.json"
    tasks_ok = tasks_json.exists()
    tasks_age = file_age_days(tasks_json) if tasks_ok else 999

    registry_score = 90 if (tasks_ok and tasks_age < 2) else 40
    registry_issues = []
    if not tasks_ok:
        registry_issues.append("tasks.json 不存在")
    elif tasks_age >= 1:
        registry_issues.append(f"tasks.json 已超过 {tasks_age:.0f} 天未同步")

    report["components"].append({
        "name": "任务注册表",
        "weight": 20,
        "score": registry_score,
        "issues": registry_issues,
        "details": {
            "文件存在": "✅" if tasks_ok else "❌",
            "最后同步": f"{tasks_age:.0f} 天前" if tasks_ok else "N/A"
        }
    })

    # --- 3. 待办事项检查 ---
    log("NOON", ">>> 待办事项检查")
    todo_file = MEMORY_DIR / "2026-04-09-todo.md"
    if not todo_file.exists():
        # 查找最新的 todo 文件
        todo_files = get_dir_files(MEMORY_DIR, "*todo*.md")
        if todo_files:
            todo_file = sorted(todo_files, key=lambda f: file_age_days(f))[0]

    todo_items = 0
    todo_pending = 0
    if todo_file.exists():
        with open(todo_file, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        todo_items = content.count("### ")
        todo_pending = content.count("⏳")

    todo_score = 80 if todo_pending < 5 else max(100 - todo_pending * 10, 30)
    report["components"].append({
        "name": "待办事项",
        "weight": 15,
        "score": todo_score,
        "issues": [f"有 {todo_pending} 个待办事项待处理"] if todo_pending > 5 else [],
        "details": {
            "总项目数": todo_items,
            "待处理": todo_pending
        }
    })

    # --- 4. 项目进度检查 ---
    log("NOON", ">>> 项目进度检查")
    projects_dir = WORKSPACE / "projects"
    project_count = 0
    stalled_projects = []
    if projects_dir.exists():
        for proj in projects_dir.iterdir():
            if proj.is_dir():
                project_count += 1
                # 检查最近修改时间
                latest_mtime = 0
                for f in proj.rglob("*"):
                    try:
                        mt = os.path.getmtime(f)
                        if mt > latest_mtime:
                            latest_mtime = mt
                    except:
                        pass
                if latest_mtime > 0:
                    age = (time.time() - latest_mtime) / 86400
                    if age > 14:
                        stalled_projects.append({"name": proj.name, "stale_days": round(age, 0)})

    project_score = 80 if not stalled_projects else max(80 - len(stalled_projects) * 10, 30)
    report["components"].append({
        "name": "项目进度",
        "weight": 15,
        "score": project_score,
        "issues": [f"{len(stalled_projects)} 个项目超过 14 天无更新"] if stalled_projects else [],
        "details": {
            "项目总数": project_count,
            "停滞项目": [p["name"] for p in stalled_projects]
        }
    })

    # --- 计算总分 ---
    health_score, all_issues = score_health(report["components"])
    report["health_score"] = health_score

    # --- 自愈动作 ---
    heal_actions = []
    if failed_tasks:
        heal_actions.append(f"[任务修复] 标记 {len(failed_tasks)} 个失败任务待排查")
    if tasks_age >= 1:
        heal_actions.append("[同步] 建议重新同步 tasks.json 与 Windows 任务计划")
    if stalled_projects:
        heal_actions.append(f"[项目治理] 标记 {len(stalled_projects)} 个停滞项目待确认")

    report["self_heal_actions"] = heal_actions
    report["summary"] = (
        f"午思-信自检完成 | 总分 {health_score}/100\n"
        f"任务 {'✅' if task_score >= 60 else '⚠️'} | "
        f"注册表 {'✅' if registry_score >= 60 else '⚠️'} | "
        f"待办 {'✅' if todo_score >= 60 else '⚠️'} | "
        f"项目 {'✅' if project_score >= 60 else '⚠️'}\n"
        f"问题: {len(all_issues)} 个 | "
        f"自愈: {len(heal_actions)} 项"
    )

    save_report("noon", report)
    log("NOON", report["summary"])
    return report


# ============================================================
# 夕思-习: 知识层 + 谱系层自检 (23:00)
# ============================================================

def evening_selfcheck():
    """
    夕思自检:
    1. 知识层 - 知识库完整性 + 文档新鲜度
    2. 谱系层 - 知识图谱健康 + 索引完整度
    3. 搜索层 - BM25/向量索引状态
    4. 压缩率分析 - 知识库存储效率
    """
    log("EVENING", "=== 夕思-习 自检开始 ===")
    report = {
        "phase": "夕思-习",
        "time": now_str(),
        "layers": ["知识层", "谱系层", "搜索层"],
        "health_score": 0,
        "components": [],
        "self_heal_actions": [],
        "summary": ""
    }

    # --- 1. 知识层自检 ---
    log("EVENING", ">>> 知识层自检")
    knowledge_dir = WORKSPACE / "knowledge"
    kb_docs = 0
    kb_stale = 0
    kb_size = 0
    if knowledge_dir.exists():
        for f in knowledge_dir.rglob("*.md"):
            kb_docs += 1
            kb_size += file_size_kb(f)
            if file_age_days(f) > 30:
                kb_stale += 1

    kb_score = 90 if kb_stale == 0 else max(90 - kb_stale * 5, 30)
    kb_issues = []
    if kb_stale > 0:
        kb_issues.append(f"{kb_stale} 个知识文档超过 30 天未更新")

    report["components"].append({
        "name": "知识库",
        "weight": 30,
        "score": kb_score,
        "issues": kb_issues,
        "details": {
            "文档数": kb_docs,
            "总大小": f"{kb_size:.0f}KB",
            "陈旧文档": kb_stale
        }
    })

    # --- 2. 知识图谱自检 ---
    log("EVENING", ">>> 知识图谱自检")
    graph_json = knowledge_dir / "graphrag" / "graph.json" if knowledge_dir.exists() else None
    graph_nodes = 0
    graph_edges = 0
    graph_ok = graph_json and graph_json.exists()

    if graph_ok:
        try:
            with open(graph_json, "r", encoding="utf-8", errors="replace") as f:
                graph_data = json.load(f)
            graph_nodes = len(graph_data.get("nodes", []))
            # Support both "edges" and "links" keys
            graph_edges = len(graph_data.get("edges", graph_data.get("links", [])))
        except:
            graph_ok = False

    graph_score = 70 if graph_ok and graph_nodes > 10 else 30
    graph_issues = []
    if not graph_ok:
        graph_issues.append("知识图谱数据文件不存在")
    elif graph_nodes < 50:
        graph_issues.append(f"图谱规模较小 ({graph_nodes} 节点, 目标 100+)")

    report["components"].append({
        "name": "知识图谱",
        "weight": 25,
        "score": graph_score,
        "issues": graph_issues,
        "details": {
            "节点数": graph_nodes,
            "边数": graph_edges,
            "目标节点": "100+"
        }
    })

    # --- 3. 搜索层自检 ---
    log("EVENING", ">>> 搜索层自检")
    # BM25 索引在 hybrid-search 技能目录下
    bm25_dir = WORKSPACE / "skills" / "hybrid-search" / "bm25-index"
    vector_count = 0
    bm25_files = 0

    if bm25_dir.exists():
        bm25_files = len(list(bm25_dir.glob("*")))

    # 向量存储在 shared-storage 下
    vector_dir = WORKSPACE / "shared-storage" / "vector-store"
    if vector_dir.exists():
        vector_count = len(list(vector_dir.glob("*")))

    search_score = 70
    search_issues = []
    if bm25_files == 0:
        search_score -= 20
        search_issues.append("BM25 索引为空")
    if vector_count == 0:
        search_score -= 15
        search_issues.append("向量索引缺失")

    report["components"].append({
        "name": "搜索引擎",
        "weight": 25,
        "score": max(search_score, 10),
        "issues": search_issues,
        "details": {
            "BM25 文件": bm25_files,
            "向量数": vector_count
        }
    })

    # --- 4. 压缩率分析 ---
    log("EVENING", ">>> 压缩率分析")
    total_kb = kb_size
    # 检查归档目录大小
    archive_dir = MEMORY_DIR / "archives"
    archive_size = 0
    if archive_dir.exists():
        for f in archive_dir.glob("*.json"):
            archive_size += file_size_kb(f)

    compression_score = 80
    compression_issues = []
    if total_kb > 1000:
        compression_score -= 20
        compression_issues.append(f"知识库总体积过大 ({total_kb:.0f}KB)")

    report["components"].append({
        "name": "存储效率",
        "weight": 20,
        "score": compression_score,
        "issues": compression_issues,
        "details": {
            "知识库大小": f"{total_kb:.0f}KB",
            "归档大小": f"{archive_size:.0f}KB"
        }
    })

    # --- 计算总分 ---
    health_score, all_issues = score_health(report["components"])
    report["health_score"] = health_score

    # --- 自愈动作 ---
    heal_actions = []
    if kb_stale > 0:
        heal_actions.append(f"[达尔文·废退] 标记 {kb_stale} 个陈旧知识文档待降级")
    if bm25_files == 0:
        heal_actions.append("[搜索层] 建议重建 BM25 索引")
    if graph_nodes < 50:
        heal_actions.append(f"[图谱] 当前 {graph_nodes} 节点，建议扩展至 100+")

    report["self_heal_actions"] = heal_actions
    report["summary"] = (
        f"夕思-习自检完成 | 总分 {health_score}/100\n"
        f"知识库 {'✅' if kb_score >= 60 else '⚠️'} | "
        f"图谱 {'✅' if graph_score >= 60 else '⚠️'} | "
        f"搜索 {'✅' if search_score >= 60 else '⚠️'}\n"
        f"问题: {len(all_issues)} 个 | "
        f"自愈: {len(heal_actions)} 项"
    )

    save_report("evening", report)
    log("EVENING", report["summary"])
    return report


# ============================================================
# 主入口
# ============================================================

def main():
    phase = sys.argv[1] if len(sys.argv) > 1 else "all"

    if phase == "morning":
        morning_selfcheck()
    elif phase == "noon":
        noon_selfcheck()
    elif phase == "evening":
        evening_selfcheck()
    elif phase == "all":
        print("执行全部自检 (通常由定时任务分别触发)")
        morning_selfcheck()
        print("---")
        noon_selfcheck()
        print("---")
        evening_selfcheck()
    else:
        print(f"未知阶段: {phase}")
        print("用法: python babel-selfcheck-engine.py [morning|noon|evening|all]")
        sys.exit(1)


if __name__ == "__main__":
    main()
