from crewai.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field
import subprocess


class GitCommitInput(BaseModel):
    """Input schema for the Git Commit Tool."""
    message: str = Field(description="The commit message to use when committing the staged changes.")


class GitCommitTool(BaseTool):
    name: str = "Git Add Tool"
    description: str = (
        "Automatically stages all changes in the current Git repository."
    )
    args_schema: Type[BaseModel] = GitCommitInput

    def _run(self, message: str) -> str:
        try:
            # Stage all changes
            result = subprocess.run(["git", "add", "."], check=True)

            # # Perform the commit
            # result = subprocess.run(
            #     ["git", "commit", "-m", message],
            #     check=True,
            #     capture_output=True,
            #     text=True
            # )
            return f"✅ Git add successful:\n{result.stdout}"
        except subprocess.CalledProcessError as e:
            return f"❌ Git operation failed:\n{e.stderr}"
