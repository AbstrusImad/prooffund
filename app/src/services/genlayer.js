import { createClient } from "genlayer-js";
import { testnetBradbury } from "genlayer-js/chains";
import { ExecutionResult, TransactionStatus } from "genlayer-js/types";

export const contractAddress = import.meta.env.VITE_CONTRACT_ADDRESS || "";
export const explorerUrl =
  import.meta.env.VITE_EXPLORER_URL || "https://explorer-bradbury.genlayer.com";

const assertContract = () => {
  if (!/^0x[a-fA-F0-9]{40}$/.test(contractAddress)) {
    throw new Error("ProofFund contract address is not configured.");
  }
};

export const publicClient = createClient({ chain: testnetBradbury });

const isNetworkBusy = (error) =>
  String(error?.details || error?.message || error).includes("Server busy");

const retryNetworkBusy = async (operation, attempts = 8) => {
  for (let attempt = 1; attempt <= attempts; attempt += 1) {
    try {
      return await operation();
    } catch (error) {
      if (!isNetworkBusy(error) || attempt === attempts) throw error;
      await new Promise((resolveDelay) => setTimeout(resolveDelay, attempt * 1_000));
    }
  }
};

export async function connectWallet({ silent = false } = {}) {
  if (!window.ethereum) {
    if (silent) return null;
    throw new Error("No browser wallet detected. Install MetaMask to continue.");
  }
  const accounts = await window.ethereum.request({
    method: silent ? "eth_accounts" : "eth_requestAccounts",
  });
  const address = accounts?.[0];
  if (!address) return null;
  const client = createClient({ chain: testnetBradbury, account: address });
  if (!silent) await client.connect("testnetBradbury");
  return { address, client };
}

export async function readContract(functionName, args = []) {
  assertContract();
  return retryNetworkBusy(() =>
    publicClient.readContract({
      address: contractAddress,
      functionName,
      args,
      jsonSafeReturn: true,
    }),
  );
}

const asText = (value) => {
  if (value == null) return "";
  if (typeof value === "string") return value;
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
};

const cleanContractMessage = (value) => {
  let text = asText(value).trim();
  if (!text) return "";
  try {
    const parsed = JSON.parse(text);
    if (typeof parsed === "string") text = parsed;
    else if (parsed?.message) text = asText(parsed.message);
  } catch {
    // GenVM readable payloads are often plain text rather than JSON.
  }
  return text
    .replace(/^\[(EXPECTED|EXTERNAL|TRANSIENT|LLM_ERROR)\]\s*/i, "")
    .replace(/^UserError:\s*/i, "")
    .trim();
};

const leaderReceipt = (receipt) =>
  receipt?.consensus_data?.leader_receipt?.[0] ||
  receipt?.consensusData?.leaderReceipt?.[0] ||
  null;

const decodeGenVmResult = (value) => {
  if (typeof value !== "string" || !value) return "";
  try {
    const normalized = value.replace(/-/g, "+").replace(/_/g, "/");
    const padded = normalized.padEnd(Math.ceil(normalized.length / 4) * 4, "=");
    const bytes = Uint8Array.from(atob(padded), (character) =>
      character.charCodeAt(0),
    );
    if (bytes.length < 2 || ![1, 2, 3].includes(bytes[0])) return "";
    return new TextDecoder().decode(bytes.slice(1));
  } catch {
    return "";
  }
};

export function extractReceiptError(receipt) {
  const leader = leaderReceipt(receipt);
  const decodedOutputs = Object.values(leader?.eq_outputs || {})
    .map(decodeGenVmResult)
    .filter(Boolean);
  const candidates = [
    decodeGenVmResult(leader?.result),
    ...decodedOutputs,
    leader?.genvm_result?.error_description,
    leader?.genvm_result?.raw_error,
    leader?.genvm_result?.stderr,
    leader?.genvmResult?.errorDescription,
    leader?.genvmResult?.rawError,
    leader?.result?.payload?.readable,
    receipt?.error?.message,
    receipt?.error,
    receipt?.txExecutionResultName,
  ];
  for (const candidate of candidates) {
    const message = cleanContractMessage(candidate);
    if (message && message !== "FINISHED_WITH_ERROR") return message;
  }
  return "The contract rejected the transaction.";
}

export function formatError(error) {
  if (!error) return "Unknown transaction error.";
  const candidates = [
    error?.shortMessage,
    error?.details,
    error?.cause?.shortMessage,
    error?.cause?.message,
    error?.message,
    error?.data?.message,
    error,
  ];
  for (const candidate of candidates) {
    const message = cleanContractMessage(candidate);
    if (message && message !== "[object Object]") return message;
  }
  return "The transaction could not be completed.";
}

export function extractReturnValue(receipt) {
  const readable = leaderReceipt(receipt)?.result?.payload?.readable;
  if (readable == null || readable === "null") return null;
  try {
    return JSON.parse(readable);
  } catch {
    return readable;
  }
}

export async function writeContract(
  client,
  functionName,
  args = [],
  value = 0n,
  onSubmitted,
) {
  assertContract();
  if (!client) throw new Error("Connect your wallet before continuing.");

  await client.connect("testnetBradbury");
  const hash = await retryNetworkBusy(() =>
    client.writeContract({
      address: contractAddress,
      functionName,
      args,
      value,
    }),
  );
  onSubmitted?.(hash);

  const receipt = await client.waitForTransactionReceipt({
    hash,
    status: TransactionStatus.ACCEPTED,
    interval: 3_000,
    retries: 100,
  });

  const studioExecution =
    receipt?.consensus_data?.leader_receipt?.[0]?.execution_result ||
    receipt?.consensusData?.leaderReceipt?.[0]?.executionResult;
  const executionSucceeded =
    receipt.txExecutionResultName === ExecutionResult.FINISHED_WITH_RETURN ||
    studioExecution === "SUCCESS";

  if (!executionSucceeded) {
    const error = new Error(extractReceiptError(receipt));
    error.hash = hash;
    error.receipt = receipt;
    throw error;
  }
  return { hash, receipt, returnValue: extractReturnValue(receipt) };
}

export const toWei = (value) => {
  const normalized = String(value || "0").trim();
  if (!/^\d+(\.\d{0,18})?$/.test(normalized)) {
    throw new Error("Enter a valid GEN amount.");
  }
  const [whole, fraction = ""] = normalized.split(".");
  return BigInt(whole) * 10n ** 18n + BigInt((fraction + "0".repeat(18)).slice(0, 18));
};

export const fromWei = (value, precision = 2) => {
  const amount = BigInt(value || 0);
  const whole = amount / 10n ** 18n;
  const fraction = (amount % 10n ** 18n)
    .toString()
    .padStart(18, "0")
    .slice(0, precision)
    .replace(/0+$/, "");
  return fraction ? `${whole}.${fraction}` : whole.toString();
};
