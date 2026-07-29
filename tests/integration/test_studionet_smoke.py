import time

from gltest import get_contract_factory
from gltest.assertions import tx_execution_succeeded


def test_studionet_project_creation():
    factory = get_contract_factory("ProofFund")
    contract = factory.deploy(args=[])

    receipt = contract.create_project(
        args=[
            "ProofFund StudioNet Verification",
            "Protocol",
            "An on-chain verification project created by the ProofFund integration suite.",
            (
                "This record verifies that project creation, persistent storage, "
                "and public reads execute correctly against the hosted StudioNet runtime."
            ),
            "https://docs.genlayer.com/",
            "",
            10**18,
            int(time.time()) + 30 * 86_400,
            "StudioNet verification tranche",
            10**18,
            int(time.time()) + 15 * 86_400,
        ]
    ).transact()
    assert tx_execution_succeeded(receipt)

    projects = contract.get_projects(args=[]).call()
    assert len(projects) >= 1
    assert projects[-1]["title"] == "ProofFund StudioNet Verification"
