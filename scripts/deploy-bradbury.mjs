import { createHash } from "node:crypto";
import { readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { createAccount, createClient } from "genlayer-js";
import { testnetBradbury } from "genlayer-js/chains";
import { ExecutionResult, TransactionStatus } from "genlayer-js/types";

const root = process.cwd();
const env = readFileSync(resolve(root, "../.env"), "utf8");
const key = env
  .split(/\r?\n/)
  .find((line) => line.startsWith("GENLAYER_PRIVATE_KEY_0="))
  ?.split("=")[1]
  ?.trim();
if (!key) throw new Error("GENLAYER_PRIVATE_KEY_0 is missing");

const account = createAccount(key);
const client = createClient({ chain: testnetBradbury, account });
const source = readFileSync(resolve(root, "contracts/proof_fund.py"), "utf8");
const code = new TextEncoder().encode(source);
const contractSha256 = createHash("sha256").update(code).digest("hex");
const hash = await client.deployContract({ code, args: [], leaderOnly: true });
console.log(`Bradbury deployment submitted: ${hash}`);
const receipt = await client.waitForTransactionReceipt({
  hash,
  status: TransactionStatus.ACCEPTED,
  retries: 360,
  interval: 3_000,
});
const leader = receipt.consensus_data?.leader_receipt?.[0];
const succeeded =
  receipt.txExecutionResultName === ExecutionResult.FINISHED_WITH_RETURN ||
  leader?.execution_result === "SUCCESS";
const contractAddress =
  receipt.data?.contractAddress ||
  receipt.data?.contract_address ||
  receipt.txDataDecoded?.contractAddress;
if (!succeeded || !contractAddress) {
  throw new Error(
    JSON.stringify(receipt, (_key, value) =>
      typeof value === "bigint" ? value.toString() : value,
    ),
  );
}

const sourceState = JSON.parse(
  readFileSync(resolve(root, "deployments/live-state-studionet.json"), "utf8"),
);
const deployment = {
  network: "testnet-bradbury",
  chainId: 4221,
  contractAddress,
  transactionHash: hash,
  deployer: account.address,
  publisher: "AbstrusImad",
  explorer: "https://explorer-bradbury.genlayer.com",
  status: "ACCEPTED",
  executionResult: "FINISHED_WITH_RETURN",
  deployedAt: new Date().toISOString(),
  contractSha256,
  migration: {
    sourceNetwork: "StudioNet",
    sourceContract: sourceState.contractAddress,
    sourceVerifiedAt: sourceState.verifiedAt,
    supersedes: {
      contractAddress: "0xa52303D93A4271Acb82E215d50038306d62717f7",
      deploymentTransaction:
        "0xe2892c12f5815656a24efcbb2b739b3f6f249f25a5b6645f71f930df62f54d5e",
      timedOutImport:
        "0xfa5424d8119dc023e93ba4c2bc007e4e4f6fc41add252ae43b12e688da8f74cb",
    },
  },
};
writeFileSync(
  resolve(root, "deployments/bradbury.json"),
  `${JSON.stringify(deployment, null, 2)}\n`,
);
writeFileSync(
  resolve(root, "app/.env.production"),
  `VITE_CONTRACT_ADDRESS=${contractAddress}\nVITE_EXPLORER_URL=https://explorer-bradbury.genlayer.com\n`,
);
console.log(JSON.stringify(deployment, null, 2));
