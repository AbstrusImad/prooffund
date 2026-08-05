import assert from "node:assert/strict";
import { readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { createClient } from "genlayer-js";
import { studionet } from "genlayer-js/chains";

const root = process.cwd();
const deployment = JSON.parse(
  readFileSync(resolve(root, "deployments/studionet.json"), "utf8"),
);
const client = createClient({ chain: studionet });
const read = (functionName, args = []) =>
  client.readContract({
    address: deployment.contractAddress,
    functionName,
    args,
    jsonSafeReturn: true,
  });

const projects = await read("get_projects");
const dashboard = await read("get_dashboard");
const governance = await read("get_governance");
assert.equal(projects.length, 9, "expected 9 StudioNet projects");
assert.equal(dashboard.project_count, 9);
assert.equal(dashboard.total_funded, "9000000000000000000");
assert.equal(dashboard.contract_balance, "9000000000000000000");
assert.equal(dashboard.total_released, 0);
assert.equal(dashboard.total_refunded, 0);
assert.equal(dashboard.total_disputes, 0);
assert.equal(dashboard.total_proposals, 3);
assert.equal(dashboard.open_proposals, 3);
assert.equal(dashboard.funded_tranches, 2);
assert.equal(governance.length, 3);
assert.equal(projects[0].status, "ACTIVE");
assert.equal(projects[0].funded_amount, "3000000000000000000");

let milestoneCount = 0;
let trancheCount = 0;
for (const project of projects) {
  const milestones = await read("get_milestones", [project.id]);
  const tranches = await read("get_tranches", [project.id]);
  assert.ok(milestones.length >= 1, `${project.id} has no milestone`);
  assert.equal(project.milestone_budget, project.funding_goal);
  milestoneCount += milestones.length;
  trancheCount += tranches.length;
}
assert.equal(milestoneCount, 9);
assert.equal(trancheCount, 10);

const profile = await read("get_profile", [deployment.deployer]);
assert.equal(profile.projects_created, 9);
assert.equal(profile.projects_backed, 7);
assert.equal(profile.total_funded, "9000000000000000000");
assert.equal(profile.proposals_created, 3);
assert.equal(profile.votes_cast, 3);
assert.equal(deployment.seed.status, "ACCEPTED");
assert.equal(deployment.seed.transactionCount, 33);
assert.equal(deployment.seed.totalFundedWei, "9000000000000000000");

const verification = {
  verifiedAt: new Date().toISOString(),
  network: "StudioNet",
  chainId: 61999,
  contractAddress: deployment.contractAddress,
  deploymentTransaction: deployment.transactionHash,
  transactionCount: deployment.seed.transactionCount,
  account0Only: true,
  fundingLimitGen: 9,
  exactStateMatch: true,
  counts: { projects: 9, milestones: milestoneCount, tranches: trancheCount, proposals: 3 },
  dashboard,
};
writeFileSync(
  resolve(root, "deployments/live-state-studionet.json"),
  `${JSON.stringify(verification, null, 2)}\n`,
);
console.log(JSON.stringify(verification, null, 2));
