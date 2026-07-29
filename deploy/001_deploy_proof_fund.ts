import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import {
  TransactionStatus,
  type GenLayerClient,
  type TransactionHash,
} from "genlayer-js/types";

export default async function main(client: GenLayerClient<any>) {
  const contractCode = new Uint8Array(
    readFileSync(resolve(process.cwd(), "contracts/proof_fund.py")),
  );

  await client.initializeConsensusSmartContract();
  const hash = (await client.deployContract({
    code: contractCode,
    args: [],
  })) as TransactionHash;

  const receipt = await client.waitForTransactionReceipt({
    hash,
    status: TransactionStatus.FINALIZED,
    retries: 240,
    interval: 3_000,
  });

  const leader = receipt.consensus_data?.leader_receipt?.[0];
  if (leader?.execution_result !== "SUCCESS") {
    throw new Error(`ProofFund deployment failed: ${JSON.stringify(receipt)}`);
  }

  const address = receipt.data?.contract_address;
  if (!address) {
    throw new Error(`Deployment succeeded without contract address: ${hash}`);
  }

  console.log(JSON.stringify({ address, transactionHash: hash }, null, 2));
  return address;
}
