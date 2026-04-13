#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
达尔文进化自动扫描 - Darwin Evolution Auto-Scanner
巴别塔再进化项目 Phase 3.3

功能:
1. 用进（高频强化）: 扫描活跃技能和记忆
2. 废退（低频降级）: 标记过期文件
3. 变异（新技能发现）: 扫描新文档建议创建技能
4. 自然选择（效能评估）: 生成健康报告

运行: python scripts/darwin-auto.py
"""

import sys
import io
import json
import os
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
RAW_DIR = WORKSPACE / "raw"
DISTILLED_DIR = WORKSPACE / "distilled"
REPORTS_DIR = WORKSPACE / "shared-storage" / "reports" / "darwin"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# 阈值
STALE_DAYS = 60        # 超过此天数标记为降级候选
VERY_STALE_DAYS = 90   # 超过此天数标记为删除候选
ACTIVE_DAYS = 7        # 此天数内更新过视为活跃


# ============================================================
# 工具函数
# ============================================================
def file_age_days(filepath):
    try:
        return (datetime.now().timestamp() - os.path.getmtime(filepath)) / 86400
    except:
        return 999


def log(section, message, level="INFO"):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] [{level}] [{section}] {message}")


# ============================================================
# 1. 用进（高频强化）
# ============================================================
def scan_active_skills():
    """扫描活跃技能"""
    log("用进", "扫描活跃技能...")
    active = []
    inactive = []
    
    if not SKILLS_DIR.exists():
        log("用进", "Skills 目录不存在", "WARN")
        return active, inactive
    
    for skill_dir in SKILLS_DIR.iterdir():
        if not skill_dir.is_dir() or skill_dir.name.startswith(('_', '.')):
            continue
        
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue
        
        age = file_age_days(skill_md)
        if age < ACTIVE_DAYS:
            active.append({
                "name": skill_dir.name,
                "days_since_update": round(age, 1),
                "status": "active",
            })
        else:
            inactive.append({
                "name": skill_dir.name,
                "days_since_update": round(age, 1),
                "status": "inactive",
            })
    
    log("用进", f"活跃技能: {len(active)}, 非活跃: {len(inactive)}")
    return active, inactive


# ============================================================
# 2. 废退（低频降级）
# ============================================================
def scan_stale_files():
    """扫描过期记忆文件"""
    log("废退", "扫描过期文件...")
    stale = []
    very_stale = []
    
    if not MEMORY_DIR.exists():
        log("废退", "Memory 目录不存在", "WARN")
        return stale, very_stale
    
    for f in MEMORY_DIR.glob("*.md"):
        if f.name in ("MEMORY.md", "DREAMS.md"):
            continue
        if not re.match(r'^20\d{2}-\d{2}-\d{2}', f.name):
            continue
        
        age = file_age_days(f)
        if age > VERY_STALE_DAYS:
            very_stale.append({
                "file": f.name,
                "days_old": round(age, 1),
                "action": "delete",
            })
        elif age > STALE_DAYS:
            stale.append({
                "file": f.name,
                "days_old": round(age, 1),
                "action": "degrade",
            })
    
    log("废退", f"降级候选: {len(stale)}, 删除候选: {len(very_stale)}")
    return stale, very_stale


# ============================================================
# 3. 变异（新技能发现）
# ============================================================
def discover_new_candidates():
    """扫描新文档，建议创建技能"""
    log("变异", "扫描新文档...")
    candidates = []
    
    for src_dir, category in [(RAW_DIR, "raw"), (DISTILLED_DIR, "distilled")]:
        if not src_dir.exists():
            continue
        
        for f in src_dir.rglob("*"):
            if f.is_file() and f.suffix.lower() in ['.md', '.py', '.json']:
                if f.name.lower() in ('readme.md', 'config.json', '__init__.py'):
                    continue
                age = file_age_days(f)
                if age < 7:  # 7 天内的新文件
                    candidates.append({
                        "file": str(f.relative_to(WORKSPACE)),
                        "category": category,
                        "age_days": round(age, 1),
                        "suggestion": f"考虑为此文档创建技能: {f.stem}",
                    })
    
    log("变异", f"发现 {len(candidates)} 个新文档候选")
    return candidates


# ============================================================
# 4. 自然选择（效能评估）
# ============================================================
def generate_health_report(active_skills, inactive_skills, stale_files, very_stale, new_candidates):
    """生成健康报告"""
    log("选择", "生成效能评估报告...")
    
    total_skills = len(active_skills) + len(inactive_skills)
    active_ratio = len(active_skills) / max(total_skills, 1)
    
    report = {
        "report_date": datetime.now().strftime("%Y-%m-%d"),
        "summary": {
            "total_skills": total_skills,
            "active_skills": len(active_skills),
            "inactive_skills": len(inactive_skills),
            "active_ratio": round(active_ratio, 2),
            "stale_memory_files": len(stale_files),
            "very_stale_files": len(very_stale),
            "new_document_candidates": len(new_candidates),
        },
        "active_skills": active_skills[:20],
        "inactive_skills": inactive_skills[:20],
        "stale_files": stale_files[:20],
        "very_stale_files": very_stale[:20],
        "new_candidates": new_candidates[:20],
        "recommendations": [],
    }
    
    # 生成建议
    if active_ratio < 0.3:
        report["recommendations"].append("活跃技能比例过低 (<30%)，建议审查不活跃技能是否需要更新或删除")
    if len(stale_files) > 10:
        report["recommendations"].append(f"有 {len(stale_files)} 个记忆文件超过 {STALE_DAYS} 天未更新，建议执行降级")
    if len(very_stale) > 5:
        report["recommendations"].append(f"有 {len(very_stale)} 个文件超过 {VERY_STALE_DAYS} 天，建议删除")
    if len(new_candidates) > 5:
        report["recommendations"].append(f"发现 {len(new_candidates)} 个新文档，建议创建对应技能")
    
    if not report["recommendations"]:
        report["recommendations"].append("系统健康，无需干预")
    
    # 保存报告
    report_file = REPORTS_DIR / f"darwin-report-{datetime.now().strftime('%Y%m%d')}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    log("选择", f"报告已保存: {report_file}")
    return report


# ============================================================
# 主函数
# ============================================================
def main():
    log("达尔文", "=" * 60)
    log("达尔文", "进化自动扫描启动")
    log("达尔文", "=" * 60)
    
    # 1. 用进
    active_skills, inactive_skills = scan_active_skills()
    
    # 2. 废退
    stale_files, very_stale = scan_stale_files()
    
    # 3. 变异
    new_candidates = discover_new_candidates()
    
    # 4. 自然选择
    report = generate_health_report(active_skills, inactive_skills, stale_files, very_stale, new_candidates)
    
    # 打印摘要
    log("达尔文", "=" * 60)
    log("达尔文", "扫描完成")
    s = report["summary"]
    log("达尔文", f"  技能: {s['total_skills']} (活跃 {s['active_skills']}, 非活跃 {s['inactive_skills']})")
    log("达尔文", f"  过期记忆: {s['stale_memory_files']} 降级, {s['very_stale_files']} 删除候选")
    log("达尔文", f"  新文档: {s['new_document_candidates']} 候选")
    log("达尔文", f"  建议: {len(report['recommendations'])} 条")
    log("达尔文", "=" * 60)


if __name__ == '__main__':
    main()
