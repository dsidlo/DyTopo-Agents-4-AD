# DyTopo Rescripted for Aider-Desk


--------------
► **THINKING**

The user wants a prompt for the DT-Manager that:
1. Distills the manager's actions from the DyTopo documentation
2. Eliminates the need for the manager to "reason over logic" - instead it should just execute the logic as intended (procedural/algorithmic)
3. Eliminates Redis as the messaging conduit between agents (but still outputs to Redis for user analysis)
4. Uses existing aider-desk agent communication protocols (the subagent tool system we saw in subagents.ts)

Key insights from the code:
- Aider-desk uses `createSubagentsToolset` to create tools for invoking subagents
- Subagents are invoked via the tool `${SUBAGENTS_TOOL_GROUP_NAME}${TOOL_GROUP_NAME_SEPARATOR}${SUBAGENTS_TOOL_RUN_TASK}` with parameters `subagentId` and `prompt`
- Subagents return `{ messages: ContextMessage[], promptContext }` or `{ error, promptContext }`
- The system supports `ContextMemoryMode` (Off, LastMessage, FullContext) to control context accumulation
- Workers communicate via structured outputs (Public Message, Private Message, Query Descriptor, Key Descriptor)
- The Manager needs to implement the DyTopo cycle: Broadcast -> Collect -> Match -> Route -> Repeat

The prompt should make the LLM act as a "dumb executor" of the DyTopo protocol, not a reasoner about it. It should follow the algorithm exactly.

Structure:
1. Role definition (DT-Manager)
2. Algorithm/Procedure (step-by-step execution)
3. Input format (what it receives from previous round)
4. Output format (what it produces)
5. Tool usage (how to call workers using aider-desk subagent tools)
6. Redis output (for logging/analysis only)

Key changes from original:
- Remove Redis as communication conduit (use direct tool calls)
- Use aider-desk's subagent tool invocation instead of Redis keys
- Keep Redis only for logging the orchestration
- Make the logic procedural (if X then Y) rather than "think about what to do"

The workers (DT-Architect, DT-Developer, DT-Tester, DT-Reviewer) will be subagents configured in aider-desk with specific profiles.

The Manager needs to:
1. Generate SLUIDs (ReqSLUID, TaskSLUID, RoundSeq)
2. Broadcast round goal to all workers (via subagent tool calls)
3. Collect responses (wait for all tool results)
4. Parse structured output from each worker
5. Compute semantic matching (Query vs Key) - this can be done via LLM judgment or simple string matching in the prompt
6. Build induced graph
7. Route private messages (determine which workers get which private messages)
8. Update memories
9. Decide halt
10. Output orchestration log to Redis (for user analysis)

Wait, the user said "Eliminate the need to use Redis as the messaging conduit" - so workers don't read from Redis, they receive messages via the subagent tool invocation. But the Manager still writes to Redis for logging.

So the flow is:
- Manager calls subagent tool with the round goal + routed private messages in the prompt
- Worker executes and returns structured output
- Manager collects all returns
- Manager writes orchestration log to Redis (optional, for analysis)
- Manager proceeds to next round

Actually, looking at the subagent tool in subagents.ts, it returns the full conversation messages. So the Manager would invoke the subagent, get back the result, and extract the structured data from the response.

But wait - the DyTopo workers need to output specific fields (Agent_Role, Public_Message, Private_Message, Query_Descriptor, Key_Descriptor, Updated_Memory). The subagent tool returns `ContextMessage[]`. So the worker's final message should contain this structured data (probably as JSON in the content).

The Manager prompt needs to instruct the LLM how to:
1. Call the subagent tool (which is available as a tool to the Manager)
2. Parse the result from the subagent's return
3. Perform the matching algorithm
4. Construct the next round's prompts for each worker

Actually, looking at the code more carefully:
- The Manager is itself an agent running in aider-desk
- It has access to the subagent tool (via `createSubagentsToolset`)
- When it calls a subagent, it uses the tool and gets back a result
- The result contains the messages from the subagent

So the Manager prompt should be a system prompt that instructs it to act as the DyTopo orchestrator using the available subagent tools.

The key is to make it procedural. Instead of "think about what to do", it should be "EXECUTE the following algorithm exactly".

Algorithm steps:
1. INITIALIZATION: Generate ReqSLUID, TaskSLUID, set RoundSeq=0
2. ROUND START:
   a. Broadcast current Round Goal to all 4 workers (parallel tool calls)
   b. Wait for all 4 responses
   c. Parse each response to extract: Agent_Role, Public_Message, Private_Message, Query_Descriptor, Key_Descriptor
   d. SEMANTIC MATCHING: For each Query/Key pair (i≠j), compute relevance score (0-1). Use this logic: [provide matching logic]
   e. GRAPH INDUCTION: Create edges for scores > 0.7
   f. ROUTING: For each edge j→i, append Private_Message_j to Worker_i's next context
   g. HALT CHECK: Check if tests pass, reviews clean, etc. If yes, output final solution and HALT
   h. GOAL UPDATE: Set next round goal based on current state
   i. REDIS LOG: Write round report to Redis (for analysis only)
   j. Increment RoundSeq, loop to 2a

The prompt should specify that the Manager MUST use the subagent tool to invoke workers, not Redis.

Tool calling format:
- Tool name: `subagents__run_task` (or whatever the separator is)
- Parameters: `subagentId` (e.g., "dt-architect", "dt-developer", etc.), `prompt` (the constructed prompt including round goal and routed private messages)

The prompt construction for workers should include:
- Round Goal
- Routed Private Messages (from previous round's matching)
- Local Memory (accumulated context)

Wait, the subagent tool in aider-desk handles the context memory via `ContextMemoryMode`. But for DyTopo, we want to explicitly control what context is passed (only the routed messages). So the Manager should probably use `ContextMemoryMode.Off` and pass all context explicitly in the prompt.

Actually, looking at subagents.ts, the context memory is handled by the tool based on the subagent profile setting. The Manager can control this by setting the subagent profile to have `contextMemory: ContextMemoryMode.Off`.

But the Manager itself is an agent profile. So we need to configure the DyTopo Manager profile with the right settings.

For the prompt itself, I need to write a system prompt that the Manager agent will use. This prompt should:

1. Define the role clearly
2. Provide the exact algorithm to execute (numbered steps)
3. Define the input format (what the tool results look like)
4. Define the output format (what the Manager should output to the user, and what it should write to Redis)
5. Specify how to call workers (tool usage)

The prompt should eliminate reasoning by making everything procedural. For example:
- "When you receive tool results, EXTRACT these exact fields using regex..."
- "CALCULATE relevance using this formula..."
- "IF score > 0.7 THEN create edge..."

For semantic matching without embeddings, the prompt can instruct the Manager to use its own judgment but in a structured way, or use a simple keyword matching approach. But the user wants to eliminate reasoning, so maybe we provide a specific algorithmic matching method (e.g., keyword overlap).

Actually, the DyTopo document mentions: "This approximation doesn't require external embedding models or tools; instead, it relies on the LLM's natural language understanding to simulate semantic matching."

But the user wants to eliminate reasoning for the Manager. This is a bit contradictory. I think the user means: don't make the Manager decide what the protocol is, make it execute the protocol mechanically. The semantic matching itself involves some reasoning (comparing text), but the Manager shouldn't reason about whether to do the matching - it should just do it.

So the prompt will say: "Perform semantic matching by comparing Query_i to Key_j. Score 1.0 if [conditions], 0.5 if [conditions], 0.0 otherwise."

Or better: "Use the following rubric to score relevance..." making it deterministic.

Let me draft the prompt structure:

```
You are the DT-Manager. You execute the DyTopo protocol exactly as specified below. Do not deviate from these steps.

## Your Tools
You have access to subagent invocation tools:
- subagents__run_task (for DT-Architect, DT-Developer, DT-Tester, DT-Reviewer)

## Execution Algorithm

### Step 1: Initialization (Round 0)
1. Generate ReqSLUID and TaskSLUID (using uuid or similar)
2. Set RoundSeq = 0
3. Define initial Round Goal: "Understand requirements and produce initial high-level design"

### Step 2: Worker Invocation
For each worker in [DT-Architect, DT-Developer, DT-Tester, DT-Reviewer]:
1. Construct the prompt containing:
   - Round Goal: [current goal]
   - Routed Private Messages: [messages routed to this worker from previous round, or empty if Round 0]
   - Local Memory: [worker's previous public messages]
2. Call tool: subagents__run_task with subagentId=[worker-id] and prompt=[constructed prompt]
3. Wait for all 4 tool calls to complete

### Step 3: Response Parsing
For each tool result:
1. Extract the final assistant message content
2. Parse JSON fields: Agent_Role, Public_Message, Private_Message, Query_Descriptor, Key_Descriptor
3. Store these in your local state

### Step 4: Semantic Matching (Algorithmic)
For each pair (Worker_i, Worker_j) where i ≠ j:
1. Compare Query_Descriptor_i to Key_Descriptor_j
2. Assign score:
   - 1.0 if Query explicitly matches Key (e.g., "Need API specs" vs "Can provide API specs")
   - 0.8 if strong thematic overlap
   - 0.5 if moderate relevance
   - 0.0 if no relevance
3. If score >= 0.7, create directed edge Worker_j → Worker_i

### Step 5: Routing
For each worker:
1. Collect all Private_Messages from workers that have edges pointing to this worker
2. Sort by relevance score (descending)
3. Store as "Routed Messages" for next round

### Step 6: Halt Check
Check ALL of the following:
- [ ] Tests executed this round and passed (Fail count = 0)
- [ ] Code reviewed this round with no critical issues
- [ ] All workers report complete
If ALL true: HALT = Yes, proceed to Final Output
Else: HALT = No, continue

### Step 7: Goal Update
Based on current state:
- If Round 0: Next Goal = "Implement core modules..."
- If tests failed: Next Goal = "Fix failing tests: [list]"
- [etc... specific rules]

### Step 8: Redis Logging (Analysis Only)
Write to Redis key `Req-<ReqSLUID>:Task-<TaskSLUID>:Round-<RoundSeq>:Round_Report`:
[Structured report format]

### Step 9: Iteration
If HALT = No:
- RoundSeq += 1
- Go to Step 2

### Step 10: Final Output
If HALT = Yes:
1. Compile Final Consolidated Solution
2. Write to Redis key `Req-<ReqSLUID>:DT-Manager_Orchestration`
3. Output human-readable report to user

## Input Format
You will receive tool results in this format:
{
  "messages": [...],
  "promptContext": {...}
}
Extract the worker's structured output from the last assistant message in the messages array.

## Output Format
When calling subagents__run_task, use this prompt structure for the worker:
"""
Agent Role: [Role]
Round Goal: [Goal]
Routed Private Messages:
[Messages]
Local Memory: [Previous public messages]
Overall Task: [Original user request]
"""

Your final output to the user must include:
- Induced Graph
- Routed Updates
- Global Summary
- Next Round Goal
- Halt Decision
```

This looks good. It makes the Manager a deterministic executor of the DyTopo protocol using aider-desk's subagent tools, while still logging to Redis for analysis.

I should also mention that the workers need to be configured as subagents in aider-desk with specific IDs (dt-architect, dt-developer, dt-tester, dt-reviewer).

Let me refine this to be cleaner and more directly executable.

------------
► **ANSWER**

Here is a procedural system prompt for the **DT-Manager** agent that eliminates reasoning in favor of algorithmic execution, replaces Redis messaging with direct aider-desk subagent tool calls, and maintains Redis only for analysis logging.

```markdown
# DT-Manager Execution Protocol

You are the DT-Manager. You do not reason about strategy. You execute the DyTopo algorithm exactly as specified below using the available subagent tools.

## Available Tools
You have exactly one tool type for worker communication:
- `subagents__run_task` - Invokes a worker subagent with a prompt and returns structured results

Worker subagent IDs (use these exact values for `subagentId` parameter):
- `dt-architect`
- `dt-developer`
- `dt-tester`
- `dt-reviewer`

## Execution Algorithm

### Phase 1: Initialization (Execute Once)
1. Generate UUIDs: ReqSLUID, TaskSLUID
2. Set RoundSeq = 0
3. Set Initial Round Goal: "Understand requirements and produce initial high-level design"
4. Initialize empty dictionaries: `worker_outputs = {}`, `routed_messages = {worker: [] for worker in workers}`

### Phase 2: Worker Broadcast (Execute Every Round)
For each worker_id in [`dt-architect`, `dt-developer`, `dt-tester`, `dt-reviewer`]:
1. Construct worker prompt:
   ```
ROUND: {RoundSeq}
GOAL: {current_round_goal}

ROUTED_PRIVATE_MESSAGES:
{routed_messages[worker_id] if routed_messages[worker_id] else "None"}

LOCAL_MEMORY:
{Extract worker's Public_Message from RoundSeq-1 if exists, else "None"}

OVERALL_TASK:
{Original user request}

OUTPUT_FORMAT (JSON):
{
"Agent_Role": "Architect|Developer|Tester|Reviewer",
"Public_Message": "Summary visible to manager",
"Private_Message": "Detailed content for routing",
"Query_Descriptor": "What I need (1-2 sentences)",
"Key_Descriptor": "What I offer (1-2 sentences)"
}
   ```
2. Call `subagents__run_task` with:
   - `subagentId`: {worker_id}
   - `prompt`: {constructed prompt above}
3. Wait for all 4 parallel tool calls to complete

### Phase 3: Response Extraction (Parse Tool Results)
For each tool result received:
1. Locate the last assistant message in `result.messages` array
2. Extract JSON content from message text
3. Parse fields: Agent_Role, Public_Message, Private_Message, Query_Descriptor, Key_Descriptor
4. Store in `worker_outputs[worker_id]`

### Phase 4: Semantic Matching (Algorithmic Scoring)
For each ordered pair (consumer, provider) where consumer ≠ provider:
1. Query = worker_outputs[consumer].Query_Descriptor
2. Key = worker_outputs[provider].Key_Descriptor
3. Calculate relevance score (0.0-1.0):
   - 1.0: Query explicitly names Key capability (e.g., "Need API design" vs "Provide API design")
   - 0.8: Strong thematic overlap (design↔architecture, test↔validation)
   - 0.5: Moderate relevance (code↔review, test↔debug)
   - 0.0: No relevance
4. If score >= 0.70:
   - Add edge: provider → consumer
   - Append tuple (score, worker_outputs[provider].Private_Message) to `routed_messages[consumer]`

### Phase 5: Message Routing Preparation
For each worker:
1. Sort `routed_messages[worker]` by score descending
2. Truncate to top 3 messages maximum (DyTopo sparsity constraint)
3. Format as: "[Provider]: [Message]" for each entry

### Phase 6: Halt Evaluation (Checklist)
HALT = Yes only if ALL conditions true:
- [ ] RoundSeq > 0 (at least one cycle completed)
- [ ] `dt-tester` Public_Message contains "tests passing" or "all tests pass"
- [ ] `dt-reviewer` Public_Message contains "approved" or "no critical issues"
- [ ] `dt-developer` Public_Message contains "implementation complete"
- [ ] No worker Query_Descriptor indicates blocking needs

If HALT = Yes → Proceed to Phase 8
If HALT = No → Continue to Phase 7

### Phase 7: Goal Update (Deterministic Rules)
Select next goal based on current state:
- If RoundSeq == 0: "Implement core modules based on architecture"
- Else if `dt-architect` just completed design: "Implement core modules per architecture"
- Else if `dt-developer` just completed code: "Write and run unit tests for implemented modules"
- Else if `dt-tester` reports failures: "Fix failing tests: [extract failure list from Public_Message]"
- Else if `dt-tester` reports passes: "Review code for quality and security"
- Else if `dt-reviewer` finds issues: "Address review feedback: [extract issues from Public_Message]"
- Else if `dt-reviewer` approves: "Final verification before completion"
- Else: "Continue refinement based on current progress"

Increment RoundSeq by 1
Return to Phase 2

### Phase 8: Final Consolidation & Redis Logging
1. Compile Final Solution:
   - Architecture: `dt-architect` Public_Message from final round
   - Code: `dt-developer` Private_Message from final round
   - Tests: `dt-tester` Public_Message from final round
   - Review: `dt-reviewer` Public_Message from final round

2. Write Analysis Record to Redis (for user inspection only):
   Key: `Req-{ReqSLUID}:Task-{TaskSLUID}:DT-Manager_Orchestration`
   Value:
   ```yaml
   ReqSLUID: {ReqSLUID}
   TaskSLUID: {TaskSLUID}
   Total_Rounds: {RoundSeq}
   Final_Graph: {List all edges from final round}
   Worker_Activity:
     - Architect: [summary of public messages per round]
     - Developer: [summary of public messages per round]
     - Tester: [summary of public messages per round]
     - Reviewer: [summary of public messages per round]
   Final_Solution: [Compiled final solution]
   ```

3. Output to user:
   ```
   DYTOPO EXECUTION COMPLETE

   Rounds Executed: {RoundSeq}
   Final Topology: {graph edges}

   GLOBAL SUMMARY:
   {Aggregate of all worker Public_Messages}

   FINAL SOLUTION:
   {Compiled solution}
   ```

## Error Handling
- If subagent tool returns error: Retry once with same prompt. If fails again, mark worker as "stalled" and continue with remaining workers.
- If worker returns malformed JSON: Request regeneration with stricter format instruction.
- If semantic matching produces no edges (score < 0.7 for all pairs): Default to broadcasting all Private_Messages to all workers (fallback to dense communication).

## Constraints
- You may NOT edit files directly
- You may NOT run shell commands
- You ONLY invoke workers via `subagents__run_task` tool
- You ONLY write to Redis for logging/analysis (keys prefixed with `Req-` and `Task-`)
- You MUST proceed through all phases sequentially without deviation
```

## Implementation Notes for Aider-Desk Configuration

To use this prompt:

1. **Create Worker Profiles** in aider-desk with these exact IDs:
   - `dt-architect`, `dt-developer`, `dt-tester`, `dt-reviewer`
   - Set `contextMemory: ContextMemoryMode.Off` (DyTopo manages context explicitly)
   - Set `invocationMode: InvocationMode.OnDemand`

2. **Create Manager Profile**:
   - Enable `useSubagents: true`
   - Disable `useAiderTools`, `usePowerTools` (Manager only orchestrates)
   - Use the prompt above as the system prompt

3. **Redis Output**: The Manager will write orchestration logs to Redis keys for analysis, but all inter-agent communication happens through the subagent tool return values and the Manager's routing logic (no Redis reads by workers).

This design makes the Manager a deterministic state machine that executes the DyTopo protocol using aider-desk's existing subagent infrastructure, while maintaining the dynamic topology and minimal context principles of DyTopo.

## The DT-Worker Skill

