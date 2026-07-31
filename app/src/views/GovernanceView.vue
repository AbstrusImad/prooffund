<script setup>
import { computed, ref } from "vue";
import {
  ArrowUpRight,
  Check,
  CircleDot,
  Clock3,
  Landmark,
  Scale,
  X,
} from "lucide-vue-next";
import { useProofFund } from "../stores/proofFund";
import { formatError, fromWei } from "../services/genlayer";

const { state, isConnected, connect, transact, refresh } = useProofFund();
const filter = ref("OPEN");
const workingId = ref("");
const actionError = ref("");

const projectById = computed(
  () => new Map(state.projects.map((project) => [project.id, project])),
);
const proposals = computed(() =>
  [...state.proposals]
    .filter((proposal) => filter.value === "ALL" || proposal.status === filter.value)
    .sort((a, b) => Number(b.created_at) - Number(a.created_at)),
);

const vote = async (proposal, support) => {
  actionError.value = "";
  workingId.value = proposal.id;
  try {
    if (!isConnected.value) await connect();
    if (state.proposalVotes[proposal.id]) {
      throw new Error(
        `This wallet already voted ${state.proposalVotes[proposal.id]} on ${proposal.id}.`,
      );
    }
    await transact(
      support ? "Casting support vote" : "Casting opposition vote",
      "vote_proposal",
      [proposal.id, support],
      0n,
      { successMessage: `${support ? "YES" : "NO"} vote recorded with contribution weight.` },
    );
    await refresh();
  } catch (error) {
    actionError.value = formatError(error);
  } finally {
    workingId.value = "";
  }
};

const finalize = async (proposal) => {
  actionError.value = "";
  workingId.value = proposal.id;
  try {
    if (!isConnected.value) await connect();
    await transact(
      "Finalizing governance proposal",
      "finalize_proposal",
      [proposal.id],
      0n,
      { successMessage: "Proposal finalized and approved action executed." },
    );
    await refresh();
  } catch (error) {
    actionError.value = formatError(error);
  } finally {
    workingId.value = "";
  }
};

const votePercent = (proposal) => {
  const yes = BigInt(proposal.yes_votes || 0);
  const no = BigInt(proposal.no_votes || 0);
  const total = yes + no;
  return total ? Number((yes * 100n) / total) : 0;
};
const ended = (proposal) => Number(proposal.voting_ends_at) <= Date.now() / 1000;
const formatDate = (timestamp) =>
  new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(Number(timestamp) * 1000));
</script>

<template>
  <div class="page governance-page">
    <header class="governance-heading">
      <div>
        <span class="eyebrow"><Landmark :size="15" /> Contribution-weighted governance</span>
        <h1>Capital earns a voice.</h1>
        <p>Project backers decide protocol signals, funding pauses, reopenings, and deadline extensions with auditable on-chain weight.</p>
      </div>
      <div class="governance-summary">
        <article><CircleDot :size="18" /><span>Open</span><strong>{{ state.dashboard?.open_proposals || 0 }}</strong></article>
        <article><Scale :size="18" /><span>Total</span><strong>{{ state.dashboard?.total_proposals || 0 }}</strong></article>
      </div>
    </header>

    <div class="governance-toolbar">
      <div class="segmented-control">
        <button
          v-for="option in ['OPEN', 'PASSED', 'REJECTED', 'ALL']"
          :key="option"
          type="button"
          :class="{ active: filter === option }"
          @click="filter = option"
        >
          {{ option }}
        </button>
      </div>
      <span>{{ proposals.length }} proposals</span>
    </div>

    <p v-if="actionError" class="action-error governance-error">{{ actionError }}</p>

    <div v-if="proposals.length" class="proposal-grid">
      <article v-for="proposal in proposals" :key="proposal.id" class="proposal-card">
        <header>
          <div>
            <span>{{ proposal.id }} · {{ proposal.action.replaceAll("_", " ") }}</span>
            <h2>{{ proposal.title }}</h2>
          </div>
          <b :data-status="proposal.status">{{ proposal.status }}</b>
        </header>
        <p>{{ proposal.description }}</p>
        <RouterLink :to="`/projects/${proposal.project_id}`" class="proposal-project">
          {{ projectById.get(proposal.project_id)?.title || proposal.project_id }}
          <ArrowUpRight :size="14" />
        </RouterLink>
        <div class="vote-meter">
          <div><span :style="{ width: `${votePercent(proposal)}%` }"></span></div>
          <p>
            <strong>{{ fromWei(proposal.yes_votes) }} YES</strong>
            <span>{{ fromWei(proposal.no_votes) }} NO</span>
          </p>
        </div>
        <footer>
          <span><Clock3 :size="14" /> {{ ended(proposal) ? "Ended" : "Ends" }} {{ formatDate(proposal.voting_ends_at) }}</span>
          <span>Quorum {{ fromWei(proposal.quorum) }} GEN</span>
        </footer>
        <div v-if="proposal.status === 'OPEN'" class="proposal-actions">
          <template v-if="!ended(proposal)">
            <button
              class="vote-button yes"
              type="button"
              :disabled="workingId === proposal.id || Boolean(state.proposalVotes[proposal.id])"
              @click="vote(proposal, true)"
            >
              <Check :size="15" />
              {{ state.proposalVotes[proposal.id] === "YES" ? "Voted yes" : "Vote yes" }}
            </button>
            <button
              class="vote-button no"
              type="button"
              :disabled="workingId === proposal.id || Boolean(state.proposalVotes[proposal.id])"
              @click="vote(proposal, false)"
            >
              <X :size="15" />
              {{ state.proposalVotes[proposal.id] === "NO" ? "Voted no" : "Vote no" }}
            </button>
          </template>
          <button v-else class="primary-button compact" type="button" :disabled="workingId === proposal.id" @click="finalize(proposal)">
            Finalize proposal
          </button>
        </div>
      </article>
    </div>
    <div v-else class="empty-state">
      <Landmark :size="30" />
      <h3>No proposals in this view</h3>
      <p>Governance records appear after a funded project opens its first proposal.</p>
    </div>
  </div>
</template>
