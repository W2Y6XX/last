#!/usr/bin/env python3
"""
Project Analyzer using AgentLightning
This script creates a simple agent that analyzes project structure and provides insights.
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Any
from agentlightning import LitAgent, Task, Rollout, NamedResources
from agentlightning.llm_proxy import LLMProxy


class ProjectAnalyzer(LitAgent):
    """Agent for analyzing project structure and providing insights."""

    def __init__(self, project_path: str = "."):
        super().__init__()
        self.project_path = Path(project_path)

    def analyze_project_structure(self) -> Dict[str, Any]:
        """Analyze the project structure and return key insights."""
        structure = {
            "project_name": self.project_path.name,
            "total_files": 0,
            "directories": [],
            "file_types": {},
            "key_files": [],
            "analysis": {}
        }

        # Walk through the project directory
        for root, dirs, files in os.walk(self.project_path):
            # Skip hidden directories and common ignore patterns
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'node_modules', '.git']]

            structure["directories"].append(root)

            for file in files:
                if not file.startswith('.'):
                    structure["total_files"] += 1

                    # Count file types
                    ext = Path(file).suffix.lower()
                    structure["file_types"][ext] = structure["file_types"].get(ext, 0) + 1

                    # Identify key files
                    if file in ['README.md', 'pyproject.toml', 'requirements.txt', 'package.json', 'Dockerfile']:
                        structure["key_files"].append(os.path.join(root, file))

        # Generate analysis
        structure["analysis"] = self.generate_analysis(structure)

        return structure

    def generate_analysis(self, structure: Dict[str, Any]) -> Dict[str, Any]:
        """Generate insights from the project structure."""
        analysis = {
            "project_type": self.detect_project_type(structure),
            "complexity_score": self.calculate_complexity_score(structure),
            "recommendations": self.generate_recommendations(structure)
        }
        return analysis

    def detect_project_type(self, structure: Dict[str, Any]) -> str:
        """Detect the type of project based on files and structure."""
        file_types = structure["file_types"]
        key_files = structure["key_files"]

        if any('pyproject.toml' in f or 'requirements.txt' in f for f in key_files):
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
        score += min(structure["total_files"] // 10, 20)  # Up to 20 points for file count
        score += min(len(structure["file_types"]) * 2, 10)  # Up to 10 points for file type diversity
        score += min(len(structure["directories"]) // 5, 10)  # Up to 10 points for directory depth
        return score

    def generate_recommendations(self, structure: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on project structure."""
        recommendations = []

        # Check for documentation
        if not any('README' in f for f in structure["key_files"]):
            recommendations.append("Consider adding a README.md file")

        # Check for dependency management
        if not any('requirements.txt' in f or 'pyproject.toml' in f or 'package.json' in f for f in structure["key_files"]):
            recommendations.append("Consider adding dependency management file")

        # Check for Docker support
        if not any('Dockerfile' in f for f in structure["key_files"]):
            recommendations.append("Consider adding Dockerfile for containerization")

        return recommendations

    def rollout(self, task: Task, resources: NamedResources, rollout: Rollout) -> Dict[str, Any]:
        """Main rollout method that performs project analysis."""
        print(f"Analyzing project: {task.input}")

        # Perform the analysis
        analysis_result = self.analyze_project_structure()

        # Print results
        print(f"\n=== Project Analysis Results ===")
        print(f"Project Name: {analysis_result['project_name']}")
        print(f"Total Files: {analysis_result['total_files']}")
        print(f"Project Type: {analysis_result['analysis']['project_type']}")
        print(f"Complexity Score: {analysis_result['analysis']['complexity_score']}")

        print(f"\nFile Types:")
        for ext, count in analysis_result['file_types'].items():
            print(f"  {ext or 'no extension'}: {count}")

        print(f"\nKey Files:")
        for file in analysis_result['key_files']:
            print(f"  {file}")

        print(f"\nRecommendations:")
        for rec in analysis_result['analysis']['recommendations']:
            print(f"  • {rec}")

        return analysis_result


def main():
    """Main function to run the project analyzer."""
    print("=== AgentLightning Project Analyzer ===")
    print("This tool analyzes project structure and provides insights.\n")

    # Create the analyzer agent
    analyzer = ProjectAnalyzer(".")

    # Create a simple task (rollout_id is required)
    task = Task(
        rollout_id="project_analysis_rollout",
        input="Analyze the current project structure"
    )

    # Create empty resources (not needed for this analysis)
    resources = {}

    # Create rollout metadata
    rollout = Rollout(
        rollout_id="project_analysis",
        task_id="analyze_project",
        agent_id="project_analyzer",
        status="running"
    )

    # Run the analysis
    try:
        result = analyzer.rollout(task, resources, rollout)

        # Save results to file
        with open("project_analysis_result.json", "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        print(f"\n=== Analysis Complete ===")
        print(f"Results saved to: project_analysis_result.json")

    except Exception as e:
        print(f"Error during analysis: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())