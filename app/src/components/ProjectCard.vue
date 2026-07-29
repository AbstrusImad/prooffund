<script setup>
import { computed } from "vue";
import { ArrowUpRight } from "lucide-vue-next";
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
    <div class="reservoir-level" :style="{ '--level': `${percent}%` }">
      <img
        :src="projectImage(project)"
        :alt="project.title"
        loading="lazy"
        @error="useImageFallback"
      />
      <i />
      <span>{{ percent }}%</span>
    </div>
    <div class="project-body">
      <div class="project-meta">
        <span>{{ project.id }}</span>
        <b :data-status="project.status">{{ project.status }}</b>
      </div>
      <h3>{{ project.title }}</h3>
      <p>{{ project.summary }}</p>
      <div class="funding-line">
        <strong>{{ fromWei(project.funded_amount) }}</strong>
        <span>/ {{ fromWei(project.funding_goal) }} GEN</span>
      </div>
      <div class="card-footer">
        <span>{{ project.backer_count }} SOURCES</span>
        <ArrowUpRight :size="19" />
      </div>
    </div>
  </RouterLink>
</template>
