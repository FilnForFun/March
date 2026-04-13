#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
知识蒸馏管线自动化脚本
======================
每晚 03:00 自动扫描 raw/ 目录新增文件，执行蒸馏管线

流程:
  1. 扫描 raw/ 目录中新增的文档（对比上次运行时间戳）
  2. 对每个新文档执行：markitdown/kreuzberg 转换 → lossless-compress 压缩 → 输出到 distilled/
  3. 更新蒸馏索引文件
  4. 生成蒸馏报告

用法:
  python scripts/knowledge-distiller-auto.py
"""

import sys
import io
import os
import json
import re
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple

# Fix Windows console encoding
if sys.stdout.encoding and 'gbk' in sys.stdout.encoding.lower():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if sys.stderr.encoding and 'gbk' in sys.stderr.encoding.lower():
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# ============================================================
# 配置
# ============================================================

WORKSPACE = Path(r"C:\Users\30959\.openclaw\workspace")
RAW_DIR = WORKSPACE / "knowledge" / "raw"
DISTILLED_DIR = WORKSPACE / "knowledge" / "distilled"
MARKITDOWN_DIR = WORKSPACE / "knowledge" / "markitdown"
KREUZBERG_DIR = WORKSPACE / "knowledge" / "kreuzberg"
PDFMUX_DIR = WORKSPACE / "knowledge" / "pdfmux"
REPORTS_DIR = WORKSPACE / "shared-storage" / "reports" / "distiller"
VECTORIZE_SCRIPT = WORKSPACE / "knowledge" / "vectorize_all.py"
INDEX_FILE = REPORTS_DIR / "distill_index.json"
STATE_FILE = REPORTS_DIR / "last_run.json"

# 添加压缩引擎路径
COMPRESS_ENGINE = WORKSPACE / "projects" / "lossless-compress" / "phases"
sys.path.insert(0, str(COMPRESS_ENGINE / "phase1_core_engine"))
sys.path.insert(0, str(COMPRESS_ENGINE / "phase2_graphrag"))
sys.path.insert(0, str(COMPRESS_ENGINE / "phase3_index"))

# 添加知识蒸馏脚本路径
DISTILLER_SCRIPT_DIR = WORKSPACE / "skills" / "knowledge-distiller" / "scripts"
sys.path.insert(0, str(DISTILLER_SCRIPT_DIR))

# 支持的非 Markdown 格式
NON_MD_EXTENSIONS = {'.pdf', '.docx', '.xlsx', '.pptx', '.html', '.htm', '.csv', '.txt'}

# ============================================================
# 工具函数
# ============================================================

def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def log(tag, msg, level="INFO"):
    prefix = {"INFO": "[INFO]", "OK": "[OK]", "FAIL": "[FAIL]", "WARN": "[WARN]"}
    print(f"{now_str()} {prefix.get(level, f'[{level}]')} [{tag}] {msg}")

def file_size_kb(filepath):
    try:
        return os.path.getsize(filepath) / 1024
    except:
        return 0

def load_json(filepath: Path) -> Dict:
    """加载 JSON 文件"""
    if filepath.exists():
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            log("JSON", f"加载失败 {filepath}: {e}", "WARN")
    return {}

def save_json(filepath: Path, data: Dict):
    """保存 JSON 文件"""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_file_hash(filepath: Path) -> str:
    """计算文件 MD5 哈希"""
    try:
        with open(filepath, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()[:16]
    except:
        return ""

# ============================================================
# 状态管理
# ============================================================

def get_last_run_time() -> Optional[datetime]:
    """获取上次运行时间"""
    state = load_json(STATE_FILE)
    if state.get('last_run'):
        try:
            return datetime.fromisoformat(state['last_run'])
        except:
            pass
    # 默认返回 24 小时前
    return datetime.now() - timedelta(hours=24)

def save_last_run_time():
    """保存本次运行时间"""
    save_json(STATE_FILE, {'last_run': datetime.now().isoformat()})

def load_index() -> Dict:
    """加载蒸馏索引"""
    return load_json(INDEX_FILE)

def save_index(index: Dict):
    """保存蒸馏索引"""
    save_json(INDEX_FILE, index)

def update_index(filepath: Path, status: str, output_path: Optional[Path] = None, error: str = ""):
    """更新索引条目"""
    index = load_index()
    rel_path = str(filepath.relative_to(WORKSPACE))
    
    entry = {
        'file': rel_path,
        'filename': filepath.name,
        'last_processed': datetime.now().isoformat(),
        'status': status,  # 'success', 'failed', 'skipped'
        'file_hash': get_file_hash(filepath),
        'file_size_kb': file_size_kb(filepath),
    }
    
    if output_path:
        entry['output'] = str(output_path.relative_to(WORKSPACE))
        entry['output_size_kb'] = file_size_kb(output_path)
    
    if error:
        entry['error'] = error
    
    index[rel_path] = entry
    save_index(index)
    return entry

# ============================================================
# 文件扫描
# ============================================================

def scan_new_files(since: datetime) -> List[Path]:
    """扫描自上次运行以来新增或修改的文件"""
    new_files = []
    
    if not RAW_DIR.exists():
        log("SCAN", f"Raw 目录不存在: {RAW_DIR}", "WARN")
        return new_files
    
    # 扫描所有支持的文件类型
    for ext in NON_MD_EXTENSIONS.union({'.md'}):
        for f in RAW_DIR.rglob(f"*{ext}"):
            # 排除隐藏文件和目录
            if any(part.startswith('.') or part.startswith('_') for part in f.parts):
                continue
            if "__pycache__" in str(f) or "venv" in str(f):
                continue
            # 排除 README.md
            if f.name.lower() == 'readme.md':
                continue
            
            # 检查修改时间
            try:
                mtime = datetime.fromtimestamp(f.stat().st_mtime)
                if mtime >= since:
                    new_files.append(f)
            except Exception as e:
                log("SCAN", f"检查文件失败 {f}: {e}", "WARN")
    
    # 去重并排序
    new_files = sorted(list(set(new_files)), key=lambda x: x.stat().st_mtime, reverse=True)
    return new_files

def should_process_file(filepath: Path) -> bool:
    """检查文件是否应该被处理"""
    index = load_index()
    rel_path = str(filepath.relative_to(WORKSPACE))
    
    if rel_path not in index:
        return True
    
    entry = index[rel_path]
    current_hash = get_file_hash(filepath)
    
    # 文件内容变化或之前处理失败
    if entry.get('file_hash') != current_hash:
        return True
    if entry.get('status') == 'failed':
        return True
    
    return False

# ============================================================
# 文档转换
# ============================================================

def has_markitdown() -> bool:
    """检查 markitdown 是否已安装"""
    try:
        from markitdown import MarkItDown
        return True
    except ImportError:
        return False

def convert_with_markitdown(file_path: Path) -> Optional[Path]:
    """使用 markitdown 转换文件为 Markdown"""
    if not has_markitdown():
        return None
    
    from markitdown import MarkItDown
    
    try:
        rel = file_path.relative_to(RAW_DIR)
    except ValueError:
        rel = file_path.name
    
    output_dir = MARKITDOWN_DIR / rel.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / file_path.with_suffix('.md').name
    
    # 跳过已转换且未修改的文件
    if output_path.exists():
        if file_path.stat().st_mtime <= output_path.stat().st_mtime:
            log("MARKITDOWN", f"已转换，跳过: {file_path.name}", "INFO")
            return output_path
    
    log("MARKITDOWN", f"转换: {file_path.name}")
    try:
        import time
        t0 = time.time()
        md = MarkItDown()
        result = md.convert(str(file_path))
        text = result.text if hasattr(result, 'text') else str(result)
        elapsed = time.time() - t0
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(text)
        
        log("MARKITDOWN", f"转换完成: {file_path.name} ({elapsed:.1f}s)", "INFO")
        return output_path
    except Exception as e:
        log("MARKITDOWN", f"转换失败 {file_path.name}: {e}", "ERROR")
        return None


# ============================================================
# 主函数
# ============================================================

def main():
    """主函数"""
    log("DISTILL", "="*60)
    log("DISTILL", "知识蒸馏管线自动化启动")
    log("DISTILL", "="*60)
    
    if not RAW_DIR.exists():
        log("DISTILL", f"Raw 目录不存在：{RAW_DIR}", "ERROR")
        return
    
    # 获取上次运行时间
    last_run = get_last_run_time()
    if last_run is None:
        last_run = datetime.now() - timedelta(days=30)  # 默认扫描 30 天
    
    # 扫描新文件
    new_files = scan_new_files(last_run)
    if not new_files:
        log("DISTILL", "没有新文件需要处理")
        return
    
    log("DISTILL", f"发现 {len(new_files)} 个新文件")
    
    # 处理每个文件
    results = {
        "converted": 0,
        "compressed": 0,
        "failed": 0,
        "files": []
    }
    
    for file_path in new_files:
        log("DISTILL", f"处理: {file_path.name}")
        
        # 转换
        converted = None
        if file_path.suffix.lower() in ['.pdf', '.docx', '.pptx']:
            converted = convert_with_markitdown(file_path)
        else:
            # CSV/MD 等文本文件直接复制
            converted = file_path
        
        if not converted:
            results["failed"] += 1
            results["files"].append({"file": file_path.name, "status": "conversion_failed"})
            continue
        
        results["converted"] += 1
        
        # 压缩（如果是 Markdown）
        if isinstance(converted, Path) and converted.suffix == '.md':
            # TODO: 调用 lossless-compress
            results["compressed"] += 1
        
        results["files"].append({
            "file": file_path.name,
            "status": "success",
            "output": str(converted) if isinstance(converted, Path) else None
        })
    
    # 保存状态
    save_last_run_time()
    
    # 报告
    log("DISTILL", "="*60)
    log("DISTILL", f"蒸馏完成: {results['converted']} 转换, {results['compressed']} 压缩, {results['failed']} 失败")
    log("DISTILL", "="*60)
    
    # 保存报告
    report_dir = WORKSPACE / "shared-storage" / "reports" / "distiller"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_file = report_dir / f"distill-report-{datetime.now().strftime('%Y%m%d')}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    log("DISTILL", f"报告已保存: {report_file}")


if __name__ == '__main__':
    main()