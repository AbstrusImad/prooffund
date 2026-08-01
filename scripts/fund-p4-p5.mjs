import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { createAccount, createClient } from "genlayer-js";
import { studionet } from "genlayer-js/chains";
import { TransactionStatus } from "genlayer-js/types";

const CONTRACT = "0x8bf3c1C1D1E7f5ba14C6Ab9C58486b92A03ECED4";
const env = readFileSync(resolve(process.cwd(), "../.env"), "utf8");
const key = env.split(/\r?\n/).find((l) => l.startsWith("GENLAYER_PRIVATE_KEY_0="))?.split("=")[1]?.trim();

const account = createAccount(key);
const client = createClient({ chain: studionet, account });

const projects = [
  { id: "PF-0004", amount: 6000000000000000000n },
  { id: "PF-0005", amount: 5000000000000000000n },
];

for (const { id, amount } of projects) {
  console.log(`Funding ${id}...`);
  const hash = await client.writeContract({
    address: CONTRACT,
    functionName: "fund_project",
    args: [id],
    value: amount,
  });
  await client.waitForTransactionReceipt({ hash, status: TransactionStatus.ACCEPTED, retries: 30, interval: 2000 });
  console.log(`✓ ${id} funded`);
}
