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
      <div class="gate-number">ACTION<br />GATE</div>
      <header>
        <span>{{ eyebrow }}</span>
        <h2>{{ title }}</h2>
        <button type="button" title="Close action gate" @click="$emit('close')">
          <X :size="22" />
        </button>
      </header>
      <div class="gate-content"><slot /></div>
    </section>
  </div>
</template>
