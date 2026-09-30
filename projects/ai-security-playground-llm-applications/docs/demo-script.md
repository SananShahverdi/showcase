# Demo script

1. Open AgentShield Lab. With hub demo data an assessment has already run: the metric row shows 6/6 scenarios, exposures, the mitigation rate, and pending approvals, and the trace panel shows the latest vulnerable and hardened runs for **Instruction override**.
2. Click **Compare both modes** and walk through the hardened decision trace (control ID, effect, reason).
3. Edit the payload to a harmless question and compare again: the vulnerable run is no longer counted as a successful attack.
4. Open **Cross-role ticket creation**, switch the role to **Security admin**, and compare: the hardened agent allows the request by role but holds it for one-time approval.
5. Click **Run full assessment** and open the **Markdown** export.
6. Close with the boundary: every tool is a synthetic fixture and the rules cover the catalog's patterns, not every possible attack.
