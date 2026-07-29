<script setup>
import { onMounted } from "vue";
import { RouterLink, RouterView } from "vue-router";
import {
  CircleDollarSign,
  CheckCircle2,
  Compass,
  ExternalLink,
  AlertTriangle,
  LayoutDashboard,
  LoaderCircle,
  Landmark,
  Plus,
  UserRound,
  Wallet,
  X,
} from "lucide-vue-next";
import { useProofFund } from "./stores/proofFund";
import { contractAddress, explorerUrl } from "./services/genlayer";

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

onMounted(async () => {
  watchWallet();
  await restoreWallet();
  await refresh();
});

const connectSafely = async () => {
  try {
    await connect();
  } catch (error) {
    console.error(error);
  }
};
</script>

<template>
  <div class="app-shell">
    <header class="topbar">
      <RouterLink class="brand" to="/" aria-label="ProofFund home">
        <span class="brand-mark"><CircleDollarSign :size="21" /></span>
        <span>ProofFund</span>
      </RouterLink>

      <nav class="desktop-nav" aria-label="Primary navigation">
        <RouterLink to="/"><LayoutDashboard :size="17" /> Overview</RouterLink>
        <RouterLink to="/projects/new"><Plus :size="17" /> Launch</RouterLink>
        <RouterLink to="/governance"><Landmark :size="17" /> Governance</RouterLink>
        <RouterLink to="/profile"><UserRound :size="17" /> Portfolio</RouterLink>
      </nav>

      <div class="topbar-actions">
        <a
          class="network-pill"
          :href="explorerUrl"
          target="_blank"
          rel="noreferrer"
          title="Open StudioNet explorer"
        >
          <span class="live-dot"></span>
          StudioNet
          <ExternalLink :size="13" />
        </a>
        <button class="wallet-button" type="button" @click="connectSafely">
          <Wallet :size="17" />
          <span>{{ isConnected ? walletLabel : "Connect wallet" }}</span>
        </button>
      </div>
    </header>

    <main>
      <div v-if="!contractAddress" class="configuration-alert">
        Contract deployment is not configured yet.
      </div>
      <RouterView />
    </main>

    <nav class="mobile-nav" aria-label="Mobile navigation">
      <RouterLink to="/"><LayoutDashboard :size="19" /><span>Overview</span></RouterLink>
      <RouterLink to="/projects/new"><Plus :size="19" /><span>Launch</span></RouterLink>
      <RouterLink to="/governance"><Landmark :size="19" /><span>Governance</span></RouterLink>
      <RouterLink to="/profile"><UserRound :size="19" /><span>Portfolio</span></RouterLink>
    </nav>

    <aside v-if="state.transaction" class="transaction-dock" aria-live="polite">
      <div class="transaction-icon" :class="state.transaction.status.toLowerCase()">
        <CheckCircle2 v-if="state.transaction.status === 'ACCEPTED'" :size="20" />
        <AlertTriangle v-else-if="state.transaction.status === 'FAILED'" :size="20" />
        <LoaderCircle v-else :size="20" />
      </div>
      <div>
        <strong>{{ state.transaction.label }}</strong>
        <span>{{ state.transaction.status.replaceAll("_", " ") }}</span>
        <p>{{ state.transaction.message }}</p>
        <small v-if="state.transaction.error">{{ state.transaction.error }}</small>
        <a
          v-if="state.transaction.hash"
          :href="`${explorerUrl}/tx/${state.transaction.hash}`"
          target="_blank"
          rel="noreferrer"
        >
          {{ state.transaction.hash.slice(0, 10) }}...{{ state.transaction.hash.slice(-6) }}
          <ExternalLink :size="12" />
        </a>
      </div>
      <button
        type="button"
        title="Dismiss transaction"
        @click="dismissTransaction"
      >
        <X :size="17" />
      </button>
    </aside>
  </div>
</template>
