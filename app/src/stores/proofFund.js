import { computed, reactive, readonly } from "vue";
import {
  connectWallet,
  formatError,
  readContract,
  writeContract,
} from "../services/genlayer";

const state = reactive({
  wallet: "",
  client: null,
  projects: [],
  proposals: [],
  proposalVotes: {},
  dashboard: null,
  profile: null,
  loading: false,
  error: "",
  transaction: null,
});

const shortAddress = (address) =>
  address ? `${address.slice(0, 6)}...${address.slice(-4)}` : "";

async function refresh() {
  state.loading = true;
  state.error = "";
  try {
    const [dashboard, projects, proposals] = await Promise.all([
      readContract("get_dashboard"),
      readContract("get_projects"),
      readContract("get_governance"),
    ]);
    state.dashboard = dashboard;
    state.projects = Array.isArray(projects) ? projects : [];
    state.proposals = Array.isArray(proposals) ? proposals : [];
    if (state.wallet) {
      const [profile, votes] = await Promise.all([
        readContract("get_profile", [state.wallet]),
        Promise.all(
          state.proposals.map(async (proposal) => [
            proposal.id,
            await readContract("get_vote", [proposal.id, state.wallet]),
          ]),
        ),
      ]);
      state.profile = profile;
      state.proposalVotes = Object.fromEntries(votes);
    } else {
      state.proposalVotes = {};
    }
  } catch (error) {
    state.error = error.message || "Unable to read Bradbury.";
  } finally {
    state.loading = false;
  }
}

async function connect() {
  state.error = "";
  const session = await connectWallet();
  if (!session) return;
  state.wallet = session.address;
  state.client = session.client;
  localStorage.setItem("prooffund.wallet.connected", "1");
  await refresh();
}

async function restoreWallet() {
  if (localStorage.getItem("prooffund.wallet.connected") !== "1") return false;
  try {
    const session = await connectWallet({ silent: true });
    if (!session) {
      localStorage.removeItem("prooffund.wallet.connected");
      return false;
    }
    state.wallet = session.address;
    state.client = session.client;
    return true;
  } catch {
    return false;
  }
}

function watchWallet() {
  if (!window.ethereum?.on) return;
  window.ethereum.on("accountsChanged", async (accounts) => {
    if (!accounts?.length) {
      state.wallet = "";
      state.client = null;
      state.profile = null;
      state.proposalVotes = {};
      localStorage.removeItem("prooffund.wallet.connected");
      return;
    }
    const session = await connectWallet({ silent: true });
    if (session) {
      state.wallet = session.address;
      state.client = session.client;
      await refresh();
    }
  });
}

async function transact(
  label,
  functionName,
  args = [],
  value = 0n,
  options = {},
) {
  if (
    state.transaction &&
    ["AWAITING_SIGNATURE", "CONSENSUS"].includes(state.transaction.status)
  ) {
    throw new Error(
      `${state.transaction.label} is already moving through Bradbury consensus.`,
    );
  }
  state.error = "";
  state.transaction = {
    label,
    status: "AWAITING_SIGNATURE",
    hash: "",
    message: "Approve the request in your wallet.",
    error: "",
    result: null,
  };
  try {
    const result = await writeContract(
      state.client,
      functionName,
      args,
      value,
      (hash) => {
        state.transaction.hash = hash;
        state.transaction.status = "CONSENSUS";
        state.transaction.message = "Bradbury validators are processing the transaction.";
      },
    );
    state.transaction.status = "ACCEPTED";
    state.transaction.result = result.returnValue;
    state.transaction.message =
      typeof options.successMessage === "function"
        ? options.successMessage(result)
        : options.successMessage || "Transaction accepted and state updated.";
    await refresh();
    return result;
  } catch (error) {
    if (!state.transaction.hash && error?.hash) state.transaction.hash = error.hash;
    const executionRejected =
      error?.receipt?.txExecutionResultName === "FINISHED_WITH_ERROR";
    state.transaction.status = executionRejected ? "EXECUTION_REJECTED" : "FAILED";
    state.transaction.message = executionRejected
      ? "Consensus accepted the receipt, but contract execution was rejected."
      : "The transaction was not applied.";
    state.transaction.error = formatError(error);
    throw error;
  }
}

async function loadProject(projectId) {
  const [project, milestones, disputes, tranches, proposals] = await Promise.all([
    readContract("get_project", [projectId]),
    readContract("get_milestones", [projectId]),
    readContract("get_disputes", [projectId]),
    readContract("get_tranches", [projectId]),
    readContract("get_proposals", [projectId]),
  ]);
  const contribution = state.wallet
    ? await readContract("get_contribution", [projectId, state.wallet])
    : 0;
  const votes = {};
  if (state.wallet) {
    await Promise.all(
      proposals.map(async (proposal) => {
        votes[proposal.id] = await readContract("get_vote", [
          proposal.id,
          state.wallet,
        ]);
      }),
    );
  }
  return { project, milestones, disputes, tranches, proposals, contribution, votes };
}

function dismissTransaction() {
  state.transaction = null;
}

export function useProofFund() {
  return {
    state: readonly(state),
    isConnected: computed(() => Boolean(state.wallet)),
    walletLabel: computed(() => shortAddress(state.wallet)),
    connect,
    restoreWallet,
    watchWallet,
    refresh,
    transact,
    loadProject,
    dismissTransaction,
  };
}
