# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

import json
from dataclasses import dataclass
from datetime import datetime, timezone

from genlayer import *


ERROR_EXPECTED = "[EXPECTED]"
ERROR_EXTERNAL = "[EXTERNAL]"
ERROR_LLM = "[LLM_ERROR]"
DISPUTE_WINDOW_SECONDS = 7 * 86_400


@allow_storage
@dataclass
class Project:
    id: str
    creator: Address
    title: str
    category: str
    summary: str
    description: str
    website_url: str
    image_url: str
    funding_goal: u256
    funded_amount: u256
    released_amount: u256
    milestone_budget: u256
    milestone_count: u32
    backer_count: u32
    status: str
    created_at: u64
    deadline: u64
    tranche_budget: u256
    tranche_count: u32
    proposal_count: u32
    refund_pool: u256
    refunded_amount: u256
    refund_claim_count: u32
    refund_opened_at: u64


@allow_storage
@dataclass
class Milestone:
    id: str
    project_id: str
    index: u32
    title: str
    criteria: str
    amount: u256
    due_at: u64
    status: str
    evidence_url: str
    evidence_note: str
    submitted_at: u64
    verdict: str
    score: u32
    analysis: str
    findings_json: str
    evaluated_at: u64
    released: bool
    dispute_count: u32
    approved_at: u64
    appeal_deadline: u64
    active_dispute_id: str


@allow_storage
@dataclass
class Dispute:
    id: str
    project_id: str
    milestone_id: str
    challenger: Address
    reason: str
    counter_evidence_url: str
    bond: u256
    status: str
    resolution: str
    analysis: str
    created_at: u64
    resolved_at: u64
    original_verdict: str


@allow_storage
@dataclass
class FundingTranche:
    id: str
    project_id: str
    index: u32
    title: str
    goal: u256
    funded_amount: u256
    deadline: u64
    status: str
    backer_count: u32


@allow_storage
@dataclass
class Proposal:
    id: str
    project_id: str
    proposer: Address
    title: str
    description: str
    action: str
    action_value: u256
    yes_votes: u256
    no_votes: u256
    snapshot_weight: u256
    quorum: u256
    voting_ends_at: u64
    status: str
    created_at: u64
    finalized_at: u64


@allow_storage
@dataclass
class Reputation:
    projects_created: u32
    projects_backed: u32
    milestones_approved: u32
    disputes_won: u32
    disputes_lost: u32
    total_funded: u256
    total_earned: u256
    proposals_created: u32
    votes_cast: u32


@gl.evm.contract_interface
class _Recipient:
    class View:
        pass

    class Write:
        pass


class ProofFund(gl.Contract):
    owner: Address
    project_ids: DynArray[str]
    projects: TreeMap[str, Project]
    milestone_ids: DynArray[str]
    milestones: TreeMap[str, Milestone]
    dispute_ids: DynArray[str]
    disputes: TreeMap[str, Dispute]
    tranche_ids: DynArray[str]
    tranches: TreeMap[str, FundingTranche]
    proposal_ids: DynArray[str]
    proposals: TreeMap[str, Proposal]
    proposal_votes: TreeMap[str, str]
    contributions: TreeMap[str, u256]
    backed_projects: TreeMap[str, bool]
    backed_tranches: TreeMap[str, bool]
    refund_claimed: TreeMap[str, bool]
    reputation: TreeMap[Address, Reputation]
    total_funded: u256
    total_released: u256
    total_refunded: u256
    total_disputes: u32
    total_proposals: u32

    def __init__(self):
        self.owner = gl.message.sender_address
        self.total_funded = u256(0)
        self.total_released = u256(0)
        self.total_refunded = u256(0)
        self.total_disputes = u32(0)
        self.total_proposals = u32(0)

    def _now(self) -> u64:
        return u64(int(datetime.now(timezone.utc).timestamp()))

    def _require_project(self, project_id: str) -> Project:
        if project_id not in self.projects:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Project not found")
        return self.projects[project_id]

    def _require_milestone(self, project_id: str, milestone_id: str) -> Milestone:
        if milestone_id not in self.milestones:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Milestone not found")
        milestone = self.milestones[milestone_id]
        if milestone.project_id != project_id:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Milestone does not belong to project")
        return milestone

    def _require_tranche(self, project_id: str, tranche_id: str) -> FundingTranche:
        if tranche_id not in self.tranches:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Funding tranche not found")
        tranche = self.tranches[tranche_id]
        if tranche.project_id != project_id:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Tranche does not belong to project")
        return tranche

    def _require_proposal(self, proposal_id: str) -> Proposal:
        if proposal_id not in self.proposals:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Proposal not found")
        return self.proposals[proposal_id]

    def _profile(self, account: Address) -> Reputation:
        return self.reputation.get(
            account,
            Reputation(
                projects_created=u32(0),
                projects_backed=u32(0),
                milestones_approved=u32(0),
                disputes_won=u32(0),
                disputes_lost=u32(0),
                total_funded=u256(0),
                total_earned=u256(0),
                proposals_created=u32(0),
                votes_cast=u32(0),
            ),
        )

    def _settle_approved_milestone(
        self, project: Project, milestone: Milestone
    ) -> None:
        if project.status == "REFUNDING":
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Project escrow is reserved for refunds")
        if milestone.released:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Milestone was already released")
        if project.released_amount + milestone.amount > project.funded_amount:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Insufficient funded escrow")

        milestone.status = "APPROVED"
        milestone.verdict = "APPROVED"
        milestone.released = True
        milestone.active_dispute_id = ""
        project.released_amount += milestone.amount
        self.total_released += milestone.amount

        profile = self._profile(project.creator)
        profile.milestones_approved += u32(1)
        profile.total_earned += milestone.amount
        self.reputation[project.creator] = profile
        if project.released_amount == project.milestone_budget:
            project.status = "COMPLETED"

        _Recipient(project.creator).emit_transfer(value=milestone.amount)

    def _validate_text(self, value: str, field: str, minimum: int, maximum: int) -> None:
        clean = value.strip()
        if len(clean) < minimum or len(clean) > maximum:
            raise gl.vm.UserError(
                f"{ERROR_EXPECTED} {field} must contain {minimum}-{maximum} characters"
            )

    def _create_tranche(
        self,
        project: Project,
        title: str,
        goal: u256,
        deadline: u64,
    ) -> str:
        self._validate_text(title, "Tranche title", 4, 100)
        if goal == u256(0):
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Tranche goal must be positive")
        if project.tranche_budget + goal > project.funding_goal:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Tranche budget exceeds funding goal")
        if deadline <= self._now() or deadline > project.deadline:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Invalid tranche deadline")

        index = project.tranche_count + u32(1)
        tranche_id = f"{project.id}-T{int(index)}"
        self.tranches[tranche_id] = FundingTranche(
            id=tranche_id,
            project_id=project.id,
            index=index,
            title=title.strip(),
            goal=goal,
            funded_amount=u256(0),
            deadline=deadline,
            status="OPEN",
            backer_count=u32(0),
        )
        self.tranche_ids.append(tranche_id)
        project.tranche_count = index
        project.tranche_budget += goal
        return tranche_id

    def _record_funding(
        self,
        project: Project,
        tranche: FundingTranche,
        amount: u256,
    ) -> None:
        if amount == u256(0):
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Contribution must be positive")
        if amount > tranche.goal - tranche.funded_amount:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Contribution exceeds tranche remainder")
        if amount > project.funding_goal - project.funded_amount:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Contribution exceeds project remainder")

        sender = gl.message.sender_address
        contribution_key = f"{project.id}:{sender.as_hex}"
        self.contributions[contribution_key] = (
            self.contributions.get(contribution_key, u256(0)) + amount
        )
        project.funded_amount += amount
        tranche.funded_amount += amount
        self.total_funded += amount

        project_backed_key = f"{sender.as_hex}:{project.id}"
        profile = self._profile(sender)
        if not self.backed_projects.get(project_backed_key, False):
            self.backed_projects[project_backed_key] = True
            project.backer_count += u32(1)
            profile.projects_backed += u32(1)

        tranche_backed_key = f"{sender.as_hex}:{tranche.id}"
        if not self.backed_tranches.get(tranche_backed_key, False):
            self.backed_tranches[tranche_backed_key] = True
            tranche.backer_count += u32(1)

        profile.total_funded += amount
        self.reputation[sender] = profile
        if tranche.funded_amount == tranche.goal:
            tranche.status = "FUNDED"
        if (
            project.funded_amount == project.funding_goal
            and project.milestone_budget == project.funding_goal
        ):
            project.status = "ACTIVE"
        self.tranches[tranche.id] = tranche
        self.projects[project.id] = project

    def _run_milestone_assessment(
        self,
        project_title: str,
        milestone_title: str,
        criteria: str,
        evidence_url: str,
        evidence_note: str,
    ) -> dict:
        def assess() -> dict:
            try:
                page = gl.nondet.web.render(
                    evidence_url, mode="text", wait_after_loaded="2s"
                )
            except Exception:
                return {
                    "verdict": "REJECTED",
                    "score": 0,
                    "summary": (
                        "Validators could not retrieve the submitted evidence page. "
                        "Submit a publicly accessible HTTPS source and try again."
                    ),
                    "findings": [
                        "The evidence URL was unreachable from the validator network.",
                        "No acceptance criterion could be independently verified.",
                    ],
                }

            prompt = f"""Audit this grant milestone using only public evidence.
Project:{project_title}\nMilestone:{milestone_title}
Criteria:<criteria>{criteria}</criteria>
Creator note:<note>{evidence_note}</note>
Evidence:<evidence>{page[:18000]}</evidence>
Return JSON: {{"verdict":"APPROVED|NEEDS_WORK|REJECTED","score":0-100,
"summary":"under 500 chars","findings":["2-6 factual findings"]}}.
APPROVED requires direct proof of every material criterion. NEEDS_WORK means
partial proof with material gaps. REJECTED means core criteria fail or the
source is irrelevant, inaccessible, or deceptive. Never reward unsupported claims."""
            result = gl.nondet.exec_prompt(prompt, response_format="json")
            if not isinstance(result, dict):
                raise gl.vm.UserError(f"{ERROR_LLM} Invalid assessment format")

            verdict = str(result.get("verdict", "")).strip().upper()
            if verdict not in ("APPROVED", "NEEDS_WORK", "REJECTED"):
                raise gl.vm.UserError(f"{ERROR_LLM} Invalid verdict")

            try:
                score = max(0, min(100, int(result.get("score", 0))))
            except Exception:
                raise gl.vm.UserError(f"{ERROR_LLM} Invalid score")

            findings = result.get("findings", [])
            if not isinstance(findings, list):
                findings = []
            return {
                "verdict": verdict,
                "score": score,
                "summary": str(result.get("summary", ""))[:500],
                "findings": [str(item)[:240] for item in findings[:6]],
            }

        def validate(leader_result: gl.vm.Result) -> bool:
            if not isinstance(leader_result, gl.vm.Return):
                return False
            validator_result = assess()
            leader = leader_result.calldata
            if leader["verdict"] != validator_result["verdict"]:
                return False
            leader_score = int(leader["score"])
            validator_score = int(validator_result["score"])
            return abs(leader_score - validator_score) <= 15

        return gl.vm.run_nondet_unsafe(assess, validate)

    def _run_dispute_assessment(
        self,
        project_title: str,
        milestone_title: str,
        criteria: str,
        evidence_url: str,
        original_verdict: str,
        dispute_reason: str,
        counter_evidence_url: str,
    ) -> dict:
        def assess() -> dict:
            try:
                original_page = gl.nondet.web.render(
                    evidence_url, mode="text", wait_after_loaded="2s"
                )
                counter_page = gl.nondet.web.render(
                    counter_evidence_url, mode="text", wait_after_loaded="2s"
                )
            except Exception:
                raise gl.vm.UserError(f"{ERROR_EXTERNAL} Dispute evidence unavailable")

            prompt = f"""Reassess this grant appeal from first principles.
Project:{project_title}\nMilestone:{milestone_title}
Criteria:<criteria>{criteria}</criteria>\nOriginal verdict:{original_verdict}
Original:<original>{original_page[:12000]}</original>
Challenge:<reason>{dispute_reason}</reason>
Counter-evidence:<counter>{counter_page[:12000]}</counter>
Return JSON: {{"resolution":"UPHOLD|OVERTURN",
"final_verdict":"APPROVED|NEEDS_WORK|REJECTED","summary":"under 600 chars"}}.
UPHOLD must retain the original verdict. OVERTURN requires a demonstrated
material error and must change it."""
            result = gl.nondet.exec_prompt(prompt, response_format="json")
            if not isinstance(result, dict):
                raise gl.vm.UserError(f"{ERROR_LLM} Invalid dispute format")
            resolution = str(result.get("resolution", "")).strip().upper()
            final_verdict = str(result.get("final_verdict", "")).strip().upper()
            if resolution not in ("UPHOLD", "OVERTURN"):
                raise gl.vm.UserError(f"{ERROR_LLM} Invalid dispute resolution")
            if final_verdict not in ("APPROVED", "NEEDS_WORK", "REJECTED"):
                raise gl.vm.UserError(f"{ERROR_LLM} Invalid final verdict")
            if resolution == "UPHOLD" and final_verdict != original_verdict:
                raise gl.vm.UserError(f"{ERROR_LLM} Inconsistent dispute result")
            if resolution == "OVERTURN" and final_verdict == original_verdict:
                raise gl.vm.UserError(f"{ERROR_LLM} Inconsistent dispute result")
            return {
                "resolution": resolution,
                "final_verdict": final_verdict,
                "summary": str(result.get("summary", ""))[:600],
            }

        def validate(leader_result: gl.vm.Result) -> bool:
            if not isinstance(leader_result, gl.vm.Return):
                return False
            validator_result = assess()
            leader = leader_result.calldata
            return (
                leader["resolution"] == validator_result["resolution"]
                and leader["final_verdict"] == validator_result["final_verdict"]
            )

        return gl.vm.run_nondet_unsafe(assess, validate)

    @gl.public.write
    def create_project(
        self,
        title: str,
        category: str,
        summary: str,
        description: str,
        website_url: str,
        image_url: str,
        funding_goal: u256,
        deadline: u64,
        initial_tranche_title: str,
        initial_tranche_goal: u256,
        initial_tranche_deadline: u64,
    ) -> str:
        self._validate_text(title, "Title", 4, 80)
        self._validate_text(category, "Category", 2, 32)
        self._validate_text(summary, "Summary", 20, 180)
        self._validate_text(description, "Description", 80, 3000)
        if not website_url.startswith("https://"):
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Website must use HTTPS")
        if image_url != "" and not image_url.startswith("https://"):
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Image URL must use HTTPS")
        if funding_goal == u256(0):
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Funding goal must be positive")
        if deadline <= self._now():
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Deadline must be in the future")

        project_id = f"PF-{len(self.project_ids) + 1:04d}"
        sender = gl.message.sender_address
        project = Project(
            id=project_id,
            creator=sender,
            title=title.strip(),
            category=category.strip(),
            summary=summary.strip(),
            description=description.strip(),
            website_url=website_url.strip(),
            image_url=image_url.strip(),
            funding_goal=funding_goal,
            funded_amount=u256(0),
            released_amount=u256(0),
            milestone_budget=u256(0),
            milestone_count=u32(0),
            backer_count=u32(0),
            status="DRAFT",
            created_at=self._now(),
            deadline=deadline,
            tranche_budget=u256(0),
            tranche_count=u32(0),
            proposal_count=u32(0),
            refund_pool=u256(0),
            refunded_amount=u256(0),
            refund_claim_count=u32(0),
            refund_opened_at=u64(0),
        )
        self._create_tranche(
            project,
            initial_tranche_title,
            initial_tranche_goal,
            initial_tranche_deadline,
        )
        project.status = "FUNDING"
        self.projects[project_id] = project
        self.project_ids.append(project_id)

        profile = self._profile(sender)
        profile.projects_created += u32(1)
        self.reputation[sender] = profile
        return project_id

    @gl.public.write
    def add_funding_tranche(
        self,
        project_id: str,
        title: str,
        goal: u256,
        deadline: u64,
    ) -> str:
        project = self._require_project(project_id)
        if gl.message.sender_address != project.creator:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Only the creator can add tranches")
        if project.status not in ("FUNDING", "PAUSED"):
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Funding tranches are locked")
        tranche_id = self._create_tranche(project, title, goal, deadline)
        self.projects[project_id] = project
        return tranche_id

    @gl.public.write
    def add_milestone(
        self,
        project_id: str,
        title: str,
        criteria: str,
        amount: u256,
        due_at: u64,
    ) -> str:
        project = self._require_project(project_id)
        if gl.message.sender_address != project.creator:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Only the creator can add milestones")
        if project.status not in ("DRAFT", "FUNDING"):
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Milestones are locked")
        self._validate_text(title, "Milestone title", 4, 100)
        self._validate_text(criteria, "Acceptance criteria", 30, 2000)
        if amount == u256(0):
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Milestone amount must be positive")
        if project.milestone_budget + amount > project.funding_goal:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Milestone budget exceeds funding goal")
        if due_at <= self._now() or due_at > project.deadline:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Invalid milestone due date")

        index = project.milestone_count + u32(1)
        milestone_id = f"{project_id}-M{int(index)}"
        self.milestones[milestone_id] = Milestone(
            id=milestone_id,
            project_id=project_id,
            index=index,
            title=title.strip(),
            criteria=criteria.strip(),
            amount=amount,
            due_at=due_at,
            status="PENDING",
            evidence_url="",
            evidence_note="",
            submitted_at=u64(0),
            verdict="",
            score=u32(0),
            analysis="",
            findings_json="[]",
            evaluated_at=u64(0),
            released=False,
            dispute_count=u32(0),
            approved_at=u64(0),
            appeal_deadline=u64(0),
            active_dispute_id="",
        )
        self.milestone_ids.append(milestone_id)
        project.milestone_count = index
        project.milestone_budget += amount
        if (
            project.funded_amount == project.funding_goal
            and project.milestone_budget == project.funding_goal
        ):
            project.status = "ACTIVE"
        else:
            project.status = "FUNDING"
        self.projects[project_id] = project
        return milestone_id

    @gl.public.write.payable
    def fund_tranche(self, project_id: str, tranche_id: str) -> None:
        project = self._require_project(project_id)
        tranche = self._require_tranche(project_id, tranche_id)
        if project.status != "FUNDING":
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Project is not accepting funds")
        if self._now() > project.deadline:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Funding deadline has passed")
        if self._now() > tranche.deadline:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Tranche deadline has passed")
        if tranche.status != "OPEN":
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Tranche is not accepting funds")
        self._record_funding(project, tranche, gl.message.value)

    @gl.public.write
    def create_proposal(
        self,
        project_id: str,
        title: str,
        description: str,
        action: str,
        action_value: u256,
        voting_ends_at: u64,
    ) -> str:
        project = self._require_project(project_id)
        if project.status in ("REFUNDING", "COMPLETED"):
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Governance is closed for this project")
        sender = gl.message.sender_address
        contribution = self.contributions.get(
            f"{project_id}:{sender.as_hex}", u256(0)
        )
        if sender != project.creator and contribution == u256(0):
            raise gl.vm.UserError(
                f"{ERROR_EXPECTED} Only the creator or project backers can propose"
            )
        if project.funded_amount == u256(0):
            raise gl.vm.UserError(
                f"{ERROR_EXPECTED} Governance activates after the first contribution"
            )
        self._validate_text(title, "Proposal title", 4, 100)
        self._validate_text(description, "Proposal description", 30, 2000)
        normalized_action = action.strip().upper()
        if normalized_action not in (
            "SIGNAL",
            "EXTEND_DEADLINE",
            "PAUSE_FUNDING",
            "REOPEN_FUNDING",
        ):
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Unsupported governance action")
        now = self._now()
        if voting_ends_at <= now + u64(60):
            raise gl.vm.UserError(
                f"{ERROR_EXPECTED} Voting period must remain open for at least 60 seconds"
            )
        if voting_ends_at > now + u64(30 * 86_400):
            raise gl.vm.UserError(
                f"{ERROR_EXPECTED} Voting period cannot exceed 30 days"
            )
        if normalized_action == "EXTEND_DEADLINE":
            if action_value <= u256(int(project.deadline)):
                raise gl.vm.UserError(
                    f"{ERROR_EXPECTED} New deadline must extend the current deadline"
                )
            if action_value > u256(int(project.deadline) + 5 * 365 * 86_400):
                raise gl.vm.UserError(
                    f"{ERROR_EXPECTED} New deadline cannot exceed five years"
                )
        elif action_value != u256(0):
            raise gl.vm.UserError(
                f"{ERROR_EXPECTED} This proposal action does not accept a value"
            )

        snapshot = project.funded_amount
        quorum = snapshot // u256(5)
        if quorum == u256(0):
            quorum = u256(1)
        index = project.proposal_count + u32(1)
        proposal_id = f"{project_id}-G{int(index)}"
        self.proposals[proposal_id] = Proposal(
            id=proposal_id,
            project_id=project_id,
            proposer=sender,
            title=title.strip(),
            description=description.strip(),
            action=normalized_action,
            action_value=action_value,
            yes_votes=u256(0),
            no_votes=u256(0),
            snapshot_weight=snapshot,
            quorum=quorum,
            voting_ends_at=voting_ends_at,
            status="OPEN",
            created_at=now,
            finalized_at=u64(0),
        )
        self.proposal_ids.append(proposal_id)
        project.proposal_count = index
        self.projects[project_id] = project
        self.total_proposals += u32(1)
        profile = self._profile(sender)
        profile.proposals_created += u32(1)
        self.reputation[sender] = profile
        return proposal_id

    @gl.public.write
    def vote_proposal(self, proposal_id: str, support: bool) -> None:
        proposal = self._require_proposal(proposal_id)
        project = self._require_project(proposal.project_id)
        if project.status == "REFUNDING":
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Governance is frozen during refunds")
        if proposal.status != "OPEN":
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Proposal is closed")
        if self._now() >= proposal.voting_ends_at:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Voting period has ended")

        sender = gl.message.sender_address
        vote_key = f"{proposal_id}:{sender.as_hex}"
        if self.proposal_votes.get(vote_key, "") != "":
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Address already voted")
        weight = self.contributions.get(
            f"{proposal.project_id}:{sender.as_hex}", u256(0)
        )
        if weight == u256(0):
            raise gl.vm.UserError(
                f"{ERROR_EXPECTED} Voting requires a project contribution"
            )

        if support:
            proposal.yes_votes += weight
            self.proposal_votes[vote_key] = "YES"
        else:
            proposal.no_votes += weight
            self.proposal_votes[vote_key] = "NO"
        self.proposals[proposal_id] = proposal
        profile = self._profile(sender)
        profile.votes_cast += u32(1)
        self.reputation[sender] = profile

    @gl.public.write
    def finalize_proposal(self, proposal_id: str) -> None:
        proposal = self._require_proposal(proposal_id)
        if proposal.status != "OPEN":
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Proposal already finalized")
        if self._now() < proposal.voting_ends_at:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Voting period is still open")
        project = self._require_project(proposal.project_id)
        if project.status == "REFUNDING":
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Governance is frozen during refunds")

        total_votes = proposal.yes_votes + proposal.no_votes
        passed = total_votes >= proposal.quorum and proposal.yes_votes > proposal.no_votes
        proposal.status = "PASSED" if passed else "REJECTED"
        proposal.finalized_at = self._now()

        if passed:
            if proposal.action == "EXTEND_DEADLINE":
                project.deadline = u64(int(proposal.action_value))
            elif proposal.action == "PAUSE_FUNDING" and project.status == "FUNDING":
                project.status = "PAUSED"
            elif proposal.action == "REOPEN_FUNDING" and project.status == "PAUSED":
                project.status = "FUNDING"
            self.projects[project.id] = project
        self.proposals[proposal_id] = proposal

    @gl.public.write
    def submit_evidence(
        self,
        project_id: str,
        milestone_id: str,
        evidence_url: str,
        evidence_note: str,
    ) -> None:
        project = self._require_project(project_id)
        milestone = self._require_milestone(project_id, milestone_id)
        if gl.message.sender_address != project.creator:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Only the creator can submit evidence")
        if project.status != "ACTIVE":
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Project must be fully funded")
        if milestone.status not in ("PENDING", "SUBMITTED", "NEEDS_WORK", "REJECTED"):
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Milestone cannot accept evidence")
        if not evidence_url.startswith("https://"):
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Evidence URL must use HTTPS")
        self._validate_text(evidence_note, "Evidence note", 20, 1200)

        milestone.evidence_url = evidence_url.strip()
        milestone.evidence_note = evidence_note.strip()
        milestone.submitted_at = self._now()
        milestone.status = "SUBMITTED"
        milestone.verdict = ""
        milestone.analysis = ""
        milestone.findings_json = "[]"
        self.milestones[milestone_id] = milestone

    @gl.public.write
    def evaluate_milestone(self, project_id: str, milestone_id: str) -> None:
        project = self._require_project(project_id)
        milestone = self._require_milestone(project_id, milestone_id)
        if project.status != "ACTIVE":
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Project is not active")
        if milestone.status != "SUBMITTED":
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Milestone is not awaiting evaluation")

        result = self._run_milestone_assessment(
            str(project.title),
            str(milestone.title),
            str(milestone.criteria),
            str(milestone.evidence_url),
            str(milestone.evidence_note),
        )
        verdict = str(result["verdict"])
        milestone.verdict = verdict
        milestone.status = verdict
        milestone.score = u32(int(result["score"]))
        milestone.analysis = str(result["summary"])
        milestone.findings_json = json.dumps(result["findings"])
        milestone.evaluated_at = self._now()
        milestone.appeal_deadline = u64(
            int(milestone.evaluated_at) + DISPUTE_WINDOW_SECONDS
        )
        milestone.active_dispute_id = ""
        if verdict == "APPROVED":
            milestone.status = "APPROVED_PENDING"
            milestone.approved_at = milestone.evaluated_at
        else:
            milestone.status = verdict
            milestone.approved_at = u64(0)

        self.milestones[milestone_id] = milestone
        self.projects[project_id] = project

    @gl.public.write
    def release_approved_milestone(
        self, project_id: str, milestone_id: str
    ) -> None:
        project = self._require_project(project_id)
        milestone = self._require_milestone(project_id, milestone_id)
        if project.status != "ACTIVE":
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Project is not active")
        if milestone.status != "APPROVED_PENDING":
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Milestone is not pending release")
        if milestone.active_dispute_id != "":
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Milestone has an open dispute")
        if self._now() <= milestone.appeal_deadline:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Dispute window is still open")

        self._settle_approved_milestone(project, milestone)
        self.milestones[milestone.id] = milestone
        self.projects[project.id] = project

    @gl.public.write
    def open_refunds(self, project_id: str) -> None:
        project = self._require_project(project_id)
        if project.status in ("REFUNDING", "COMPLETED"):
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Refund state is already final")
        if self._now() <= project.deadline:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Project deadline has not passed")
        if project.funded_amount == u256(0):
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Project has no refundable funds")
        if project.released_amount >= project.funded_amount:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Project has no refundable escrow")

        for milestone_id in self.milestone_ids:
            milestone = self.milestones[milestone_id]
            if milestone.project_id != project_id:
                continue
            if milestone.active_dispute_id != "" or milestone.status == "DISPUTED":
                raise gl.vm.UserError(f"{ERROR_EXPECTED} Resolve open disputes first")
            if milestone.status == "APPROVED_PENDING":
                raise gl.vm.UserError(f"{ERROR_EXPECTED} Settle approved milestones first")

        project.refund_pool = project.funded_amount - project.released_amount
        project.refunded_amount = u256(0)
        project.refund_claim_count = u32(0)
        project.refund_opened_at = self._now()
        project.status = "REFUNDING"

        for tranche_id in self.tranche_ids:
            tranche = self.tranches[tranche_id]
            if tranche.project_id == project_id and tranche.status == "OPEN":
                tranche.status = "CLOSED"
                self.tranches[tranche_id] = tranche
        for proposal_id in self.proposal_ids:
            proposal = self.proposals[proposal_id]
            if proposal.project_id == project_id and proposal.status == "OPEN":
                proposal.status = "CANCELLED"
                proposal.finalized_at = self._now()
                self.proposals[proposal_id] = proposal

        self.projects[project_id] = project

    @gl.public.write
    def claim_refund(self, project_id: str) -> None:
        project = self._require_project(project_id)
        if project.status != "REFUNDING":
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Refunds are not open")

        sender = gl.message.sender_address
        contribution = self.contributions.get(
            f"{project_id}:{sender.as_hex}", u256(0)
        )
        if contribution == u256(0):
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Address did not fund this project")
        claim_key = f"{project_id}:{sender.as_hex}"
        if self.refund_claimed.get(claim_key, False):
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Refund already claimed")

        amount = contribution * project.refund_pool // project.funded_amount
        if project.refund_claim_count + u32(1) == project.backer_count:
            amount = project.refund_pool - project.refunded_amount
        if amount == u256(0):
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Refund rounds to zero")
        if project.refunded_amount + amount > project.refund_pool:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Refund exceeds reserved escrow")

        self.refund_claimed[claim_key] = True
        project.refunded_amount += amount
        project.refund_claim_count += u32(1)
        self.total_refunded += amount
        self.projects[project_id] = project
        _Recipient(sender).emit_transfer(value=amount)

    @gl.public.write.payable
    def open_dispute(
        self,
        project_id: str,
        milestone_id: str,
        reason: str,
        counter_evidence_url: str,
    ) -> str:
        project = self._require_project(project_id)
        milestone = self._require_milestone(project_id, milestone_id)
        if project.status != "ACTIVE":
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Project is not active")
        if milestone.status not in ("APPROVED_PENDING", "NEEDS_WORK", "REJECTED"):
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Milestone has no disputable verdict")
        if milestone.released:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Released milestones cannot be disputed")
        if milestone.active_dispute_id != "":
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Milestone already has an open dispute")
        if milestone.appeal_deadline == u64(0) or self._now() > milestone.appeal_deadline:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Dispute window has closed")
        if gl.message.sender_address == project.creator:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Creator cannot challenge own milestone")
        contribution = self.contributions.get(
            f"{project_id}:{gl.message.sender_address.as_hex}", u256(0)
        )
        if contribution == u256(0):
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Only project backers can dispute")
        self._validate_text(reason, "Dispute reason", 30, 1500)
        if not counter_evidence_url.startswith("https://"):
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Counter-evidence must use HTTPS")
        if gl.message.value == u256(0):
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Dispute bond must be positive")

        dispute_id = f"DP-{len(self.dispute_ids) + 1:04d}"
        self.disputes[dispute_id] = Dispute(
            id=dispute_id,
            project_id=project_id,
            milestone_id=milestone_id,
            challenger=gl.message.sender_address,
            reason=reason.strip(),
            counter_evidence_url=counter_evidence_url.strip(),
            bond=gl.message.value,
            status="OPEN",
            resolution="",
            analysis="",
            created_at=self._now(),
            resolved_at=u64(0),
            original_verdict=milestone.verdict,
        )
        self.dispute_ids.append(dispute_id)
        milestone.status = "DISPUTED"
        milestone.active_dispute_id = dispute_id
        milestone.dispute_count += u32(1)
        self.milestones[milestone_id] = milestone
        self.total_disputes += u32(1)
        return dispute_id

    @gl.public.write
    def resolve_dispute(self, dispute_id: str) -> None:
        if dispute_id not in self.disputes:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Dispute not found")
        dispute = self.disputes[dispute_id]
        if dispute.status != "OPEN":
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Dispute already resolved")

        project = self._require_project(dispute.project_id)
        milestone = self._require_milestone(dispute.project_id, dispute.milestone_id)
        if project.status != "ACTIVE":
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Project is not active")
        if milestone.active_dispute_id != dispute_id:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Dispute is not active for milestone")
        original_verdict = dispute.original_verdict
        result = self._run_dispute_assessment(
            str(project.title),
            str(milestone.title),
            str(milestone.criteria),
            str(milestone.evidence_url),
            str(original_verdict),
            str(dispute.reason),
            str(dispute.counter_evidence_url),
        )

        resolution = str(result["resolution"])
        final_verdict = str(result["final_verdict"])
        if resolution == "UPHOLD" and final_verdict != original_verdict:
            raise gl.vm.UserError(f"{ERROR_LLM} Inconsistent upheld verdict")
        if resolution == "OVERTURN" and final_verdict == original_verdict:
            raise gl.vm.UserError(f"{ERROR_LLM} Overturn must change the verdict")
        dispute.status = "RESOLVED"
        dispute.resolution = resolution
        dispute.analysis = str(result["summary"])
        dispute.resolved_at = self._now()
        milestone.status = final_verdict
        milestone.verdict = final_verdict
        milestone.analysis = str(result["summary"])
        milestone.evaluated_at = self._now()
        milestone.active_dispute_id = ""

        challenger_profile = self._profile(dispute.challenger)
        if resolution == "OVERTURN":
            challenger_profile.disputes_won += u32(1)
            _Recipient(dispute.challenger).emit_transfer(value=dispute.bond)
        else:
            challenger_profile.disputes_lost += u32(1)
            _Recipient(project.creator).emit_transfer(value=dispute.bond)

        if final_verdict == "APPROVED":
            self._settle_approved_milestone(project, milestone)
        else:
            milestone.released = False
            milestone.approved_at = u64(0)

        self.reputation[dispute.challenger] = challenger_profile
        self.disputes[dispute_id] = dispute
        self.milestones[milestone.id] = milestone
        self.projects[project.id] = project

    @gl.public.view
    def get_dashboard(self) -> dict:
        active = 0
        completed = 0
        funded_tranches = 0
        open_proposals = 0
        refunding = 0
        for project_id in self.project_ids:
            status = self.projects[project_id].status
            if status in ("FUNDING", "ACTIVE", "PAUSED"):
                active += 1
            elif status == "COMPLETED":
                completed += 1
            elif status == "REFUNDING":
                refunding += 1
        for tranche_id in self.tranche_ids:
            if self.tranches[tranche_id].status == "FUNDED":
                funded_tranches += 1
        for proposal_id in self.proposal_ids:
            if self.proposals[proposal_id].status == "OPEN":
                open_proposals += 1
        return {
            "project_count": len(self.project_ids),
            "active_projects": active,
            "completed_projects": completed,
            "total_funded": self.total_funded,
            "total_released": self.total_released,
            "total_refunded": self.total_refunded,
            "total_disputes": self.total_disputes,
            "total_proposals": self.total_proposals,
            "open_proposals": open_proposals,
            "funded_tranches": funded_tranches,
            "refunding_projects": refunding,
            "contract_balance": self.balance,
        }

    @gl.public.view
    def get_projects(self) -> list:
        return [self.projects[project_id] for project_id in self.project_ids]

    @gl.public.view
    def get_project(self, project_id: str) -> dict:
        return self._require_project(project_id)

    @gl.public.view
    def get_milestones(self, project_id: str) -> list:
        self._require_project(project_id)
        result = []
        for milestone_id in self.milestone_ids:
            milestone = self.milestones[milestone_id]
            if milestone.project_id == project_id:
                result.append(milestone)
        return result

    @gl.public.view
    def get_disputes(self, project_id: str) -> list:
        self._require_project(project_id)
        result = []
        for dispute_id in self.dispute_ids:
            dispute = self.disputes[dispute_id]
            if dispute.project_id == project_id:
                result.append(dispute)
        return result

    @gl.public.view
    def get_tranches(self, project_id: str) -> list:
        self._require_project(project_id)
        result = []
        for tranche_id in self.tranche_ids:
            tranche = self.tranches[tranche_id]
            if tranche.project_id == project_id:
                result.append(tranche)
        return result

    @gl.public.view
    def get_proposals(self, project_id: str) -> list:
        self._require_project(project_id)
        result = []
        for proposal_id in self.proposal_ids:
            proposal = self.proposals[proposal_id]
            if proposal.project_id == project_id:
                result.append(proposal)
        return result

    @gl.public.view
    def get_governance(self) -> list:
        return [self.proposals[proposal_id] for proposal_id in self.proposal_ids]

    @gl.public.view
    def get_vote(self, proposal_id: str, account: str) -> str:
        self._require_proposal(proposal_id)
        return self.proposal_votes.get(
            f"{proposal_id}:{Address(account).as_hex}", ""
        )

    @gl.public.view
    def get_contribution(self, project_id: str, account: str) -> u256:
        return self.contributions.get(
            f"{project_id}:{Address(account).as_hex}", u256(0)
        )

    @gl.public.view
    def get_refund(self, project_id: str, account: str) -> dict:
        project = self._require_project(project_id)
        address = Address(account)
        contribution = self.contributions.get(
            f"{project_id}:{address.as_hex}", u256(0)
        )
        claimed = self.refund_claimed.get(
            f"{project_id}:{address.as_hex}", False
        )
        amount = u256(0)
        if project.status == "REFUNDING" and contribution > u256(0) and not claimed:
            amount = contribution * project.refund_pool // project.funded_amount
            if project.refund_claim_count + u32(1) == project.backer_count:
                amount = project.refund_pool - project.refunded_amount
        return {
            "status": project.status,
            "contribution": contribution,
            "refund_pool": project.refund_pool,
            "refunded_amount": project.refunded_amount,
            "claimable_refund": amount,
            "claimed": claimed,
        }

    @gl.public.view
    def get_profile(self, account: str) -> dict:
        address = Address(account)
        profile = self._profile(address)
        return {
            "address": address.as_hex,
            "projects_created": profile.projects_created,
            "projects_backed": profile.projects_backed,
            "milestones_approved": profile.milestones_approved,
            "disputes_won": profile.disputes_won,
            "disputes_lost": profile.disputes_lost,
            "total_funded": profile.total_funded,
            "total_earned": profile.total_earned,
            "proposals_created": profile.proposals_created,
            "votes_cast": profile.votes_cast,
        }
