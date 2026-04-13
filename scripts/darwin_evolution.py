# -*- coding: utf-8 -*-
"""
达尔文自进化引擎 - Darwin Evolution Engine
巴别塔再进化项目 Phase 3.3

核心理念: 用进废退 + 自然选择
- 用进: 高频使用的技能/记忆自动强化
- 废退: 低频内容自动降级
- 变异: 新文档自动发现，建议创建技能
- 自然选择: 定期评估，淘汰低效内容

运行: python scripts/darwin_evolution.py [--scan-only|--auto|--report]
"""

import sys
import io
import os
import json
import re
from pathlib import Path
from datetime import datetime, timedelta
from collections import Counter, defaultdict

if sys.stdout.encoding and 'gbk' in sys.stdout.encoding.lower():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


# ============================================================
# 配置
# ============================================================
WORKSPACE = Path(__file__).resolve().parent.parent
SKILLS_DIR = WORKSPACE / "skills"
MEMORY_DIR = WORKSPACE / "memory"
MEMORY_FILE = WORKSPACE / "MEMORY.md"
RAW_DIR = WORKSPACE / "raw"
DISTILLED_DIR = WORKSPACE / "knowledge" / "distilled"
REPORTS_DIR = WORKSPACE / "shared-storage" / "reports" / "darwin"
STATE_FILE = WORKSPACE / "shared-storage" / ".state" / "darwin_state.json"

REPORTS_DIR.mkdir(parents=True, exist_ok=True)
STATE_FILE.parent.mkdir(parents=True, exist_ok=True)

# 阈值
STALE_DAYS = 30         # 超过此天数标记为降级候选
VERY_STALE_DAYS = 60    # 超过此天数建议删除
ACTIVE_DAYS = 14        # 此天数内更新过视为活跃
HIGH_FREQ_THRESHOLD = 5 # 引用次数 >= 此值视为高频


# ============================================================
# 工具函数
# ============================================================
def log(section, message, level="INFO"):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    safe_msg = message.replace('✅', '[OK]').replace('⚠️', '[WARN]').replace('❌', '[FAIL]')
    print(f"[{ts}] [{level}] [{section}] {safe_msg}")


def file_age_days(filepath):
    try:
        return (datetime.now().timestamp() - os.path.getmtime(filepath)) / 86400
    except:
        return 999


def load_state():
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {"last_scan": None, "skill_refs": {}, "memory_refs": {}}


def save_state(state):
    state["last_scan"] = datetime.now().isoformat()
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def scan_skill_references():
    """扫描技能被引用的次数"""
    ref_counts = Counter()
    
    # 扫描 MEMORY.md
    if MEMORY_FILE.exists():
        content = MEMORY_FILE.read_text(encoding='utf-8', errors='replace')
        if SKILLS_DIR.exists():
            for skill_dir in SKILLS_DIR.iterdir():
                if skill_dir.is_dir() and not skill_dir.name.startswith('_'):
                    count = content.count(skill_dir.name)
                    if count > 0:
                        ref_counts[skill_dir.name] += count
    
    # 扫描记忆文件
    if MEMORY_DIR.exists():
        for f in MEMORY_DIR.glob("*.md"):
            try:
                content = f.read_text(encoding='utf-8', errors='replace')
                if SKILLS_DIR.exists():
                    for skill_dir in SKILLS_DIR.iterdir():
                        if skill_dir.is_dir() and not skill_dir.name.startswith('_'):
                            count = content.count(skill_dir.name)
                            if count > 0:
                                ref_counts[skill_dir.name] += count
            except:
                pass
    
    return ref_counts


# ============================================================
# 1. 用进 (高频强化)
# ============================================================
def scan_active_skills():
    """扫描活跃技能"""
    log("用进", "扫描活跃技能...")
    active = []
    inactive = []
    ref_counts = scan_skill_references()
    
    if not SKILLS_DIR.exists():
        log("用进", "Skills 目录不存在", "WARN")
        return active, inactive, ref_counts
    
    for skill_dir in sorted(SKILLS_DIR.iterdir()):
        if not skill_dir.is_dir() or skill_dir.name.startswith(('_', '.')):
            continue
        
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue
        
        age = file_age_days(skill_md)
        refs = ref_counts.get(skill_dir.name, 0)
        
        if age < ACTIVE_DAYS or refs >= HIGH_FREQ_THRESHOLD:
            active.append({
                "name": skill_dir.name,
                "days_since_update": round(age, 1),
                "references": refs,
                "status": "active" if age < ACTIVE_DAYS else "high_freq",
            })
        else:
            inactive.append({
                "name": skill_dir.name,
                "days_since_update": round(age, 1),
                "references": refs,
                "status": "inactive",
            })
    
    log("用进", f"活跃技能: {len(active)}, 非活跃: {len(inactive)}")
    return active, inactive, ref_counts


# ============================================================
# 2. 废退 (低频降级)
# ============================================================
def scan_stale_memory():
    """扫描过期记忆文件"""
    log("废退", "扫描过期记忆...")
    stale = []
    very_stale = []
    
    if not MEMORY_DIR.exists():
        log("废退", "Memory 目录不存在", "WARN")
        return stale, very_stale
    
    for f in sorted(MEMORY_DIR.glob("*.md")):
        if f.name in ("MEMORY.md", "DREAMS.md"):
            continue
        if not re.match(r'^20\d{2}-\d{2}-\d{2}', f.name):
            continue
        
        age = file_age_days(f)
        if age > VERY_STALE_DAYS:
            very_stale.append({
                "file": f.name,
                "days_old": round(age, 1),
                "size_kb": round(f.stat().st_size / 1024, 1),
                "action": "delete",
            })
        elif age > STALE_DAYS:
            stale.append({
                "file": f.name,
                "days_old": round(age, 1),
                "size_kb": round(f.stat().st_size / 1024, 1),
                "action": "degrade",
            })
    
    log("废退", f"降级候选: {len(stale)}, 删除候选: {len(very_stale)}")
    return stale, very_stale


# ============================================================
# 3. 变异 (新内容发现)
# ============================================================
def discover_new_content():
    """发现新内容，建议创建技能或知识条目"""
    log("变异", "扫描新内容...")
    candidates = []
    
    # 扫描 raw 目录
    for src_dir, category in [(RAW_DIR, "raw"), (DISTILLED_DIR, "distilled")]:
        if not src_dir.exists():
            continue
        
        for f in sorted(src_dir.rglob("*")):
            if f.is_file() and f.suffix.lower() in ['.md', '.py', '.json']:
                if f.name.lower() in ('readme.md', 'config.json', '__init__.py', '.gitkeep'):
                    continue
                age = file_age_days(f)
                if age < 7:
                    rel_path = f.relative_to(WORKSPACE)
                    candidates.append({
                        "file": str(rel_path),
                        "category": category,
                        "age_days": round(age, 1),
                        "size_kb": round(f.stat().st_size / 1024, 1),
                        "suggestion": f"考虑为 {f.stem} 创建技能或知识条目",
                    })
    
    log("变异", f"发现 {len(candidates)} 个新内容候选")
    return candidates


# ============================================================
# 4. 自然选择 (效能评估)
# ============================================================
def generate_report(active_skills, inactive_skills, ref_counts, stale_mem, very_stale, new_content):
    """生成健康报告"""
    log("选择", "生成效能评估报告...")
    
    total_skills = len(active_skills) + len(inactive_skills)
    active_ratio = len(active_skills) / max(total_skills, 1)
    
    # 计算健康分
    health_score = 100
    deductions = []
    
    if active_ratio < 0.5:
        penalty = int((0.5 - active_ratio) * 40)
        health_score -= penalty
        deductions.append(f"活跃技能比例过低 ({active_ratio:.0%}), 扣 {penalty} 分")
    
    if len(stale_mem) > 5:
        penalty = min(len(stale_mem) * 2, 15)
        health_score -= penalty
        deductions.append(f"{len(stale_mem)} 个记忆文件过期, 扣 {penalty} 分")
    
    if len(very_stale) > 0:
        penalty = min(len(very_stale) * 5, 20)
        health_score -= penalty
        deductions.append(f"{len(very_stale)} 个文件建议删除, 扣 {penalty} 分")
    
    health_score = max(health_score, 0)
    
    report = {
        "report_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "health_score": health_score,
        "summary": {
            "total_skills": total_skills,
            "active_skills": len(active_skills),
            "inactive_skills": len(inactive_skills),
            "active_ratio": round(active_ratio, 2),
            "high_freq_skills": sum(1 for s in active_skills if s["status"] == "high_freq"),
            "stale_memory_files": len(stale_mem),
            "very_stale_files": len(very_stale),
            "new_content_candidates": len(new_content),
        },
        "top_skills_by_ref": sorted(
            [{"name": k, "refs": v} for k, v in ref_counts.items()],
            key=lambda x: -x["refs"]
        )[:15],
        "active_skills": active_skills[:20],
        "inactive_skills": inactive_skills[:20],
        "stale_memory": stale_mem[:20],
        "very_stale": very_stale[:20],
        "new_content": new_content[:20],
        "deductions": deductions,
        "recommendations": [],
    }
    
    # 生成建议
    if active_ratio < 0.5:
        report["recommendations"].append(f"活跃技能比例 {active_ratio:.0%} < 50%, 建议审查非活跃技能")
    if len(stale_mem) > 5:
        report["recommendations"].append(f"有 {len(stale_mem)} 个记忆文件超过 {STALE_DAYS} 天未更新, 建议执行降级")
    if len(very_stale) > 0:
        report["recommendations"].append(f"有 {len(very_stale)} 个文件超过 {VERY_STALE_DAYS} 天, 建议删除")
    if len(new_content) > 3:
        report["recommendations"].append(f"发现 {len(new_content)} 个新内容, 建议创建对应技能")
    if not report["recommendations"]:
        report["recommendations"].append("系统健康, 无需干预")
    
    # 保存报告
    report_file = REPORTS_DIR / f"darwin-report-{datetime.now().strftime('%Y%m%d-%H%M')}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    log("选择", f"报告已保存: {report_file}")
    return report


# ============================================================
# 自动执行动作
# ============================================================
def auto_actions(stale_mem, very_stale, state):
    """执行自动进化动作"""
    log("自进化", "执行自动进化动作...")
    actions_taken = []
    
    # 废退: 标记降级候选
    for item in stale_mem[:5]:  # 最多处理 5 个
        src = MEMORY_DIR / item["file"]
        dst = MEMORY_DIR / "archives" / item["file"]
        if src.exists():
            (MEMORY_DIR / "archives").mkdir(exist_ok=True)
            src.rename(dst)
            log("自进化", f"[废退] {item['file']} -> archives/ ({item['days_old']}天未更新)")
            actions_taken.append(f"降级: {item['file']}")
    
    # 记录到状态
    for action in actions_taken:
        if "actions" not in state:
            state["actions"] = []
        state["actions"].append({
            "time": datetime.now().isoformat(),
            "action": action,
        })
    
    # 保留最近 50 条动作记录
    if "actions" in state:
        state["actions"] = state["actions"][-50:]
    
    log("自进化", f"执行了 {len(actions_taken)} 个进化动作")
    return actions_taken


# ============================================================
# 主函数
# ============================================================
def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="达尔文自进化引擎")
    parser.add_argument("--scan-only", action="store_true", help="仅扫描, 不执行动作")
    parser.add_argument("--auto", action="store_true", help="扫描 + 自动执行进化动作")
    parser.add_argument("--report", action="store_true", help="仅显示上次报告")
    args = parser.parse_args()
    
    if args.report:
        # 显示上次报告
        reports = sorted(REPORTS_DIR.glob("darwin-report-*.json"), reverse=True)
        if reports:
            with open(reports[0], 'r', encoding='utf-8') as f:
                report = json.load(f)
            print(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            print("尚无报告, 先执行扫描: python darwin_evolution.py --scan-only")
        return
    
    log("达尔文", "=" * 60)
    log("达尔文", "自进化引擎启动")
    log("达尔文", "=" * 60)
    
    state = load_state()
    
    # 1. 用进
    active_skills, inactive_skills, ref_counts = scan_active_skills()
    
    # 2. 废退
    stale_mem, very_stale = scan_stale_memory()
    
    # 3. 变异
    new_content = discover_new_content()
    
    # 4. 自然选择
    report = generate_report(active_skills, inactive_skills, ref_counts, stale_mem, very_stale, new_content)
    
    # 5. 自动执行 (如果 --auto)
    actions_taken = []
    if args.auto:
        actions_taken = auto_actions(stale_mem, very_stale, state)
    
    # 保存状态
    state["last_report"] = report
    save_state(state)
    
    # 打印摘要
    log("达尔文", "=" * 60)
    log("达尔文", "扫描完成")
    s = report["summary"]
    log("达尔文", f"  技能: {s['total_skills']} (活跃 {s['active_skills']}, 非活跃 {s['inactive_skills']})")
    log("达尔文", f"  高频技能: {s['high_freq_skills']}")
    log("达尔文", f"  过期记忆: {s['stale_memory_files']} 降级, {s['very_stale_files']} 删除候选")
    log("达尔文", f"  新内容: {s['new_content_candidates']} 候选")
    log("达尔文", f"  健康分: {report['health_score']}/100")
    if actions_taken:
        log("达尔文", f"  执行动作: {len(actions_taken)} 个")
    log("达尔文", f"  建议: {len(report['recommendations'])} 条")
    for rec in report['recommendations']:
        log("达尔文", f"    - {rec}")
    log("达尔文", "=" * 60)


if __name__ == '__main__':
    main()
