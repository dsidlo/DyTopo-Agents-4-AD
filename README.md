# How To: DyTopo Agent Orchestration

  - DyTopo (die-toe-po)
    - Dynamic Topology Agent Management

  - Using Simulated Semantic Matching

**Paper:** [Dynamic Topology Routing for Multi-Agent Reasoning via Semantic Matching](https://arxiv.org/pdf/2602.06039)

## Latest: Added pi coding DyTopo Agent skills.

- I recently discovered the [pi-mono](https://github.com/badlogic/pi-mono) AI coding environment and have been enjoying using it with ollama kimi-k2:cloud.
- I created a DyTopo Agent skill that I've been using on some medium-sized codebases and have found it to be very effective.
- If you use pi, try it out and let me know what you think!

## Advantage of DyTopo Agent Interaction

One of the most striking advantages of the DyTopo framework is indeed how dramatically it boosts the performance of smaller or weaker LLM backbones—such as Qwen3-8B—bringing them much closer to (or even surpassing in relative gains) the results achieved by much larger models.

The great advantage of using DyTops for Software Engineering is the fact that all important aspects of software development can be automated and optimized using DyTopo agents, leading to increased efficiency and productivity. Good architecture practice, Good programming practice is applied functions are always tested; architecture, code and tests are always reviewed, on every round.

## These scripts work within pi and Aider-Desk Agents

## Pre-requisites

- Ensure you have the latest version of Aider-Desk installed.
- Familiarize yourself with the basic usage of Aider-Desk Agents.
- Understand the concept of DyTopo Agents and their role in Aider-Desk.
- Redis for key-value storage for Agent Communication.
- Redis keys are simply use date and/or time strings.
- Always output this data when it is created.
- Always output reports to the User in human-readable form along with the ReqLUID and the TaskLUID.
- A full trace of the Request's Rounds is available from Redis.

## The Agents

The DyTopo agents comprise of...
  - DT-Manager (The Software Manager and Agent Orchestrator)
  - DT-Architect (The Worker Sub-Agent)
  - DT-Dev (The Developer Worker Sub-Agent)
  - DT-Tester (The Testing Worker Sub-Agent)
  - DT-Reviewer (The Reviewer Worker Sub-Agent)

  1. DyTopo Agent Management works by first sending a (Round-0) to the all the worker agents.
  2. All the worker agents then review the request... do research on the code base... then respond back to the DT-Manager with... 
     - what they have done so for, 
     - what else may they need to continue on with making progress on the request?
     - and what additional things that they can do to move the request closer to fulfillment.
  3. The DT-Manager receives all the responses from (Round-0)...
     - performs semantic matching and decides the next appropriate DT-Worker to hand off any of the tasks returned from the work done in the prior round (Round-0), if more work needs to be done on that task.
     - Thus, a task returned by DT-Architect, if the work looks complete, will be handed off to DT-Reviewer to review before implementation by DT-Dev (The Programmer).
     - Now, we are at Round-1. The DT-Manager will then decide which tasks to send to which worker agents and does so.
     - Worker agent does work based on the data they have, when they can go no further, reports back to the DT-Manager.
     - And, the cycle of rounds continues until there are no-more tasks to execute, and the request is fulfilled, to the best ability of the team of agents.
 
So far, I have found this agentic process quite workable. You can see the agents working on their tasks in parallel on Aider-Desk. And where your input-verification is required, you will be prompted.

## Semantic Matching
  - pi/agnents/scripts/dt-agents/semantic_matcher.py.
    - The script currnetly uses local ollama nomic-embed-text:latest for vector embeddings.
  - In the case of Agents for pi. Semantic matching is implemented using local ollama nomic-embed-text:latest for vector embeddings and the math python lib.

### Semantic Matching in Aider is currently simulated
  - So far, I have found that the Grok's ability to simulate semantic matching is pretty good, and I am getting great results from it.
    - I need to update Aider Agents to use the symantic_matcher.py script

## Future improvements
  - The calculations required to perform semantic matching can be performed using an MCP Service. The endpoints for such a service are outlined in my research document [0-DyTopo_Agent_Prompts_and_Research.md](https://github.com/dsidlo/DyTopo-Agents-4-AD/blob/main/DyTopo%20Agent%20Instructions/0-DyTopo_Agent_Prompts_and_Research.md) if you are interested.

## Create these Agents by Name in Aider-Desk

  - Then **copy and paste** the full prompt for each agent into the Rules dialog appropriate for each agent.
  - Give each sub-agent a different color.

## pi: Installing DyTopo Agent Skills

- Copy pi/agents/scripts and pi/agents/skills into you ~/.pi/agents directory.
- dytopo-skills use pi-team for async agent operation
  - Install teams npm:@tmustier/pi-agent-teams 
    - pi install npm:pi-teams

### pi: Example Prompts

- "Send this request to async dt-manager: Use the DyTopo process to find functions that don't have unit tests. Implement the missing test ensuring that test fully covers the functions logic. Ensure that all tests pass."
  - This prompt should run as a background task.
- "As the dt-manager: Review this code base and create a Markdown document that contains all components in this codebase, their contracts and interactions with one another, using text explanations and mermaid diagrams as appropriate. Place this system overview document into the docs/ directory. Include the date in the filename."
  - The Lead Agent will block and run a team of dt-<worker> to satisfy this request.

## Aider: Key Agent Setting

### DT-Manger: (The Agentic Orchestrator)
  - Tools
    - todo: off
    - power: off
    - tasks: on
      - all-settings: Always
    - memory: on
    - MCP Servers
      - redis
      - python-sandbox
  - sub-agent: off

### DT-Architect (The Wise Architect)
  - todo: on
    - set_items: Never
    - get_items: Always
    - update_item_completion: Always
    - clear_items: Never
  - tasks
    - get-items: Always
    - get_task_message: Always
    - ..rest..: Never
  - memory: off
  - skills: off
  - power: off
    - MCP Servers
      - redis
      - probe (source code analyzer)
      - web_fetch (optional)
      - brave_search (optional)
  - sub-agent: on

### DT-Dev (Out Pro Programmer)
  - todo: on
    - set_items: Never
    - get_items: Always
    - update_item_completion: Always
    - clear_items: Never
  - tasks
    - get-items: Always
    - get_task_message: Always
    - ..rest..: Never
  - memory: off
  - skills: off
  - power: on (Calls on Aider to write code)
    - MCP Servers
      - redis
      - probe (source code analyzer)
      - web_fetch (optional)
      - brave_search (optional)
  - sub-agent: on

### DT-Tester (Writes and Runs Tests)
  - todo: on
    - set_items: Never
    - get_items: Always
    - update_item_completion: Always
    - clear_items: Never
  - tasks
    - get-items: Always
    - get_task_message: Always
    - ..rest..: Never
  - memory: off
  - skills: off
  - power: on (Calls on Aider to write code)
    - MCP Servers
      - redis
      - probe (source code analyzer)
      - web_fetch (optional)
      - brave_search (optional)

### DT-Reviewer (Reviews Plans/Code/Tests/Results)
  - todo: on
    - set_items: Never
    - get_items: Always
    - update_item_completion: Always
    - clear_items: Never
  - tasks
    - get-items: Always
    - get_task_message: Always
    - ..rest..: Never
  - memory: off
  - skills: off
  - power: off
    - MCP Servers
      - redis
      - probe (source code analyzer)
      - web_fetch (optional)
      - brave_search (optional)
  - sub-agent: on

## DyTopo Agent Orchestration in Context

Add the [DyTopo Agent Orchestration Basics](https://github.com/dsidlo/DyTopo-Agents-4-AD/blob/main/DyTopo%20Agent%20Instructions/0-DyTopo-Agent-Orchestration-Basics.md) file as to Aider-Desk's Context, if you find that the Manager needs to know about DyTopo's agent orchestration principles.

## Redis and Python-Sandbox MCP Services

  - Redis can be replaced by any other database lookup system that is has an MCP service such as SQK, Neo4J, SqLite, etc...
    Just change the text "redis" to the name of the MCP database service that is available to you.
  - python-sandbox can be replaced with allowing bash execution, or the exception of a small script that returns LUIDs, which the agent can execute, given a little more instruction in the DT-Manager.md prompt file.

## Overriding Aider-Desk's Preference to Perform Pre-Planning

As Aider-Desk has a very strong preference to perform pre-planning and to use 
```text
Launch full DyTopo with Redis integration for the following request:
  - Run tests with: uv run pytest tests/ -v
  - Fix the failing test.
"""
```

## Conclusion

Let me know of your experience with using using these Agent Orchestration prompts in the Discussions Thread.

 ## Licence

  - MIT License