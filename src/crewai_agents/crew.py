from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task, before_kickoff, after_kickoff
from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List
from tools.git_commit_tool import GitCommitTool  
from crewai_tools import (
    DirectoryReadTool,
    DirectorySearchTool,
    FileReadTool,
    FileWriterTool,
    CodeDocsSearchTool,
    CodeInterpreterTool,
)
import os
from dotenv import load_dotenv
load_dotenv()
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "")
os.environ['OPENAI_API_BASE'] = os.getenv("OPENAI_API_BASE", "")  # "http://188.245.32.59:4000/v1"
directory_read_tool = DirectoryReadTool()
# directory_search_tool = DirectorySearchTool("/repos")
file_read_tool = FileReadTool()
file_writer_tool = FileWriterTool()
code_interpreter_tool = CodeInterpreterTool(unsafe_mode=True)  # Set unsafe_mode to True if you want to allow code execution
git_commit_tool = GitCommitTool()  # Uncomment if you want to use the Git Commit Tool
# code_docs_search_tool = CodeDocsSearchTool()


# If you want to run a snippet of code before or after the crew starts,
# you can use the @before_kickoff and @after_kickoff decorators
# https://docs.crewai.com/concepts/crews#example-crew-class-with-decorators

@CrewBase
class CrewaiAgents():
    """CrewaiAgents crew"""
    agents: List[BaseAgent]
    tasks: List[Task]

    # Learn more about YAML configuration files here:
    # Agents: https://docs.crewai.com/concepts/agents#yaml-configuration-recommended
    # Tasks: https://docs.crewai.com/concepts/tasks#yaml-configuration-recommended
    
    # If you would like to add tools to your agents, you can learn more about it here:
    # https://docs.crewai.com/concepts/agents#agent-tools
    
    def __init__(self, working_directory: str):
        super().__init__()
        self.working_directory = working_directory
    
    @agent
    def planner(self) -> Agent:
        print("Creating planner agent...")
        print(f"Working directory: {self.working_directory}")
        # The planner agent is responsible for planning the tasks and delegating them to other agents
        return Agent(
            config=self.agents_config['planner'], # type: ignore[index]
            verbose=True,
            # allow_delegation=True,  # Allow the planner to delegate tasks to other agents
            working_directory=self.working_directory,  # Set the working directory for the planner agent
            tools=[
                directory_read_tool,
                # directory_search_tool,
                file_read_tool,
                code_interpreter_tool,
            ]
        )

    @agent
    def coder(self) -> Agent:
        print("Creating coder agent...")
        print(f"Working directory: {self.working_directory}")
        # The coder agent is responsible for coding the tasks assigned by the planner
        return Agent(
            config=self.agents_config['coder'], # type: ignore[index]
            verbose=True,
            allow_code_execution=True,  # Allow the coder to execute code
            
            # allow_delegation=True,  # Allow the coder to delegate tasks to other agents
            working_directory=self.working_directory,  # Set the working directory for the coder agent
            tools=[
                directory_read_tool,
                # directory_search_tool,
                file_read_tool,
                file_writer_tool,
                code_interpreter_tool,
                git_commit_tool,
            ]
        )
    
    @agent
    def tester(self) -> Agent:
        print("Creating tester agent...")
        print(f"Working directory: {self.working_directory}")
        # The tester agent is responsible for testing the code written by the coder
        return Agent(
            config=self.agents_config['tester'], # type: ignore[index]
            verbose=True,
            allow_code_execution=True,  # Allow the tester to execute code
            # allow_delegation=True,  # Allow the tester to delegate tasks to other agents
            working_directory=self.working_directory,  # Set the working directory for the tester agent
            tools=[
                directory_read_tool,
                # directory_search_tool,
                file_read_tool,
                file_writer_tool,
                code_interpreter_tool,
                git_commit_tool,
            ]
        )

    # To learn more about structured task outputs,
    # task dependencies, and task callbacks, check out the documentation:
    # https://docs.crewai.com/concepts/tasks#overview-of-a-task
    @task
    def plan_task(self) -> Task:
        return Task(
            config=self.tasks_config['plan_task'], # type: ignore[index]
        )

    @task
    def coding_task(self) -> Task:
        return Task(
            config=self.tasks_config['coding_task'], # type: ignore[index]
        )
        
    @task
    def testing_task(self) -> Task:
        return Task(
            config=self.tasks_config['testing_task'], # type: ignore[index]
        )

    @crew
    def crew(self, log_directory: str = './logs') -> Crew:
        """Creates the CrewaiAgents crew"""
        # To learn how to add knowledge sources to your crew, check out the documentation:
        # https://docs.crewai.com/concepts/knowledge#what-is-knowledge
        print("Creating crew...")
        print(f"Working directory set to: {self.working_directory}")
        
        return Crew(
            agents=self.agents, # Automatically created by the @agent decorator
            tasks=self.tasks, # Automatically created by the @task decorator
            process=Process.sequential, 
            memory=False,
            verbose=True,
            output_log_file=f'{log_directory}/crew_output.log', # Optional: specify a file to log the crew output
            # process=Process.hierarchical, # In case you wanna use that instead https://docs.crewai.com/how-to/Hierarchical/
        )

    @before_kickoff
    def before_kickoff_function(self, inputs):
        print(f"Before kickoff function with inputs: {inputs}")
        return inputs # You can return the inputs or modify them as needed

    @after_kickoff
    def after_kickoff_function(self, result):
        print(f"After kickoff function with result: {result}")
        return result # You can return the result or modify it as needed