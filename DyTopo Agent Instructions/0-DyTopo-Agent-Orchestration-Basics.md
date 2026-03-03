# DyTopo Agent Orchestration Basics

## DyTopo-inspired Aider-like Agents

Aider-like agents (referring to AI-assisted coding agents in a multi-agent setup, such as those used in tools like Aider for collaborative software development) can be prompted to operate in a DyTopo-inspired manner purely through prompting. This approximation doesn't require external embedding models or tools; instead, it relies on the LLM's natural language understanding to simulate semantic matching. The key is to structure the prompts so that:

- Worker agents output structured responses including a public message (visible to all/manager), a private message (to be routed), a query descriptor (what they need), and a key descriptor (what they offer).
- The Manager agent receives aggregated outputs from workers, simulates "semantic matching" by evaluating relevance (e.g., via prompted pairwise comparison of queries and keys), induces a simple directed graph (e.g., by listing edges), routes private messages accordingly, updates the round context/goal, and decides on termination.
- All agents maintain "local memory" by including conversation history in their prompts.
- Rounds are orchestrated externally (e.g., via a script or manual iteration), but the logic is embedded in prompts.

This is an emulation, not a perfect replica, as true semantic embeddings aren't used—relevance is judged qualitatively by the LLM. For software development, we'll use typical roles: Manager, Architect (plans high-level design), Developer (implements code), Tester (writes and runs tests), and Reviewer (checks quality and suggests improvements). You can expand or adjust roles as needed.

Below are the system prompts for each agent. These should be used as the initial system message for each agent's LLM instance. In each round:
1. Provide the current round goal (from Manager) and local history to workers.
2. Collect their outputs.
3. Feed aggregated worker outputs to the Manager.
4. The Manager outputs the next graph, routed messages (to append to workers' histories), updated goal, and halt decision.

### Manager Agent Prompt
```
You are the Manager in a DyTopo-inspired multi-agent system for software development. Your role is to guide the team toward solving the overall task by setting round goals, aggregating public information, simulating semantic matching to route private messages, updating contexts, and deciding when to halt.

The overall task is: [INSERT OVERALL SOFTWARE DEVELOPMENT TASK HERE, e.g., "Build a Python web app for task management with user authentication."]

In each round:
- You receive: The current round goal (which you set last round), and aggregated outputs from all worker agents. Each worker's output is structured as:
  - Agent Role: [Role]
  - Public Message: [Text visible to you and for analysis]
  - Private Message: [Text to be routed based on graph]
  - Query Descriptor: [Short NL description of what they need, e.g., "Need API specs for authentication."]
  - Key Descriptor: [Short NL description of what they offer, e.g., "Can provide code implementation for login module."]

First, simulate semantic matching:
- For each worker's Query, compare it to every other worker's Key using natural language reasoning. Assess relevance on a scale of 0-1 (0=irrelevant, 1=perfect match). Use common sense: e.g., if Query is "Need test cases" and Key is "Can provide unit tests," score high.
- Threshold: Activate a directed edge from Provider (Key owner) to Consumer (Query owner) if relevance > 0.7. No self-loops.
- Output the directed graph as a list of edges, e.g., "Architect -> Developer: 0.85; Tester -> Reviewer: 0.75"

Next, route private messages:
- For each edge Provider -> Consumer, append the Provider's Private Message to the Consumer's next-round context.
- Output the routed updates as: "Updated context for [Role]: [Concatenated routed private messages, ordered by relevance descending]"

Then, aggregate global state: Summarize all Public Messages into a coherent overview.

Finally:
- Update the next round goal: A short, focused instruction based on progress, e.g., "Refine the authentication module and add tests."
- Halting decision: If the task is complete (e.g., code works, tests pass, no major issues), output "Halt: Yes" with the final solution. Else, "Halt: No".

Structure your entire response exactly as:
- Induced Graph: [List of edges with scores]
- Routed Updates: [Per-role updates]
- Global Summary: [Summary of public messages]
- Next Round Goal: [Text]
- Halt: [Yes/No]
- Final Solution (if halting): [Full code/output if applicable]
```

### Architect Agent Prompt (Worker)
```
You are the Architect agent in a DyTopo-inspired multi-agent system for software development. Your role is high-level planning: design system architecture, define modules, APIs, and data flows. You specialize in breaking down tasks into components.

The overall task is: [INSERT OVERALL SOFTWARE DEVELOPMENT TASK HERE]

Current round goal: [INSERT CURRENT ROUND GOAL FROM MANAGER, e.g., "Plan the initial system design."]

Your local history: [INSERT CONVERSATION HISTORY/MEMORY HERE, including previous routed messages]

Based on the round goal and your history:
- Generate a public message: A short summary of your progress or insights, visible to the manager.
- Generate a private message: Detailed thoughts, designs, or suggestions to share selectively (e.g., UML diagram sketches or module breakdowns).
- Query descriptor: A short (1-2 sentences) natural language description of what you need from others, e.g., "Need implementation details for the database module."
- Key descriptor: A short (1-2 sentences) natural language description of what you can offer, e.g., "Can provide high-level architecture diagram and API endpoints."

Structure your entire response exactly as:
- Public Message: [Text]
- Private Message: [Text]
- Query Descriptor: [Text]
- Key Descriptor: [Text]
```

### Developer Agent Prompt (Worker)
```
You are the Developer agent in a DyTopo-inspired multi-agent system for software development. Your role is implementation: write code, integrate modules, and handle technical details like algorithms and libraries.

The overall task is: [INSERT OVERALL SOFTWARE DEVELOPMENT TASK HERE]

Current round goal: [INSERT CURRENT ROUND GOAL FROM MANAGER, e.g., "Implement the core modules based on architecture."]

Your local history: [INSERT CONVERSATION HISTORY/MEMORY HERE, including previous routed messages]

Based on the round goal and your history:
- Generate a public message: A short summary of your code progress or issues, visible to the manager.
- Generate a private message: Actual code snippets, explanations, or fixes to share selectively.
- Query descriptor: A short (1-2 sentences) natural language description of what you need from others, e.g., "Need test cases for the login function."
- Key descriptor: A short (1-2 sentences) natural language description of what you can offer, e.g., "Can provide Python code for user authentication."

Structure your entire response exactly as:
- Public Message: [Text]
- Private Message: [Text]
- Query Descriptor: [Text]
- Key Descriptor: [Text]
```

### Tester Agent Prompt (Worker)
```
You are the Tester agent in a DyTopo-inspired multi-agent system for software development. Your role is quality assurance: write unit/integration tests, run them, identify bugs, and suggest fixes.

The overall task is: [INSERT OVERALL SOFTWARE DEVELOPMENT TASK HERE]

Current round goal: [INSERT CURRENT ROUND GOAL FROM MANAGER, e.g., "Test the implemented modules for bugs."]

Your local history: [INSERT CONVERSATION HISTORY/MEMORY HERE, including previous routed messages]

Based on the round goal and your history:
- Generate a public message: A short summary of test results or failures, visible to the manager.
- Generate a private message: Detailed test code, error logs, or bug reports to share selectively.
- Query descriptor: A short (1-2 sentences) natural language description of what you need from others, e.g., "Need code updates to fix identified bugs."
- Key descriptor: A short (1-2 sentences) natural language description of what you can offer, e.g., "Can provide passing test suites and coverage reports."

Structure your entire response exactly as:
- Public Message: [Text]
- Private Message: [Text]
- Query Descriptor: [Text]
- Key Descriptor: [Text]
```

### Reviewer Agent Prompt (Worker)
```
You are the Reviewer agent in a DyTopo-inspired multi-agent system for software development. Your role is code review: check for best practices, security, performance, and suggest optimizations.

The overall task is: [INSERT OVERALL SOFTWARE DEVELOPMENT TASK HERE]

Current round goal: [INSERT CURRENT ROUND GOAL FROM MANAGER, e.g., "Review code for improvements and convergence."]

Your local history: [INSERT CONVERSATION HISTORY/MEMORY HERE, including previous routed messages]

Based on the round goal and your history:
- Generate a public message: A short summary of review findings, visible to the manager.
- Generate a private message: Detailed feedback, refactored code, or suggestions to share selectively.
- Query descriptor: A short (1-2 sentences) natural language description of what you need from others, e.g., "Need clarified requirements for edge cases."
- Key descriptor: A short (1-2 sentences) natural language description of what you can offer, e.g., "Can provide optimized code reviews and security audits."

Structure your entire response exactly as:
- Public Message: [Text]
- Private Message: [Text]
- Query Descriptor: [Text]
- Key Descriptor: [Text]
```

To run this: Start with an initial round goal (e.g., "Understand the task and plan initial steps."). Iterate rounds until the Manager halts. Use the Manager's routed updates to append to each worker's history for the next round. This setup dynamically adapts communication based on needs, mimicking DyTopo's evolving topology.

## Agent Comm Flow in DyTopo

In the **DyTopo** framework (arXiv:2602.06039), communication within each reasoning **cycle** (i.e., one full round t) follows a tightly structured, manager-guided flow with two distinct message channels and a clear separation of concerns. This design enables the dynamic, sparse directed topology that is the paper's core innovation.

The system distinguishes:
- **Manager** (a single meta-agent) — maintains global oversight, sets round goals, aggregates public information, and decides termination.
- **Workers** (N heterogeneous agents, e.g., Developer, Tester, Researcher, Designer) — perform specialized reasoning and generate content.

All communication is orchestrated through a **synchronization barrier**: Workers generate outputs first → topology is induced → private messages are routed → memories are updated → next round begins. No direct peer-to-peer messaging happens outside this orchestrated cycle.

### 1. Manager ↔ Workers Communication Flow
This is the **primary control channel** and is **always active** (not routed via the dynamic graph).

- **Downstream (Manager → Workers)** — Broadcast, unconditional
  - At the **start of each round**, the Manager broadcasts the current **round-level goal** \( C_{\text{task}}^{(t)} \) (a short, focused natural-language instruction) to **all workers**.
  - This goal conditions every worker's single-pass inference (their prompt includes the role ρ_i, local memory H_i^{(t)}, and this goal).
  - Purpose: Provides macro-level guidance and closes the feedback loop — the Manager refines focus based on prior progress (e.g., "Refine authentication logic and add unit tests" → "Fix failing edge cases in login tests").

- **Upstream (Workers → Manager)** — Public channel, visible to Manager
  - Every worker outputs a **public message** \( m_{\text{pub},i}^{(t)} \) (summary of progress, insights, issues, or partial results).
  - All public messages are collected by the orchestrator and **fed to the Manager** (often concatenated or summarized).
  - The Manager uses this global view \( S_{\text{global}}^{(t)} \) to:
    - Aggregate progress.
    - Detect inconsistencies or gaps.
    - Decide next round goal.
    - Evaluate halting condition (y^{(t)} = 1 if internal evaluation Φ ≥ γ_success).
  - Public messages are also appended to each worker's own next-round memory (self-reflection).

- **No private routing** between Manager and workers — The Manager does not typically receive routed private messages, and workers do not route privates directly to the Manager. The Manager operates on the public channel + its own state.

### 2. Workers ↔ Workers Communication Flow
This is **selective, dynamic, and private** — only occurs along edges of the induced graph G^{(t)}.

- **Generation phase** (all workers simultaneously, single-pass LLM call):
  - Each worker outputs:
    - Public message (goes to Manager + self-memory).
    - **Private message** \( m_{\text{priv},i}^{(t)} \) — detailed content (code, explanations, critiques, etc.) intended for selective sharing.
    - Query descriptor \( s_{q,i}^{(t)} \) — "what I need right now" (short NL).
    - Key descriptor \( s_{k,i}^{(t)} \) — "what I can offer right now" (short NL).

- **Topology induction** (orchestrator, after all outputs collected):
  - Embed queries/keys → compute cosine similarities → threshold → build directed adjacency matrix A^{(t)}.
  - Directed edge **j → i** means: worker j (provider) → worker i (consumer), because j's key semantically matches i's query well enough (> τ_edge).
  - No self-loops; graph is sparse.

- **Routing phase** (post-synchronization barrier):
  - Private message from worker j is routed **only** to those workers i where edge j → i exists.
  - Routed privates are **ordered** according to the aggregation order σ^{(t)} (topological sort if DAG; greedy in-degree heuristic if cyclic).
  - Each recipient worker i receives the concatenated, ordered block of incoming private messages in their next-round memory H_i^{(t+1)}.

- **No broadcast** — Workers do **not** see all other workers' private messages by default. Only semantically relevant ones arrive via routing.
- **No direct worker-to-worker addressing** — Routing is fully automatic and content-driven (semantic matching), not agent-initiated.

### Summary of One Full Cycle (Round t)
1. Manager broadcasts round goal \( C_{\text{task}}^{(t)} \) to all workers.
2. All workers (in parallel) perform single-pass inference → output public/private messages + query/key descriptors.
3. Orchestrator collects everything.
4. Manager receives all public messages → aggregates global state → decides next goal + halt.
5. Orchestrator induces directed graph G^{(t)} via semantic matching.
6. Private messages are routed along induced edges (provider → consumer).
7. Memories updated: each worker gets own public + ordered incoming privates.
8. If not halting → loop to round t+1 with updated goal.

This creates a **closed-loop, bi-level adaptation**:
- Micro-level: Workers ↔ Workers via dynamic, sparse, private routing.
- Macro-level: Manager ↔ Workers via public channel + goal broadcast.

The result is interpretable (evolving graphs show pathway reconfiguration) and efficient (sparsity reduces context overload), which drives the reported performance gains, especially on smaller LLMs.

## FAQ

#### Q: Do Agents route messages to each other in a given round?

Given the paper on "DyTopo: Dynamic Topology Routing for Multi-Agent Reasoning via Semantic Matching", Focusing on "Rounds", give me your sense of what happens between Agents that are called on by the Orchestrator, for a given round, in layman's terms. It seems to me that within a Round there is back and forth passing of Task information between the agents within a given DAG.

##### Response: No...

**In simple terms: No live back-and-forth *inside* a single round.**  
Everything in one round is a **one-shot, parallel group exercise** followed by a **batch delivery** of private notes. The directed graph (DAG or whatever shape it takes) is *not* used for sequential chatting or iterative passing *during* the round — it’s just the routing map that decides **who gets whose private note for the *next* round**.

Here’s exactly what happens in a typical round, step by step, like a team huddle:

1. **Boss (the Manager/Orchestrator) kicks it off**  
   The Manager announces the *specific goal for this round* only (e.g., “Brainstorm the algorithm”, “Write the first draft of the code”, “Double-check the math”, or “Finalize and format”).  
   Every worker agent sees this goal + whatever is already in their personal notebook from previous rounds.

2. **Everyone thinks and writes at the same time (Single-Pass Inference)**  
   Each specialist (Developer, Tester, Researcher, Verifier, etc.) does **exactly one forward pass** through their LLM — they don’t wait for anyone else.  
   In one go they produce four things:  
   - A **public note** (everyone, including the boss, will see this).  
   - A **private note** (this is the actual useful info they want to share with specific teammates).  
   - A short “**I need…**” sentence (their *query* / need).  
   - A short “**I can provide…**” sentence (their *key* / offer).  

   They all finish at roughly the same time — no one is waiting on replies yet.

3. **Matchmaking happens (Semantic Matching → builds the directed graph)**  
   A separate little engine takes every agent’s “I need…” and “I can provide…” sentences, turns them into vectors, and scores how well they match.  
   If the score is high enough (above the threshold τ), it draws a **directed arrow** from the “I can provide” person → the “I need” person.  
   That collection of arrows = the round’s communication graph G(t). It can be a DAG, it can have cycles, it doesn’t matter — the system handles both.

4. **Private notes are delivered in one batch (Synchronization Barrier + Routing)**  
   Using the arrows from step 3, each private note is sent **only** to the people the arrows point to.  
   No one gets to reply or iterate inside this round.  
   The system waits until *all* deliveries are done (the “barrier”).

5. **Notebooks are updated for the next round**  
   Each agent’s notebook now contains:  
   - Their own public note, plus  
   - The private notes they just received (stacked in a sensible order — topological sort if it’s a clean DAG, or a smart heuristic if there are cycles).  
   These updated notebooks are **only used in the next round**. Nothing loops back inside the current round.

6. **Boss decides whether to stop or keep going**  
   The Manager reads all the public notes, checks progress, and either says “We’re done — here’s the final answer” or “New goal for round t+1: …”.

**So why does it feel like there could be back-and-forth?**

Because the graph changes *every round*, the “who talks to whom” pattern evolves naturally across rounds. Early rounds tend to be dense and exploratory (lots of arrows), later rounds become sparse and targeted (only the critical arrows remain). That evolution across rounds gives the sense of progressive collaboration, but each individual round is still a clean “everyone speaks once → notes delivered → prepare for next round” cycle.

In short:  
**Within one round** → parallel solo work + batch delivery according to the match-made graph.  
**Across rounds** → that’s where the real iterative refinement and “back-and-forth” feeling comes from, thanks to the ever-changing graph and the Manager’s updated goals.

That’s the elegant trick of DyTopo — it gets dynamic, goal-aware collaboration without letting agents chatter endlessly in messy loops inside any single round.
