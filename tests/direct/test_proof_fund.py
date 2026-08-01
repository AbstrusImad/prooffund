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

    # Funds held through dispute window — not yet released
    assert milestone.verdict == "APPROVED"
    assert milestone.status == "APPROVED_PENDING"
    assert milestone.released is False
    assert profile["claimable"] == 0
    assert profile["milestones_approved"] == 0

    # Warp past dispute window and release
    direct_vm.warp(
        datetime.fromtimestamp(
            int(milestone.dispute_window_end) + 1, timezone.utc
        ).isoformat()
    )
    contract.release_approved_milestone(project_id, milestone_id)

    milestone = contract.get_milestones(project_id)[0]
    profile = contract.get_profile(address_hex(direct_alice))

    assert milestone.verdict == "APPROVED"
    assert milestone.status == "APPROVED"
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
    # Add milestones covering the full 2*GOAL funding goal
    contract.add_milestone(
        project_id,
        "Research complete",
        "A published research document with specifications and references covering the full scope.",
        GOAL,
        FUTURE - 86_400,
    )
    contract.add_milestone(
        project_id,
        "Implementation shipped",
        "A public release with runnable source, setup documentation, and integration tests.",
        GOAL,
        FUTURE - 43_200,
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


def test_inspector_role_management_and_authorization(
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

    bob_hex = address_hex(direct_bob)
    assert contract.is_inspector(bob_hex) is False

    # Owner registers Bob as authorized inspector
    contract.register_inspector(bob_hex)
    assert contract.is_inspector(bob_hex) is True
    assert bob_hex.lower() in [i.lower() for i in contract.get_inspectors()]

    # Non-inspector cannot submit inspection finding
    direct_vm.sender = direct_bob
    inc_id = contract.submit_inspection_finding(
        project_id,
        milestone_id,
        "Sensor telemetry shows 99.8% node uptime across test nodes.",
        "https://example.com/telemetry-sensor",
        "a" * 64,
        "Verify node uptime telemetry and ensure setup guide matches release.",
    )

    incidents = contract.get_incidents(project_id)
    assert len(incidents) == 1
    assert incidents[0]["id"] == inc_id
    assert incidents[0]["inspector"].lower() == bob_hex.lower()
    assert incidents[0]["status"] == "OPEN"
    assert incidents[0]["required_response"] == "Verify node uptime telemetry and ensure setup guide matches release."


def test_incident_state_and_validated_response(
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

    # Alice registers Bob as inspector
    direct_vm.sender = direct_alice
    contract.register_inspector(address_hex(direct_bob))

    # Bob submits inspection finding and required response
    direct_vm.sender = direct_bob
    inc_id = contract.submit_inspection_finding(
        project_id,
        milestone_id,
        "Inspector finding: Verification report loaded with cryptographic proof.",
        "https://example.com/verified-report",
        "b" * 64,
        "Action required: Confirm release tag matches attestation hash.",
    )

    direct_vm.mock_web(
        r".*example\.com/verified-report.*",
        {"status": 200, "body": "<html>Verified Report Attestation HTML</html>"},
    )
    direct_vm.mock_llm(
        r".*independent grant milestone auditor.*",
        json.dumps(
            {
                "verdict": "APPROVED",
                "score": 96,
                "summary": "Verified report attestation satisfied all criteria and response actions.",
                "findings": [
                    "Attestation hash confirmed.",
                    "Required action validated.",
                ],
            }
        ),
    )

    direct_vm.sender = direct_alice
    contract.evaluate_milestone(project_id, milestone_id)

    incident = contract.get_incident(inc_id)
    assert incident["status"] == "RESOLVED"
    assert incident["validated_response"] == "Verified report attestation satisfied all criteria and response actions."


def test_dispute_window_holds_funds_until_release(
    direct_vm, direct_deploy, direct_alice, direct_bob
):
    """Funds stay locked during dispute window — creator cannot claim early."""
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
        "The release, source tree, and setup instructions are all linked.",
    )
    direct_vm.mock_web(
        r".*example\.com/proof.*",
        {"status": 200, "body": "<html>Public alpha release</html>"},
    )
    direct_vm.mock_llm(
        r".*independent grant milestone auditor.*",
        json.dumps({"verdict": "APPROVED", "score": 90, "summary": "Meets all criteria.", "findings": ["A", "B"]}),
    )
    contract.evaluate_milestone(project_id, milestone_id)

    milestone = contract.get_milestones(project_id)[0]
    assert milestone.status == "APPROVED_PENDING"
    assert milestone.released is False

    # Creator cannot claim — funds not yet in claimable
    profile = contract.get_profile(address_hex(direct_alice))
    assert profile["claimable"] == 0

    # Cannot release before window closes
    with direct_vm.expect_revert("Dispute window has not closed"):
        contract.release_approved_milestone(project_id, milestone_id)


def test_milestone_coverage_gate_blocks_activation(
    direct_vm, direct_deploy, direct_alice, direct_bob
):
    """Project stays in FUNDING if milestone budget doesn't cover the goal."""
    contract = deploy_as(direct_vm, direct_deploy, direct_alice)
    project_id = contract.create_project(
        "Under-covered project",
        "Test",
        "A project with milestones that do not cover the full funding goal.",
        DESCRIPTION,
        "https://github.com/genlayerlabs",
        "",
        2 * GOAL,
        FUTURE,
        "Initial tranche",
        2 * GOAL,
        FUTURE - 86_400,
    )
    # Only add a milestone for half the goal
    contract.add_milestone(
        project_id,
        "Partial milestone",
        "This milestone only covers half the funding goal with verifiable output.",
        GOAL,
        FUTURE - 43_200,
    )

    direct_vm.sender = direct_bob
    direct_vm.value = 2 * GOAL
    contract.fund_project(project_id)
    direct_vm.value = 0

    project = contract.get_project(project_id)
    assert project.status == "FUNDING"
    assert project.funded_amount == 2 * GOAL
    assert project.milestone_budget == GOAL

    # Adding the remaining milestone coverage should activate
    direct_vm.sender = direct_alice
    contract.add_milestone(
        project_id,
        "Remaining milestone",
        "This second milestone covers the remaining half of the funding goal with deliverables.",
        GOAL,
        FUTURE - 21_600,
    )
    project = contract.get_project(project_id)
    assert project.status == "ACTIVE"


def test_backer_refund_after_deadline(
    direct_vm, direct_deploy, direct_alice, direct_bob
):
    """Backers can claim proportional refund after deadline with unreleased funds."""
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
    assert project.status == "ACTIVE"

    # Warp past deadline — creator never submitted evidence
    direct_vm.warp(datetime.fromtimestamp(FUTURE + 1, timezone.utc).isoformat())

    # Bob claims refund — full amount since nothing was released
    direct_vm.sender = direct_bob
    contract.claim_refund(project_id)

    profile = contract.get_profile(address_hex(direct_bob))
    assert profile["claimable"] == GOAL

    # Cannot double-claim
    with direct_vm.expect_revert("Refund already claimed"):
        contract.claim_refund(project_id)

    # Bob withdraws the refund
    contract.claim()
    profile = contract.get_profile(address_hex(direct_bob))
    assert profile["claimable"] == 0

