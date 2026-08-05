import json
import time
from datetime import datetime, timezone

import pytest


FUTURE = 4_102_444_800
GOAL = 10**18
DISPUTE_WINDOW = 7 * 86_400
DESCRIPTION = (
    "ProofFund finances verifiable public-interest software through explicit "
    "milestones, public evidence, validator adjudication, and transparent escrow."
)
CONTRACT = "contracts/proof_fund.py"


def address_hex(address):
    return "0x" + bytes(address).hex()


def deploy_as(direct_vm, direct_deploy, sender):
    direct_vm.sender = sender
    direct_vm.value = 0
    return direct_deploy(CONTRACT)


def create_project(contract):
    return contract.create_project(
        "Open Source Climate Ledger",
        "Public goods",
        "A transparent ledger for independently verifiable climate contributions.",
        DESCRIPTION,
        "https://github.com/genlayerlabs",
        "https://images.unsplash.com/photo-1569163139394-de4e4f43e4e5",
        GOAL,
        FUTURE,
        "Public launch tranche",
        GOAL,
        FUTURE - 172_800,
    )


def test_project_and_milestone_lifecycle(
    direct_vm, direct_deploy, direct_alice
):
    contract = deploy_as(direct_vm, direct_deploy, direct_alice)
    project_id = create_project(contract)
    milestone_id = contract.add_milestone(
        project_id,
        "Public alpha",
        "The repository contains runnable source code, setup documentation, and a public release.",
        GOAL,
        FUTURE - 86_400,
    )

    project = contract.get_project(project_id)
    milestones = contract.get_milestones(project_id)

    assert project.id == "PF-0001"
    assert project.creator.as_hex.lower() == address_hex(direct_alice).lower()
    assert project.status == "FUNDING"
    assert milestone_id == "PF-0001-M1"
    assert len(milestones) == 1
    assert milestones[0].status == "PENDING"


def test_only_creator_can_add_milestones(
    direct_vm, direct_deploy, direct_alice, direct_bob
):
    contract = deploy_as(direct_vm, direct_deploy, direct_alice)
    project_id = create_project(contract)

    direct_vm.sender = direct_bob
    with direct_vm.expect_revert("Only the creator"):
        contract.add_milestone(
            project_id,
            "Unauthorized milestone",
            "This criterion is long enough to pass the input-length validation.",
            GOAL,
            FUTURE - 86_400,
        )


def test_budget_cannot_exceed_goal(direct_vm, direct_deploy, direct_alice):
    contract = deploy_as(direct_vm, direct_deploy, direct_alice)
    project_id = create_project(contract)
    contract.add_milestone(
        project_id,
        "First delivery",
        "The public repository includes the first complete and documented delivery.",
        GOAL,
        FUTURE - 172_800,
    )

    with direct_vm.expect_revert("exceeds funding goal"):
        contract.add_milestone(
            project_id,
            "Second delivery",
            "The public repository includes another complete and documented delivery.",
            1,
            FUTURE - 86_400,
        )


def test_real_value_funding_activates_project(
    direct_vm, direct_deploy, direct_alice, direct_bob
):
    contract = deploy_as(direct_vm, direct_deploy, direct_alice)
    project_id = create_project(contract)
    contract.add_milestone(
        project_id,
        "Public alpha",
        "The repository contains runnable source code, setup documentation, and a public release.",
        GOAL,
        FUTURE - 86_400,
    )

    direct_vm.sender = direct_bob
    direct_vm.value = GOAL
    contract.fund_tranche(project_id, f"{project_id}-T1")
    direct_vm.value = 0

    project = contract.get_project(project_id)
    dashboard = contract.get_dashboard()
    profile = contract.get_profile(address_hex(direct_bob))

    assert project.funded_amount == GOAL
    assert project.backer_count == 1
    assert project.status == "ACTIVE"
    assert dashboard["total_funded"] == GOAL
    assert profile["projects_backed"] == 1
    assert profile["total_funded"] == GOAL


def test_full_funding_does_not_activate_without_full_milestone_coverage(
    direct_vm, direct_deploy, direct_alice, direct_bob
):
    contract = deploy_as(direct_vm, direct_deploy, direct_alice)
    project_id = create_project(contract)
    contract.add_milestone(
        project_id,
        "Partial delivery",
        "The repository contains a documented first delivery with reproducible validation steps.",
        GOAL // 2,
        FUTURE - 86_400,
    )
    direct_vm.sender = direct_bob
    direct_vm.value = GOAL
    contract.fund_tranche(project_id, f"{project_id}-T1")
    direct_vm.value = 0

    project = contract.get_project(project_id)
    assert project.funded_amount == GOAL
    assert project.milestone_budget == GOAL // 2
    assert project.status == "FUNDING"

    direct_vm.sender = direct_alice
    contract.add_milestone(
        project_id,
        "Final delivery",
        "The final public release completes the remaining scope and includes independent verification steps.",
        GOAL // 2,
        FUTURE - 43_200,
    )
    assert contract.get_project(project_id).status == "ACTIVE"


def test_consensus_evaluation_holds_then_releases_milestone(
    direct_vm, direct_deploy, direct_alice, direct_bob
):
    contract = deploy_as(direct_vm, direct_deploy, direct_alice)
    project_id = create_project(contract)
    milestone_id = contract.add_milestone(
        project_id,
        "Public alpha",
        "The repository contains runnable source code, setup documentation, and a public release.",
        GOAL,
        FUTURE - 86_400,
    )

    direct_vm.sender = direct_bob
    direct_vm.value = GOAL
    contract.fund_tranche(project_id, f"{project_id}-T1")
    direct_vm.value = 0

    direct_vm.sender = direct_alice
    contract.submit_evidence(
        project_id,
        milestone_id,
        "https://example.com/proof",
        "The release, source tree, and setup instructions are all linked on this page.",
    )

    direct_vm.mock_web(
        r".*example\.com/proof.*",
        {"status": 200, "body": "<html>Public alpha release and setup guide</html>"},
    )
    direct_vm.mock_llm(
        r".*Audit this grant milestone.*",
        json.dumps(
            {
                "verdict": "APPROVED",
                "score": 94,
                "summary": "All material criteria are directly supported.",
                "findings": [
                    "Runnable source is linked.",
                    "Setup documentation is present.",
                ],
            }
        ),
    )
    contract.evaluate_milestone(project_id, milestone_id)

    milestone = contract.get_milestones(project_id)[0]
    profile = contract.get_profile(address_hex(direct_alice))

    assert milestone.verdict == "APPROVED"
    assert milestone.status == "APPROVED_PENDING"
    assert milestone.released is False
    assert profile["milestones_approved"] == 0

    with direct_vm.expect_revert("Dispute window is still open"):
        contract.release_approved_milestone(project_id, milestone_id)

    direct_vm.warp(
        datetime.fromtimestamp(int(milestone.appeal_deadline) + 1, timezone.utc).isoformat()
    )
    contract.release_approved_milestone(project_id, milestone_id)

    milestone = contract.get_milestones(project_id)[0]
    project = contract.get_project(project_id)
    profile = contract.get_profile(address_hex(direct_alice))
    assert milestone.released is True
    assert milestone.status == "APPROVED"
    assert project.released_amount == GOAL
    assert project.status == "COMPLETED"
    assert profile["milestones_approved"] == 1
    assert profile["total_earned"] == GOAL


def test_creator_can_replace_submitted_evidence(
    direct_vm, direct_deploy, direct_alice, direct_bob
):
    contract = deploy_as(direct_vm, direct_deploy, direct_alice)
    project_id = create_project(contract)
    milestone_id = contract.add_milestone(
        project_id,
        "Public alpha",
        "The repository contains runnable source code, setup documentation, and a public release.",
        GOAL,
        FUTURE - 86_400,
    )

    direct_vm.sender = direct_bob
    direct_vm.value = GOAL
    contract.fund_tranche(project_id, f"{project_id}-T1")
    direct_vm.value = 0

    direct_vm.sender = direct_alice
    contract.submit_evidence(
        project_id,
        milestone_id,
        "https://example.com/unavailable",
        "The first submitted source cannot be retrieved by the validator network.",
    )
    contract.submit_evidence(
        project_id,
        milestone_id,
        "https://example.com/public-proof",
        "This replacement links the public release, source tree, and setup instructions.",
    )

    milestone = contract.get_milestones(project_id)[0]
    assert milestone.status == "SUBMITTED"
    assert milestone.evidence_url == "https://example.com/public-proof"


def test_multiple_funding_tranches_activate_project(
    direct_vm, direct_deploy, direct_alice, direct_bob
):
    contract = deploy_as(direct_vm, direct_deploy, direct_alice)
    project_id = contract.create_project(
        "Two-stage public infrastructure",
        "Infrastructure",
        "A project financed through two independently visible funding stages.",
        DESCRIPTION,
        "https://github.com/genlayerlabs",
        "",
        2 * GOAL,
        FUTURE,
        "Research and specification",
        GOAL,
        FUTURE - 172_800,
    )
    second_tranche = contract.add_funding_tranche(
        project_id,
        "Implementation and release",
        GOAL,
        FUTURE - 86_400,
    )
    contract.add_milestone(
        project_id,
        "Specification package",
        "The public repository contains a complete reviewed specification and implementation plan.",
        GOAL,
        FUTURE - 172_800,
    )

    direct_vm.sender = direct_bob
    direct_vm.value = GOAL
    contract.fund_tranche(project_id, f"{project_id}-T1")
    contract.fund_tranche(project_id, second_tranche)
    direct_vm.value = 0

    assert contract.get_project(project_id).status == "FUNDING"

    direct_vm.sender = direct_alice
    contract.add_milestone(
        project_id,
        "Production release",
        "The public release is deployed, documented, reproducible, and independently inspectable.",
        GOAL,
        FUTURE - 86_400,
    )

    project = contract.get_project(project_id)
    tranches = contract.get_tranches(project_id)
    assert project.status == "ACTIVE"
    assert project.funded_amount == 2 * GOAL
    assert len(tranches) == 2
    assert all(tranche.status == "FUNDED" for tranche in tranches)


def test_backer_weighted_governance_executes_deadline_extension(
    direct_vm, direct_deploy, direct_alice, direct_bob
):
    contract = deploy_as(direct_vm, direct_deploy, direct_alice)
    project_id = create_project(contract)

    direct_vm.sender = direct_bob
    direct_vm.value = GOAL
    contract.fund_tranche(project_id, f"{project_id}-T1")
    direct_vm.value = 0

    voting_end = int(time.time()) + 120
    direct_vm.sender = direct_alice
    proposal_id = contract.create_proposal(
        project_id,
        "Extend the delivery horizon",
        "Move the final project deadline to preserve review quality after an external dependency delay.",
        "EXTEND_DEADLINE",
        FUTURE + 86_400,
        voting_end,
    )

    direct_vm.sender = direct_bob
    contract.vote_proposal(proposal_id, True)
    direct_vm.warp(
        datetime.fromtimestamp(voting_end + 1, timezone.utc).isoformat()
    )
    contract.finalize_proposal(proposal_id)

    proposal = contract.get_proposals(project_id)[0]
    project = contract.get_project(project_id)
    assert proposal.status == "PASSED"
    assert proposal.yes_votes == GOAL
    assert project.deadline == FUTURE + 86_400
    assert contract.get_vote(proposal_id, address_hex(direct_bob)) == "YES"


def activate_single_milestone_project(contract, direct_vm, creator, backer):
    direct_vm.sender = creator
    project_id = create_project(contract)
    milestone_id = contract.add_milestone(
        project_id,
        "Public alpha",
        "The repository contains runnable source code, setup documentation, and a public release.",
        GOAL,
        FUTURE - 86_400,
    )
    direct_vm.sender = backer
    direct_vm.value = GOAL
    contract.fund_tranche(project_id, f"{project_id}-T1")
    direct_vm.value = 0
    return project_id, milestone_id


def evaluate(contract, direct_vm, creator, project_id, milestone_id, verdict):
    direct_vm.sender = creator
    contract.submit_evidence(
        project_id,
        milestone_id,
        "https://example.com/proof",
        "The release, source tree, and reproducible setup instructions are linked here.",
    )
    direct_vm.mock_web(
        r".*example\.com/proof.*",
        {"status": 200, "body": "<html>Release, source, tests, and setup guide</html>"},
    )
    direct_vm.mock_llm(
        r".*Audit this grant milestone.*",
        json.dumps(
            {
                "verdict": verdict,
                "score": 95 if verdict == "APPROVED" else 24,
                "summary": "The submitted evidence was assessed against every criterion.",
                "findings": ["Source inspected.", "Acceptance criteria checked."],
            }
        ),
    )
    contract.evaluate_milestone(project_id, milestone_id)


def mock_dispute(direct_vm, resolution, final_verdict):
    direct_vm.mock_web(
        r".*example\.com/(proof|counter).*$",
        {"status": 200, "body": "<html>Independent evidence record</html>"},
    )
    direct_vm.mock_llm(
        r".*Reassess this grant appeal.*",
        json.dumps(
            {
                "resolution": resolution,
                "final_verdict": final_verdict,
                "summary": "The appeal record supports this final disposition.",
            }
        ),
    )


def open_backer_dispute(contract, direct_vm, backer, project_id, milestone_id):
    direct_vm.sender = backer
    direct_vm.value = GOAL // 10
    dispute_id = contract.open_dispute(
        project_id,
        milestone_id,
        "The submitted record omits a material acceptance condition and requires appeal review.",
        "https://example.com/counter",
    )
    direct_vm.value = 0
    return dispute_id


def test_approved_appeal_uphold_atomically_releases_funds_and_bond(
    direct_vm, direct_deploy, direct_alice, direct_bob
):
    contract = deploy_as(direct_vm, direct_deploy, direct_alice)
    project_id, milestone_id = activate_single_milestone_project(
        contract, direct_vm, direct_alice, direct_bob
    )
    evaluate(contract, direct_vm, direct_alice, project_id, milestone_id, "APPROVED")
    dispute_id = open_backer_dispute(
        contract, direct_vm, direct_bob, project_id, milestone_id
    )
    mock_dispute(direct_vm, "UPHOLD", "APPROVED")
    contract.resolve_dispute(dispute_id)

    milestone = contract.get_milestones(project_id)[0]
    dispute = contract.get_disputes(project_id)[0]
    creator = contract.get_profile(address_hex(direct_alice))
    challenger = contract.get_profile(address_hex(direct_bob))
    assert dispute.original_verdict == "APPROVED"
    assert dispute.status == "RESOLVED"
    assert dispute.resolution == "UPHOLD"
    assert milestone.status == "APPROVED"
    assert milestone.released is True
    assert milestone.active_dispute_id == ""
    assert creator["total_earned"] == GOAL
    assert challenger["disputes_lost"] == 1


def test_approved_appeal_overturn_preserves_escrow_for_refunds(
    direct_vm, direct_deploy, direct_alice, direct_bob
):
    contract = deploy_as(direct_vm, direct_deploy, direct_alice)
    project_id, milestone_id = activate_single_milestone_project(
        contract, direct_vm, direct_alice, direct_bob
    )
    evaluate(contract, direct_vm, direct_alice, project_id, milestone_id, "APPROVED")
    dispute_id = open_backer_dispute(
        contract, direct_vm, direct_bob, project_id, milestone_id
    )
    mock_dispute(direct_vm, "OVERTURN", "REJECTED")
    contract.resolve_dispute(dispute_id)

    milestone = contract.get_milestones(project_id)[0]
    project = contract.get_project(project_id)
    creator = contract.get_profile(address_hex(direct_alice))
    challenger = contract.get_profile(address_hex(direct_bob))
    assert milestone.status == "REJECTED"
    assert milestone.released is False
    assert project.released_amount == 0
    assert creator["total_earned"] == 0
    assert challenger["disputes_won"] == 1


def test_rejected_appeal_overturn_atomically_approves_and_releases(
    direct_vm, direct_deploy, direct_alice, direct_bob
):
    contract = deploy_as(direct_vm, direct_deploy, direct_alice)
    project_id, milestone_id = activate_single_milestone_project(
        contract, direct_vm, direct_alice, direct_bob
    )
    evaluate(contract, direct_vm, direct_alice, project_id, milestone_id, "REJECTED")
    dispute_id = open_backer_dispute(
        contract, direct_vm, direct_bob, project_id, milestone_id
    )
    mock_dispute(direct_vm, "OVERTURN", "APPROVED")
    contract.resolve_dispute(dispute_id)

    milestone = contract.get_milestones(project_id)[0]
    project = contract.get_project(project_id)
    dispute = contract.get_disputes(project_id)[0]
    assert dispute.original_verdict == "REJECTED"
    assert dispute.resolution == "OVERTURN"
    assert milestone.verdict == "APPROVED"
    assert milestone.released is True
    assert project.released_amount == GOAL
    assert project.status == "COMPLETED"
    assert contract.get_dashboard()["contract_balance"] == 0


def test_dispute_cannot_open_after_window(
    direct_vm, direct_deploy, direct_alice, direct_bob
):
    contract = deploy_as(direct_vm, direct_deploy, direct_alice)
    project_id, milestone_id = activate_single_milestone_project(
        contract, direct_vm, direct_alice, direct_bob
    )
    evaluate(contract, direct_vm, direct_alice, project_id, milestone_id, "REJECTED")
    milestone = contract.get_milestones(project_id)[0]
    direct_vm.warp(
        datetime.fromtimestamp(int(milestone.appeal_deadline) + 1, timezone.utc).isoformat()
    )
    direct_vm.sender = direct_bob
    direct_vm.value = GOAL // 10
    with direct_vm.expect_revert("Dispute window has closed"):
        contract.open_dispute(
            project_id,
            milestone_id,
            "The record should be reconsidered based on this independently reproducible counter-proof.",
            "https://example.com/counter",
        )
    direct_vm.value = 0


def test_terminal_refunds_are_proportional_and_block_double_spend(
    direct_vm, direct_deploy, direct_alice, direct_bob, direct_charlie
):
    contract = deploy_as(direct_vm, direct_deploy, direct_alice)
    direct_vm.sender = direct_alice
    project_id = create_project(contract)
    milestone_id = contract.add_milestone(
        project_id,
        "Public alpha",
        "The repository contains runnable source code, setup documentation, and a public release.",
        GOAL,
        FUTURE - 86_400,
    )
    direct_vm.sender = direct_bob
    direct_vm.value = GOAL // 4
    contract.fund_tranche(project_id, f"{project_id}-T1")
    direct_vm.sender = direct_charlie
    direct_vm.value = GOAL - GOAL // 4
    contract.fund_tranche(project_id, f"{project_id}-T1")
    direct_vm.value = 0

    direct_vm.warp(datetime.fromtimestamp(FUTURE + 1, timezone.utc).isoformat())
    contract.open_refunds(project_id)
    project = contract.get_project(project_id)
    assert project.status == "REFUNDING"
    assert project.refund_pool == GOAL

    direct_vm.sender = direct_bob
    contract.claim_refund(project_id)
    with direct_vm.expect_revert("Refund already claimed"):
        contract.claim_refund(project_id)
    direct_vm.sender = direct_charlie
    contract.claim_refund(project_id)

    project = contract.get_project(project_id)
    dashboard = contract.get_dashboard()
    assert project.refunded_amount == GOAL
    assert project.refund_claim_count == 2
    assert dashboard["total_refunded"] == GOAL
    assert dashboard["contract_balance"] == 0

    direct_vm.sender = direct_alice
    with direct_vm.expect_revert("Project must be fully funded"):
        contract.submit_evidence(
            project_id,
            milestone_id,
            "https://example.com/proof",
            "This action must remain impossible after terminal refunds have opened.",
        )


def test_open_dispute_prevents_refund_mode(
    direct_vm, direct_deploy, direct_alice, direct_bob
):
    contract = deploy_as(direct_vm, direct_deploy, direct_alice)
    project_id, milestone_id = activate_single_milestone_project(
        contract, direct_vm, direct_alice, direct_bob
    )
    evaluate(contract, direct_vm, direct_alice, project_id, milestone_id, "REJECTED")
    open_backer_dispute(contract, direct_vm, direct_bob, project_id, milestone_id)
    direct_vm.warp(datetime.fromtimestamp(FUTURE + 1, timezone.utc).isoformat())
    with direct_vm.expect_revert("Resolve open disputes first"):
        contract.open_refunds(project_id)
