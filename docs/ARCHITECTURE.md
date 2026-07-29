# ProofFund Architecture

ProofFund is a milestone escrow and adjudication protocol for projects whose
deliverables cannot be verified by deterministic code alone.

## Responsibility boundary

- The frontend owns wallet connection, forms, transaction progress, filtering,
  formatting, and non-authoritative convenience views.
- The ProofFund Intelligent Contract owns projects, contributions, milestone
  criteria, evidence, validator-agreed judgments, disputes, claimable balances,
  payouts, and reputation.
- External HTTPS sources own the raw evidence. Validators independently render
  the same sources and compare the material verdict before state changes.

## Core flow

1. A creator registers a project and measurable milestones.
2. Backers send real StudioNet GEN into contract escrow.
3. Once fully funded, the creator submits a public evidence URL.
4. Validators independently inspect the evidence and compare verdict and score.
5. Approved milestone funds become claimable by the creator.
6. A third party may post a bond and provide counter-evidence.
7. Validators reassess both sources. A successful challenge restores the
   milestone to work-in-progress and returns the bond; a failed challenge
   awards the bond to the creator.
8. Claims are transferred from contract escrow to the recipient address.

## Consensus rule

Milestone evaluation requires exact agreement on the verdict and a score
difference of no more than 15 points. Dispute resolution requires exact
agreement on both resolution and final verdict. Explanatory text is retained
from the leader but never determines settlement by itself.

## Safety properties

- Every state transition validates caller, lifecycle state, and ownership.
- Project funding cannot exceed its goal.
- Milestone budgets cannot exceed the project goal.
- A milestone can release funds only once.
- Nondeterministic code reads copied values and cannot mutate storage.
- All monetary values use `u256` wei units.
- The GenVM runner is pinned to a concrete production hash.
