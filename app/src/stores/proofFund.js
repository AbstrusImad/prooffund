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
  refreshing: false,
  initialized: false,
  error: "",
  transaction: null,
});

const shortAddress = (address) =>
  address ? `${address.slice(0, 6)}...${address.slice(-4)}` : "";

let refreshPromise = null;

async function refresh({ initial = false } = {}) {
  if (refreshPromise) {
    try {
      await refreshPromise;
    } catch {
      // The original refresh owns the user-facing error state.
    }
    return;
  }
  const blocking = initial && !state.initialized;
  state.loading = blocking;
  state.refreshing = !blocking;
  state.error = "";
  refreshPromise = (async () => {
    const [dashboard, projects, proposals] = await Promise.all([
      readContract("get_dashboard"),
      readContract("get_projects"),
      readContract("get_governance"),
    ]);
    const nextProjects = Array.isArray(projects) ? projects : [];
    const nextProposals = Array.isArray(proposals) ? proposals : [];
    if (JSON.stringify(state.dashboard) !== JSON.stringify(dashboard)) {
      state.dashboard = dashboard;
    }
    if (JSON.stringify(state.projects) !== JSON.stringify(nextProjects)) {
      state.projects = nextProjects;
    }
    if (JSON.stringify(state.proposals) !== JSON.stringify(nextProposals)) {
      state.proposals = nextProposals;
    }
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
      const nextVotes = Object.fromEntries(votes);
      if (JSON.stringify(state.profile) !== JSON.stringify(profile)) {
        state.profile = profile;
      }
      if (JSON.stringify(state.proposalVotes) !== JSON.stringify(nextVotes)) {
        state.proposalVotes = nextVotes;
      }
    } else {
      state.proposalVotes = {};
    }
    state.initialized = true;
  })();
  try {
    await refreshPromise;
  } catch (error) {
    state.error = error.message || "Unable to read StudioNet.";
  } finally {
    state.loading = false;
    state.refreshing = false;
    refreshPromise = null;
  }
}

async function connect() {
  state.error = "";
  try {
    const session = await connectWallet();
    if (!session) {
      state.error = "Select an account in your browser wallet to enter ProofFund.";
      return;
    }
    state.wallet = session.address;
    state.client = session.client;
    localStorage.setItem("prooffund.wallet.connected", "1");
    await refresh();
  } catch (error) {
    state.error = formatError(error);
    throw error;
  }
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
      `${state.transaction.label} is already moving through StudioNet consensus.`,
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
        state.transaction.message = "StudioNet validators are processing the transaction.";
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
  const refund = state.wallet
    ? await readContract("get_refund", [projectId, state.wallet])
    : null;
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
  return {
    project,
    milestones,
    disputes,
    tranches,
    proposals,
    contribution,
    refund,
    votes,
  };
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
