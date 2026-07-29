<script setup>
import { X } from "lucide-vue-next";
defineProps({
  title: { type: String, required: true },
  eyebrow: { type: String, default: "ProofFund action" },
});
defineEmits(["close"]);
</script>

<template>
  <div class="modal-backdrop" @click.self="$emit('close')">
    <section class="modal-panel" role="dialog" aria-modal="true" :aria-label="title">
      <header>
        <div><span>{{ eyebrow }}</span><h2>{{ title }}</h2></div>
        <button type="button" title="Close" @click="$emit('close')"><X :size="20" /></button>
      </header>
      <slot />
    </section>
  </div>
</template>
