# AI Engineering Operating Model

AI-assisted delivery is a system change, not a license rollout. The unit of improvement is the full path from a user problem to verified production behavior.

## Five Delivery Loops

1. **Frame:** define the user outcome, baseline, constraints, and acceptance evidence.
2. **Build:** give people and agents bounded context, interfaces, tools, and permissions.
3. **Verify:** combine deterministic tests, task evals, review, and adversarial checks.
4. **Operate:** observe quality, cost, latency, incidents, and changing model behavior.
5. **Learn:** feed failures and successful patterns back into evals, standards, and training.

## Maturity Stages

| Stage | Characteristic | Exit evidence |
|---|---|---|
| Exploratory | Individual experimentation | Bounded use cases and explicit baselines |
| Assisted | Repeatable use in isolated tasks | Team workflow and quality evidence |
| Repeatable | Shared practices and release checks | Stable evals, interfaces, and ownership |
| Measured | Portfolio telemetry and risk-tiered controls | Demonstrated outcome and control effectiveness |
| Adaptive | Continuous learning across tools and teams | Standards change from operational evidence |

## Adoption Principles

- Start with workflow bottlenecks, not model features.
- Treat generated code and decisions as untrusted inputs until verified.
- Keep changes small enough for meaningful review and rollback.
- Measure accepted work and user outcomes, not generated volume.
- Match autonomy to evidence, reversibility, and impact.
- Preserve human accountability even when agents execute the work.
