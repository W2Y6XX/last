#!/usr/bin/env python3
"""
Simple AgentLightning Demo
This demonstrates how to use AgentLightning concepts without the complex infrastructure.
"""

import os
import ast
import json
from typing import Dict, List, Any
from pathlib import Path


class SimpleCodeAnalyzer:
    """
    A simplified code analyzer that demonstrates AgentLightning-like capabilities.
    This shows how you can apply AgentLightning concepts to your project.
    """

    def __init__(self):
        self.analysis_results = []

    def analyze_project_code(self, project_path: str = ".") -> Dict[str, Any]:
        """
        Analyze all Python code in the project.
        This mimics what an AgentLightning agent would do.
        """
        print(f"=== Simple AgentLightning Demo: Code Analysis ===")
        print(f"Analyzing project: {project_path}")

        results = {
            "project_path": project_path,
            "files_analyzed": 0,
            "total_python_files": 0,
            "analysis_summary": {},
            "findings": [],
            "recommendations": []
        }

        # Find all Python files
        python_files = list(Path(project_path).rglob("*.py"))

        # Skip common ignore patterns
        python_files = [f for f in python_files if not any(
            part.startswith('.') or part in ['__pycache__', 'node_modules', '.git']
            for part in f.parts
        )]

        results["total_python_files"] = len(python_files)

        print(f"Found {len(python_files)} Python files")

        # Analyze each file
        for file_path in python_files[:10]:  # Limit to first 10 for demo
            try:
                file_analysis = self.analyze_single_file(file_path)
                if file_analysis:
                    results["files_analyzed"] += 1
                    results["findings"].append(file_analysis)
                    print(f"  [OK] Analyzed: {file_path.relative_to(project_path)}")
            except Exception as e:
                print(f"  [ERROR] Analyzing {file_path}: {e}")

        # Generate summary and recommendations
        results["analysis_summary"] = self.generate_summary(results["findings"])
        results["recommendations"] = self.generate_recommendations(results["findings"])

        return results

    def analyze_single_file(self, file_path: Path) -> Dict[str, Any]:
        """Analyze a single Python file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Parse AST
            tree = ast.parse(content)

            analysis = {
                "file_path": str(file_path),
                "relative_path": str(file_path),
                "lines_of_code": len([line for line in content.splitlines() if line.strip() and not line.strip().startswith('#')]),
                "functions": [],
                "classes": [],
                "imports": [],
                "complexity_indicators": {
                    "nested_loops": 0,
                    "exception_handling": 0,
                    "function_length": 0
                },
                "potential_issues": []
            }

            # Analyze AST
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    analysis["functions"].append({
                        "name": node.name,
                        "line_number": node.lineno,
                        "arg_count": len(node.args.args)
                    })

                    # Check function length
                    if hasattr(node, 'end_lineno') and node.end_lineno:
                        func_length = node.end_lineno - node.lineno + 1
                        if func_length > 50:
                            analysis["potential_issues"].append({
                                "type": "long_function",
                                "function": node.name,
                                "line": node.lineno,
                                "length": func_length
                            })

                elif isinstance(node, ast.ClassDef):
                    analysis["classes"].append({
                        "name": node.name,
                        "line_number": node.lineno,
                        "method_count": len([n for n in node.body if isinstance(n, ast.FunctionDef)])
                    })

                elif isinstance(node, (ast.For, ast.While)):
                    # Check for nested loops
                    if any(isinstance(parent, (ast.For, ast.While)) for parent in ast.walk(tree)
                           if hasattr(parent, 'lineno') and hasattr(node, 'lineno')
                           and parent.lineno < node.lineno):
                        analysis["complexity_indicators"]["nested_loops"] += 1

                elif isinstance(node, ast.Try):
                    analysis["complexity_indicators"]["exception_handling"] += 1

                elif isinstance(node, ast.Import):
                    analysis["imports"].extend([alias.name for alias in node.names])

                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        analysis["imports"].append(node.module)

            return analysis

        except SyntaxError as e:
            return {
                "file_path": str(file_path),
                "error": f"Syntax error: {e}",
                "line": e.lineno
            }
        except Exception as e:
            return {
                "file_path": str(file_path),
                "error": f"Analysis error: {e}"
            }

    def generate_summary(self, findings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate summary statistics from findings."""
        summary = {
            "total_lines_of_code": 0,
            "total_functions": 0,
            "total_classes": 0,
            "total_imports": set(),
            "total_issues": 0,
            "average_function_per_file": 0,
            "most_common_imports": []
        }

        for finding in findings:
            if "error" not in finding:
                summary["total_lines_of_code"] += finding["lines_of_code"]
                summary["total_functions"] += len(finding["functions"])
                summary["total_classes"] += len(finding["classes"])
                summary["total_imports"].update(finding["imports"])
                summary["total_issues"] += len(finding["potential_issues"])

        # Calculate averages
        if findings:
            summary["average_function_per_file"] = summary["total_functions"] / len(findings)

        # Most common imports
        import_counts = {}
        for imp in summary["total_imports"]:
            import_counts[imp] = import_counts.get(imp, 0) + 1

        summary["most_common_imports"] = sorted(
            import_counts.items(), key=lambda x: x[1], reverse=True
        )[:10]

        # Convert set back to list for JSON serialization
        summary["total_imports"] = list(summary["total_imports"])

        return summary

    def generate_recommendations(self, findings: List[Dict[str, Any]]) -> List[str]:
        """Generate recommendations based on analysis."""
        recommendations = []

        total_issues = sum(len(f.get("potential_issues", [])) for f in findings)
        if total_issues > 0:
            recommendations.append(f"Address {total_issues} potential code quality issues")

        # Check for large functions
        long_functions = [issue for f in findings for issue in f.get("potential_issues", [])
                          if issue.get("type") == "long_function"]
        if long_functions:
            recommendations.append(f"Consider refactoring {len(long_functions)} long functions")

        # Check for exception handling
        total_exception_handling = sum(f["complexity_indicators"]["exception_handling"] for f in findings)
        if total_exception_handling == 0:
            recommendations.append("Consider adding exception handling to improve code robustness")

        # Check for documentation
        documented_files = len([f for f in findings if len(f.get("functions", [])) > 0])
        if documented_files > 0:
            recommendations.append("Consider adding docstrings to functions and classes")

        return recommendations

    def save_results(self, results: Dict[str, Any], output_file: str = "agentlightning_demo_results.json"):
        """Save analysis results to JSON file."""
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            print(f"\n[SUCCESS] Results saved to: {output_file}")
        except Exception as e:
            print(f"\n[ERROR] Failed to save results: {e}")

    def print_summary(self, results: Dict[str, Any]):
        """Print a summary of the analysis results."""
        print(f"\n=== Analysis Summary ===")
        print(f"Files analyzed: {results['files_analyzed']}/{results['total_python_files']}")

        summary = results["analysis_summary"]
        print(f"Total lines of code: {summary['total_lines_of_code']}")
        print(f"Total functions: {summary['total_functions']}")
        print(f"Total classes: {summary['total_classes']}")
        print(f"Total issues found: {summary['total_issues']}")
        print(f"Average functions per file: {summary['average_function_per_file']:.1f}")

        if summary["most_common_imports"]:
            print(f"\nMost common imports:")
            for imp, count in summary["most_common_imports"][:5]:
                print(f"  {imp}: {count}")

        if results["recommendations"]:
            print(f"\nRecommendations:")
            for rec in results["recommendations"]:
                print(f"  - {rec}")

        print(f"\n=== AgentLightning Integration Potential ===")
        print("This analysis demonstrates how AgentLightning can be used to:")
        print("  - Automate code quality analysis")
        print("  - Identify potential issues and improvements")
        print("  - Generate actionable recommendations")
        print("  - Scale analysis across large codebases")
        print("  - Integrate with development workflows")


def main():
    """Main function to run the demo."""
    print("=== AgentLightning Integration Demo ===")
    print("This demo shows how AgentLightning concepts can be applied to your project.\n")

    # Create analyzer
    analyzer = SimpleCodeAnalyzer()

    # Run analysis
    results = analyzer.analyze_project_code(".")

    # Print summary
    analyzer.print_summary(results)

    # Save results
    analyzer.save_results(results)

    print(f"\n=== Integration Steps ===")
    print("To integrate AgentLightning into your project:")
    print("1. Replace SimpleCodeAnalyzer with LitAgent subclasses")
    print("2. Use AgentLightning's task management for distributed analysis")
    print("3. Implement LLM-powered code analysis for deeper insights")
    print("4. Set up automated analysis pipelines")
    print("5. Integrate with your existing development tools")

    print(f"\n[SUCCESS] Demo completed successfully!")


if __name__ == "__main__":
    main()