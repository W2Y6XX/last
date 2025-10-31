#!/usr/bin/env python3
"""
Example AgentLightning Integration for Code Analysis
This demonstrates how to use AgentLightning to analyze Python code in your project.
"""

import os
import ast
from typing import Dict, List, Any, Optional
from agentlightning import LitAgent, Task, Rollout, NamedResources
from agentlightning.llm_proxy import LLMProxy


class CodeAnalysisAgent(LitAgent):
    """
    Agent for analyzing Python code structure and providing insights.
    This agent can be integrated into your existing project to automate code analysis.
    """

    def __init__(self):
        super().__init__()
        self.analysis_methods = {
            'structure': self.analyze_code_structure,
            'complexity': self.analyze_complexity,
            'dependencies': self.analyze_dependencies,
            'security': self.analyze_security_issues
        }

    def rollout(self, task: Task, resources: NamedResources, rollout: Rollout) -> Dict[str, Any]:
        """
        Main rollout method that performs code analysis.

        Args:
            task: Contains the file path or code to analyze
            resources: LLM resources for advanced analysis
            rollout: Rollout metadata

        Returns:
            Analysis results as dictionary
        """
        print(f"Starting code analysis for: {task.input}")

        # Determine what to analyze
        if os.path.isfile(task.input):
            return self.analyze_file(task.input)
        elif os.path.isdir(task.input):
            return self.analyze_directory(task.input)
        else:
            # Assume it's code content directly
            return self.analyze_code_content(task.input, "inline_code.py")

    def analyze_file(self, file_path: str) -> Dict[str, Any]:
        """Analyze a single Python file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return self.analyze_code_content(content, file_path)
        except Exception as e:
            return {"error": f"Failed to read file {file_path}: {str(e)}"}

    def analyze_directory(self, dir_path: str) -> Dict[str, Any]:
        """Analyze all Python files in a directory."""
        results = {
            "directory": dir_path,
            "files_analyzed": 0,
            "total_files": 0,
            "summary": {},
            "file_details": []
        }

        for root, dirs, files in os.walk(dir_path):
            # Skip common ignore patterns
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'node_modules']]

            for file in files:
                if file.endswith('.py'):
                    results["total_files"] += 1
                    file_path = os.path.join(root, file)
                    file_analysis = self.analyze_file(file_path)

                    if "error" not in file_analysis:
                        results["files_analyzed"] += 1
                        results["file_details"].append(file_analysis)

        # Generate summary
        if results["file_details"]:
            results["summary"] = self.generate_directory_summary(results["file_details"])

        return results

    def analyze_code_content(self, content: str, file_name: str) -> Dict[str, Any]:
        """Analyze Python code content."""
        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            return {"error": f"Syntax error in {file_name}: {str(e)}"}

        analysis = {
            "file_name": file_name,
            "lines_of_code": len(content.splitlines()),
            "structure": self.analyze_code_structure(tree),
            "complexity": self.analyze_complexity(tree),
            "dependencies": self.analyze_dependencies(tree),
            "security_issues": self.analyze_security_issues(tree),
            "metrics": self.calculate_metrics(content, tree)
        }

        return analysis

    def analyze_code_structure(self, tree: ast.AST) -> Dict[str, Any]:
        """Analyze the structure of the code."""
        structure = {
            "classes": [],
            "functions": [],
            "imports": [],
            "variables": []
        }

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                structure["classes"].append({
                    "name": node.name,
                    "methods": [n.name for n in node.body if isinstance(n, ast.FunctionDef)],
                    "base_classes": [base.id for base in node.bases if isinstance(base, ast.Name)]
                })
            elif isinstance(node, ast.FunctionDef):
                if not any(isinstance(parent, ast.ClassDef) for parent in ast.walk(tree)
                          if hasattr(parent, 'body') and node in parent.body):
                    structure["functions"].append({
                        "name": node.name,
                        "args": [arg.arg for arg in node.args.args]
                    })
            elif isinstance(node, ast.Import):
                structure["imports"].extend([alias.name for alias in node.names])
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                structure["imports"].extend([f"{module}.{alias.name}" for alias in node.names])

        return structure

    def analyze_complexity(self, tree: ast.AST) -> Dict[str, Any]:
        """Analyze code complexity."""
        complexity = {
            "cyclomatic_complexity": 0,
            "nested_depth": 0,
            "function_count": 0,
            "class_count": 0
        }

        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.While, ast.For, ast.Try)):
                complexity["cyclomatic_complexity"] += 1
            elif isinstance(node, ast.FunctionDef):
                complexity["function_count"] += 1
                complexity["nested_depth"] = max(complexity["nested_depth"],
                                               self.calculate_nested_depth(node))
            elif isinstance(node, ast.ClassDef):
                complexity["class_count"] += 1

        return complexity

    def calculate_nested_depth(self, node: ast.AST, depth: int = 0) -> int:
        """Calculate maximum nesting depth."""
        max_depth = depth
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.Try, ast.With)):
                max_depth = max(max_depth, self.calculate_nested_depth(child, depth + 1))
            else:
                max_depth = max(max_depth, self.calculate_nested_depth(child, depth))
        return max_depth

    def analyze_dependencies(self, tree: ast.AST) -> List[str]:
        """Analyze external dependencies."""
        dependencies = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    dependencies.add(alias.name.split('.')[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    dependencies.add(node.module.split('.')[0])

        return sorted(list(dependencies))

    def analyze_security_issues(self, tree: ast.AST) -> List[Dict[str, Any]]:
        """Analyze potential security issues."""
        issues = []

        for node in ast.walk(tree):
            # Check for dangerous function calls
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                    if func_name in ['eval', 'exec', 'compile']:
                        issues.append({
                            "type": "dangerous_function",
                            "function": func_name,
                            "line": node.lineno,
                            "severity": "high"
                        })
                elif isinstance(node.func, ast.Attribute):
                    if node.func.attr in ['execute', 'executemany'] and isinstance(node.func.value, ast.Name):
                        if node.func.value.id == 'cursor':
                            issues.append({
                                "type": "sql_injection_risk",
                                "function": f"{node.func.value.id}.{node.func.attr}",
                                "line": node.lineno,
                                "severity": "medium"
                            })

        return issues

    def calculate_metrics(self, content: str, tree: ast.AST) -> Dict[str, int]:
        """Calculate various code metrics."""
        lines = content.splitlines()
        return {
            "total_lines": len(lines),
            "code_lines": len([line for line in lines if line.strip() and not line.strip().startswith('#')]),
            "comment_lines": len([line for line in lines if line.strip().startswith('#')]),
            "blank_lines": len([line for line in lines if not line.strip()]),
            "docstring_count": len([node for node in ast.walk(tree)
                                   if isinstance(node, (ast.FunctionDef, ast.ClassDef))
                                   and ast.get_docstring(node)])
        }

    def generate_directory_summary(self, file_details: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate summary statistics for directory analysis."""
        summary = {
            "total_lines": 0,
            "total_functions": 0,
            "total_classes": 0,
            "total_security_issues": 0,
            "average_complexity": 0,
            "most_common_dependencies": {}
        }

        dependencies_count = {}
        total_complexity = 0

        for detail in file_details:
            if "metrics" in detail:
                summary["total_lines"] += detail["metrics"]["code_lines"]

            if "complexity" in detail:
                summary["total_functions"] += detail["complexity"]["function_count"]
                summary["total_classes"] += detail["complexity"]["class_count"]
                total_complexity += detail["complexity"]["cyclomatic_complexity"]

            if "security_issues" in detail:
                summary["total_security_issues"] += len(detail["security_issues"])

            if "dependencies" in detail:
                for dep in detail["dependencies"]:
                    dependencies_count[dep] = dependencies_count.get(dep, 0) + 1

        if file_details:
            summary["average_complexity"] = total_complexity / len(file_details)

        # Top 10 most common dependencies
        summary["most_common_dependencies"] = dict(
            sorted(dependencies_count.items(), key=lambda x: x[1], reverse=True)[:10]
        )

        return summary


def main():
    """Example usage of the CodeAnalysisAgent."""
    print("=== AgentLightning Code Analysis Example ===")

    # Create the agent
    agent = CodeAnalysisAgent()

    # Example 1: Analyze a single file
    print("\n1. Analyzing this script file...")
    task = Task(
        rollout_id="code_analysis_example",
        input=__file__  # Analyze this file
    )

    rollout = Rollout(
        rollout_id="code_analysis_example",
        task_id="code_analysis_example",
        agent_id="code_analysis_agent",
        status="running",
        input=__file__
    )

    # Empty resources for this example
    resources = {}

    # Run the analysis
    result = agent.rollout(task, resources, rollout)

    if "error" not in result:
        print(f"✅ Successfully analyzed: {result['file_name']}")
        print(f"   Lines of code: {result['metrics']['code_lines']}")
        print(f"   Functions: {result['complexity']['function_count']}")
        print(f"   Classes: {result['complexity']['class_count']}")
        print(f"   Security issues: {len(result['security_issues'])}")
    else:
        print(f"❌ Analysis failed: {result['error']}")

    # Example 2: Analyze the src directory
    print("\n2. Analyzing src directory...")
    if os.path.exists("src"):
        task.input = "src"
        result = agent.rollout(task, resources, rollout)

        if "file_details" in result:
            print(f"✅ Analyzed {result['files_analyzed']}/{result['total_files']} Python files")
            summary = result.get("summary", {})
            print(f"   Total lines of code: {summary.get('total_lines', 0)}")
            print(f"   Total functions: {summary.get('total_functions', 0)}")
            print(f"   Total classes: {summary.get('total_classes', 0)}")
            print(f"   Total security issues: {summary.get('total_security_issues', 0)}")
    else:
        print("⚠️  src directory not found")

    print("\n=== Analysis Complete ===")
    print("This example demonstrates how AgentLightning can be integrated into your project")
    print("for automated code analysis and quality assurance.")


if __name__ == "__main__":
    main()