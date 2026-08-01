<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import { useRoute } from "vue-router";
import {
  ArrowLeft,
  ArrowUpRight,
  BadgeCheck,
  Calendar,
  CircleDollarSign,
  FileCheck2,
  Gavel,
  Landmark,
  Layers3,
  Link2,
  Plus,
  RefreshCw,
  ShieldCheck,
  Unlock,
  UserRound,
  Users,
  Check,
  X,
  Clock3,
} from "lucide-vue-next";
import BaseModal from "../components/BaseModal.vue";
import { useProofFund } from "../stores/proofFund";
import { formatError, fromWei, toWei } from "../services/genlayer";
import { projectImage, useImageFallback } from "../utils/projectImage";

const route = useRoute();
const { state, isConnected, connect, loadProject, transact } = useProofFund();
const data = reactive({
  project: null,
  milestones: [],
  disputes: [],
  tranches: [],
  proposals: [],
  contribution: 0,
  votes: {},
});
const loading = ref(true);
const loadError = ref("");
const modal = ref("");
const selectedMilestone = ref(null);
const selectedTranche = ref(null);
const funding = ref(false);
const addingMilestone = ref(false);
const submittingEvidence = ref(false);
const evaluatingMilestone = ref("");
const releasingMilestone = ref("");
const openingDispute = ref(false);
const addingTranche = ref(false);
const creatingProposal = ref(false);
const votingProposal = ref("");
const finalizingProposal = ref("");
const actionError = ref("");
const fundingAmount = ref("1");
const milestoneForm = reactive({ title: "", criteria: "", amount: "", due: "" });
const evidenceForm = reactive({ url: "", note: "" });
const disputeForm = reactive({ reason: "", url: "", bond: "0.1" });
const trancheForm = reactive({ title: "", goal: "", deadline: "" });
const proposalForm = reactive({
  title: "",
  description: "",
  action: "SIGNAL",
  votingEnd: "",
  newDeadline: "",
});

const reload = async () => {
  loading.value = true;
  loadError.value = "";
  try {
    Object.assign(data, await loadProject(route.params.id));
  } catch (error) {
    loadError.value = formatError(error);
  } finally {
    loading.value = false;
  }
};

onMounted(reload);

const isCreator = computed(
  () =>
    state.wallet &&
    data.project?.creator?.toLowerCase() === state.wallet.toLowerCase(),
);
const progress = computed(() => {
  if (!data.project) return 0;
  const goal = BigInt(data.project.funding_goal || 0);
  return goal
    ? Math.min(100, Number((BigInt(data.project.funded_amount || 0) * 100n) / goal))
    : 0;
});
const openDisputes = computed(() => data.disputes.filter((item) => item.status === "OPEN"));
const remainingMilestoneBudget = computed(() => {
  if (!data.project) return 0n;
  return (
    BigInt(data.project.funding_goal || 0) -
    BigInt(data.project.milestone_budget || 0)
  );
});
const remainingTrancheBudget = computed(() => {
  if (!data.project) return 0n;
  return (
    BigInt(data.project.funding_goal || 0) -
    BigInt(data.project.tranche_budget || 0)
  );
});
const canPropose = computed(
  () =>
    BigInt(data.project?.funded_amount || 0) > 0n &&
    (isCreator.value || BigInt(data.contribution || 0) > 0n),
);

const ensureWallet = async () => {
  if (!isConnected.value) await connect();
};

const fund = async () => {
  actionError.value = "";
  let amount;
  try {
    amount = toWei(fundingAmount.value);
    if (!selectedTranche.value) throw new Error("Select an open funding tranche.");
    const remaining =
      BigInt(selectedTranche.value.goal) -
      BigInt(selectedTranche.value.funded_amount);
    if (amount <= 0n) throw new Error("Contribution must be greater than zero.");
    if (amount > remaining) {
      throw new Error(`Maximum remaining contribution is ${fromWei(remaining)} GEN.`);
    }
    await ensureWallet();
    funding.value = true;
    await transact(
      `Funding ${selectedTranche.value.title}`,
      "fund_tranche",
      [data.project.id, selectedTranche.value.id],
      amount,
      {
        successMessage: `${fundingAmount.value} GEN accepted into project escrow.`,
      },
    );
    modal.value = "";
    await reload();
  } catch (error) {
    actionError.value = formatError(error);
  } finally {
    funding.value = false;
  }
};

const addTranche = async () => {
  actionError.value = "";
  addingTranche.value = true;
  try {
    const goal = toWei(trancheForm.goal);
    if (trancheForm.title.trim().length < 4) {
      throw new Error("Tranche title must contain at least 4 characters.");
    }
    if (goal <= 0n || goal > remainingTrancheBudget.value) {
      throw new Error(`Available tranche budget is ${fromWei(remainingTrancheBudget.value)} GEN.`);
    }
    const deadline = Math.floor(new Date(trancheForm.deadline).getTime() / 1000);
    if (!deadline || deadline <= Date.now() / 1000 || deadline > Number(data.project.deadline)) {
      throw new Error("Tranche deadline must be future-dated and within the project deadline.");
    }
    await transact(
      "Adding funding tranche",
      "add_funding_tranche",
      [data.project.id, trancheForm.title, goal, deadline],
      0n,
      { successMessage: "Funding tranche opened on Bradbury." },
    );
    modal.value = "";
    await reload();
  } catch (error) {
    actionError.value = formatError(error);
  } finally {
    addingTranche.value = false;
  }
};

const createProposal = async () => {
  actionError.value = "";
  creatingProposal.value = true;
  try {
    const votingEnd = Math.floor(new Date(proposalForm.votingEnd).getTime() / 1000);
    if (proposalForm.title.trim().length < 4) {
      throw new Error("Proposal title must contain at least 4 characters.");
    }
    if (proposalForm.description.trim().length < 30) {
      throw new Error("Proposal description must contain at least 30 characters.");
    }
    if (!votingEnd || votingEnd <= Date.now() / 1000 + 60) {
      throw new Error("Voting must remain open for at least 60 seconds.");
    }
    let actionValue = 0n;
    if (proposalForm.action === "EXTEND_DEADLINE") {
      actionValue = BigInt(
        Math.floor(new Date(proposalForm.newDeadline).getTime() / 1000),
      );
      if (actionValue <= BigInt(data.project.deadline)) {
        throw new Error("The proposed deadline must extend the current deadline.");
      }
    }
    await ensureWallet();
    await transact(
      "Publishing governance proposal",
      "create_proposal",
      [
        data.project.id,
        proposalForm.title,
        proposalForm.description,
        proposalForm.action,
        actionValue,
        votingEnd,
      ],
      0n,
      { successMessage: "Proposal opened for contribution-weighted voting." },
    );
    modal.value = "";
    await reload();
  } catch (error) {
    actionError.value = formatError(error);
  } finally {
    creatingProposal.value = false;
  }
};

const voteProposal = async (proposal, support) => {
  actionError.value = "";
  votingProposal.value = proposal.id;
  try {
    await ensureWallet();
    await transact(
      support ? "Casting support vote" : "Casting opposition vote",
      "vote_proposal",
      [proposal.id, support],
      0n,
      { successMessage: `${support ? "YES" : "NO"} vote recorded on Bradbury.` },
    );
    await reload();
  } catch (error) {
    actionError.value = formatError(error);
  } finally {
    votingProposal.value = "";
  }
};

const finalizeProposal = async (proposal) => {
  actionError.value = "";
  finalizingProposal.value = proposal.id;
  try {
    await ensureWallet();
    await transact(
      "Finalizing governance proposal",
      "finalize_proposal",
      [proposal.id],
      0n,
      { successMessage: "Proposal finalized and approved action executed." },
    );
    await reload();
  } catch (error) {
    actionError.value = formatError(error);
  } finally {
    finalizingProposal.value = "";
  }
};

const addMilestone = async () => {
  actionError.value = "";
  try {
    if (milestoneForm.title.trim().length < 4) {
      throw new Error("Milestone title must contain at least 4 characters.");
    }
    if (milestoneForm.criteria.trim().length < 30) {
      throw new Error("Acceptance criteria must contain at least 30 characters.");
    }
    const amount = toWei(milestoneForm.amount);
    const available =
      BigInt(data.project.funding_goal) - BigInt(data.project.milestone_budget);
    if (amount <= 0n) throw new Error("Release amount must be greater than zero.");
    if (amount > available) {
      throw new Error(`Only ${fromWei(available)} GEN remains in the milestone budget.`);
    }
    const dueAt = Math.floor(new Date(milestoneForm.due).getTime() / 1000);
    if (!dueAt || dueAt <= Math.floor(Date.now() / 1000)) {
      throw new Error("Milestone due date must be in the future.");
    }
    if (dueAt > Number(data.project.deadline)) {
      throw new Error(`Due date cannot exceed ${formatDate(data.project.deadline)}.`);
    }

    addingMilestone.value = true;
    await transact(
      "Adding milestone",
      "add_milestone",
      [
        data.project.id,
        milestoneForm.title,
        milestoneForm.criteria,
        amount,
        dueAt,
      ],
      0n,
      {
        successMessage: ({ returnValue }) =>
          `${returnValue || "Milestone"} added to the on-chain release ledger.`,
      },
    );
    modal.value = "";
    await reload();
  } catch (error) {
    actionError.value = formatError(error);
  } finally {
    addingMilestone.value = false;
  }
};

const submitEvidence = async () => {
  actionError.value = "";
  submittingEvidence.value = true;
  try {
    await transact(
      "Submitting public evidence",
      "submit_evidence",
      [
        data.project.id,
        selectedMilestone.value.id,
        evidenceForm.url,
        evidenceForm.note,
      ],
      0n,
      { successMessage: "Evidence published and ready for validator evaluation." },
    );
    modal.value = "";
    await reload();
  } catch (error) {
    actionError.value = formatError(error);
  } finally {
    submittingEvidence.value = false;
  }
};

const evaluate = async (milestone) => {
  actionError.value = "";
  evaluatingMilestone.value = milestone.id;
  try {
    await ensureWallet();
    await transact(
      "Validators evaluating evidence",
      "evaluate_milestone",
      [data.project.id, milestone.id],
      0n,
      { successMessage: "Consensus verdict recorded on Bradbury." },
    );
    await reload();
  } catch (error) {
    actionError.value = formatError(error);
  } finally {
    evaluatingMilestone.value = "";
  }
};

const isPastDisputeWindow = (milestone) => {
  const end = Number(milestone.dispute_window_end || 0);
  return end > 0 && Math.floor(Date.now() / 1000) >= end;
};

const canClaimRefund = computed(() => {
  if (!data.project || !data.contribution || !state.wallet) return false;
  if (data.project.status === "COMPLETED") return false;
  const deadline = Number(data.project.deadline || 0);
  return deadline > 0 && Math.floor(Date.now() / 1000) > deadline;
});

const claimRefund = async () => {
  actionError.value = "";
  try {
    await ensureWallet();
    await transact(
      "Claiming backer refund",
      "claim_refund",
      [data.project.id],
      0n,
      { successMessage: "Refund added to your claimable balance." },
    );
    await reload();
  } catch (error) {
    actionError.value = formatError(error);
  }
};

const releaseMilestone = async (milestone) => {
  actionError.value = "";
  releasingMilestone.value = milestone.id;
  try {
    await ensureWallet();
    await transact(
      "Releasing approved milestone funds",
      "release_approved_milestone",
      [data.project.id, milestone.id],
      0n,
      { successMessage: "Milestone funds released to creator claimable." },
    );
    await reload();
  } catch (error) {
    actionError.value = formatError(error);
  } finally {
    releasingMilestone.value = "";
  }
};

const openDispute = async () => {
  actionError.value = "";
  openingDispute.value = true;
  try {
    await ensureWallet();
    await transact(
      "Opening bonded dispute",
      "open_dispute",
      [data.project.id, selectedMilestone.value.id, disputeForm.reason, disputeForm.url],
      toWei(disputeForm.bond),
      { successMessage: "Bonded dispute opened and recorded on Bradbury." },
    );
    modal.value = "";
    await reload();
  } catch (error) {
    actionError.value = formatError(error);
  } finally {
    openingDispute.value = false;
  }
};

const resolveDispute = async (dispute) => {
  await ensureWallet();
  await transact("Resolving dispute by consensus", "resolve_dispute", [dispute.id]);
  await reload();
};

const openModal = (name, item = null) => {
  actionError.value = "";
  if (name === "fund") selectedTranche.value = item;
  if (name === "evidence" || name === "dispute") selectedMilestone.value = item;
  modal.value = name;
};

const formatDate = (timestamp) =>
  new Intl.DateTimeFormat("en", { month: "short", day: "numeric", year: "numeric" }).format(
    new Date(Number(timestamp) * 1000),
  );
const tranchePercent = (tranche) => {
  const goal = BigInt(tranche.goal || 0);
  return goal
    ? Number((BigInt(tranche.funded_amount || 0) * 100n) / goal)
    : 0;
};
const proposalPercent = (proposal) => {
  const yes = BigInt(proposal.yes_votes || 0);
  const no = BigInt(proposal.no_votes || 0);
  return yes + no ? Number((yes * 100n) / (yes + no)) : 0;
};
const proposalEnded = (proposal) =>
  Number(proposal.voting_ends_at) <= Date.now() / 1000;
</script>

<template>
  <div v-if="loading" class="page project-loading">
    <div class="skeleton-line wide"></div><div class="skeleton-line"></div>
  </div>
  <div v-else-if="loadError" class="page">
    <section class="empty-state">
      <RefreshCw :size="28" />
      <h3>Bradbury is temporarily busy</h3>
      <p>{{ loadError }}</p>
      <button class="primary-button" type="button" @click="reload">Retry project data</button>
    </section>
  </div>
  <div v-else-if="data.project" class="page project-page">
    <RouterLink class="back-link" to="/"><ArrowLeft :size="16" /> Project registry</RouterLink>

    <section class="project-hero">
      <div class="project-hero-copy">
        <div class="project-meta-line">
          <span class="status-chip" :data-status="data.project.status">{{ data.project.status }}</span>
          <span>{{ data.project.category }}</span>
          <span>{{ data.project.id }}</span>
        </div>
        <h1>{{ data.project.title }}</h1>
        <p>{{ data.project.summary }}</p>
        <div class="project-links">
          <a :href="data.project.website_url" target="_blank" rel="noreferrer">
            <Link2 :size="16" /> Project source <ArrowUpRight :size="14" />
          </a>
          <span><UserRound :size="16" /> {{ data.project.creator.slice(0, 8) }}...{{ data.project.creator.slice(-6) }}</span>
          <span><Calendar :size="16" /> Ends {{ formatDate(data.project.deadline) }}</span>
        </div>
      </div>
      <div class="project-hero-visual">
        <img
          :src="projectImage(data.project)"
          :alt="data.project.title"
          @error="useImageFallback"
        />
      </div>
    </section>

    <div class="project-layout">
      <div class="project-main">
        <section class="content-section">
          <div class="content-heading"><span>01</span><h2>Project mandate</h2></div>
          <p class="long-copy">{{ data.project.description }}</p>
        </section>

        <section id="tranches" class="content-section">
          <div class="content-heading">
            <span>02</span>
            <div><h2>Funding tranches</h2><p>{{ data.tranches.length }} bounded capital rounds</p></div>
            <button
              v-if="isCreator && ['FUNDING', 'PAUSED'].includes(data.project.status) && remainingTrancheBudget > 0n"
              class="icon-text-button"
              type="button"
              @click="openModal('tranche')"
            >
              <Plus :size="16" /> Add tranche
            </button>
            <span v-else-if="isCreator && remainingTrancheBudget === 0n" class="budget-complete">
              Tranche budget allocated
            </span>
          </div>
          <div class="tranche-list">
            <article v-for="tranche in data.tranches" :key="tranche.id" class="tranche-item">
              <header>
                <div>
                  <span>{{ tranche.id }}</span>
                  <h3>{{ tranche.title }}</h3>
                </div>
                <b :data-status="tranche.status">{{ tranche.status }}</b>
              </header>
              <div class="tranche-numbers">
                <strong>{{ fromWei(tranche.funded_amount) }} / {{ fromWei(tranche.goal) }} GEN</strong>
                <span>{{ tranche.backer_count }} sponsors · closes {{ formatDate(tranche.deadline) }}</span>
              </div>
              <div class="progress-track"><span :style="{ width: `${tranchePercent(tranche)}%` }"></span></div>
              <button
                v-if="tranche.status === 'OPEN' && data.project.status === 'FUNDING'"
                class="secondary-button compact"
                type="button"
                @click="openModal('fund', tranche)"
              >
                <CircleDollarSign :size="15" /> Fund tranche
              </button>
            </article>
          </div>
        </section>

        <section class="content-section">
          <div class="content-heading">
            <span>03</span>
            <div><h2>Milestone ledger</h2><p>{{ data.milestones.length }} explicit release conditions</p></div>
            <button
              v-if="isCreator && ['DRAFT', 'FUNDING'].includes(data.project.status) && remainingMilestoneBudget > 0n"
              class="icon-text-button"
              type="button"
              @click="openModal('milestone')"
            >
              <Plus :size="16" /> Add milestone
            </button>
            <span
              v-else-if="isCreator && remainingMilestoneBudget === 0n"
              class="budget-complete"
            >
              Budget fully allocated
            </span>
          </div>

          <div v-if="data.milestones.length" class="milestone-list">
            <article v-for="milestone in data.milestones" :key="milestone.id" class="milestone-item">
              <div class="milestone-rail">
                <span :class="milestone.status.toLowerCase()"><FileCheck2 :size="18" /></span>
                <i></i>
              </div>
              <div class="milestone-content">
                <header>
                  <div><small>Milestone {{ milestone.index }}</small><h3>{{ milestone.title }}</h3></div>
                  <div class="milestone-value"><strong>{{ fromWei(milestone.amount) }} GEN</strong><span>{{ milestone.status === 'APPROVED_PENDING' ? 'Pending dispute window' : milestone.status }}</span></div>
                </header>
                <p>{{ milestone.criteria }}</p>
                <div class="milestone-facts">
                  <span>Due {{ formatDate(milestone.due_at) }}</span>
                  <span v-if="milestone.score">Consensus score {{ milestone.score }}/100</span>
                  <span v-if="milestone.dispute_count">{{ milestone.dispute_count }} dispute</span>
                </div>
                <div v-if="milestone.analysis" class="audit-note">
                  <ShieldCheck :size="18" />
                  <div><strong>Validator conclusion</strong><p>{{ milestone.analysis }}</p></div>
                </div>
                <a v-if="milestone.evidence_url" class="evidence-link" :href="milestone.evidence_url" target="_blank" rel="noreferrer">
                  View submitted evidence <ArrowUpRight :size="14" />
                </a>
                <div class="milestone-actions">
                  <button
                    v-if="isCreator && ['PENDING', 'SUBMITTED', 'NEEDS_WORK', 'REJECTED', 'APPROVED_PENDING'].includes(milestone.status) && data.project.status === 'ACTIVE'"
                    class="secondary-button"
                    type="button"
                    @click="openModal('evidence', milestone)"
                  >
                    {{ milestone.status === "SUBMITTED" ? "Replace evidence" : "Submit evidence" }}
                  </button>
                  <button
                    v-if="milestone.status === 'SUBMITTED'"
                    class="primary-button compact"
                    type="button"
                    :disabled="evaluatingMilestone === milestone.id"
                    @click="evaluate(milestone)"
                  >
                    <span v-if="evaluatingMilestone === milestone.id" class="button-spinner"></span>
                    <RefreshCw v-else :size="15" />
                    {{ evaluatingMilestone === milestone.id ? "Evaluating..." : "Run consensus" }}
                  </button>
                  <button
                    v-if="!isCreator && ['APPROVED', 'APPROVED_PENDING', 'NEEDS_WORK', 'REJECTED'].includes(milestone.status)"
                    class="danger-button"
                    type="button"
                    @click="openModal('dispute', milestone)"
                  >
                    <Gavel :size="15" /> Challenge verdict
                  </button>
                  <button
                    v-if="isCreator && milestone.status === 'APPROVED_PENDING' && isPastDisputeWindow(milestone)"
                    class="primary-button compact"
                    type="button"
                    :disabled="releasingMilestone === milestone.id"
                    @click="releaseMilestone(milestone)"
                  >
                    <span v-if="releasingMilestone === milestone.id" class="button-spinner"></span>
                    <Unlock v-else :size="15" />
                    {{ releasingMilestone === milestone.id ? "Releasing..." : "Release funds" }}
                  </button>
                </div>
              </div>
            </article>
          </div>
          <div v-else class="inline-empty">
            <FileCheck2 :size="24" /><div><strong>No milestones defined</strong><p>The creator must define release conditions before funding.</p></div>
          </div>
        </section>

        <section class="content-section">
          <div class="content-heading">
            <span>04</span>
            <div><h2>Project governance</h2><p>Contribution-weighted proposals and execution</p></div>
            <button v-if="canPropose" class="icon-text-button" type="button" @click="openModal('proposal')">
              <Plus :size="16" /> New proposal
            </button>
          </div>
          <p v-if="actionError && !modal" class="action-error governance-error">{{ actionError }}</p>
          <div v-if="data.proposals.length" class="project-proposals">
            <article v-for="proposal in data.proposals" :key="proposal.id" class="project-proposal">
              <header>
                <div><span>{{ proposal.id }} · {{ proposal.action.replaceAll("_", " ") }}</span><h3>{{ proposal.title }}</h3></div>
                <b :data-status="proposal.status">{{ proposal.status }}</b>
              </header>
              <p>{{ proposal.description }}</p>
              <div class="vote-meter">
                <div><span :style="{ width: `${proposalPercent(proposal)}%` }"></span></div>
                <p><strong>{{ fromWei(proposal.yes_votes) }} YES</strong><span>{{ fromWei(proposal.no_votes) }} NO</span></p>
              </div>
              <footer>
                <span><Clock3 :size="14" /> {{ proposalEnded(proposal) ? "Ended" : "Ends" }} {{ formatDate(proposal.voting_ends_at) }}</span>
                <span>Quorum {{ fromWei(proposal.quorum) }} GEN</span>
              </footer>
              <div v-if="proposal.status === 'OPEN'" class="proposal-actions">
                <template v-if="!proposalEnded(proposal)">
                  <button
                    class="vote-button yes"
                    type="button"
                    :disabled="votingProposal === proposal.id || Boolean(data.votes[proposal.id])"
                    @click="voteProposal(proposal, true)"
                  >
                    <Check :size="15" /> {{ data.votes[proposal.id] === "YES" ? "Voted yes" : "Vote yes" }}
                  </button>
                  <button
                    class="vote-button no"
                    type="button"
                    :disabled="votingProposal === proposal.id || Boolean(data.votes[proposal.id])"
                    @click="voteProposal(proposal, false)"
                  >
                    <X :size="15" /> {{ data.votes[proposal.id] === "NO" ? "Voted no" : "Vote no" }}
                  </button>
                </template>
                <button
                  v-else
                  class="primary-button compact"
                  type="button"
                  :disabled="finalizingProposal === proposal.id"
                  @click="finalizeProposal(proposal)"
                >
                  Finalize proposal
                </button>
              </div>
            </article>
          </div>
          <div v-else class="inline-empty"><Landmark :size="24" /><div><strong>No governance proposals</strong><p>Governance activates after the first contribution.</p></div></div>
        </section>

        <section class="content-section">
          <div class="content-heading"><span>05</span><div><h2>Dispute record</h2><p>Bonded, public, and validator-resolved</p></div></div>
          <div v-if="data.disputes.length" class="dispute-table">
            <div class="table-row table-header"><span>Case</span><span>Challenge</span><span>Bond</span><span>Outcome</span><span></span></div>
            <div v-for="dispute in data.disputes" :key="dispute.id" class="table-row">
              <span><strong>{{ dispute.id }}</strong><small>{{ dispute.milestone_id }}</small></span>
              <span>{{ dispute.reason }}</span>
              <span>{{ fromWei(dispute.bond) }} GEN</span>
              <span><b :data-status="dispute.status">{{ dispute.resolution || dispute.status }}</b></span>
              <span><button v-if="dispute.status === 'OPEN'" class="icon-button" title="Resolve dispute" type="button" @click="resolveDispute(dispute)"><Gavel :size="16" /></button></span>
            </div>
          </div>
          <div v-else class="inline-empty"><BadgeCheck :size="24" /><div><strong>Clean adjudication record</strong><p>No verdict has been challenged.</p></div></div>
        </section>
      </div>

      <aside class="funding-panel">
        <span class="eyebrow">Escrow status</span>
        <strong class="funding-total">{{ fromWei(data.project.funded_amount) }} <small>GEN</small></strong>
        <p>committed of {{ fromWei(data.project.funding_goal) }} GEN</p>
        <div class="progress-track large"><span :style="{ width: `${progress}%` }"></span></div>
        <div class="funding-percentage"><strong>{{ progress }}%</strong><span>{{ data.project.backer_count }} backers</span></div>
        <dl>
          <div><dt>Released</dt><dd>{{ fromWei(data.project.released_amount) }} GEN</dd></div>
          <div><dt>Milestone budget</dt><dd>{{ fromWei(data.project.milestone_budget) }} GEN</dd></div>
          <div><dt>Open disputes</dt><dd>{{ openDisputes.length }}</dd></div>
        </dl>
        <a v-if="data.project.status === 'FUNDING' && progress < 100" class="primary-button full" href="#tranches">
          <Layers3 :size="17" /> Choose funding tranche
        </a>
        <button
          v-if="canClaimRefund"
          class="secondary-button full"
          type="button"
          @click="claimRefund"
        >
          <CircleDollarSign :size="17" /> Claim refund
        </button>
        <div class="escrow-note"><ShieldCheck :size="17" /><span>Funds remain in contract escrow until a milestone is approved.</span></div>
      </aside>
    </div>

    <BaseModal v-if="modal === 'fund'" title="Commit capital" :eyebrow="selectedTranche?.title" @close="modal = ''">
      <form class="modal-form" @submit.prevent="fund">
        <label class="field"><span>Contribution</span><div class="input-suffix"><input v-model="fundingAmount" inputmode="decimal" autofocus /><b>GEN</b></div></label>
        <p class="modal-note">Available in this tranche: {{ fromWei(BigInt(selectedTranche?.goal || 0) - BigInt(selectedTranche?.funded_amount || 0)) }} GEN.</p>
        <p v-if="actionError" class="action-error">{{ actionError }}</p>
        <button class="primary-button full" type="submit" :disabled="funding">
          <span v-if="funding" class="button-spinner"></span>
          <CircleDollarSign v-else :size="17" />
          {{ funding ? "Waiting for consensus..." : "Confirm contribution" }}
        </button>
      </form>
    </BaseModal>

    <BaseModal v-if="modal === 'tranche'" title="Open a funding tranche" eyebrow="Staged capital" @close="modal = ''">
      <form class="modal-form" @submit.prevent="addTranche">
        <label class="field"><span>Tranche title</span><input v-model="trancheForm.title" maxlength="100" required placeholder="e.g. Public beta delivery" /></label>
        <div class="field-grid">
          <label class="field"><span>Funding target</span><div class="input-suffix"><input v-model="trancheForm.goal" inputmode="decimal" required /><b>GEN</b></div></label>
          <label class="field"><span>Funding deadline</span><input v-model="trancheForm.deadline" type="date" required /></label>
        </div>
        <p class="modal-note">Unallocated project target: {{ fromWei(remainingTrancheBudget) }} GEN.</p>
        <p v-if="actionError" class="action-error">{{ actionError }}</p>
        <button class="primary-button full" type="submit" :disabled="addingTranche">
          <span v-if="addingTranche" class="button-spinner"></span>
          <Layers3 v-else :size="17" />
          {{ addingTranche ? "Opening tranche..." : "Open funding tranche" }}
        </button>
      </form>
    </BaseModal>

    <BaseModal v-if="modal === 'proposal'" title="Open a governance proposal" eyebrow="Backer vote" @close="modal = ''">
      <form class="modal-form" @submit.prevent="createProposal">
        <label class="field"><span>Proposal title</span><input v-model="proposalForm.title" maxlength="100" required /></label>
        <label class="field"><span>Rationale and requested decision</span><textarea v-model="proposalForm.description" rows="6" maxlength="2000" required></textarea></label>
        <label class="field">
          <span>Action</span>
          <select v-model="proposalForm.action">
            <option value="SIGNAL">Signal decision</option>
            <option value="EXTEND_DEADLINE">Extend project deadline</option>
            <option value="PAUSE_FUNDING">Pause funding</option>
            <option value="REOPEN_FUNDING">Reopen funding</option>
          </select>
        </label>
        <label v-if="proposalForm.action === 'EXTEND_DEADLINE'" class="field">
          <span>Proposed project deadline</span>
          <input v-model="proposalForm.newDeadline" type="date" required />
        </label>
        <label class="field"><span>Voting closes</span><input v-model="proposalForm.votingEnd" type="datetime-local" required /></label>
        <p class="modal-note">Quorum is fixed at 20% of funded GEN when the proposal opens. Each address votes with its project contribution.</p>
        <p v-if="actionError" class="action-error">{{ actionError }}</p>
        <button class="primary-button full" type="submit" :disabled="creatingProposal">
          <span v-if="creatingProposal" class="button-spinner"></span>
          <Landmark v-else :size="17" />
          {{ creatingProposal ? "Publishing proposal..." : "Open proposal" }}
        </button>
      </form>
    </BaseModal>

    <BaseModal v-if="modal === 'milestone'" title="Define a release condition" eyebrow="Project structure" @close="modal = ''">
      <form class="modal-form" @submit.prevent="addMilestone">
        <label class="field"><span>Milestone title</span><input v-model="milestoneForm.title" maxlength="100" required /></label>
        <label class="field"><span>Acceptance criteria</span><textarea v-model="milestoneForm.criteria" rows="6" maxlength="2000" required placeholder="State observable conditions validators can verify from a public URL."></textarea></label>
        <div class="field-grid">
          <label class="field"><span>Release amount</span><div class="input-suffix"><input v-model="milestoneForm.amount" inputmode="decimal" required /><b>GEN</b></div></label>
          <label class="field"><span>Due date</span><input v-model="milestoneForm.due" type="date" required /></label>
        </div>
        <p class="modal-note">
          Available milestone budget: {{ fromWei(remainingMilestoneBudget) }} GEN
        </p>
        <p v-if="actionError" class="action-error">{{ actionError }}</p>
        <button class="primary-button full" type="submit" :disabled="addingMilestone">
          <span v-if="addingMilestone" class="button-spinner"></span>
          <Plus v-else :size="17" />
          {{ addingMilestone ? "Waiting for consensus..." : "Add milestone" }}
        </button>
      </form>
    </BaseModal>

    <BaseModal v-if="modal === 'evidence'" title="Submit public evidence" :eyebrow="selectedMilestone?.title" @close="modal = ''">
      <form class="modal-form" @submit.prevent="submitEvidence">
        <label class="field"><span>Evidence URL</span><input v-model="evidenceForm.url" type="url" required placeholder="https://..." /></label>
        <label class="field"><span>Evidence note</span><textarea v-model="evidenceForm.note" rows="6" maxlength="1200" required placeholder="Point validators to the exact artifacts that satisfy each criterion."></textarea></label>
        <p class="modal-note">GenLayer validators independently render this URL and compare their verdict.</p>
        <p v-if="actionError" class="action-error">{{ actionError }}</p>
        <button class="primary-button full" type="submit" :disabled="submittingEvidence">
          <span v-if="submittingEvidence" class="button-spinner"></span>
          <FileCheck2 v-else :size="17" />
          {{ submittingEvidence ? "Submitting..." : "Submit evidence" }}
        </button>
      </form>
    </BaseModal>

    <BaseModal v-if="modal === 'dispute'" title="Challenge the verdict" eyebrow="Bonded appeal" @close="modal = ''">
      <form class="modal-form" @submit.prevent="openDispute">
        <label class="field"><span>Material issue</span><textarea v-model="disputeForm.reason" rows="6" maxlength="1500" required placeholder="Explain the factual or interpretive error in the existing verdict."></textarea></label>
        <label class="field"><span>Counter-evidence URL</span><input v-model="disputeForm.url" type="url" required placeholder="https://..." /></label>
        <label class="field"><span>Dispute bond</span><div class="input-suffix"><input v-model="disputeForm.bond" inputmode="decimal" required /><b>GEN</b></div></label>
        <p v-if="actionError" class="action-error">{{ actionError }}</p>
        <button class="danger-button full" type="submit" :disabled="openingDispute">
          <span v-if="openingDispute" class="button-spinner dark"></span>
          <Gavel v-else :size="17" />
          {{ openingDispute ? "Opening dispute..." : "Open dispute" }}
        </button>
      </form>
    </BaseModal>
  </div>
</template>
