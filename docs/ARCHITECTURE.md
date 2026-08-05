# ProofFund Architecture

ProofFund is a milestone escrow and adjudication protocol for projects whose
deliverables cannot be verified by deterministic code alone.

## Responsibility boundary

- The frontend owns wallet connection, forms, transaction progress, filtering,
  formatting, and non-authoritative convenience views.
- The ProofFund Intelligent Contract owns projects, contributions, milestone
  criteria, evidence, validator-agreed judgments, dispute windows, direct
  payouts, proportional refunds, and reputation.
- External HTTPS sources own the raw evidence. Validators independently render
  the same sources and compare the material verdict before state changes.

## Core flow

1. A creator registers a project and measurable milestones.
2. Backers send real StudioNet GEN into contract escrow.
3. Once fully funded, the creator submits a public evidence URL.
4. Validators independently inspect the evidence and compare verdict and score.
5. Approval enters `APPROVED_PENDING`; escrow remains locked for seven days.
6. A contributing backer may post a bond and counter-evidence inside that window.
7. If no dispute opens, permissionless release atomically marks the milestone
   released, updates accounting and reputation, and transfers GEN to the creator.
8. If disputed, validators reassess both sources. `UPHOLD` must retain the
   snapshotted verdict; `OVERTURN` must change it. Verdict, release state,
   accounting, bond, and milestone transfers settle in one transaction.
9. After a failed project deadline, terminal refund mode freezes all competing
   state transitions and reserves unreleased escrow for proportional backer claims.

## Consensus rule

Milestone evaluation requires exact agreement on the verdict and a score
difference of no more than 15 points. Dispute resolution requires exact
agreement on both resolution and final verdict. Explanatory text is retained
from the leader but never determines settlement by itself.

## Safety properties

- Every state transition validates caller, lifecycle state, and ownership.
- Project funding cannot exceed its goal.
- Milestone budgets cannot exceed the project goal.
- Full funding does not activate a project until milestone coverage equals the goal.
- A milestone can release funds only once.
- Approved funds cannot release before the dispute deadline.
- A released milestone cannot be disputed or reversed.
- Refund state and milestone release are mutually exclusive.
- Aggregate refunds cannot exceed the frozen project refund pool.
- Nondeterministic code reads copied values and cannot mutate storage.
- All monetary values use `u256` wei units.
- The GenVM runner is pinned to a concrete production hash.
