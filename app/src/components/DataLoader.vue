<script setup>
defineProps({
  label: { type: String, default: "Reading StudioNet state" },
});
</script>

<template>
  <div class="data-loader" role="status" aria-live="polite">
    <div class="data-loader-current" aria-hidden="true">
      <i v-for="index in 5" :key="index" />
    </div>
    <strong>{{ label }}</strong>
    <span>VALIDATOR LEDGER / LIVE CONTRACT</span>
  </div>
</template>
