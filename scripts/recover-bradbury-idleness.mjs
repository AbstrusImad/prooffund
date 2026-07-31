import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { createAccount, createClient } from "genlayer-js";
import { testnetBradbury } from "genlayer-js/chains";

const txId = process.argv[2];
if (!/^0x[0-9a-fA-F]{64}$/.test(txId ?? "")) {
  throw new Error("Usage: node scripts/recover-bradbury-idleness.mjs <tx-id>");
}
const env = readFileSync(resolve(process.cwd(), "../.env"), "utf8");
const key = env
  .split(/\r?\n/)
  .find((line) => line.startsWith("GENLAYER_PRIVATE_KEY_0="))
  ?.slice("GENLAYER_PRIVATE_KEY_0=".length)
  .trim();
if (!key) throw new Error("GENLAYER_PRIVATE_KEY_0 is missing");

const account = createAccount(key);
const client = createClient({ chain: testnetBradbury, account });
const processHash = await client.sendTransaction({
  account,
  to: testnetBradbury.consensusMainContract.address,
  data: `0xc7e6e766${txId.slice(2)}`,
  value: 0n,
});
console.log(`Idleness processing submitted: ${processHash}`);
await new Promise((resolveDelay) => setTimeout(resolveDelay, 5_000));
const finalizationHash = await client.finalizeIdlenessTxs({ txIds: [txId] });
console.log(`Idleness finalization submitted: ${finalizationHash}`);
