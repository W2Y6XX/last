#!/usr/bin/env python3
"""
HTML页面全方位解析工具
模拟chrome-devtools-mcp功能，提供全面的页面分析
"""

import os
import re
import json
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import defaultdict, Counter
import urllib.parse


class HTMLPageAnalyzer:
    """
    HTML页面全方位解析器
    提供类似Chrome DevTools的全面分析功能
    """

    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.content = ""
        self.analysis_results = {
            "file_info": {},
            "dom_analysis": {},
            "css_analysis": {},
            "javascript_analysis": {},
            "performance_analysis": {},
            "accessibility_analysis": {},
            "security_analysis": {},
            "summary": {},
            "recommendations": []
        }
        self.start_time = time.time()

    def load_file(self) -> bool:
        """加载HTML文件"""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                self.content = f.read()

            self.analysis_results["file_info"] = {
                "file_path": str(self.file_path),
                "file_size": len(self.content) / 1024,  # KB
                "line_count": len(self.content.splitlines()),
                "encoding": "utf-8",
                "load_time": time.time()
            }
            return True
        except Exception as e:
            print(f"Error loading file: {e}")
            return False

    def analyze_dom_structure(self) -> Dict[str, Any]:
        """分析DOM结构"""
        print("Analyzing DOM structure...")

        # 提取所有HTML标签
        tag_pattern = r'<(/?)([a-zA-Z][a-zA-Z0-9]*)(?:\s+[^>]*)?(/?)>'
        tags = re.findall(tag_pattern, self.content, re.IGNORECASE)

        # 统计标签使用情况
        tag_stats = Counter()
        hierarchy_depth = 0
        max_depth = 0

        for closing_slash, tag_name, opening_slash in tags:
            tag_name_lower = tag_name.lower()
            tag_stats[tag_name_lower] += 1

            # 计算嵌套深度（简化计算）
            if not closing_slash and tag_name_lower not in ['br', 'hr', 'img', 'input', 'meta', 'link']:
                hierarchy_depth += 1
                max_depth = max(max_depth, hierarchy_depth)
            elif closing_slash:
                hierarchy_depth = max(0, hierarchy_depth - 1)

        # 检查HTML5语义标签使用
        semantic_tags = ['header', 'nav', 'main', 'section', 'article', 'aside', 'footer', 'figure', 'figcaption']
        semantic_usage = {tag: tag_stats.get(tag, 0) for tag in semantic_tags}

        # 提取页面标题和meta信息
        title_match = re.search(r'<title[^>]*>(.*?)</title>', self.content, re.IGNORECASE | re.DOTALL)
        title = title_match.group(1).strip() if title_match else "No title found"

        meta_tags = re.findall(r'<meta[^>]*>', self.content, re.IGNORECASE)
        meta_info = []
        for meta in meta_tags:
            name_match = re.search(r'name=["\']([^"\']*)["\']', meta, re.IGNORECASE)
            content_match = re.search(r'content=["\']([^"\']*)["\']', meta, re.IGNORECASE)
            if name_match and content_match:
                meta_info.append({
                    "name": name_match.group(1),
                    "content": content_match.group(1)
                })

        # 分析ID和class使用
        ids = re.findall(r'id=["\']([^"\']*)["\']', self.content)
        classes = re.findall(r'class=["\']([^"\']*)["\']', self.content)

        # 提取所有class（拆分多个class）
        all_classes = []
        for class_str in classes:
            all_classes.extend(class_str.split())

        class_stats = Counter(all_classes)

        dom_analysis = {
            "total_elements": sum(tag_stats.values()),
            "unique_tags": len(tag_stats),
            "tag_distribution": dict(tag_stats.most_common(20)),
            "semantic_tags_usage": semantic_usage,
            "max_nesting_depth": max_depth,
            "page_title": title,
            "meta_tags": meta_info,
            "unique_ids": len(set(ids)),
            "duplicate_ids": len(ids) - len(set(ids)),
            "unique_classes": len(set(all_classes)),
            "most_common_classes": dict(class_stats.most_common(15)),
            "images": len(re.findall(r'<img[^>]*>', self.content, re.IGNORECASE)),
            "links": len(re.findall(r'<a[^>]*href=', self.content, re.IGNORECASE)),
            "forms": len(re.findall(r'<form[^>]*>', self.content, re.IGNORECASE))
        }

        self.analysis_results["dom_analysis"] = dom_analysis
        return dom_analysis

    def analyze_css_styles(self) -> Dict[str, Any]:
        """分析CSS样式"""
        print("Analyzing CSS styles...")

        # 提取内联CSS
        inline_styles = re.findall(r'style=["\']([^"\']*)["\']', self.content, re.IGNORECASE)

        # 提取<style>标签内容
        style_blocks = re.findall(r'<style[^>]*>(.*?)</style>', self.content, re.IGNORECASE | re.DOTALL)
        internal_css = '\n'.join(style_blocks)

        # 提取外部CSS链接
        external_css = re.findall(r'<link[^>]*rel=["\']stylesheet["\'][^>]*href=["\']([^"\']*)["\']', self.content, re.IGNORECASE)

        # 分析CSS选择器
        selector_pattern = r'([^{]+)\s*\{([^}]*)\}'
        selectors = re.findall(selector_pattern, internal_css)

        css_analysis = {
            "inline_styles_count": len(inline_styles),
            "internal_css_size": len(internal_css) / 1024,  # KB
            "external_css_links": external_css,
            "total_selectors": len(selectors),
            "complex_selectors": [],
            "animation_rules": 0,
            "media_queries": len(re.findall(r'@media', internal_css, re.IGNORECASE)),
            "keyframes": len(re.findall(r'@keyframes', internal_css, re.IGNORECASE))
        }

        # 分析复杂选择器
        for selector, rules in selectors:
            selector = selector.strip()
            if len(selector) > 50 or selector.count(' ') > 3:
                css_analysis["complex_selectors"].append({
                    "selector": selector,
                    "complexity": len(selector) + selector.count(' ') * 2
                })

        # 统计动画相关规则
        css_analysis["animation_rules"] = len(re.findall(r'animation|transition|@keyframes', internal_css, re.IGNORECASE))

        # 检查响应式设计
        viewport_meta = re.search(r'<meta[^>]*name=["\']viewport["\']', self.content, re.IGNORECASE)
        css_analysis["responsive_design"] = {
            "has_viewport_meta": bool(viewport_meta),
            "media_query_count": css_analysis["media_queries"]
        }

        # 分析颜色使用
        colors = re.findall(r'#[0-9a-fA-F]{3,6}|rgb\([^)]+\)|rgba\([^)]+\)', internal_css)
        css_analysis["unique_colors"] = len(set(colors))

        self.analysis_results["css_analysis"] = css_analysis
        return css_analysis

    def analyze_javascript(self) -> Dict[str, Any]:
        """分析JavaScript代码"""
        print("Analyzing JavaScript...")

        # 提取<script>标签内容
        script_blocks = re.findall(r'<script[^>]*>(.*?)</script>', self.content, re.IGNORECASE | re.DOTALL)
        external_scripts = re.findall(r'<script[^>]*src=["\']([^"\']*)["\']', self.content, re.IGNORECASE)

        all_js = '\n'.join(script_blocks)

        js_analysis = {
            "inline_scripts_count": len(script_blocks),
            "external_scripts": external_scripts,
            "total_js_size": len(all_js) / 1024,  # KB
            "functions": [],
            "event_listeners": [],
            "ajax_calls": 0,
            "console_logs": 0,
            "third_party_libraries": []
        }

        # 分析函数定义
        function_patterns = [
            r'function\s+(\w+)\s*\(',
            r'const\s+(\w+)\s*=\s*\([^)]*\)\s*=>',
            r'var\s+(\w+)\s*=\s*function',
            r'let\s+(\w+)\s*=\s*function',
            r'(\w+)\s*:\s*function'
        ]

        for pattern in function_patterns:
            matches = re.findall(pattern, all_js)
            js_analysis["functions"].extend(matches)

        js_analysis["unique_functions"] = len(set(js_analysis["functions"]))

        # 检测事件监听器
        event_methods = ['addEventListener', 'onclick', 'onload', 'onchange', 'onsubmit']
        for method in event_methods:
            count = len(re.findall(method, all_js))
            if count > 0:
                js_analysis["event_listeners"].append({"method": method, "count": count})

        # 检测AJAX调用
        ajax_patterns = [r'fetch\s*\(', r'\$\.ajax\s*\(', r'XMLHttpRequest', r'axios\.']
        for pattern in ajax_patterns:
            js_analysis["ajax_calls"] += len(re.findall(pattern, all_js))

        # 检测console.log
        js_analysis["console_logs"] = len(re.findall(r'console\.(log|warn|error)', all_js))

        # 检测第三方库
        library_patterns = {
            'jQuery': r'jquery|\$\.',
            'Chart.js': r'chart\.|new Chart',
            'Bootstrap': r'bootstrap',
            'React': r'react|React',
            'Vue': r'vue|Vue',
            'Angular': r'angular|ng-'
        }

        for library, pattern in library_patterns.items():
            if re.search(pattern, all_js, re.IGNORECASE):
                js_analysis["third_party_libraries"].append(library)

        self.analysis_results["javascript_analysis"] = js_analysis
        return js_analysis

    def analyze_performance(self) -> Dict[str, Any]:
        """分析性能相关指标"""
        print("Analyzing performance...")

        # 计算页面大小
        html_size = len(self.content) / 1024  # KB

        # 统计资源引用
        img_tags = re.findall(r'<img[^>]*src=["\']([^"\']*)["\']', self.content, re.IGNORECASE)
        css_links = re.findall(r'<link[^>]*href=["\']([^"\']*)["\']', self.content, re.IGNORECASE)
        js_links = re.findall(r'<script[^>]*src=["\']([^"\']*)["\']', self.content, re.IGNORECASE)

        performance_analysis = {
            "html_size_kb": html_size,
            "total_resources": len(img_tags) + len(css_links) + len(js_links),
            "images_count": len(img_tags),
            "css_files_count": len(css_links),
            "js_files_count": len(js_links),
            "external_resources": [],
            "optimization_suggestions": []
        }

        # 分析外部资源
        external_resources = css_links + js_links
        cdn_resources = []
        local_resources = []

        for resource in external_resources:
            if resource.startswith('http'):
                cdn_resources.append(resource)
            else:
                local_resources.append(resource)

        performance_analysis["external_resources"] = {
            "cdn_resources": cdn_resources,
            "local_resources": local_resources,
            "cdn_usage_percentage": len(cdn_resources) / len(external_resources) * 100 if external_resources else 0
        }

        # 性能优化建议
        if html_size > 100:
            performance_analysis["optimization_suggestions"].append("HTML文件较大，考虑压缩或拆分")

        if len(img_tags) > 20:
            performance_analysis["optimization_suggestions"].append("图片数量较多，考虑懒加载或图片优化")

        if len(js_links) > 10:
            performance_analysis["optimization_suggestions"].append("JavaScript文件过多，考虑合并或按需加载")

        # 检查defer和async属性
        scripts_with_defer = len(re.findall(r'<script[^>]*defer', self.content, re.IGNORECASE))
        scripts_with_async = len(re.findall(r'<script[^>]*async', self.content, re.IGNORECASE))

        performance_analysis["script_loading_optimization"] = {
            "scripts_with_defer": scripts_with_defer,
            "scripts_with_async": scripts_with_async,
            "optimization_score": (scripts_with_defer + scripts_with_async) / len(js_links) * 100 if js_links else 0
        }

        self.analysis_results["performance_analysis"] = performance_analysis
        return performance_analysis

    def analyze_accessibility(self) -> Dict[str, Any]:
        """分析可访问性"""
        print("Analyzing accessibility...")

        accessibility_analysis = {
            "score": 0,
            "issues": [],
            "good_practices": [],
            "checks": {}
        }

        # 检查lang属性
        lang_attr = re.search(r'<html[^>]*lang=["\'][^"\']*["\']', self.content, re.IGNORECASE)
        accessibility_analysis["checks"]["has_lang_attribute"] = bool(lang_attr)
        if lang_attr:
            accessibility_analysis["good_practices"].append("页面设置了语言属性")
        else:
            accessibility_analysis["issues"].append("缺少lang属性")

        # 检查alt属性
        img_tags = re.findall(r'<img[^>]*>', self.content, re.IGNORECASE)
        img_with_alt = len(re.findall(r'<img[^>]*alt=["\'][^"\']*["\']', self.content, re.IGNORECASE))
        accessibility_analysis["checks"]["images_with_alt"] = {
            "total": len(img_tags),
            "with_alt": img_with_alt,
            "percentage": img_with_alt / len(img_tags) * 100 if img_tags else 100
        }

        if img_with_alt < len(img_tags):
            accessibility_analysis["issues"].append(f"{len(img_tags) - img_with_alt}张图片缺少alt属性")

        # 检查表单标签
        form_inputs = re.findall(r'<input[^>]*>', self.content, re.IGNORECASE)
        labelled_inputs = len(re.findall(r'<label[^>]*for=["\'][^"\']*["\']', self.content, re.IGNORECASE))
        accessibility_analysis["checks"]["form_labels"] = {
            "inputs": len(form_inputs),
            "labelled": labelled_inputs
        }

        # 检查标题层级
        headings = re.findall(r'<h([1-6])[^>]*>(.*?)</h[1-6]>', self.content, re.IGNORECASE)
        heading_levels = [int(h[0]) for h in headings]
        accessibility_analysis["checks"]["heading_hierarchy"] = {
            "total_headings": len(headings),
            "levels_used": sorted(set(heading_levels))
        }

        # 检查ARIA标签
        aria_attributes = re.findall(r'aria-[a-zA-Z-]+=["\'][^"\']*["\']', self.content, re.IGNORECASE)
        accessibility_analysis["checks"]["aria_usage"] = len(aria_attributes)

        if aria_attributes:
            accessibility_analysis["good_practices"].append(f"使用了{len(aria_attributes)}个ARIA属性")

        # 计算可访问性评分
        total_checks = 5
        passed_checks = sum([
            accessibility_analysis["checks"]["has_lang_attribute"],
            accessibility_analysis["checks"]["images_with_alt"]["percentage"] > 80,
            len(aria_attributes) > 0,
            len(headings) > 0,
            True  # 基础检查
        ])

        accessibility_analysis["score"] = (passed_checks / total_checks) * 100

        self.analysis_results["accessibility_analysis"] = accessibility_analysis
        return accessibility_analysis

    def analyze_security(self) -> Dict[str, Any]:
        """分析安全性"""
        print("Analyzing security...")

        security_analysis = {
            "score": 100,
            "risks": [],
            "recommendations": [],
            "https_usage": False,
            "csp_present": False
        }

        # 检查HTTPS链接
        https_links = len(re.findall(r'https://', self.content))
        http_links = len(re.findall(r'http://', self.content))
        security_analysis["https_usage"] = https_links > 0
        security_analysis["mixed_content"] = http_links > 0 and https_links > 0

        if http_links > 0:
            security_analysis["risks"].append(f"发现{http_links}个HTTP链接，存在安全风险")
            security_analysis["score"] -= 10

        # 检查CSP
        csp_meta = re.search(r'content-security-policy', self.content, re.IGNORECASE)
        security_analysis["csp_present"] = bool(csp_meta)
        if not csp_meta:
            security_analysis["recommendations"].append("建议添加Content Security Policy (CSP)")
            security_analysis["score"] -= 15

        # 检查内联脚本
        inline_scripts = len(re.findall(r'<script[^>]*>(?:(?!<script).)*</script>', self.content, re.IGNORECASE | re.DOTALL))
        if inline_scripts > 5:
            security_analysis["risks"].append("大量内联脚本可能增加XSS风险")
            security_analysis["score"] -= 10

        # 检查eval()使用
        eval_usage = len(re.findall(r'eval\s*\(', self.content, re.IGNORECASE))
        if eval_usage > 0:
            security_analysis["risks"].append(f"发现{eval_usage}处eval()使用，存在代码注入风险")
            security_analysis["score"] -= 20

        # 检查敏感信息泄露
        sensitive_patterns = [
            (r'password["\']?\s*[:=]\s*["\'][^"\']+["\']', "密码信息"),
            (r'api[_-]?key["\']?\s*[:=]\s*["\'][^"\']+["\']', "API密钥"),
            (r'secret["\']?\s*[:=]\s*["\'][^"\']+["\']', "密钥信息")
        ]

        for pattern, info_type in sensitive_patterns:
            matches = re.findall(pattern, self.content, re.IGNORECASE)
            if matches:
                security_analysis["risks"].append(f"可能泄露{info_type}")
                security_analysis["score"] -= 25

        self.analysis_results["security_analysis"] = security_analysis
        return security_analysis

    def generate_summary(self) -> Dict[str, Any]:
        """生成分析摘要"""
        print("Generating summary...")

        summary = {
            "overall_score": 0,
            "analysis_time": time.time() - self.start_time,
            "page_health": "Good",
            "key_metrics": {},
            "top_issues": [],
            "quick_wins": []
        }

        # 计算各部分评分
        scores = {
            "structure": min(100, self.analysis_results["dom_analysis"].get("unique_tags", 0) * 2),
            "styling": min(100, 100 - len(self.analysis_results["css_analysis"].get("complex_selectors", [])) * 5),
            "functionality": min(100, self.analysis_results["javascript_analysis"].get("unique_functions", 0) * 2),
            "performance": min(100, 100 - len(self.analysis_results["performance_analysis"].get("optimization_suggestions", [])) * 10),
            "accessibility": self.analysis_results["accessibility_analysis"].get("score", 0),
            "security": self.analysis_results["security_analysis"].get("score", 0)
        }

        summary["key_metrics"] = scores
        summary["overall_score"] = sum(scores.values()) / len(scores)

        # 确定页面健康状态
        if summary["overall_score"] >= 80:
            summary["page_health"] = "Excellent"
        elif summary["overall_score"] >= 60:
            summary["page_health"] = "Good"
        elif summary["overall_score"] >= 40:
            summary["page_health"] = "Fair"
        else:
            summary["page_health"] = "Poor"

        # 收集主要问题
        all_issues = []

        # DOM问题
        if self.analysis_results["dom_analysis"].get("duplicate_ids", 0) > 0:
            all_issues.append({
                "category": "Structure",
                "severity": "Medium",
                "issue": f"发现{self.analysis_results['dom_analysis']['duplicate_ids']}个重复ID"
            })

        # 性能问题
        perf_issues = self.analysis_results["performance_analysis"].get("optimization_suggestions", [])
        for issue in perf_issues:
            all_issues.append({
                "category": "Performance",
                "severity": "High",
                "issue": issue
            })

        # 可访问性问题
        a11y_issues = self.analysis_results["accessibility_analysis"].get("issues", [])
        for issue in a11y_issues:
            all_issues.append({
                "category": "Accessibility",
                "severity": "Medium",
                "issue": issue
            })

        # 安全问题
        sec_risks = self.analysis_results["security_analysis"].get("risks", [])
        for risk in sec_risks:
            all_issues.append({
                "category": "Security",
                "severity": "High",
                "issue": risk
            })

        # 按严重程度排序
        severity_order = {"High": 3, "Medium": 2, "Low": 1}
        summary["top_issues"] = sorted(all_issues, key=lambda x: severity_order.get(x["severity"], 0), reverse=True)[:10]

        # 快速改进建议
        summary["quick_wins"] = [
            "为所有图片添加alt属性以改善可访问性",
            "启用脚本压缩以减少页面大小",
            "使用CDN加速静态资源加载",
            "添加Content Security Policy提高安全性"
        ]

        self.analysis_results["summary"] = summary
        return summary

    def generate_recommendations(self) -> List[Dict[str, Any]]:
        """生成优化建议"""
        print("Generating recommendations...")

        recommendations = []

        # 性能优化建议
        if self.analysis_results["performance_analysis"]["html_size_kb"] > 100:
            recommendations.append({
                "category": "Performance",
                "priority": "High",
                "title": "优化HTML大小",
                "description": "HTML文件较大，建议进行压缩和优化",
                "estimated_impact": "页面加载速度提升20-30%"
            })

        # CSS优化建议
        complex_selectors = self.analysis_results["css_analysis"].get("complex_selectors", [])
        if len(complex_selectors) > 5:
            recommendations.append({
                "category": "CSS",
                "priority": "Medium",
                "title": "简化CSS选择器",
                "description": f"发现{len(complex_selectors)}个复杂CSS选择器，建议简化",
                "estimated_impact": "CSS解析速度提升10-15%"
            })

        # JavaScript优化建议
        if self.analysis_results["javascript_analysis"]["console_logs"] > 5:
            recommendations.append({
                "category": "JavaScript",
                "priority": "Low",
                "title": "清理调试代码",
                "description": f"发现{self.analysis_results['javascript_analysis']['console_logs']}处console日志，生产环境应移除",
                "estimated_impact": "减少代码体积和提升轻微性能"
            })

        # 可访问性改进
        a11y_score = self.analysis_results["accessibility_analysis"]["score"]
        if a11y_score < 80:
            recommendations.append({
                "category": "Accessibility",
                "priority": "Medium",
                "title": "改善可访问性",
                "description": f"当前可访问性评分为{a11y_score}，建议添加更多ARIA标签和语义化HTML",
                "estimated_impact": "提升用户体验和SEO排名"
            })

        # 安全性改进
        sec_score = self.analysis_results["security_analysis"]["score"]
        if sec_score < 90:
            recommendations.append({
                "category": "Security",
                "priority": "High",
                "title": "增强安全性",
                "description": f"安全评分为{sec_score}，建议添加CSP和移除不安全的外部资源",
                "estimated_impact": "降低安全风险，保护用户数据"
            })

        self.analysis_results["recommendations"] = recommendations
        return recommendations

    def run_complete_analysis(self) -> Dict[str, Any]:
        """运行完整分析"""
        print("=== HTML Page全方位解析开始 ===")
        print(f"分析文件: {self.file_path}")

        if not self.load_file():
            return {"error": "Failed to load HTML file"}

        # 执行各项分析
        self.analyze_dom_structure()
        self.analyze_css_styles()
        self.analyze_javascript()
        self.analyze_performance()
        self.analyze_accessibility()
        self.analyze_security()
        self.generate_summary()
        self.generate_recommendations()

        return self.analysis_results

    def save_report(self, output_dir: str = "html_analysis_reports") -> List[str]:
        """保存分析报告"""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        timestamp = time.strftime("%Y%m%d_%H%M%S")
        saved_files = []

        # 保存完整JSON报告
        json_file = output_path / f"html_analysis_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(self.analysis_results, f, indent=2, ensure_ascii=False)
        saved_files.append(str(json_file))

        # 保存摘要报告
        summary_file = output_path / f"html_summary_{timestamp}.md"
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(self.generate_markdown_report())
        saved_files.append(str(summary_file))

        # 保存性能指标
        perf_file = output_path / f"performance_metrics_{timestamp}.json"
        with open(perf_file, 'w', encoding='utf-8') as f:
            json.dump(self.analysis_results["performance_analysis"], f, indent=2)
        saved_files.append(str(perf_file))

        return saved_files

    def generate_markdown_report(self) -> str:
        """生成Markdown格式报告"""
        summary = self.analysis_results["summary"]

        report = f"""# HTML页面分析报告

## 基本信息
- **文件路径**: {self.analysis_results['file_info']['file_path']}
- **文件大小**: {self.analysis_results['file_info']['file_size']:.2f} KB
- **分析时间**: {time.strftime('%Y-%m-%d %H:%M:%S')}
- **页面标题**: {self.analysis_results['dom_analysis']['page_title']}

## 总体评分
- **综合评分**: {summary['overall_score']:.1f}/100
- **页面健康状态**: {summary['page_health']}
- **分析耗时**: {summary['analysis_time']:.2f}秒

## 各项指标评分
"""

        for metric, score in summary['key_metrics'].items():
            report += f"- **{metric.title()}**: {score:.1f}/100\n"

        report += f"""
## 页面统计
- **总元素数**: {self.analysis_results['dom_analysis']['total_elements']}
- **唯一标签数**: {self.analysis_results['dom_analysis']['unique_tags']}
- **图片数量**: {self.analysis_results['dom_analysis']['images']}
- **链接数量**: {self.analysis_results['dom_analysis']['links']}
- **表单数量**: {self.analysis_results['dom_analysis']['forms']}

## 主要问题
"""

        for issue in summary['top_issues'][:5]:
            report += f"### {issue['category']} - {issue['severity']}\n"
            report += f"- {issue['issue']}\n\n"

        report += "## 优化建议\n\n"

        for rec in self.analysis_results['recommendations'][:5]:
            report += f"### {rec['title']} ({rec['priority']})\n"
            report += f"**类别**: {rec['category']}\n\n"
            report += f"**描述**: {rec['description']}\n\n"
            report += f"**预期影响**: {rec['estimated_impact']}\n\n"

        return report


def main():
    """主函数"""
    file_path = "D:/connect/frontend/88.html"

    if not os.path.exists(file_path):
        print(f"Error: File not found - {file_path}")
        return

    # 创建分析器
    analyzer = HTMLPageAnalyzer(file_path)

    # 运行完整分析
    results = analyzer.run_complete_analysis()

    if "error" in results:
        print(f"Analysis failed: {results['error']}")
        return

    # 保存报告
    saved_files = analyzer.save_report()

    # 打印摘要
    summary = results["summary"]
    print(f"\n=== 分析完成 ===")
    print(f"综合评分: {summary['overall_score']:.1f}/100")
    print(f"页面健康状态: {summary['page_health']}")
    print(f"发现问题数: {len(summary['top_issues'])}")
    print(f"优化建议数: {len(results['recommendations'])}")

    print(f"\n报告已保存到:")
    for file_path in saved_files:
        print(f"  - {file_path}")

    print(f"\n=== 详细信息 ===")
    print(f"文件大小: {results['file_info']['file_size']:.2f} KB")
    print(f"DOM元素: {results['dom_analysis']['total_elements']}")
    print(f"CSS选择器: {results['css_analysis']['total_selectors']}")
    print(f"JavaScript函数: {results['javascript_analysis']['unique_functions']}")
    print(f"可访问性评分: {results['accessibility_analysis']['score']:.1f}/100")
    print(f"安全评分: {results['security_analysis']['score']:.1f}/100")


if __name__ == "__main__":
    main()