<script setup>
import { computed } from "vue";
import { ArrowUpRight, Users } from "lucide-vue-next";
import { fromWei } from "../services/genlayer";
import { projectImage, useImageFallback } from "../utils/projectImage";

const props = defineProps({ project: { type: Object, required: true } });

const percent = computed(() => {
  const goal = BigInt(props.project.funding_goal || 0);
  const funded = BigInt(props.project.funded_amount || 0);
  return goal ? Math.min(100, Number((funded * 100n) / goal)) : 0;
});
</script>

<template>
  <RouterLink class="project-card" :to="`/projects/${project.id}`">
    <div class="project-visual">
      <img
        :src="projectImage(project)"
        :alt="project.title"
        loading="lazy"
        @error="useImageFallback"
      />
      <span class="status-chip" :data-status="project.status">{{ project.status }}</span>
    </div>
    <div class="project-body">
      <div class="project-meta">
        <span>{{ project.category }}</span>
        <span>{{ project.id }}</span>
      </div>
      <h3>{{ project.title }}</h3>
      <p>{{ project.summary }}</p>
      <div class="funding-line">
        <strong>{{ fromWei(project.funded_amount) }} GEN</strong>
        <span>of {{ fromWei(project.funding_goal) }}</span>
      </div>
      <div class="progress-track">
        <span :style="{ width: `${percent}%` }"></span>
      </div>
      <div class="card-footer">
        <span><Users :size="15" /> {{ project.backer_count }} backers</span>
        <span class="open-label">Inspect <ArrowUpRight :size="15" /></span>
      </div>
    </div>
  </RouterLink>
</template>
