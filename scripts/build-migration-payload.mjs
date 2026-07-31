import { createHash } from "node:crypto";
import { readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";

const root = process.cwd();
const state = JSON.parse(
  readFileSync(resolve(root, "deployments/live-state-studionet.json"), "utf8"),
);
const fundingAccount = state.fundingAccount.toLowerCase();
const contributions = [];
const votes = [];
const backedProjects = [];
for (const account of state.accounts) {
  for (const [projectId, amount] of Object.entries(account.contributions)) {
    if (BigInt(amount) > 0n) {
      contributions.push({ account: account.address, project_id: projectId, amount });
      backedProjects.push({ account: account.address, project_id: projectId });
    }
  }
  for (const [proposalId, vote] of Object.entries(account.votes)) {
    if (vote) votes.push({ account: account.address, proposal_id: proposalId, vote });
  }
}
const backedTranches = state.tranches
  .filter((tranche) => Number(tranche.backer_count) > 0)
  .map((tranche) => ({
    account: fundingAccount,
    tranche_id: tranche.id,
  }));

const migration = {
  source: {
    network: "StudioNet",
    contract: state.contractAddress,
    deployment_transaction: state.deploymentTransaction,
    verified_at: state.verifiedAt,
  },
  dashboard: state.dashboard,
  projects: state.projects,
  milestones: state.milestones,
  disputes: state.disputes,
  tranches: state.tranches,
  proposals: state.proposals,
  accounts: state.accounts.map(({ address, profile }) => ({ address, profile })),
  contributions,
  votes,
  backed_projects: backedProjects,
  backed_tranches: backedTranches,
};
const payload = JSON.stringify(migration);
const snapshotHash = createHash("sha256").update(payload).digest("hex");
const batchDefinitions = [
  ["projects", 0, migration.projects],
  ["milestones", 0, migration.milestones],
  ["disputes", 0, migration.disputes],
  ["tranches", 0, migration.tranches.slice(0, 9)],
  ["tranches", 1, migration.tranches.slice(9, 18)],
  ["tranches", 2, migration.tranches.slice(18, 27)],
  ["proposals", 0, migration.proposals],
  ["accounts", 0, migration.accounts],
  ["ledger", 0, [...migration.contributions, ...migration.votes]],
  ["backing", 0, [...migration.backed_projects, ...migration.backed_tranches]],
];
const batches = batchDefinitions.map(([kind, index, records]) => {
  const batch = { snapshot_hash: snapshotHash, kind, index, records };
  const compact = JSON.stringify(batch);
  return {
    kind,
    index,
    hash: createHash("sha256").update(compact).digest("hex"),
    payload: compact,
    records: records.length,
    payloadBytes: Buffer.byteLength(compact),
  };
});
const begin = {
  snapshot_hash: snapshotHash,
  source: migration.source,
  dashboard: migration.dashboard,
};
const beginPayload = JSON.stringify(begin);
const beginHash = createHash("sha256").update(beginPayload).digest("hex");
const reviewHistory = {
  snapshot_hash: snapshotHash,
  milestones: migration.milestones.filter((item) => item.status === "DISPUTED"),
  disputes: migration.disputes,
};
const reviewHistoryPayload = JSON.stringify(reviewHistory);
const reviewHistoryHash = createHash("sha256")
  .update(reviewHistoryPayload)
  .digest("hex");
const counts = Object.fromEntries(
  [
    "projects",
    "milestones",
    "disputes",
    "tranches",
    "proposals",
    "accounts",
    "contributions",
    "votes",
    "backed_projects",
    "backed_tranches",
  ].map((key) => [key, migration[key].length]),
);
const manifest = {
  snapshotHash,
  payloadBytes: Buffer.byteLength(payload),
  backingWei: String(state.dashboard.contract_balance),
  backingGen: "57.3",
  migratedRecords: Object.values(counts).reduce((sum, count) => sum + count, 0),
  counts,
  source: migration.source,
  begin: {
    hash: beginHash,
    payload: beginPayload,
    payloadBytes: Buffer.byteLength(beginPayload),
  },
  batches,
  reviewHistory: {
    hash: reviewHistoryHash,
    payload: reviewHistoryPayload,
    payloadBytes: Buffer.byteLength(reviewHistoryPayload),
    milestones: reviewHistory.milestones.length,
    disputes: reviewHistory.disputes.length,
  },
};
writeFileSync(
  resolve(root, "deployments/migration-payload.json"),
  `${JSON.stringify(migration, null, 2)}\n`,
);
writeFileSync(
  resolve(root, "deployments/migration-manifest.json"),
  `${JSON.stringify(manifest, null, 2)}\n`,
);
console.log(JSON.stringify(manifest, null, 2));
