import { readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { createAccount, createClient } from "genlayer-js";
import { studionet } from "genlayer-js/chains";

const root = process.cwd();
const deployment = JSON.parse(
  readFileSync(resolve(root, "deployments/studionet.json"), "utf8"),
);
const env = readFileSync(resolve(root, "../.env"), "utf8");
const key = env
  .split(/\r?\n/)
  .find((line) => line.startsWith("GENLAYER_PRIVATE_KEY_0="))
  ?.split("=")[1]
  ?.trim();
if (!key) throw new Error("GENLAYER_PRIVATE_KEY_0 is missing");

const account = createAccount(key);
const client = createClient({ chain: studionet });
const read = (functionName, args = []) =>
  client.readContract({
    address: deployment.address,
    functionName,
    args,
    jsonSafeReturn: true,
  });

const dashboard = await read("get_dashboard");
const projects = await read("get_projects");
const milestones = [];
const disputes = [];
const tranches = [];
const proposals = [];
for (const project of projects) {
  milestones.push(...(await read("get_milestones", [project.id])));
  disputes.push(...(await read("get_disputes", [project.id])));
  tranches.push(...(await read("get_tranches", [project.id])));
  proposals.push(...(await read("get_proposals", [project.id])));
}

const addresses = new Set([account.address.toLowerCase()]);
for (const project of projects) addresses.add(project.creator.toLowerCase());
for (const dispute of disputes) addresses.add(dispute.challenger.toLowerCase());
for (const proposal of proposals) addresses.add(proposal.proposer.toLowerCase());

const accounts = [];
for (const address of addresses) {
  const profile = await read("get_profile", [address]);
  const contributions = {};
  const votes = {};
  for (const project of projects) {
    contributions[project.id] = await read("get_contribution", [
      project.id,
      address,
    ]);
  }
  for (const proposal of proposals) {
    votes[proposal.id] = await read("get_vote", [proposal.id, address]);
  }
  accounts.push({ address, profile, contributions, votes });
}

for (const tranche of tranches) {
  if (Number(tranche.backer_count) > 1) {
    throw new Error(`Unexpected multi-backer tranche ${tranche.id}`);
  }
}

const state = {
  verifiedAt: new Date().toISOString(),
  network: "StudioNet",
  contractAddress: deployment.address,
  deploymentTransaction: deployment.deploymentTransaction,
  fundingAccount: account.address,
  dashboard,
  projects,
  milestones,
  disputes,
  tranches,
  proposals,
  accounts,
};
writeFileSync(
  resolve(root, "deployments/live-state-studionet.json"),
  `${JSON.stringify(state, null, 2)}\n`,
);
console.log(
  JSON.stringify(
    {
      verifiedAt: state.verifiedAt,
      dashboard,
      records: {
        projects: projects.length,
        milestones: milestones.length,
        disputes: disputes.length,
        tranches: tranches.length,
        proposals: proposals.length,
        accounts: accounts.length,
      },
    },
    null,
    2,
  ),
);
