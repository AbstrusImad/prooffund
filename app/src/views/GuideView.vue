<script setup>
import {
  ArrowLeft,
  CheckCircle2,
  ExternalLink,
  FileSearch,
  Gavel,
  HandCoins,
  Landmark,
  RotateCcw,
  ShieldCheck,
  Wallet,
} from "lucide-vue-next";
import { contractAddress, explorerUrl } from "../services/genlayer";

const steps = [
  {
    number: "01",
    title: "Enter with a wallet",
    icon: Wallet,
    text: "Select OPEN on the landing page and approve the standard account request in MetaMask. ProofFund never asks for wallet Snaps. The connected account is restored after refresh while it remains available to the site.",
  },
  {
    number: "02",
    title: "Create a covered project",
    icon: Landmark,
    text: "Open SOURCE, define the funding goal, project deadline and first tranche, then sign the transaction. Add milestones from the project page until their combined amounts equal the complete funding goal. Full milestone coverage is mandatory before activation.",
  },
  {
    number: "03",
    title: "Fund a tranche",
    icon: HandCoins,
    text: "Choose an OPEN tranche, enter a GEN amount no greater than its remainder and confirm. GEN moves into contract escrow, not to the creator. Contribution weight also becomes the address's voting power for that project.",
  },
  {
    number: "04",
    title: "Submit verifiable evidence",
    icon: FileSearch,
    text: "The project creator opens a pending milestone and supplies a public HTTPS evidence URL plus a precise note mapping the source to every acceptance condition. The source must be reachable, project-specific and independently reproducible.",
  },
  {
    number: "05",
    title: "Run validator consensus",
    icon: ShieldCheck,
    text: "Select RUN CONSENSUS. GenLayer validators retrieve and assess the submitted evidence, then persist the verdict, score, findings and explanation. Approval becomes APPROVED PENDING: funds remain locked for the seven-day dispute window.",
  },
  {
    number: "06",
    title: "Dispute or release",
    icon: Gavel,
    text: "A contributing backer may challenge a verdict during the window by posting a positive bond and public counter-evidence. Without a dispute, RELEASE becomes valid only after the deadline. A resolved appeal atomically records the final verdict, release state, accounting, reputation and both milestone and bond transfers.",
  },
  {
    number: "07",
    title: "Recover failed-project escrow",
    icon: RotateCcw,
    text: "After the project deadline, unreleased escrow can enter terminal REFUNDING once disputes and pending approvals are settled. Each backer claims once, proportionally to their contribution; final-claimant handling distributes the entire reserved balance without stranded rounding surplus.",
  },
];
</script>

<template>
  <div class="guide-page">
    <header class="guide-header">
      <RouterLink class="guide-back" to="/"><ArrowLeft :size="18" /> ProofFund</RouterLink>
      <div>
        <a :href="`${explorerUrl}/address/${contractAddress}`" target="_blank" rel="noreferrer">
          CONTRACT <ExternalLink :size="13" />
        </a>
        <span>STUDIONET / 61999</span>
      </div>
    </header>

    <main>
      <section class="guide-intro">
        <p>OPERATOR MANUAL / LIVE PROTOCOL</p>
        <h1>From escrow<br />to verified release.</h1>
        <div class="guide-intro-copy">
          <strong>Seven actions. One accountable capital path.</strong>
          <p>This guide follows the actual StudioNet interface and contract. Every write displays wallet, consensus and terminal result states; use its transaction link to verify the same outcome in the explorer.</p>
        </div>
      </section>

      <section class="guide-sequence" aria-label="ProofFund operating sequence">
        <article v-for="step in steps" :key="step.number" class="guide-step">
          <span>{{ step.number }}</span>
          <component :is="step.icon" :size="25" />
          <div><h2>{{ step.title }}</h2><p>{{ step.text }}</p></div>
        </article>
      </section>

      <section class="guide-states">
        <div>
          <small>MILESTONE SETTLEMENT</small>
          <h2>What happens after consensus</h2>
        </div>
        <ol>
          <li><b>APPROVED_PENDING</b><span>Escrow remains inside the contract for seven days.</span></li>
          <li><b>DISPUTED</b><span>Release is blocked while validators adjudicate the appeal.</span></li>
          <li><b>APPROVED</b><span>Final settlement transfers the milestone amount to the creator.</span></li>
          <li><b>NEEDS_WORK / REJECTED</b><span>No milestone funds move; evidence may be corrected or terminal refunds may later open.</span></li>
        </ol>
      </section>

      <section class="guide-checklist">
        <div><CheckCircle2 :size="22" /><span>Public HTTPS evidence</span></div>
        <div><CheckCircle2 :size="22" /><span>Complete milestone coverage</span></div>
        <div><CheckCircle2 :size="22" /><span>Seven-day appeal window</span></div>
        <div><CheckCircle2 :size="22" /><span>Proportional backer recovery</span></div>
      </section>

      <footer class="guide-footer">
        <p>Ready to operate the live deployment?</p>
        <RouterLink to="/"><Wallet :size="18" /> OPEN PROOFFUND</RouterLink>
      </footer>
    </main>
  </div>
</template>
