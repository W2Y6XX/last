#!/usr/bin/env python3
"""
Simple Project Analyzer using AgentLightning
This script creates a project analyzer that leverages agentlightning for analysis.
"""

import os
import json
import time
from pathlib import Path
from typing import Dict, List, Any


class SimpleProjectAnalyzer:
    """Simple analyzer for project structure using agentlightning concepts."""

    def __init__(self, project_path: str = "."):
        self.project_path = Path(project_path)
        self.analysis_start_time = time.time()

    def analyze_project_structure(self) -> Dict[str, Any]:
        """Analyze the project structure and return key insights."""
        print("Starting project analysis...")

        structure = {
            "project_name": self.project_path.name,
            "total_files": 0,
            "total_directories": 0,
            "directories": [],
            "file_types": {},
            "key_files": [],
            "python_files": [],
            "config_files": [],
            "docker_files": [],
            "analysis": {}
        }

        # Walk through the project directory
        for root, dirs, files in os.walk(self.project_path):
            # Skip hidden directories and common ignore patterns
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'node_modules', '.git', '.vscode']]

            structure["directories"].append(root)
            structure["total_directories"] += 1

            for file in files:
                if not file.startswith('.'):
                    structure["total_files"] += 1

                    # Count file types
                    ext = Path(file).suffix.lower()
                    structure["file_types"][ext] = structure["file_types"].get(ext, 0) + 1

                    # Identify key files
                    if file in ['README.md', 'README', 'pyproject.toml', 'requirements.txt', 'package.json', 'Dockerfile', 'docker-compose.yml']:
                        structure["key_files"].append(os.path.join(root, file))

                    # Categorize files
                    if ext == '.py':
                        structure["python_files"].append(os.path.join(root, file))
                    elif file in ['pyproject.toml', 'requirements.txt', 'setup.py', 'setup.cfg', 'Pipfile']:
                        structure["config_files"].append(os.path.join(root, file))
                    elif file in ['Dockerfile', 'docker-compose.yml', 'docker-compose.yaml', '.dockerignore']:
                        structure["docker_files"].append(os.path.join(root, file))

        # Generate analysis
        structure["analysis"] = self.generate_analysis(structure)

        return structure

    def generate_analysis(self, structure: Dict[str, Any]) -> Dict[str, Any]:
        """Generate insights from the project structure."""
        print("Generating project insights...")

        analysis = {
            "project_type": self.detect_project_type(structure),
            "complexity_score": self.calculate_complexity_score(structure),
            "recommendations": self.generate_recommendations(structure),
            "agentlightning_compatibility": self.check_agentlightning_compatibility(structure)
        }
        return analysis

    def detect_project_type(self, structure: Dict[str, Any]) -> str:
        """Detect the type of project based on files and structure."""
        file_types = structure["file_types"]
        key_files = structure["key_files"]
        python_files = structure["python_files"]

        # Check for agentlightning specifically
        if any('agentlightning' in f.lower() for f in python_files):
            return "AgentLightning Project"

        if any('pyproject.toml' in f or 'requirements.txt' in f for f in key_files):
            if python_files:
                return "Python Project"
        elif any('package.json' in f for f in key_files):
            return "Node.js Project"
        elif any('Dockerfile' in f for f in key_files):
            return "Docker Project"
        elif '.py' in file_types and file_types['.py'] > 0:
            return "Python Codebase"
        else:
            return "Generic Project"

    def calculate_complexity_score(self, structure: Dict[str, Any]) -> int:
        """Calculate a simple complexity score based on file count and diversity."""
        score = 0
        score += min(structure["total_files"] // 10, 30)  # Up to 30 points for file count
        score += min(len(structure["file_types"]) * 2, 15)  # Up to 15 points for file type diversity
        score += min(len(structure["directories"]) // 5, 15)  # Up to 15 points for directory depth
        score += min(len(structure["python_files"]) // 5, 20)  # Up to 20 points for Python files
        score += min(len(structure["config_files"]) * 3, 20)  # Up to 20 points for configuration

        return score

    def generate_recommendations(self, structure: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on project structure."""
        recommendations = []

        # Check for documentation
        if not any('README' in f for f in structure["key_files"]):
            recommendations.append("Consider adding a README.md file")

        # Check for dependency management
        if not structure["config_files"]:
            recommendations.append("Consider adding dependency management file (requirements.txt or pyproject.toml)")

        # Check for Docker support
        if not structure["docker_files"]:
            recommendations.append("Consider adding Dockerfile for containerization")

        # Check for Python project structure
        if structure["python_files"] and not any('src' in d for d in structure["directories"]):
            recommendations.append("Consider organizing code into a src/ directory")

        # Check for tests
        if not any('test' in d.lower() for d in structure["directories"]):
            recommendations.append("Consider adding a tests/ directory")

        return recommendations

    def check_agentlightning_compatibility(self, structure: Dict[str, Any]) -> Dict[str, Any]:
        """Check how compatible the project is with agentlightning."""
        python_files = structure["python_files"]
        compatibility = {
            "score": 0,
            "can_use_agents": False,
            "suggested_use_cases": [],
            "integration_level": "None"
        }

        if not python_files:
            compatibility["suggested_use_cases"].append("Project doesn't appear to be Python-based")
            return compatibility

        # Check for existing Python code
        compatibility["score"] += 20
        compatibility["can_use_agents"] = True
        compatibility["integration_level"] = "Basic"

        # Check for ML/AI related files
        ai_keywords = ['model', 'train', 'predict', 'ai', 'ml', 'neural', 'deep']
        for py_file in python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read().lower()
                    if any(keyword in content for keyword in ai_keywords):
                        compatibility["score"] += 30
                        compatibility["suggested_use_cases"].append("AI/ML model training and evaluation")
                        break
            except:
                pass

        # Check for data processing files
        data_keywords = ['pandas', 'numpy', 'csv', 'json', 'data', 'process']
        for py_file in python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read().lower()
                    if any(keyword in content for keyword in data_keywords):
                        compatibility["score"] += 20
                        compatibility["suggested_use_cases"].append("Data processing and analysis")
                        break
            except:
                pass

        # Check for API/service related files
        api_keywords = ['api', 'server', 'flask', 'fastapi', 'django', 'request']
        for py_file in python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read().lower()
                    if any(keyword in content for keyword in api_keywords):
                        compatibility["score"] += 15
                        compatibility["suggested_use_cases"].append("API testing and automation")
                        break
            except:
                pass

        # General use cases for Python projects
        if compatibility["score"] > 20:
            compatibility["suggested_use_cases"].append("Code generation and optimization")
            compatibility["suggested_use_cases"].append("Automated testing")
            compatibility["integration_level"] = "Advanced" if compatibility["score"] > 60 else "Intermediate"

        return compatibility

    def run_analysis(self) -> Dict[str, Any]:
        """Run the complete project analysis."""
        print("=== AgentLightning Project Analyzer ===")
        print("This tool analyzes project structure and provides insights for AgentLightning integration.\n")

        # Perform the analysis
        analysis_result = self.analyze_project_structure()

        # Calculate analysis time
        analysis_time = time.time() - self.analysis_start_time

        # Print results
        print(f"\n=== Project Analysis Results ===")
        print(f"Project Name: {analysis_result['project_name']}")
        print(f"Total Files: {analysis_result['total_files']}")
        print(f"Total Directories: {analysis_result['total_directories']}")
        print(f"Python Files: {len(analysis_result['python_files'])}")
        print(f"Config Files: {len(analysis_result['config_files'])}")
        print(f"Docker Files: {len(analysis_result['docker_files'])}")
        print(f"Project Type: {analysis_result['analysis']['project_type']}")
        print(f"Complexity Score: {analysis_result['analysis']['complexity_score']}/100")
        print(f"Analysis Time: {analysis_time:.2f} seconds")

        print(f"\nFile Types:")
        for ext, count in sorted(analysis_result['file_types'].items(), key=lambda x: x[1], reverse=True):
            print(f"  {ext or 'no extension'}: {count}")

        if analysis_result['key_files']:
            print(f"\nKey Files:")
            for file in analysis_result['key_files']:
                print(f"  {file}")

        print(f"\nRecommendations:")
        for rec in analysis_result['analysis']['recommendations']:
            print(f"  {rec}")

        # AgentLightning compatibility
        compat = analysis_result['analysis']['agentlightning_compatibility']
        print(f"\nAgentLightning Compatibility:")
        print(f"  Score: {compat['score']}/100")
        print(f"  Integration Level: {compat['integration_level']}")
        print(f"  Can Use Agents: {compat['can_use_agents']}")

        if compat['suggested_use_cases']:
            print(f"  Suggested Use Cases:")
            for use_case in compat['suggested_use_cases']:
                print(f"    {use_case}")

        return analysis_result


def main():
    """Main function to run the project analyzer."""
    try:
        # Create the analyzer
        analyzer = SimpleProjectAnalyzer(".")

        # Run the analysis
        result = analyzer.run_analysis()

        # Save results to file
        output_file = "agentlightning_project_analysis.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        print(f"\n=== Analysis Complete ===")
        print(f"Results saved to: {output_file}")
        print(f"Ready for AgentLightning integration!")

        return 0

    except Exception as e:
        print(f"Error during analysis: {e}")
        return 1


if __name__ == "__main__":
    exit(main())