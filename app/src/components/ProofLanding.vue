<script setup>
import {
  ArrowDownRight,
  ExternalLink,
  FileCheck2,
  LoaderCircle,
  Wallet,
} from "lucide-vue-next";
import { contractAddress, explorerUrl, fromWei } from "../services/genlayer";

defineProps({
  connecting: { type: Boolean, default: false },
  error: { type: String, default: "" },
  dashboard: { type: Object, default: null },
  projectCount: { type: Number, default: 0 },
});
defineEmits(["connect"]);
</script>

<template>
  <section class="proof-landing">
    <div class="landing-word word-fund" aria-hidden="true">FUND</div>
    <div class="landing-word word-proof" aria-hidden="true">PROOF</div>
    <div class="landing-word word-release" aria-hidden="true">RELEASE</div>

    <div class="landing-streams" aria-hidden="true">
      <div class="stream stream-a"><i v-for="n in 8" :key="`a${n}`" /></div>
      <div class="stream stream-b"><i v-for="n in 6" :key="`b${n}`" /></div>
      <div class="stream stream-c"><i v-for="n in 7" :key="`c${n}`" /></div>
    </div>

    <header class="landing-index">
      <span class="proof-monogram"><FileCheck2 :size="18" /> PF / 001</span>
      <a :href="explorerUrl" target="_blank" rel="noreferrer">
        LIVE ON BRADBURY <ExternalLink :size="13" />
      </a>
    </header>

    <div class="landing-statement">
      <small>CAPITAL RELEASE INFRASTRUCTURE</small>
      <h1>Money should<br />move after proof.</h1>
      <p>
        Sponsor verifiable public work. Capital waits in bounded tranches while
        GenLayer validators inspect evidence, resolve disputes and authorize release.
      </p>
    </div>

    <div class="landing-live-ledger">
      <div>
        <span>{{ projectCount }}</span>
        <small>PROJECT<br />RESERVOIRS</small>
      </div>
      <div>
        <span>{{ fromWei(dashboard?.total_funded || 0) }}</span>
        <small>GEN<br />COMMITTED</small>
      </div>
      <div>
        <span>{{ dashboard?.total_disputes || 0 }}</span>
        <small>DISPUTE<br />CHANNELS</small>
      </div>
    </div>

    <button
      class="source-valve"
      type="button"
      :disabled="connecting"
      @click="$emit('connect')"
    >
      <span class="valve-rim" aria-hidden="true" />
      <LoaderCircle v-if="connecting" class="valve-loader" :size="34" />
      <Wallet v-else :size="34" />
      <strong>{{ connecting ? "SIGN" : "OPEN" }}</strong>
      <small>{{ connecting ? "CHECK WALLET" : "CONNECT WALLET" }}</small>
      <ArrowDownRight :size="20" />
    </button>

    <div class="landing-contract">
      <small>PUBLIC SOURCE</small>
      <span>{{ contractAddress }}</span>
    </div>

    <p v-if="error" class="proof-landing-error">{{ error }}</p>
  </section>
</template>
