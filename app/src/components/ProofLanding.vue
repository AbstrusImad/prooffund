<script setup>
import {
  ArrowRight,
  CheckCircle2,
  ExternalLink,
  FileCheck2,
  LoaderCircle,
  LockKeyhole,
  Wallet,
} from "lucide-vue-next";
import { contractAddress, explorerUrl } from "../services/genlayer";

defineProps({
  connecting: { type: Boolean, default: false },
  error: { type: String, default: "" },
});
defineEmits(["connect"]);

const projectImages = [
  "pf-0001.jpg",
  "pf-0004.jpg",
  "pf-0007.jpg",
  "pf-0009.jpg",
].map((name) => `${import.meta.env.BASE_URL}projects/${name}`);
</script>

<template>
  <section class="proof-landing">
    <div class="proof-contact-sheet" aria-hidden="true">
      <figure v-for="(image, index) in projectImages" :key="image">
        <img :src="image" alt="" />
        <span>0{{ index + 1 }} / PUBLIC EVIDENCE</span>
      </figure>
    </div>
    <div class="proof-landing-wash" aria-hidden="true" />
    <div class="proof-ledger-lines" aria-hidden="true" />

    <header class="proof-landing-header">
      <div class="proof-landing-brand">
        <span class="proof-seal"><FileCheck2 :size="19" /></span>
        <div>
          <strong>PROOFFUND</strong>
          <small>VALIDATOR-GOVERNED CAPITAL</small>
        </div>
      </div>
      <a :href="explorerUrl" target="_blank" rel="noreferrer">
        <i />
        StudioNet
        <ExternalLink :size="13" />
      </a>
    </header>

    <div class="proof-landing-copy">
      <span class="proof-folio">INSTRUMENT / 001</span>
      <h1>
        Capital waits.<br />
        <em>Proof moves it.</em>
      </h1>
      <p>
        Fund public work in bounded tranches. Release capital only when
        independent GenLayer validators confirm the evidence.
      </p>
    </div>

    <div class="proof-verification-rail" aria-hidden="true">
      <div><CheckCircle2 :size="14" /> Tranche escrow</div>
      <i />
      <div><FileCheck2 :size="14" /> Evidence consensus</div>
      <i />
      <div><LockKeyhole :size="14" /> Governed release</div>
    </div>

    <footer class="proof-signature-gate">
      <div class="proof-contract-reference">
        <span>LIVE CONTRACT</span>
        <strong>
          {{ contractAddress.slice(0, 8) }}...{{ contractAddress.slice(-6) }}
        </strong>
      </div>
      <div class="proof-gate-statement">
        <span>WALLET SIGNATURE REQUIRED</span>
        <p>Your wallet opens the live funding ledger and signing workflows.</p>
      </div>
      <button
        type="button"
        :disabled="connecting"
        @click="$emit('connect')"
      >
        <LoaderCircle v-if="connecting" class="proof-connect-spinner" :size="19" />
        <Wallet v-else :size="19" />
        <span>
          <small>{{ connecting ? "REQUESTING SIGNATURE" : "ENTER THE LEDGER" }}</small>
          <strong>{{ connecting ? "Check your wallet" : "Connect wallet" }}</strong>
        </span>
        <ArrowRight :size="18" />
      </button>
    </footer>

    <p v-if="error" class="proof-landing-error">{{ error }}</p>
  </section>
</template>
