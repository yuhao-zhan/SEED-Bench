"""
Absolute-Zero-Reasoner (AZR) for 2D_exploration.

AZR solver vs agent solver:
- The AZR solver is the code-generation model used by this method: it takes a task prompt
  and outputs agent code (build_agent, etc.). It is the same concept as the "agent solver"
  for this method—the LLM that plays the role of the agent designer.
- The evaluation pipeline calls it "solver" (SolverInterface or AbsoluteZeroSolver); when
  method is absolute_zero_iter, we use AbsoluteZeroSolver (get_azr_solver) so the same
  model (base or AZR-trained) is used to generate code at each iteration.

Our 2D paradigm (this reimplementation):
1. (Optional) Training: run training/train.py to improve the model with REINFORCE++/PPO on
   2D tasks. We use a task proposer (or fixed pool) to get prompts; reward comes from
   CodeVerifier. This produces checkpoints.
2. Evaluation: use that model (or a base model) as the AZR solver and run iteration-based
   solving: at each iteration, generate code -> verify -> if not success, refine (next
   iteration with feedback) until success or max_iterations. So the trained model is the
   agent solver used during evaluation in iterations.

Official repo (paper + README): the model proposes tasks (PROPOSE) and solves them (SOLVE);
task proposition is central—see OFFICIAL_WORKFLOW.md. For alignment checklist and
intentional differences, see ALIGNMENT.md.

Evaluation: absolute_zero_method.py (AbsoluteZeroSolver, get_azr_solver) — method
  absolute_zero_iter only.
Training:   training/train.py (AZR-style PPO loop for 2D).
"""
