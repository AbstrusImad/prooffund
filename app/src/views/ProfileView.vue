<script setup>
import { computed } from "vue";
import { BadgeCheck, CircleDollarSign, Gavel, Landmark, Vote, Wallet } from "lucide-vue-next";
import ProjectCard from "../components/ProjectCard.vue";
import DataLoader from "../components/DataLoader.vue";
import { useProofFund } from "../stores/proofFund";
import { fromWei } from "../services/genlayer";

const { state, isConnected, connect } = useProofFund();
const ownProjects = computed(() =>
  state.projects.filter(
    (project) => project.creator?.toLowerCase() === state.wallet?.toLowerCase(),
  ),
);
</script>

<template>
  <div class="page">
    <section v-if="!isConnected" class="wallet-gate">
      <div><Wallet :size="30" /></div>
      <h1>Connect your funding identity</h1>
      <p>Your portfolio and reputation are read directly from your StudioNet address.</p>
      <button class="primary-button" type="button" @click="connect">Connect wallet</button>
    </section>
    <DataLoader
      v-else-if="!state.profile && (state.loading || state.refreshing)"
      label="Reading your on-chain portfolio"
    />
    <template v-else>
      <header class="profile-heading">
        <div><span class="eyebrow">On-chain portfolio</span><h1>{{ state.wallet }}</h1></div>
        <div class="budget-complete">DIRECT SETTLEMENT / {{ fromWei(state.profile?.total_earned || 0) }} GEN EARNED</div>
      </header>
      <section class="profile-stats">
        <article><CircleDollarSign :size="19" /><span>Capital backed</span><strong>{{ fromWei(state.profile?.total_funded || 0) }} GEN</strong></article>
        <article><BadgeCheck :size="19" /><span>Milestones approved</span><strong>{{ state.profile?.milestones_approved || 0 }}</strong></article>
        <article><Gavel :size="19" /><span>Dispute record</span><strong>{{ state.profile?.disputes_won || 0 }}W / {{ state.profile?.disputes_lost || 0 }}L</strong></article>
        <article><Landmark :size="19" /><span>Proposals created</span><strong>{{ state.profile?.proposals_created || 0 }}</strong></article>
        <article><Vote :size="19" /><span>Votes cast</span><strong>{{ state.profile?.votes_cast || 0 }}</strong></article>
      </section>
      <section class="market-section">
        <div class="section-heading"><div><span class="eyebrow">Created by you</span><h2>Project portfolio</h2></div><span>{{ ownProjects.length }} records</span></div>
        <div v-if="ownProjects.length" class="project-grid">
          <ProjectCard v-for="project in ownProjects" :key="project.id" :project="project" />
        </div>
        <div v-else class="empty-state"><h3>No launched projects yet</h3><p>Your projects will appear here after StudioNet accepts them.</p><RouterLink class="secondary-button" to="/projects/new">Launch project</RouterLink></div>
      </section>
    </template>
  </div>
</template>
