import { readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { createAccount, createClient } from "genlayer-js";
import { testnetBradbury } from "genlayer-js/chains";

const root = process.cwd();
const deploymentPath = resolve(root, "deployments/bradbury.json");
const deployment = JSON.parse(readFileSync(deploymentPath, "utf8"));
const env = readFileSync(resolve(root, "../.env"), "utf8");
const key = env
  .split(/\r?\n/)
  .find((line) => line.startsWith("GENLAYER_PRIVATE_KEY_0="))
  ?.slice("GENLAYER_PRIVATE_KEY_0=".length)
  .trim();
if (!key) throw new Error("GENLAYER_PRIVATE_KEY_0 is missing");

const client = createClient({
  chain: testnetBradbury,
  account: createAccount(key),
});
deployment.finalization ??= {};
const transactions = [
  ["deployment", deployment.transactionHash],
  ...Object.entries(deployment.seed?.transactions ?? {}).map(([stage, item]) => [
    stage,
    item.hash,
  ]),
];

let finalized = 0;
for (const [stage, txId] of transactions) {
  if (deployment.finalization[stage]?.status === "FINALIZED") continue;
  try {
    await client.finalizeTransaction({ txId });
    deployment.finalization[stage] = {
      txId,
      status: "FINALIZED",
      finalizedAt: new Date().toISOString(),
    };
    finalized += 1;
    console.log(`${stage}: finalized`);
  } catch (error) {
    deployment.finalization[stage] = {
      txId,
      status: "NOT_READY",
      checkedAt: new Date().toISOString(),
      message: String(error?.shortMessage || error?.message || error).slice(0, 300),
    };
    console.log(`${stage}: not ready`);
  }
  writeFileSync(deploymentPath, `${JSON.stringify(deployment, null, 2)}\n`);
}
console.log(`Finalized in this pass: ${finalized}`);
