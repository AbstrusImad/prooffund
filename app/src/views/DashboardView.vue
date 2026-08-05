<script setup>
import { computed, ref } from "vue";
import {
  ArrowRight,
  BadgeCheck,
  CircleDollarSign,
  Gavel,
  Landmark,
  Search,
  Sparkles,
} from "lucide-vue-next";
import ProjectCard from "../components/ProjectCard.vue";
import DataLoader from "../components/DataLoader.vue";
import { useProofFund } from "../stores/proofFund";
import { fromWei } from "../services/genlayer";

const { state } = useProofFund();
const query = ref("");
const filter = ref("ALL");

const projects = computed(() =>
  state.projects.filter((project) => {
    const matchesQuery = `${project.title} ${project.summary} ${project.category}`
      .toLowerCase()
      .includes(query.value.toLowerCase());
    const matchesFilter =
      filter.value === "ALL" ||
      (filter.value === "OPEN" && ["FUNDING", "ACTIVE"].includes(project.status)) ||
      project.status === filter.value;
    return matchesQuery && matchesFilter;
  }),
);
</script>

<template>
  <div class="page">
    <section class="dashboard-heading">
      <div>
        <span class="eyebrow"><Sparkles :size="15" /> Validator-governed capital</span>
        <h1>Fund outcomes.<br />Release on proof.</h1>
        <p>
          Milestone escrow for work that needs judgment, public evidence, and an
          appealable decision trail.
        </p>
        <div class="heading-actions">
          <RouterLink class="primary-button" to="/projects/new">
            Launch a project <ArrowRight :size="17" />
          </RouterLink>
          <a class="text-button" href="#market">Explore live projects</a>
        </div>
      </div>
      <div class="protocol-brief">
        <div class="brief-label"><span class="live-dot"></span> Protocol live</div>
        <div class="brief-flow">
          <span>Tranches</span><i></i><span>Governance</span><i></i><span>Consensus</span>
        </div>
        <p>Every release is linked to public criteria and validator-reviewed evidence.</p>
      </div>
    </section>

    <section class="stats-band">
      <article>
        <CircleDollarSign :size="20" />
        <span>Total funded</span>
        <strong>{{ fromWei(state.dashboard?.total_funded || 0) }} GEN</strong>
      </article>
      <article>
        <BadgeCheck :size="20" />
        <span>Released on proof</span>
        <strong>{{ fromWei(state.dashboard?.total_released || 0) }} GEN</strong>
      </article>
      <article>
        <Sparkles :size="20" />
        <span>Active projects</span>
        <strong>{{ state.dashboard?.active_projects || 0 }}</strong>
      </article>
      <article>
        <Gavel :size="20" />
        <span>Disputes opened</span>
        <strong>{{ state.dashboard?.total_disputes || 0 }}</strong>
      </article>
      <article>
        <Landmark :size="20" />
        <span>Open proposals</span>
        <strong>{{ state.dashboard?.open_proposals || 0 }}</strong>
      </article>
    </section>

    <section id="market" class="market-section">
      <div class="section-heading">
        <div><span class="eyebrow">StudioNet registry</span><h2>Capital in motion</h2></div>
        <span>{{ projects.length }} on-chain records</span>
      </div>

      <div class="market-toolbar">
        <label class="search-field">
          <Search :size="17" />
          <input v-model="query" type="search" placeholder="Search projects or categories" />
        </label>
        <div class="segmented-control">
          <button
            v-for="option in ['ALL', 'OPEN', 'COMPLETED']"
            :key="option"
            type="button"
            :class="{ active: filter === option }"
            @click="filter = option"
          >
            {{ option }}
          </button>
        </div>
      </div>

      <DataLoader
        v-if="!state.initialized && !state.error && !state.projects.length"
        label="Opening the project registry"
      />
      <div v-else-if="projects.length" class="project-grid">
        <ProjectCard v-for="project in projects" :key="project.id" :project="project" />
      </div>
      <div v-else class="empty-state">
        <div class="empty-symbol"><CircleDollarSign :size="30" /></div>
        <h3>No projects match this view</h3>
        <p>The registry only displays records read directly from the deployed contract.</p>
        <RouterLink class="secondary-button" to="/projects/new">Create the first project</RouterLink>
      </div>
    </section>
  </div>
</template>
