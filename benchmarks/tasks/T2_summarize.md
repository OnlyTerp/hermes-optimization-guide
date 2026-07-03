Summarize the following research document into a one-page brief (max 400
words) with sections: Key Findings, Methodology, Limitations, Action Items.

NOTE TO RUNNERS: the committed prompt below is a short stand-in so the repo
stays small. For the real T2 run, replace everything below the line with a
~200K-token document of your choice (we used a concatenation of arXiv
cs.CL papers; any long corpus works — what matters is that every model gets
the same one). Models whose context window is below `skip_if_context_lt:
300000` in matrix.yaml are skipped for this task by run.sh.

---

Title: Retrieval-Augmented Agents in Production: A 12-Month Field Study

Abstract: We deployed retrieval-augmented LLM agents across 40 small-team
production environments for 12 months, measuring task completion, cost,
and failure modes. Agents with graph-based retrieval completed 23% more
multi-step tasks than vector-only baselines but showed 2.1x higher tail
latency during index merges. The dominant failure mode was not retrieval
quality but context contamination: stale or wrong memories injected into
unrelated sessions accounted for 38% of user-reported errors. Monthly
memory pruning reduced this class of error by 61%. Cost per completed task
fell 74% when auxiliary calls (compression, extraction, classification)
were routed to small models, with no measurable quality loss on the rubric.
We conclude that operational hygiene — pruning, routing, and isolation —
dominates model choice once a capability floor is met.
