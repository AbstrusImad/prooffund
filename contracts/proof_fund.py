# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone

from genlayer import *


ERROR_EXPECTED = "[EXPECTED]"
ERROR_EXTERNAL = "[EXTERNAL]"
ERROR_LLM = "[LLM_ERROR]"

DISPUTE_WINDOW_SECONDS = 7 * 86_400  # 7 days


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
    dispute_window_end: u64


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
    claimable: TreeMap[Address, u256]
    reputation: TreeMap[Address, Reputation]
    total_funded: u256
    total_released: u256
    total_disputes: u32
    total_proposals: u32
    review_history_restored: bool
    inspectors: TreeMap[str, bool]
    inspector_ids: DynArray[str]
    incidents: TreeMap[str, str]
    incident_ids: DynArray[str]
    backer_refunded: TreeMap[str, bool]

    def __init__(self):
        self.owner = gl.message.sender_address
        self.total_funded = u256(0)
        self.total_released = u256(0)
        self.total_disputes = u32(0)
        self.total_proposals = u32(0)
        self.review_history_restored = False

    @gl.public.write.payable
    def restore_review_history(self, payload: str) -> None:
        if gl.message.sender_address != self.owner:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Owner authorization required")
        if self.review_history_restored:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Review history already restored")
        if len(self.project_ids) != 9 or self.total_funded != u256(57000000000000000000):
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Funding snapshot is incomplete")
        if gl.message.value != u256(300000000000000000):
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Dispute backing must be 0.3 GEN")
        if (
            hashlib.sha256(payload.encode()).hexdigest()
            != "323e5cd84049d17217f336c57a1ebe733c3e110b6235558fccd0fd671edea297"
        ):
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Review snapshot hash mismatch")
        try:
            data = json.loads(payload)
        except Exception:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Review snapshot is invalid")
        if len(data["milestones"]) != 3 or len(data["disputes"]) != 3:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Review snapshot count mismatch")

        for record in data["milestones"]:
            milestone = self._require_milestone(record["project_id"], record["id"])
            milestone.status = record["status"]
            milestone.evidence_url = record["evidence_url"]
            milestone.evidence_note = record["evidence_note"]
            milestone.submitted_at = u64(record["submitted_at"])
            milestone.verdict = record["verdict"]
            milestone.score = u32(record["score"])
            milestone.analysis = record["analysis"]
            milestone.findings_json = record["findings_json"]
            milestone.evaluated_at = u64(record["evaluated_at"])
            milestone.released = record["released"]
            milestone.dispute_count = u32(record["dispute_count"])
            milestone.approved_at = u64(record.get("approved_at", 0))
            milestone.dispute_window_end = u64(record.get("dispute_window_end", 0))
            self.milestones[milestone.id] = milestone

        for record in data["disputes"]:
            item = Dispute(
                id=record["id"],
                project_id=record["project_id"],
                milestone_id=record["milestone_id"],
                challenger=Address(record["challenger"]),
                reason=record["reason"],
                counter_evidence_url=record["counter_evidence_url"],
                bond=u256(int(record["bond"])),
                status=record["status"],
                resolution=record["resolution"],
                analysis=record["analysis"],
                created_at=u64(record["created_at"]),
                resolved_at=u64(record["resolved_at"]),
            )
            self.dispute_ids.append(item.id)
            self.disputes[item.id] = item

        self.total_disputes = u32(3)
        self.review_history_restored = True

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
        if project.funded_amount == project.funding_goal:
            if project.milestone_budget >= project.funding_goal:
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

            prompt = f"""
You are an independent grant milestone auditor. Evaluate only the supplied
evidence against the explicit acceptance criteria. Do not reward effort,
intentions, visual polish, or claims that are not supported by the page.

Project: {project_title}
Milestone: {milestone_title}
Acceptance criteria:
<criteria>{criteria}</criteria>
Creator note:
<note>{evidence_note}</note>
Evidence page:
<evidence>{page[:18000]}</evidence>

Return JSON with exactly:
{{
  "verdict": "APPROVED" | "NEEDS_WORK" | "REJECTED",
  "score": integer from 0 to 100,
  "summary": concise audit conclusion under 500 characters,
  "findings": array of 2 to 6 concise factual findings
}}

APPROVED requires direct evidence that every material criterion is satisfied.
NEEDS_WORK means some criteria are supported but material gaps remain.
REJECTED means the evidence is unrelated, inaccessible, deceptive, or fails
the core criterion.
"""
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

            prompt = f"""
Act as an appeal panel for an on-chain grant milestone. Reassess the original
evidence and the challenger's counter-evidence from first principles.

Project: {project_title}
Milestone: {milestone_title}
Criteria: <criteria>{criteria}</criteria>
Original verdict: {original_verdict}
Original evidence: <original>{original_page[:12000]}</original>
Challenge: <reason>{dispute_reason}</reason>
Counter-evidence: <counter>{counter_page[:12000]}</counter>

Return JSON:
{{
  "resolution": "UPHOLD" | "OVERTURN",
  "final_verdict": "APPROVED" | "NEEDS_WORK" | "REJECTED",
  "summary": concise reason under 600 characters
}}

UPHOLD means the original verdict remains correct. OVERTURN requires a
material factual or interpretive error demonstrated by the counter-evidence.
"""
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
            dispute_window_end=u64(0),
        )
        self.milestone_ids.append(milestone_id)
        project.milestone_count = index
        project.milestone_budget += amount
        project.status = "FUNDING"
        if (
            project.funded_amount == project.funding_goal
            and project.milestone_budget >= project.funding_goal
        ):
            project.status = "ACTIVE"
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

    @gl.public.write.payable
    def fund_project(self, project_id: str) -> None:
        project = self._require_project(project_id)
        if project.status != "FUNDING":
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Project is not accepting funds")
        if self._now() > project.deadline:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Funding deadline has passed")
        for tranche_id in self.tranche_ids:
            tranche = self.tranches[tranche_id]
            if tranche.project_id == project_id and tranche.status == "OPEN":
                if self._now() > tranche.deadline:
                    continue
                self._record_funding(project, tranche, gl.message.value)
                return
        raise gl.vm.UserError(f"{ERROR_EXPECTED} No open funding tranche")

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

        total_votes = proposal.yes_votes + proposal.no_votes
        passed = total_votes >= proposal.quorum and proposal.yes_votes > proposal.no_votes
        proposal.status = "PASSED" if passed else "REJECTED"
        proposal.finalized_at = self._now()

        if passed:
            project = self._require_project(proposal.project_id)
            if proposal.action == "EXTEND_DEADLINE":
                project.deadline = u64(int(proposal.action_value))
            elif proposal.action == "PAUSE_FUNDING" and project.status == "FUNDING":
                project.status = "PAUSED"
            elif proposal.action == "REOPEN_FUNDING" and project.status == "PAUSED":
                project.status = "FUNDING"
            self.projects[project.id] = project
        self.proposals[proposal_id] = proposal

    @gl.public.write
    def register_inspector(self, inspector: Address) -> None:
        if gl.message.sender_address != self.owner:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Only owner can register inspectors")
        addr_hex = Address(inspector).as_hex.lower()
        if not self.inspectors.get(addr_hex, False):
            self.inspectors[addr_hex] = True
            self.inspector_ids.append(addr_hex)

    @gl.public.write
    def revoke_inspector(self, inspector: Address) -> None:
        if gl.message.sender_address != self.owner:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Only owner can revoke inspectors")
        addr_hex = Address(inspector).as_hex.lower()
        self.inspectors[addr_hex] = False

    @gl.public.view
    def is_inspector(self, account: str) -> bool:
        addr_hex = Address(account).as_hex.lower()
        return self.inspectors.get(addr_hex, False)

    @gl.public.view
    def get_inspectors(self) -> list:
        out = []
        for i in range(len(self.inspector_ids)):
            addr_hex = self.inspector_ids[i]
            if self.inspectors.get(addr_hex, False):
                out.append(addr_hex)
        return out

    @gl.public.write
    def submit_inspection_finding(
        self,
        project_id: str,
        milestone_id: str,
        findings: str,
        evidence_url: str,
        attestation_hash: str,
        required_response: str,
    ) -> str:
        sender = gl.message.sender_address
        sender_hex = sender.as_hex.lower()
        if not self.inspectors.get(sender_hex, False) and sender != self.owner:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Sender is not an authorized inspector")

        project = self._require_project(project_id)
        milestone = self._require_milestone(project_id, milestone_id)

        self._validate_text(findings, "Inspection findings", 15, 1000)
        self._validate_text(required_response, "Required response", 15, 1000)
        if not evidence_url.startswith("https://"):
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Evidence URL must use HTTPS")
        if attestation_hash and (
            len(attestation_hash) != 64
            or any(c not in "0123456789abcdefABCDEF" for c in attestation_hash)
        ):
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Invalid attestation hash format")

        incident_id = f"INC-{len(self.incident_ids) + 1:04d}"
        incident_data = {
            "id": incident_id,
            "project_id": project_id,
            "milestone_id": milestone_id,
            "inspector": sender.as_hex,
            "findings": findings.strip(),
            "evidence_url": evidence_url.strip(),
            "attestation_hash": attestation_hash.strip().lower(),
            "required_response": required_response.strip(),
            "validated_response": "",
            "status": "OPEN",
            "created_at": int(self._now()),
            "evaluated_at": 0,
        }
        self.incidents[incident_id] = json.dumps(incident_data)
        self.incident_ids.append(incident_id)

        milestone.evidence_url = evidence_url.strip()
        milestone.evidence_note = (
            f"Inspector Finding: {findings.strip()} | "
            f"Required Action: {required_response.strip()}"
        )
        milestone.submitted_at = self._now()
        milestone.status = "SUBMITTED"
        milestone.verdict = ""
        milestone.analysis = ""
        milestone.findings_json = "[]"
        self.milestones[milestone_id] = milestone

        return incident_id

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
        sender = gl.message.sender_address
        sender_hex = sender.as_hex.lower()
        is_authorized = (
            sender == project.creator
            or sender == self.owner
            or self.inspectors.get(sender_hex, False)
        )
        if not is_authorized:
            raise gl.vm.UserError(
                f"{ERROR_EXPECTED} Only creator or authorized inspector can submit evidence"
            )
        if project.status != "ACTIVE":
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Project must be fully funded")
        if milestone.status not in ("PENDING", "SUBMITTED", "NEEDS_WORK", "REJECTED", "APPROVED_PENDING"):
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

        # Update linked incident state if present
        for i in range(len(self.incident_ids)):
            inc_id = self.incident_ids[i]
            inc_str = self.incidents.get(inc_id, "")
            if inc_str:
                inc = json.loads(inc_str)
                if inc.get("milestone_id") == milestone_id and inc.get("status") in (
                    "OPEN",
                    "EVALUATING",
                ):
                    inc["status"] = "RESOLVED" if verdict == "APPROVED" else "REJECTED"
                    inc["validated_response"] = str(result["summary"])
                    inc["evaluated_at"] = int(self._now())
                    self.incidents[inc_id] = json.dumps(inc)

        if verdict == "APPROVED":
            # Hold funds through dispute window — do NOT release immediately
            if project.released_amount + milestone.amount > project.funded_amount:
                raise gl.vm.UserError(f"{ERROR_EXPECTED} Insufficient funded escrow")
            self._enter_dispute_window(milestone)

        self.milestones[milestone_id] = milestone
        self.projects[project_id] = project

    def _credit_milestone_release(
        self, project: Project, milestone: Milestone
    ) -> None:
        milestone.released = True
        milestone.status = "APPROVED"
        project.released_amount += milestone.amount
        self.total_released += milestone.amount
        self.claimable[project.creator] = (
            self.claimable.get(project.creator, u256(0)) + milestone.amount
        )
        profile = self._profile(project.creator)
        profile.milestones_approved += u32(1)
        profile.total_earned += milestone.amount
        self.reputation[project.creator] = profile
        if project.released_amount == project.milestone_budget:
            project.status = "COMPLETED"

    def _enter_dispute_window(self, milestone: Milestone) -> None:
        milestone.status = "APPROVED_PENDING"
        milestone.approved_at = self._now()
        milestone.dispute_window_end = self._now() + u64(DISPUTE_WINDOW_SECONDS)

    def _reverse_milestone_release(
        self, project: Project, milestone: Milestone
    ) -> None:
        milestone.released = False
        project.released_amount -= milestone.amount
        self.total_released -= milestone.amount
        creator_claim = self.claimable.get(project.creator, u256(0))
        if creator_claim >= milestone.amount:
            self.claimable[project.creator] = creator_claim - milestone.amount
            creator_profile = self._profile(project.creator)
            if creator_profile.milestones_approved > u32(0):
                creator_profile.milestones_approved -= u32(1)
            if creator_profile.total_earned >= milestone.amount:
                creator_profile.total_earned -= milestone.amount
            self.reputation[project.creator] = creator_profile
        project.status = "ACTIVE"

    @gl.public.write
    def release_approved_milestone(
        self, project_id: str, milestone_id: str
    ) -> None:
        project = self._require_project(project_id)
        milestone = self._require_milestone(project_id, milestone_id)
        if milestone.status != "APPROVED_PENDING":
            raise gl.vm.UserError(
                f"{ERROR_EXPECTED} Milestone is not awaiting dispute window"
            )
        if self._now() < milestone.dispute_window_end:
            raise gl.vm.UserError(
                f"{ERROR_EXPECTED} Dispute window has not closed"
            )
        if milestone.released:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Milestone already released")
        self._credit_milestone_release(project, milestone)
        self.milestones[milestone_id] = milestone
        self.projects[project_id] = project

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
        if milestone.status not in (
            "APPROVED",
            "APPROVED_PENDING",
            "NEEDS_WORK",
            "REJECTED",
        ):
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Milestone has no disputable verdict")
        if gl.message.sender_address == project.creator:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Creator cannot challenge own milestone")
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
        )
        self.dispute_ids.append(dispute_id)
        milestone.status = "DISPUTED"
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
        original_verdict = milestone.verdict
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
        dispute.status = "RESOLVED"
        dispute.resolution = resolution
        dispute.analysis = str(result["summary"])
        dispute.resolved_at = self._now()

        was_released = milestone.released
        was_approved_pending = milestone.status == "APPROVED_PENDING"

        milestone.status = final_verdict
        milestone.verdict = final_verdict
        milestone.analysis = str(result["summary"])
        milestone.evaluated_at = self._now()
        milestone.approved_at = u64(0)
        milestone.dispute_window_end = u64(0)

        challenger_profile = self._profile(dispute.challenger)
        if resolution == "OVERTURN":
            challenger_profile.disputes_won += u32(1)
            self.claimable[dispute.challenger] = (
                self.claimable.get(dispute.challenger, u256(0)) + dispute.bond
            )
            if was_released:
                self._reverse_milestone_release(project, milestone)
            elif was_approved_pending:
                if final_verdict == "APPROVED":
                    self._enter_dispute_window(milestone)
                if project.status == "COMPLETED":
                    project.status = "ACTIVE"
            if (
                final_verdict == "APPROVED"
                and not was_released
                and not was_approved_pending
            ):
                self._enter_dispute_window(milestone)
        else:
            challenger_profile.disputes_lost += u32(1)
            self.claimable[project.creator] = (
                self.claimable.get(project.creator, u256(0)) + dispute.bond
            )
            if final_verdict == "APPROVED":
                if was_released:
                    milestone.status = "APPROVED"
                elif was_approved_pending:
                    self._credit_milestone_release(project, milestone)
                else:
                    self._enter_dispute_window(milestone)

        self.reputation[dispute.challenger] = challenger_profile
        self.disputes[dispute_id] = dispute
        self.milestones[milestone.id] = milestone
        self.projects[project.id] = project

    @gl.public.write
    def claim(self) -> None:
        sender = gl.message.sender_address
        amount = self.claimable.get(sender, u256(0))
        if amount == u256(0):
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Nothing to claim")
        self.claimable[sender] = u256(0)
        _Recipient(sender).emit_transfer(value=amount)

    @gl.public.write
    def claim_refund(self, project_id: str) -> None:
        project = self._require_project(project_id)
        if self._now() <= project.deadline:
            raise gl.vm.UserError(
                f"{ERROR_EXPECTED} Refund activates after project deadline"
            )
        if project.status == "COMPLETED":
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Completed projects are not refundable")

        sender = gl.message.sender_address
        refund_key = f"{project_id}:{sender.as_hex}"
        if self.backer_refunded.get(refund_key, False):
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Refund already claimed")

        contribution = self.contributions.get(refund_key, u256(0))
        if contribution == u256(0):
            raise gl.vm.UserError(f"{ERROR_EXPECTED} No contribution to refund")

        available = project.funded_amount - project.released_amount
        if available == u256(0):
            raise gl.vm.UserError(f"{ERROR_EXPECTED} No funds available for refund")

        refund_amount = contribution * available // project.funded_amount
        if refund_amount == u256(0):
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Refund amount is zero")

        self.backer_refunded[refund_key] = True
        self.claimable[sender] = self.claimable.get(sender, u256(0)) + refund_amount

    @gl.public.view
    def get_dashboard(self) -> dict:
        active = 0
        completed = 0
        funded_tranches = 0
        open_proposals = 0
        for project_id in self.project_ids:
            status = self.projects[project_id].status
            if status in ("FUNDING", "ACTIVE", "PAUSED"):
                active += 1
            elif status == "COMPLETED":
                completed += 1
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
            "total_disputes": self.total_disputes,
            "total_proposals": self.total_proposals,
            "open_proposals": open_proposals,
            "funded_tranches": funded_tranches,
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
            "claimable": self.claimable.get(address, u256(0)),
            "is_inspector": self.inspectors.get(address.as_hex.lower(), False),
        }

    @gl.public.view
    def get_incidents(self, project_id: str) -> list:
        out = []
        for i in range(len(self.incident_ids)):
            inc_str = self.incidents.get(self.incident_ids[i], "")
            if inc_str:
                inc = json.loads(inc_str)
                if inc.get("project_id") == project_id or not project_id:
                    out.append(inc)
        return out

    @gl.public.view
    def get_incident(self, incident_id: str) -> dict:
        inc_str = self.incidents.get(incident_id, "")
        if not inc_str:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Incident not found")
        return json.loads(inc_str)
