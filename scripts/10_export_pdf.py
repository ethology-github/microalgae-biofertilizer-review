# -*- encoding: utf-8 -*-
"""
PDF导出脚本 - 使用pandoc + xelatex将Markdown转换为PDF

功能：
1. check_dependencies() - 检查pandoc和xelatex是否已安装
2. convert_md_to_pdf(input_md, output_pdf, citation_style) - 使用pandoc转换Markdown为PDF

命令行参数：
--input: 输入Markdown文件路径
--output: 输出PDF文件路径
--citation-style: 引用样式文件路径 (default: gbt7714)
--check-deps: 仅检查依赖是否满足
"""

import argparse
import logging
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

# 尝试从utils导入setup_logging，失败时使用内联实现
try:
    sys.path.insert(0, str(Path(__file__).parent))
    from utils import setup_logging
except ImportError:
    def setup_logging(name='pdf_export'):
        logger = logging.getLogger(name)
        if not logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger


logger = setup_logging('pdf_export')


def check_dependencies() -> bool:
    """检查pandoc和xelatex是否已安装
    
    Returns:
        bool: 所有依赖都满足返回True，否则返回False
    """
    logger.info("检查PDF导出依赖...")
    
    missing = []
    
    # 检查pandoc
    if shutil.which('pandoc') is None:
        missing.append('pandoc')
        logger.error("pandoc 未安装或不在PATH中")
    else:
        pandoc_version = subprocess.run(
            ['pandoc', '--version'],
            capture_output=True,
            text=True
        )
        version_line = pandoc_version.stdout.split('\n')[0]
        logger.info(f"pandoc 已安装: {version_line}")
    
    # 检查xelatex
    if shutil.which('xelatex') is None:
        missing.append('xelatex')
        logger.error("xelatex 未安装或不在PATH中")
    else:
        xelatex_version = subprocess.run(
            ['xelatex', '--version'],
            capture_output=True,
            text=True
        )
        version_line = xelatex_version.stdout.split('\n')[0]
        logger.info(f"xelatex 已安装: {version_line}")
    
    if missing:
        logger.error(f"缺少依赖: {', '.join(missing)}")
        logger.info("安装提示:")
        logger.info("  macOS: brew install pandoc && brew install --cask mactex")
        logger.info("  Ubuntu: sudo apt install pandoc texlive-xetex")
        logger.info("  Windows: 下载安装 pandoc 和 MiKTeX")
        return False
    
    logger.info("所有依赖检查通过")
    return True


def convert_md_to_pdf(
    input_md: str,
    output_pdf: str,
    citation_style: Optional[str] = None
) -> bool:
    """使用pandoc将Markdown文件转换为PDF
    
    Args:
        input_md: 输入Markdown文件路径
        output_pdf: 输出PDF文件路径
        citation_style: 引用样式文件路径 (可选)
    
    Returns:
        bool: 转换成功返回True，否则返回False
    """
    input_path = Path(input_md)
    output_path = Path(output_pdf)
    
    # 检查输入文件
    if not input_path.exists():
        logger.error(f"输入文件不存在: {input_md}")
        return False
    
    # 确保输出目录存在
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 构建pandoc命令
    cmd = [
        'pandoc',
        str(input_path),
        '-o', str(output_path),
        '--pdf-engine=xelatex',
        '-V', 'mainfont=SimHei',
        '-V', 'CJKmainfont=SimHei',
        '--toc', '--toc-depth=3',
        '--number-sections',
        '--citeproc'
    ]
    
    # 添加引用样式文件
    if citation_style:
        style_path = Path(citation_style)
        if style_path.exists():
            cmd.extend(['--csl', str(style_path)])
            logger.info(f"使用引用样式: {citation_style}")
        else:
            logger.warning(f"引用样式文件不存在: {citation_style}，忽略")
    
    logger.info(f"执行命令: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5分钟超时
        )
        
        if result.returncode != 0:
            logger.error(f"pandoc转换失败 (返回码 {result.returncode})")
            if result.stderr:
                logger.error(f"错误信息: {result.stderr}")
            return False
        
        if output_path.exists():
            size_kb = output_path.stat().st_size / 1024
            logger.info(f"PDF导出成功: {output_pdf} ({size_kb:.1f} KB)")
            return True
        else:
            logger.error("PDF文件未生成")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error("PDF转换超时（超过5分钟）")
        return False
    except Exception as e:
        logger.error(f"PDF转换异常: {e}")
        return False


def main():
    """主函数 - 处理命令行参数"""
    parser = argparse.ArgumentParser(
        description='PDF导出脚本 - 使用pandoc + xelatex将Markdown转换为PDF',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s --input report.md --output report.pdf
  %(prog)s --input report.md --output report.pdf --citation-style gbt7714.csl
  %(prog)s --check-deps
        """
    )
    
    parser.add_argument(
        '--input', '-i',
        help='输入Markdown文件路径',
        required=False
    )
    
    parser.add_argument(
        '--output', '-o',
        help='输出PDF文件路径',
        required=False
    )
    
    parser.add_argument(
        '--citation-style', '-c',
        help='引用样式文件路径 (default: gbt7714)',
        default=None
    )
    
    parser.add_argument(
        '--check-deps',
        action='store_true',
        help='仅检查依赖是否满足，不执行转换'
    )
    
    args = parser.parse_args()
    
    # 仅检查依赖
    if args.check_deps:
        success = check_dependencies()
        sys.exit(0 if success else 1)
    
    # 检查必要参数
    if not args.input or not args.output:
        parser.print_help()
        sys.exit(1)
    
    # 检查依赖
    if not check_dependencies():
        sys.exit(1)
    
    # 执行转换
    success = convert_md_to_pdf(
        args.input,
        args.output,
        args.citation_style
    )
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
