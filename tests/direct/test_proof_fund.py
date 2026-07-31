import json
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest


FUTURE = 4_102_444_800
GOAL = 10**18
DESCRIPTION = (
    "ProofFund finances verifiable public-interest software through explicit "
    "milestones, public evidence, validator adjudication, and transparent escrow."
)
CONTRACT = "contracts/proof_fund.py"
ROOT = Path(__file__).resolve().parents[2]


def address_hex(address):
    return "0x" + bytes(address).hex()


def deploy_as(direct_vm, direct_deploy, sender):
    direct_vm.sender = sender
    direct_vm.value = 0
    return direct_deploy(CONTRACT)


def test_review_restore_requires_complete_funding_snapshot(
    direct_vm, direct_deploy, direct_alice
):
    contract = deploy_as(direct_vm, direct_deploy, direct_alice)
    manifest = json.loads(
        (ROOT / "deployments/migration-manifest.json").read_text()
    )
    direct_vm.value = 300_000_000_000_000_000
    with direct_vm.expect_revert("Funding snapshot is incomplete"):
        contract.restore_review_history(manifest["reviewHistory"]["payload"])
    direct_vm.value = 0


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
    contract.fund_project(project_id)
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


def test_consensus_evaluation_releases_milestone(
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
    contract.fund_project(project_id)
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
        r".*independent grant milestone auditor.*",
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
    assert milestone.released is True
    assert profile["claimable"] == GOAL
    assert profile["milestones_approved"] == 1


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
    contract.fund_project(project_id)
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

    direct_vm.sender = direct_bob
    direct_vm.value = GOAL
    contract.fund_tranche(project_id, f"{project_id}-T1")
    contract.fund_tranche(project_id, second_tranche)
    direct_vm.value = 0

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
