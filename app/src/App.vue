<script setup>
import { computed, onMounted, ref } from "vue";
import { RouterLink, RouterView } from "vue-router";
import {
  Check,
  ExternalLink,
  RefreshCw,
  Wallet,
  X,
} from "lucide-vue-next";
import { useProofFund } from "./stores/proofFund";
import { contractAddress, explorerUrl } from "./services/genlayer";
import ProofLanding from "./components/ProofLanding.vue";

const {
  state,
  isConnected,
  walletLabel,
  connect,
  restoreWallet,
  watchWallet,
  refresh,
  dismissTransaction,
} = useProofFund();

const authReady = ref(false);
const connecting = ref(false);
const refreshing = ref(false);
const transactionPending = computed(() =>
  ["AWAITING_SIGNATURE", "CONSENSUS"].includes(state.transaction?.status),
);

onMounted(async () => {
  watchWallet();
  await restoreWallet();
  await refresh();
  authReady.value = true;
});

const connectSafely = async () => {
  connecting.value = true;
  try {
    await connect();
  } catch (error) {
    console.error(error);
  } finally {
    connecting.value = false;
  }
};

const refreshSafely = async () => {
  refreshing.value = true;
  try {
    await refresh();
  } finally {
    refreshing.value = false;
  }
};
</script>

<template>
  <div v-if="!authReady" class="proof-auth-loader">
    <div class="auth-current"><i /><i /><i /></div>
    <strong>READING THE PUBLIC LEDGER</strong>
  </div>

  <ProofLanding
    v-else-if="!isConnected"
    :connecting="connecting"
    :error="state.error"
    :dashboard="state.dashboard"
    :project-count="state.projects.length"
    @connect="connectSafely"
  />

  <div v-else class="app-shell proof-app-enter">
    <div class="flow-brand" aria-label="ProofFund">
      <span>PF</span>
      <strong>PROOF<br />FUND</strong>
    </div>

    <nav class="route-current" aria-label="Primary navigation">
      <RouterLink to="/"><span>01</span>FLOW</RouterLink>
      <RouterLink to="/projects/new"><span>02</span>SOURCE</RouterLink>
      <RouterLink to="/governance"><span>03</span>VOTE</RouterLink>
      <RouterLink to="/profile"><span>04</span>CLAIM</RouterLink>
    </nav>

    <div class="network-valves">
      <a
        :href="explorerUrl"
        target="_blank"
        rel="noreferrer"
        title="Open Bradbury explorer"
      >
        <i />
        <span>BRADBURY</span>
        <ExternalLink :size="14" />
      </a>
      <button type="button" :class="{ spinning: refreshing }" title="Refresh live data" @click="refreshSafely">
        <RefreshCw :size="16" />
      </button>
      <button type="button" title="Reconnect wallet" @click="connectSafely">
        <Wallet :size="16" />
        <span>{{ walletLabel }}</span>
      </button>
    </div>

    <main class="flow-stage">
      <div v-if="!contractAddress" class="configuration-alert">
        CONTRACT SOURCE IS CLOSED
      </div>
      <RouterView />
    </main>

    <aside
      v-if="state.transaction"
      class="capital-current"
      :class="{
        pending: transactionPending,
        accepted: state.transaction.status === 'ACCEPTED',
        failed: ['FAILED', 'EXECUTION_REJECTED'].includes(state.transaction.status),
      }"
      aria-live="polite"
    >
      <div class="current-pipe" aria-hidden="true">
        <span v-for="index in 7" :key="index" />
      </div>
      <div class="current-stage">
        <small>ACTIVE CAPITAL CURRENT</small>
        <strong>{{ state.transaction.label }}</strong>
      </div>
      <div class="current-result">
        <span class="current-status">
          <i v-if="transactionPending" />
          <Check v-else-if="state.transaction.status === 'ACCEPTED'" :size="16" />
          <X v-else :size="16" />
          {{ state.transaction.status.replaceAll("_", " ") }}
        </span>
        <p>{{ state.transaction.message }}</p>
        <b v-if="state.transaction.error">{{ state.transaction.error }}</b>
        <a
          v-if="state.transaction.hash"
          :href="`${explorerUrl}/tx/${state.transaction.hash}`"
          target="_blank"
          rel="noreferrer"
        >
          {{ state.transaction.hash.slice(0, 12) }}...{{ state.transaction.hash.slice(-8) }}
          <ExternalLink :size="12" />
        </a>
      </div>
      <button
        v-if="!transactionPending"
        class="current-close"
        type="button"
        title="Dismiss transaction result"
        @click="dismissTransaction"
      >
        <X :size="18" />
      </button>
    </aside>
  </div>
</template>
