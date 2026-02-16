# How To: DyTopo Agent Orchestration

  - DyTopo (die-toe-po)
    - Dynamic Topology Agent Management


  - Using Simulated Semantic Matching

**Paper:** [Dynamic Topology Routing for Multi-Agent Reasoning via Semantic Matching](https://arxiv.org/pdf/2602.06039)


## Advantage of DyTopo Agent Interaction

One of the most striking advantages of the DyTopo framework is indeed how dramatically it boosts the performance of smaller or weaker LLM backbones—such as Qwen3-8B—bringing them much closer to (or even surpassing in relative gains) the results achieved by much larger models.

The great advantage of using DyTops for Software Engineering is the fact that all important aspects of software development can be automated and optimized using DyTopo agents, leading to increased efficiency and productivity. Good architecture practice, Good programming practice is applied functions are always tested; architecture, code and tests are always reviewed, on every round.

## These scripts work within Aider-Desk Agents

## Latest Changes
Added prompts specific to Kimi-K2's review and requirements.
- Process validation against DyTopo Documentation.
- Validation of consistency between agent scripts.
- Reduction of ambiguity in agent roles and responsibilities.
- Enhanced clarity in agent communication patterns.


## Pre-requisites

- Ensure you have the latest version of Aider-Desk installed.
- Familiarize yourself with the basic usage of Aider-Desk Agents.
- Understand the concept of DyTopo Agents and their role in Aider-Desk.

- Redis for key-value storage for Agent Communication.
- MCP Server python-sandbox for SLUID (Short Local Unique Identifier) generation (used for Agentic Message Identification).
- Always output this data when it is created.
- Always ouput reports to the User in human-readable form along with the ReqLUID and the TaskLUID.

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
     - simulates semantic matching (when done properly, requires performing math operations on the vector embeddings of the worker's responses as defined in the paper). But basically decides the next appropriate DT-Worker to hand off any of the tasks returned from the work done in the prior round (Round-0), if more work needs to be done on that task.
     - Thus, a task returned by DT-Architect, if the work looks complete, will be handed off to DT-Reviewer to review before implementation by DT-Dev (The Programmer).
     - Now, we are at Round-1. The DT-Manager will then decide which tasks to send to which worker agents and does so.
     - Worker agent does work based on the data they have, when they can go no further, reports back to the DT-Manager.
     - And, the cycle of rounds continues until there are no-more tasks to execute, and the request is fulfilled, to the best ability of the team of agents.
 
So far, I have found this agentic process quite workable. You can see the agents working on their tasks in parallel on Aider-Desk. And where your input-verification is required, you will be prompted.

## Differences from true DyTopo Process
  - The true DyTopo process is more complex, involving calculation on vector embeddings. The process simply replaces those calculations with the reasoning skills of LLM used by the DT-Manager.
  - So far, I hove found that the Grok's ability to simulate semantic matching is pretty good, and I am getting great results from it.

## Future improvements
  - The calculations required to perform semantic matching can be performed using an MCP Service. The endpoints for such a service are outlined in my research document [0-DyTopo_Agent_Prompts_and_Research.md](https://github.com/dsidlo/DyTopo-Agents-4-AD/blob/main/DyTopo%20Agent%20Instructions/0-DyTopo_Agent_Prompts_and_Research.md) if you are interested.

## Create these Agents by Name in Aider-Desk

  - Then **copy and paste** the full prompt for each agent into the Rules dialog appropriate for each agent.
  - Give each sub-agent a different color.

## Key Agent Setting

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
Direct to DT-Master: Apply DyTopo to resolve these issues.
The following error occured ...
"""
<Runtime Error...>
"""
```

## Conclusion

Let me know of your experience with using using these Agent Orchestration prompts in the Discussions Thread.

 ## Licence

  - MIT License